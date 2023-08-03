import json
import os
import time

import requests
from flask import current_app, jsonify, request
from pyVmomi import vim

from common.cleanup.cleanup_constants import SePrefixNames
from common.common_utilities import (
    checkObjectIsPresentAndReturnPath,
    getClusterID,
    getList,
    grabNsxtHeaders,
    isAviHaEnabled,
    isEnvTkgs_ns,
    isEnvTkgs_wcp,
    isWcpEnabled,
    obtain_avi_version,
    obtain_second_csrf,
)
from common.constants.constants import FirewallRulePrefix
from common.lib.kubectl_client import KubectlClient
from common.lib.nsxt_client import NsxtClient
from common.operation.constants import (
    VCF,
    ControllerLocation,
    Env,
    EnvType,
    FirewallRuleCgw,
    FirewallRuleMgw,
    GroupNameCgw,
    GroupNameMgw,
    KubernetesOva,
    Policy_Name,
    RegexPattern,
    SegmentsName,
    ServiceName,
    Type,
)
from common.operation.ShellHelper import (
    runProcess,
    runShellCommandAndReturnOutput,
    runShellCommandAndReturnOutputAsList,
    verifyPodsAreRunning,
)
from common.operation.vcenter_operations import checkVmPresent, get_dc, get_obj, getSi
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.tanzu_util import TanzuCommands, TanzuUtil

SUPPORTED_NON_VCD_ENV_LIST = [Env.VSPHERE, Env.VMC, Env.VCF]
SUPPORTED_ENV_LIST = SUPPORTED_NON_VCD_ENV_LIST.append(Env.VCD)
__author__ = "Pooja Deshmukh"


def cleanup_avi_vms(govc_client, env, datacenter, avi_list):
    try:
        for avi_fqdn in avi_list:
            vm_path = govc_client.get_vm_path(avi_fqdn)
            govc_client.delete_vm(avi_fqdn, vm_path.replace(" ", "#remove_me#"))
        return True, "NXS load balancer cleanup successful"
    except Exception as e:
        return False, str(e)


def fetch_mgmt_workload_se_engines(govc_client, env, data_center, spec, type=None):
    data_center = data_center.replace(" ", "#remove_me#")
    vm_list = []
    delete_only = "all"

    if type == Type.MANAGEMENT:
        vmc_se_vms_list = [
            ControllerLocation.CONTROLLER_SE_NAME,
            ControllerLocation.CONTROLLER_SE_NAME2,
        ]
        delete_only = SePrefixNames.Management

    elif type == Type.WORKLOAD:
        vmc_se_vms_list = [
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2,
        ]
        delete_only = SePrefixNames.Workload
    else:
        vmc_se_vms_list = [
            ControllerLocation.CONTROLLER_SE_NAME,
            ControllerLocation.CONTROLLER_SE_NAME2,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2,
        ]

    if isEnvTkgs_wcp(env):
        avi_fqdn = spec.tkgsComponentSpec.aviComponents.aviController01Fqdn
    elif env == Env.VSPHERE or env == Env.VCF:
        avi_fqdn = spec.tkgComponentSpec.aviComponents.aviController01Fqdn
    else:
        avi_fqdn = ControllerLocation.CONTROLLER_NAME

    # cleanup for non-orchestrated SE engine's VM.
    if env == Env.VSPHERE and not isEnvTkgs_wcp(env):
        is_non_orchestrated = False
        try:
            mode = spec.tkgComponentSpec.aviComponents.modeOfDeployment
            if mode == "non-orchestrated":
                is_non_orchestrated = True
        except Exception:
            is_non_orchestrated = False
        if is_non_orchestrated:
            for se_vm in vmc_se_vms_list:
                se_vm = se_vm.replace("vmc", "vsphere")
                if govc_client.find_vms_by_name(vm_name=se_vm, options="-dc " + data_center):
                    vm_list.append(se_vm)
    if env == Env.VMC:
        for se_vm in vmc_se_vms_list:
            if govc_client.find_vms_by_name(vm_name=se_vm, options="-dc " + data_center):
                vm_list.append(se_vm)
    if govc_client.find_vms_by_name(vm_name=avi_fqdn):
        try:
            ip = govc_client.get_vm_ip(avi_fqdn)[0]
            if ip is None:
                current_app.logger.warn("Unable to fetch IP address for NSX ALB LoadBalancer")
                return True, vm_list
        except Exception:
            current_app.logger.warn("Unable to fetch IP address for NSX ALB LoadBalancer")
            return True, vm_list

        try:
            deployed_avi_version = obtain_avi_version(ip, env)
            if deployed_avi_version[0] is None:
                current_app.logger.warn("Failed to obtain deployed AVI version")
                return True, vm_list
            csrf2 = obtain_second_csrf(ip, env)
            if csrf2 is None:
                current_app.logger.warn("Failed to get csrf for AVI")
                return True, vm_list
        except Exception:
            current_app.logger.error("Failed to login to NSX ALB LoadBalancer")
            return True, vm_list

        url = "https://" + str(ip) + "/api/serviceengine-inventory"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": deployed_avi_version[0],
            "x-csrftoken": csrf2[0],
        }
        payload = {}
        try:
            response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code != 200:
                current_app.logger.error(response_csrf.json())
                current_app.logger.error("Failed to fetch AVI Service Engine VM details")
                return False, []

            else:
                for config in response_csrf.json()["results"]:
                    if delete_only not in config["config"]["name"] and delete_only != "all":
                        continue
                    if govc_client.find_vms_by_name(config["config"]["name"], options="-dc " + data_center):
                        current_app.logger.info(config["config"]["name"] + " is present in datacenter " + data_center)
                        vm_list.append(config["config"]["name"])
                return True, vm_list
        except Exception:
            current_app.logger.warn("Failed to login to NSX Load Balancer")
            return True, vm_list
    else:
        current_app.logger.warn("NSX ALB Controller VM not found")
        return True, vm_list


