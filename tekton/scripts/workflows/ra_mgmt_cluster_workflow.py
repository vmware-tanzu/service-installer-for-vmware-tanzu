#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path
from re import sub
import re
import json
import time
from jinja2 import Template
import requests
from tqdm import tqdm
import base64
from constants.constants import Constants, Paths, TKGCommands, ComponentPrefix, AkoType, Env, \
    ControllerLocation, KubernetesOva, Cloud, VrfType, ResourcePoolAndFolderName, RegexPattern, CertName, Avi_Version,\
    Avi_Tkgs_Version, ServiceName, Tkg_version, SePrefixName
from constants.alb_api_constants import AlbEndpoint, AlbPayload
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from model.spec import Bootstrap
from model.vsphereSpec import VsphereMasterSpec
from model.status import HealthEnum, Info
from util.cmd_helper import CmdHelper
from util.file_helper import FileHelper
from util.git_helper import Git
from util.govc_helper import get_alb_ip_address
from util.logger_helper import LoggerHelper, log
from util.avi_api_helper import isAviHaEnabled, obtain_avi_version
from util.ssh_helper import SshHelper
from util.ssl_helper import get_base64_cert
from util.tanzu_utils import TanzuUtils
from workflows.cluster_common_workflow import ClusterCommonWorkflow
import subprocess
import shutil
import traceback
from common.certificate_base64 import getBase64CertWriteToFile
from util.common_utils import downloadAndPushKubernetesOvaMarketPlace, \
    getCloudStatus, seperateNetmaskAndIp, getSECloudStatus, getSeNewBody, getVrfAndNextRoutId, \
    addStaticRoute, getVipNetworkIpNetMask, getClusterStatusOnTanzu, runSsh, checkenv, \
    switchToManagementContext, getClusterID, getPolicyID, envCheck, checkAirGappedIsEnabled, \
    convertStringToCommaSeperated, cidr_to_netmask, getCountOfIpAdress, getLibraryId, getAviCertificate, \
    checkTmcEnabled, createSubscribedLibrary, checkAndWaitForAllTheServiceEngineIsUp, configureKubectl, \
    registerTMCTKGs,grabPortFromUrl, grabHostFromUrl, loadBomFile, checkMgmtProxyEnabled, registerWithTmc, \
    obtain_second_csrf, update_template_in_ova, getNetworkDetailsVip, create_virtual_service
from util.replace_value import generateVsphereConfiguredSubnets, replaceValueSysConfig, \
    generateVsphereConfiguredSubnetsForSe
from util.vcenter_operations import createResourcePool, create_folder, getDvPortGroupId, checkforIpAddress, getSi
from util.ShellHelper import runProcess, runShellCommandAndReturnOutputAsList, verifyPodsAreRunning, grabKubectlCommand
from util.oidc_helper import checkEnableIdentityManagement, checkPinnipedInstalled, checkPinnipedServiceStatus, \
    checkPinnipedDexServiceStatus, createRbacUsers
from util.tkg_util import TkgUtil
from util.cleanup_util import CleanUpUtil
from constants.nsxt_constants import NSXtCloud
from lib.nsxt_client import NsxtClient


# logger = LoggerHelper.get_logger(Path(__file__).stem)
logger = LoggerHelper.get_logger(name='ra_mgmt_cluster_workflow')


