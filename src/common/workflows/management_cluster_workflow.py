# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause


__author__ = "Tasmiya Bano"


import base64
import json
import os
import time
from http import HTTPStatus

from flask import current_app, request
from jinja2 import Template
from tqdm import tqdm

from common.certificate_base64 import getBase64CertWriteToFile
from common.common_utilities import createRbacUsers
from common.lib.avi.avi_base_operations import AVIBaseOperations
from common.lib.avi.avi_constants import AVIDataFiles
from common.lib.avi.avi_helper import AVIHelper
from common.lib.avi.avi_infra_operations import AVIInfraOps
from common.lib.avi.avi_template_operations import AVITemplateOperations
from common.lib.govc.govc_client import GOVClient
from common.lib.govc.govc_operations import GOVCOperations
from common.lib.vcenter.vcenter_ssl_operations import VCenterSSLOperations
from common.operation.constants import (
    AkoType,
    Cloud,
    ControllerLocation,
    Env,
    KubernetesOva,
    Paths,
    ResourcePoolAndFolderName,
    Tkg_version,
    Type,
    Versions,
    VrfType,
)
from common.operation.ShellHelper import runProcess, runShellCommandAndReturnOutputAsList
from common.replace_value import replaceValueSysConfig
from common.util.common_utils import CommonUtils
from common.util.file_helper import FileHelper
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.marketplace_util import MarketPlaceUtils
from common.util.saas_util import SaaSUtil
from common.util.service_engine_utils import ServiceEngineUtils
from common.util.ssl_helper import get_base64_cert
from common.util.tanzu_util import TanzuCommands, TanzuUtil
from common.workflows.nsx_alb_workflow import NsxAlbWorkflow