def fetch_avi_vms(govc_client, env, data_center, spec):
    data_center = data_center.replace(" ", "#remove_me#")
    vm_list = []
    if isEnvTkgs_wcp(env):
        avi_fqdn = spec.tkgsComponentSpec.aviComponents.aviController01Fqdn
    elif env == Env.VSPHERE or env == Env.VCF:
        avi_fqdn = spec.tkgComponentSpec.aviComponents.aviController01Fqdn
    else:
        avi_fqdn = ControllerLocation.CONTROLLER_NAME

    if env == Env.VMC:
        if isAviHaEnabled(env):
            if govc_client.find_vms_by_name(vm_name=ControllerLocation.CONTROLLER_NAME2, options="-dc " + data_center):
                vm_list.append(ControllerLocation.CONTROLLER_NAME2)
            if govc_client.find_vms_by_name(vm_name=ControllerLocation.CONTROLLER_NAME3, options="-dc " + data_center):
                vm_list.append(ControllerLocation.CONTROLLER_NAME3)

    elif isAviHaEnabled(env):
        if isEnvTkgs_wcp(env):
            avi_fqdn2 = spec.tkgsComponentSpec.aviComponents.aviController02Fqdn
            avi_fqdn3 = spec.tkgsComponentSpec.aviComponents.aviController03Fqdn
        else:
            avi_fqdn2 = spec.tkgComponentSpec.aviComponents.aviController02Fqdn
            avi_fqdn3 = spec.tkgComponentSpec.aviComponents.aviController03Fqdn

        if govc_client.find_vms_by_name(vm_name=avi_fqdn2, options="-dc " + data_center):
            vm_list.append(avi_fqdn2)
        if govc_client.find_vms_by_name(vm_name=avi_fqdn3, options="-dc " + data_center):
            vm_list.append(avi_fqdn3)
    if govc_client.find_vms_by_name(vm_name=avi_fqdn):
        vm_list.append(avi_fqdn)
    else:
        current_app.logger.warn("NSX ALB Controller VM not found")
        return False, []
    return True, vm_list


def cleanup_resource_pools(govc_client, env, vc_datcenter, vc_cluster, parent_rp, delete_pool):
    if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env) or not parent_rp:
        resource_pool_path = "/" + vc_datcenter + "/host/" + vc_cluster + "/Resources/"
    else:
        resource_pool_path = "/" + vc_datcenter + "/host/" + vc_cluster + "/Resources/" + parent_rp + "/"
    resource_pools = fetch_resource_pools(env, vc_datcenter, vc_cluster, parent_rp, delete_pool)
    for rp in resource_pools[1]:
        current_app.logger.info(rp + " resource pool exists, deleting it")
        if child_elements(vc_datcenter, rp):
            current_app.logger.info(rp + " skipped deletion due to the presence of virtual machines")
        elif clusterNodes(vc_datcenter, rp):
            current_app.logger.info(rp + " skipped deletion due to the presence cluster nodes")
        else:
            govc_client.delete_resource_pool(resource_pool_path.replace(" ", "#remove_me#") + rp)
            current_app.logger.info(rp + " deleted successfully")
    return True, "Resource pools deleted successfully"


def child_elements(vc_datcenter, resource_pool):
    password = current_app.config["VC_PASSWORD"]
    username = current_app.config["VC_USER"]
    vcenter_host = current_app.config["VC_IP"]
    rp_vms = []
    datacenter_obj = get_dc(getSi(vcenter_host, username, password), vc_datcenter)
    vms = datacenter_obj.vmFolder.childEntity
    for vm in vms:
        if isinstance(vm, vim.VirtualMachine):
            rp_obj = vm.resourcePool
            if rp_obj:
                if rp_obj.name == resource_pool:
                    rp_vms.append(vm.name)

    if rp_vms:
        current_app.logger.info(resource_pool + " resource pool contains virtual machines - " + str(rp_vms))
        return True
    return False


def clusterNodes(vc_datcenter, resource_pool):
    data_center = vc_datcenter.replace(" ", "#remove_me#")

    command = ["govc", "ls", "/" + data_center.replace("#remove_me#", " ") + "/vm/" + resource_pool.lower()]
    node_list = runShellCommandAndReturnOutputAsList(command)
    if node_list[1] != 0:
        return False
    for ele in node_list[0]:
        if resource_pool in ele:
            current_app.logger.info(
                resource_pool + " resource pool still contains cluster nodes - " + str(node_list[0])
            )
            return True
    return False


def fetch_resource_pools(env, vc_datcenter, vc_cluster, parent_rp, delete_pool):
    to_be_deleted = []
    if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env) or not parent_rp:
        resource_pool_path = "/" + vc_datcenter + "/host/" + vc_cluster + "/Resources/"
    else:
        resource_pool_path = "/" + vc_datcenter + "/host/" + vc_cluster + "/Resources/" + parent_rp + "/"

    password = current_app.config["VC_PASSWORD"]
    username = current_app.config["VC_USER"]
    vcenter_host = current_app.config["VC_IP"]

    si = getSi(vcenter_host, username, password)
    content = si.RetrieveContent()

    for resource_pool in delete_pool:
        resource_pool_obj = get_obj(content, [vim.ResourcePool], resource_pool)
        obj = content.searchIndex.FindByInventoryPath(resource_pool_path + resource_pool)
        if obj is None:
            current_app.logger.info(resource_pool + " resource pool does not exist.")
        elif hasattr(resource_pool_obj, "childEntity"):
            current_app.logger.info(resource_pool + " has child elements. Hence, its deletion is skipped")
        else:
            to_be_deleted.append(resource_pool)

    return True, to_be_deleted


