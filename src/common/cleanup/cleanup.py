import logging
import os
from http import HTTPStatus

import requests
from flask import Blueprint, current_app, jsonify, request
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.cleanup.cleanup_constants import Cleanup, VCenter
from common.cleanup.cleanup_helper import (
    get_cluster_names,
    get_required_resource_folder_pool,
    getVcenterConfig,
    validateTKGsFile,
)
from common.cleanup.cleanup_operations import (
    cleanup_avi_vms,
    cleanup_content_libraries,
    cleanup_downloaded_ovas,
    cleanup_resource_pools,
    cluster_exists,
    delete_cluster,
    delete_config_yaml,
    delete_extensions,
    delete_folders,
    delete_kubernetes_templates,
    delete_mgmt_cluster,
    delete_supervisor_namespace,
    delete_tkgs_workload_cluster,
    delete_tmc_cluster,
    delete_vcf_components,
    delete_vmc_components,
    disableWCP,
    fetch_avi_vms,
    fetch_mgmt_workload_se_engines,
    fetch_resource_pools,
    get_avi_uuid,
    get_deployed_templates,
    get_vcenter_sessionID,
    getAllClusters_tkgs,
    getCluster,
    kubectl_configs_cleanup,
    list_network_segments,
    management_exists,
)
from common.common_utilities import envCheck, getClusterID, isEnvTkgs_ns, isEnvTkgs_wcp, isWcpEnabled
from common.lib.govc.govc_client import GOVClient
from common.login_auth.authentication import token_required
from common.operation.constants import ControllerLocation, Env, ResourcePoolAndFolderName, Type
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
from common.prechecks.list_reources import getAllNamespaces
from common.session.session_acquire import login
from common.util.common_utils import CommonUtils
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.request_api_util import RequestApiUtil
from common.util.saas_util import SaaSUtil

cleanup_env = Blueprint("cleanup_env", __name__, static_folder="cleanup")
logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
__author__ = ["Tasmiya", "Pooja Deshmukh"]


@cleanup_env.route("/api/tanzu/cleanup-env", methods=["POST"])
@token_required
def cleanup_environment(current_user):
    cleanup = request.headers["cleanup"]
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        message = f"Wrong env provided {env[0]}"
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    env = env[0]
    spec_json = request.get_json(force=True)
    spec_obj = CommonUtils.get_spec_obj(env)
    spec: spec_obj = spec_obj.parse_obj(spec_json)
    saas_util: SaaSUtil = SaaSUtil(env, spec)
    login()
    VC_reponse = getVcenterConfig(env, spec)
    if VC_reponse[1] != 200:
        return VC_reponse
    VC = VC_reponse[0]
    data_center = VC[VCenter.datacenter].replace(" ", "#remove_me#")
    govc_client = GOVClient(
        VC[VCenter.vCenter],
        VC[VCenter.user],
        VC[VCenter.PASSWORD],
        VC[VCenter.cluster],
        data_center,
        None,
        LocalCmdHelper(),
    )
    GOVClient.set_env_vars(govc_client)
    os.putenv("KUBECTL_VSPHERE_PASSWORD", VC[VCenter.PASSWORD])
    os.putenv("HOME", "/root")

    if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env):
        current_app.logger.info("Verifying provided json..")
        verifyJson = validateTKGsFile(env, cleanup)
        if verifyJson[1] != 200:
            return verifyJson
    if cleanup == Cleanup.ALL:
        if isEnvTkgs_wcp(env):
            tkgs_response = tkgs_cleanup(VC, saas_util=saas_util, spec=spec)
            if tkgs_response[1] != 200:
                message = "Cleanup failed - " + tkgs_response[0].json["msg"]
                current_app.logger.error(message)
                return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        elif env == Env.VSPHERE or env == Env.VMC or env == Env.VCF:
            tkg_response = tkgm_cleanup(env=env, VC=VC, saas_util=saas_util, spec=spec)
            if tkg_response[1] != 200:
                message = "Cleanup failed - " + tkg_response[0].json["msg"]
                current_app.logger.error(tkg_response)
                return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR

        current_app.logger.info("Clusters are deleted successfully. Performing other components cleanup")

        response = delete_common_comp(govc_client=govc_client, env=env, VC=VC, spec=spec)
        if response[1] != 200:
            message = "Cleanup failed - " + response[0].json["msg"]
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        message = "Cleanup for " + env + " is successful"
        current_app.logger.info(message)
        return RequestApiUtil.send_ok(message), HTTPStatus.OK
    elif cleanup == Cleanup.VCF:
        return vcf_cleanup(govc_client=govc_client, env=env, VC=VC, spec=spec)
    elif cleanup == Cleanup.VMC:
        return vmc_cleanup(govc_client=govc_client, env=env, VC=VC, spec=spec)
    elif cleanup == Cleanup.AVI:
        return avi_cleanup(govc_client=govc_client, env=env, VC=VC, spec=spec)
    elif cleanup == Cleanup.MGMT_CLUSTER:
        return mgmt_cluster_cleanup(govc_client=govc_client, env=env, VC=VC, saas_util=saas_util, spec=spec)
    elif cleanup == Cleanup.SHARED_CLUSTER:
        return shared_cluster_cleanup(govc_client=govc_client, env=env, VC=VC, saas_util=saas_util, spec=spec)
    elif cleanup == Cleanup.WORKLOAD_CLUSTER:
        return tkgm_workload_cluster_cleanup(govc_client=govc_client, env=env, VC=VC, saas_util=saas_util, spec=spec)
    elif cleanup == Cleanup.TKG_WORKLOAD_CLUSTER:
        return tkgs_workload_cleanup(env=env, VC=VC, saas_util=saas_util, spec=spec)
    elif cleanup == Cleanup.SUPERVISOR_NAMESPACE:
        return supervisor_namespace_cleanup(VC=VC, spec=spec)
    elif cleanup == Cleanup.DISABLE_WCP:
        return wcp_cleanup(VC=VC, spec=spec, saas_util=saas_util)
    elif cleanup == Cleanup.EXTENSION:
        return extensions_cleanup(env=env, VC=VC, spec=spec)