class RaMgmtClusterWorkflow:
    def __init__(self, run_config: RunConfig):
        self.run_config = run_config
        logger.info ("Current deployment state: %s", self.run_config.state)
        self.tkg_util_obj = TkgUtil(run_config=self.run_config)
        self.tkg_version_dict = self.tkg_util_obj.get_desired_state_tkg_version()
        if "tkgs" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_WCP_MASTER_SPEC_PATH)
        elif "tkgm" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        else:
            raise Exception(f"Could not find supported TKG version: {self.tkg_version_dict}")

        self.cleanup_obj = CleanUpUtil()

        with open(self.jsonpath) as f:
            self.jsonspec = json.load(f)
        self.env = envCheck(self.run_config)
        if self.env[1] != 200:
            logger.error("Wrong env provided " + self.env[0])
            d = {
                "responseType": "ERROR",
                "msg": "Wrong env provided " + self.env[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        self.env = self.env[0]
        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)
        self.isEnvTkgs_wcp = TkgUtil.isEnvTkgs_wcp(self.jsonspec)
        self.isEnvTkgs_ns = TkgUtil.isEnvTkgs_ns(self.jsonspec)
        self.harbor_url = self.run_config.user_cred.harbor_url
        if checkAirGappedIsEnabled(self.jsonspec) and self.harbor_url == "":
            msg = "Harbor url is not provided"
            raise Exception(msg)
        self.get_vcenter_details()
        self.nsxtObj = NsxtClient(self.run_config)

    def get_vcenter_details(self):
        """
        Method to get vCenter Details from JSON file
        :return:
        """
        self.vcenter_dict = {}
        try:
            self.vcenter_dict.update({'vcenter_ip': self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress'],
                                      'vcenter_password': CmdHelper.decode_base64(
                                          self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']),
                                      'vcenter_username': self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser'],
                                      'vcenter_cluster_name': self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster'],
                                      'vcenter_datacenter': self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter'],
                                      'vcenter_data_store': self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
                                      })
        except KeyError as e:
            logger.warning(f"Field  {e} not configured in vcenterDetails")
            pass

    @log("Preparing to deploy Management cluster")
    def create_mgmt_cluster(self):
        try:
            config_cloud = self.configCloud()
            if config_cloud[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to Config management cluster ",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if not self.isEnvTkgs_wcp:
                try:
                    config_mgmt = self.configTkgMgmt()
                    if config_mgmt[1] != 200:
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to Config management cluster ",
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Management cluster configured Successfully",
                        "ERROR_CODE": 200
                    }
                    logger.info("Management cluster configured Successfully")
                    return json.dumps(d), 200
                except Exception as e:
                    logger.error(f"ERROR: Failed to create MGMT cluster: {e}")
                    self.mgmt_cluster_name = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                        'tkgMgmtClusterName']
                    self.cleanup_obj.delete_mgmt_cluster(self.mgmt_cluster_name)
            else:
                logger.info("Management cluster not required for TKGs")
                return True, 200
        except Exception as e:
            logger.error(f"ERROR: Failed to create MGMT cluster: {e}")
            if not self.isEnvTkgs_wcp or not self.isEnvTkgs_ns:
                self.mgmt_cluster_name = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
                self.cleanup_obj.delete_mgmt_cluster(self.mgmt_cluster_name)

    @log("Template yaml deployment of management cluster in progress...")
    def templateMgmtDeployYaml(self, ip, datacenter, avi_version, data_store, cluster_name, wpName, wipIpNetmask,
                               vcenter_ip,
                               vcenter_username,
                               password, vsSpec):
        tkg_cluster_vip_network_name = self.jsonspec['tkgComponentSpec']['tkgClusterVipNetwork'][
            'tkgClusterVipNetworkName']
        cluster_vip_cidr = self.jsonspec['tkgComponentSpec']['tkgClusterVipNetwork'][
            'tkgClusterVipNetworkGatewayCidr']
        mgmt_group_name = Cloud.SE_GROUP_NAME_VSPHERE
        workload_group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
        tier1_path = ""
        if self.env == Env.VCF:
            mgmt_group_name = Cloud.SE_GROUP_NAME_VSPHERE.replace("vsphere","nsxt")
            workload_group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere","nsxt")
            if self.isEnvTkgs_wcp:
                avienc_pass = str(self.jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
            else:
                avienc_pass = str(self.jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
            csrf2 = obtain_second_csrf(ip, avienc_pass)
            if csrf2 is None:
                logger.error("Failed to get csrf from new set password")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get csrf from new set password",
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Cookie": csrf2[1],
                "referer": "https://" + ip + "/login",
                "x-avi-version": avi_version,
                "x-csrftoken": csrf2[0]
            }
            status, value = self.nsxtObj.getCloudConnectUser(ip, headers)
            nsxt_cred = value["nsxUUid"]
            tier1_id, status_tier1 = self.nsxtObj.fetchTier1GatewayId(ip, headers, nsxt_cred)
            if tier1_id is None:
                logger.error("Failed to get Tier 1 details " + str(status_tier1))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Tier 1 details " + str(status_tier1),
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500
            tier1_path = status_tier1
        deploy_yaml = FileHelper.read_resource(Paths.TKG_MGMT_SPEC_J2)
        t = Template(deploy_yaml)
        datastore_path = "/" + datacenter + "/datastore/" + data_store
        vsphere_folder_path = "/" + datacenter + "/vm/" + \
                              ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE
        str_enc = str(password)
        _base64_bytes = str_enc.encode('ascii')
        _enc_bytes = base64.b64encode(_base64_bytes)
        vcenter_passwd = _enc_bytes.decode('ascii')
        management_cluster = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
        parent_resourcePool = vsSpec.envSpec.vcenterDetails.resourcePoolName
        if parent_resourcePool:
            vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + \
                         parent_resourcePool + "/" + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
        else:
            vsphere_rp = "/" + datacenter + "/host/" + cluster_name + "/Resources/" + \
                         ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
        datacenter = "/" + datacenter
        ssh_key = runSsh(vcenter_username)
        size = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtSize
        control_plane_vcpu = ""
        control_plane_disk_gb = ""
        control_plane_mem_gb = ""
        control_plane_mem_mb = ""
        proxyCert = ""
        try:
            proxyCert_raw = self.jsonspec['envSpec']['proxySpec']['tkgMgmt']['proxyCert']
            base64_bytes = base64.b64encode(proxyCert_raw.encode("utf-8"))
            proxyCert = str(base64_bytes, "utf-8")
            isProxy = "true"
        except:
            isProxy = "false"
            logger.info("Proxy certificate for  Management is not provided")
        ciep = self.jsonspec['envSpec']["ceipParticipation"]
        if size.lower() == "medium":
            pass
        elif size.lower() == "large":
            pass
        elif size.lower() == "extra-large":
            pass
        elif size.lower() == "custom":
            control_plane_vcpu = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtCpuSize']
            control_plane_disk_gb = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtStorageSize']
            control_plane_mem_gb = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtMemorySize']
            control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
        else:
            logger.error(
                "Un supported cluster size please specify medium/large/extra-large/custom " + size)
            d = {
                "responseType": "ERROR",
                "msg": "Un supported cluster size please specify medium/large/extra-large/custom " + size,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        try:
            osName = str(self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtBaseOs'])
            if osName == "photon":
                osVersion = "3"
            elif osName == "ubuntu":
                osVersion = "20.04"
            else:
                raise Exception("Wrong os name provided")
        except Exception as e:
            raise Exception("Keyword " + str(e) + "  not found in input file")
        with open("vip_ip.txt", "r") as e:
            vip_ip = e.read()
        avi_cluster_vip_network_gateway_cidr  = vip_ip
        tkg_cluster_vip_network_cidr = vip_ip
        avi_version = Avi_Tkgs_Version.VSPHERE_AVI_VERSION if TkgUtil.isEnvTkgs_wcp(self.jsonspec) else Avi_Version.VSPHERE_AVI_VERSION
        air_gapped_repo = ""
        repo_certificate = ""
        if checkAirGappedIsEnabled(self.jsonspec):
                air_gapped_repo = vsSpec.envSpec.customRepositorySpec.tkgCustomImageRepository
                air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
                bom_image_cmd = ["tanzu", "config", "set", "env.TKG_BOM_IMAGE_TAG", Tkg_version.TAG]
                custom_image_cmd = ["tanzu", "config", "set", "env.TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo]
                custom_image_skip_tls_cmd = ["tanzu", "config", "set", "env.TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False"]
                runProcess(bom_image_cmd)
                runProcess(custom_image_cmd)
                runProcess(custom_image_skip_tls_cmd)
                getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
                with open('cert.txt', 'r') as file2:
                    repo_cert = file2.readline()
                repo_certificate = repo_cert
                tkg_custom_image_repo = ["tanzu", "config", "set", "env.TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate]
                runProcess(tkg_custom_image_repo)

        FileHelper.write_to_file(
            t.render(config=vsSpec, avi_cert=get_base64_cert(ip), ip=ip, wpName=wpName, wipIpNetmask=wipIpNetmask,
                     avi_label_key=AkoType.KEY, avi_label_value=AkoType.VALUE, cluster_name=management_cluster,
                     data_center=datacenter, datastore_path=datastore_path, ceip=ciep, isProxyCert=isProxy,
                     proxyCert=proxyCert,
                     vsphere_folder_path=vsphere_folder_path, vcenter_passwd=vcenter_passwd, vsphere_rp=vsphere_rp,
                     vcenter_ip=vcenter_ip, ssh_key=ssh_key, vcenter_username=vcenter_username,
                     size_controlplane=size.lower(), size_worker=size.lower(),
                     avi_version=avi_version, tier1_path=tier1_path, vip_cidr=cluster_vip_cidr,
                     tkg_cluster_vip_network_name=tkg_cluster_vip_network_name,
                     management_group=mgmt_group_name, workload_group=workload_group_name,
                     tkg_cluster_vip_network_cidr=tkg_cluster_vip_network_cidr,
                     air_gapped_repo=air_gapped_repo, repo_certificate=repo_certificate, osName=osName,
                     osVersion=osVersion, env = self.env,
                     size=size, control_plane_vcpu=control_plane_vcpu, control_plane_disk_gb=control_plane_disk_gb,
                     control_plane_mem_mb=control_plane_mem_mb), "management_cluster_vsphere.yaml")

    @log("Executing management cluster deployment...")
    def deployManagementCluster(self, management_cluster, ip, data_center, data_store, cluster_name,
                                wpName, wipIpNetmask, vcenter_ip, vcenter_username, aviVersion, password,
                                vsSpec):
        try:
            logger.info('Getting cluster state if any previous clusters are  deployed..')
            if not getClusterStatusOnTanzu(management_cluster, "management"):
                os.system("rm -rf kubeconfig.yaml")
                self.templateMgmtDeployYaml(ip, data_center, aviVersion, data_store, cluster_name, wpName,
                                            wipIpNetmask, vcenter_ip, vcenter_username, password,
                                            vsSpec)

                logger.info("Deploying management cluster")
                os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
                listOfCmd = ["tanzu", "management-cluster", "create", "-y", "--file",
                             "management_cluster_vsphere.yaml",
                             "-v",
                             "6"]

                if checkAirGappedIsEnabled(self.jsonspec):
                    dckr_pull_cmd = ["docker", "pull",
                                 self.harbor_url+"/tekton_dep/kindest/node@sha256:f97edf7f7ed53c57762b24f90a34fad101386c5bd4d93baeb45449557148c717"]
                    runProcess(dckr_pull_cmd)

                    # Updating kind YAML file with HARBOR URL
                    with open(Paths.TMP_KIND_YAML_PATH, "r") as fp:
                        content = fp.read()
                    content = re.sub("<HARBOR_URL>", self.harbor_url, content)
                    with open(Paths.TMP_KIND_YAML_PATH, 'w') as fp1:
                        fp1.write(content)

                    kind_create_cmd = ["kind", "create", "cluster", "--config", Paths.TMP_KIND_YAML_PATH]
                    runProcess(kind_create_cmd)
                    listOfCmd = ["tanzu", "management-cluster", "create", "-y", "--file",
                             "management_cluster_vsphere.yaml", "--use-existing-bootstrap-cluster", "tkg-kind",
                             "-v",
                             "6"]
                runProcess(listOfCmd)
                listOfCmdKube = ["tanzu", "management-cluster", "kubeconfig", "get",
                                 management_cluster, "--admin",
                                 "--export-file",
                                 "kubeconfig.yaml"]
                runProcess(listOfCmdKube)
                return "SUCCESS", 200
            else:
                return "SUCCESS", 200
        except Exception as e:
            logger.info(traceback.format_exc())
            return None, str(e)

    @log("Creating TKGM management cluster")
    def configTkgMgmt(self):

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
        parent_resourcepool = self.jsonspec['envSpec']['vcenterDetails']['resourcePoolName']
        try:
            isCreated5 = createResourcePool(vcenter_ip, vcenter_username, password,
                                            cluster_name,
                                            ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE,
                                            parent_resourcepool)
            if isCreated5 is not None:
                logger.info("Created resource pool " +
                            ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE)
        except Exception as e:
            logger.error("Failed to create resource pool " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create resource pool " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        try:
            isCreated3 = create_folder(vcenter_ip, vcenter_username, password, data_center,
                                       ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)
            if isCreated3 is not None:
                logger.info("Created folder " +
                            ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)

        except Exception as e:
            logger.error("Failed to create folder " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create folder " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
        ha_field = self.jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
        if isAviHaEnabled(ha_field):
            ip = self.jsonspec['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
        else:
            ip = avi_fqdn
        if ip is None:
            logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if self.isEnvTkgs_wcp:
            avienc_pass = str(self.jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
        else:
            avienc_pass = str(self.jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
        csrf2 = obtain_second_csrf(ip, avienc_pass)
        if csrf2 is None:
            logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if self.env == Env.VSPHERE:
            data_network = self.jsonspec["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkName"]
        else:
            data_network =  self.jsonspec['tkgComponentSpec']['tkgClusterVipNetwork'][
            'tkgClusterVipNetworkName']
        get_wip = getVipNetworkIpNetMask(ip, csrf2, data_network, aviVersion)
        if get_wip[0] is None or get_wip[0] == "NOT_FOUND":
            logger.error("Failed to get se vip network ip and netmask " + str(get_wip[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get vip network " + str(get_wip[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        management_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtClusterName']
        avi_ip = self.jsonspec['tkgComponentSpec']['aviComponents'][
            'aviController01Ip']
        avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents'][
            'aviController01Fqdn']
        if not avi_ip:
            controller_fqdn = ip
        elif not avi_fqdn:
            controller_fqdn = avi_fqdn
        else:
            controller_fqdn = ip
        logger.info("Deploying Management Cluster " + management_cluster)
        deploy_status = self.deployManagementCluster(management_cluster, controller_fqdn,
                                                     data_center, data_store, cluster_name,
                                                     data_network, get_wip[0], vcenter_ip,
                                                     vcenter_username, aviVersion, password, vsSpec)
        if deploy_status[0] is None:
            logger.error("Failed to deploy management cluster " + deploy_status[1])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy management cluster " + deploy_status[1],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        command = ["tanzu", "plugin", "sync"]
        runShellCommandAndReturnOutputAsList(command)
        if checkEnableIdentityManagement(self.env, self.jsonspec):
            podRunninng = ["tanzu", "cluster", "list", "--include-management-cluster", "-A"]
            command_status = runShellCommandAndReturnOutputAsList(podRunninng)
            if not verifyPodsAreRunning(management_cluster, command_status[0], RegexPattern.running):
                logger.error(management_cluster + " is not deployed")
                d = {
                    "responseType": "ERROR",
                    "msg": management_cluster + " is not deployed",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            switch = switchToManagementContext(management_cluster)
            if switch[1] != 200:
                logger.info(switch[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": switch[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
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
                logger.info("Validating pinniped service status")
                check_pinniped_svc = checkPinnipedServiceStatus()
                if check_pinniped_svc[1] != 200:
                    logger.error(check_pinniped_svc[0])
                    d = {
                        "responseType": "ERROR",
                        "msg": check_pinniped_svc[0],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                logger.info("Successfully validated Pinniped service status")
                identity_mgmt_type = str(
                    self.jsonspec["tkgComponentSpec"]["identityManagementSpec"]["identityManagementType"])
                if identity_mgmt_type.lower() == "ldap":
                    check_pinniped_dexsvc = checkPinnipedDexServiceStatus()
                    if check_pinniped_dexsvc[1] != 200:
                        logger.error(check_pinniped_dexsvc[0])
                        d = {
                            "responseType": "ERROR",
                            "msg": check_pinniped_dexsvc[0],
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    logger.info("External IP for Pinniped is set as: " + check_pinniped_svc[0])

                cluster_admin_users = \
                self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'][
                    'clusterAdminUsers']
                admin_users = \
                self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'][
                    'adminUsers']
                edit_users = \
                self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'][
                    'editUsers']
                view_users = \
                self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtRbacUserRoleSpec'][
                    'viewUsers']
                rbac_user_status = createRbacUsers(management_cluster, isMgmt=True, env=self.env, edit_users=edit_users,
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

        # there is check for if not airgap for tmc registration, moved it to else part of below if (sivt reference)
        if checkAirGappedIsEnabled(self.jsonspec):
            commands = ["tanzu", "management-cluster", "kubeconfig", "get", management_cluster, "--admin"]
            kubeContextCommand = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
            if kubeContextCommand is None:
                logger.error("Failed to get switch to management cluster context command")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get switch to management cluster context command",
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500
            lisOfSwitchContextCommand = str(kubeContextCommand).split(" ")
            status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand)
            if status[1] != 0:
                logger.error("Failed to switch to management cluster context " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to switch to management cluster context " + str(status[0]),
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500
            air_gapped_repo = str(
                self.jsonspec['envSpec']['customRepositorySpec']['tkgCustomImageRepository'])
            air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
            bom = loadBomFile()
            if bom is None:
                logger.error("Failed to load bom")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to load BOM",
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500
            try:
                tag = bom['components']['kube_rbac_proxy'][0]['images']['kubeRbacProxyControllerImage']['tag']
            except Exception as e:
                logger.error("Failed to load bom key " + str(e))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to load BOM key " + str(e),
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500
            kube = air_gapped_repo + "/kube-rbac-proxy:" + tag
            spec = "{\"spec\": {\"template\": {\"spec\": {\"containers\": [{\"name\": \"kube-rbac-proxy\",\"image\": \"" + kube + "\"}]}}}}"
            command = ["kubectl", "patch", "deployment", "ako-operator-controller-manager", "-n", "tkg-system-networking",
                    "--patch", spec]
            status = runShellCommandAndReturnOutputAsList(command)
            if status[1] != 0:
                logger.error("Failed to patch ako operator " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to patch ako operator " + str(status[0]),
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500
        else :
            if checkTmcEnabled(self.env):
                if Tkg_version.TKG_VERSION == "2.1":
                    logger.info("TMC registration on management cluster is supported on tanzu 1.5")
                    clusterGroup = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                        'tkgMgmtClusterGroupName']
                    if not clusterGroup:
                        clusterGroup = "default"
                    if checkMgmtProxyEnabled(self.env, self.jsonspec):
                        state = registerWithTmc(management_cluster, self.env, "true", "management", clusterGroup)
                    else:
                        state = registerWithTmc(management_cluster, self.env, "false", "management", clusterGroup)
                    if state[0] is None:
                        logger.error("Failed to register on tmc " + state[1])
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to register on TMC " + state[1],
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully configured management cluster ",
            "ERROR_CODE": 200
        }

        return json.dumps(d), 200

    @log("Wait for AVI Default Cloud to be in Ready State")
    def waitForCloudPlacementReady(self, ip, csrf2, name, aviVersion):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        url = "https://" + ip + "/api/cloud"
        body = {}
        response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        uuid = None
        for se in response_csrf.json()["results"]:
            if se["name"] == name:
                uuid = se["uuid"]
                break
        if uuid is None:
            return None, "Failed", "Error"
        status_url = "https://" + ip + "/api/cloud/" + uuid + "/status"
        count = 0
        response_csrf = None
        while count < 60:
            response_csrf = requests.request("GET", status_url, headers=headers, data=body,
                                             verify=False)
            if response_csrf.status_code != 200:
                return None, "Failed", "Error"
            try:
                logger.info(name + " cloud state " + response_csrf.json()["state"])
                if response_csrf.json()["state"] == "CLOUD_STATE_PLACEMENT_READY":
                    break
            except:
                pass
            count = count + 1
            time.sleep(10)
            logger.info("Waited for " + str(count * 10) + "s retrying")
        if response_csrf is None:
            logger.info("Waited for " + str(count * 10) + "s default cloud status")
            return None, "Failed", "ERROR"

        return "SUCCESS", "READY", response_csrf.json()["state"]

    @log("Creating mgmt cloud")
    def createNewCloud(self, ip, csrf2, aviVersion):
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {
            "name": Cloud.CLOUD_NAME_VSPHERE,
            "vtype": "CLOUD_VCENTER",
            "vcenter_configuration": {
                "privilege": "WRITE_ACCESS",
                "deactivate_vm_discovery": False,
                "vcenter_url": vcenter_ip,
                "username": vcenter_username,
                "password": password,
                "datacenter": data_center
            },
            "dhcp_enabled": False,
            "mtu": 1500,
            "prefer_static_routes": False,
            "enable_vip_static_routes": False,
            "state_based_dns_registration": True,
            "ip6_autocfg_enabled": False,
            "dns_resolution_on_se": False,
            "enable_vip_on_all_interfaces": False,
            "autoscale_polling_interval": 60,
            "vmc_deployment": False,
            "license_type": "LIC_CORES"
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/cloud"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            os.system("rm -rf newCloudInfo.json")
            with open("./newCloudInfo.json", "w") as outfile:
                json.dump(response_csrf.json(), outfile)
            return response_csrf.json()["url"], "SUCCESS"

    @log("Fetching Network url")
    def getNetworkUrl(self, ip, csrf2, name, aviVersion, cloudName=None):
        cloudName = Cloud.CLOUD_NAME_VSPHERE if cloudName is None else cloudName
        with open("./newCloudInfo.json", 'r') as file2:
            new_cloud_json = json.load(file2)
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except:
            env = envCheck(self.run_config)
            env = env[0]
            cloudName = Cloud.CLOUD_NAME_VSPHERE
            if env == Env.VCF:
                cloudName = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
            for re in new_cloud_json["results"]:
                if re["name"] == cloudName:
                    uuid = re["uuid"]
        if uuid is None:
            return None, "Failed", "ERROR"
        url = "https://" + ip + "/api/network-inventory/?cloud_ref.uuid=" + uuid
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}
        count = 0
        response_csrf = None
        try:
            while count < 60:
                response_csrf = requests.request("GET", url, headers=headers, data=payload,
                                                 verify=False)
                if response_csrf.status_code == 200:
                    if response_csrf.json()["count"] > 1:
                        break
                count = count + 1
                time.sleep(10)
                logger.info("Waited for " + str(count * 10) + "s retrying")
            if response_csrf is None:
                logger.info(
                    "Waited for " + str(count * 10) + "s but service engine is not up")
                return None, "Failed", "ERROR"
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            elif count >= 59:
                return None, "NOT_FOUND", "TIME_OUT"
            else:
                for se in response_csrf.json()["results"]:
                    if se["config"]["name"] == name:
                        return se["config"]["url"], se["config"]["uuid"], "FOUND", "SUCCESS"
                else:
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()[
                        "next"]
                    while len(next_url) > 0:
                        response_csrf = requests.request("GET", next_url, headers=headers,
                                                         data=payload, verify=False)
                        for se in response_csrf.json()["results"]:
                            if se["config"]["name"] == name:
                                return se["config"]["url"], se["config"]["uuid"], "FOUND", "SUCCESS"
                        next_url = None if not response_csrf.json()["next"] else \
                            response_csrf.json()["next"]
            return None, "NOT_FOUND", "Failed"
        except KeyError:
            return None, "NOT_FOUND", "Failed"

    @log("Fetching Network details")
    def getNetworkDetails(self, ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask,
                          aviVersion, isSeRequired=False):
        url = managementNetworkUrl
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        details = {}
        if response_csrf.status_code != 200:
            details["error"] = response_csrf.text
            return None, "Failed", details
        try:
            add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
            details["subnet_ip"] = add
            details["vim_ref"] = response_csrf.json()["vimgrnw_ref"]
            details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
            return "AlreadyConfigured", 200, details
        except Exception as e:
            logger.info("Ip pools are not configured.")

        os.system("rm -rf managementNetworkDetails.json")
        with open("./managementNetworkDetails.json", "w") as outfile:
            json.dump(response_csrf.json(), outfile)
        if isSeRequired:
            generateVsphereConfiguredSubnetsForSe("managementNetworkDetails.json", startIp, endIp, prefixIp,
                                                  int(netmask))
        else:
            generateVsphereConfiguredSubnets("managementNetworkDetails.json", startIp, endIp, prefixIp,
                                             int(netmask))
        return "SUCCESS", 200, details

    @log("Updating Network with IP Pools")
    def updateNetworkWithIpPools(self, ip, csrf2, managementNetworkUrl, fileName, aviVersion):
        with open(fileName, 'r') as openfile:
            json_object = json.load(openfile)
        json_object_m = json.dumps(json_object, indent=4)
        url = managementNetworkUrl
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        details = {}
        response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m,
                                         verify=False)
        if response_csrf.status_code != 200:
            count = 0
            if response_csrf.text.__contains__(
                    "Cannot edit network properties till network sync from Service Engines is complete"):
                while count < 10:
                    time.sleep(60)
                    response_csrf = requests.request("PUT", url, headers=headers,
                                                     data=json_object_m, verify=False)
                    if response_csrf.status_code == 200:
                        break
                    logger.info("waited for " + str(count * 60) + "s sync to complete")
                    count = count + 1
            else:
                return 500, response_csrf.text, details
        details["subnet_ip"] = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"][
            "addr"]
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        if self.env == Env.VSPHERE:
            details["vimref"] = response_csrf.json()["vimgrnw_ref"]
        return 200, "SUCCESS", details

    @log("Getting Details of New Cloud")
    def getDetailsOfNewCloud(self, ip, csrf2, newCloudUrl, vim_ref, captured_ip, captured_mask,
                             aviVersion):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}
        url = newCloudUrl
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            json_object = json.dumps(response_csrf.json(), indent=4)
            os.system("rm -rf detailsOfNewCloud.json")
            with open("./detailsOfNewCloud.json", "w") as outfile:
                outfile.write(json_object)
            replaceValueSysConfig("detailsOfNewCloud.json", "vcenter_configuration",
                                  "management_network", vim_ref)
            ip_val = dict(ip_addr=dict(addr=captured_ip, type="V4"), mask=captured_mask)
            replaceValueSysConfig("detailsOfNewCloud.json", "vcenter_configuration",
                                  "management_ip_subnet", ip_val)
            return response_csrf.json(), "SUCCESS"

    @log("Updating new cloud details...")
    def updateNewCloud(self, ip, csrf2, newCloudUrl, aviVersion):
        with open("./detailsOfNewCloud.json", 'r') as file2:
            new_cloud_json = json.load(file2)
        json_object = json.dumps(new_cloud_json, indent=4)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            return response_csrf.json(), "SUCCESS"



    def getNSXTNetworkDetailsVip(self, ip, csrf2, vipNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion):
        url = vipNetworkUrl
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        details = {}
        if response_csrf.status_code != 200:
            details["error"] = response_csrf.text
            return None, "Failed", details
        try:
            add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
            details["subnet_ip"] = add
            # vim_ref has been removed for NSX-T cloud
            details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
            return "AlreadyConfigured", 200, details
        except Exception as e:
            logger.info("Ip pools are not configured configuring it")
        # update attributes
        os.system("rm -rf vipNetworkDetails.json")
        with open("./vipNetworkDetails.json", "w") as outfile:
            json.dump(response_csrf.json(), outfile)
        with open("./vipNetworkDetails.json") as f:
            data = json.load(f)
        dic = dict(dhcp_enabled=False)
        data.update(dic)
        with open("./vipNetworkDetails.json", 'w') as f:
            json.dump(data, f)
        generateVsphereConfiguredSubnets("vipNetworkDetails.json", startIp, endIp, prefixIp,
                                        int(netmask))
        return "SUCCESS", 200, details

    @log("Updating VIP with the IP Pools....")
    def updateVipNetworkIpPools(self, ip, csrf2, get_vip, aviVersion):
        try:
            startIp = self.jsonspec["tkgComponentSpec"]['tkgClusterVipNetwork'][
                "tkgClusterVipIpStartRange"]
            endIp = self.jsonspec["tkgComponentSpec"]['tkgClusterVipNetwork'][
                "tkgClusterVipIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(
                self.jsonspec["tkgComponentSpec"]['tkgClusterVipNetwork'][
                    "tkgClusterVipNetworkGatewayCidr"])
            if self.env == Env.VCF:
                getVIPNetworkDetails = self.getNSXTNetworkDetailsVip(ip, csrf2, get_vip[0], startIp, endIp, prefixIpNetmask[0],
                                                            prefixIpNetmask[1], aviVersion)
            else:
                getVIPNetworkDetails = getNetworkDetailsVip(ip, csrf2, get_vip[0], startIp, endIp, prefixIpNetmask[0],
                                                        prefixIpNetmask[1], aviVersion, self.env)

            if getVIPNetworkDetails[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get vip network details " + str(getVIPNetworkDetails[2]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if getVIPNetworkDetails[0] == "AlreadyConfigured":
                logger.info("Vip Ip pools are already configured.")
                ip_pre = getVIPNetworkDetails[2]["subnet_ip"] + "/" + str(
                    getVIPNetworkDetails[2]["subnet_mask"])
            else:
                update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_vip[0],
                                                            "vipNetworkDetails.json",
                                                            aviVersion)
                if update_resp[0] != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to update vip network ip pools " + str(update_resp[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                ip_pre = update_resp[2]["subnet_ip"] + "/" + str(update_resp[2]["subnet_mask"])
            with open("vip_ip.txt", "w") as e:
                e.write(ip_pre)
            d = {
                "responseType": "SUCCESS",
                "msg": "Updated ip vip pools successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update vip ip pools " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

    @log("Fetching IPAM details")
    def getIpam(self, ip, csrf2, name, aviVersion):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {}
        url = "https://" + ip + "/api/ipamdnsproviderprofile"
        response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            json_object = json.dumps(response_csrf.json(), indent=4)
            with open("./ipam_details.json", "w") as outfile:
                outfile.write(json_object)
            for re in response_csrf.json()["results"]:
                if re['name'] == name:
                    return re["url"], "SUCCESS"
        return "NOT_FOUND", "SUCCESS"

    @log("Creating IPAM...")
    def createIpam(self, ip, csrf2, managementNetworkUrl, vip_network, name,
                   aviVersion, managementDataNetwork=None):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        if managementDataNetwork is not None:
            body = {
                "name": name,
                "internal_profile": {
                    "ttl": 30,
                    "usable_networks": [
                        {
                            "nw_ref": managementNetworkUrl
                        },
                        {
                            "nw_ref": managementDataNetwork
                        },
                        {
                            "nw_ref": vip_network
                        }
                    ]
                },
                "allocate_ip_in_vrf": False,
                "type": "IPAMDNS_TYPE_INTERNAL",
                "gcp_profile": {
                    "match_se_group_subnet": False,
                    "use_gcp_network": False
                },
                "azure_profile": {
                    "use_enhanced_ha": False,
                    "use_standard_alb": False
                }
            }
        else:
            body = {
                "name": name,
                "internal_profile": {
                    "ttl": 30,
                    "usable_networks": [
                        {
                            "nw_ref": managementNetworkUrl
                        },
                        {
                            "nw_ref": vip_network
                        }
                    ]
                },
                "allocate_ip_in_vrf": False,
                "type": "IPAMDNS_TYPE_INTERNAL",
                "gcp_profile": {
                    "match_se_group_subnet": False,
                    "use_gcp_network": False
                },
                "azure_profile": {
                    "use_enhanced_ha": False,
                    "use_standard_alb": False
                }
            }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/ipamdnsproviderprofile"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"

    @log("Getting IPAM details of Newly added cloud")
    def getDetailsOfNewCloudAddIpam(self, ip, csrf2, newCloudUrl, ipamUrl, aviVersion):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}
        url = newCloudUrl
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            json_object = json.dumps(response_csrf.json(), indent=4)
            os.system("rm -rf detailsOfNewCloudIpam.json")
            with open("./detailsOfNewCloudIpam.json", "w") as outfile:
                outfile.write(json_object)
            with open("detailsOfNewCloudIpam.json") as f:
                data = json.load(f)
            data["ipam_provider_ref"] = ipamUrl
            with open("detailsOfNewCloudIpam.json", 'w') as f:
                json.dump(data, f)
            return response_csrf.json(), "SUCCESS"

    @log("Updating IPAM...")
    def updateIpam(self, ip, csrf2, newCloudUrl, aviVersion):
        with open("./detailsOfNewCloudIpam.json", 'r') as file2:
            new_cloud_json = json.load(file2)
        json_object = json.dumps(new_cloud_json, indent=4)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            return response_csrf.json(), "SUCCESS"

    @log("Getting Cluster URL")
    def getClusterUrl(self, ip, csrf2, cluster_name, aviVersion):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        url = "https://" + ip + "/api/vimgrclusterruntime"
        payload = {}
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            for cluster in response_csrf.json()["results"]:
                if cluster["name"] == cluster_name:
                    return cluster["url"], "SUCCESS"

            return "NOT_FOUND", "FAILED"

    @log("Creating Service Engine for cloud")
    def createSECloud(self, ip, csrf2, newCloudUrl, seGroupName, clusterUrl, dataStore, aviVersion, se_prefix_name):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {
            "max_vs_per_se": 10,
            "min_scaleout_per_vs": 1,
            "max_scaleout_per_vs": 4,
            "max_se": 2,
            "vcpus_per_se": 2,
            "memory_per_se": 4096,
            "disk_per_se": 15,
            "max_cpu_usage": 80,
            "min_cpu_usage": 30,
            "se_deprovision_delay": 120,
            "auto_rebalance": False,
            "se_name_prefix": se_prefix_name,
            "vs_host_redundancy": True,
            "vcenter_folder": "AviSeFolder",
            "vcenter_datastores_include": True,
            "vcenter_datastore_mode": "VCENTER_DATASTORE_SHARED",
            "cpu_reserve": False,
            "mem_reserve": True,
            "ha_mode": "HA_MODE_LEGACY_ACTIVE_STANDBY",
            "algo": "PLACEMENT_ALGO_PACKED",
            "buffer_se": 1,
            "active_standby": False,
            "placement_mode": "PLACEMENT_MODE_AUTO",
            "se_dos_profile": {
                "thresh_period": 5
            },
            "auto_rebalance_interval": 300,
            "aggressive_failure_detection": False,
            "realtime_se_metrics": {
                "enabled": False,
                "duration": 30
            },
            "vs_scaleout_timeout": 600,
            "vs_scalein_timeout": 30,
            "connection_memory_percentage": 50,
            "extra_config_multiplier": 0,
            "vs_scalein_timeout_for_upgrade": 30,
            "log_disksz": 10000,
            "os_reserved_memory": 0,
            "hm_on_standby": False,
            "per_app": False,
            "distribute_load_active_standby": False,
            "auto_redistribute_active_standby_load": False,
            "dedicated_dispatcher_core": False,
            "cpu_socket_affinity": False,
            "num_flow_cores_sum_changes_to_ignore": 8,
            "least_load_core_selection": True,
            "extra_shared_config_memory": 0,
            "se_tunnel_mode": 0,
            "se_vs_hb_max_vs_in_pkt": 256,
            "se_vs_hb_max_pkts_in_batch": 64,
            "se_thread_multiplier": 1,
            "async_ssl": False,
            "async_ssl_threads": 1,
            "se_udp_encap_ipc": 0,
            "se_tunnel_udp_port": 1550,
            "archive_shm_limit": 8,
            "significant_log_throttle": 100,
            "udf_log_throttle": 100,
            "non_significant_log_throttle": 100,
            "ingress_access_mgmt": "SG_INGRESS_ACCESS_ALL",
            "ingress_access_data": "SG_INGRESS_ACCESS_ALL",
            "se_sb_dedicated_core": False,
            "se_probe_port": 7,
            "se_sb_threads": 1,
            "ignore_rtt_threshold": 5000,
            "waf_mempool": True,
            "waf_mempool_size": 64,
            "host_gateway_monitor": False,
            "vss_placement": {
                "num_subcores": 4,
                "core_nonaffinity": 2
            },
            "flow_table_new_syn_max_entries": 0,
            "disable_csum_offloads": False,
            "disable_gro": True,
            "disable_tso": False,
            "enable_hsm_priming": False,
            "distribute_queues": False,
            "vss_placement_enabled": False,
            "enable_multi_lb": False,
            "n_log_streaming_threads": 1,
            "free_list_size": 1024,
            "max_rules_per_lb": 150,
            "max_public_ips_per_lb": 30,
            "self_se_election": True,
            "minimum_connection_memory": 20,
            "shm_minimum_config_memory": 4,
            "heap_minimum_config_memory": 8,
            "disable_se_memory_check": False,
            "memory_for_config_update": 15,
            "num_dispatcher_cores": 0,
            "ssl_preprocess_sni_hostname": True,
            "se_dpdk_pmd": 0,
            "se_use_dpdk": 0,
            "min_se": 1,
            "se_pcap_reinit_frequency": 0,
            "se_pcap_reinit_threshold": 0,
            "disable_avi_securitygroups": False,
            "se_flow_probe_retries": 2,
            "vs_switchover_timeout": 300,
            "config_debugs_on_all_cores": False,
            "vs_se_scaleout_ready_timeout": 60,
            "vs_se_scaleout_additional_wait_time": 0,
            "se_dp_hm_drops": 0,
            "disable_flow_probes": False,
            "dp_aggressive_hb_frequency": 100,
            "dp_aggressive_hb_timeout_count": 10,
            "bgp_state_update_interval": 60,
            "max_memory_per_mempool": 64,
            "app_cache_percent": 0,
            "app_learning_memory_percent": 0,
            "datascript_timeout": 1000000,
            "se_pcap_lookahead": False,
            "enable_gratarp_permanent": False,
            "gratarp_permanent_periodicity": 10,
            "reboot_on_panic": True,
            "se_flow_probe_retry_timer": 40,
            "se_lro": True,
            "se_tx_batch_size": 64,
            "se_pcap_pkt_sz": 69632,
            "se_pcap_pkt_count": 0,
            "distribute_vnics": False,
            "se_dp_vnic_queue_stall_event_sleep": 0,
            "se_dp_vnic_queue_stall_timeout": 10000,
            "se_dp_vnic_queue_stall_threshold": 2000,
            "se_dp_vnic_restart_on_queue_stall_count": 3,
            "se_dp_vnic_stall_se_restart_window": 3600,
            "se_pcap_qdisc_bypass": True,
            "se_rum_sampling_nav_percent": 1,
            "se_rum_sampling_res_percent": 100,
            "se_rum_sampling_nav_interval": 1,
            "se_rum_sampling_res_interval": 2,
            "se_kni_burst_factor": 0,
            "max_queues_per_vnic": 1,
            "se_rl_prop": {
                "msf_num_stages": 1,
                "msf_stage_size": 16384
            },
            "app_cache_threshold": 5,
            "core_shm_app_learning": False,
            "core_shm_app_cache": False,
            "pcap_tx_mode": "PCAP_TX_AUTO",
            "se_dp_max_hb_version": 2,
            "resync_time_interval": 65536,
            "use_hyperthreaded_cores": True,
            "se_hyperthreaded_mode": "SE_CPU_HT_AUTO",
            "compress_ip_rules_for_each_ns_subnet": True,
            "se_vnic_tx_sw_queue_size": 256,
            "se_vnic_tx_sw_queue_flush_frequency": 0,
            "transient_shared_memory_max": 30,
            "log_malloc_failure": True,
            "se_delayed_flow_delete": True,
            "se_txq_threshold": 2048,
            "se_mp_ring_retry_count": 500,
            "dp_hb_frequency": 100,
            "dp_hb_timeout_count": 10,
            "pcap_tx_ring_rd_balancing_factor": 10,
            "use_objsync": True,
            "se_ip_encap_ipc": 0,
            "se_l3_encap_ipc": 0,
            "handle_per_pkt_attack": True,
            "per_vs_admission_control": False,
            "objsync_port": 9001,
            "se_dp_isolation": False,
            "se_dp_isolation_num_non_dp_cpus": 0,
            "cloud_ref": newCloudUrl,
            "vcenter_datastores": [{
                "datastore_name": dataStore
            }],
            "service_ip_subnets": [],
            "auto_rebalance_criteria": [],
            "auto_rebalance_capacity_per_se": [],
            "vcenter_clusters": {
                "include": True,
                "cluster_refs": [
                    clusterUrl
                ]
            },
            "license_tier": "ESSENTIALS",
            "license_type": "LIC_CORES",
            "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
            "name": seGroupName
        }
        json_object = getSeNewBody(newCloudUrl, seGroupName, clusterUrl, dataStore, se_prefix_name)
        url = "https://" + ip + "/api/serviceenginegroup"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object,
                                         verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"

    @log("Getting networking details for DHCP")
    def getNetworkDetailsDhcp(self, ip, csrf2, managementNetworkUrl, aviVersion):
        url = managementNetworkUrl
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return None, "Failed"
        os.system("rm -rf managementNetworkDetailsDhcp.json")
        with open("./managementNetworkDetailsDhcp.json", "w") as outfile:
            json.dump(response_csrf.json(), outfile)
        replaceValueSysConfig("managementNetworkDetailsDhcp.json", "dhcp_enabled", "name", "true")
        return "SUCCESS", 200

    @log("Enabling DHCP for Shared network")
    def getNetworkDetailsSharedDhcp(self,ip, csrf2, managementNetworkUrl, aviVersion):
        url = managementNetworkUrl
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return None, "Failed"
        os.system("rm -rf sharedNetworkDetailsDhcp.json")
        with open("./sharedNetworkDetailsDhcp.json", "w") as outfile:
            json.dump(response_csrf.json(), outfile)
        replaceValueSysConfig("sharedNetworkDetailsDhcp.json", "dhcp_enabled", "name", "true")
        return "SUCCESS", 200


    @log("Enabling DHCP for management network")
    def enableDhcpForManagementNetwork(self, ip, csrf2, name, aviVersion):
        getNetwork = self.getNetworkUrl(ip, csrf2, name, aviVersion)
        if getNetwork[0] is None:
            logger.error("Failed to network url " + name)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to network url " + name,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        details = self.getNetworkDetailsDhcp(ip, csrf2, getNetwork[0], aviVersion)
        if details[0] is None:
            logger.error("Failed to network details " + details[1])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get network details " + details[1],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        with open('./managementNetworkDetailsDhcp.json', 'r') as openfile:
            json_object = json.load(openfile)
        json_object_m = json.dumps(json_object, indent=4)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        response_csrf = requests.request("PUT", getNetwork[0], headers=headers, data=json_object_m,
                                         verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        return "SUCCESS", 200


    def enableDhcpForSharedNetwork(self,ip, csrf2, name, aviVersion):
        getNetwork = self.getNetworkUrl(ip, csrf2, name, aviVersion)
        if getNetwork[0] is None:
            logger.error("Failed to network url " + name)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to network url " + name,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        details = self.getNetworkDetailsSharedDhcp(ip, csrf2, getNetwork[0], aviVersion)
        if details[0] is None:
            logger.error("Failed to network details " + details[1])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get network details " + details[1],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        with open('./sharedNetworkDetailsDhcp.json', 'r') as openfile:
            json_object = json.load(openfile)
        json_object_m = json.dumps(json_object, indent=4)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        response_csrf = requests.request("PUT", getNetwork[0], headers=headers, data=json_object_m, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        return "SUCCESS", 200

    @log("Configuring cloud")
    def configCloud(self):
        aviVersion = Avi_Tkgs_Version.VSPHERE_AVI_VERSION if TkgUtil.isEnvTkgs_wcp(self.jsonspec) else Avi_Version.VSPHERE_AVI_VERSION
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        cluster_name = self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
        data_center = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        data_store = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
        refToken = self.jsonspec['envSpec']['marketplaceSpec']['refreshToken']
        req = True
        if refToken and (self.env == Env.VSPHERE or self.env == Env.VCF):
            if not (self.isEnvTkgs_wcp or self.isEnvTkgs_ns):
                kubernetes_ova_os = self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtBaseOs"]
                kubernetes_ova_version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION
                logger.info("Kubernetes OVA configs for management cluster")
                down_status = downloadAndPushKubernetesOvaMarketPlace(self.env, self.jsonspec, kubernetes_ova_version, kubernetes_ova_os)
                if down_status[0] is None:
                    logger.error(down_status[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": down_status[1],
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
        else:
            logger.info("MarketPlace refresh token is not provided, "
                        "skipping the download of kubernetes ova")
        if self.isEnvTkgs_wcp:
            avi_fqdn = self.jsonspec['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
            aviClusterFqdn = self.jsonspec['tkgsComponentSpec']['aviComponents']['aviClusterFqdn']
        else:
            avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
            aviClusterFqdn = self.jsonspec['tkgComponentSpec']['aviComponents'][
                    'aviClusterFqdn']
        if not avi_fqdn:
            controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
        else:
            controller_name = avi_fqdn
        if self.isEnvTkgs_wcp:
            ha_field = self.jsonspec['tkgsComponentSpec']['aviComponents']['enableAviHa']
        else:
            ha_field = self.jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
        if isAviHaEnabled(ha_field):
            ip = aviClusterFqdn
        else:
            ip = avi_fqdn
        if ip is None:
            logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if self.isEnvTkgs_wcp:
            avienc_pass = str(self.jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
        else:
            avienc_pass = str(self.jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
        csrf2 = obtain_second_csrf(ip, avienc_pass)
        if csrf2 is None:
            logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        deployed_avi_version = obtain_avi_version(ip, self.jsonspec)
        if deployed_avi_version[0] is None:
            logger.error("Failed to login and obtain avi version" + str(deployed_avi_version[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        aviVersion = deployed_avi_version[0]
        default = self.waitForCloudPlacementReady(ip, csrf2, "Default-Cloud", aviVersion)
        if default[0] is None:
            logger.error("Failed to get default cloud status")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get default cloud status",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        if self.isEnvTkgs_wcp:
            configTkgs = self.configTkgsCloud(ip, csrf2, aviVersion)
            if configTkgs[0] is None:
                logger.error("Failed to config tkgs " + str(configTkgs[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to config tkgs " + str(configTkgs[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            else:
                logger.info("Configured AVI Management Network for TKGs successfully")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Configured AVI Management Network for TKGs successfully",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200
        else:
            cloudName = Cloud.CLOUD_NAME_VSPHERE
            if self.env == Env.VCF:
                cloudName = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
            get_cloud = getCloudStatus(ip, csrf2, aviVersion, cloudName)
            if get_cloud[0] is None:
                logger.error("Failed to get cloud status " + str(get_cloud[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get cloud status " + str(get_cloud[1]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500

            isGen = False
            if get_cloud[0] == "NOT_FOUND":
                if req:
                    for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                        time.sleep(1)
                isGen = True
                logger.info("Creating New cloud " + cloudName)
                if self.env == Env.VCF:
                    cloud = self.nsxtObj.createNsxtCloud(ip, csrf2, aviVersion)
                    if cloud[0] is None:
                        logger.error("Failed to create cloud " + str(cloud[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create cloud " + str(cloud[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                else:
                    logger.info("Creating New cloud " + cloudName)
                    cloud = self.createNewCloud(ip, csrf2, aviVersion)
                    if cloud[0] is None:
                        logger.error("Failed to create cloud " + str(cloud[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create cloud " + str(cloud[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                cloud_url = cloud[0]
            else:
                cloud_url = get_cloud[0]
                isGen = True
            if isGen:
                for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                    time.sleep(1)
                mgmt_pg = self.jsonspec['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']
                get_management = self.getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion)
                if get_management[0] is None:
                    logger.error("Failed to get management network " + str(get_management[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get management network " + str(get_management[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                startIp = self.jsonspec["tkgComponentSpec"]["aviMgmtNetwork"][
                    "aviMgmtServiceIpStartRange"]
                endIp = self.jsonspec["tkgComponentSpec"]["aviMgmtNetwork"][
                    "aviMgmtServiceIpEndRange"]
                prefixIpNetmask = seperateNetmaskAndIp(self.jsonspec["tkgComponentSpec"]
                                                       ["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
                if self.env == Env.VSPHERE:
                    getManagementDetails = self.getNetworkDetails(ip, csrf2, get_management[0], startIp,
                                                                endIp, prefixIpNetmask[0],
                                                                prefixIpNetmask[1], aviVersion)
                    if getManagementDetails[0] is None:
                        logger.error(
                            "Failed to get management network details " + str(getManagementDetails[2]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to get management network details " + str(
                                getManagementDetails[2]),
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    if getManagementDetails[0] == "AlreadyConfigured":
                        logger.info("Ip pools are already configured.")
                        vim_ref = getManagementDetails[2]["vim_ref"]
                        ip_pre = getManagementDetails[2]["subnet_ip"]
                        mask = getManagementDetails[2]["subnet_mask"]
                    else:
                        update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_management[0],
                                                                    "managementNetworkDetails.json",
                                                                    aviVersion)
                        if update_resp[0] != 200:
                            logger.error(
                                "Failed to update management network ip pools " + str(update_resp[1]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to update management network ip pools " + str(
                                    update_resp[1]),
                                "ERROR_CODE": 500
                            }
                            return json.dumps(d), 500
                        vim_ref = update_resp[2]["vimref"]
                        mask = update_resp[2]["subnet_mask"]
                        ip_pre = update_resp[2]["subnet_ip"]
                
                    new_cloud_status = self.getDetailsOfNewCloud(ip, csrf2, cloud_url, vim_ref, ip_pre, mask, aviVersion)
                    if new_cloud_status[0] is None:
                        logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    updateNewCloudStatus = self.updateNewCloud(ip, csrf2, cloud_url, aviVersion)
                    if updateNewCloudStatus[0] is None:
                        logger.error("Failed to update cloud " + str(updateNewCloudStatus[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to update cloud " + str(updateNewCloudStatus[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    mgmt_data_pg = self.jsonspec['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName']
                    get_management_data_pg = self.getNetworkUrl(ip, csrf2, mgmt_data_pg, aviVersion)
                    if get_management_data_pg[0] is None:
                        logger.error(
                            "Failed to get management data network details " + str(get_management_data_pg[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to get management data network details " + str(get_management_data_pg[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    startIp = self.jsonspec["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpStartRange"]
                    endIp = self.jsonspec["tkgMgmtDataNetwork"]["tkgMgmtAviServiceIpEndRange"]
                    prefixIpNetmask = seperateNetmaskAndIp(
                        self.jsonspec["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkGatewayCidr"])
                    getManagementDetails_data_pg = self.getNetworkDetails(ip, csrf2, get_management_data_pg[0], startIp, endIp,
                                                                    prefixIpNetmask[0], prefixIpNetmask[1], aviVersion)
                    if getManagementDetails_data_pg[0] is None:
                        logger.error(
                            "Failed to get management data network details " + str(getManagementDetails_data_pg[2]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to get management data network details " + str(getManagementDetails_data_pg[2]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    if getManagementDetails_data_pg[0] == "AlreadyConfigured":
                        logger.info("Ip pools are already configured.")
                    else:
                        update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_management_data_pg[0],
                                                            "managementNetworkDetails.json",
                                                            aviVersion)
                        if update_resp[0] != 200:
                            logger.error("Failed to update management network details " + str(update_resp[1]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to update management network details " + str(update_resp[1]),
                                "STATUS_CODE": 500
                            }
                            return json.dumps(d), 500
            
                mgmt_pg = self.jsonspec['tkgComponentSpec']['tkgClusterVipNetwork'][
                    'tkgClusterVipNetworkName']
                get_vip = self.getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion)
                if get_vip[0] is None:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get vip network " + str(get_vip[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                vip_pool = self.updateVipNetworkIpPools(ip, csrf2, get_vip, aviVersion)
                if vip_pool[1] != 200:
                    logger.error(str(vip_pool[0]['msg']))
                    d = {
                        "responseType": "ERROR",
                        "msg": str(vip_pool[0]['msg']),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500

            if self.env == Env.VSPHERE:
                get_ipam = self.getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
                if get_ipam[0] is None:
                    logger.error("Failed to get se Ipam " + str(get_ipam[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get ipam " + str(get_ipam[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500

                isGen = False
                if get_ipam[0] == "NOT_FOUND":
                    isGen = True
                    logger.info("Creating IPAM " + Cloud.IPAM_NAME_VSPHERE)
                    ipam = self.createIpam(ip, csrf2, get_management[0], get_vip[0], Cloud.IPAM_NAME_VSPHERE,
                                        aviVersion, get_management_data_pg[0])
                    if ipam[0] is None:
                        logger.error("Failed to create ipam " + str(ipam[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create  ipam " + str(ipam[1]),
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500
                    ipam_url = ipam[0]
                else:
                    ipam_url = get_ipam[0]

                new_cloud_status = self.getDetailsOfNewCloudAddIpam(ip, csrf2, cloud_url, ipam_url,
                                                                    aviVersion)
                if new_cloud_status[0] is None:
                    logger.error(
                        "Failed to get new cloud details" + str(new_cloud_status[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get new cloud details " + str(new_cloud_status[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                updateIpam_re = self.updateIpam(ip, csrf2, cloud_url, aviVersion)
                if updateIpam_re[0] is None:
                    logger.error("Failed to update ipam to cloud " + str(updateIpam_re[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to update ipam to cloud " + str(updateIpam_re[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
                cluster_status = self.getClusterUrl(ip, csrf2, cluster_name, aviVersion)
                if cluster_status[0] is None:
                    logger.error("Failed to get cluster details" + str(cluster_status[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get cluster details " + str(cluster_status[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                if cluster_status[0] == "NOT_FOUND":
                    logger.error("Failed to get cluster details" + str(cluster_status[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get cluster details " + str(cluster_status[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            seGroupName = Cloud.SE_GROUP_NAME_VSPHERE
            if self.env == Env.VCF:
                seGroupName = Cloud.SE_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
            get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, seGroupName)
            if get_se_cloud[0] is None:
                logger.error("Failed to get service engine cloud status " + str(get_se_cloud[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get service engine cloud status " + str(get_se_cloud[1]),
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500

            isGen = False
            if get_se_cloud[0] == "NOT_FOUND":
                isGen = True
                logger.info("Creating New service engine cloud " + seGroupName)
                if self.env == Env.VCF:
                    nsx_cloud_info = self.nsxtObj.configureVcenterInNSXTCloud(ip, csrf2, cloud_url, aviVersion)
                    if nsx_cloud_info[0] is None:
                        logger.error("Failed to configure vcenter in cloud " + str(nsx_cloud_info[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to configure vcenter in cloud " + str(nsx_cloud_info[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    cloud_se = self.nsxtObj.createNsxtSECloud(ip, csrf2, cloud_url, seGroupName, nsx_cloud_info[1], aviVersion, SePrefixName.MGMT)
                else:
                    cloud_se = self.createSECloud(ip, csrf2, cloud_url, seGroupName, cluster_status[0], data_store,
                                         aviVersion, SePrefixName.MGMT)
                if cloud_se[0] is None:
                    logger.error("Failed to create service engine cloud " + str(cloud_se[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to create service engine cloud " + str(cloud_se[1]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
                se_cloud_url = cloud_se[0]
            else:
                se_cloud_url = get_se_cloud[0]
            clo = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
            if self.env == Env.VCF:
                clo = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
            get_se_cloud_workload = getSECloudStatus(ip, csrf2, aviVersion, clo)
            if get_se_cloud_workload[0] is None:
                logger.error(
                    "Failed to get service engine cloud status " + str(get_se_cloud_workload[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get service engine cloud status " + str(get_se_cloud_workload[1]),
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500

            isGen = False
            if get_se_cloud_workload[0] == "NOT_FOUND":
                isGen = True
                logger.info("Creating New service engine cloud " + clo)
                cloud_se_workload = self.createSECloud_Arch(ip, csrf2, cloud_url, clo,
                                                        aviVersion, SePrefixName.WORKLOAD)
                if cloud_se_workload[0] is None:
                    logger.error("Failed to create service engine cloud " + str(cloud_se_workload[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to create service engine cloud " + str(cloud_se_workload[1]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
                se_cloud_url_workload = cloud_se_workload[0]
            else:
                se_cloud_url_workload = get_se_cloud_workload[0]

            if self.env == Env.VSPHERE:
                mgmt_name = self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtNetworkName"]
                dhcp = self.enableDhcpForManagementNetwork(ip, csrf2, mgmt_name, aviVersion)
                if dhcp[0] is None:
                    logger.error("Failed to enable dhcp " + str(dhcp[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to enable dhcp " + str(dhcp[1]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            
            # if self.env == Env.VCF:
            #     shared_service_name = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
            #             'tkgSharedserviceNetworkName']
            #     dhcp = self.enableDhcpForSharedNetwork(ip, csrf2, shared_service_name, aviVersion)
            #     if dhcp[0] is None:
            #         logger.error("Failed to enable dhcp " + str(dhcp[1]))
            #         d = {
            #             "responseType": "ERROR",
            #             "msg": "Failed to enable dhcp " + str(dhcp[1]),
            #             "ERROR_CODE": 500
            #             }
            #         return json.dumps(d), 500

            cloudName = Cloud.CLOUD_NAME_VSPHERE
            if self.env == Env.VCF:
                cloudName = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
            with open("./newCloudInfo.json", 'r') as file2:
                new_cloud_json = json.load(file2)
            uuid = None
            try:
                uuid = new_cloud_json["uuid"]
            except:
                for re in new_cloud_json["results"]:
                    if re["name"] == cloudName:
                        uuid = re["uuid"]
            if uuid is None:
                return None, "NOT_FOUND"
            prefixIpNetmask_vip = seperateNetmaskAndIp(
                self.jsonspec['tkgComponentSpec']["tkgClusterVipNetwork"][
                    "tkgClusterVipNetworkGatewayCidr"])
            tier1 = ""
            vrf_url = ""
            if self.env == Env.VSPHERE:
                ipNetMask = seperateNetmaskAndIp(
                    self.jsonspec["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
                vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.MANAGEMENT, ipNetMask[0], aviVersion)
                if vrf[0] is None or vrf[1] == "NOT_FOUND":
                    logger.error("Vrf not found " + str(vrf[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Vrf not found " + str(vrf[1]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
                if vrf[1] != "Already_Configured":
                    ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask[0], vrf[1], aviVersion)
                    if ad[0] is None:
                        logger.error("Failed to add static route " + str(ad[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Vrf not found " + str(ad[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                prefixIpNetmask_vip = seperateNetmaskAndIp(
                    self.jsonspec['tkgComponentSpec']["tkgClusterVipNetwork"][
                        "tkgClusterVipNetworkGatewayCidr"])
                list_ = [prefixIpNetmask[0], prefixIpNetmask_vip[0]]
                for l in list_:
                    vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, l, aviVersion)
                    if vrf[0] is None or vrf[1] == "NOT_FOUND":
                        logger.error("Vrf not found " + str(vrf[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Vrf not found " + str(vrf[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    if vrf[1] != "Already_Configured":
                        ad = addStaticRoute(ip, csrf2, vrf[0], l, vrf[1], aviVersion)
                        if ad[0] is None:
                            logger.error("Failed to add static route " + str(ad[1]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Vrf not found " + str(ad[1]),
                                "STATUS_CODE": 500
                            }
                            return json.dumps(d), 500
            else:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Cookie": csrf2[1],
                    "referer": "https://" + ip + "/login",
                    "x-avi-version": aviVersion,
                    "x-csrftoken": csrf2[0]
                }
                status, value = self.nsxtObj.getCloudConnectUser(ip, headers)
                nsxt_cred = value["nsxUUid"]
                tier1_id, status_tier1 = self.nsxtObj.fetchTier1GatewayId(ip, headers, nsxt_cred)
                if tier1_id is None:
                    logger.error("Failed to get Tier 1 details " + str(status_tier1))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get Tier 1 details " + str(status_tier1),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
                tier1 = status_tier1
                vrf_avi_mgmt = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, prefixIpNetmask[0], aviVersion)
                if vrf_avi_mgmt[0] is None or vrf_avi_mgmt[1] == "NOT_FOUND":
                    logger.error("AVI mgmt Vrf not found " + str(vrf_avi_mgmt[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "AVI mgmt Vrf not found " + str(vrf_avi_mgmt[1]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
                if vrf_avi_mgmt[1] != "Already_Configured":
                    ad = addStaticRoute(ip, csrf2, vrf_avi_mgmt[0], prefixIpNetmask[0], vrf_avi_mgmt[1], aviVersion)
                    if ad[0] is None:
                        logger.error("Failed to add static route " + str(ad[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Vrf not found " + str(ad[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                teir1name = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtTier1RouterDisplayName"])
                vrf_vip = getVrfAndNextRoutId(ip, csrf2, uuid, teir1name, prefixIpNetmask_vip[0], aviVersion)
                if vrf_vip[0] is None or vrf_vip[1] == "NOT_FOUND":
                    logger.error("Cluster vip Vrf not found " + str(vrf_vip[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Cluster vip Vrf not found " + str(vrf_vip[1]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
                if vrf_vip[1] != "Already_Configured":
                    ad = addStaticRoute(ip, csrf2, vrf_vip[0], prefixIpNetmask_vip[0], vrf_vip[1], aviVersion)
                    if ad[0] is None:
                        logger.error("Failed to add static route " + str(ad[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Vrf not found " + str(ad[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                vrf_url = vrf_vip[0]
                getManagementDetails = self.nsxtObj.getNsxTNetworkDetails(ip, csrf2, get_management[0], startIp, endIp,
                                                         prefixIpNetmask[0],
                                                         prefixIpNetmask[1], aviVersion)
                if getManagementDetails[0] is None:
                    logger.error("Failed to get AVI management network details " + str(getManagementDetails[2]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get AVI management network details " + str(getManagementDetails[2]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
                if getManagementDetails[0] == "AlreadyConfigured":
                    logger.info("Ip pools are already configured.")
                    # vim_ref = getManagementDetails[2]["vim_ref"]
                    ip_pre = getManagementDetails[2]["subnet_ip"]
                    mask = getManagementDetails[2]["subnet_mask"]
                else:
                    update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_management[0], "managementNetworkDetails.json",
                                                       aviVersion)
                    if update_resp[0] != 200:
                        logger.error("Failed to update management network ip pools " + str(update_resp[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to update management network ip pools " + str(update_resp[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    # vim_ref = update_resp[2]["vimref"]
                    mask = update_resp[2]["subnet_mask"]
                    ip_pre = update_resp[2]["subnet_ip"]
                ipam_name = Cloud.IPAM_NAME_VSPHERE.replace("vsphere", "nsxt")
                get_ipam = self.getIpam(ip, csrf2, ipam_name, aviVersion)
                if get_ipam[0] is None:
                    logger.error("Failed to get service engine Ipam " + str(get_ipam[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get service engine Ipam " + str(get_ipam[1]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500

                isGen = False
                if get_ipam[0] == "NOT_FOUND":
                    logger.info("Creating IPam " + ipam_name)
                    ipam = self.nsxtObj.createIpam_nsxtCloud(ip, csrf2, get_management[0], get_vip[0], ipam_name, aviVersion)
                    if ipam[0] is None:
                        logger.error("Failed to create Ipam " + str(ipam[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create Ipam " + str(ipam[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    ipam_url = ipam[0]
                else:
                    ipam_url = get_ipam[0]
                dns_profile_name = "tkg-nsxt-dns"
                search_domain = self.jsonspec['envSpec']['infraComponents']['searchDomains']
                get_dns = self.getIpam(ip, csrf2, dns_profile_name, aviVersion)
                if get_dns[0] is None:
                    logger.error("Failed to get service engine Ipam " + str(get_dns[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get service engine ipam " + str(get_dns[1]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
                if get_dns[0] == "NOT_FOUND":
                    dns = self.nsxtObj.createDns_nsxtCloud(ip, csrf2, search_domain, dns_profile_name, aviVersion)
                    if dns[0] is None:
                        logger.error("Failed to create Nsxt dns " + str(dns[1]))
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to create Nsxt dns " + str(dns[1]),
                            "STATUS_CODE": 500
                        }
                        return json.dumps(d), 500
                    dnsurl = dns[0]
                else:
                    logger.info("Dns already created")
                    dnsurl = get_dns[0]
                ipam_asso = self.nsxtObj.associate_ipam_nsxtCloud(ip, csrf2, aviVersion, uuid, ipam_url, dnsurl)
                if ipam_asso[0] is None:
                    logger.error("Failed to associate Ipam and dns to cloud " + str(ipam_asso[1]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to associate Ipam and dns to cloud " + str(ipam_asso[1]),
                        "STATUS_CODE": 500
                    }
                    return json.dumps(d), 500
            virtual_service, error = create_virtual_service(ip, csrf2, uuid, seGroupName, get_vip[0], 2,
                                                        tier1, vrf_url, aviVersion, self.jsonspec, self.env)
            if virtual_service is None:
                logger.error("Failed to create virtual service " + str(error))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create virtual service " + str(error),
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500

            logger.info("Configured management cluster cloud successfully")
            d = {
                "responseType": "SUCCESS",
                "msg": "Configured management cluster cloud successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200



    def configTkgsCloud(self, ip, csrf2, aviVersion):
        try:
            get_cloud = getCloudStatus(ip, csrf2, aviVersion, Cloud.DEFAULT_CLOUD_NAME_VSPHERE)
            if get_cloud[0] is None:
                return None, str(get_cloud[1])
            cloud_url = get_cloud[0]
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Cookie": csrf2[1],
                "referer": "https://" + ip + "/login",
                "x-avi-version": aviVersion,
                "x-csrftoken": csrf2[0]
            }
            with open("./newCloudInfo.json", 'r') as file2:
                new_cloud_json = json.load(file2)
            try:
                for result in new_cloud_json['results']:
                    if result['name'] == Cloud.DEFAULT_CLOUD_NAME_VSPHERE:
                        vcenter_config = result["vcenter_configuration"]["vcenter_url"]
                        break
                logger.info(
                    " vcenter details are already updated to cloud " + Cloud.DEFAULT_CLOUD_NAME_VSPHERE)
            except:
                logger.info("Updating vcenter details to cloud " + Cloud.DEFAULT_CLOUD_NAME_VSPHERE)
                vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
                vcenter_password = CmdHelper.decode_base64(vcpass_base64)
                vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
                vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
                vcenter_datacenter = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
                body = {
                    "name": Cloud.DEFAULT_CLOUD_NAME_VSPHERE,
                    "vtype": "CLOUD_VCENTER",
                    "vcenter_configuration": {
                        "privilege": "WRITE_ACCESS",
                        "deactivate_vm_discovery": False,
                        "vcenter_url": vcenter_ip,
                        "username": vcenter_username,
                        "password": vcenter_password,
                        "datacenter": vcenter_datacenter
                    }
                }
                json_object = json.dumps(body, indent=4)
                url = cloud_url
                logger.info("Waiting for 1 min status == ready")
                time.sleep(60)
                response_csrf = requests.request("PUT", url, headers=headers, data=json_object, verify=False)
                if response_csrf.status_code != 200:
                    return None, response_csrf.text
                else:
                    os.system("rm -rf newCloudInfo.json")
                    with open("./newCloudInfo.json", "w") as outfile:
                        json.dump(response_csrf.json(), outfile)
            mgmt_pg = self.jsonspec['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']
            get_management = self.getNetworkUrl(ip, csrf2, mgmt_pg, aviVersion,
                                                cloudName=Cloud.DEFAULT_CLOUD_NAME_VSPHERE)
            if get_management[0] is None:
                return None, "Failed to get avi management network " + str(get_management[1])
            startIp = self.jsonspec["tkgsComponentSpec"]["aviMgmtNetwork"][
                "aviMgmtServiceIpStartRange"]
            endIp = self.jsonspec["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtServiceIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(
                self.jsonspec["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
            getManagementDetails = self.getNetworkDetails(ip, csrf2, get_management[0], startIp, endIp, prefixIpNetmask[0],
                                                     prefixIpNetmask[1], aviVersion, isSeRequired=True)
            if getManagementDetails[0] is None:
                logger.error("Failed to get management network details " + str(getManagementDetails[2]))
                return None, str(getManagementDetails[2])
            if getManagementDetails[0] == "AlreadyConfigured":
                logger.info("Ip pools are already configured.")
                vim_ref = getManagementDetails[2]["vim_ref"]
                ip_pre = getManagementDetails[2]["subnet_ip"]
                mask = getManagementDetails[2]["subnet_mask"]
            else:
                update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_management[0], "managementNetworkDetails.json",
                                                       aviVersion)
                if update_resp[0] != 200:
                    return None, str(update_resp[1])
                vim_ref = update_resp[2]["vimref"]
                mask = update_resp[2]["subnet_mask"]
                ip_pre = update_resp[2]["subnet_ip"]
            new_cloud_status = self.getDetailsOfNewCloud(ip, csrf2, cloud_url, vim_ref, ip_pre, mask, aviVersion)
            if new_cloud_status[0] is None:
                return None, str(new_cloud_status[1])
            updateNewCloudStatus = self.updateNewCloud(ip, csrf2, cloud_url, aviVersion)
            if updateNewCloudStatus[0] is None:
                logger.error("Failed to update cloud " + str(updateNewCloudStatus[1]))
                return None, str(updateNewCloudStatus[1])
            with open("./newCloudInfo.json", 'r') as file2:
                new_cloud_json = json.load(file2)
            uuid = None
            try:
                uuid = new_cloud_json["uuid"]
            except:
                for re in new_cloud_json["results"]:
                    if re["name"] == Cloud.DEFAULT_CLOUD_NAME_VSPHERE:
                        uuid = re["uuid"]
            if uuid is None:
                logger.error(Cloud.DEFAULT_CLOUD_NAME_VSPHERE + " cloud not found")
                return None, "NOT_FOUND"
            ipNetMask = seperateNetmaskAndIp(
                self.jsonspec["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
            vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.MANAGEMENT, ipNetMask[0], aviVersion)
            if vrf[0] is None or vrf[1] == "NOT_FOUND":
                logger.error("Vrf not found " + str(vrf[1]))
                return None, str(vrf[1])
            if vrf[1] != "Already_Configured":
                ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask[0], vrf[1], aviVersion)
                if ad[0] is None:
                    logger.error("Failed to add static route " + str(ad[1]))
                    return None, str(ad[1])
            ##########################################################
            vip_pg = self.jsonspec['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipNetworkName']
            get_vip = self.getNetworkUrl(ip, csrf2, vip_pg, aviVersion,cloudName=Cloud.DEFAULT_CLOUD_NAME_VSPHERE)
            if get_vip[0] is None:
                return None, "Failed to get tkgs vip network " + str(get_vip[1])
            startIp_vip = self.jsonspec["tkgsComponentSpec"]["tkgsVipNetwork"]["tkgsVipIpStartRange"]
            endIp_vip = self.jsonspec["tkgsComponentSpec"]["tkgsVipNetwork"]["tkgsVipIpEndRange"]
            prefixIpNetmask_vip = seperateNetmaskAndIp(
                self.jsonspec["tkgsComponentSpec"]["tkgsVipNetwork"]["tkgsVipNetworkGatewayCidr"])
            getManagementDetails_vip = self.getNetworkDetails(ip, csrf2, get_vip[0], startIp_vip, endIp_vip,
                                                         prefixIpNetmask_vip[0],
                                                         prefixIpNetmask_vip[1], aviVersion, isSeRequired=False)
            if getManagementDetails_vip[0] is None:
                logger.error("Failed to get tkgs vip network details " + str(getManagementDetails_vip[2]))
                return None, str(getManagementDetails_vip[2])
            if getManagementDetails_vip[0] == "AlreadyConfigured":
                logger.info("Ip pools are already configured for tkgs vip.")
            else:
                update_resp = self.updateNetworkWithIpPools(ip, csrf2, get_vip[0], "managementNetworkDetails.json",
                                                       aviVersion)
                if update_resp[0] != 200:
                    logger.error("Failed to update tkgs vip details to cloud " + str(update_resp[1]))
                    return None, str(update_resp[1])
            get_ipam = self.getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
            if get_ipam[0] is None:
                logger.error("Failed to get se Ipam " + str(get_ipam[1]))
                return None, str(get_ipam[1])

            isGen = False
            if get_ipam[0] == "NOT_FOUND":
                isGen = True
                logger.info("Creating IPam " + Cloud.IPAM_NAME_VSPHERE)
                ipam = self.createIpam(ip, csrf2, get_management[0], get_vip[0], Cloud.IPAM_NAME_VSPHERE,
                                  aviVersion)
                if ipam[0] is None:
                    logger.error("Failed to create ipam " + str(ipam[1]))
                    return None, str(ipam[1])
                ipam_url = ipam[0]
            else:
                ipam_url = get_ipam[0]

            new_cloud_status = self.getDetailsOfNewCloudAddIpam(ip, csrf2, cloud_url, ipam_url, aviVersion)
            if new_cloud_status[0] is None:
                logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
                return None, str(new_cloud_status[1])
            updateIpam_re = self.updateIpam(ip, csrf2, cloud_url, aviVersion)
            if updateIpam_re[0] is None:
                logger.error("Failed to update ipam to cloud " + str(updateIpam_re[1]))
                return None, str(updateIpam_re[1])
            cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
            cluster_status = self.getClusterUrl(ip, csrf2, cluster_name, aviVersion)
            if cluster_status[0] is None:
                logger.error("Failed to get cluster details" + str(cluster_status[1]))
                return None, str(cluster_status[1])
            if cluster_status[0] == "NOT_FOUND":
                logger.error("Failed to get cluster details" + str(cluster_status[1]))
                return None, str(cluster_status[1])
            get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.DEFAULT_SE_GROUP_NAME_VSPHERE)
            if get_se_cloud[0] is None:
                logger.error("Failed to get se cloud status " + str(get_se_cloud[1]))
                return None, str(get_se_cloud[1])
            se_engine_url = get_se_cloud[0]
            update = self.updateSeEngineDetails(ip, csrf2, se_engine_url, cluster_status[0], aviVersion)
            if update[0] is None:
                return None, update[1]
            ipNetMask_vip = prefixIpNetmask_vip
            vrf_vip = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, ipNetMask_vip[0], aviVersion)
            if vrf_vip[0] is None or vrf_vip[1] == "NOT_FOUND":
                logger.error("Vrf not found " + str(vrf_vip[1]))
                return None, str(vrf_vip[1])
            if vrf_vip[1] != "Already_Configured":
                ad = addStaticRoute(ip, csrf2, vrf_vip[0], ipNetMask_vip[0], vrf_vip[1], aviVersion)
                if ad[0] is None:
                    logger.error("Failed to add static route " + str(ad[1]))
                    return None, str(ad[1])
            return "SUCCESS", "CONFIGURED_TKGS_CLOUD"
        except Exception as e:
            return None, str(e)

    def updateSeEngineDetails(self, ip, csrf2, seUrl, clusterUrl, aviVersion):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {
            "name": Cloud.DEFAULT_SE_GROUP_NAME_VSPHERE,
            "vcpus_per_se": 2,
            "memory_per_se": 4096,
            "vcenter_datastores_include": True,
            "vcenter_datastore_mode": "VCENTER_DATASTORE_SHARED",
            "vcenter_clusters": {
                "include": True,
                "cluster_refs": [clusterUrl]
            }
        }
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("PUT", seUrl, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"

    def enableWCP(self, ip, csrf2, aviVersion):
        try:
            vCenter = self.vcenter_dict["vcenter_ip"]
            vc_user = self.vcenter_dict["vcenter_username"]
            vc_password = self.vcenter_dict["vcenter_password"]
            vc_data_center = self.vcenter_dict["vcenter_datacenter"]
            sess = requests.post("https://" + vCenter + "/rest/com/vmware/cis/session", auth=(vc_user, vc_password),
                                 verify=False)
            if sess.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                    "ERROR_CODE": 500
                }
                logger.error(f"Error occurred: [ {d} ]")
                return False
            else:
                vc_session = sess.json()['value']

            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": vc_session
            }
            cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
            id = getClusterID(vCenter, vc_user, vc_password, cluster_name, self.jsonspec)
            if id[1] != 200:
                return None, id[0]
            url = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + str(id[0])
            response_csrf = requests.request("GET", url, headers=header, verify=False)
            endpoint_ip = None
            isRuning = False
            if response_csrf.status_code != 200:
                if response_csrf.status_code == 400:
                    if response_csrf.json()["messages"][0]["default_message"] == "Cluster with identifier " + str(
                            id[0]) + " does " \
                                     "not have Workloads enabled.":
                        pass
                    else:
                        return None, response_csrf.text
                else:
                    return None, response_csrf.text
            else:
                try:
                    if response_csrf.json()["config_status"] == "RUNNING":
                        endpoint_ip = response_csrf.json()["api_server_cluster_endpoint"]
                        isRuning = True
                    else:
                        isRuning = False
                    if response_csrf.json()["config_status"] == "ERROR":
                        return None, "WCP is enabled but in ERROR state"
                except:
                    isRuning = False

            if isRuning:
                logger.info("Wcp is already enabled")
            else:
                logger.info("Enabling Wcp..")
                control_plane_size = self.jsonspec["tkgsComponentSpec"]["controlPlaneSize"]
                allowed_tkgs_size = ["TINY", "SMALL", "MEDIUM", "LARGE"]
                if not control_plane_size.upper() in allowed_tkgs_size:
                    return None, \
                           "Allowed Control plane sizes [tkgsComponentSpec][controlPlaneSize] are TINY, SMALL, MEDIUM, LARGE"
                image_storage_policy_name = self.jsonspec["tkgsComponentSpec"]["tkgsStoragePolicySpec"][
                    "imageStoragePolicy"]
                image_storage_policyId = getPolicyID(image_storage_policy_name, vCenter, vc_user, vc_password)
                if image_storage_policyId[0] is None:
                    return None, image_storage_policyId[1]
                ephemeral_storage_policy_name = \
                    self.jsonspec["tkgsComponentSpec"]["tkgsStoragePolicySpec"][
                        "ephemeralStoragePolicy"]
                ephemeral_storage_policyId = getPolicyID(ephemeral_storage_policy_name, vCenter, vc_user, vc_password)
                if ephemeral_storage_policyId[0] is None:
                    return None, ephemeral_storage_policyId[1]
                master_storage_policy_name = \
                    self.jsonspec["tkgsComponentSpec"]["tkgsStoragePolicySpec"][
                        "masterStoragePolicy"]
                master_storage_policyId = getPolicyID(master_storage_policy_name, vCenter, vc_user, vc_password)
                if master_storage_policyId[0] is None:
                    return None, master_storage_policyId[1]
                str_enc_avi = str(
                    self.jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
                base64_bytes_avi = str_enc_avi.encode('ascii')
                enc_bytes_avi = base64.b64decode(base64_bytes_avi)
                password_avi = enc_bytes_avi.decode('ascii').rstrip("\n")
                avi_fqdn = self.jsonspec['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
                master_dnsServers = self.jsonspec['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                    'tkgsMgmtNetworkDnsServers']
                master_search_domains = self.jsonspec['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                    'tkgsMgmtNetworkSearchDomains']
                master_ntp_servers = self.jsonspec['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                    'tkgsMgmtNetworkNtpServers']
                worker_dns = self.jsonspec['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                    'tkgsWorkloadDnsServers']
                worker_ntps = self.jsonspec['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                    'tkgsWorkloadNtpServers']
                worker_cidr = self.jsonspec['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                    'tkgsPrimaryWorkloadNetworkGatewayCidr']
                start = self.jsonspec['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                    'tkgsPrimaryWorkloadNetworkStartRange']
                end = self.jsonspec['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                    'tkgsPrimaryWorkloadNetworkEndRange']
                ip_cidr = seperateNetmaskAndIp(worker_cidr)
                count_of_ip = getCountOfIpAdress(worker_cidr, start, end)
                service_cidr = self.jsonspec['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                    'tkgsWorkloadServiceCidr']
                service_cidr_split = seperateNetmaskAndIp(service_cidr)
                worker_network_name = self.jsonspec['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                    'tkgsPrimaryWorkloadPortgroupName']
                workload_network_name = self.jsonspec['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                    'tkgsPrimaryWorkloadNetworkName']
                worker_network_id = getDvPortGroupId(vCenter, vc_user, vc_password, worker_network_name, vc_data_center)
                if worker_network_id is None:
                    return None, "Failed to get worker dv port id"
                ###################################################
                master_management = self.jsonspec['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                    'tkgsMgmtNetworkGatewayCidr']
                master_management_start = self.jsonspec['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                    'tkgsMgmtNetworkStartingIp']
                master_management_ip_netmask = seperateNetmaskAndIp(master_management)
                mgmt_network_name = self.jsonspec['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                    'tkgsMgmtNetworkName']
                try:
                    isProxyEnabled = self.jsonspec['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'][
                        'enableProxy']
                    if str(isProxyEnabled).lower() == "true":
                        proxyEnabled = True
                    else:
                        proxyEnabled = False
                except:
                    proxyEnabled = False
                mgmt_network_id = getDvPortGroupId(vCenter, vc_user, vc_password, mgmt_network_name, vc_data_center)
                if mgmt_network_id is None:
                    return None, "Failed to get management dv port id"
                subs_lib_name = self.jsonspec['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                    'subscribedContentLibraryName']
                if not subs_lib_name:
                    lib = getLibraryId(vCenter, vc_user, vc_password, ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY)
                else:
                    lib = getLibraryId(vCenter, vc_user, vc_password, subs_lib_name)
                if lib is None:
                    return None, "Failed to get subscribed lib id"
                cert = getAviCertificate(ip, csrf2, CertName.VSPHERE_CERT_NAME, aviVersion)
                if cert[0] is None or cert[0] == "NOT_FOUND":
                    return None, "Avi certificate not found"
                body = {
                    "default_kubernetes_service_content_library": lib,
                    "image_storage": {
                        "storage_policy": image_storage_policyId[0]
                    },
                    "ephemeral_storage_policy": ephemeral_storage_policyId[0],
                    "master_storage_policy": master_storage_policyId[0],
                    "load_balancer_config_spec": {
                        "address_ranges": [],
                        "avi_config_create_spec": {
                            "certificate_authority_chain": cert[0],
                            "password": password_avi,
                            "server": {
                                "host": avi_fqdn,
                                "port": 443
                            },
                            "username": "admin"
                        },
                        "id": "tkgs-avi01",
                        "provider": "AVI"
                    },
                    "master_DNS": convertStringToCommaSeperated(master_dnsServers),
                    "master_DNS_search_domains": convertStringToCommaSeperated(master_search_domains),
                    "master_NTP_servers": convertStringToCommaSeperated(master_ntp_servers),
                    "master_management_network": {
                        "address_range": {
                            "address_count": 5,
                            "gateway": master_management_ip_netmask[0],
                            "starting_address": master_management_start,
                            "subnet_mask": cidr_to_netmask(master_management)
                        },
                        "mode": "STATICRANGE",
                        "network": mgmt_network_id
                    },
                    "network_provider": "VSPHERE_NETWORK",
                    "service_cidr": {
                        "address": service_cidr_split[0],
                        "prefix": int(service_cidr_split[1])
                    },
                    "size_hint": control_plane_size.upper(),
                    "worker_DNS": convertStringToCommaSeperated(worker_dns),
                    "worker_ntp_servers": convertStringToCommaSeperated(worker_ntps),
                    "workload_networks_spec": {
                        "supervisor_primary_workload_network": {
                            "network": workload_network_name,
                            "network_provider": "VSPHERE_NETWORK",
                            "vsphere_network": {
                                "address_ranges": [{
                                    "address": start,
                                    "count": count_of_ip
                                }],
                                "gateway": ip_cidr[0],
                                "portgroup": worker_network_id,
                                "subnet_mask": cidr_to_netmask(worker_cidr)
                            }
                        }
                    }
                }
                if proxyEnabled:
                    httpProxy = self.jsonspec['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'][
                        'httpProxy']
                    httpsProxy = self.jsonspec['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'][
                        'httpsProxy']
                    noProxy = self.jsonspec['tkgsComponentSpec']['tkgServiceConfig']['proxySpec'][
                        'noProxy']
                    list_ = convertStringToCommaSeperated(noProxy)
                    body_u = {
                        "cluster_proxy_config": {
                            "http_proxy_config": httpProxy,
                            "https_proxy_config": httpsProxy,
                            "no_proxy_config": list_,
                            "proxy_settings_source": "CLUSTER_CONFIGURED"
                        }
                    }
                    body.update(body_u)
                url1 = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + str(
                    id[0]) + "?action=enable"
                json_object = json.dumps(body, indent=4)
                response_csrf = requests.request("POST", url1, headers=header, data=json_object, verify=False)
                if response_csrf.status_code != 204:
                    return None, response_csrf.text
                count = 0
                found = False
                while count < 135:
                    response_csrf = requests.request("GET", url, headers=header, verify=False)
                    try:
                        if response_csrf.json()["config_status"] == "RUNNING":
                            endpoint_ip = response_csrf.json()["api_server_cluster_endpoint"]
                            found = True
                            break
                        else:
                            if response_csrf.json()["config_status"] == "ERROR":
                                return None, "WCP status in ERROR"
                            logger.info("Cluster config status " + response_csrf.json()["config_status"])
                    except:
                        pass
                    time.sleep(20)
                    count = count + 1
                    logger.info("Waited " + str(count * 20) + "s, retrying")
                if not found:
                    logger.error("Cluster is not running on waiting " + str(count * 20))
                    return None, "Failed"
            '''if endpoint_ip is not None:
                logger.info("Setting up kubectl vsphere")
                time.sleep(30)
                configure_kubectl = configureKubectl(endpoint_ip)
                if configure_kubectl[1] != 200:
                    return configure_kubectl[0], 500'''
            return "SUCCESS", "WCP_ENABLED"
        except Exception as e:
            return None, str(e)

    def enable_wcp(self):
        if not self.isEnvTkgs_wcp:
            logger.error("Wrong env provided wcp can  only be  enabled on TKGS")
            d = {
                "responseType": "ERROR",
                "msg": "Wrong env provided wcp can  only be  enabled on TKGS",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        password = self.vcenter_dict["vcenter_password"]
        vcenter_username = self.vcenter_dict["vcenter_username"]
        vcenter_ip = self.vcenter_dict["vcenter_ip"]
        subs_lib_name = self.jsonspec['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
            'subscribedContentLibraryName']
        if not subs_lib_name:
            cLib = createSubscribedLibrary(vcenter_ip, vcenter_username, password, self.jsonspec)
            if cLib[0] is None:
                logger.error("Failed to create content library " + str(cLib[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create content library " + str(cLib[1]),
                    "STATUS_CODE": 500
                }
                return json.dumps(d), 500
        avi_fqdn = self.jsonspec['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
        if not avi_fqdn:
            controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
        else:
            controller_name = avi_fqdn
        ha_field = self.jsonspec['tkgsComponentSpec']['aviComponents']['enableAviHa']
        if isAviHaEnabled(ha_field):
            ip = self.jsonspec['tkgsComponentSpec']['aviComponents']['aviClusterFqdn']
        else:
            ip = avi_fqdn
        if ip is None:
            logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        avienc_pass = str(self.jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
        csrf2 = obtain_second_csrf(ip, avienc_pass)
        if csrf2 is None:
            logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        avi_ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), avi_fqdn)
        if avi_ip is None:
            logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        deployed_avi_version = obtain_avi_version(avi_ip, self.jsonspec)
        if deployed_avi_version[0] is None:
            logger.error("Failed to login and obtain avi version" + str(deployed_avi_version[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        aviVersion = deployed_avi_version[0]

        enable = self.enableWCP(ip, csrf2, aviVersion)
        if enable[0] is None:
            logger.error("Failed to enable wcp " + str(enable[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to configure wcp " + str(enable[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        isUp = checkAndWaitForAllTheServiceEngineIsUp(ip, Cloud.DEFAULT_CLOUD_NAME_VSPHERE, self.jsonspec, aviVersion)
        if isUp[0] is None:
            logger.error("All service engines are not up, check your network configuration " + str(isUp[1]))
            d = {
                "responseType": "ERROR",
                "msg": "All service engines are not up, check your network configuration " + str(isUp[1]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        logger.info("Setting up kubectl vsphere plugin...")
        url_ = "https://" + vcenter_ip + "/"
        sess = requests.post(url_ + "rest/com/vmware/cis/session", auth=(vcenter_username, password), verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vcenter_ip,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            session_id = sess.json()['value']

        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": session_id
        }
        cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
        id = getClusterID(vcenter_ip, vcenter_username, password, cluster_name, self.jsonspec)
        if id[1] != 200:
            return None, id[0]
        clusterip_resp = requests.get(url_ + "api/vcenter/namespace-management/clusters/" + str(id[0]), verify=False,
                                      headers=header)
        if clusterip_resp.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch API server cluster endpoint - " + vcenter_ip,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]

        configure_kubectl = configureKubectl(cluster_endpoint)
        if configure_kubectl[1] != 200:
            logger.error(configure_kubectl[0])
            d = {
                "responseType": "ERROR",
                "msg": configure_kubectl[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        logger.info("Configured Wcp successfully")

        if checkTmcEnabled(self.jsonspec):
            tmc_register_response = registerTMCTKGs(vcenter_ip, vcenter_username, password, self.jsonspec)
            if tmc_register_response[1] != 200:
                logger.error("Supervisor cluster TMC registration failed " + str(tmc_register_response[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Supervisor cluster TMC registration failed " + str(tmc_register_response[0]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            else:
                logger.info("TMC registration successful")
        else:
            logger.info("Skipping TMC registration, as tmcAvailability is set to False")
        d = {
            "responseType": "SUCCESS",
            "msg": "Configured Wcp successfully",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    def createSECloud_Arch(self, ip, csrf2, newCloudUrl, seGroupName, aviVersion, se_name_prefix):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        json_object = self.getNewBody(newCloudUrl, seGroupName, se_name_prefix)
        url = "https://" + ip + "/api/serviceenginegroup"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"


    def getNewBody(self, newCloudUrl, seGroupName, se_name_prefix):
        body = {
            "max_vs_per_se": 10,
            "min_scaleout_per_vs": 2,
            "max_scaleout_per_vs": 4,
            "max_se": 10,
            "vcpus_per_se": 1,
            "memory_per_se": 2048,
            "disk_per_se": 15,
            "max_cpu_usage": 80,
            "min_cpu_usage": 30,
            "se_deprovision_delay": 120,
            "auto_rebalance": False,
            "se_name_prefix": se_name_prefix,
            "vs_host_redundancy": True,
            "vcenter_folder": "AviSeFolder",
            "vcenter_datastores_include": False,
            "vcenter_datastore_mode": "VCENTER_DATASTORE_ANY",
            "cpu_reserve": False,
            "mem_reserve": True,
            "ha_mode": "HA_MODE_SHARED_PAIR",
            "algo": "PLACEMENT_ALGO_PACKED",
            "buffer_se": 0,
            "active_standby": False,
            "placement_mode": "PLACEMENT_MODE_AUTO",
            "se_dos_profile": {
                "thresh_period": 5
            },
            "auto_rebalance_interval": 300,
            "aggressive_failure_detection": False,
            "realtime_se_metrics": {
                "enabled": False,
                "duration": 30
            },
            "vs_scaleout_timeout": 600,
            "vs_scalein_timeout": 30,
            "connection_memory_percentage": 50,
            "extra_config_multiplier": 0,
            "vs_scalein_timeout_for_upgrade": 30,
            "log_disksz": 10000,
            "os_reserved_memory": 0,
            "hm_on_standby": True,
            "per_app": False,
            "distribute_load_active_standby": False,
            "auto_redistribute_active_standby_load": False,
            "dedicated_dispatcher_core": False,
            "cpu_socket_affinity": False,
            "num_flow_cores_sum_changes_to_ignore": 8,
            "least_load_core_selection": True,
            "extra_shared_config_memory": 0,
            "se_tunnel_mode": 0,
            "se_vs_hb_max_vs_in_pkt": 256,
            "se_vs_hb_max_pkts_in_batch": 64,
            "se_thread_multiplier": 1,
            "async_ssl": False,
            "async_ssl_threads": 1,
            "se_udp_encap_ipc": 0,
            "se_tunnel_udp_port": 1550,
            "archive_shm_limit": 8,
            "significant_log_throttle": 100,
            "udf_log_throttle": 100,
            "non_significant_log_throttle": 100,
            "ingress_access_mgmt": "SG_INGRESS_ACCESS_ALL",
            "ingress_access_data": "SG_INGRESS_ACCESS_ALL",
            "se_sb_dedicated_core": False,
            "se_probe_port": 7,
            "se_sb_threads": 1,
            "ignore_rtt_threshold": 5000,
            "waf_mempool": True,
            "waf_mempool_size": 64,
            "host_gateway_monitor": False,
            "vss_placement": {
                "num_subcores": 4,
                "core_nonaffinity": 2
            },
            "flow_table_new_syn_max_entries": 0,
            "disable_csum_offloads": False,
            "disable_gro": True,
            "disable_tso": False,
            "enable_hsm_priming": False,
            "distribute_queues": False,
            "vss_placement_enabled": False,
            "enable_multi_lb": False,
            "n_log_streaming_threads": 1,
            "free_list_size": 1024,
            "max_rules_per_lb": 150,
            "max_public_ips_per_lb": 30,
            "self_se_election": True,
            "minimum_connection_memory": 20,
            "shm_minimum_config_memory": 4,
            "heap_minimum_config_memory": 8,
            "disable_se_memory_check": False,
            "memory_for_config_update": 15,
            "num_dispatcher_cores": 0,
            "ssl_preprocess_sni_hostname": True,
            "se_dpdk_pmd": 0,
            "se_use_dpdk": 0,
            "min_se": 1,
            "se_pcap_reinit_frequency": 0,
            "se_pcap_reinit_threshold": 0,
            "disable_avi_securitygroups": False,
            "se_flow_probe_retries": 2,
            "vs_switchover_timeout": 300,
            "config_debugs_on_all_cores": False,
            "vs_se_scaleout_ready_timeout": 60,
            "vs_se_scaleout_additional_wait_time": 0,
            "se_dp_hm_drops": 0,
            "disable_flow_probes": False,
            "dp_aggressive_hb_frequency": 100,
            "dp_aggressive_hb_timeout_count": 10,
            "bgp_state_update_interval": 60,
            "max_memory_per_mempool": 64,
            "app_cache_percent": 10,
            "app_learning_memory_percent": 0,
            "datascript_timeout": 1000000,
            "se_pcap_lookahead": False,
            "enable_gratarp_permanent": False,
            "gratarp_permanent_periodicity": 10,
            "reboot_on_panic": True,
            "se_flow_probe_retry_timer": 40,
            "se_lro": True,
            "se_tx_batch_size": 64,
            "se_pcap_pkt_sz": 69632,
            "se_pcap_pkt_count": 0,
            "distribute_vnics": False,
            "se_dp_vnic_queue_stall_event_sleep": 0,
            "se_dp_vnic_queue_stall_timeout": 10000,
            "se_dp_vnic_queue_stall_threshold": 2000,
            "se_dp_vnic_restart_on_queue_stall_count": 3,
            "se_dp_vnic_stall_se_restart_window": 3600,
            "se_pcap_qdisc_bypass": True,
            "se_rum_sampling_nav_percent": 1,
            "se_rum_sampling_res_percent": 100,
            "se_rum_sampling_nav_interval": 1,
            "se_rum_sampling_res_interval": 2,
            "se_kni_burst_factor": 0,
            "max_queues_per_vnic": 1,
            "se_rl_prop": {
                "msf_num_stages": 1,
                "msf_stage_size": 16384
            },
            "app_cache_threshold": 5,
            "core_shm_app_learning": False,
            "core_shm_app_cache": False,
            "pcap_tx_mode": "PCAP_TX_AUTO",
            "se_dp_max_hb_version": 2,
            "resync_time_interval": 65536,
            "use_hyperthreaded_cores": True,
            "se_hyperthreaded_mode": "SE_CPU_HT_AUTO",
            "compress_ip_rules_for_each_ns_subnet": True,
            "se_vnic_tx_sw_queue_size": 256,
            "se_vnic_tx_sw_queue_flush_frequency": 0,
            "transient_shared_memory_max": 30,
            "log_malloc_failure": True,
            "se_delayed_flow_delete": True,
            "se_txq_threshold": 2048,
            "se_mp_ring_retry_count": 500,
            "dp_hb_frequency": 100,
            "dp_hb_timeout_count": 10,
            "pcap_tx_ring_rd_balancing_factor": 10,
            "use_objsync": True,
            "se_ip_encap_ipc": 0,
            "se_l3_encap_ipc": 0,
            "handle_per_pkt_attack": True,
            "per_vs_admission_control": False,
            "objsync_port": 9001,
            "objsync_config": {
                "objsync_cpu_limit": 30,
                "objsync_reconcile_interval": 10,
                "objsync_hub_elect_interval": 60
            },
            "se_dp_isolation": False,
            "se_dp_isolation_num_non_dp_cpus": 0,
            "cloud_ref": newCloudUrl,
            "vcenter_datastores": [
            ],
            "service_ip_subnets": [
            ],
            "auto_rebalance_criteria": [
            ],
            "auto_rebalance_capacity_per_se": [
            ],
            "license_tier": "ENTERPRISE",
            "license_type": "LIC_CORES",
            "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
            "name": seGroupName
        }
        return json.dumps(body, indent=4)



