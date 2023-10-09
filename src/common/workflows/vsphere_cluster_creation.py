import logging
import time
from http import HTTPStatus

import requests
from flask import current_app, request
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.common_utilities import (
    VrfType,
    checkAirGappedIsEnabled,
    checkEnableIdentityManagement,
    checkSharedServiceProxyEnabled,
    checkWorkloadProxyEnabled,
    create_virtual_service,
    createClusterFolder,
    createRbacUsers,
    envCheck,
    get_avi_version,
    isAviHaEnabled,
    ping_test,
    preChecks,
    seperateNetmaskAndIp,
)
from common.constants.nsxt_api_constants import NsxWorkflows
from common.lib.avi.avi_base_operations import AVIBaseOperations
from common.lib.avi.avi_constants import AVIDataFiles
from common.lib.avi.avi_infra_operations import AVIInfraOps
from common.lib.avi.avi_template_operations import AVITemplateOperations
from common.lib.govc.govc_client import GOVClient
from common.lib.govc.govc_operations import GOVCOperations
from common.lib.vcenter.vcenter_ssl_operations import VCenterSSLOperations
from common.operation.constants import (
    PLAN,
    Cloud,
    ControllerLocation,
    Env,
    KubernetesOva,
    Paths,
    RegexPattern,
    ResourcePoolAndFolderName,
    Sizing,
    Type,
)
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList, verifyPodsAreRunning
from common.operation.vcenter_operations import checkVmPresent
from common.prechecks.list_reources import validateKubeVersion
from common.replace_value import generateVsphereConfiguredSubnets, generateVsphereConfiguredSubnetsForSeandVIP
from common.util.ako_config_utils import AkoConfigUtils
from common.util.cluster_yaml_data_util import VCFDeployData, VDSDeployData
from common.util.common_utils import CommonUtils
from common.util.file_helper import FileHelper
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.marketplace_util import MarketPlaceUtils
from common.util.request_api_util import RequestApiUtil
from common.util.saas_util import SaaSUtil
from common.util.service_engine_utils import ServiceEngineUtils
from common.util.tanzu_util import TanzuCommands, TanzuUtil
from common.util.velero_util import StandaloneVelero, TmcVelero, VeleroUtil
from common.workflows.nsxt_workflow import NsxtWorkflow

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logger = logging.getLogger(__name__)

__author__ = "Pooja Deshmukh"


class ClusterCreationConstants:
    PING_COMMAND = "ping -c 1 "
    WORKLOAD_SE_NAME_PREFIX = "Workload"
    DETAILS_OF_SERVICE_ENGINE_3 = "detailsOfServiceEngine3.json"
    DETAILS_OF_SERVICE_ENGINE_4 = "detailsOfServiceEngine4.json"
    SE_JSON_PATH = "./vsphere/workloadConfig/se.json"
    SSH_FILE_PATH = "/root/.ssh/id_rsa.pub"