def vcf_cleanup(govc_client: GOVClient, env, VC, spec):
    current_app.logger.info("Checking if AVI controller running....")
    avi_vms = fetch_avi_vms(govc_client, env, VC[VCenter.datacenter], spec)[1]
    if len(avi_vms) != 0:
        message = "Found below running AVI controller, please delete it before deleting nsx-t configurations"
        current_app.logger.error(message)
        current_app.logger.warn(avi_vms)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    vcf_res = delete_vcf_components(env, spec)
    if not vcf_res[0]:
        current_app.logger.error(vcf_res[1])
        return RequestApiUtil.send_error(vcf_res[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    return RequestApiUtil.send_ok(vcf_res[1]), HTTPStatus.OK


def vmc_cleanup(govc_client: GOVClient, env, VC, spec):
    current_app.logger.info("Checking if AVI controller running....")
    avi_vms = fetch_avi_vms(govc_client, env, VC[VCenter.datacenter], spec)[1]
    if len(avi_vms) != 0:
        message = "Found below running AVI controller, please delete it before deleting vmc configurations"
        current_app.logger.error(message)
        current_app.logger.warn(avi_vms)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    vmc_res = delete_vmc_components(env, spec)
    if not vmc_res[0]:
        current_app.logger.error(vmc_res[1])
        return RequestApiUtil.send_error(vmc_res[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    return RequestApiUtil.send_ok(vmc_res[1]), HTTPStatus.OK


def avi_cleanup(govc_client: GOVClient, env, VC, spec):
    """
    Method to Clean AVI configurations for TKGs and TKGm
    """
    if isEnvTkgs_wcp(env):
        try:
            cluster_id = getClusterID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.cluster])
            if cluster_id[1] != 200:
                current_app.logger.error(cluster_id[0].json["msg"])
                return RequestApiUtil.send_error(cluster_id[0].json["msg"]), HTTPStatus.INTERNAL_SERVER_ERROR
            cluster_id = cluster_id[0]
            enabled = getWCPStatus(cluster_id, VC)
            if enabled[0]:
                message = "Failed to delete avi, WCP is enabled,please try deleting WCP first." + enabled[1]
                current_app.logger.error(message)
                return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        except Exception:
            current_app.logger.info("WCP is not enabled")
    else:
        if management_exists(VC[VCenter.management_cluster]):
            message = "Failed to delete AVI, Management cluster exists, try deleting management cluster first."
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    avi_se_list = fetch_avi_vms(govc_client, env, VC[VCenter.datacenter], spec)[1]
    current_app.logger.info("Fetched Avi se list:")
    current_app.logger.info(avi_se_list)
    if isEnvTkgs_wcp(env):
        se_engine = fetch_mgmt_workload_se_engines(govc_client, env, VC[VCenter.datacenter], spec)
        if not se_engine[0]:
            message = "Failed to fetch AVI Service Engine list"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        avi_se_list.extend(se_engine[1])
    avi_cleanup_status = cleanup_avi_vms(govc_client, env, VC[VCenter.datacenter], avi_se_list)
    if not avi_cleanup_status[0]:
        current_app.logger.error(avi_cleanup_status[1])
        return RequestApiUtil.send_error(avi_cleanup_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info(avi_cleanup_status[1])
    resource_pool = get_required_resource_folder_pool(env)
    delete_pool = resource_pool["delete_pool"][Type.AVI]
    folders = resource_pool["folders"][Type.AVI]
    current_app.logger.info("Deleting Avi resource pools")
    response = cleanup_resource_pools(
        govc_client, env, VC[VCenter.datacenter], VC[VCenter.cluster], VC[VCenter.parent_rp], [delete_pool]
    )
    current_app.logger.info(response[1])
    if not response[0]:
        message = response[1]
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Deleting avi folders")
    if not delete_folders(env, VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], [folders]):
        message = "Failed to delete folders which were created by SIVT"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    delete_lib = []
    delete_lib.append(ControllerLocation.CONTROLLER_CONTENT_LIBRARY)
    library_response = cleanup_content_libraries(delete_lib)
    if not library_response[0]:
        current_app.logger.error(library_response[1])
        return RequestApiUtil.send_error(library_response[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    delete_files = [
        ControllerLocation.CONTENT_LIBRARY_OVA_NAME + ".ova",
    ]
    cleanup_sivt = cleanup_downloaded_ovas(delete_files)
    if not cleanup_sivt[0]:
        current_app.logger.error(cleanup_sivt[1])
        return RequestApiUtil.send_error(cleanup_sivt[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    message = "Cleanup for AVI is successful"
    current_app.logger.info(message)
    return RequestApiUtil.send_ok(message), HTTPStatus.OK


def mgmt_cluster_cleanup(govc_client: GOVClient, env, VC, saas_util, spec):
    """
    Method to delete TKGm Management Cluster
    """
    current_app.logger.info("Cleanup: Deleting Management Cluster")
    uuid = get_avi_uuid(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD])
    workload_cluster = VC[VCenter.workload_cluster]
    shared_cluster = VC[VCenter.shared_cluster]
    mgmt_cluster = VC[VCenter.management_cluster]
    delete_files = [
        "arcas-photon-kube-v*.ova",
        "arcas-ubuntu-kube-v*.ova",
    ]
    resource_pool = get_required_resource_folder_pool(env)
    delete_pool = resource_pool["delete_pool"][Type.MANAGEMENT]
    folders = resource_pool["folders"][Type.MANAGEMENT]

    current_app.logger.info("Checking if management cluster exists")
    if management_exists(mgmt_cluster):
        current_app.logger.info("Checking if any workload cluster is present")
        if getCluster(workload_cluster) or getCluster(shared_cluster):
            message = (
                "There are existing workload clusters running,Please delete those before deleting management cluster"
            )
            current_app.logger.warn(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        if delete_mgmt_cluster(mgmt_cluster):
            current_app.logger.info("Management cluster " + mgmt_cluster + " - deleted successfully")
        else:
            message = "Failed to delete management cluster - " + mgmt_cluster
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        current_app.logger.info("Management cluster " + mgmt_cluster + " is not present in environment")
    kubectl_configs_status = kubectl_configs_cleanup(env, [mgmt_cluster])
    if not kubectl_configs_status[0]:
        message = kubectl_configs_status[1]
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    if saas_util.check_tmc_enabled():
        current_app.logger.info("Performing TMC cleanup")
        if not delete_tmc_cluster([mgmt_cluster], True, saas_util):
            current_app.logger.warn("Failed to delete management clusters from TMC")
            current_app.logger.warn("Try deleting it using :'tmc cluster delete <clusterName>' command")
    else:
        current_app.logger.info("Workload cluster " + mgmt_cluster + " is not available in environment")
    current_app.logger.info("Fetching list of Service engines")
    se_list_res = fetch_mgmt_workload_se_engines(govc_client, env, VC[VCenter.datacenter], spec, Type.MANAGEMENT)
    if not se_list_res[0]:
        message = "Failed to fetch management SE list"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    se_list = se_list_res[1]
    avi_cleanup_status = cleanup_avi_vms(govc_client, env, VC[VCenter.datacenter], se_list)
    if not avi_cleanup_status[0]:
        current_app.logger.error(avi_cleanup_status[1])
        return RequestApiUtil.send_error(avi_cleanup_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info(avi_cleanup_status[1])
    response = cleanup_resource_pools(
        govc_client, env, VC[VCenter.datacenter], VC[VCenter.cluster], VC[VCenter.parent_rp], [delete_pool]
    )
    if not response[0]:
        current_app.logger.error(response[1])
        return RequestApiUtil.send_error(response[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    if not delete_folders(env, VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], [folders]):
        message = "Failed to delete folders which were created by SIVT"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    cleanup_sivt = cleanup_downloaded_ovas(delete_files)
    if not cleanup_sivt[0]:
        current_app.logger.warn(cleanup_sivt[1])
        return RequestApiUtil.send_error(cleanup_sivt[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    if env == Env.VMC or env == Env.VCF or env == Env.VSPHERE:
        if not delete_kubernetes_templates(
            govc_client, VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.datacenter], uuid
        ):
            message = "Failed to delete Kubernetes templates"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        if not delete_config_yaml():
            message = "Failed to delete config.yaml files /root/.config/tanzu/config.yaml \
                and /root/.config/tanzu/tkg/config.yaml"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    message = "Cleanup for Management Cluster " + mgmt_cluster + " is successful"
    current_app.logger.info(message)
    return RequestApiUtil.send_ok(message), HTTPStatus.OK


def extensions_cleanup(env, VC, spec):
    """
    Method to delete extensions from deployed cluster in TKGm and TKGs
    """
    endpoint_ip = VC[VCenter.vCenter]
    extn_clusters = spec.tanzuExtensions.tkgClustersName
    if isEnvTkgs_ns(env):
        cluster_ns = spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereNamespaceName
        switch_context = KubectlUtil.SWITCH_CONTEXT.format(cluster_ip=cluster_ns)
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if context_output[1] != 0:
            current_app.logger.error(context_output[0])
            return None, "Failed to login to cluster context - " + cluster_ns
        if not cluster_exists(env, extn_clusters):
            message = extn_clusters + " Cluster does not exist, extensions deleted successfully ..."
            current_app.logger.info(message)
            return RequestApiUtil.send_ok(message), HTTPStatus.OK
        cluster_id = getClusterID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.cluster])
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[1])
            return RequestApiUtil.send_error(cluster_id[1]), HTTPStatus.INTERNAL_SERVER_ERROR
        cluster_id = cluster_id[0]
        wcp_status = isWcpEnabled(cluster_id)
        if wcp_status[0]:
            endpoint_ip = wcp_status[1]["api_server_cluster_endpoint"]
        else:
            current_app.logger.error(wcp_status[1])
            return RequestApiUtil.send_error(wcp_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        if not getCluster(extn_clusters):
            message = extn_clusters + "Cluster does not exists, hence skipping deletion ..."
            current_app.logger.info(message)
            return RequestApiUtil.send_ok(message), HTTPStatus.OK
        current_app.logger.info("Switching to " + extn_clusters + " context")
        switch_context = KubectlUtil.SET_KUBECTL_CONTEXT.format(cluster=extn_clusters)
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if context_output[1] != 0:
            current_app.logger.error(context_output[0])
            return None, "Failed to login to " + extn_clusters + " context - " + cluster_ns
    if delete_extensions(env, extn_clusters, VC[VCenter.user], endpoint_ip)[0]:
        message = "Cleanup for Extensions is successful"
        current_app.logger.info(message)
        return RequestApiUtil.send_ok(message), HTTPStatus.OK
    message = "Cleanup for Extensions Failed"
    current_app.logger.error(message)
    return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR


def supervisor_namespace_cleanup(VC, spec):
    """
    Method to delete supervisor namespaces in TKGs
    """
    try:
        current_app.logger.info("Cleanup: Deleting Supervisor namespace ...")
        current_app.logger.info("Fetching Vcenter SessionID")
        session_reponse = get_vcenter_sessionID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD])
        if session_reponse[1] != 200:
            return session_reponse
        current_app.logger.info("fetched sessionID")
        vc_session = session_reponse[0].json["vc_session"]
        cluster_id = getClusterID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.cluster])
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[1])
            return RequestApiUtil.send_error(cluster_id[1]), HTTPStatus.INTERNAL_SERVER_ERROR
        cluster_id = cluster_id[0]
        enabled = getWCPStatus(cluster_id, VC)
        if enabled[0]:
            current_app.logger.info("WCP is enabled and it's status is " + enabled[1])
            if enabled[1] == "RUNNING":
                current_app.logger.info("Fetching list of namespaces")
                response = getAllNamespaces()
                if response[1] == 200:
                    namespaces = response[0].json["NAMESPACES_LIST"]
                clusters_response = getAllClusters_tkgs(
                    VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], namespaces, VC[VCenter.cluster]
                )
                if not (clusters_response[0] is None):
                    workload_clusters = clusters_response[0]
        if len(workload_clusters) != 0:
            message = "There is existing workload cluster present, please delete it before deleting namespace"
            current_app.logger.info(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        if len(namespaces) != 0:
            for ns in namespaces:
                current_app.logger.info("Deleting Namespace " + ns)
                delete_supervisor_res = delete_supervisor_namespace(VC[VCenter.vCenter], vc_session, ns)
                if delete_supervisor_res[0] is None:
                    current_app.logger.error(delete_supervisor_res[1])
                    return RequestApiUtil.send_error(delete_supervisor_res[1]), HTTPStatus.INTERNAL_SERVER_ERROR
        message = "Supervisor Namespace deleted successfully"
        current_app.logger.info(message)
        return RequestApiUtil.send_ok(message), HTTPStatus.OK
    except Exception as e:
        message = "Exception occured while deleting supervisor namespace" + str(e)
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR


def shared_cluster_cleanup(govc_client: GOVClient, env, VC, saas_util, spec):
    """
    Method to delete TKGm Shared cluster
    """
    current_app.logger.info("Cleanup: Deleting Shared Service cluster...")
    return cluster_cleanup(Type.SHARED, govc_client, env, VC, saas_util, spec)


def tkgm_workload_cluster_cleanup(govc_client: GOVClient, env, VC, saas_util, spec):
    """
    Method to delete TKGm Workload cluster
    """
    response = cluster_cleanup(Type.WORKLOAD, govc_client, env, VC, saas_util, spec)
    if response[1] != 200:
        message = "Failed to delete workload cluster"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Fetching list of Service engines")
    se_list_res = fetch_mgmt_workload_se_engines(govc_client, env, VC[VCenter.datacenter], spec, Type.WORKLOAD)
    if not se_list_res[0]:
        message = "Failed to fetch Workload Service engine list"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    se_list = se_list_res[1]
    avi_cleanup_status = cleanup_avi_vms(govc_client, env, VC[VCenter.datacenter], se_list)
    if not avi_cleanup_status[0]:
        current_app.logger.error(avi_cleanup_status[1])
        return RequestApiUtil.send_error(avi_cleanup_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        return response


def cluster_cleanup(cluster_type, govc_client, env, VC, saas_util, spec):
    """
    Common Method to delete TKGm cluster and its dependencies, user for shared and workload deletion
    """
    clusterList = get_cluster_names(env, spec)
    cluster = clusterList[cluster_type]
    resource_pool = get_required_resource_folder_pool(env)
    delete_pool = resource_pool["delete_pool"][cluster_type]
    folders = resource_pool["folders"][cluster_type]
    current_app.logger.info("Deleting " + cluster + " cluster")
    if getCluster(cluster):
        if delete_cluster(cluster):
            current_app.logger.info(cluster + " cluster deleted successfully")
            kubectl_configs_status = kubectl_configs_cleanup(env, [cluster])
            if not kubectl_configs_status[0]:
                current_app.logger.error(kubectl_configs_status[1])
                return RequestApiUtil.send_error(kubectl_configs_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            message = "Failed to delete cluster - " + cluster
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Checking if TMC is enabled")
    if saas_util.check_tmc_enabled():
        current_app.logger.info("Performing TMC cleanup")
        if not delete_tmc_cluster([cluster], False, saas_util):
            current_app.logger.warn("Failed to delete workload clusters from TMC")
            current_app.logger.warn("Try deleting it using :'tmc cluster delete <clusterName>' command")

    current_app.logger.info("Deleting resource pools")
    response = cleanup_resource_pools(
        govc_client, env, VC[VCenter.datacenter], VC[VCenter.cluster], VC[VCenter.parent_rp], [delete_pool]
    )
    if not response[0]:
        current_app.logger.error(response[1])
        return RequestApiUtil.send_error(response[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Deleting folders")
    if not delete_folders(env, VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], [folders]):
        message = "Failed to delete folders which were created by SIVT"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(response[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    message = cluster_type + " cluster cleanup completed successfully"
    current_app.logger.info(message)
    return RequestApiUtil.send_ok(message), HTTPStatus.OK


def tkgs_workload_cleanup(env, VC, saas_util, spec):
    try:
        """
        Method to delete TKGs Workload cluster
        """
        namespaces = []
        workload_cluster_name = (
            spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterName
        )
        cluster_kind = (
            spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterKind
        )
        cluster_id = getClusterID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.cluster])
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[1])
            return RequestApiUtil.send_error(cluster_id[1]), HTTPStatus.INTERNAL_SERVER_ERROR
        cluster_id = cluster_id[0]
        enabled = getWCPStatus(cluster_id, VC)
        if enabled[0]:
            current_app.logger.info("WCP is enabled and it's status is " + enabled[1])
            if enabled[1] == "RUNNING":
                current_app.logger.info("Fetching list of clusters deployed")
                response = getAllNamespaces()
                if response[1] == 200:
                    namespaces = response[0].json["NAMESPACES_LIST"]
                clusters_response = getAllClusters_tkgs(
                    VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], namespaces, VC[VCenter.cluster]
                )
                if not (clusters_response[0] is None):
                    workload_clusters = clusters_response[0]
                current_app.logger.info("List of deployed workload clusters")
                current_app.logger.info(workload_clusters)
            else:
                current_app.logger.error(
                    "Unable to fetch list of namespaces and workload clusters as " "WCP status is " + enabled[1]
                )
        else:
            message = "WCP is already deactivated on cluster - " + VC[VCenter.cluster]
            current_app.logger.info(message)
            return RequestApiUtil.send_ok(message), HTTPStatus.OK
        if len(namespaces) == 0:
            message = "No namespace found, Workload clusters deleted successfully"
            current_app.logger.info(message)
            return RequestApiUtil.send_ok(message), HTTPStatus.OK
        if len(workload_clusters) != 0:
            wcp_status = isWcpEnabled(cluster_id)
            if wcp_status[0]:
                endpoint_ip = wcp_status[1]["api_server_cluster_endpoint"]
            else:
                current_app.logger.error(wcp_status[1])
                return RequestApiUtil.send_error(wcp_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
            for ns in namespaces:
                delete_workload_res = delete_tkgs_workload_cluster(env, ns, VC[VCenter.user], endpoint_ip, cluster_kind)
                if not delete_workload_res[0]:
                    current_app.logger.error(delete_workload_res[1])
                    return RequestApiUtil.send_error(delete_workload_res[1]), HTTPStatus.INTERNAL_SERVER_ERROR
        if saas_util.check_tmc_enabled:
            current_app.logger.info("Performing TMC Cleanup")
            if isEnvTkgs_wcp(Env.VSPHERE):
                if not delete_tmc_cluster(workload_cluster_name, False, saas_util):
                    current_app.logger.warn("Failed to delete workload clusters from TMC")
                    current_app.logger.warn("Try deleting it using :'tmc cluster delete <clusterName>' command")
        message = "Workload clusters deleted successfully"
        current_app.logger.info(message)
        return RequestApiUtil.send_ok(message), HTTPStatus.OK
    except Exception as e:
        message = "Exception occured while deleting Workload cluster"
        current_app.logger.error(str(e))
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR


def wcp_cleanup(VC, spec, saas_util):
    try:
        """
        Method to disable wcp in TKGs
        """
        current_app.logger.warn(
            "Please note that disabling wcp will delete all existing namespaces and workload clusters"
        )
        current_app.logger.info("Connecting to vcenter")
        session_reponse = get_vcenter_sessionID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD])
        if session_reponse[1] != 200:
            return session_reponse
        vc_session = session_reponse[0].json["vc_session"]
        current_app.logger.info("successfully connected to vcenter")
        id = getClusterID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.cluster])
        if id[1] != 200:
            current_app.logger.error(id[1])
            return RequestApiUtil.send_error(id[0]), HTTPStatus.INTERNAL_SERVER_ERROR

        cluster_id = id[0]
        enabled = getWCPStatus(cluster_id, VC)
        if enabled[0]:
            current_app.logger.info("Proceeding to deactivate WCP on cluster - " + VC[VCenter.cluster])
            disable = disableWCP(VC[VCenter.vCenter], cluster_id, vc_session)
            if disable[0] is None:
                current_app.logger.error(disable[1])
                return RequestApiUtil.send_error(disable[1]), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("WCP is already deactivated on cluster - " + VC[VCenter.cluster])
        current_app.logger.info("Deleting Content Library")
        delete_lib = []
        delete_lib.append(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY)
        library_response = cleanup_content_libraries(delete_lib)
        if not library_response[0]:
            d = {"responseType": "ERROR", "msg": library_response[1], "STATUS_CODE": 500}
            return jsonify(d), 500
        current_app.logger.info(library_response[1])
        if saas_util.check_tmc_enabled:
            current_app.logger.info("Performing TMC Cleanup")
            if isEnvTkgs_wcp(Env.VSPHERE):
                if not delete_tmc_cluster(
                    [spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName], True, saas_util
                ):
                    current_app.logger.warn("Failed to delete Management clusters from TMC")
                    current_app.logger.warn(
                        "Try deleting it using :'tmc managmentcluster delete <clusterName>' command"
                    )
        message = "WCP deactivated successfully"
        current_app.logger.info(message)
        return RequestApiUtil.send_ok(message), HTTPStatus.OK
    except Exception as e:
        message = "Exception occured while deactivating wcp"
        current_app.logger.error(str(e))
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR


def tkgs_cleanup(VC, saas_util, spec):
    try:
        """
        Method to Clean tkgs deployment
        """
        session_reponse = get_vcenter_sessionID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD])
        if session_reponse[1] != 200:
            return session_reponse
        current_app.logger.info("fetched sessionID")
        vc_session = session_reponse[0].json["vc_session"]

        id = getClusterID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.cluster])
        if id[1] != 200:
            return RequestApiUtil.send_error(id[0]), HTTPStatus.INTERNAL_SERVER_ERROR

        cluster_id = id[0]

        namespaces = []
        workload_clusters = []
        delete = True
        if delete:
            enabled = getWCPStatus(cluster_id, VC)
            if enabled[0]:
                current_app.logger.info("WCP is enabled and it's status is " + enabled[1])
                current_app.logger.info("Proceeding to deactivate WCP on cluster - " + VC[VCenter.cluster])
                if enabled[1] == "RUNNING":
                    current_app.logger.info("Fetching list of namespaces and clusters deployed")
                    response = getAllNamespaces()
                    if response[1] == 200:
                        namespaces = response[0].json["NAMESPACES_LIST"]
                    clusters_response = getAllClusters_tkgs(
                        VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], namespaces, VC[VCenter.cluster]
                    )
                    if not (clusters_response[0] is None):
                        workload_clusters = clusters_response[0]
                    current_app.logger.info("List of deployed workload clusters")
                    current_app.logger.info(workload_clusters)
                else:
                    current_app.logger.error(
                        "Unable to fetch list of namespaces and workload clusters as " "WCP status is " + enabled[1]
                    )

                disable = disableWCP(VC[VCenter.vCenter], cluster_id, vc_session)
                if disable[0] is None:
                    current_app.logger.error(disable[1])
                    return RequestApiUtil.send_error(disable[1]), HTTPStatus.INTERNAL_SERVER_ERROR
            else:
                current_app.logger.info("WCP is already deactivated on cluster - " + VC[VCenter.cluster])

        kubectl_configs_status = kubectl_configs_cleanup(Env.VSPHERE, workload_clusters + namespaces)
        if not kubectl_configs_status[0]:
            current_app.logger.error(kubectl_configs_status[1])
            return RequestApiUtil.send_error(kubectl_configs_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
        current_app.logger.info(kubectl_configs_status[1])

        if saas_util.check_tmc_enabled():
            current_app.logger.info("Performing TMC Cleanup")
            if isEnvTkgs_wcp(Env.VSPHERE):
                if not delete_tmc_cluster(workload_clusters, False, saas_util):
                    current_app.logger.warn("Failed to delete workload clusters from TMC")
                    current_app.logger.warn("Try deleting it using :'tmc cluster delete <clusterName>' command")
                if not delete_tmc_cluster(
                    [spec.envSpec.saasEndpoints.tmcDetails.tmcSupervisorClusterName], True, saas_util
                ):
                    current_app.logger.warn("Failed to delete Management clusters from TMC")
                current_app.logger.warn("Try deleting it using :'tmc managmentcluster delete <clusterName>' command")
        message = "TKGs components deleted successfully"
        current_app.logger.info(message)
        return RequestApiUtil.send_ok(message), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(str(e))
        message = "Exception occured while performing cleanup"
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR


def getWCPStatus(cluster_id, VC):
    """
    :param cluster_id:
    :return:
     False: If WCP is not enabled
    True: if WCP is enabled and any state, not necessarily running status
    """
    if not (VC[VCenter.vCenter] or VC[VCenter.user] or VC[VCenter.PASSWORD]):
        return False, "Failed to fetch VC details"

    session_reponse = get_vcenter_sessionID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD])
    if session_reponse[1] != 200:
        return session_reponse
    current_app.logger.info("fetched sessionID")
    vc_session = session_reponse[0].json["vc_session"]

    header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": vc_session}
    url = "https://" + VC[VCenter.vCenter] + "/api/vcenter/namespace-management/clusters/" + cluster_id
    response_csrf = requests.request("GET", url, headers=header, verify=False)
    if response_csrf.status_code != 200:
        if response_csrf.status_code == 400:
            if (
                response_csrf.json()["messages"][0]["default_message"]
                == "Cluster with identifier " + cluster_id + " does "
                "not have Workloads enabled."
            ):
                return False, None
    else:
        return True, response_csrf.json()["config_status"]