def cleanup_content_libraries(delete_lib):
    try:
        retain_content_lib = request.headers["Retain"]
        if retain_content_lib.lower() == "true":
            retain_content_lib = True
        else:
            retain_content_lib = False
    except Exception:
        retain_content_lib = False

    if not retain_content_lib:
        list_libraries = ["govc", "library.ls"]
        list_output = runShellCommandAndReturnOutputAsList(list_libraries)
        if list_output[1] != 0:
            current_app.logger.error(list_output[0])
            return False, "Command to list content libraries failed"

        for library in delete_lib:
            if "/" + library in list_output[0]:
                current_app.logger.info(library + " - Content Library exists, deleting it")
                delete_command = ["govc", "library.rm", "/" + library]
                delete_output = runShellCommandAndReturnOutputAsList(delete_command)
                if delete_output[1] != 0:
                    current_app.logger.error(delete_output[0])
                    return False, "Failed to delete content library - " + library
                elif delete_output[0]:
                    if delete_output[0][0].__contains__("403 Forbidden"):
                        current_app.logger.info(delete_output[0])
                        current_app.logger.info(library + " - could not be deleted due to permission issue")
                else:
                    current_app.logger.info(library + " - Content Library deleted successfully")
            else:
                current_app.logger.info(library + " - Content Library does not exist")

        return True, "Successfully Deleted Content library"
    else:
        return True, "Skipped deleting content library"


def cleanup_downloaded_ovas(delete_files):
    try:
        retain_downloaded_ova = request.headers["Retain"]
        if retain_downloaded_ova.lower() == "true":
            retain_downloaded_ova = True
        else:
            retain_downloaded_ova = False
    except Exception:
        retain_downloaded_ova = False
    if not retain_downloaded_ova:
        path = "/tmp/"
        for file in delete_files:
            delete_ova = "rm " + path + file
            os.system(delete_ova)
        return True, "All OVAs downloaded during SIVT deployment are deleted."
    else:
        return True, "Skipped deleting downloaded Kubernetes OVAs"


def get_ova_filename(os, version):
    if version is None:
        version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION

    if os == "photon":
        return KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + version
    elif os == "ubuntu":
        return KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + version
    else:
        return None


# ask user
def delete_kubernetes_templates(govc_client, vcenter_host, username, password, datacenter, avi_uuid):
    try:
        try:
            retain_k8s_templates = request.headers["Retain"]
            if retain_k8s_templates.lower() == "true":
                retain_k8s_templates = True
            else:
                retain_k8s_templates = False
        except Exception:
            retain_k8s_templates = False
        if not retain_k8s_templates:
            deployed_templates = get_deployed_templates(vcenter_host, username, password, avi_uuid)
            if deployed_templates[0]:
                deployed_templates = deployed_templates[1]
            else:
                return False
            for template in deployed_templates:
                current_app.logger.info("deleting template - " + template)
                vm_path = govc_client.get_vm_path(template)
                if vm_path:
                    govc_client.delete_vm(template, vm_path)
                current_app.logger.info(f"{template} deleted.")
            return True
        else:
            current_app.logger.info("Skipped deleting kubernetes templates")
            return True
    except Exception as e:
        current_app.logger.error("Exception occurred while deleting Kubernetes templates ")
        current_app.logger.error(str(e))
        return False


def get_avi_uuid(center_host, username, password):
    avi_uuid = None
    vm_state = checkVmPresent(center_host, username, password, ControllerLocation.CONTROLLER_NAME)
    if not (vm_state is None):
        avi_uuid = vm_state.config.uuid
    return avi_uuid