class ClusterCreateWorkflow:
    """Class Constructor"""

    def __init__(self, config, cluster_type):
        self.run_config = config
        spec_json = request.get_json(force=True)
        self.env = self._fetch_env()
        spec_obj = CommonUtils.get_spec_obj(self.env)
        self.spec: spec_obj = spec_obj.parse_obj(spec_json)
        self.tanzu_util = TanzuUtil(env=self.env, spec=self.spec)
        self.saas_util: SaaSUtil = SaaSUtil(self.env, self.spec)

        self.kubectl_util = KubectlUtil()
        self.cluster_type = cluster_type
        self.object_mapping = {Env.VCF: VCFDeployData, Env.VSPHERE: VDSDeployData}
        vc_data = self.spec.envSpec.vcenterDetails
        self.vcenter_ip = vc_data.vcenterAddress
        self.vcenter_username = vc_data.vcenterSsoUser

        str_enc = str(vc_data.vcenterSsoPasswordBase64)
        self.password = CommonUtils.decode_password(str_enc)
        self.vsphere_decoded_password = CommonUtils.encode_password(self.password)
        str_enc_avi = str(self.spec.tkgComponentSpec.aviComponents.aviPasswordBase64)
        self.password_avi = CommonUtils.decode_password(str_enc_avi)

        self.data_center = vc_data.vcenterDatacenter
        self.data_store = vc_data.vcenterDatastore
        self.vc_cluster_name = vc_data.vcenterCluster
        self.parent_resourcePool = vc_data.resourcePoolName
        self.management_cluster = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName

        self.refreshToken = self.spec.envSpec.marketplaceSpec.refreshToken
        self.tmc_required = self.spec.envSpec.saasEndpoints.tmcDetails.tmcAvailability
        cluster_object = self._cluster_config_object(cluster_type=cluster_type)
        self.cluster_data = cluster_object.cluster_data
        self.refreshToken = self.spec.envSpec.marketplaceSpec.refreshToken
        self.aviVersion = get_avi_version(self.env)
        self.avi_fqdn = self._fetch_avi_fqdn()
        self.tmc_flag = self._get_tmc_flag(self.tmc_required)

        self.AviInfraObj = AVIInfraOps(
            self.avi_fqdn, self.password_avi, self.vcenter_ip, self.vcenter_username, self.password
        )
        self.AviTemplateObj = AVITemplateOperations(self.avi_fqdn, self.password_avi, None)
        self.AviBaseOperation = AVIBaseOperations(self.avi_fqdn, self.password_avi)
        self.se_util = ServiceEngineUtils(self.spec)
        self.govc_operation = GOVCOperations(
            self.vcenter_ip,
            self.vcenter_username,
            self.password,
            self.vc_cluster_name,
            self.data_center,
            self.data_store,
            LocalCmdHelper(),
        )
        self.ssl_obj = VCenterSSLOperations(
            self.vcenter_ip,
            self.vcenter_username,
            self.password,
            self.vc_cluster_name,
            self.data_center,
            self.govc_operation,
        )
        self.ako_obj = AkoConfigUtils(
            self.spec,
            self.cluster_type,
            self.avi_fqdn,
            self.password_avi,
            self.vcenter_ip,
            self.vcenter_username,
            self.password,
        )
        if isAviHaEnabled(self.env):
            self.avi_ip = self.spec.tkgComponentSpec.aviComponents.aviClusterIp
        else:
            self.avi_ip = self._fetch_avi_ip(self.avi_fqdn)
        self.tmc_velero = TmcVelero(self.env, self.spec)
        self.standalone_velero = StandaloneVelero(self.env, self.spec)
        self.velero_util = VeleroUtil(self.env, self.spec)
        # license type for cloud SE creation
        self.avi_license_type = self.spec.tkgComponentSpec.aviComponents.typeOfLicense

    def _fetch_env(self):
        env = envCheck()
        if env[1] != 200:
            message = f"Wrong env provided {env[0]}"
            current_app.logger.error(message)
            raise Exception(str(message))
        return env[0]

    def _fetch_avi_ip(self, avi_fqdn):
        govc_client = GOVClient(
            self.vcenter_ip,
            self.vcenter_username,
            self.password,
            self.vc_cluster_name,
            self.data_center,
            self.data_store,
            LocalCmdHelper(),
        )
        avi_ip = govc_client.get_vm_ip(avi_fqdn)
        if avi_ip is None:
            message = "Failed to get IP of AVI controller"
            current_app.logger.error(message)
            raise Exception(message)
        return avi_ip[0]

    def _fetch_avi_fqdn(self):
        avi_fqdn = self.spec.tkgComponentSpec.aviComponents.aviController01Fqdn
        if isAviHaEnabled(self.env):
            avi_fqdn = self.spec.tkgComponentSpec.aviComponents.aviClusterFqdn
        if avi_fqdn is None:
            current_app.logger.error("Failed to get IP of AVI controller")
            raise Exception("Failed to get ip of avi controller")
        return avi_fqdn

    def _cluster_config_object(self, cluster_type):
        return self.object_mapping[self.env](self.spec, cluster_type)

    def _validate_cluster_kube_version(self):
        if not checkAirGappedIsEnabled(self.env) and self.refreshToken != "":
            validateK8s = validateKubeVersion(self.env, self.cluster_type)
            if validateK8s[1] != 200:
                current_app.logger.error(validateK8s[0].json["msg"])
                raise Exception("Failed to validate KubeVersion" + str(validateK8s[0].json["msg"]))
        return True

    def _ping_test_to_vcf_gateway_addr(self):
        if self.cluster_type == Type.SHARED:
            gateway_address = self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceGatewayCidr
        elif self.cluster_type == Type.WORKLOAD:
            gateway_address = self.spec.tkgWorkloadComponents.tkgWorkloadGatewayCidr
        current_app.logger.info("Performing ping test on " + self.cluster_type + " Network Gateway...")
        if ping_test(ClusterCreationConstants.PING_COMMAND + gateway_address.split("/")[0]) != 0:
            current_app.logger.warn(
                "Ping test failed for " + gateway_address + " gateway. It is Recommended to fix "
                "this before proceeding with deployment"
            )
            time.sleep(30)
        else:
            current_app.logger.info("Ping test passed for gateway - " + gateway_address)
        return True

    def _download_and_push_kubernetes_ova_to_vc(self, cluster_data):
        if self.refreshToken:
            current_app.logger.info("Kubernetes OVA configs for  " + self.cluster_type + " cluster")
            mgmt_network = str(self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtNetworkName)
            down_status = MarketPlaceUtils(self.refreshToken).download_kubernetes_ova(
                self.govc_operation,
                mgmt_network,
                cluster_data.kube_version,
                cluster_data.os_name,
                cluster_data.kube_version,
            )
            if down_status[0] is None:
                current_app.logger.error(down_status[1])
                raise Exception(str(down_status[1]))
        else:
            current_app.logger.info(
                "MarketPlace refresh token is not provided, skipping the download of kubernetes ova"
            )
        return True

    def create_orchostrated(
        self, cluster_data, vcenter_ip, vcenter_username, password, data_center, data_store, cluster_name, workload_vip
    ):
        workload_cluster_path = Paths.CLUSTER_PATH + cluster_data.cluster_name
        if not createClusterFolder(cluster_data.cluster_name):
            raise Exception("Failed to create directory: " + str(workload_cluster_path))
        csrf2 = self.AviBaseOperation.obtain_second_csrf()
        if csrf2 is None:
            current_app.logger.error("Failed to get csrf from new password")
            raise Exception("Failed to get csrf from new password")
        get_cloud = self.AviInfraObj.get_cloud_status(Cloud.CLOUD_NAME_VSPHERE)
        if get_cloud[0] is None:
            message = "Failed to get cloud status " + str(get_cloud[1])
            current_app.logger.error(message)
            raise Exception(message)

        if get_cloud[0] == "NOT_FOUND":
            message = "Requested cloud is not created"
            current_app.logger.error(message)
            raise Exception(message)
        else:
            cloud_url = get_cloud[0]
        get_wip = self.AviInfraObj.get_vip_network(workload_vip)
        if get_wip[0] is None:
            message = "Failed to get service engine VIP network " + str(get_wip[1])
            current_app.logger.error(message)
            raise Exception(message)

        if get_wip[0] == "NOT_FOUND":
            current_app.logger.info("Creating New VIP network " + workload_vip)
            ipNetmask = seperateNetmaskAndIp(
                self.spec.componentSpec.tkgWorkloadDataNetworkSpec.tkgWorkloadDataGatewayCidr
            )
            network_gateway = ipNetmask[0]
            network_netmask = ipNetmask[1]
            start_ip = self.spec.componentSpec.tkgWorkloadDataNetworkSpec.tkgWorkloadDataServiceStartRange
            end_ip = self.spec.componentSpec.tkgWorkloadDataNetworkSpec.tkgWorkloadDataServiceEndRange
            vip_net = self.AviInfraObj.create_vip_network(
                workload_vip, cloud_url, network_gateway, network_netmask, start_ip, end_ip
            )
            if vip_net[0] is None:
                message = "Failed to create VIP network " + str(vip_net[1])
                current_app.logger.error(message)
                raise Exception(message)
            wip_url = vip_net[0]
            current_app.logger.info("Created New VIP network " + workload_vip)
        else:
            wip_url = get_wip[0]
        get_se_cloud = self.AviInfraObj.get_SE_cloud_status(Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
        if get_se_cloud[0] is None:
            message = "Failed to get service engine cloud status " + str(get_se_cloud[1])
            current_app.logger.error(message)
            raise Exception(message)

        if get_se_cloud[0] == "NOT_FOUND":
            current_app.logger.info("Creating New service engine cloud " + Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE)
            cloud_se = self.AviInfraObj.create_SE_cloud_arch(
                cloud_url,
                Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE,
                "Workload",
                license_type=self.avi_license_type,
                datastore=data_store,
            )
            if cloud_se[0] is None:
                message = "Failed to create  service engine cloud " + str(cloud_se[1])
                current_app.logger.error(message)
                raise Exception(message)
            se_cloud_url = cloud_se[0]
        else:
            se_cloud_url = get_se_cloud[0]
        get_ipam = self.AviTemplateObj.get_ipam(Cloud.IPAM_NAME_VSPHERE)
        if get_ipam[0] is None or get_ipam[0] == "NOT_FOUND":
            message = "Failed to get service engine Ipam " + str(get_ipam[1])
            current_app.logger.error(message)
            raise Exception(message)

        else:
            ipam_url = get_ipam[0]
        ipam = self.AviTemplateObj.get_ipam_details(ipam_url, wip_url)
        if ipam[0] is None:
            message = "Failed to get service engine Ipam Details " + str(ipam[1])
            current_app.logger.error(message)
            raise Exception(message)
        vm_state = checkVmPresent(vcenter_ip, vcenter_username, password, self.avi_fqdn)
        if vm_state is None:
            message = "Avi controller not found "
            current_app.logger.error(message)
            raise Exception(message)
        avi_uuid = vm_state.config.uuid
        current_app.config["se_ova_path"] = "/tmp/" + avi_uuid + ".ova"
        new_cloud_status = self.AviTemplateObj.update_ipam_with_data_network(ipam_url)
        if new_cloud_status[0] is None:
            message = "Failed to update Ipam " + str(new_cloud_status[1])
            current_app.logger.error(message)
            raise Exception(message)
        dep = self.se_util.controller_deployment(
            self.avi_ip,
            csrf2,
            data_center,
            data_store,
            cluster_name,
            vcenter_ip,
            vcenter_username,
            password,
            se_cloud_url,
            ClusterCreationConstants.SE_JSON_PATH,
            ClusterCreationConstants.DETAILS_OF_SERVICE_ENGINE_3,
            ClusterCreationConstants.DETAILS_OF_SERVICE_ENGINE_4,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME_VSPHERE,
            ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2_VSPHERE,
            3,
            Type.WORKLOAD,
            1,
            self.aviVersion,
        )
        if dep[1] != 200:
            message = "Controller deployment failed" + str(dep[0])
            current_app.logger.error(message)
            raise Exception(message)
        self.ako_obj.ako_deployment_config_for_cluster(
            self.avi_ip, self.management_cluster, cluster_data.cluster_name, cluster_data.cluster_network
        )
        return RequestApiUtil.send_ok("Successfully configured workload cluster"), HTTPStatus.OK

    def _connect_to_cluster(self, cluster_name, cluster_type):
        current_app.logger.info("Connect to " + cluster_type + " cluster")
        cmd_status = self.tanzu_util.switch_to_context(cluster_name)
        if cmd_status[1] != 200:
            message = "Failed to get switch to " + cluster_type + " cluster context " + str(cmd_status[0])
            current_app.logger.error(message)
            raise Exception(message)
        return True

    def _wait_for_pods_running(self, podRunninng, cluster_name):
        count = 0
        command_status = runShellCommandAndReturnOutputAsList(podRunninng)
        if command_status[1] != 0:
            current_app.logger.error("Failed to check if pods are running " + str(command_status[0]))
            raise Exception("Failed to check if pods are running " + str(command_status[0]))
        while not verifyPodsAreRunning(cluster_name, command_status[0], RegexPattern.running) and count < 60:
            command_status_retry = runShellCommandAndReturnOutputAsList(podRunninng)
            if verifyPodsAreRunning(cluster_name, command_status_retry[0], RegexPattern.running):
                return
            if command_status_retry[1] != 0:
                current_app.logger.error("Failed to check if pods are running " + str(command_status_retry[0]))
                return Exception("Failed to check pods are running " + str(command_status_retry[0]))
            count = count + 1
            time.sleep(30)
            current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")

        return Exception(cluster_name + " is not running on waiting " + str(count * 30) + "s")

    def _configure_data_protection(self, cluster_type, cluster_name):
        if self.saas_util.check_tmc_enabled():
            current_app.logger.info("Cluster is already deployed via TMC")
            if TmcVelero.check_data_protection_enabled(self.env, self.spec, cluster_type):
                is_enabled = self.tmc_velero.enable_data_protection(cluster_name, self.management_cluster)
                if not is_enabled[0]:
                    current_app.logger.error(is_enabled[1])
                    raise Exception(str(is_enabled[1]))
                current_app.logger.info(is_enabled[1])
            else:
                current_app.logger.info("Data protection not enabled for cluster " + cluster_name)
        else:
            current_app.logger.info("TMC is deactivated")
            current_app.logger.info("Check whether data protection is to be enabled via Velero on Shared Cluster")
            if StandaloneVelero.check_data_protection_enabled(self.env, self.spec, cluster_type):
                status = self.tanzu_util.switch_to_context(cluster_name)
                if status[1] != 200:
                    current_app.logger.error(
                        "Failed to switch to " + cluster_type + " cluster context " + str(status[0])
                    )
                    raise Exception("Failed to switch to " + cluster_type + " cluster context " + str(status[0]))
                current_app.logger.info("Switched to " + cluster_name + " context")
                is_enabled = self.standalone_velero.enable_data_protection(cluster_type)
                if not is_enabled[0]:
                    current_app.logger.error("ERROR: Failed to enable data protection via velero on Shared Cluster")
                    current_app.logger.error(is_enabled[1])
                    raise Exception(str(is_enabled[1]))
                current_app.logger.info(
                    "Successfully enabled data protection via Velero on " + cluster_type + "Cluster"
                )
                current_app.logger.info(is_enabled[1])
            else:
                current_app.logger.info(
                    "Data protection via Velero setting is not active for " + cluster_type + "Cluster"
                )
        return True

    def _configure_identity_management(self, cluster_data):
        if checkEnableIdentityManagement(self.env):
            current_app.logger.info("Validating pinniped installation status")
            check_pinniped = TanzuUtil.check_pinniped_installed()
            if check_pinniped[1] != 200:
                current_app.logger.error(check_pinniped[0])
                raise Exception(str(check_pinniped[0]))
            rbac_user_status = createRbacUsers(
                cluster_data.cluster_name,
                isMgmt=False,
                env=self.env,
                edit_users=cluster_data.edit_users,
                cluster_admin_users=cluster_data.cluster_admin_users,
                admin_users=cluster_data.admin_users,
                view_users=cluster_data.view_users,
            )
            if rbac_user_status[1] != 200:
                current_app.logger.error(rbac_user_status[0].json["msg"])
                return Exception(str(rbac_user_status[0].json["msg"]))
            current_app.logger.info("Successfully created RBAC for all the provided users")
        else:
            current_app.logger.info("Identity Management is not enabled")
        return

    def _verify_ako_pods_running(self, cluster_name, tmc_enabled):
        current_app.logger.info("Verifying if AKO pods are running...")
        if not self.kubectl_util.check_ako_pods_running(cluster_name, tmc_enabled):
            raise Exception("Ako pods are not running")
        return True

    def _switch_to_mgmt_cluster(self, management_cluster):
        status = TanzuUtil.switch_to_management_context(management_cluster)
        if status[1] != 200:
            current_app.logger.error("Failed to get switch to management cluster context " + str(status[0]))
            raise Exception("Failed to get switch to management cluster context " + str(status[0]))

    def _configure_wrkld_vcf_workflow(self, cluster_type):
        if cluster_type == Type.WORKLOAD:
            try:
                NsxtWorkflow(self.spec, current_app.config, current_app.logger).execute_workflow_vcf(
                    workflow=NsxWorkflows.WORKLOAD
                )
                return True
            except Exception as e:
                raise Exception(str(e))
        return True

    def _configure_workload_se_workflow(self):
        if self.cluster_type == Type.WORKLOAD:
            csrf2 = self.AviBaseOperation.obtain_second_csrf()
            if csrf2 is None:
                current_app.logger.error("Failed to get csrf from new password")
                raise Exception("Failed to get csrf from new password")
            if CommonUtils.is_avi_non_orchestrated(self.spec):
                config_se = self.se_util._create_workload_service_engines(
                    self.avi_fqdn,
                    self.password_avi,
                    csrf2,
                    self.vcenter_ip,
                    self.vcenter_username,
                    self.password,
                    self.vc_cluster_name,
                    self.data_center,
                    self.data_store,
                    self.aviVersion,
                )
                if config_se[1] != 200:
                    raise Exception("Failed to config service engines " + str(config_se[0].json["msg"]))
        return True

    def _checkProxyEnabled(self, cluster_type):
        if cluster_type == Type.SHARED:
            return checkSharedServiceProxyEnabled(self.env)
        elif cluster_type == Type.WORKLOAD:
            return checkWorkloadProxyEnabled(self.env)

    def _get_os_template(self, kube_version):
        return {
            "photon": KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + kube_version,
            "ubuntu": KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + kube_version,
        }

    def _get_tmc_flag(self, tmc_required):
        if tmc_required.lower() == "true":
            return True
        elif tmc_required.lower() == "false":
            current_app.logger.info("TMC registration is deactivated")
            return False
        else:
            raise Exception("Wrong TMC selection attribute provided " + tmc_required)

    def _get_resource_folders_and_pool(self, cluster_type):
        if cluster_type == Type.SHARED:
            ResourcePool = ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER
            ResourceFolder = ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE
        elif cluster_type == Type.WORKLOAD:
            ResourcePool = ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE
            ResourceFolder = ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE
        return ResourcePool, ResourceFolder

    def _get_ssh_key(self):
        try:
            ssh_key = FileHelper.read_line_from_file(file_path=ClusterCreationConstants.SSH_FILE_PATH)
            return ssh_key
        except Exception as e:
            current_app.logger.error("Failed to ssh key from config file " + str(e))
            raise Exception("Failed to ssh key from config file " + str(e))

    def _get_kube_version_for_tmc(self, cluster_data, management_cluster):
        self._switch_to_mgmt_cluster(management_cluster)
        version_status = self.kubectl_util.get_kube_version_full_name(cluster_data.kube_version)
        if version_status[0] is None:
            current_app.logger.error("Kubernetes OVA Version not found for " + self.cluster_type + " Cluster")
            raise Exception("Kubernetes OVA Version not found for " + str(self.cluster_type) + " Cluster")
        else:
            version = version_status[0]
            return version

    def _create_proxy_credentials_tmc(self, cluster_name):
        proxy_name = ""
        if self._checkProxyEnabled(self.env) and not self.saas_util.check_tmc_Register(cluster_name, False):
            proxy_name_state = self.saas_util.create_tkgm_tmc_proxy_credentials(
                cluster_name, "true", self.cluster_type, register=False
            )
            if proxy_name_state[1] != 200:
                raise Exception(str(proxy_name_state[0]))
            proxy_name = "arcas-" + cluster_name + "-tmc-proxy"
            return proxy_name
        return proxy_name

    def _get_control_plane_node_count(self, cluster_data):
        if cluster_data.cluster_plan == PLAN.DEV_PLAN:
            controlPlaneNodeCount = "1"
        elif cluster_data.cluster_plan == PLAN.PROD_PLAN:
            controlPlaneNodeCount = "3"
        else:
            current_app.logger.error(
                "Unsupported control plan provided please specify PROD or DEV " + cluster_data.cluster_plan
            )
            raise Exception("Unsupported control plan provided please specify PROD or DEV " + cluster_data.cluster_plan)
        return controlPlaneNodeCount

    def _get_cpu_memory_disk(self, cluster_data):
        if cluster_data.cluster_size.lower() == "small":
            cpu, memory, disk = Sizing.small["CPU"], Sizing.small["MEMORY"], Sizing.small["DISK"]
        elif cluster_data.cluster_size.lower() == "medium":
            cpu, memory, disk = Sizing.medium["CPU"], Sizing.medium["MEMORY"], Sizing.medium["DISK"]
        elif cluster_data.cluster_size.lower() == "large":
            cpu, memory, disk = Sizing.large["CPU"], Sizing.large["MEMORY"], Sizing.large["DISK"]
        elif cluster_data.cluster_size.lower() == "extra-large":
            cpu, memory, disk = Sizing.extraLarge["CPU"], Sizing.extraLarge["MEMORY"], Sizing.extraLarge["DISK"]
        elif cluster_data.cluster_size.lower() == "custom":
            memory = str(int(cluster_data.control_plane_mem_gb) * 1024)
        else:
            errorMessage = (
                "Provided cluster size: " + cluster_data.cluster_size + "is not supported, please provide one of: "
            )
            "small/medium/large/extra-large/custom"
            current_app.logger.error(errorMessage)
            raise Exception(str(errorMessage))
        return cpu, memory, disk

    def _apply_k8s_lable_to_shared(self, cluster_name):
        if self.cluster_type == Type.SHARED:
            status = runShellCommandAndReturnOutputAsList(KubectlUtil.ADD_SERVICES_LABEL.format(cluster=cluster_name))
            if status[1] != 0:
                current_app.logger.error("Failed to apply k8s label " + str(status[0]))
                raise Exception("Failed to apply k8s label " + str(status[0]))
        return

    def _fetch_nsxt_tier1_gateway(self):
        status, value = self.AviInfraObj._get_cloud_connect_user()
        nsxt_cred = value["nsxUUid"]
        nsxt_tier1_route_name = str(self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName)
        nsxt_address = str(self.spec.envSpec.vcenterDetails.nsxtAddress)
        tier1_status, tier1_id = self.AviInfraObj.fetch_tier1_gateway_id(nsxt_cred, nsxt_tier1_route_name, nsxt_address)
        if tier1_status is None:
            current_app.logger.error("Failed to get Tier 1 details " + str(tier1_id))
            raise Exception("Failed to get Tier 1 details " + str(tier1_id))
        return tier1_id

    def workload_preconfig(self):
        cluster_object = self._cluster_config_object(cluster_type=self.cluster_type)
        cluster_data = cluster_object.cluster_data
        if self.env == Env.VSPHERE:
            workload_config_network_name = self.spec.tkgWorkloadDataNetwork.tkgWorkloadDataNetworkName
        if self.env == Env.VCF:
            workload_config_network_name = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
        self._validate_cluster_kube_version()
        self._download_and_push_kubernetes_ova_to_vc(cluster_data)
        if CommonUtils.is_avi_non_orchestrated(self.spec):
            workload_vip = self.spec.tkgWorkloadDataNetwork.tkgWorkloadDataNetworkName
            status = self.create_orchostrated(
                cluster_data,
                self.vcenter_ip,
                self.vcenter_username,
                self.password,
                self.data_center,
                self.data_store,
                self.vc_cluster_name,
                workload_vip,
            )
            if status[1] != 200:
                message = "Failed to configure workload cluster " + str(status[0])
                current_app.logger.error(message)
                raise Exception(message)
        else:
            csrf2 = self.AviBaseOperation.obtain_second_csrf()
            if csrf2 is None:
                message = "Failed to get csrf from new password"
                current_app.logger.error(message)
                raise Exception(message)
            cloud = Cloud.CLOUD_NAME_VSPHERE
            if self.env == Env.VCF:
                cloud = Cloud.CLOUD_NAME_NSXT
            get_cloud = self.AviInfraObj.get_cloud_status(cloud)
            if get_cloud[0] is None:
                message = "Failed to get cloud status " + str(get_cloud[1])
                current_app.logger.error(message)
                raise Exception(message)

            if get_cloud[0] == "NOT_FOUND":
                message = "Requested cloud is not created"
                current_app.logger.error(message)
                raise Exception(message)
            else:
                cloud_url = get_cloud[0]
            if self.env == Env.VSPHERE:
                cluster_status = self.AviInfraObj.get_cluster_url(self.vc_cluster_name)
                startIp = self.spec.tkgWorkloadDataNetwork.tkgWorkloadAviServiceIpStartRange
                endIp = self.spec.tkgWorkloadDataNetwork.tkgWorkloadAviServiceIpEndRange
                prefixIpNetmask = seperateNetmaskAndIp(
                    self.spec.tkgWorkloadDataNetwork.tkgWorkloadDataNetworkGatewayCidr
                )
                if cluster_status[0] is None or cluster_status[0] == "NOT_FOUND":
                    message = "Failed to get cluster details" + str(cluster_status[1])
                    current_app.logger.error(message)
                    raise Exception(message)

                get_ipam = self.AviTemplateObj.get_ipam(Cloud.IPAM_NAME_VSPHERE)
                if get_ipam[0] is None:
                    message = "Failed to get service engine Ipam " + str(get_ipam[1])
                    current_app.logger.error(message)
                    raise Exception(message)
                get_network_url = self.AviInfraObj.get_network_url(workload_config_network_name, cloud)
                if get_network_url[0] is None:
                    message = "Failed to get network details " + str(get_network_url[1])
                    current_app.logger.error(message)
                    raise Exception(message)
                update = self.AviTemplateObj.update_ipam_profile(Cloud.IPAM_NAME_VSPHERE, get_network_url[0])
                if update[0] is None:
                    message = "Failed to update service engine Ipam " + str(update[1])
                    current_app.logger.error(message)
                    raise Exception(message)
                group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
            else:
                group_name = Cloud.SE_WORKLOAD_GROUP_NAME_NSXT
                startIp = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipIpStartRange
                endIp = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipIpEndRange
                prefixIpNetmask = seperateNetmaskAndIp(
                    self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr
                )
            get_se_cloud = self.AviInfraObj.get_SE_cloud_status(group_name)
            if get_se_cloud[0] is None:
                message = "Failed to get service engine cloud status " + str(get_se_cloud[1])
                current_app.logger.error(message)
                raise Exception(message)
            if get_se_cloud[0] == "NOT_FOUND":
                current_app.logger.info("Creating New service engine cloud " + group_name)
                cloud_se = self.AviInfraObj.create_se_cloud(
                    cloud_url,
                    group_name,
                    cluster_status[0],
                    self.data_store,
                    ClusterCreationConstants.WORKLOAD_SE_NAME_PREFIX,
                    self.avi_license_type,
                )
                if cloud_se[0] is None:
                    message = "Failed to create service engine cloud " + str(cloud_se[1])
                    current_app.logger.error(message)
                    raise Exception(message)
            get_management_data_pg = self.AviInfraObj.get_network_url(workload_config_network_name, cloud)
            if get_management_data_pg[0] is None:
                message = "Failed to get workload data network details " + str(get_management_data_pg[1])
                current_app.logger.error(message)
                raise Exception(message)
            getManagementDetails_data_pg = self.AviInfraObj.get_network_details(get_management_data_pg[0])
            if getManagementDetails_data_pg[0] is None:
                message = "Failed to get workload data network details " + str(getManagementDetails_data_pg[2])
                current_app.logger.error(message)
                raise Exception(message)
            if self.env == Env.VSPHERE:
                generateVsphereConfiguredSubnets(
                    AVIDataFiles.NETWORK_DETAILS, startIp, endIp, prefixIpNetmask[0], int(prefixIpNetmask[1])
                )
            else:
                generateVsphereConfiguredSubnetsForSeandVIP(
                    AVIDataFiles.NETWORK_DETAILS, startIp, endIp, prefixIpNetmask[0], int(prefixIpNetmask[1])
                )
            if getManagementDetails_data_pg[0] == "AlreadyConfigured":
                current_app.logger.info("Ip pools are already configured.")
            else:
                update_resp = self.AviInfraObj.update_network_with_ip_pools(get_management_data_pg[0])
                if update_resp[0] != 200:
                    message = "Failed to update ip " + str(update_resp[1])
                    current_app.logger.error(message)
                    raise Exception(message)
            new_cloud_json = FileHelper.load_json(spec_path=AVIDataFiles.NEW_CLOUD_DETAILS)
            uuid = None
            try:
                uuid = new_cloud_json["uuid"]
            except Exception:
                for re in new_cloud_json["results"]:
                    if re["name"] == cloud:
                        uuid = re["uuid"]
            if uuid is None:
                message = "Uuid not found "
                current_app.logger.error(message)
                raise Exception(message)
            vrf = self.AviInfraObj.get_vrf_and_next_route_id(uuid, VrfType.GLOBAL, prefixIpNetmask[0])
            if vrf[0] is None or vrf[1] == "NOT_FOUND":
                message = "Vrf not found " + str(vrf[1])
                current_app.logger.error(message)
                raise Exception(message)
            if vrf[1] != "Already_Configured":
                current_app.logger.info("Routing is not cofigured, configuring it.")
                add_static_route = self.AviInfraObj.add_static_route(vrf[0], prefixIpNetmask[0], vrf[1])
                if add_static_route[0] is None:
                    message = "Failed to add static route " + str(add_static_route[1])
                    current_app.logger.error(message)
                    raise Exception(message)
                current_app.logger.info("Routing is configured")
            self.ako_obj.ako_deployment_config_for_cluster(
                self.avi_ip, self.management_cluster, cluster_data.cluster_name, cluster_data.cluster_network
            )
            if self.env == Env.VCF:
                tier1name = str(self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName)
                vrf_vip = self.AviInfraObj.get_vrf_and_next_route_id(uuid, tier1name, prefixIpNetmask[0])
                if vrf_vip[0] is None or vrf_vip[1] == "NOT_FOUND":
                    message = "Cluster VIP Vrf not found " + str(vrf_vip[1])
                    current_app.logger.error(message)
                    raise Exception(message)
                if vrf_vip[1] != "Already_Configured":
                    ad = self.AviInfraObj.add_static_route(vrf_vip[0], prefixIpNetmask[0], vrf_vip[1])
                    if ad[0] is None:
                        message = "Failed to add static route " + str(ad[1])
                        current_app.logger.error(message)
                        raise Exception(message)
                vrf_url = vrf_vip[0]
                tier1 = self._fetch_nsxt_tier1_gateway()
                se_count = 2
                virtual_service, error = create_virtual_service(
                    self.avi_fqdn,
                    csrf2,
                    uuid,
                    group_name,
                    get_management_data_pg[0],
                    se_count,
                    tier1,
                    vrf_url,
                    self.aviVersion,
                )
                if virtual_service is None:
                    message = "Failed to create virtual service " + str(error)
                    current_app.logger.error(message)
                    raise Exception(message)
        return RequestApiUtil.send_ok("Successfully configured workload preconfig"), HTTPStatus.OK

    def create_cluster(self):
        cluster_type = self.cluster_type
        cluster_object = self._cluster_config_object(cluster_type=cluster_type)
        cluster_data = cluster_object.cluster_data
        self._validate_cluster_kube_version()
        pre = preChecks()
        if pre[1] != 200:
            message = str(pre[0].json["msg"])
            current_app.logger.error(message)
            raise Exception(message)
        self._download_and_push_kubernetes_ova_to_vc(cluster_data)
        if self.env == Env.VCF:
            # perform ping test to the gateways
            self._configure_wrkld_vcf_workflow(cluster_type)
            self._ping_test_to_vcf_gateway_addr()
        if self.env == Env.VSPHERE and cluster_type == Type.WORKLOAD:
            workload_network = self.spec.tkgWorkloadComponents.tkgWorkloadNetworkName
            cloud = Cloud.CLOUD_NAME_VSPHERE
            dhcp = self.AviInfraObj.enable_dhcp(workload_network, cloud)
            if dhcp[0] is None:
                raise Exception("Failed to enable dhcp on workload network" + str(dhcp[1]))
        self._configure_workload_se_workflow()
        ResourcePool, ResourceFolder = self._get_resource_folders_and_pool(cluster_type)
        create = self.ssl_obj.create_resource_folder_and_wait(
            ResourcePool,
            ResourceFolder,
            self.parent_resourcePool,
        )
        if create[1] != 200:
            message = "Failed to create resource pool and folder " + create[0].json["msg"]
            current_app.logger.error(message)
            raise Exception(message)
        ssh_key = self._get_ssh_key()
        controlPlaneNodeCount = self._get_control_plane_node_count(cluster_data)
        cpu, memory, disk = self._get_cpu_memory_disk(cluster_data)
        if not createClusterFolder(cluster_data.cluster_name):
            message = "Failed to create directory: " + Paths.CLUSTER_PATH + cluster_data.cluster_name
            current_app.logger.error(message)
            raise Exception(message)
        current_app.logger.info(
            "The config files for "
            + cluster_type
            + " services cluster will be located at: "
            + Paths.CLUSTER_PATH
            + cluster_data.cluster_name
        )
        if self.saas_util.check_tmc_enabled():
            version = self._get_kube_version_for_tmc(cluster_data, self.management_cluster)
            proxy_name = self._create_proxy_credentials_tmc(cluster_data.cluster_name)
        vsphere_management_config = "/" + self.data_center
        datastore_path = vsphere_management_config + "/datastore/" + self.data_store
        cluster_folder_path = vsphere_management_config + "/vm/" + ResourceFolder
        cluster_resource_path = vsphere_management_config + "/host/" + self.vc_cluster_name + "/Resources/"
        if self.parent_resourcePool:
            cluster_resource_path = cluster_resource_path + self.parent_resourcePool + "/" + ResourcePool
        else:
            cluster_resource_path = cluster_resource_path + ResourcePool
        cluster_network_path = self.saas_util.get_network_Path_tmc(
            cluster_data.cluster_network, self.vcenter_ip, self.vcenter_username, self.password
        )
        if cluster_network_path is None:
            message = "Network folder not found for " + cluster_network_path
            current_app.logger.error(message)
            raise Exception(message)
        tanzu_cluster_list_cmd = TanzuCommands.CLUSTER_LIST
        tanzu_cluster_list = runShellCommandAndReturnOutputAsList(tanzu_cluster_list_cmd)
        if tanzu_cluster_list[1] != 0:
            message = "Failed to run command to check status of pods"
            current_app.logger.error(message)
            raise Exception(message)
        if not tanzu_cluster_list[0] is None and not verifyPodsAreRunning(
            cluster_data.cluster_name, tanzu_cluster_list[0], RegexPattern.running
        ):
            if not self.saas_util.check_tmc_enabled():
                if cluster_type == Type.SHARED:
                    current_app.logger.info("Creating AkoDeploymentConfig for shared services cluster")
                    self.ako_obj.ako_deployment_config_for_cluster(
                        self.avi_ip,
                        self.management_cluster,
                        cluster_data.cluster_name,
                        cluster_data.cluster_network,
                    )
                current_app.logger.info("Deploying " + cluster_type + " cluster using tanzu")
                deploy_status = self.tanzu_util.deploy_multi_cloud_cluster(
                    cluster_data.cluster_name,
                    cluster_data.cluster_plan,
                    self.data_center,
                    self.data_store,
                    cluster_folder_path,
                    cluster_network_path,
                    self.vsphere_decoded_password,
                    cluster_resource_path,
                    self.vcenter_ip,
                    ssh_key,
                    self.vcenter_username,
                    cluster_data.machineCount,
                    cluster_data.cluster_size,
                    cluster_type,
                )
                if deploy_status[0] is None:
                    message = "Failed to deploy cluster " + deploy_status[1]
                    current_app.logger.error(message)
                    raise Exception(message)
            else:
                current_app.logger.info("Creating AkoDeploymentConfig for shared services cluster")
                if cluster_type == Type.SHARED:
                    self.ako_obj.ako_deployment_config_for_cluster(
                        self.avi_ip,
                        self.management_cluster,
                        cluster_data.cluster_name,
                        cluster_data.cluster_network,
                    )
                current_app.logger.info("Deploying " + cluster_type + " cluster, after verification using tmc")
                template = self._get_os_template(cluster_data.kube_version)[cluster_data.os_name]
                templatePath = vsphere_management_config + "/vm/" + template
                ako_label = self.ako_obj.fetch_ako_label_for_cluster()
                provisioner = "default"
                if not cluster_data.clusterGroup:
                    cluster_data.clusterGroup = "default"
                register_payload = self.saas_util.payload_tmc_cluster_creation(
                    self.management_cluster,
                    provisioner,
                    cluster_data.cluster_name,
                    cluster_data.clusterGroup,
                    cluster_data.pod_cidr,
                    cluster_data.service_cidr,
                    ssh_key,
                    self.vcenter_ip,
                    cpu,
                    disk,
                    memory,
                    cluster_data.machineCount,
                    ako_label,
                    version,
                    vsphere_management_config,
                    datastore_path,
                    cluster_folder_path,
                    cluster_network_path,
                    cluster_resource_path,
                    cluster_data.os_name,
                    cluster_data.os_version,
                    "amd64",
                    templatePath,
                    proxy_name,
                    controlPlaneNodeCount,
                )
                create_response = self.saas_util.create_tkgm_workload_cluster_on_tmc(
                    register_payload, self.management_cluster, provisioner
                )
                if not create_response[0]:
                    message = str(create_response[1])
                    current_app.logger.error(message)
                    raise Exception(message)
                else:
                    current_app.logger.info(create_response[1])
        else:
            current_app.logger.info(cluster_data.cluster_name + " cluster is already deployed and running ")
        self._wait_for_pods_running(tanzu_cluster_list_cmd, cluster_data.cluster_name)

        self._switch_to_mgmt_cluster(self.management_cluster)

        self._apply_k8s_lable_to_shared(cluster_data.cluster_name)

        self._connect_to_cluster(cluster_data.cluster_name, cluster_type)

        self._configure_identity_management(cluster_data)

        self._verify_ako_pods_running(cluster_data.cluster_name, self.tmc_flag)

        self._configure_data_protection(self.cluster_type, cluster_data.cluster_name)

        to = self.saas_util.register_tanzu_observability(cluster_data.cluster_name, cluster_data.cluster_size)
        if to[1] != 200:
            message = str(to[0])
            current_app.logger.error(message)
            raise Exception(message)

        if cluster_type == Type.WORKLOAD:
            tsm = self.saas_util.register_tsm(cluster_data.cluster_name, cluster_data.cluster_size)
            if tsm[1] != 200:
                message = str(tsm[0])
                current_app.logger.error(message)
                raise Exception(message)
