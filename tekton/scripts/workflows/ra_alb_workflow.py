#!/usr/local/bin/python3

#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path
import time
from retry import retry
import json

from constants.constants import Paths, AlbPrefix, AlbCloudType, ComponentPrefix, AlbLicenseTier, VmPowerState, \
    AlbVrfContext, ControllerLocation, CertName
from model.run_config import RunConfig
from model.status import HealthEnum, Info, State
from util.avi_api_helper import AviApiSpec, ra_avi_download, isAviHaEnabled, \
    deployAndConfigureAvi, form_avi_ha_cluster, manage_avi_certificates
from util.cmd_helper import CmdHelper, timer
from util.file_helper import FileHelper
from util.logger_helper import LoggerHelper, log
from jinja2 import Template
from util.govc_client import GovcClient
from util.local_cmd_helper import LocalCmdHelper
from util.vcenter_operations import checkforIpAddress, getSi
from util.common_utils import checkenv
from util.vcenter_operations import create_folder, createResourcePool
from util.tkg_util import TkgUtil

logger = LoggerHelper.get_logger(name='alb_workflow')


class RALBWorkflow:
    def __init__(self, run_config: RunConfig) -> None:
        self.run_config = run_config
        self.version = None
        self.jsonpath = None
        self.tkg_type = ''.join([attr for attr in dir(self.run_config.desired_state.version) if "tkg" in attr])
        if "tkgs" in self.tkg_type:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_WCP_MASTER_SPEC_PATH)
            #self.ns_jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_NS_MASTER_SPEC_PATH)
        elif "tkg" in self.tkg_type:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        else:
            raise Exception(f"Could not find supported TKG version: {self.tkg_type}")

        with open(self.jsonpath) as f:
            self.jsonspec = json.load(f)

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)
        self.isEnvTkgs_wcp = TkgUtil.isEnvTkgs_wcp(self.jsonspec)
        self.isEnvTkgs_ns = TkgUtil.isEnvTkgs_ns(self.jsonspec)

    @log("Setting up AVI Certificate")
    def aviCertManagement_vsphere(self):
        vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
        password = CmdHelper.decode_base64(vcpass_base64)
        vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
        vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
        if self.isEnvTkgs_wcp:
            avi_fqdn = self.jsonspec['tkgsComponentSpec']['aviComponents'][
                'aviController01Fqdn']
        else:
            avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents'][
                'aviController01Fqdn']
        if not avi_fqdn:
            logger.error("Avi fqdn not provided")
            return None
        ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), avi_fqdn)
        if ip is None:
            logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return None
        aviVersion = ControllerLocation.VSPHERE_AVI_VERSION
        cert = manage_avi_certificates(ip, aviVersion, self.jsonspec,
                                       avi_fqdn, CertName.VSPHERE_CERT_NAME)
        if cert[1] != 200:
            logger.error("Failed to mange-certificate " + cert[0].json['msg'])
            return None
        isGen = cert[2]
        if isGen:
            logger.info("Generated and replaced the certificate successfully")
            d = {
                "responseType": "SUCCESS",
                "msg": "Generated and replaced the certificate successfully",
                "ERROR_CODE": 200
            }
            return True
        else:
            logger.info("Certificate is already generated")
            return True

    @log("Setting up AVI Controller")
    def avi_controller_setup(self):

        if self.run_config.state.avi.deployed:
            logger.debug("NSX-ALB is deployed")
            return True
        if not ra_avi_download(self.jsonspec):
            logger.error("Failed to setup AVI")
            raise ValueError('Failed to deploy and configure avi.')
        avi_fqdn2 = ''
        avi_ip2 = ''
        avi_fqdn3 = ''
        avi_ip3 = ''
        if self.isEnvTkgs_wcp:
            control_plan = "dev"
            avi_fqdn = self.jsonspec['tkgsComponentSpec']['aviComponents'][
                'aviController01Fqdn']
            avi_ip = self.jsonspec['tkgsComponentSpec']['aviComponents'][
                'aviController01Ip']
            ha_field = self.jsonspec['tkgsComponentSpec']['aviComponents']['enableAviHa']
            if isAviHaEnabled(ha_field):
                avi_fqdn2 = self.jsonspec['tkgsComponentSpec']['aviComponents'][
                    'aviController02Fqdn']
                avi_ip2 = self.jsonspec['tkgsComponentSpec']['aviComponents'][
                    'aviController02Ip']
                avi_fqdn3 = self.jsonspec['tkgsComponentSpec']['aviComponents'][
                    'aviController03Fqdn']
                avi_ip3 = self.jsonspec['tkgsComponentSpec']['aviComponents'][
                    'aviController03Ip']
            mgmgt_name = self.jsonspec['tkgsComponentSpec']['aviMgmtNetwork'][
                'aviMgmtNetworkName']
            mgmt_cidr = self.jsonspec['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']
        else:
            control_plan = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtDeploymentType']
            avi_fqdn = self.jsonspec['tkgComponentSpec']['aviComponents'][
                'aviController01Fqdn']
            avi_ip = self.jsonspec['tkgComponentSpec']['aviComponents'][
                'aviController01Ip']
            ha_field = self.jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
            if isAviHaEnabled(ha_field):
                avi_fqdn2 = self.jsonspec['tkgComponentSpec']['aviComponents'][
                    'aviController02Fqdn']
                avi_ip2 = self.jsonspec['tkgComponentSpec']['aviComponents'][
                    'aviController02Ip']
                avi_fqdn3 = self.jsonspec['tkgComponentSpec']['aviComponents'][
                    'aviController03Fqdn']
                avi_ip3 = self.jsonspec['tkgComponentSpec']['aviComponents'][
                    'aviController03Ip']
            mgmgt_name = self.jsonspec['tkgComponentSpec']['aviMgmtNetwork'][
                'aviMgmtNetworkName']
            mgmt_cidr = self.jsonspec['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkGatewayCidr']
        if str(control_plan) == "prod":
            control_plan = "dev"
        if isAviHaEnabled(ha_field):
            if not avi_fqdn or not avi_fqdn2 or not avi_fqdn3:
                logger.info("Avi fqdn not provided, for ha mode 3 fqdns are required")
                raise ValueError('Failed to deploy and configure avi.')
        if not avi_fqdn:
            logger.info("Avi fqdn not provided")
            raise ValueError('Failed to deploy and configure avi.')

        if str(control_plan).lower() == "dev":
            if not avi_ip:
                controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
                if isAviHaEnabled(ha_field):
                    controller_name2 = ControllerLocation.CONTROLLER_NAME_VSPHERE2
                    controller_name3 = ControllerLocation.CONTROLLER_NAME_VSPHERE3
                netmask = ''
                ip = ''
                gateway = ''
            else:
                if not mgmt_cidr:
                    logger.error("Mgmt cidr not provided")
                    raise ValueError('Failed to deploy and configure avi.')
                gateway, netmask = str(mgmt_cidr).split('/')
                ip = avi_ip
                controller_name = avi_fqdn
                if isAviHaEnabled(ha_field):
                    controller_name2 = avi_fqdn2
                    controller_name3 = avi_fqdn3
                    ip2 = avi_ip2
                    ip3 = avi_ip3
            fqdn = avi_fqdn
            if isAviHaEnabled(ha_field):
                fqdn2 = avi_fqdn2
                fqdn3 = avi_fqdn3
            deploy_options = Template(FileHelper.read_resource(Paths.VSPHERE_ALB_DEPLOY_J2))
            VSPHERE_ALB_DEPLOY_JSON = "/tmp/deploy_vsphere_alb_controller_config.json"
            FileHelper.write_to_file(
                deploy_options.render(ip=ip, netmask=netmask, gateway=gateway, fqdn=fqdn,
                                      network=mgmgt_name, vm_name=controller_name),
                VSPHERE_ALB_DEPLOY_JSON)
            if isAviHaEnabled(ha_field):
                VSPHERE_ALB_DEPLOY_JSON2 = "/tmp/deploy_vsphere_alb_controller_config2.json"
                VSPHERE_ALB_DEPLOY_JSON3 = "/tmp/deploy_vsphere_alb_controller_config3.json"
                FileHelper.write_to_file(
                    deploy_options.render(ip=ip2, netmask=netmask, gateway=gateway, fqdn=fqdn2,
                                          network=mgmgt_name, vm_name=controller_name2),
                    VSPHERE_ALB_DEPLOY_JSON2)
                FileHelper.write_to_file(
                    deploy_options.render(ip=ip3, netmask=netmask, gateway=gateway, fqdn=fqdn3,
                                          network=mgmgt_name, vm_name=controller_name3),
                    VSPHERE_ALB_DEPLOY_JSON3)
            VC_Content_Library_name = self.jsonspec['envSpec']['vcenterDetails'][
                    "contentLibraryName"]
            if not VC_Content_Library_name:
                VC_Content_Library_name = 'TanzuAutomation-Lib'
            VC_AVI_OVA_NAME = self.jsonspec['envSpec']['vcenterDetails'][
                    "aviOvaName"]
            if not VC_AVI_OVA_NAME:
                VC_AVI_OVA_NAME = 'avi-controller'
            controller_location = "/" + VC_Content_Library_name + "/" + VC_AVI_OVA_NAME
            dcname = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
            clustername = self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
            dsname = self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
            if self.isEnvTkgs_wcp:
                parent_resourcepool = ""
            else:
                parent_resourcepool = self.jsonspec['envSpec']['vcenterDetails']['resourcePoolName']
            rp_pool = dcname + "/host/" + clustername + "/Resources/" + parent_resourcepool
            foldername = "TEKTON"
            vcpass_base64 = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
            password = CmdHelper.decode_base64(vcpass_base64)
            vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
            vcenter_ip = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
            create_folder(vcenter_ip, vcenter_username, password, dcname, foldername)
            options = f"-options {VSPHERE_ALB_DEPLOY_JSON} -dc={dcname} -ds={dsname} -folder={foldername} -pool=/{rp_pool}"
            if isAviHaEnabled(ha_field):
                options2 = f"-options {VSPHERE_ALB_DEPLOY_JSON2} -dc={dcname} -ds={dsname} -folder={foldername} -pool=/{rp_pool}"
                options3 = f"-options {VSPHERE_ALB_DEPLOY_JSON3} -dc={dcname} -ds={dsname} -folder={foldername} -pool=/{rp_pool}"
        else:
            logger.error("Currently other then dev plan is not supported")
            raise ValueError('Failed to deploy and configure avi.')
        avi_version = ControllerLocation.VSPHERE_AVI_VERSION
        govc_client = GovcClient(self.jsonspec, LocalCmdHelper())
        dep = deployAndConfigureAvi(govc_client=govc_client, vm_name=controller_name,
                                    controller_ova_location=controller_location,
                                    deploy_options=options,
                                    performOtherTask=True,
                                    avi_version=avi_version,
                                    jsonspec=self.jsonspec)
        if not dep:
            logger.error(
                "Failed to deploy and configure avi " + str(dep))

            raise ValueError('Failed to deploy and configure avi.')
        if isAviHaEnabled(ha_field):
            logger.info("Deploying 2nd avi controller")
            dep2 = deployAndConfigureAvi(govc_client=govc_client, vm_name=controller_name2,
                                         controller_ova_location=controller_location,
                                         deploy_options=options2,
                                         performOtherTask=False,
                                         avi_version=avi_version,
                                         jsonspec=self.jsonspec)
            if not dep2:
                logger.error(
                    "Failed to deploy and configure avi 2nd controller  " + str(
                        dep2[0].json['msg']))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to deploy and configure avi  " + str(dep2[0].json['msg']),
                    "ERROR_CODE": 500
                }
                raise ValueError('Failed to deploy and configure avi.')
            logger.info("Deploying 3rd avi controller")
            dep3 = deployAndConfigureAvi(govc_client=govc_client, vm_name=controller_name3,
                                         controller_ova_location=controller_location,
                                         deploy_options=options3,
                                         performOtherTask=False,
                                         avi_version=avi_version,
                                         jsonspec=self.jsonspec)
            if not dep3:
                logger.error("Failed to deploy and configure avi 2nd controller")
                raise ValueError('Failed to deploy and configure avi.')
            res, status = form_avi_ha_cluster(ip, self.jsonspec, avi_version)
            if res is None:
                logger.error("Failed to form avi ha cluster ")
                raise ValueError('Failed to deploy and configure avi.')
        avi_cert = self.aviCertManagement_vsphere()
        return True