def get_deployed_templates(vcenter_host, username, password, avi_uuid):
    try:
        delete_templates = []
        si = getSi(vcenter_host, username, password)
        content = si.RetrieveContent()
        all_vms = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], recursive=True).view

        for vm in all_vms:
            if vm.config.template:
                if vm.name.startswith(
                    KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-"
                ) or vm.name.startswith(KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-"):
                    delete_templates.append(vm.name)
                elif vm.name.startswith(ControllerLocation.SE_OVA_TEMPLATE_NAME) and not (avi_uuid is None):
                    if vm.name == ControllerLocation.SE_OVA_TEMPLATE_NAME + "_" + avi_uuid:
                        delete_templates.append(ControllerLocation.SE_OVA_TEMPLATE_NAME + "_" + avi_uuid)
        return True, delete_templates
    except Exception as e:
        current_app.logger.error(str(e))
        return False, None


# mgmt one
def delete_config_yaml():
    command = ["rm", "-r", "/root/.config/tanzu/config.yaml", "/root/.config/tanzu/tkg/config.yaml"]
    delete_output = runShellCommandAndReturnOutputAsList(command)
    if delete_output[1] != 0:
        current_app.logger.error(delete_output[0])
        return False
    return True


def delete_folders(env, vcenter_host, username, password, folders):
    try:
        si = getSi(vcenter_host, username, password)
        content = si.RetrieveContent()
        for folder in folders:
            folder_obj = get_obj(content, [vim.Folder], folder)
            if folder_obj:
                if folder_obj.childEntity:
                    current_app.logger.info(folder + " folder contains child elements hence, skipping it's deletion")
                else:
                    current_app.logger.info("deleting folder - " + folder)
                    folder_obj.Destroy_Task()
                    current_app.logger.info(f"{folder} deleted.")
                    time.sleep(1)
            else:
                current_app.logger.debug("Folder " + folder + " does not exist")
        return True
    except Exception as e:
        current_app.logger.error("Exception occurred while deleting folders")
        current_app.logger.error(str(e))
        return False


def getCluster(cluster):
    podRunninng = TanzuCommands.CLUSTER_LIST
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if command_status[1] != 0:
        return False

    # fetch the cluster even if it is in error state
    try:
        for line in command_status[0]:
            if line.split()[0] == cluster:
                return True
        return False
    except Exception:
        return False


def getAllClusters_tkgs(vc_ip, vc_user, password, namspaces, vc_cluster):
    cluster_list = []
    current_app.logger.info("Checking workload cluster...")
    cluster_id = getClusterID(vc_ip, vc_user, password, vc_cluster)
    if cluster_id[1] != 200:
        current_app.logger.error(cluster_id[0])
        return None, cluster_id[0].json["msg"]

    cluster_id = cluster_id[0]
    wcp_status = isWcpEnabled(cluster_id)
    if wcp_status[0]:
        endpoint_ip = wcp_status[1]["api_server_cluster_endpoint"]
    else:
        return None, "Failed to obtain cluster endpoint IP on given cluster - " + vc_cluster
    current_app.logger.info("logging into cluster - " + endpoint_ip)
    os.putenv("KUBECTL_VSPHERE_PASSWORD", password)
    for ns in namspaces:
        connect_command = KubectlUtil.KUBECTL_VPSHERE_LOGIN_TKGS_NS.format(
            vc_user=vc_user, endpoint_ip=endpoint_ip, ns=ns
        )
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            current_app.logger.error(output[0])
            return None, "Failed to login to cluster endpoint - " + endpoint_ip
        switch_context = KubectlUtil.KUBECTL_USE_TKGS_NS_CONTEXT.format(namespace=ns)
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if context_output[1] != 0:
            current_app.logger.error(context_output[0])
            return None, "Failed to login to cluster context - " + ns

        command = KubectlUtil.KUBECTL_GET_TKC
        cluster_output = runShellCommandAndReturnOutputAsList(command)
        if cluster_output[1] != 0:
            current_app.logger.error(cluster_output[0])
        else:
            for line in cluster_output[0]:
                if not line.__contains__("NAME"):
                    if line.__contains__("No resources found"):
                        current_app.logger.info("No workload clusters found on namespace " + ns)
                    else:
                        cluster_list.append(line.split()[0])
        command = KubectlUtil.KUBECTL_GET_CLUSTER
        cluster_output = runShellCommandAndReturnOutputAsList(command)
        if cluster_output[1] != 0:
            current_app.logger.error(cluster_output[0])
        else:
            for line in cluster_output[0]:
                if not line.__contains__("NAME"):
                    if line.__contains__("No resources found"):
                        current_app.logger.info("No workload clusters found on namespace " + ns)
                    else:
                        cluster_list.append(line.split()[0])
    return cluster_list, "Obtained workload clusters successfully"


def delete_nsxt_components(url, header, list_components):
    for element in list_components:
        response = requests.request("DELETE", url + element, headers=header, verify=False)
        if response.status_code != 200:
            return False, str(response.text)
        else:
            current_app.logger.info(element + " deleted")

    return True, "SUCCESS"


def nsxt_list_groups():
    return [
        VCF.ESXI_GROUP,
        VCF.ARCAS_GROUP,
        GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group,
        GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group,
        GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group,
        GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW,
    ]


def nsxt_list_services():
    return [ServiceName.ARCAS_BACKEND_SVC, ServiceName.ARCAS_SVC, ServiceName.KUBE_VIP_VCF_SERVICE]


def vmc_list_mgw_firewall_rules():
    return [
        FirewallRulePrefix.INFRA_TO_VC,
        FirewallRulePrefix.MGMT_TO_ESXI,
        FirewallRuleMgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVItovCenter,
    ]


def vmc_list_cgw_firewall_rules():
    return [
        FirewallRulePrefix.INFRA_TO_NTP,
        FirewallRulePrefix.INFRA_TO_DNS,
        FirewallRulePrefix.INFRA_TO_VC,
        FirewallRulePrefix.INFRA_TO_ANY,
        FirewallRulePrefix.INFRA_TO_ALB,
        FirewallRulePrefix.INFRA_TO_CLUSTER_VIP,
        FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS,
        FirewallRuleCgw.DISPLAY_NAME_TKG_WORKLOAD_to_vCenter,
        FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_to_Internet,
    ]


def vmc_list_cgw_inventory_groups():
    return [
        GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_TKG_Management_Network_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_DNS_IPs_Group,
        GroupNameCgw.DISPLAY_NAME_NTP_IPs_Group,
        GroupNameCgw.DISPLAY_NAME_vCenter_IP_Group,
    ]


def vmc_list_mgw_inventory_groups():
    return [
        GroupNameMgw.DISPLAY_NAME_TKG_Management_Network_Group_Mgw,
        GroupNameMgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_MGW,
        GroupNameMgw.DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw,
        GroupNameMgw.DISPLAY_NAME_AVI_Management_Network_Group_Mgw,
        GroupNameMgw.DISPLAY_NAME_Tkg_Shared_Network_Group_Mgw,
    ]


def list_network_segments(env, spec):
    if env == Env.VMC:
        list_of_segments = [
            SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT,
            SegmentsName.DISPLAY_NAME_CLUSTER_VIP,
            SegmentsName.DISPLAY_NAME_TKG_WORKLOAD,
            SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
            SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
            SegmentsName.DISPLAY_NAME_AVI_DATA_SEGMENT,
        ]

        listOfSegment = NsxtClient(current_app.config).list_segments(gateway_id="cgw")
        for segment in list_of_segments:
            if not NsxtClient.find_object(listOfSegment, segment):
                current_app.logger.info(segment + " network segment not found in environment.")
                list_of_segments.remove(segment)

    elif env == Env.VCF:
        list_of_segments = [
            spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkName,
            spec.tkgWorkloadComponents.tkgWorkloadNetworkName,
            spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName,
            spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceNetworkName,
        ]
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            current_app.logger.error("Failed to nsxt info " + str(headers_[1]))
            return list_of_segments
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            current_app.logger.error("Failed to get list of segments " + str(output[0]))
            return list_of_segments

        for segmentName in list_of_segments:
            if not checkObjectIsPresentAndReturnPath(output[0], segmentName)[0]:
                current_app.logger.info(segmentName + " network segment not found in environment.")
                list_of_segments.remove(segmentName)

    else:
        list_of_segments = []

    return list_of_segments


def get_vcenter_sessionID(vCenter, vCenter_user, VC_PASSWORD):
    try:
        sess = requests.post(
            "https://" + vCenter + "/rest/com/vmware/cis/session",
            auth=(vCenter_user, VC_PASSWORD),
            verify=False,
        )
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        else:
            vc_session = sess.json()["value"]
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully fetched session ID for vCenter - " + vCenter,
                "STATUS_CODE": 200,
                "vc_session": str(vc_session),
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "Exception occured while fetching session ID for vCenter",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500


def delete_cluster(cluster):
    try:
        current_app.logger.info("Initiating deletion of cluster - " + cluster)
        delete = TanzuCommands.CLUSTER_DELETE.format(cluster_name=cluster)
        delete_status = runShellCommandAndReturnOutputAsList(delete)
        if delete_status[1] != 0:
            current_app.logger.error("Command to delete - " + cluster + " Failed")
            current_app.logger.debug(delete_status[0])
            d = {"responseType": "ERROR", "msg": "Failed delete cluster - " + cluster, "STATUS_CODE": 500}
            return jsonify(d), 500
        cluster_running = TanzuCommands.CLUSTER_LIST
        command_status = runShellCommandAndReturnOutputAsList(cluster_running)
        if command_status[1] != 0:
            current_app.logger.error("Failed to run command to check status of workload cluster - " + cluster)
            return False
        deleting = True
        count = 0
        while count < 360 and deleting:
            if verifyPodsAreRunning(cluster, command_status[0], RegexPattern.deleting) or verifyPodsAreRunning(
                cluster, command_status[0], RegexPattern.running
            ):
                current_app.logger.info("Waiting for " + cluster + " deletion to complete...")
                current_app.logger.info("Retrying in 10s...")
                time.sleep(10)
                count = count + 1
                command_status = runShellCommandAndReturnOutputAsList(cluster_running)
            else:
                deleting = False
        if not deleting:
            return True

        current_app.logger.error("waited for " + str(count * 5) + "s")
        return False
    except Exception as e:
        current_app.logger.error("Exception occurred while deleting cluster " + str(e))
        return False


def cluster_exists(env, cluster):
    try:
        if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env):
            listn = KubectlUtil.KUBECTL_GET_TKC
            list_beta = KubectlUtil.KUBECTL_GET_CLUSTER
        o = runShellCommandAndReturnOutput(listn)
        o_beta = runShellCommandAndReturnOutput(list_beta)
        if o[1] == 0:
            try:
                if o[1] == 0 and o[0].__contains__(cluster):
                    return True
                elif o_beta[1] == 0 and o_beta[0].__contains__(cluster):
                    return True
                else:
                    return False
            except Exception:
                return False
        else:
            return False
    except Exception:
        return False