class MgmtWorkflow:
    def __init__(self):
        self.env = request.headers["Env"]
        spec_obj = CommonUtils.get_spec_obj(self.env)
        json_dict = request.get_json(force=True)
        self.spec: spec_obj = spec_obj.parse_obj(json_dict)

        vc_data = self.spec.envSpec.vcenterDetails
        self.vcenter_ip = vc_data.vcenterAddress
        self.vcenter_username = vc_data.vcenterSsoUser
        str_enc = str(vc_data.vcenterSsoPasswordBase64)
        self.password = CommonUtils.decode_password(str_enc)

        self.data_center = vc_data.vcenterDatacenter
        self.data_store = vc_data.vcenterDatastore

        self.data_center = self.data_center.replace(" ", "#remove_me#")
        self.data_store = self.data_store.replace(" ", "#remove_me#")

        self.vc_cluster_name = vc_data.vcenterCluster
        self.parent_resourcePool = vc_data.resourcePoolName

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

        self.avi_ip = NsxAlbWorkflow.get_alb_data_objects(self.spec, self.env)[0].aviController01Ip
        self.avi_password = CommonUtils.decode_password(
            str(NsxAlbWorkflow.get_alb_data_objects(self.spec, self.env)[0].aviPasswordBase64)
        )
        self.avi_base_ops = AVIBaseOperations(avi_host=self.avi_ip, avi_password=self.avi_password)
        self.avi_infra_ops = AVIInfraOps(
            self.avi_ip, self.avi_password, self.vcenter_ip, self.vcenter_username, self.password
        )
        self.cloud_name = Cloud.CLOUD_NAME if self.env == Env.VMC else Cloud.CLOUD_NAME.replace("vmc", "vsphere")
        self.se_group_name = (
            Cloud.SE_GROUP_NAME if self.env == Env.VMC else Cloud.SE_GROUP_NAME.replace("vmc", "vsphere")
        )
        self.mgmt_object = None
        self.se_util = ServiceEngineUtils(self.spec)
        self.avi_template_ops = AVITemplateOperations(self.avi_ip, self.avi_password, None)
        TanzuUtil(env=self.env, spec=self.spec)
        self.kubectl_util = KubectlUtil()
        self.license_type = self.spec.tkgComponentSpec.aviComponents.typeOfLicense

    def _get_mgmt_data_object(self):
        if self.env == Env.VSPHERE or Env.VCF:
            return self.spec.tkgComponentSpec.tkgMgmtComponents
        else:
            return self.spec.componentSpec.tkgMgmtSpec

    def _get_rp_and_folder(self):
        if self.env == Env.VSPHERE or Env.VCF:
            resource_pool = ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
            folder = ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE
        else:
            resource_pool = ResourcePoolAndFolderName.TKG_Mgmt_RP
            folder = ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder
        return resource_pool, folder

    def _create_templates_folder(self):
        if self.env == Env.VSPHERE or Env.VCF:
            folder_name = ResourcePoolAndFolderName.Template_Automation_Folder.replace("vmc", "vsphere")
        else:
            folder_name = ResourcePoolAndFolderName.Template_Automation_Folder

        response = self.vc_ssl_obj.create_folder(folder_name)
        if response is None:
            return None
        else:
            return "SUCCESS"

    def push_se_ova_to_vcenter(self, avi_uuid, ova_location):
        avi_rp = ResourcePoolAndFolderName.AVI_RP.replace("vmc", "vsphere")
        if self.parent_resourcePool is not None:
            resource_pool = (
                f"/{self.data_center}/host/{self.vc_cluster_name}/Resources/{self.parent_resourcePool}/{avi_rp}"
            )
        else:
            resource_pool = f"{self.data_center}/host/{self.vc_cluster_name}/Resources/{avi_rp}"
        replaceValueSysConfig(
            "./vsphere/managementConfig/importSeOva-vc.json",
            "Name",
            "name",
            ControllerLocation.SE_OVA_TEMPLATE_NAME.replace("vmc", "vsphere") + "_" + avi_uuid,
        )
        output = self.govc_client.import_se_ova(
            resource_pool,
            ResourcePoolAndFolderName.Template_Automation_Folder.replace("vmc", "vsphere"),
            "./vsphere/managementConfig/importSeOva-vc.json",
            ova_location,
        )
        if output is None or output == "":
            return None, "Failed import SE OVA to vCenter"
        return "SUCCESS", 200

    def configure_non_orchestrated_cloud(self, csrf, avi_version):
        if self._create_templates_folder() is None:
            return None, "Failed to create templates folder"

        cloud_status = self.avi_infra_ops.get_cloud_status(self.cloud_name)
        if cloud_status[0] is None:
            return None, f"Failed to get cloud status {cloud_status[1]}"
        if cloud_status[0] == "NOT_FOUND":
            for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                time.sleep(1)
            current_app.logger.info(f"Creating New cloud {self.cloud_name}")
            cloud = self.avi_infra_ops.create_new_cloud_arch(self.cloud_name)
            if cloud[0] is None:
                return None, f"Failed to create cloud - {cloud[1]}"
            cloud_url = cloud[0]
        else:
            cloud_url = cloud_status[0]

        current_app.logger.info(f"Cloud {self.cloud_name} url {cloud_url}")

        get_se_cloud = self.avi_infra_ops.get_SE_cloud_status(self.se_group_name)
        if get_se_cloud[0] is None:
            return None, f"Failed to get service engine cloud status {str(get_se_cloud[1])}"
        if get_se_cloud[0] == "NOT_FOUND":
            current_app.logger.info(f"Creating New SE Cloud {self.se_group_name}")
            cloud_se = self.avi_infra_ops.create_SE_cloud_arch(
                cloud_url, self.se_group_name, "Mgmt", license_type=self.license_type, datastore=self.data_store
            )
            if cloud_se[0] is None:
                return None, "Failed to create service engine cloud " + str(cloud_se[1])
            se_cloud_url = cloud_se[0]
        else:
            se_cloud_url = get_se_cloud[0]

        current_app.logger.info(f"SE Cloud {self.se_group_name} URL {se_cloud_url}")

        data_network = self.spec.tkgMgmtDataNetwork.tkgMgmtDataNetworkName
        get_wip = self.avi_infra_ops.get_vip_network(data_network)
        if get_wip[0] is None:
            return None, f"Failed to get service engine VIP network {str(get_wip[1])}"
        if get_wip[0] == "NOT_FOUND":
            current_app.logger.info(f"Creating New VIP network {data_network}")
            ip_net_mask = CommonUtils.seperate_netmask_and_ip(
                str(self.spec.tkgMgmtDataNetwork.tkgMgmtDataNetworkGatewayCidr)
            )
            start_ip = self.spec.tkgMgmtDataNetwork.tkgMgmtAviServiceIpStartRange
            end_ip = self.spec.tkgMgmtDataNetwork.tkgMgmtAviServiceIpEndRange
            vip_net = self.avi_infra_ops.create_vip_network(
                data_network, cloud_url, ip_net_mask[0], ip_net_mask[1], start_ip, end_ip
            )
            # vip_net = createVipNetwork(ip, csrf2, cloud_url, data_network, Type.MANAGEMENT, aviVersion)
            if vip_net[0] is None:
                return None, f"Failed to create VIP network {vip_net[1]}"
            wip_url = vip_net[0]
            wip_cluster_url = ""
            current_app.logger.info("Created New VIP network " + data_network)
        else:
            wip_url = get_wip[0]
            wip_cluster_url = ""

        current_app.logger.info(f"{data_network} URL {wip_url}")

        cluster_vip = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
        ip_net_mask = CommonUtils.seperate_netmask_and_ip(
            self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr
        )
        start_ip = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipIpStartRange
        end_ip = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipIpEndRange
        cidr = CommonUtils.seperate_netmask_and_ip(
            str(self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr)
        )
        get__cluster_wip = self.avi_infra_ops.get_vip_network(cluster_vip)
        if get__cluster_wip[0] is None:
            return None, "Failed to get cluster VIP network " + str(get__cluster_wip[1])
        if get__cluster_wip[0] == "NOT_FOUND":
            current_app.logger.info("Creating New cluster VIP network " + cluster_vip)
            vip_net = self.avi_infra_ops.create_vip_network(
                cluster_vip, cloud_url, ip_net_mask[0], ip_net_mask[1], start_ip, end_ip
            )
            if vip_net[0] is None:
                return None, "Failed to create cluster VIP network " + str(vip_net[1])
            wip_cluster_url = vip_net[0]
            current_app.logger.info("Created New cluster VIP network " + cluster_vip)
        else:
            wip_cluster_url = get__cluster_wip[0]

        current_app.logger.info(f"{cluster_vip} URL {wip_cluster_url}")

        get_vip_network_details = self.avi_infra_ops.get_network_details_vip(
            wip_cluster_url, start_ip, end_ip, cidr[0], cidr[1]
        )

        if get_vip_network_details[0] is None:
            return None, "Failed to get VIP network details " + str(get_vip_network_details[2])
        ip_pre = get_vip_network_details[2]["subnet_ip"] + "/" + str(get_vip_network_details[2]["subnet_mask"])
        current_app.logger.info(ip_pre)
        FileHelper.write_to_file(ip_pre, AVIDataFiles.VIP_IP_TXT)

        ipam_name = Cloud.IPAM_NAME if self.env == Env.VMC else Cloud.IPAM_NAME.replace("vmc", "vsphere")
        get_ipam = self.avi_template_ops.get_ipam(ipam_name)
        if get_ipam[0] is None:
            return None, "Failed to get service engine Ipam " + str(get_ipam[1])
        if get_ipam[0] == "NOT_FOUND":
            current_app.logger.info("Creating IPam " + self.se_group_name)
            ipam = self.avi_template_ops.create_ipam_arch(wip_url, wip_cluster_url, ipam_name)
            if ipam[0] is None:
                return None, "Failed to create  ipam " + str(ipam[1])
            ipam_url = ipam[0]
        else:
            current_app.logger.info(f"{ipam_name} ipam created successfully")
            ipam_url = get_ipam[0]

        new_cloud_status = self.avi_infra_ops.get_details_of_new_cloud_arch(cloud_url, ipam_url, se_cloud_url)
        if new_cloud_status[0] is None:
            return None, "Failed to get new cloud details" + str(new_cloud_status[1])
        update = self.avi_infra_ops.update_new_cloud(cloud_url)
        if update[0] is None:
            return None, "Failed to update cloud " + str(update[1])

        se_ova = self.avi_infra_ops.generate_se_ova(self.cloud_name)
        if se_ova[0] is None:
            return None, "Failed to generate service engine ova " + str(se_ova[1])

        current_app.logger.info(f"SE OVA for {self.cloud_name} cloud generated successfully")

        avi_vm_obj = self.vc_ssl_obj.check_VM_present(
            NsxAlbWorkflow.get_alb_data_objects(self.spec, self.env)[0].aviController01Fqdn
        )
        avi_uuid = avi_vm_obj.config.uuid
        se_download_ova = self.avi_infra_ops.download_se_ova(avi_uuid, self.cloud_name)
        if se_download_ova[0] is None:
            return None, "Failed to download service engine ova " + str(se_download_ova[1])
        se_ova_path = se_download_ova[2]
        current_app.logger.info("Getting token")
        token = self.se_util.generate_token(self.avi_ip, csrf, avi_version, self.cloud_name)
        if token[0] is None:
            return None, "Failed to  token " + str(token[1])

        current_app.logger.info("Get cluster uuid")
        uuid = self.se_util.get_cluster_uuid(self.avi_ip, csrf, avi_version)
        if uuid[0] is None:
            return None, "Failed to get cluster uuid " + str(uuid[1])

        se_group = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
        get_se_cloud_workload = self.avi_infra_ops.get_SE_cloud_status(se_group)
        if get_se_cloud_workload[0] is None:
            return None, "Failed to get service engine cloud status " + str(get_se_cloud_workload[1])
        if get_se_cloud_workload[0] == "NOT_FOUND":
            current_app.logger.info("Creating New service engine cloud " + se_group)
            cloud_se_workload = self.avi_infra_ops.create_SE_cloud_arch(
                cloud_url, se_group, "Workload", license_type=self.license_type, datastore=self.data_store
            )
            if cloud_se_workload[0] is None:
                return None, "Failed to create service engine cloud " + str(cloud_se_workload[1])
            se_cloud_url_workload = cloud_se_workload[0]
        else:
            se_cloud_url_workload = get_se_cloud_workload[0]
        current_app.logger.info(f"SE workload cloud url {se_cloud_url_workload}")

        self.se_util.replace_network_values_vsphere(
            self.avi_ip, token[0], uuid[0], "./vsphere/managementConfig/importSeOva-vc.json"
        )
        se_ova_template = (
            ControllerLocation.SE_OVA_TEMPLATE_NAME.replace("vmc", "vsphere")
            if self.env == Env.VSPHERE
            else ControllerLocation.SE_OVA_TEMPLATE_NAME
        )
        vm_state = self.vc_ssl_obj.check_VM_present(se_ova_template + "_" + avi_uuid)
        if vm_state is None:
            try:
                self.vc_ssl_obj.destroy_vm(
                    ResourcePoolAndFolderName.Template_Automation_Folder,
                    se_ova_template,
                )
            except Exception as e:
                current_app.logger.info(str(e))
            # if vm_state is None:      Removed this if, it was redundant
            current_app.logger.info("Pushing ova and marking it as template..")
            push = self.push_se_ova_to_vcenter(avi_uuid, se_ova_path)
            if push[0] is None:
                return None, "Failed to push service engine ova to vcenter " + str(push[1])
        else:
            current_app.logger.info("Service engine ova is already pushed to the vcenter")

        controller1 = (
            ControllerLocation.CONTROLLER_SE_NAME.replace("vmc", "vsphere")
            if self.env == Env.VSPHERE
            else ControllerLocation.CONTROLLER_SE_NAME
        )
        controller2 = (
            ControllerLocation.CONTROLLER_SE_NAME2.replace("vmc", "vsphere")
            if self.env == Env.VSPHERE
            else ControllerLocation.CONTROLLER_SE_NAME2
        )

        dep = self.se_util.controller_deployment(
            self.avi_ip,
            csrf,
            self.data_center,
            self.data_store,
            self.vc_cluster_name,
            self.vcenter_ip,
            self.vcenter_username,
            self.password,
            se_cloud_url,
            "./vsphere/managementConfig/se.json",
            "detailsOfServiceEngine1.json",
            "detailsOfServiceEngine2.json",
            controller1,
            controller2,
            1,
            Type.MANAGEMENT,
            0,
            avi_version,
        )
        if dep[1] != 200:
            return None, "Controller deployment failed " + str(dep[0])
        current_app.logger.info("Configured management cluster successfully")

        return "SUCCESS", "Configured non-orchestrated cloud for management cluster successfully"

    def get_cloud_url(self, cloud_name):
        get_cloud = self.avi_infra_ops.get_cloud_status(cloud_name)
        if get_cloud[0] is None:
            return None, "Failed to get cloud status " + str(get_cloud[1])

        is_gen = False
        req = True
        if get_cloud[0] == "NOT_FOUND":
            if req:
                for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                    time.sleep(1)
            is_gen = True
            current_app.logger.info("Creating New cloud " + cloud_name)
            if self.env == Env.VCF:
                nsx_password = CommonUtils.decode_password(str(self.spec.envSpec.vcenterDetails.nsxtUserPasswordBase64))
                nsx_user = self.spec.envSpec.vcenterDetails.nsxtUser
                nsx_address = self.spec.envSpec.vcenterDetails.nsxtAddress
                nsx_overlays = self.spec.envSpec.vcenterDetails.nsxtOverlay
                avi_mgmt = self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkName
                cluster_vip_nw = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
                teir1_route = self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName
                cloud = self.avi_infra_ops.create_nsxt_cloud(
                    nsx_address, nsx_user, nsx_password, nsx_overlays, teir1_route, avi_mgmt, cluster_vip_nw
                )

            else:
                cloud = self.avi_infra_ops.create_new_cloud(cloud_name, self.data_center, self.license_type)
            if cloud[0] is None:
                return None, "Failed to create cloud " + str(cloud[1])
            cloud_url = cloud[0]
        else:
            cloud_url = get_cloud[0]
        if is_gen:
            for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
                time.sleep(1)

        return cloud_url, "Obtained Cloud URL Successfully"

    def get_vip_pool(self, cloud_name):
        start_ip = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipIpStartRange
        end_ip = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipIpEndRange
        prefix_ip_netmask = CommonUtils.seperate_netmask_and_ip(
            self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr
        )

        vip_network = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
        get_vip = self.avi_infra_ops.get_network_url(vip_network, cloud_name)
        if get_vip[0] is None:
            return None, "Failed to get vip network " + str(get_vip[1])
        if self.env == Env.VSPHERE:
            vip_pool = self.avi_infra_ops.update_vip_network_ip_pools(
                get_vip[0], start_ip, end_ip, prefix_ip_netmask[0], prefix_ip_netmask[1]
            )
            if vip_pool[1] != 200:
                return None, str(vip_pool[0].json["msg"])
        else:
            network_details = self.avi_infra_ops.get_network_details_vip(
                get_vip[0], start_ip, end_ip, prefix_ip_netmask[0], prefix_ip_netmask[1]
            )
            if network_details[0] is None:
                return None, network_details[1]
            if network_details[0] == "AlreadyConfigured":
                subnet_ip = network_details[2]["subnet_ip"]
                mask = network_details[2]["subnet_mask"]
                ip_pre = str(subnet_ip) + "/" + str(mask)
                FileHelper.write_to_file(content=ip_pre, file=AVIDataFiles.VIP_IP_TXT)
            else:
                vip_pool = self.avi_infra_ops.update_network_with_ip_pools(get_vip[0])
                if vip_pool[0] != HTTPStatus.OK:
                    return None, vip_pool[1]
                subnet_ip = vip_pool[2]["subnet_ip"]
                mask = vip_pool[2]["subnet_mask"]
                ip_pre = str(subnet_ip) + "/" + str(mask)
                FileHelper.write_to_file(content=ip_pre, file=AVIDataFiles.VIP_IP_TXT)

        return get_vip[0], "VIP network details obtained successfully"

    def get_se_cloud_url(self, se_group_name, cloud_url, cluster_url, cloud_name):
        get_se_cloud = self.avi_infra_ops.get_SE_cloud_status(se_group_name)
        if get_se_cloud[0] is None:
            return None, "Failed to get service engine cloud status " + str(get_se_cloud[1])

        vc_content_library_name = self.spec.envSpec.vcenterDetails.contentLibraryName
        if not vc_content_library_name:
            vc_content_library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY

        if get_se_cloud[0] == "NOT_FOUND":
            current_app.logger.info("Creating New service engine cloud " + se_group_name)
            if self.env == Env.VCF:
                nsx_password = CommonUtils.decode_password(str(self.spec.envSpec.vcenterDetails.nsxtUserPasswordBase64))
                nsx_user = self.spec.envSpec.vcenterDetails.nsxtUser
                nsx_address = self.spec.envSpec.vcenterDetails.nsxtAddress
                nsx_overlays = self.spec.envSpec.vcenterDetails.nsxtOverlay
                nsx_cloud_info = self.avi_infra_ops.configure_vcenter_in_nsxt_cloud(
                    cloud_name,
                    cloud_url,
                    self.vc_cluster_name,
                    vc_content_library_name,
                    nsx_user,
                    nsx_password,
                    nsx_overlays,
                    nsx_address,
                )
                if nsx_cloud_info[0] is None:
                    return None, "Failed to configure vcenter in cloud " + str(nsx_cloud_info[1])
                current_app.logger.info("vCenter configuration in cloud successful")
                cloud_se = self.avi_infra_ops.create_nsxt_se_cloud(
                    cloud_url, se_group_name, nsx_cloud_info[1], "Mgmt", self.data_store, self.license_type
                )
            else:
                cloud_se = self.avi_infra_ops.create_se_cloud(
                    cloud_url, se_group_name, cluster_url, self.data_store, "Mgmt", self.license_type
                )
            if cloud_se[0] is None:
                return None, "Failed to create service engine cloud " + str(cloud_se[1])
            se_cloud_url = cloud_se[0]
        else:
            se_cloud_url = get_se_cloud[0]

        return se_cloud_url, "Obtained se cloud URL successfully"

    def get_vrf_url(self, uuid):
        prefix_ip_netmask_vip = CommonUtils.seperate_netmask_and_ip(
            self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr
        )
        vrf_avi_mgmt = self.avi_infra_ops.get_vrf_and_next_route_id(uuid, VrfType.GLOBAL, prefix_ip_netmask_vip[0])
        if vrf_avi_mgmt[0] is None or vrf_avi_mgmt[1] == "NOT_FOUND":
            return None, "AVI mgmt Vrf not found " + str(vrf_avi_mgmt[1])

        if vrf_avi_mgmt[1] != "Already_Configured":
            ad = self.avi_infra_ops.add_static_route(vrf_avi_mgmt[0], prefix_ip_netmask_vip[0], vrf_avi_mgmt[1])
            if ad[0] is None:
                return None, "Failed to add static route " + str(ad[1])
        teir1name = self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName
        vrf_vip = self.avi_infra_ops.get_vrf_and_next_route_id(uuid, teir1name, prefix_ip_netmask_vip[0])
        if vrf_vip[0] is None or vrf_vip[1] == "NOT_FOUND":
            return None, "Cluster vip Vrf not found " + str(vrf_vip[1])
        if vrf_vip[1] != "Already_Configured":
            ad = self.avi_infra_ops.add_static_route(vrf_vip[0], prefix_ip_netmask_vip[0], vrf_vip[1])
            if ad[0] is None:
                return None, "Failed to add static route " + str(ad[1])
        vrf_url = vrf_vip[0]

        return vrf_url, "Obtained VRF URL successfully"

    def configure_orchestrated_cloud(self):
        cloud_name = (
            Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt") if self.env == Env.VCF else Cloud.CLOUD_NAME_VSPHERE
        )

        se_group_name = (
            Cloud.SE_GROUP_NAME_VSPHERE
            if self.env == Env.VSPHERE
            else Cloud.SE_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
        )

        cloud_url, msg = self.get_cloud_url(cloud_name)
        if cloud_url is None:
            return None, msg

        current_app.logger.info(f"{msg} {cloud_url}")

        mgmt_pg = self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkName
        cidr = CommonUtils.seperate_netmask_and_ip(
            str(self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkGatewayCidr)
        )
        start_ip = self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtServiceIpStartRange
        end_ip = self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtServiceIpEndRange
        get_management = self.avi_infra_ops.get_network_url(mgmt_pg, cloud_name)
        if get_management[0] is None:
            return None, "Failed to get management network " + str(get_management[1])
        network_url = get_management[0]

        current_app.logger.info(f"{mgmt_pg} network URL {network_url}")

        if self.env == Env.VSPHERE:
            get_management_details = self.avi_infra_ops.get_network_details(network_url)
            if get_management_details[0] is None:
                return None, "Failed to get management network details " + str(get_management_details[2])
            if get_management_details[0] == "AlreadyConfigured":
                current_app.logger.info("Ip pools are already configured.")
                if self.env == Env.VSPHERE:
                    vim_ref = get_management_details[2]["vim_ref"]
                subnet_ip = get_management_details[2]["subnet_ip"]
                mask = get_management_details[2]["subnet_mask"]
            else:
                AVIHelper.generate_vsphere_configured_subnets(
                    begin_ip=start_ip, end_ip=end_ip, prefix_ip=cidr[0], prefix_mask=cidr[1]
                )
                update_resp = self.avi_infra_ops.update_network_with_ip_pools(network_url)
                if update_resp[0] != HTTPStatus.OK:
                    return None, "Failed to update management network ip pools " + str(update_resp[1])
                if self.env == Env.VSPHERE:
                    vim_ref = update_resp[2]["vimref"]
                mask = update_resp[2]["subnet_mask"]
                subnet_ip = update_resp[2]["subnet_ip"]

            # if self.env == Env.VSPHERE:
            new_cloud_status = self.avi_infra_ops.get_details_of_new_cloud(cloud_url, vim_ref, subnet_ip, mask)
            if new_cloud_status[0] is None:
                return None, "Failed to get new cloud details" + str(new_cloud_status[1])
            update_new_cloud_status = self.avi_infra_ops.update_new_cloud(cloud_url)
            if update_new_cloud_status[0] is None:
                return None, "Failed to update cloud " + str(update_new_cloud_status[1])
            mgmt_data_pg = self.spec.tkgMgmtDataNetwork.tkgMgmtDataNetworkName
            mgmt_data_cidr = CommonUtils.seperate_netmask_and_ip(
                str(self.spec.tkgMgmtDataNetwork.tkgMgmtDataNetworkGatewayCidr)
            )
            mgmt_data_start = self.spec.tkgMgmtDataNetwork.tkgMgmtAviServiceIpStartRange
            mgmt_data_end = self.spec.tkgMgmtDataNetwork.tkgMgmtAviServiceIpEndRange
            get_management_data_pg = self.avi_infra_ops.get_network_url(mgmt_data_pg, cloud_name)
            if get_management_data_pg[0] is None:
                return None, "Failed to get management data network details " + str(get_management_data_pg[1])

            get_management_details_data_pg = self.avi_infra_ops.get_network_details(get_management_data_pg[0])
            if get_management_details_data_pg[0] is None:
                return None, "Failed to get management data network details " + str(get_management_details_data_pg[2])
            if get_management_details_data_pg[0] == "AlreadyConfigured":
                current_app.logger.info("Ip pools are already configured.")
            else:
                AVIHelper.generate_vsphere_configured_subnets(
                    begin_ip=mgmt_data_start,
                    end_ip=mgmt_data_end,
                    prefix_ip=mgmt_data_cidr[0],
                    prefix_mask=mgmt_data_cidr[1],
                )
                update_resp = self.avi_infra_ops.update_network_with_ip_pools(get_management_data_pg[0])
                if update_resp[0] != 200:
                    return None, "Failed to update management network details " + str(update_resp[1])

        vip_url, msg = self.get_vip_pool(cloud_name)
        if vip_url is None:
            return None, msg

        current_app.logger.info(f"Cluster VIP URL {vip_url}")

        cluster_url = None
        if self.env == Env.VSPHERE:
            get_ipam = self.avi_template_ops.get_ipam(Cloud.IPAM_NAME_VSPHERE)
            if get_ipam[0] is None:
                return None, "Failed to get service engine Ipam " + str(get_ipam[1])
            if get_ipam[0] == "NOT_FOUND":
                current_app.logger.info("Creating IPam " + Cloud.IPAM_NAME_VSPHERE)
                ipam = self.avi_template_ops.create_ipam(
                    network_url, get_management_data_pg[0], vip_url, Cloud.IPAM_NAME_VSPHERE
                )
                if ipam[0] is None:
                    return None, "Failed to create Ipam " + str(ipam[1])
                ipam_url = ipam[0]
            else:
                ipam_url = get_ipam[0]

            new_cloud_status = self.avi_infra_ops.get_details_of_new_cloud_add_ipam(cloud_url, ipam_url)
            if new_cloud_status[0] is None:
                return None, "Failed to get new cloud details" + str(new_cloud_status[1])
            update_ipam_response = self.avi_template_ops.update_ipam(cloud_url)
            if update_ipam_response[0] is None:
                return None, "Failed to update Ipam to cloud " + str(update_ipam_response[1])

            cluster_status = self.avi_infra_ops.get_cluster_url(self.vc_cluster_name)
            if cluster_status[0] is None or cluster_status[0] == "NOT_FOUND":
                return None, "Failed to get cluster details" + str(cluster_status[1])
            cluster_url = cluster_status[0]

        se_cloud_url, msg = self.get_se_cloud_url(se_group_name, cloud_url, cluster_url, cloud_name)
        if se_cloud_url is None:
            return None, msg

        current_app.logger.info(f"SE cloud url is {se_cloud_url}")

        clo = (
            Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
            if self.env == Env.VSPHERE
            else Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
        )
        get_se_cloud_workload = self.avi_infra_ops.get_SE_cloud_status(clo)
        if get_se_cloud_workload[0] is None:
            return None, "Failed to get service engine cloud status " + str(get_se_cloud_workload[1])
        if get_se_cloud_workload[0] == "NOT_FOUND":
            current_app.logger.info("Creating New service engine cloud " + clo)
            cloud_se_workload = self.avi_infra_ops.create_SE_cloud_arch(
                cloud_url, clo, "Workload", license_type=self.license_type, datastore=self.data_store
            )
            if cloud_se_workload[0] is None:
                return None, "Failed to create service engine cloud " + str(cloud_se_workload[1])
            se_cloud_url_workload = cloud_se_workload[0]
        else:
            se_cloud_url_workload = get_se_cloud_workload[0]
        current_app.logger.info(f"SE workload cloud url {se_cloud_url_workload}")
        if self.env == Env.VSPHERE:
            mgmt_name = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtNetworkName
            dhcp = self.avi_infra_ops.enable_dhcp(mgmt_name, cloud_name)
            if dhcp[0] is None:
                return None, "Failed to enable dhcp " + str(dhcp[1])

        with open("./newCloudInfo.json", "r") as file2:
            new_cloud_json = json.load(file2)
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except Exception:
            for re in new_cloud_json["results"]:
                if re["name"] == cloud_name:
                    uuid = re["uuid"]
        if uuid is None:
            return None, "NOT_FOUND"

        tier1 = ""
        vrf_url = ""

        if self.env == Env.VSPHERE:
            ip_net_mask = CommonUtils.seperate_netmask_and_ip(
                self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkGatewayCidr
            )
            vrf = self.avi_infra_ops.get_vrf_and_next_route_id(uuid, VrfType.MANAGEMENT, ip_net_mask[0])
            if vrf[0] is None or vrf[1] == "NOT_FOUND":
                return None, "Vrf not found " + str(vrf[1])
            if vrf[1] != "Already_Configured":
                ad = self.avi_infra_ops.add_static_route(vrf[0], ip_net_mask[0], vrf[1])
                if ad[0] is None:
                    return None, "Failed to add static route " + str(ad[1])
        else:
            status, value = self.avi_infra_ops._get_cloud_connect_user()
            nsxt_cred = value["nsxUUid"]
            teir1name = self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName
            nsx_address = str(self.spec.envSpec.vcenterDetails.nsxtAddress)
            tier1_id, status_tier1 = self.avi_infra_ops.fetch_tier1_gateway_id(nsxt_cred, teir1name, nsx_address)
            if tier1_id is None:
                return None, "Failed to get Tier 1 details " + str(status_tier1)
            tier1 = status_tier1

            vrf_url, msg = self.get_vrf_url(uuid)
            if vrf_url is None:
                return None, msg

            # replace getNsxTNetworkDetails function
            get_management_details = self.avi_infra_ops.get_network_details(network_url)
            if get_management_details[0] is None:
                return None, "Failed to get AVI management network details " + str(get_management_details[2])
            if get_management_details[0] == "AlreadyConfigured":
                current_app.logger.info("Ip pools are already configured.")
                subnet_ip = get_management_details[2]["subnet_ip"]
                mask = get_management_details[2]["subnet_mask"]
            else:
                current_app.logger.info("Network details not found, updating them")
                cidr = CommonUtils.seperate_netmask_and_ip(
                    str(self.spec.tkgComponentSpec.aviMgmtNetwork.aviMgmtNetworkGatewayCidr)
                )
                AVIHelper.generate_vsphere_configured_subnets_for_se(start_ip, end_ip, cidr[0], cidr[1])
                update_resp = self.avi_infra_ops.update_network_with_ip_pools(network_url)
                if update_resp[0] != 200:
                    return None, "Failed to update management network ip pools " + str(update_resp[1])
                mask = update_resp[2]["subnet_mask"]
                subnet_ip = update_resp[2]["subnet_ip"]
            ipam_name = Cloud.IPAM_NAME_VSPHERE.replace("vsphere", "nsxt")
            get_ipam = self.avi_template_ops.get_ipam(ipam_name)
            if get_ipam[0] is None:
                return None, "Failed to get service engine Ipam " + str(get_ipam[1])
            if get_ipam[0] == "NOT_FOUND":
                current_app.logger.info("Creating IPam " + ipam_name)
                ipam = self.avi_template_ops.create_ipam_nsxt_cloud(vip_url, network_url, ipam_name)
                if ipam[0] is None:
                    return None, "Failed to create Ipam " + str(ipam[1])
                ipam_url = ipam[0]
            else:
                ipam_url = get_ipam[0]

            current_app.logger.info(f"{ipam_name} URL {ipam_url}")

            dns_profile_name = "tkg-nsxt-dns"
            search_domain = self.spec.envSpec.infraComponents.searchDomains
            get_dns = self.avi_template_ops.get_ipam(dns_profile_name)
            if get_dns[0] is None:
                return None, "Failed to get service engine Ipam " + str(get_dns[1])
            if get_dns[0] == "NOT_FOUND":
                dns = self.avi_template_ops.create_dns_nsxt_cloud(search_domain, dns_profile_name)
                if dns[0] is None:
                    return None, "Failed to create Nsxt dns " + str(dns[1])
                dns_url = dns[0]
            else:
                current_app.logger.info("Dns already created")
                dns_url = get_dns[0]

            current_app.logger.info(f"DNS URL is {dns_url}")

            ipam_asso = self.avi_template_ops.associate_ipam_nsxt_cloud(uuid, ipam_url, dns_url)
            if ipam_asso[0] is None:
                return None, "Failed to associate Ipam and dns to cloud " + str(ipam_asso[1])

        current_app.logger.info(f"Waiting for cloud placement status to be ready for {cloud_name}")
        default = self.avi_infra_ops.wait_for_cloud_placement(cloud_name)
        if default[0] is None:
            return None, "Failed to get " + cloud_name + " cloud status"

        # replace this function create_virtual_service
        virtual_service, error = self.avi_infra_ops.create_virtual_service(
            uuid, se_group_name, vip_url, 2, tier1, vrf_url
        )
        if virtual_service is None:
            return None, "Failed to create virtual service " + str(error)

        current_app.logger.info("Configured management cluster cloud successfully")

        return "SUCCESS", "Configured management cluster cloud successfully"

    def update_template_in_ova(self):
        # update bom with custom ova template
        tkr_files = os.listdir(Env.BOM_FILE_LOCATION)
        tkr_file = ""
        for fl in tkr_files:
            if fl.startswith("tkr-bom"):
                tkr_file = os.path.join(Env.BOM_FILE_LOCATION, fl)
                break
        else:
            raise Exception(f"tkr-bom files are not available inside {Env.BOM_FILE_LOCATION}")
        yaml_data = FileHelper.load_yaml(spec_path=tkr_file)
        ova_data = yaml_data["ova"]
        for data in ova_data:
            if data["name"] == "ova-ubuntu-2004":
                data["version"] = Versions.COMPLIANT_OVA_TEMPLATE
        FileHelper.dump_yaml(data=yaml_data, file_path=tkr_file)

    def templateMgmtDeployYaml(self, avi_version, wp_network_name, wip_network_ip_netmask):
        tkg_cluster_vip_network_name = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
        cluster_vip_cidr = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkGatewayCidr
        mgmt_group_name = Cloud.SE_GROUP_NAME_VSPHERE
        workload_group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
        tier1_path = ""
        if self.env == Env.VCF:
            mgmt_group_name = Cloud.SE_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
            workload_group_name = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE.replace("vsphere", "nsxt")
            status, value = self.avi_infra_ops._get_cloud_connect_user()
            nsxt_cred = value["nsxUUid"]
            teir1name = self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName
            nsx_address = str(self.spec.envSpec.vcenterDetails.nsxtAddress)
            tier1_id, status_tier1 = self.avi_infra_ops.fetch_tier1_gateway_id(nsxt_cred, teir1name, nsx_address)
            if tier1_id is None:
                return None, "Failed to get Tier 1 details " + str(status_tier1)
            tier1_path = status_tier1
        deploy_yaml = FileHelper.read_resource(Paths.TKG_MGMT_SPEC_J2)
        t = Template(deploy_yaml)
        datastore_path = "/" + self.data_center + "/datastore/" + self.data_store
        vsphere_folder_path = (
            "/" + self.data_center + "/vm/" + ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE
        )
        management_cluster = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
        FileHelper.delete_file(Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml")
        parent_resource_pool = self.parent_resourcePool
        if parent_resource_pool:
            vsphere_rp = (
                "/"
                + self.data_center
                + "/host/"
                + self.vc_cluster_name
                + "/Resources/"
                + parent_resource_pool
                + "/"
                + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
            )
        else:
            vsphere_rp = (
                "/"
                + self.data_center
                + "/host/"
                + self.vc_cluster_name
                + "/Resources/"
                + ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE
            )
        datacenter = "/" + self.data_center
        ssh_key = CommonUtils.runSsh(self.vcenter_username)
        size = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtSize
        control_plane_vcpu = ""
        control_plane_disk_gb = ""
        control_plane_mem_mb = ""
        proxy_cert = ""
        try:
            proxy_cert_raw = self.spec.envSpec.proxySpec.tkgMgmt.proxyCert
            base64_bytes = base64.b64encode(proxy_cert_raw.encode("utf-8"))
            proxy_cert = str(base64_bytes, "utf-8")
            isProxy = "true"
        except Exception:
            isProxy = "false"
            current_app.logger.info("Proxy certificate for  Management is not provided")
        ciep = self.spec.envSpec.ceipParticipation
        if size.lower() == "small":
            current_app.logger.debug(
                "Recommended size for Management cluster nodes is: medium/large/extra-large/custom"
            )
        elif size.lower() == "medium":
            pass
        elif size.lower() == "large":
            pass
        elif size.lower() == "extra-large":
            pass
        elif size.lower() == "custom":
            control_plane_vcpu = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtCpuSize
            control_plane_disk_gb = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtStorageSize
            control_plane_mem_gb = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtMemorySize
            control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
        else:
            current_app.logger.error(
                "Provided cluster size: "
                + size
                + "is not supported, please provide one of: medium/large/extra-large/custom"
            )
            return (
                None,
                f"Provided cluster size {size} is not supported, please provide one of: medium/large/extra-large/custom",
            )
        try:
            osName = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtBaseOs
            if osName == "photon":
                osVersion = "3"
            elif osName == "ubuntu":
                osVersion = "20.04"
            else:
                raise Exception("Wrong os name provided")
        except Exception as e:
            raise Exception("Keyword " + str(e) + "  not found in input file")
        with open(AVIDataFiles.VIP_IP_TXT, "r") as e:
            vip_ip = e.read()
        tkg_cluster_vip_network_cidr = vip_ip
        air_gapped_repo = ""
        repo_certificate = ""
        if CommonUtils.is_airGapped_enabled(self.env, self.spec):
            air_gapped_repo = self.spec.envSpec.customRepositorySpec.tkgCustomImageRepository
            air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
            os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
            getBase64CertWriteToFile(
                CommonUtils.grab_host_from_url(air_gapped_repo), CommonUtils.grab_port_from_url(air_gapped_repo)
            )
            with open("cert.txt", "r") as file2:
                repo_cert = file2.readline()
            repo_certificate = repo_cert
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
        # compliant deployment flogs for TKGm deployment
        if CommonUtils.is_env_tkgm(self.env, self.spec) or self.env == Env.VCF:
            compliant_flag = self.spec.envSpec.compliantSpec.compliantDeployment
            if compliant_flag.lower() == "true":
                if osName != "ubuntu":
                    raise Exception("Wrong os name provided for complaint deployment, please use ubuntu as OS")
                current_app.logger.info("Performing compliant enable deployment.")
                os.putenv("TKG_CUSTOM_COMPATIBILITY_IMAGE_PATH", "fips/tkg-compatibility")
                # copy fips enabled overlays
                os.system(f"cp -rf common/overlays/04_user_customizations/  {Env.UPDATED_YTT_FILE_LOCATION}/")
                # remove old bom
                current_app.logger.info("Customized FIPS enabled overlay has been copied.")
                FileHelper.delete_file(f"{Env.BOM_FILE_LOCATION}/")
                FileHelper.delete_file(f"{Env.COMPATIBILITY_FILE_LOCATION}/")
                FileHelper.delete_file(f"{Env.CACHE_FILE_LOCATION}/")
                # fetch new bom for fips deployment
                # Update with RTM
                list_of_cmd = TanzuCommands.PLUGIN_SYNC
                runProcess(list_of_cmd)
                list_of_cmd = TanzuCommands.CONFIG_INIT
                runProcess(list_of_cmd)
                self.update_template_in_ova()
            else:
                os.putenv("TKG_CUSTOM_COMPATIBILITY_IMAGE_PATH", "tkg-compatibility")
            ceip = str(self.spec.envSpec.ceipParticipation)
            if ceip.lower() == "true":
                os.putenv("TANZU_CLI_CEIP_OPT_IN_PROMPT_ANSWER", "Yes")
            else:
                os.putenv("TANZU_CLI_CEIP_OPT_IN_PROMPT_ANSWER", "No")
            list_of_cmd = TanzuCommands.ACCEPT_EULA
            runProcess(list_of_cmd)
            list_of_cmd = TanzuCommands.INSTALL_PLUGIN
            runProcess(list_of_cmd)
        if CommonUtils.is_identity_management_enabled(self.env, self.spec):
            try:
                identity_mgmt_type = self.spec.tkgComponentSpec.identityManagementSpec.identityManagementType
                if identity_mgmt_type.lower() == "oidc":
                    oidc_provider_client_id = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.oidcSpec.oidcClientId
                    )
                    oidc_provider_client_secret = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.oidcSpec.oidcClientSecret
                    )
                    oidc_provider_groups_claim = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.oidcSpec.oidcGroupsClaim
                    )
                    oidc_provider_issuer_url = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.oidcSpec.oidcIssuerUrl
                    )
                    oidc_provider_scopes = str(self.spec.tkgComponentSpec.identityManagementSpec.oidcSpec.oidcScopes)
                    oidc_provider_username_claim = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.oidcSpec.oidcUsernameClaim
                    )
                    FileHelper.write_to_file(
                        t.render(
                            config=self.spec,
                            avi_cert=get_base64_cert(self.avi_ip),
                            ip=self.avi_ip,
                            wpName=wp_network_name,
                            wipIpNetmask=wip_network_ip_netmask,
                            ceip=ciep,
                            isProxyCert=isProxy,
                            proxyCert=proxy_cert,
                            avi_label_key=AkoType.KEY,
                            avi_label_value=AkoType.VALUE,
                            cluster_name=management_cluster,
                            data_center=datacenter,
                            datastore_path=datastore_path,
                            vsphere_folder_path=vsphere_folder_path,
                            vcenter_passwd=self.spec.envSpec.vcenterDetails.vcenterSsoPasswordBase64,
                            vsphere_rp=vsphere_rp,
                            vcenter_ip=self.vcenter_ip,
                            ssh_key=ssh_key,
                            vcenter_username=self.vcenter_username,
                            size_controlplane=size.lower(),
                            size_worker=size.lower(),
                            tkg_cluster_vip_network_cidr=tkg_cluster_vip_network_cidr,
                            air_gapped_repo=air_gapped_repo,
                            repo_certificate=repo_certificate,
                            osName=osName,
                            osVersion=osVersion,
                            avi_version=avi_version,
                            env=self.env,
                            tier1_path=tier1_path,
                            vip_cidr=cluster_vip_cidr,
                            tkg_cluster_vip_network_name=tkg_cluster_vip_network_name,
                            management_group=mgmt_group_name,
                            workload_group=workload_group_name,
                            size=size,
                            control_plane_vcpu=control_plane_vcpu,
                            control_plane_disk_gb=control_plane_disk_gb,
                            control_plane_mem_mb=control_plane_mem_mb,
                            identity_mgmt_type=identity_mgmt_type,
                            oidc_provider_client_id=oidc_provider_client_id,
                            oidc_provider_client_secret=oidc_provider_client_secret,
                            oidc_provider_groups_claim=oidc_provider_groups_claim,
                            oidc_provider_issuer_url=oidc_provider_issuer_url,
                            oidc_provider_scopes=oidc_provider_scopes,
                            oidc_provider_username_claim=oidc_provider_username_claim,
                        ),
                        Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml",
                    )
                elif identity_mgmt_type.lower() == "ldap":
                    ldap_endpoint_ip = str(self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapEndpointIp)
                    ldap_endpoint_port = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapEndpointPort
                    )
                    str_enc = str(self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapBindPWBase64)
                    base64_bytes = str_enc.encode("ascii")
                    enc_bytes = base64.b64decode(base64_bytes)
                    ldap_endpoint_bind_pw = enc_bytes.decode("ascii").rstrip("\n")
                    ldap_bind_dn = str(self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapBindDN)
                    ldap_user_search_base_dn = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapUserSearchBaseDN
                    )
                    ldap_user_search_filter = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapUserSearchFilter
                    )
                    ldap_user_search_uname = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapUserSearchUsername
                    )
                    ldap_grp_search_base_dn = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapGroupSearchBaseDN
                    )
                    ldap_grp_search_filter = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapGroupSearchFilter
                    )
                    ldap_grp_search_user_attr = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapGroupSearchUserAttr
                    )
                    ldap_grp_search_grp_attr = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapGroupSearchGroupAttr
                    )
                    ldap_grp_search_name_attr = str(
                        self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapGroupSearchNameAttr
                    )
                    ldap_root_ca_data = str(self.spec.tkgComponentSpec.identityManagementSpec.ldapSpec.ldapRootCAData)
                    if not ldap_user_search_base_dn:
                        current_app.logger.error("Please provide ldapUserSearchBaseDN for installing pinniped")
                        return None, "Please provide ldapUserSearchBaseDN for installing pinniped"
                    if not ldap_grp_search_base_dn:
                        current_app.logger.error("Please provide ldapGroupSearchBaseDN for installing pinniped")
                        return None, "Please provide ldapGroupSearchBaseDN for installing pinniped"
                    base64_bytes = base64.b64encode(ldap_root_ca_data.encode("utf-8"))
                    ldap_root_ca_data_base64 = str(base64_bytes, "utf-8")
                    FileHelper.write_to_file(
                        t.render(
                            config=self.spec,
                            avi_cert=get_base64_cert(self.avi_ip),
                            ip=self.avi_ip,
                            wpName=wp_network_name,
                            wipIpNetmask=wip_network_ip_netmask,
                            ceip=ciep,
                            isProxyCert=isProxy,
                            proxyCert=proxy_cert,
                            avi_label_key=AkoType.KEY,
                            avi_label_value=AkoType.VALUE,
                            cluster_name=management_cluster,
                            data_center=datacenter,
                            datastore_path=datastore_path,
                            vsphere_folder_path=vsphere_folder_path,
                            vcenter_passwd=self.spec.envSpec.vcenterDetails.vcenterSsoPasswordBase64,
                            vsphere_rp=vsphere_rp,
                            vcenter_ip=self.vcenter_ip,
                            ssh_key=ssh_key,
                            vcenter_username=self.vcenter_username,
                            size_controlplane=size.lower(),
                            size_worker=size.lower(),
                            tkg_cluster_vip_network_cidr=tkg_cluster_vip_network_cidr,
                            air_gapped_repo=air_gapped_repo,
                            repo_certificate=repo_certificate,
                            osName=osName,
                            osVersion=osVersion,
                            avi_version=avi_version,
                            env=self.env,
                            tier1_path=tier1_path,
                            vip_cidr=cluster_vip_cidr,
                            tkg_cluster_vip_network_name=tkg_cluster_vip_network_name,
                            management_group=mgmt_group_name,
                            workload_group=workload_group_name,
                            size=size,
                            control_plane_vcpu=control_plane_vcpu,
                            control_plane_disk_gb=control_plane_disk_gb,
                            control_plane_mem_mb=control_plane_mem_mb,
                            identity_mgmt_type=identity_mgmt_type,
                            ldap_endpoint_ip=ldap_endpoint_ip,
                            ldap_endpoint_port=ldap_endpoint_port,
                            ldap_endpoint_bind_pw=ldap_endpoint_bind_pw,
                            ldap_bind_dn=ldap_bind_dn,
                            ldap_user_search_base_dn=ldap_user_search_base_dn,
                            ldap_user_search_filter=ldap_user_search_filter,
                            ldap_user_search_uname=ldap_user_search_uname,
                            ldap_grp_search_base_dn=ldap_grp_search_base_dn,
                            ldap_grp_search_filter=ldap_grp_search_filter,
                            ldap_grp_search_user_attr=ldap_grp_search_user_attr,
                            ldap_grp_search_grp_attr=ldap_grp_search_grp_attr,
                            ldap_grp_search_name_attr=ldap_grp_search_name_attr,
                            ldap_root_ca_data_base64=ldap_root_ca_data_base64,
                        ),
                        Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml",
                    )
                else:
                    raise Exception("Wrong Identity Management type provided, accepted values are: oidc or ldap")
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
        else:
            FileHelper.write_to_file(
                t.render(
                    config=self.spec,
                    avi_cert=get_base64_cert(self.avi_ip),
                    ip=self.avi_ip,
                    wpName=wp_network_name,
                    wipIpNetmask=wip_network_ip_netmask,
                    avi_label_key=AkoType.KEY,
                    avi_label_value=AkoType.VALUE,
                    cluster_name=management_cluster,
                    data_center=datacenter,
                    datastore_path=datastore_path,
                    ceip=ciep,
                    isProxyCert=isProxy,
                    proxyCert=proxy_cert,
                    vsphere_folder_path=vsphere_folder_path,
                    vcenter_passwd=self.spec.envSpec.vcenterDetails.vcenterSsoPasswordBase64,
                    vsphere_rp=vsphere_rp,
                    vcenter_ip=self.vcenter_ip,
                    ssh_key=ssh_key,
                    vcenter_username=self.vcenter_username,
                    size_controlplane=size.lower(),
                    size_worker=size.lower(),
                    avi_version=avi_version,
                    env=self.env,
                    tier1_path=tier1_path,
                    vip_cidr=cluster_vip_cidr,
                    tkg_cluster_vip_network_name=tkg_cluster_vip_network_name,
                    management_group=mgmt_group_name,
                    workload_group=workload_group_name,
                    tkg_cluster_vip_network_cidr=tkg_cluster_vip_network_cidr,
                    air_gapped_repo=air_gapped_repo,
                    repo_certificate=repo_certificate,
                    osName=osName,
                    osVersion=osVersion,
                    size=size,
                    control_plane_vcpu=control_plane_vcpu,
                    control_plane_disk_gb=control_plane_disk_gb,
                    control_plane_mem_mb=control_plane_mem_mb,
                ),
                Paths.CLUSTER_PATH + management_cluster + "/management_cluster_vsphere.yaml",
            )
        return "SUCCESS", "SUCCESS"

    def create_cluster_folder(self, cluster_name):
        return CommonUtils.create_directory(f"{Paths.CLUSTER_PATH}{cluster_name}/")

    def configure_airgap_variables(self, cluster_deployed):
        try:
            if CommonUtils.is_airGapped_enabled(self.env, self.spec):
                if not cluster_deployed:
                    air_gapped_repo = str(self.spec.envSpec.customRepositorySpec.tkgCustomImageRepository)
                    air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
                    os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
                    os.putenv("TKG_CUSTOM_COMPATIBILITY_IMAGE_PATH", "tkg-compatibility")
                else:
                    command = "tanzu plugin sync"
                    runShellCommandAndReturnOutputAsList(command)
            else:
                current_app.logger.info("Custom Repo details not found, considering this as internet environment")
                if cluster_deployed:
                    command = "tanzu plugin install --group vmware-tkg/default:v2.4.0"
                    runShellCommandAndReturnOutputAsList(command)
        except Exception as e:
            raise Exception(str(e))

    def deploy_cluster(self, management_cluster, data_network, wip_mask):
        try:
            avi_version = self.avi_base_ops.obtain_avi_version()
            if avi_version[0] is None:
                return None, f"Failed to obtain deployed NSX ALB version {avi_version[1]}"
            avi_version = avi_version[0]

            if not TanzuUtil.get_cluster_status_on_tanzu(management_cluster, "management"):
                os.system("rm -rf kubeconfig.yaml")
                self.templateMgmtDeployYaml(avi_version, data_network, wip_mask)
                current_app.logger.info("Deploying management cluster")
                os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
                yaml_path = f"{Paths.CLUSTER_PATH}{management_cluster}/management_cluster_vsphere.yaml"
                list_of_cmd = TanzuCommands.CREATE_MGMT_CLUSTER.format(file_path=yaml_path)
                runProcess(list_of_cmd)
                list_of_cmd_kube = TanzuCommands.GET_MANAGEMENT_CLUSTER_CONTEXT.format(cluster_name=management_cluster)
                list_of_cmd_kube = list_of_cmd_kube + " --export-file kubeconfig.yaml"
                runProcess(list_of_cmd_kube)
                current_app.logger.info("Waiting for 1 min for status==ready")
                time.sleep(60)
                if not TanzuUtil.verify_cluster(management_cluster):
                    return None, f"{management_cluster} is not deployed"
                return "SUCCESS", 200
            else:
                return "SUCCESS", 200
        except Exception as e:
            return None, str(e)

    def enable_identity_management(self):
        if CommonUtils.is_identity_management_enabled(self.env, self.spec):
            management_cluster = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
            if not TanzuUtil.verify_cluster(management_cluster):
                return None, f"{management_cluster} is not deployed"

            switch = TanzuUtil.switch_to_management_context(management_cluster)
            if switch[1] != 200:
                current_app.logger.info(switch[0])
                return None, switch[0]
            # if checkEnableIdentityManagement(env):
            current_app.logger.info("Validating pinnipped installation status")
            check_pinniped = TanzuUtil.check_pinniped_installed()
            if check_pinniped[1] != 200:
                current_app.logger.error(check_pinniped[0])
                return None, check_pinniped[0]
            current_app.logger.info("Validating pinniped service status")
            check_pinniped_svc = self.kubectl_util.check_pinniped_service_status()
            if check_pinniped_svc[1] != 200:
                current_app.logger.error(check_pinniped_svc[0])
                return None, check_pinniped_svc[0]

            current_app.logger.info("Successfully validated Pinniped service status")
            identity_mgmt_type = str(self.spec.tkgComponentSpec.identityManagementSpec.identityManagementType)
            if identity_mgmt_type.lower() == "ldap":
                check_pinniped_dexsvc = self.kubectl_util.check_pinniped_dex_service_status()
                if check_pinniped_dexsvc[1] != 200:
                    return None, check_pinniped_dexsvc[0]
                current_app.logger.info("External IP for Pinniped is set as: " + check_pinniped_svc[0])

            cluster_admin_users = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtRbacUserRoleSpec.clusterAdminUsers
            admin_users = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtRbacUserRoleSpec.adminUsers
            edit_users = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtRbacUserRoleSpec.editUsers
            view_users = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtRbacUserRoleSpec.viewUsers
            rbac_user_status = createRbacUsers(
                management_cluster,
                isMgmt=True,
                env=self.env,
                edit_users=edit_users,
                cluster_admin_users=cluster_admin_users,
                admin_users=admin_users,
                view_users=view_users,
            )
            if rbac_user_status[1] != 200:
                current_app.logger.error(rbac_user_status[0].json["msg"])
                return None, rbac_user_status[0].json["msg"]
            current_app.logger.info("Successfully created RBAC for all the provided users")
            current_app.logger.info("Identity Management configured successfully on Management Cluster")
            return "SUCCESS", "Successfully created RBAC for all the provided users"
        else:
            current_app.logger.info("Identity Management is not enabled")
            return "SUCCESS", "Identity Management is not enabled"

    def download_kubernetes_ova_marketplace(self):
        """
        Download kubernetes OVA from marketplace
        :return:
        """
        if self.market_place_token:
            mgmt_object = self._get_mgmt_data_object()
            kubernetes_ova_os = mgmt_object.tkgMgmtBaseOs
            network = mgmt_object.tkgMgmtNetworkName
            current_app.logger.info(f"Download latest {kubernetes_ova_os} kubernetes OVA from marketplace")
            kubernetes_ova_version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION
            market_place_utils = MarketPlaceUtils(self.market_place_token)
            down_status = market_place_utils.download_kubernetes_ova(
                self.govc_operation,
                network,
                kubernetes_ova_version,
                kubernetes_ova_os,
                kubernetes_ova_version,
            )
            if down_status[0] is None:
                raise Exception(down_status[1])
        else:
            current_app.logger.info(
                "MarketPlace refresh token is not provided, skipping the download of kubernetes ova"
            )

    def configure_cluster_cloud(self):
        """
        Perform AVI configurations, create SE, SE Group and SE VMs
        :return:
        """
        self.mgmt_object = self._get_mgmt_data_object()

        csrf = self.avi_base_ops.obtain_second_csrf()

        avi_version = self.avi_base_ops.obtain_avi_version()
        if avi_version[0] is None:
            return None, f"Failed to obtain deployed NSX ALB version {avi_version[1]}"
        avi_version = avi_version[0]

        current_app.logger.info("waiting for the Default-cloud status to be available...")
        if self.avi_infra_ops.wait_for_cloud_placement("Default-Cloud")[0] is None:
            raise Exception("Failed to get default cloud status")

        try:
            mode_of_deployment = str(
                NsxAlbWorkflow.get_alb_data_objects(self.spec, self.env)[0].modeOfDeployment
            ).lower()
        except Exception:
            mode_of_deployment = "orchestrated"

        current_app.logger.info(f"Mode of deployment is {mode_of_deployment}")

        if mode_of_deployment == "non-orchestrated":
            config_response = self.configure_non_orchestrated_cloud(csrf, avi_version)
        else:
            config_response = self.configure_orchestrated_cloud()

        if config_response[0] is None:
            raise Exception(config_response[1])

        current_app.logger.info(config_response[1])

    def create_mgmt_folder_and_rp(self):
        """
        Create Folders and Resource pools for creating cluster
        :return:
        """
        resource_pool, folder = self._get_rp_and_folder()
        create_response = self.vc_ssl_obj.create_resource_folder_and_wait(
            resource_pool, folder, self.parent_resourcePool
        )
        if create_response[1] != 200:
            message = "Failed to create resource pool and folder " + create_response[0].json["msg"]
            raise Exception(message)

    def deploy_management_cluster(self):
        """
        Deploy Management cluster
        :return: Raise exception on failure
        """
        management_cluster = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
        if not TanzuUtil.verify_cluster(management_cluster):
            data_network = (
                self.spec.tkgMgmtDataNetwork.tkgMgmtDataNetworkName
                if self.env == Env.VSPHERE
                else self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
            )

            management_cluster = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName

            get_wip = self.avi_infra_ops.get_vip_network_ip_netmask(data_network)
            if get_wip[0] is None or get_wip[0] == "NOT_FOUND":
                raise Exception("Failed to get se VIP network IP and netmask " + str(get_wip[1]))

            if not self.create_cluster_folder(management_cluster):
                raise Exception("Failed to create directory: " + Paths.CLUSTER_PATH + management_cluster)

            self.configure_airgap_variables(False)

            status, msg = self.deploy_cluster(management_cluster, data_network, get_wip[0])
            if status is None:
                current_app.logger.error("Failed to deploy management cluster")
                raise Exception(msg)

            list_of_cmd = TanzuCommands.CONFIG_ACCEPT
            runProcess(list_of_cmd)

            self.configure_airgap_variables(True)

            current_app.logger.info(f"Management Cluster {management_cluster} deployed successfully")
        else:
            current_app.logger.info(f"Management Cluster {management_cluster} is already deployed successfully")

    def configure_identity_management(self):
        """
        Configure identity management on cluster
        :return: Raise exception if it fails
        """
        status, msg = self.enable_identity_management()
        if status is None:
            raise Exception(msg)

    def tmc_registration(self):
        """
        Perform TMC registration for management cluster
        :return: Raise exception if it fails
        """
        saas_util: SaaSUtil = SaaSUtil(self.env, self.spec)
        if saas_util.check_tmc_enabled():
            cluster_group = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterGroupName
            management_cluster = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
            if not cluster_group:
                cluster_group = "default"
            if CommonUtils.check_mgmt_proxy_enabled(self.env, self.spec):
                state = saas_util.register_management_cluster_tmc(
                    management_cluster, "true", "management", cluster_group
                )
            else:
                state = saas_util.register_management_cluster_tmc(
                    management_cluster, "false", "management", cluster_group
                )
            if state[1] != 200:
                current_app.logger.error("Failed to register on TMC " + state[1])
                raise Exception("Failed to register on TMC " + state[1])
        else:
            current_app.logger.info("TMC is disabled, hence skipping TMC registration for management cluster")

    def airgap_cluster_configuration(self):
        """
        Load Bom file for airgap environments after cluster is created
        :return:
        """
        if CommonUtils.is_airGapped_enabled(self.env, self.spec):
            management_cluster = self.spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
            msg, status = TanzuUtil.switch_to_management_context(management_cluster)
            if status == HTTPStatus.INTERNAL_SERVER_ERROR:
                current_app.logger.error(msg)
                raise Exception(msg)

            bom, msg = CommonUtils.load_bom_file(self.spec)
            if bom is None:
                raise Exception(msg)
        current_app.logger.info("Successfully configured management cluster")

    def management_cluster_deploy_worklflow(self):
        """
        Management Cluster create workflow for vsphere environments
        :return: Success if flow executes successfully
        """
        self.download_kubernetes_ova_marketplace()

        self.configure_cluster_cloud()

        self.create_mgmt_folder_and_rp()

        self.deploy_management_cluster()

        self.configure_identity_management()

        self.tmc_registration()

        self.airgap_cluster_configuration()
