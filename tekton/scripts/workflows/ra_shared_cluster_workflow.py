#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path
import traceback
import time
import json
import base64
import ruamel
from model.vsphereSpec import VsphereMasterSpec
from constants.constants import TKG_EXTENSIONS_ROOT, ControllerLocation, KubectlCommands, \
    Paths, Task, ResourcePoolAndFolderName, PLAN, Sizing, ClusterType, RegexPattern, AkoType,\
    AppName, Avi_Tkgs_Version, Avi_Version, Cloud, Env, Tkg_version, SegmentsName

from jinja2 import Template
from lib.kubectl_client import KubectlClient
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from model.status import (ExtensionState, HealthEnum, SharedExtensionState,
                          State)
from tqdm import tqdm
from util.cmd_helper import CmdHelper
from util.file_helper import FileHelper
from util.git_helper import Git
from util.logger_helper import LoggerHelper, log, log_debug
from util.ssh_helper import SshHelper
from util.tanzu_utils import TanzuUtils
from util.cmd_runner import RunCmd
from util.common_utils import downloadAndPushKubernetesOvaMarketPlace, runSsh, getNetworkFolder, \
    deployCluster, registerWithTmcOnSharedAndWorkload, registerTanzuObservability, checkenv, getVipNetworkIpNetMask, \
    obtain_second_csrf, createClusterFolder, createResourceFolderAndWait, checkTmcEnabled, getKubeVersionFullName, \
    getNetworkPathTMC, checkSharedServiceProxyEnabled, checkTmcRegister, createProxyCredentialsTMC, enable_data_protection,\
    checkEnableIdentityManagement, checkPinnipedInstalled, createRbacUsers, checkDataProtectionEnabled
from util.vcenter_operations import createResourcePool, create_folder
from util.ShellHelper import runShellCommandAndReturnOutputAsList, verifyPodsAreRunning,\
    grabKubectlCommand, grabPipeOutput, grabPipeOutputChagedDir, runShellCommandWithPolling
from workflows.cluster_common_workflow import ClusterCommonWorkflow
from util.shared_config import deployExtentions
from util.tkg_util import TkgUtil



logger = LoggerHelper.get_logger(Path(__file__).stem)