def management_exists(mgmt_cluster):
    try:
        o = TanzuUtil.get_management_cluster_output()
        if o[1] == 0:
            try:
                if o[0].__contains__(mgmt_cluster):
                    return True
                else:
                    return False
            except Exception:
                return False
        else:
            return False
    except Exception:
        return False


def kubectl_configs_cleanup(env, clusters):
    try:
        kubectl_client = KubectlClient(LocalCmdHelper())
        current_app.logger.info("Deleting contexts of clusters")
        for cluster in clusters:
            if isEnvTkgs_wcp(env):
                try:
                    delete = kubectl_client.delete_cluster_context_tkgs(cluster)
                    if delete == 0:
                        current_app.logger.info(cluster + " context deleted successfully")
                    else:
                        current_app.logger.error("Failed to delete kubectl context for cluster - " + cluster)
                except Exception:
                    current_app.logger.info("Cluster context does not exist for " + cluster)
            else:
                try:
                    delete = kubectl_client.delete_cluster_context(cluster)
                    if delete == 0:
                        current_app.logger.info(cluster + " context deleted successfully")
                    else:
                        current_app.logger.error("Failed to delete kubectl context for cluster - " + cluster)

                    delete_cluster = kubectl_client.delete_cluster(cluster)
                    if delete_cluster == 0:
                        current_app.logger.info(cluster + " context deleted successfully")
                    else:
                        current_app.logger.error("Failed to delete kubectl context for cluster - " + cluster)
                except Exception:
                    current_app.logger.info("Cluster context does not exist for " + cluster)
        return True, "kubectl contexts deleted successfully"
    except Exception as e:
        current_app.logger.error("Exception occurred while cleaning cluster contexts - " + str(e))
        return False


