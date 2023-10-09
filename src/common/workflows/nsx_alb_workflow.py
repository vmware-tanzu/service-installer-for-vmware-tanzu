# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause


__author__ = "Tasmiya Bano"

from http import HTTPStatus

from flask import current_app, request
from jinja2 import Template

from common.lib.avi.avi_admin_operations import AVIAdminOps
from common.lib.avi.avi_deployment_operations import AVIDeploymentOps
from common.lib.avi.avi_template_operations import AVITemplateOperations
from common.lib.govc.govc_client import GOVClient
from common.lib.govc.govc_operations import GOVCOperations
from common.lib.vcenter.vcenter_ssl_operations import VCenterSSLOperations
from common.operation.constants import Avi_Version, CertName, ControllerLocation, Env, Paths, ResourcePoolAndFolderName
from common.util.common_utils import CommonUtils
from common.util.file_helper import FileHelper
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.marketplace_util import MarketPlaceUtils
from common.util.tkgs_util import TkgsUtil


class NsxAlbWorkflow:
    def __init__(self):
        self.env = request.headers["Env"]
        spec_obj = CommonUtils.get_spec_obj(self.env)
        json_dict = request.get_json(force=True)
        self.spec: spec_obj = spec_obj.parse_obj(json_dict)
        if self.env == Env.VCD:
            vc_data = self.spec.envSpec.aviCtrlDeploySpec.vcenterDetails
        else:
            vc_data = self.spec.envSpec.vcenterDetails
        self.vcenter_ip = vc_data.vcenterAddress
        self.vcenter_username = vc_data.vcenterSsoUser
        str_enc = str(vc_data.vcenterSsoPasswordBase64)
        self.password = CommonUtils.decode_password(str_enc)
        self.vsphere_decoded_password = CommonUtils.encode_password(self.password)

        self.password_avi = None

        self.data_center = vc_data.vcenterDatacenter
        self.data_store = vc_data.vcenterDatastore

        self.data_center = self.data_center.replace(" ", "#remove_me#")
        self.data_store = self.data_store.replace(" ", "#remove_me#")

        self.vc_cluster_name = vc_data.vcenterCluster
        self.parent_resourcePool = "" if TkgsUtil.is_env_tkgs_wcp(self.spec, self.env) else vc_data.resourcePoolName
        self.market_place_token = self.spec.envSpec.marketplaceSpec.refreshToken

        self.govc_operation = GOVCOperations(
            self.vcenter_ip,
            self.vcenter_username,
            self.password,
            self.vc_cluster_name,
            self.data_center,
            self.data_store,
            LocalCmdHelper(),
        )

        self.govc_client = GOVClient(
            self.vcenter_ip,
            self.vcenter_username,
            self.password,
            self.vc_cluster_name,
            self.data_center,
            self.data_store,
            LocalCmdHelper(),
        )

        self.vc_ssl_obj = VCenterSSLOperations(
            self.vcenter_ip,
            self.vcenter_username,
            self.password,
            self.vc_cluster_name,
            self.data_center,
            self.govc_operation,
        )

    def _get_rp_and_folder(self):
        if self.env == Env.VSPHERE or self.env == Env.VCF or self.env == Env.VCD:
            return ResourcePoolAndFolderName.AVI_RP_VSPHERE, ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE
        else:
            return ResourcePoolAndFolderName.AVI_RP, ResourcePoolAndFolderName.AVI_Components_FOLDER

    @staticmethod
    def get_alb_data_objects(spec, env):
        if TkgsUtil.is_env_tkgs_wcp(spec, env):
            alb_data_object = spec.tkgsComponentSpec.aviComponents
            alb_network_object = spec.tkgsComponentSpec.aviMgmtNetwork
        else:
            if env == Env.VCD:
                alb_data_object = spec.envSpec.aviCtrlDeploySpec.aviComponentsSpec
                alb_network_object = spec.envSpec.aviCtrlDeploySpec.aviMgmtNetwork
            else:
                alb_data_object = spec.tkgComponentSpec.aviComponents
                alb_network_object = spec.tkgComponentSpec.aviMgmtNetwork

        return alb_data_object, alb_network_object

    def get_alb_details_dict(self, data_object):
        alb_config = dict()
        alb_config[data_object.aviController01Fqdn] = {
            "ip": data_object.aviController01Ip,
            "file_path": Paths.VSPHERE_ALB_DEPLOY_JSON,
            "main_ova": True,
        }
        if self._check_avi_ha_enabled():
            if not data_object.aviController02Fqdn or not data_object.aviController03Fqdn:
                raise Exception("NSX ALB HA is enabled but additional controller details are missing")

            alb_config[data_object.aviController02Fqdn] = {
                "ip": data_object.aviController02Ip,
                "file_path": Paths.VSPHERE_ALB_DEPLOY_JSON2,
                "main_ova": False,
            }
            alb_config[data_object.aviController03Fqdn] = {
                "ip": data_object.aviController03Ip,
                "file_path": Paths.VSPHERE_ALB_DEPLOY_JSON3,
                "main_ova": False,
            }
        return alb_config

    def _check_avi_ha_enabled(self):
        try:
            if TkgsUtil.is_env_tkgs_wcp(self.spec, self.env):
                enable_avi_ha = self.spec.tkgsComponentSpec.aviComponents.enableAviHa
            else:
                if self.env == Env.VCD:
                    enable_avi_ha = self.spec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.enableAviHa
                else:
                    enable_avi_ha = self.spec.tkgComponentSpec.aviComponents.enableAviHa
            if str(enable_avi_ha).lower() == "true":
                return True
            else:
                return False
        except KeyError:
            return False

    def _get_contoller_plan(self):
        if TkgsUtil.is_env_tkgs_wcp(self.spec, self.env):
            plan = "dev"
        else:
            if self.env == Env.VCD:
                plan = "dev"
            else:
                plan = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtDeploymentType

        if str(plan).lower() == "prod":
            current_app.logger.info("Currently only dev plan is supported for NSX ALB")
            plan = "dev"

        return plan

    def _get_avi_version(self):
        if self.env == Env.VMC:
            version = Avi_Version.VMC_AVI_VERSION
        else:
            version = Avi_Version.VSPHERE_AVI_VERSION
        return version

    def get_content_library(self):
        if CommonUtils.is_airGapped_enabled(self.env, self.spec) or not self.market_place_token:
            if self.env == Env.VCD:
                content_library_name = self.spec.envSpec.aviCtrlDeploySpec.vcenterDetails.contentLibraryName
                avi_ova_name = self.spec.envSpec.aviCtrlDeploySpec.vcenterDetails.aviOvaName
            else:
                content_library_name = self.spec.envSpec.vcenterDetails.contentLibraryName
                avi_ova_name = self.spec.envSpec.vcenterDetails.aviOvaName
        else:
            content_library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
            avi_ova_name = ControllerLocation.CONTROLLER_NAME

        return content_library_name, avi_ova_name

    def download_alb_marketplace(self):
        # marketplace_refresh_token = self.spec.envSpec.marketplaceSpec.refreshToken
        if self.market_place_token:
            marketplace_util = MarketPlaceUtils(self.market_place_token)
            download_status = marketplace_util.download_avi_ova(self.govc_operation, Avi_Version.VSPHERE_AVI_VERSION)
            if download_status[0] is None:
                raise Exception(download_status[1])
        else:
            current_app.logger.info(
                "MarketPlace refresh token is not provided, skipping the download of AVI Controller OVA"
            )

    def create_alb_folder_and_rp(self):
        resource_pool, folder = self._get_rp_and_folder()
        create_response = self.vc_ssl_obj.create_resource_folder_and_wait(
            resource_pool, folder, self.parent_resourcePool
        )
        if create_response[1] != 200:
            message = "Failed to create resource pool and folder " + create_response[0].json["msg"]
            raise Exception(message)

    def deploy_controller_ova(self):
        data_object, network_object = NsxAlbWorkflow.get_alb_data_objects(self.spec, self.env)
        alb_config = self.get_alb_details_dict(data_object)

        str_enc_avi = str(data_object.aviPasswordBase64)
        self.password_avi = CommonUtils.decode_password(str_enc_avi)

        alb_network_name = network_object.aviMgmtNetworkName
        alb_network_cidr = network_object.aviMgmtNetworkGatewayCidr

        self._get_contoller_plan()

        if not data_object.aviController01Ip:
            netmask = ""
            gateway = ""
        else:
            if not alb_network_cidr:
                raise Exception("CIDR not provided for AVI Management network")
            gateway, netmask = CommonUtils.seperate_netmask_and_ip(alb_network_cidr)
        avi_version = self._get_avi_version()
        deploy_options = Template(FileHelper.read_resource(Paths.VSPHERE_ALB_DEPLOY_J2))

        content_library, avi_ova = self.get_content_library()
        controller_location = f"/{content_library}/{avi_ova}"
        controller_location = controller_location.replace(" ", "#remove_me#")

        if self.parent_resourcePool is not None:
            resource_pool = (
                f"/{self.data_center}/host/{self.vc_cluster_name}/Resources/{self.parent_resourcePool}"
                f"/{ResourcePoolAndFolderName.AVI_RP_VSPHERE}"
            )
        else:
            resource_pool = (
                f"/{self.data_center}/host/{self.vc_cluster_name}/Resources/{ResourcePoolAndFolderName.AVI_RP_VSPHERE}"
            )

        resource_pool = resource_pool.replace(" ", "#remove_me#")

        is_tkgs = False if not TkgsUtil.is_env_tkgs_wcp(self.spec, self.env) else True
        dns_ip = self.spec.envSpec.infraComponents.dnsServersIp
        ntp_ip = self.spec.envSpec.infraComponents.ntpServers
        search_domains = self.spec.envSpec.infraComponents.searchDomains

        backup_pass_phrase = CommonUtils.decode_password(data_object.aviBackupPassphraseBase64)
        if self.env == Env.VCD:
            type_of_license = "enterprise"
        else:
            type_of_license = data_object.typeOfLicense
        avi_deployment = AVIDeploymentOps(
            self.govc_client,
            controller_location,
            avi_version,
            self.data_center,
            data_object.aviSize,
            True,
            backup_pass_phrase,
            is_tkgs,
            dns_ip,
            ntp_ip,
            search_domains,
            self.password_avi,
            license_type=type_of_license,
        )

        for fqdn, details in alb_config.items():
            file_path = details["file_path"]
            FileHelper.write_to_file(
                deploy_options.render(
                    ip=details["ip"],
                    netmask=netmask,
                    gateway=gateway,
                    fqdn=fqdn,
                    network=alb_network_name,
                    vm_name=fqdn,
                ),
                file_path,
            )
            options = (
                f"-options {file_path} -dc=/{self.data_center} "
                f"-ds={self.data_store} -folder={ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE}"
                f" -pool=/{resource_pool}"
            )

            deploy_response = avi_deployment.deploy_and_configure_avi(options, details["main_ova"], fqdn)
            if deploy_response[1] != HTTPStatus.OK:
                raise Exception(f"Failed to deploy NSX ALB Controller {fqdn}")

    def configure_alb_ha(self):
        if self._check_avi_ha_enabled():
            data_object, network_object = NsxAlbWorkflow.get_alb_data_objects(self.spec, self.env)
            admin_ops = AVIAdminOps(data_object.aviController01Ip, self.password_avi)
            admin_ops.obtain_second_csrf()
            avi_ips = [
                data_object.aviController01Ip,
                data_object.aviController02Ip,
                data_object.aviController03Ip,
                data_object.aviClusterIp,
            ]
            response = admin_ops.form_avi_ha_cluster(avi_ips)
            if response[0] is None:
                raise Exception(f"Failed to configure HA for NSX ALB {response[1]}")
        else:
            current_app.logger.info("HA for NSX ALB is disabled hence, skipping HA configurations")

    def alb_certificate_configuration(self):
        data_object, network_object = NsxAlbWorkflow.get_alb_data_objects(self.spec, self.env)
        avi_template = AVITemplateOperations(
            data_object.aviController01Fqdn, self.password_avi, CertName.VSPHERE_CERT_NAME
        )
        avi_ips = [data_object.aviController01Ip, data_object.aviController01Fqdn]
        if self._check_avi_ha_enabled():
            avi_ips.extend([data_object.aviController02Ip, data_object.aviController02Fqdn])
            avi_ips.extend([data_object.aviController03Ip, data_object.aviController03Fqdn])
            avi_ips.extend([data_object.aviClusterIp, data_object.aviClusterFqdn])
        cert_response = avi_template.manage_avi_certificates(
            avi_ips, data_object.aviCertPath, data_object.aviCertKeyPath
        )
        if cert_response[1] != HTTPStatus.OK:
            raise Exception("Failed to update certificate for NSX ALB Controller ")

    def nsx_alb_deploy_workflow(self):
        self.download_alb_marketplace()

        self.create_alb_folder_and_rp()

        self.deploy_controller_ova()

        self.configure_alb_ha()

        self.alb_certificate_configuration()