def tkgm_cleanup(env, VC, saas_util, spec):
    """
    Method to clean TKGm deployment
    """

    worload_clusters = [VC[VCenter.shared_cluster], VC[VCenter.workload_cluster]]
    if management_exists(VC[VCenter.management_cluster]):
        for cluster in worload_clusters:
            current_app.logger.info("Deleting " + cluster + " cluster")
            if getCluster(cluster):
                if delete_cluster(cluster):
                    current_app.logger.info("Cluster " + cluster + " deleted successfully")
                else:
                    message = "Failed to delete cluster - " + cluster
                    current_app.logger.error(message)
                    return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
            else:
                current_app.logger.info("Workload cluster " + cluster + " is not available in environment")

        current_app.logger.info("Deleting management cluster...")
        if delete_mgmt_cluster(VC[VCenter.management_cluster]):
            current_app.logger.info("Management cluster " + VC[VCenter.management_cluster] + " - deleted successfully")
        else:
            message = "Failed to delete management cluster - " + VC[VCenter.management_cluster]
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        current_app.logger.info(
            "Management cluster " + VC[VCenter.management_cluster] + " is not present in environment"
        )

    kubectl_configs_status = kubectl_configs_cleanup(
        env, [VC[VCenter.management_cluster], VC[VCenter.workload_cluster], VC[VCenter.shared_cluster]]
    )
    if not kubectl_configs_status[0]:
        current_app.logger.error(kubectl_configs_status[1])
        return RequestApiUtil.send_error(kubectl_configs_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info(kubectl_configs_status[1])

    if saas_util.check_tmc_enabled():
        current_app.logger.info("Performing TMC cleanup")
        if not delete_tmc_cluster([VC[VCenter.workload_cluster], VC[VCenter.shared_cluster]], False, saas_util):
            current_app.logger.warn("Failed to delete workload clusters from TMC")
            current_app.logger.warn("Try deleting it using :'tmc cluster delete <clusterName>' command")
        if not delete_tmc_cluster([VC[VCenter.management_cluster]], True, saas_util):
            current_app.logger.warn(
                "Failed to delete management cluster " + VC[VCenter.management_cluster] + " from TMC"
            )
            current_app.logger.warn("Try deleting it using :'tmc managementcluster delete <clusterName>' command")

    message = "TKG Clusters and Nodes deleted successfully"
    current_app.logger.info(message)
    return RequestApiUtil.send_ok(message), HTTPStatus.OK


def delete_common_comp(govc_client: GOVClient, env, VC, spec):
    """
    Method to delete common deployment components of TKGm and TKGs
    """
    se_list = []
    delete_files = [
        ControllerLocation.CONTENT_LIBRARY_OVA_NAME + ".ova",
        "arcas-photon-kube-v*.ova",
        "arcas-ubuntu-kube-v*.ova",
    ]
    uuid = get_avi_uuid(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD])
    current_app.logger.info("Fetching AVI controller")
    avi_list = fetch_avi_vms(govc_client, env, VC[VCenter.datacenter], spec)
    se_list.extend(avi_list[1])
    current_app.logger.info("Fetching list of Service engines")
    workload_se = fetch_mgmt_workload_se_engines(govc_client, env, VC[VCenter.datacenter], spec)
    if not workload_se[0]:
        message = "Failed to fetch Workload Service Engine list"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    se_list.extend(workload_se[1])
    avi_cleanup_status = cleanup_avi_vms(govc_client, env, VC[VCenter.datacenter], se_list)
    if not avi_cleanup_status[0]:
        current_app.logger.error(avi_cleanup_status[1])
        return RequestApiUtil.send_error(avi_cleanup_status[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info(avi_cleanup_status[1])

    delete_pool = []
    if env == Env.VSPHERE or env == Env.VCF:
        delete_pool.append(ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE)
        if not isEnvTkgs_ns(env) or not isEnvTkgs_wcp(env):
            delete_pool.append(ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE)
            delete_pool.append(ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER)
            delete_pool.append(ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE)
    elif env == Env.VMC:
        delete_pool.append(ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL)
        delete_pool.append(ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME)
        delete_pool.append(ResourcePoolAndFolderName.TKG_Mgmt_RP)
        delete_pool.append(ResourcePoolAndFolderName.AVI_Components_FOLDER)
    else:
        message = "Wrong environment provided for Resource Pool deletion"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR

    response = cleanup_resource_pools(
        govc_client, env, VC[VCenter.datacenter], VC[VCenter.cluster], VC[VCenter.parent_rp], delete_pool
    )
    if not response[0]:
        return RequestApiUtil.send_error(response[1]), HTTPStatus.INTERNAL_SERVER_ERROR

    current_app.logger.info(response[1])
    delete_lib = []
    if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
        delete_lib.append(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY)

    delete_lib.append(ControllerLocation.CONTROLLER_CONTENT_LIBRARY)
    library_response = cleanup_content_libraries(delete_lib)
    if not library_response[0]:
        return RequestApiUtil.send_error(library_response[1]), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info(library_response[1])
    cleanup_sivt = cleanup_downloaded_ovas(delete_files)
    if not cleanup_sivt[0]:
        current_app.logger.info(cleanup_sivt[1])
        return RequestApiUtil.send_error(cleanup_sivt[1]), HTTPStatus.INTERNAL_SERVER_ERROR

    current_app.logger.info(cleanup_sivt[1])
    folders = []
    if env == Env.VSPHERE or env == Env.VCF:
        folders.append(ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE)
        if not isEnvTkgs_ns(env) or not isEnvTkgs_wcp(env):
            folders.append(ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE)
            folders.append(ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE)
            folders.append(ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)
    elif env == Env.VMC:
        folders.append(ResourcePoolAndFolderName.WORKLOAD_FOLDER)
        folders.append(ResourcePoolAndFolderName.SHARED_FOLDER_NAME)
        folders.append(ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder)
        folders.append(ResourcePoolAndFolderName.AVI_Components_FOLDER)

    if not delete_folders(env, VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], folders):
        message = "Failed to delete folders which were created by SIVT"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR

    if env == Env.VMC or env == Env.VCF or env == Env.VSPHERE:
        if not delete_kubernetes_templates(
            govc_client, VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.datacenter], uuid
        ):
            message = "Failed to delete Kubernetes templates"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        if not delete_config_yaml():
            message = "Failed to delete config.yaml files /root/.config/tanzu/config.yaml \
                and /root/.config/tanzu/tkg/config.yaml"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR

    current_app.logger.info("Performing NSX-T components cleanup")
    if env == Env.VCF:
        delete_vcf_res = delete_vcf_components(env, spec)
        if not delete_vcf_res[0]:
            current_app.logger.error(delete_vcf_res[1])
            return RequestApiUtil.send_error(delete_vcf_res[1]), HTTPStatus.INTERNAL_SERVER_ERROR

    elif env == Env.VMC:
        delete_vmc_res = delete_vmc_components(env, spec)
        if not delete_vmc_res[0]:
            current_app.logger.error(delete_vmc_res[1])
            return RequestApiUtil.send_error(delete_vmc_res[1]), HTTPStatus.INTERNAL_SERVER_ERROR

    message = "Common Components deleted successfully"
    current_app.logger.info(message)
    return RequestApiUtil.send_ok(message), HTTPStatus.OK