def get_context_name(env, cluster):
    try:
        command = KubectlUtil.KUBECTL_GET_CONTEXT
        command_status = runShellCommandAndReturnOutputAsList(command)
        if command_status[1] != 0:
            current_app.logger.error(command_status[0])
            return None

        for context in command_status[0]:
            if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
                if context.split()[0] == cluster:
                    return context.split()[0]
                elif context.split()[1] == cluster:
                    return context.split()[1]
            else:
                if context.split()[2] == cluster:
                    return context.split()[1]
                elif context.split()[1] == cluster:
                    return context.split()[0]

        return None
    except Exception as e:
        current_app.logger.error(str(e))
        return None


def delete_vcf_components(env, spec):
    current_app.logger.info("Deleting NSX-T components")
    headers_ = grabNsxtHeaders()
    if headers_[0] is None:
        return False, headers_[1]
    headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})

    current_app.logger.info("Deleting NSX-T gateway policies...")
    url = "https://" + headers_[2] + "/policy/api/v1/infra/domains/default/gateway-policies/"
    delete_policy = delete_nsxt_components(url, headers_[1], [Policy_Name.POLICY_NAME])
    if not delete_policy[0]:
        current_app.logger.error(delete_policy[1])
        return False, delete_policy[1]
    current_app.logger.info("Gateway policies deleted successfully")

    current_app.logger.info("Deleting Inventory groups and firewall rules...")
    url = "https://" + headers_[2] + "/policy/api/v1/infra/domains/default/groups/"
    delete_groups = delete_nsxt_components(url, headers_[1], nsxt_list_groups())
    if not delete_groups[0]:
        current_app.logger.error(delete_groups[1])
        return False, delete_groups[1]
    current_app.logger.info("Inventory groups and firewall rules deleted successfully")

    current_app.logger.info("Deleting Services...")
    url = "https://" + headers_[2] + "/policy/api/v1/infra/services/"
    delete_services = delete_nsxt_components(url, headers_[1], nsxt_list_services())
    if not delete_services[0]:
        current_app.logger.error(delete_services[1])
        return False, delete_services[1]
    current_app.logger.info("Services deleted successfully")

    current_app.logger.info("Deleting network Segments...")
    time.sleep(30)
    url = "https://" + headers_[2] + "/policy/api/v1/infra/segments/"
    delete_segments = delete_nsxt_components(url, headers_[1], list_network_segments(env, spec))
    if not delete_segments[0]:
        current_app.logger.error(delete_segments[1])
        return False, delete_segments[1]
    return True, "Successfully deleted NSX-T components"


def delete_vmc_components(env, spec):
    current_app.logger.info("Deleting VMC components")
    headers = {"Content-Type": "application/json", "csp-auth-token": current_app.config["access_token"]}

    url = (
        current_app.config["NSX_REVERSE_PROXY_URL"]
        + "orgs/"
        + current_app.config["ORG_ID"]
        + "/sddcs/"
        + current_app.config["SDDC_ID"]
    )

    current_app.logger.info("Deleting firewall rules for compute Gateway...")
    del_cgw_rules = delete_nsxt_components(
        url + "/policy/api/v1/infra/domains/cgw/gateway-policies/default/rules/",
        headers,
        vmc_list_cgw_firewall_rules(),
    )
    if not del_cgw_rules[0]:
        current_app.logger.error(del_cgw_rules[1])
        return False, del_cgw_rules[1]
    current_app.logger.info("Firewall rules for Compute Gateway deleted successfully...")

    current_app.logger.info("Deleting firewall rules for Management Gateway...")
    del_mgw_rules = delete_nsxt_components(
        url + "/policy/api/v1/infra/domains/mgw/gateway-policies/default/rules/",
        headers,
        vmc_list_mgw_firewall_rules(),
    )
    if not del_cgw_rules[0]:
        current_app.logger.error(del_mgw_rules[1])
        return False, del_mgw_rules[1]
    current_app.logger.info("Firewall rules for Management Gateway deleted successfully...")

    current_app.logger.info("Deleting services... ")
    del_services = delete_nsxt_components(
        url + "/policy/api/v1/infra/services/", headers, [ServiceName.KUBE_VIP_SERVICE]
    )
    if not del_services[0]:
        current_app.logger.error(del_services[1])
        return False, del_services[1]
    current_app.logger.info("Services deleted successfully... ")

    current_app.logger.info("Deleting inventory groups for Management Gateway...")
    del_mgw_inventory_grps = delete_nsxt_components(
        url + "/policy/api/v1/infra/domains/mgw/groups/", headers, vmc_list_mgw_inventory_groups()
    )
    if not del_mgw_inventory_grps[0]:
        current_app.logger.error(del_mgw_inventory_grps[1])
        return False, del_mgw_inventory_grps[1]
    current_app.logger.info("Inventory groups for Management Gateway deleted successfully")

    current_app.logger.info("Deleting inventory groups for Compute Gateway...")
    del_cgw_inventory_grps = delete_nsxt_components(
        url + "/policy/api/v1/infra/domains/cgw/groups/", headers, vmc_list_cgw_inventory_groups()
    )
    if not del_cgw_inventory_grps[0]:
        current_app.logger.error(del_cgw_inventory_grps[1])
        return False, del_cgw_inventory_grps[1]
    current_app.logger.info("Inventory groups for Compute Gateway deleted successfully")

    current_app.logger.info("Deleting network segments...")
    time.sleep(30)
    del_segments = delete_nsxt_components(
        url + "/policy/api/v1/infra/tier-1s/cgw/segments/", headers, list_network_segments(env, spec)
    )
    if not del_segments[0]:
        current_app.logger.error(del_segments[1])
        return False, del_segments[1]
    return True, "Successfully deleted VMC components"