class RaSharedClusterWorkflow:
    def __init__(self, run_config: RunConfig):

        self.run_config = run_config
        self.tkg_util_obj = TkgUtil(run_config=self.run_config)
        self.tkg_version_dict = self.tkg_util_obj.get_desired_state_tkg_version()
        self.desired_state_tkg_version = None
        self.env = "vsphere"         #keeping code for env check, so hardcoding env as vsphere
        if "tkgs" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_WCP_MASTER_SPEC_PATH)
            self.desired_state_tkg_version = self.tkg_version_dict['tkgs']
        elif "tkgm" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
            self.desired_state_tkg_version = self.tkg_version_dict['tkgm']
        else:
            raise Exception(f"Could not find supported TKG version: {self.tkg_version_dict}")
        
        #self.extensions_root = TKG_EXTENSIONS_ROOT[self.desired_state_tkg_version]
        #self.extensions_dir = Paths.TKG_EXTENSIONS_DIR.format(extensions_root=self.extensions_root)
        # Specifies current running version as per state.yml
        self.current_version = self.run_config.state.shared_services.version
        self.prev_version = self.run_config.state.shared_services.upgradedFrom or self.run_config.state.shared_services.version
        self.tkg_cli_client = TkgCliClient()
        self.kubectl_client =  KubectlClient()
        self.common_workflow = ClusterCommonWorkflow()
        # Following values must be set in upgrade scenarios
        self.prev_extensions_root = None
        self.prev_extensions_dir = None
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        with open(jsonpath) as f:
            self.jsonspec = json.load(f)
        self.rcmd = RunCmd()

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)


    def _template_deploy_yaml(self):
        deploy_yaml = FileHelper.read_resource(Paths.VSPHERE_SHARED_SERVICES_SPEC_J2)
        t = Template(deploy_yaml)
        return t.render(spec=self.run_config.spec)


    def isAviHaEnabled(self):
        try:
            if TkgUtil.isEnvTkgs_wcp(self.jsonspec):
                enable_avi_ha = self.jsonspec['tkgsComponentSpec']['aviComponents']['enableAviHa']
            else:
                enable_avi_ha = self.jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
            if str(enable_avi_ha).lower() == "true":
                return True
            else:
                return False
        except:
            return False


    def akoDeploymentConfigSharedCluster(self,shared_cluster_name, aviVersion):
        management_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtClusterName']
        commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]
        kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kubeContextCommand is None:
            logger.error("Failed to get switch to management cluster context command")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to management cluster context command",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
        status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
        if status[1] != 0:
            logger.error("Failed to get switch to management cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to management cluster context " + str(status[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        podRunninng_ako_main = ["kubectl", "get", "pods", "-A"]
        podRunninng_ako_grep = ["grep", AppName.AKO]
        time.sleep(30)
        timer = 30
        ako_pod_running = False
        while timer < 600:
            logger.info("Check AKO pods are running. Waited for " + str(timer) + "s retrying")
            command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
            if command_status_ako[1] != 0:
                time.sleep(30)
                timer = timer + 30
            else:
                ako_pod_running = True
                break
        if not ako_pod_running:
            logger.error("AKO pods are not running on waiting for 10m " + command_status_ako[0])
            d = {
                "responseType": "ERROR",
                "msg": "AKO pods are not running on waiting for 10m " + str(command_status_ako[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        logger.info("Checking if AKO Deployment Config already exists for Shared services cluster: " + shared_cluster_name)
        command_main = ["kubectl", "get", "adc"]
        command_grep = ["grep", "install-ako-for-shared-services-cluster"]
        command_status_adc = grabPipeOutput(command_main, command_grep)
        if command_status_adc[1] == 0:
            logger.debug("Found an already existing AKO Deployment Config: "
                                    "install-ako-for-shared-services-cluster")
            command = ["kubectl", "delete", "adc", "install-ako-for-shared-services-cluster"]
            status = runShellCommandAndReturnOutputAsList(command)
            if status[1] != 0:
                logger.error("Failed to delete an already present AKO Deployment config")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to delete an already present AKO Deployment config",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

        if self.isAviHaEnabled():
            avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
        else:
            avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
        if avi_fqdn is None:
            logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        try:
            tkg_mgmt_data_pg = self.jsonspec['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName']
            tkg_cluster_vip_name = self.jsonspec['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkName']
        except Exception as e:
            logger.error("One of the following values is not present in input file: "
                                    "tkgMgmtDataNetworkName, tkgClusterVipNetworkName")
            logger.error(str(e))
            d = {
                "responseType": "ERROR",
                "msg": "One of the following values is not present in input file: tkgMgmtDataNetworkName, "
                    "tkgClusterVipNetworkName",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if TkgUtil.isEnvTkgs_wcp(self.jsonspec):
            avienc_pass = str(self.jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
        else:
            avienc_pass = str(self.jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
        csrf2 = obtain_second_csrf(avi_fqdn, avienc_pass)
        if csrf2 is None:
            logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        tkg_mgmt_data_netmask = getVipNetworkIpNetMask(avi_fqdn, csrf2, tkg_mgmt_data_pg, aviVersion)
        if tkg_mgmt_data_netmask[0] is None or tkg_mgmt_data_netmask[0] == "NOT_FOUND":
            logger.error("Failed to get TKG Management Data netmask")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get TKG Management Data netmask",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        tkg_cluster_vip_netmask = getVipNetworkIpNetMask(avi_fqdn, csrf2, tkg_cluster_vip_name, aviVersion)
        if tkg_cluster_vip_netmask[0] is None or tkg_cluster_vip_netmask[0] == "NOT_FOUND":
            logger.error("Failed to get Cluster VIP netmask")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get Cluster VIP netmask",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        logger.info("Creating AKODeploymentConfig for shared services cluster...")
        self.createAkoFile(avi_fqdn, shared_cluster_name, tkg_mgmt_data_netmask[0], tkg_mgmt_data_pg)
        yaml_file_path = Paths.CLUSTER_PATH + shared_cluster_name + "/tkgvsphere-ako-shared-services-cluster.yaml"
        listOfCommand = ["kubectl", "create", "-f", yaml_file_path]
        status = runShellCommandAndReturnOutputAsList(listOfCommand)
        if status[1] != 0:
            if not str(status[0]).__contains__("already has a value"):
                logger.error("Failed to apply ako" + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create new AkoDeploymentConfig " + str(status[0]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        logger.info("Successfully created a new AkoDeploymentConfig for shared services cluster")
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully validated running status for AKO",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200



    def createAkoFile(self,ip, shared_cluster_name, tkgMgmtDataVipCidr, tkgMgmtDataPg):
        repository = 'projects.registry.vmware.com/tkg/ako'

        data = dict(
            apiVersion='networking.tkg.tanzu.vmware.com/v1alpha1',
            kind='AKODeploymentConfig',
            metadata=dict(
                finalizers=['ako-operator.networking.tkg.tanzu.vmware.com'],
                generation=1,
                name='install-ako-for-shared-services-cluster',
            ),
            spec=dict(
                adminCredentialRef=dict(
                    name='avi-controller-credentials',
                    namespace='tkg-system-networking'),
                certificateAuthorityRef=dict(
                    name='avi-controller-ca',
                    namespace='tkg-system-networking'
                ),
                cloudName=Cloud.CLOUD_NAME_VSPHERE,
                clusterSelector=dict(
                    matchLabels=dict(
                        type=AkoType.SHARED_CLUSTER_SELECTOR
                    )
                ),
                controller=ip,
                dataNetwork=dict(cidr=tkgMgmtDataVipCidr, name=tkgMgmtDataPg),
                extraConfigs=dict(ingress=dict(defaultIngressController=False, disableIngressClass=True)),
                serviceEngineGroup=Cloud.SE_GROUP_NAME_VSPHERE
            )
        )
        with open(Paths.CLUSTER_PATH + shared_cluster_name + '/tkgvsphere-ako-shared-services-cluster.yaml', 'w') as outfile:
            yaml = ruamel.yaml.YAML()
            yaml.indent(mapping=2, sequence=4, offset=3)
            yaml.dump(data, outfile)
        
    @log("Updating state file")
    def _update_state(self, task: Task, msg="Successful shared cluster deployment"):
        state_file_path = os.path.join(self.run_config.root_dir, Paths.STATE_PATH)
        state: State = FileHelper.load_state(state_file_path)
        self.cluster_to_deploy = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterName']
        if task == Task.DEPLOY_CLUSTER:
            state.shared_services.deployed = True
            state.shared_services.name = self.cluster_to_deploy
            state.shared_services.version = self.desired_state_tkg_version
            state.shared_services.health = HealthEnum.UP
        elif task == Task.UPGRADE_CLUSTER:
            ext_state = ExtensionState(deployed=True, upgraded=False)
            state.shared_services.upgradedFrom = state.shared_services.version
            state.shared_services.version = self.desired_state_tkg_version
            state.shared_services.name = self.cluster_to_deploy
            state.shared_services.health = HealthEnum.UP
            state.shared_services.extensions = SharedExtensionState(certManager=ext_state,
                                                                    contour=ext_state,
                                                                    externalDns=ext_state,
                                                                    harbor=ext_state)
        elif task == Task.DEPLOY_CERT_MANAGER or task == Task.UPGRADE_CERT_MANAGER:
            state.shared_services.extensions.certManager = ExtensionState(deployed=True,
                                                                          upgraded=True)
        elif task == Task.DEPLOY_CONTOUR or task == Task.UPGRADE_CONTOUR:
            state.shared_services.extensions.contour = ExtensionState(deployed=True, upgraded=True)
        elif task == Task.DEPLOY_EXTERNAL_DNS or task == Task.UPGRADE_EXTERNAL_DNS:
            state.shared_services.extensions.externalDns = ExtensionState(deployed=True,
                                                                          upgraded=True)
        elif task == Task.DEPLOY_HARBOR or task == Task.UPGRADE_HARBOR:
            state.shared_services.extensions.harbor = ExtensionState(deployed=True, upgraded=True)
        elif task == Task.ATTACH_CLUSTER_TO_TMC:
            state.shared_services.integrations.tmc.attached = True

        FileHelper.dump_state(state, state_file_path)

    def _attach_cluster_to_tmc(self, jsonspec):
        try:
            cluster_group = 'default'
            api_token = jsonspec['envSpec']["saasEndpoints"]['tmcDetails']['tmcRefreshToken']
            self.common_workflow.attach_cluster_to_tmc(cluster_name=self.cluster_to_deploy,
                                                       cluster_group=cluster_group,
                                                       api_token=self.spec.integrations.tmc.apiToken)
            self._update_state(task=Task.ATTACH_CLUSTER_TO_TMC,
                               msg=f'Cluster attachment to Tmc completed for '
                                   f'{self.cluster_to_deploy}')
            return True
        except Exception:
            logger.error("Error Encountered in Attaching to TMC: {}".format(traceback.format_exc()))
            return False

    @log('Deploy Shared Services Cluster')
    def deploy(self):
        json_dict = self.jsonspec
        vsSpec = VsphereMasterSpec.parse_obj(json_dict)
        aviVersion = Avi_Tkgs_Version.VSPHERE_AVI_VERSION if TkgUtil.isEnvTkgs_wcp(self.jsonspec) else Avi_Version.VSPHERE_AVI_VERSION
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        cluster_name = self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        data_store = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
        parent_resourcePool = self.jsonspec['envSpec']['vcenterDetails']['resourcePoolName']
        refToken = self.jsonspec['envSpec']['marketplaceSpec']['refreshToken']
        kubernetes_ova_os = self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"]["tkgSharedserviceBaseOs"]
        kubernetes_ova_version = self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"]["tkgSharedserviceKubeVersion"]
        pod_cidr = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceClusterCidr']
        service_cidr = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceServiceCidr']
        isEnvTkgs_ns = TkgUtil.isEnvTkgs_ns(self.jsonspec)
        if refToken:
            logger.info("Kubernetes OVA configs for shared services cluster")
            down_status = downloadAndPushKubernetesOvaMarketPlace(self.jsonspec,
                                                                  kubernetes_ova_version,
                                                                  kubernetes_ova_os)
            if down_status[0] is None:
                logger.error(down_status[1])
                d = {
                    "responseType": "ERROR",
                    "msg": down_status[1],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        else:
            logger.info("MarketPlace refresh token is not provided, skipping the download of kubernetes ova")
        try:
            isCreated4 = createResourcePool(vcenter_ip, vcenter_username, password,
                                            cluster_name,
                                            ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER,
                                            parent_resourcePool)
            if isCreated4 is not None:
                logger.info(
                    "Created resource pool " + ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER)
        except Exception as e:
            logger.error("Failed to create resource pool " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create resource pool " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        try:
            isCreated1 = create_folder(vcenter_ip, vcenter_username, password,
                                    data_center,
                                    ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE)
            if isCreated1 is not None:
                logger.info("Created folder " + ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE)
        except Exception as e:
            logger.error("Failed to create folder " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create folder " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500, str(e)
        management_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtClusterName']
        try:
            ssh_key = runSsh(vcenter_username)
            # with open('/root/.ssh/id_rsa.pub', 'r') as f:
            #     re = f.readline()
        except Exception as e:
            logger.error("Failed to ssh key from config file " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to ssh key from config file " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        #Init tanzu cli plugins
        tanzu_init_cmd = "tanzu plugin sync"
        command_status = self.rcmd.run_cmd_output(tanzu_init_cmd)
        logger.debug("Tanzu plugin output: {}".format(command_status))
        podRunninng = ["tanzu", "cluster", "list"]
        command_status = runShellCommandAndReturnOutputAsList(podRunninng)
        if command_status[1] != 0:
            logger.error("Failed to run command to check status of pods")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to run command to check status of pods",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        tmc_required = str(self.jsonspec['envSpec']["saasEndpoints"]['tmcDetails']['tmcAvailability'])
        tmc_flag = False
        if tmc_required.lower() == "true":
            tmc_flag = True
        elif tmc_required.lower() == "false":
            tmc_flag = False
            logger.info("Tmc registration is disabled")
        else:
            logger.error("Wrong tmc selection attribute provided " + tmc_required)
            d = {
                "responseType": "ERROR",
                "msg": "Wrong tmc selection attribute provided " + tmc_required,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if self.env == Env.VCF:
            shared_cluster_name = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceClusterName']
            cluster_plan = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceDeploymentType']
        else:
            shared_cluster_name = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceClusterName']
            cluster_plan = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceDeploymentType']
        if cluster_plan == PLAN.DEV_PLAN or cluster_plan == PLAN.DEV_PLAN:
            if self.env == Env.VCF:
                machineCount = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceWorkerMachineCount']
            else:
                machineCount = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceWorkerMachineCount']
        else:
            logger.error("Unsupported control plan provided please specify PROD or DEV " + cluster_plan)
            d = {
                "responseType": "ERROR",
                "msg": "Unsupported control plan provided please specify PROD or DEV " + cluster_plan,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if self.env == Env.VSPHERE:
            size = str(self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceSize'])
        else:
            size = str(self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceSize'])
        if size.lower() == "small":
            logger.debug("Recommended size for shared services cluster is: medium/large/extra-large/custom")
            pass
        elif size.lower() == "large":
            pass
        elif size.lower() == "medium":
            pass
        elif size.lower() == "extra-large":
            pass
        elif size.lower() == "custom":
            pass
        else:
            logger.error("Provided cluster size: " + size + "is not supported, please provide one of: "
                                                                        "small/medium/large/extra-large/custom")
            d = {
                "responseType": "ERROR",
                "msg": "Provided cluster size: " + size + "is not supported, please provide one of: "
                                                        "small/medium/large/extra-large/custom",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if size.lower() == "small":
            cpu = Sizing.small['CPU']
            memory = Sizing.small['MEMORY']
            disk = Sizing.small['DISK']
        elif size.lower() == "medium":
            cpu = Sizing.medium['CPU']
            memory = Sizing.medium['MEMORY']
            disk = Sizing.medium['DISK']
        elif size.lower() == "large":
            cpu = Sizing.large['CPU']
            memory = Sizing.large['MEMORY']
            disk = Sizing.large['DISK']
        elif size.lower() == "extra-large":
            cpu = Sizing.extraLarge['CPU']
            memory = Sizing.extraLarge['MEMORY']
            disk = Sizing.extraLarge['DISK']
        elif size.lower() == "custom":
            if self.env == Env.VCF:
                cpu = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceCpuSize']
                disk = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceStorageSize']
                control_plane_mem_gb = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceMemorySize']
                memory = str(int(control_plane_mem_gb) * 1024)
            else:
                cpu = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceCpuSize']
                disk = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceStorageSize']
                control_plane_mem_gb = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceMemorySize']
                memory = str(int(control_plane_mem_gb) * 1024)
        else:
            logger.error("Provided cluster size: " + size + "is not supported, please provide one of: "
                                                                        "small/medium/large/extra-large/custom")
            d = {
                "responseType": "ERROR",
                "msg": "Provided cluster size: " + size + "is not supported, please provide one of: "
                                                        "small/medium/large/extra-large/custom",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if self.env == Env.VCF:
            shared_service_network = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceNetworkName']
        else:
            shared_service_network = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgMgmtNetworkName']

        vsphere_password = password
        _base64_bytes = vsphere_password.encode('ascii')
        _enc_bytes = base64.b64encode(_base64_bytes)
        vsphere_password = _enc_bytes.decode('ascii')
        datacenter_path = "/" + data_center
        datastore_path = datacenter_path + "/datastore/" + data_store
        shared_folder_path = datacenter_path + "/vm/" + ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE
        if parent_resourcePool:
            shared_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + parent_resourcePool + "/" + ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER
        else:
            shared_resource_path = datacenter_path + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER
        shared_network_path = getNetworkFolder(shared_service_network, vcenter_ip, vcenter_username, password)
        if not shared_network_path:
            logger.error("Network folder not found for " + shared_service_network)
            d = {
                "responseType": "ERROR",
                "msg": "Network folder not found for " + shared_service_network,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        if not createClusterFolder(shared_cluster_name):
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + shared_cluster_name,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        logger.info("The config files for shared services cluster will be located at: " + Paths.CLUSTER_PATH + shared_cluster_name)
        if Tkg_version.TKG_VERSION == "1.5" and checkTmcEnabled(self.jsonspec, self.env):
            if self.env == Env.VCF:
                clusterGroup = self.jsonspec['tkgComponentSpec']["tkgSharedserviceSpec"]['tkgSharedserviceClusterGroupName']
            else:
                clusterGroup = self.jsonspec['tkgComponentSpec']["tkgMgmtComponents"]['tkgSharedserviceClusterGroupName']

            if not clusterGroup:
                clusterGroup = "default"
            commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]
            kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
            if kubeContextCommand is None:
                logger.error("Failed to get switch to management cluster context command")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to management cluster context command",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
            status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
            if status[1] != 0:
                logger.error("Failed to get switch to management cluster context " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to management cluster context " + str(status[0]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            version_status = getKubeVersionFullName(kubernetes_ova_version)
            if version_status[0] is None:
                logger.error("Kubernetes OVA Version is not found for Shared Service Cluster")
                d = {
                    "responseType": "ERROR",
                    "msg": "Kubernetes OVA Version is not found for Shared Service Cluster",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            else:
                version = version_status[0]
            shared_network_folder_path = getNetworkPathTMC(shared_service_network, vcenter_ip, vcenter_username, password)
            if checkSharedServiceProxyEnabled(self.env, self.jsonspec) and not checkTmcRegister(shared_cluster_name, False):
                proxy_name_state = createProxyCredentialsTMC(self.env, shared_cluster_name, "true", "shared", self.jsonspec, register=False)
                if proxy_name_state[1] != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": proxy_name_state[0],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                proxy_name = "arcas-" + shared_cluster_name + "-tmc-proxy"
                if cluster_plan.lower() == PLAN.PROD_PLAN:
                    createSharedCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", shared_cluster_name, "-m",
                                        management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                        "--ssh-key", ssh_key, "--version", version, "--datacenter", datacenter_path,
                                        "--datastore",
                                        datastore_path, "--folder", shared_folder_path, "--resource-pool",
                                        shared_resource_path,
                                        "--workspace-network", shared_network_folder_path, "--control-plane-cpu", cpu,
                                        "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                        "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                        disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                        "--service-cidr-blocks", service_cidr, "--high-availability", "--proxy-name",
                                        proxy_name]
                else:
                    createSharedCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", shared_cluster_name, "-m",
                                        management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                        "--ssh-key", ssh_key, "--version", version, "--datacenter", datacenter_path,
                                        "--datastore",
                                        datastore_path, "--folder", shared_folder_path, "--resource-pool",
                                        shared_resource_path,
                                        "--workspace-network", shared_network_folder_path, "--control-plane-cpu", cpu,
                                        "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                        "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                        disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                        "--service-cidr-blocks", service_cidr,"--proxy-name",
                                        proxy_name]
            else:
                if cluster_plan.lower() == PLAN.PROD_PLAN:
                    createSharedCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", shared_cluster_name, "-m",
                                        management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                        "--ssh-key", ssh_key, "--version", version, "--datacenter", datacenter_path,
                                        "--datastore",
                                        datastore_path, "--folder", shared_folder_path, "--resource-pool",
                                        shared_resource_path,
                                        "--workspace-network", shared_network_folder_path, "--control-plane-cpu", cpu,
                                        "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                        "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                        disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                        "--service-cidr-blocks", service_cidr, "--high-availability"]
                else:
                    createSharedCluster = ["tmc", "cluster", "create", "-t", "tkg-vsphere", "-n", shared_cluster_name, "-m",
                                        management_cluster, "-p", "default", "--cluster-group", clusterGroup,
                                        "--ssh-key", ssh_key, "--version", version, "--datacenter", datacenter_path,
                                        "--datastore",
                                        datastore_path, "--folder", shared_folder_path, "--resource-pool",
                                        shared_resource_path,
                                        "--workspace-network", shared_network_folder_path, "--control-plane-cpu", cpu,
                                        "--control-plane-disk-gib", disk, "--control-plane-memory-mib", memory,
                                        "--worker-node-count", machineCount, "--worker-cpu", cpu, "--worker-disk-gib",
                                        disk, "--worker-memory-mib", memory, "--pods-cidr-blocks", pod_cidr,
                                        "--service-cidr-blocks", service_cidr]
        isCheck = False
        if command_status[0] is None:
            if Tkg_version.TKG_VERSION == "1.5" and checkTmcEnabled(self.jsonspec, self.env):
                logger.info("Creating AkoDeploymentConfig for shared services cluster")
                ako_deployment_config_status = self.akoDeploymentConfigSharedCluster(shared_cluster_name, aviVersion)
                if ako_deployment_config_status[1] != 200:
                    logger.info("Failed to create AKO Deployment Config for shared services cluster")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": ako_deployment_config_status[0].json['msg'],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                logger.info("Deploying shared cluster...")
                command_status = runShellCommandAndReturnOutputAsList(createSharedCluster)
                if command_status[1] != 0:
                    logger.error("Failed to run command to create shared cluster " + str(command_status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run command to create shared cluster " + str(command_status[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                else:
                    logger.info("Shared cluster is successfully deployed and running " + command_status[0])
        else:
            if not verifyPodsAreRunning(shared_cluster_name, command_status[0], RegexPattern.running):
                isCheck = True
                if not checkTmcEnabled(self.jsonspec, self.env):
                    logger.info("Creating AkoDeploymentConfig for shared services cluster")
                    ako_deployment_config_status = self.akoDeploymentConfigSharedCluster(shared_cluster_name, aviVersion)
                    if ako_deployment_config_status[1] != 200:
                        logger.info("Failed to create AKO Deployment Config for shared services cluster")
                        d = {
                            "responseType": "SUCCESS",
                            "msg": ako_deployment_config_status[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    logger.info("Deploying shared cluster using tanzu 1.5")
                    deploy_status = deployCluster(shared_cluster_name, cluster_plan,
                                      data_center, data_store, shared_folder_path,
                                      shared_network_path,
                                      vsphere_password, shared_resource_path, vcenter_ip,
                                      ssh_key, vcenter_username, machineCount, size,
                                      ClusterType.SHARED, vsSpec, self.jsonspec)


                    if deploy_status[0] is None:
                        logger.error("Failed to deploy cluster " + deploy_status[1])
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to deploy cluster " + deploy_status[1],
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                else:
                    if checkTmcEnabled(self.jsonspec, self.env):
                        logger.info("Creating AkoDeploymentConfig for shared services cluster")
                        ako_deployment_config_status = self.akoDeploymentConfigSharedCluster(shared_cluster_name, aviVersion)
                        if ako_deployment_config_status[1] != 200:
                            logger.info("Failed to create AKO Deployment Config for shared services cluster")
                            d = {
                                "responseType": "SUCCESS",
                                "msg": ako_deployment_config_status[0].json['msg'],
                                "ERROR_CODE": 500
                            }
                            return json.dumps(d), 500
                        logger.info("Deploying shared cluster, after verification using tmc")
                        command_status_v = runShellCommandAndReturnOutputAsList(createSharedCluster)
                        if command_status_v[1] != 0:
                            if str(command_status_v[0]).__contains__("DeadlineExceeded"):
                                logger.error(
                                    "Failed to run command to create shared cluster check tmc management cluster is not in disconnected state " + str(
                                        command_status_v[0]))
                            else:
                                logger.info("Waiting for folders to be available in tmc…")
                                for i in tqdm(range(150), desc="Waiting for folders to be available in tmc…", ascii=False,
                                            ncols=75):
                                    time.sleep(1)
                                command_status_v = runShellCommandAndReturnOutputAsList(createSharedCluster)
                                if command_status_v[1] != 0:
                                    logger.error(
                                        "Failed to run command to create shared cluster " + str(command_status_v[0]))
                                    d = {
                                        "responseType": "ERROR",
                                        "msg": "Failed to run command to create shared cluster " + str(command_status_v[0]),
                                        "ERROR_CODE": 500
                                    }
                                    return json.dumps(d), 500
                count = 0
                if isCheck:
                    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
                    if command_status[1] != 0:
                        logger.error("Failed to check pods are running " + str(command_status[0]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to check pods are running " + str(command_status[0]),
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    while not verifyPodsAreRunning(shared_cluster_name, command_status[0],
                                                RegexPattern.running) and count < 60:
                        command_status = runShellCommandAndReturnOutputAsList(podRunninng)
                        if command_status[1] != 0:
                            logger.error("Failed to check pods are running " + str(command_status[0]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to check pods are running " + str(command_status[0]),
                                "ERROR_CODE": 500
                            }
                            return json.dumps(d), 500
                        count = count + 1
                        time.sleep(30)
                        logger.info("Waited for  " + str(count * 30) + "s, retrying.")
                if not verifyPodsAreRunning(shared_cluster_name, command_status[0], RegexPattern.running):
                    logger.error(shared_cluster_name + " is not running on waiting " + str(count * 30) + "s")
                    d = {
                        "responseType": "ERROR",
                        "msg": shared_cluster_name + " is not running on waiting " + str(count * 30) + "s",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]
                kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
                if kubeContextCommand is None:
                    logger.error("Failed to get switch to management cluster context command")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get switch to management cluster context command",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
                status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
                if status[1] != 0:
                    logger.error("Failed to get switch to management cluster context " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get switch to management cluster context " + str(status[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                lisOfCommand = ["kubectl", "label", "cluster.cluster.x-k8s.io/" + shared_cluster_name,
                                "cluster-role.tkg.tanzu.vmware.com/tanzu-services=""", "--overwrite=true"]
                status = runShellCommandAndReturnOutputAsList(lisOfCommand)
                if status[1] != 0:
                    logger.error("Failed to apply k8s label " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to apply k8s label " + str(status[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                lisOfCommand = ["kubectl", "label", "cluster",
                                shared_cluster_name, AkoType.KEY + "=" + AkoType.SHARED_CLUSTER_SELECTOR, "--overwrite=true"]
                status = runShellCommandAndReturnOutputAsList(lisOfCommand)
                if status[1] != 0:
                    if not str(status[0]).__contains__("already has a value"):
                        logger.error("Failed to apply ako label " + str(status[0]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to apply ako label " + str(status[0]),
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                else:
                    logger.info(status[0])
                commands_shared = ["tanzu", "cluster", "kubeconfig", "get", shared_cluster_name, "--admin"]
                kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
                if kubeContextCommand_shared is None:
                    logger.error("Failed to get switch to shared cluster context command")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get switch to shared cluster context command",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
                status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
                if status[1] != 0:
                    logger.error("Failed to get switch to shared cluster context " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get switch to shared cluster context " + str(status[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                logger.info("Switched to " + shared_cluster_name + " context")
                if checkEnableIdentityManagement(self.env, self.jsonspec):
                    logger.info("Validating pinniped installation status")
                    check_pinniped = checkPinnipedInstalled()
                    if check_pinniped[1] != 200:
                        logger.error(check_pinniped[0].json['msg'])
                        d = {
                            "responseType": "ERROR",
                            "msg": check_pinniped[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    if self.env == Env.VSPHERE:
                        cluster_admin_users = \
                            self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                                'tkgSharedserviceRbacUserRoleSpec'][
                                'clusterAdminUsers']
                        admin_users = \
                            self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                                'tkgSharedserviceRbacUserRoleSpec'][
                                'adminUsers']
                        edit_users = \
                            self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                                'tkgSharedserviceRbacUserRoleSpec'][
                                'editUsers']
                        view_users = \
                            self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                                'tkgSharedserviceRbacUserRoleSpec'][
                                'viewUsers']
                    elif self.env == Env.VCF:
                        cluster_admin_users = \
                            self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                                'tkgSharedserviceRbacUserRoleSpec'][
                                'clusterAdminUsers']
                        admin_users = \
                            self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                                'tkgSharedserviceRbacUserRoleSpec'][
                                'adminUsers']
                        edit_users = \
                            self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                                'tkgSharedserviceRbacUserRoleSpec'][
                                'editUsers']
                        view_users = \
                            self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                                'tkgSharedserviceRbacUserRoleSpec'][
                                'viewUsers']
                    rbac_user_status = createRbacUsers(shared_cluster_name, isMgmt=False, env=self.env, edit_users=edit_users,
                                                    cluster_admin_users=cluster_admin_users, admin_users=admin_users,
                                                    view_users=view_users)
                    if rbac_user_status[1] != 200:
                        logger.error(rbac_user_status[0].json['msg'])
                        d = {
                            "responseType": "ERROR",
                            "msg": rbac_user_status[0].json['msg'],
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    logger.info("Successfully created RBAC for all the provided users")
                else:
                    logger.info("Identity Management is not enabled")

                logger.info("Verifying if AKO pods are running...")
                podRunninng_ako_main = ["kubectl", "get", "pods", "-n", "avi-system"]
                podRunninng_ako_grep = ["grep", "ako-0"]
                command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
                count_ako = 0
                found = False
                if verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING):
                    found = True
                while not verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING) and count_ako < 20:
                    command_status = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
                    if verifyPodsAreRunning(AppName.AKO, command_status[0], RegexPattern.RUNNING):
                        found = True
                        break
                    count_ako = count_ako + 1
                    time.sleep(30)
                    logger.info("Waited for  " + str(count_ako * 30) + "s, retrying.")
                if not found:
                    logger.error("Ako pods are not running on waiting " + str(count_ako * 30))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Ako pods are not running on waiting " + str(count_ako * 30),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                if count_ako > 30:
                    for i in tqdm(range(60), desc="Waiting for ako pods to be uup…", ascii=False, ncols=75):
                        time.sleep(1)
            else:
                logger.info(shared_cluster_name + " cluster is already deployed and running ")
        if tmc_flag and (Tkg_version.TKG_VERSION != "1.5"):
            isSharedProxy = "false"
            if checkSharedServiceProxyEnabled(self.env, self.jsonspec):
                isSharedProxy = "true"
            state = registerWithTmcOnSharedAndWorkload(self.jsonspec, shared_cluster_name, "shared")
            if state[1] != 200:
                logger.error(state[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": state[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        elif checkTmcEnabled(self.jsonspec, self.env) and Tkg_version.TKG_VERSION == "1.5":
            logger.info("Cluster is already deployed via TMC")
            if checkDataProtectionEnabled(self.jsonspec, "shared", isEnvTkgs_ns):
                is_enabled = enable_data_protection(self.jsonspec, shared_cluster_name, management_cluster, isEnvTkgs_ns)
                if not is_enabled[0]:
                    logger.error(is_enabled[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": is_enabled[1],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                logger.info(is_enabled[1])
            else:
                logger.info("Data protection not enabled for cluster " + shared_cluster_name)
        elif checkTmcEnabled(self.jsonspec, self.env):
            logger.info("Cluster is already deployed via TMC")
        else:
            logger.info("TMC is disabled")
        to = registerTanzuObservability(shared_cluster_name, size, self.jsonspec)
        if to[1] != 200:
            logger.error(to[0].json['msg'])
            return to[0], to[1]
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully deployed  cluster " + shared_cluster_name,
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200


    def waitForGrepProcess(self,list1, list2, podName, dir):
            cert_state = grabPipeOutputChagedDir(list1, list2, dir)
            if cert_state[1] != 0:
                logger.error("Failed to apply " + podName + " " + cert_state[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply " + podName + " " + cert_state[0],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500, 0
            count_cert = 0
            while verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING) and count_cert < 10:
                cert_state = grabPipeOutputChagedDir(list1, list2, dir)
                time.sleep(30)
                count_cert = count_cert + 1
                logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
            if not verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING):
                logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
                d = {
                    "responseType": "ERROR",
                    "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500, count_cert
            d = {
                "responseType": "ERROR",
                "msg": "Failed to apply " + podName + " " + cert_state[0],
                "ERROR_CODE": 500
            }

            return json.dumps(d), 200, count_cert


    def changeNetworks(self,vcenter_ip, vcenter_username, password, engine_name):
            os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
            os.putenv("GOVC_USERNAME", vcenter_username)
            os.putenv("GOVC_PASSWORD", password)
            os.putenv("GOVC_INSECURE", "true")
            change_VM_Net = ["govc", "vm.network.change", "-vm=" + engine_name, "-net", SegmentsName.DISPLAY_NAME_TKG_WORKLOAD,
                            "ethernet-2"]
            connect_VM_Net = ["govc", "device.connect", "-vm=" + engine_name, "ethernet-2"]
            try:
                runShellCommandWithPolling(change_VM_Net)
                runShellCommandWithPolling(connect_VM_Net)
            except Exception as e:
                return str(e), 500
            return "SUCCEES", 200


    def waitForProcess(self,list1, podName):
            cert_state = runShellCommandAndReturnOutputAsList(list1)
            if cert_state[1] != 0:
                logger.error("Failed to apply " + podName + " " + cert_state[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply " + podName + " " + cert_state[0],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500, 0
            count_cert = 0
            while verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING) and count_cert < 50:
                cert_state = runShellCommandAndReturnOutputAsList(list1)
                time.sleep(30)
                count_cert = count_cert + 1
                logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
            if not verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RECONCILE_SUCCEEDED):
                logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
                d = {
                    "responseType": "ERROR",
                    "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500, count_cert
            d = {
                "responseType": "ERROR",
                "msg": "Failed to apply " + podName + " " + cert_state[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 200, count_cert