@cleanup_env.route("/api/tanzu/cleanup-prompt", methods=["POST"])
@token_required
def cleanup_resources_list(current_user):
    env = envCheck()
    if env[1] != 200:
        message = "Wrong env provided " + env[0]
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    env = env[0]
    spec_json = request.get_json(force=True)
    spec_obj = CommonUtils.get_spec_obj(env)
    spec: spec_obj = spec_obj.parse_obj(spec_json)
    login()
    os.putenv("HOME", "/root")
    VC_reponse = getVcenterConfig(env, spec)
    if VC_reponse[1] != 200:
        return VC_reponse
    VC = VC_reponse[0]
    data_center = VC[VCenter.datacenter].replace(" ", "#remove_me#")
    govc_client = GOVClient(
        VC[VCenter.vCenter],
        VC[VCenter.user],
        VC[VCenter.PASSWORD],
        VC[VCenter.cluster],
        data_center,
        None,
        LocalCmdHelper(),
    )
    GOVClient.set_env_vars(govc_client)
    management_cluster_list = []
    work_clusters_list = []
    content_libraries = []
    kubernetes_templates = []
    avi_vms = []
    resource_pools = []
    namespaces = []
    network_segments = []
    supervisor_cluster = ""
    delete_pool = []
    if not isEnvTkgs_wcp(env) and not isEnvTkgs_ns(env):
        if env == Env.VCF or env == Env.VMC:
            network_segments = list_network_segments(env, spec)

        if management_exists(VC[VCenter.management_cluster]):
            management_cluster_list.append(VC[VCenter.management_cluster])

        if getCluster(VC[VCenter.workload_cluster]):
            work_clusters_list.append(VC[VCenter.workload_cluster])
        if getCluster(VC["shared_cluster"]):
            work_clusters_list.append(VC[VCenter.shared_cluster])

        kubernetes_templates = get_deployed_templates(
            VC[VCenter.vCenter],
            VC[VCenter.user],
            VC[VCenter.PASSWORD],
            get_avi_uuid(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD]),
        )[1]

    else:
        id = getClusterID(VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], VC[VCenter.cluster])
        if id[1] != 200:
            return RequestApiUtil.send_error(id[0]), HTTPStatus.INTERNAL_SERVER_ERROR
        cluster_id = id[0]

        if getWCPStatus(cluster_id, VC)[0]:
            supervisor_cluster = (
                "Workload Control Plane (WCP) will be deactivated on cluster: [ " + VC[VCenter.cluster] + " ]"
            )
        else:
            supervisor_cluster = (
                "Workload Control Plane (WCP) is not enabled on cluster: [ " + VC[VCenter.cluster] + " ]"
            )

        response = getAllNamespaces()
        if response[1] == 200:
            namespaces = response[0].json["NAMESPACES_LIST"]
        output = getAllClusters_tkgs(
            VC[VCenter.vCenter], VC[VCenter.user], VC[VCenter.PASSWORD], namespaces, VC[VCenter.cluster]
        )
        if not (output[0] is None):
            work_clusters_list = output[0]

    for c_lib in govc_client.get_content_libraries():
        if str(c_lib) == "/" + ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY:
            content_libraries.append(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY)
        elif str(c_lib) == "/" + ControllerLocation.CONTROLLER_CONTENT_LIBRARY:
            content_libraries.append(ControllerLocation.CONTROLLER_CONTENT_LIBRARY)

    current_app.logger.info("Fetching AVI controller")
    vm_list = fetch_avi_vms(govc_client, env, VC[VCenter.datacenter], spec)
    if vm_list[0]:
        avi_vms = vm_list[1]
    current_app.logger.info("Fetching list of Service engines")
    se_list = fetch_mgmt_workload_se_engines(govc_client, env, VC[VCenter.datacenter], spec)
    if se_list[0]:
        avi_vms.append(se_list[1])
    if env == Env.VSPHERE or env == Env.VCF:
        delete_pool.append(ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE)
        if not isEnvTkgs_ns(env) or not isEnvTkgs_wcp(env):
            delete_pool.append(ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE)
            delete_pool.append(ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER)
            delete_pool.append(ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE)
    elif env == Env.VMC:
        delete_pool.append(ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL)
        delete_pool.append(ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME)
        delete_pool.append(ResourcePoolAndFolderName.TKG_Mgmt_RP)
        delete_pool.append(ResourcePoolAndFolderName.AVI_Components_FOLDER)
    else:
        message = "Wrong environment provided for Resource Pool deletion"
        current_app.logger.error(message)
        return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    response = fetch_resource_pools(
        env, VC[VCenter.datacenter], VC[VCenter.cluster], VC[VCenter.parent_rp], delete_pool
    )
    if response[0]:
        resource_pools = response[1]
    else:
        current_app.logger.warn("Failed to fetch resource pools")

    d = {
        "responseType": "SUCCESS",
        "msg": "got the details",
        "MANAGEMENT_CLUSTERS": management_cluster_list,
        "WORKLOAD_CLUSTERS": work_clusters_list,
        "CONTENT_LIBRARY": content_libraries,
        "KUBERNETES_TEMPLATES": kubernetes_templates,
        "AVI_VMS": avi_vms,
        "RESOURCE_POOLS": resource_pools,
        "NETWORK_SEGMENTS": network_segments,
        "NAMESPACES": namespaces,
        "PORT_GROUPS": network_segments,
        "SUPERVISOR_CLUSTER": supervisor_cluster,
        "STATUS_CODE": 200,
    }
    return jsonify(d), 200