def delete_tmc_cluster(clusters, is_mgmt):
    try:
        for cls in clusters:
            if not is_mgmt:
                current_app.logger.info("Performing TMC cleanup for workload clusters")
                command = ["tmc", "cluster", "list"]
                command_status = runShellCommandAndReturnOutputAsList(command)
                if command_status[1] != 0:
                    current_app.logger.error("Failed to run command to check status of workload cluster - " + cls)
                    return False
                for line in command_status[0]:
                    if line.split()[0] == cls:
                        current_app.logger.info("Un-register cluster " + cls + " from TMC")
                        delete_command = [
                            "tmc",
                            "cluster",
                            "delete",
                            cls,
                            "-m",
                            line.split()[1],
                            "-p",
                            line.split()[2],
                            "--force",
                        ]
                        current_app.logger.debug(delete_command)
                        delete_status = runShellCommandAndReturnOutputAsList(delete_command)
                        if delete_status[1] != 0:
                            current_app.logger.error(delete_status[0])
                            current_app.logger.error("Failed to un-register cluster - " + cls + " from TMC")
                            return False
                        else:
                            current_app.logger.info(cls + " un-registered from TMC successfully")
            else:
                current_app.logger.info("Performing TMC cleanup for management clusters")
                mgmt_command = ["tmc", "managementcluster", "list"]
                mgmt_command_status = runShellCommandAndReturnOutputAsList(mgmt_command)
                if mgmt_command_status[1] != 0:
                    current_app.logger.error("Failed to run command to check status of workload cluster - " + cls)
                    return False
                for mgmt in mgmt_command_status[0]:
                    if mgmt.strip() == cls:
                        current_app.logger.info("Un-register cluster " + cls + " from TMC")
                        delete_mgmt = ["tmc", "managementcluster", "delete", cls, "--force"]
                        delete_mgmt_status = runShellCommandAndReturnOutputAsList(delete_mgmt)
                        if delete_mgmt_status[1] != 0:
                            current_app.logger.error(delete_mgmt_status[0])
                            current_app.logger.error("Failed to un-register cluster - " + cls + " from TMC")
                            return False
                        else:
                            current_app.logger.info(cls + " un-registered from TMC successfully")
        return True
    except Exception as e:
        current_app.logger.error(str(e))
        return False


def delete_mgmt_cluster(mgmt_cluster):
    try:
        current_app.logger.info("Delete Management cluster - " + mgmt_cluster)
        delete_command = TanzuCommands.MANAGEMENT_CLUSTER_DELETE
        runProcess(delete_command)

        deleted = False
        count = 0
        while count < 360 and not deleted:
            if management_exists(mgmt_cluster):
                current_app.logger.debug("Management cluster is still not deleted... retrying in 10s")
                time.sleep(10)
                count = count + 1
            else:
                deleted = True
                break

        if not deleted:
            current_app.logger.error(
                "Management cluster " + mgmt_cluster + " is not deleted even after " + str(count * 5) + "s"
            )
            return False
        else:
            return True

        return False

    except Exception as e:
        current_app.logger.error(str(e))
        return False


def delete_tkgs_workload_cluster(env, namespace, vc_user, endpoint_ip, cluster_kind):
    try:
        current_app.logger.info("Logging into cluster" + endpoint_ip)
        connect_command = KubectlUtil.KUBECTL_VPSHERE_LOGIN_TKGS_NS.format(
            vc_user=vc_user, endpoint_ip=endpoint_ip, ns=namespace
        )
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            current_app.logger.error(output[0])
            return False, "Failed to login to cluster endpoint - " + endpoint_ip
        current_app.logger.info("Switching context to " + namespace)
        switch_context = KubectlUtil.KUBECTL_USE_TKGS_NS_CONTEXT.format(namespace=namespace)
        current_app.logger.info(switch_context)
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if context_output[1] != 0:
            current_app.logger.error(context_output[0])
            return False, "Failed to login to cluster context - " + namespace
        current_app.logger.info("Initiating deletion of TKG workload clusters - ")
        cluster_list = []
        switch_context = KubectlUtil.KUBECTL_USE_TKGS_NS_CONTEXT.format(namespace=namespace)
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if context_output[1] != 0:
            current_app.logger.error(context_output[0])
            return False, "Failed to login to cluster context - " + namespace

        if cluster_kind == EnvType.TKGS_CLUSTER_CLASS_KIND:
            command = KubectlUtil.KUBECTL_GET_CLUSTER
        else:
            command = KubectlUtil.KUBECTL_GET_TKC
        cluster_output = runShellCommandAndReturnOutputAsList(command)
        if cluster_output[1] != 0:
            current_app.logger.error(cluster_output[0])
        else:
            for line in cluster_output[0]:
                if not line.__contains__("NAME"):
                    if line.__contains__("No resources found"):
                        current_app.logger.info("No workload clusters found on namespace " + namespace)
                    else:
                        cluster_list.append(line.split()[0])
        if len(cluster_list) != 0:
            for cluster in cluster_list:
                if cluster_kind == EnvType.TKGS_CLUSTER_CLASS_KIND:
                    delete_cmd = KubectlUtil.KUBECTL_DELETE_TKGS_CLUSTER_BETA.format(
                        namespace=namespace, cluster=cluster
                    )
                else:
                    delete_cmd = KubectlUtil.KUBECTL_DELETE_TKGS_CLUSTER.format(namespace=namespace, cluster=cluster)
                current_app.logger.info("Deleting cluster " + cluster)
                runProcess(delete_cmd)
                deleted = False
                count = 0
                while count < 360 and not deleted:
                    if cluster_exists(env, cluster):
                        current_app.logger.debug("waited for " + str(count * 5) + "s")
                        time.sleep(10)
                        count = count + 1
                    else:
                        deleted = True
                        break
        if cluster_kind == EnvType.TKGS_CLUSTER_CLASS_KIND:
            cluster_running = KubectlUtil.KUBECTL_GET_CLUSTER
        else:
            cluster_running = KubectlUtil.KUBECTL_GET_TKC
        command_status = runShellCommandAndReturnOutputAsList(cluster_running)
        if command_status[1] != 0:
            return False, "Failed to run command to check status of workload cluster"
        if command_status[1] == 0:
            current_app.logger.info("Workload cluster deleted successfully")
            return True, "Workload cluster deleted successfully"
    except Exception:
        return False, "Exception occurred while deleting TKG workload cluster"


def delete_extensions(env, cluster, vc_user, endpoint_ip):
    current_app.logger.info("Cleanup: Deleting Extensions")
    user_added_extns = []
    if isEnvTkgs_ns(env):
        current_app.logger.info("Logging into vsphere")
        connect_command = KubectlUtil.CLUSTER_LOGIN.format(cluster_ip=endpoint_ip, vcenter_username=vc_user)
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            current_app.logger.error(output[0])
            return False, "Failed to login to cluster endpoint - " + endpoint_ip
        switch_context = KubectlUtil.SWITCH_CONTEXT.format(cluster_ip=cluster)
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if context_output[1] != 0:
            current_app.logger.error(context_output[0])
            return None, "Failed to login to cluster context - " + cluster
    current_app.logger.info("Checking list of all installed packages")
    extensions_json = TanzuUtil.get_installed_package_json()
    if extensions_json[1] != 0:
        current_app.logger.error(extensions_json[0])
        return False, "Failed to get extension list to cluster"
    all_extns_list = json.loads(extensions_json[0])
    for extn in all_extns_list:
        # to skip to deletion of other packages apart from user-added packages , following check is added
        if extn["namespace"] == "tkg-system":
            continue
        user_added_extns.append(extn)
    if len(user_added_extns) == 0:
        current_app.logger.info("No Extensions found for deletion")
        return True, "No Extensions found for deletion"
    current_app.logger.info("Fetched list of installed packages Successfully")
    current_app.logger.info(user_added_extns)
    current_app.logger.info("Deleting extensions..")
    for extn in user_added_extns:
        current_app.logger.info("Deleting extension " + extn["package-name"])
        output = TanzuUtil.delete_installed_package(extn["name"], extn["namespace"])
        if output[1] != 0:
            current_app.logger.warn("Deletion taking longer, Retrying....")
            retry_output = TanzuUtil.delete_installed_package(extn["name"], extn["namespace"])
            if retry_output[1] != 0:
                current_app.logger.info("Failed to delete extensions")
                return False, "Failed to delete extension- " + extn["name"]
        current_app.logger.info("Successfully deleted extension " + extn["name"])
    extensions_json = TanzuUtil.get_installed_package_json()
    if extensions_json[1] != 0:
        current_app.logger.error(extensions_json[0])
        return False, "Failed to get extension list to cluster"
    return True, "Deleted Extensions successfully"


def delete_supervisor_namespace(vCenter, session_id, namespace):
    header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": session_id}
    url1 = "https://" + vCenter + "/api/vcenter/namespaces/instances/" + namespace
    response_csrf = requests.request("DELETE", url1, headers=header, verify=False)
    if response_csrf.status_code != 204:
        return None, response_csrf.text

    current_app.logger.info("Checking Namespace Status")
    count = 0
    deleted = False
    time.sleep(20)
    url = "https://" + vCenter + "/api/vcenter/namespaces/instances/" + namespace
    response_csrf = requests.request("GET", url, headers=header, verify=False)
    if response_csrf.status_code != 204:
        if response_csrf.json()["messages"][0]["default_message"].__contains__("does not exist in this vCenter."):
            deleted = True
    if not deleted:
        current_app.logger.error("Supervisor Namespace delete Failed " + str(count * 20))
        return None, "Supervisor Namespace delete Failed"
    return "SUCCESS", "Supervisor Namespace deleted successfully"


def disableWCP(vCenter, cluster_id, session_id):
    header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": session_id}

    url1 = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + cluster_id + "?action=disable"
    response_csrf = requests.request("POST", url1, headers=header, verify=False)
    if response_csrf.status_code != 204:
        return None, response_csrf.text

    current_app.logger.info("Checking WCP Status")
    count = 0
    disabled = False
    while count < 90 and not disabled:
        url = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + cluster_id
        response_csrf = requests.request("GET", url, headers=header, verify=False)
        if response_csrf.status_code != 200:
            if response_csrf.json()["messages"][0]["default_message"].__contains__("does not have Workloads enabled"):
                disabled = True
                break
        else:
            try:
                if (
                    response_csrf.json()["config_status"] == "REMOVING"
                    or response_csrf.json()["config_status"] == "ERROR"
                ):
                    current_app.logger.info("Cluster config status " + response_csrf.json()["config_status"])
            except Exception:
                pass
        time.sleep(20)
        count = count + 1
        current_app.logger.info("Waited " + str(count * 20) + "s, retrying")
    if not disabled:
        current_app.logger.error("Cluster is still running " + str(count * 20))
        return None, "WCP Deactivate Failed"
    return "SUCCESS", "WCP is Deactivated successfully"
