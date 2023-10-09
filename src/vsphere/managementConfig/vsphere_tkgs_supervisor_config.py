# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import json
import logging
import os
import subprocess
import time
from http import HTTPStatus
from pathlib import Path

import requests
import ruamel
from flask import Blueprint, current_app, request
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.certificate_base64 import getBase64CertWriteToFile
from common.common_utilities import (
    VrfType,
    addStaticRoute,
    checkAndWaitForAllTheServiceEngineIsUp,
    cidr_to_netmask,
    convertStringToCommaSeperated,
    envCheck,
    fetchContentLibrary,
    get_avi_version,
    getAviCertificate,
    getCloudStatus,
    getClusterUrl,
    getCountOfIpAdress,
    getDetailsOfNewCloud,
    getDetailsOfNewCloudAddIpam,
    getIpam,
    getNetworkDetails,
    getNetworkUrl,
    getSECloudStatus,
    getVrfAndNextRoutId,
    isAviHaEnabled,
    obtain_avi_version,
    obtain_second_csrf,
    preChecks,
    seperateNetmaskAndIp,
    updateIpam,
    updateNetworkWithIpPools,
    updateNewCloud,
    verifyVcenterVersion,
)
from common.lib.govc.govc_operations import GOVCOperations
from common.lib.vcenter.vcenter_endpoints_operations import VCEndpointOperations
from common.login_auth.authentication import token_required
from common.model.vsphereTkgsSpec import VsphereTkgsMasterSpec
from common.operation.constants import CertName, Cloud, ControllerLocation
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
from common.operation.vcenter_operations import checkforIpAddress, getDvPortGroupId, getSi
from common.util.file_helper import FileHelper
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.request_api_util import RequestApiUtil
from common.util.saas_util import SaaSUtil
from common.util.tkgs_util import TkgsUtil

logger = logging.getLogger(__name__)
vsphere_supervisor_cluster = Blueprint("vsphere_supervisor_cluster", __name__, static_folder="managementConfig")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class TkgsSupervisorCluster:
    def __init__(self, spec):
        self.spec: VsphereTkgsMasterSpec = spec
        self.vCenter = current_app.config["VC_IP"]
        self.vc_user = current_app.config["VC_USER"]
        self.vc_password = current_app.config["VC_PASSWORD"]
        self.vc_data_center = current_app.config["VC_DATACENTER"]
        self.vc_data_store = current_app.config["VC_DATASTORE"]
        self.cluster_name = spec.envSpec.vcenterDetails.vcenterCluster
        self.vc_operation = VCEndpointOperations(self.vCenter, self.vc_user, self.vc_password)
        self.tkgs_util = TkgsUtil(spec)
        self.govc_operation = GOVCOperations(
            self.vCenter,
            self.vc_user,
            self.vc_password,
            self.cluster_name,
            self.vc_data_center,
            self.vc_data_store,
            LocalCmdHelper(),
        )

    def config_tkgs_cloud(self, ip, csrf2, aviVersion, license_type="enterprise"):
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
                "x-csrftoken": csrf2[0],
            }
            with open("./newCloudInfo.json", "r") as file2:
                new_cloud_json = json.load(file2)
            try:
                for result in new_cloud_json["results"]:
                    if result["name"] == Cloud.DEFAULT_CLOUD_NAME_VSPHERE:
                        vcenter_config = result["vcenter_configuration"]["vcenter_url"]
                        current_app.logger.debug(f"Vcenter config url {vcenter_config}")
                        break
                current_app.logger.info(
                    "Vcenter details are already updated to cloud " + Cloud.DEFAULT_CLOUD_NAME_VSPHERE
                )
            except Exception:
                current_app.logger.info("Updating Vcenter details to cloud " + Cloud.DEFAULT_CLOUD_NAME_VSPHERE)
                datacenter = current_app.config["VC_DATACENTER"]
                if str(datacenter).__contains__("/"):
                    datacenter = datacenter[datacenter.rindex("/") + 1 :]
                library, status_lib = fetchContentLibrary(ip, headers, "")
                if library is None:
                    return None, status_lib
                true_content_lib_body = {
                    "vcenter_configuration": {
                        "privilege": "WRITE_ACCESS",
                        "content_lib": {"id": status_lib},
                        "vcenter_url": current_app.config["VC_IP"],
                        "username": current_app.config["VC_USER"],
                        "password": current_app.config["VC_PASSWORD"],
                        "datacenter": datacenter,
                    }
                }
                false_content_lib_body = {
                    "vcenter_configuration": {
                        "privilege": "WRITE_ACCESS",
                        "vcenter_url": current_app.config["VC_IP"],
                        "username": current_app.config["VC_USER"],
                        "password": current_app.config["VC_PASSWORD"],
                        "datacenter": datacenter,
                        "use_content_lib": False,
                    }
                }
                content_lib_body = false_content_lib_body if license_type == "essentials" else true_content_lib_body
                body = {
                    "name": Cloud.DEFAULT_CLOUD_NAME_VSPHERE,
                    "vtype": "CLOUD_VCENTER",
                }
                body.update(content_lib_body)
                json_object = json.dumps(body, indent=4)
                url = cloud_url
                current_app.logger.info("Waiting for 1 min status == ready")
                time.sleep(60)
                response_csrf = RequestApiUtil.exec_req("PUT", url, headers=headers, data=json_object, verify=False)
                if response_csrf.status_code != HTTPStatus.OK:
                    return None, response_csrf.text
                else:
                    os.system("rm -rf newCloudInfo.json")
                    with open("./newCloudInfo.json", "w") as outfile:
                        json.dump(response_csrf.json(), outfile)

            mgmt_pg = self.spec.tkgsComponentSpec.aviMgmtNetwork.aviMgmtNetworkName
            get_management = getNetworkUrl(ip, csrf2, mgmt_pg, Cloud.DEFAULT_CLOUD_NAME_VSPHERE, aviVersion)
            if get_management[0] is None:
                return None, "Failed to get avi management network " + str(get_management[1])
            startIp = self.spec.tkgsComponentSpec.aviMgmtNetwork.aviMgmtServiceIpStartRange
            endIp = self.spec.tkgsComponentSpec.aviMgmtNetwork.aviMgmtServiceIpEndRange
            prefixIpNetmask = seperateNetmaskAndIp(self.spec.tkgsComponentSpec.aviMgmtNetwork.aviMgmtNetworkGatewayCidr)
            getManagementDetails = getNetworkDetails(
                ip, csrf2, get_management[0], startIp, endIp, prefixIpNetmask[0], prefixIpNetmask[1], True, aviVersion
            )
            if getManagementDetails[0] is None:
                current_app.logger.error("Failed to get management network details " + str(getManagementDetails[2]))
                return None, str(getManagementDetails[2])
            if getManagementDetails[0] == "AlreadyConfigured":
                current_app.logger.info("Ip pools are already configured.")
                vim_ref = getManagementDetails[2]["vim_ref"]
                ip_pre = getManagementDetails[2]["subnet_ip"]
                mask = getManagementDetails[2]["subnet_mask"]
            else:
                update_resp = updateNetworkWithIpPools(
                    ip, csrf2, get_management[0], "managementNetworkDetails.json", aviVersion
                )
                if update_resp[0] != HTTPStatus.OK:
                    return None, str(update_resp[1])
                vim_ref = update_resp[2]["vimref"]
                mask = update_resp[2]["subnet_mask"]
                ip_pre = update_resp[2]["subnet_ip"]
            new_cloud_status = getDetailsOfNewCloud(ip, csrf2, cloud_url, vim_ref, ip_pre, mask, aviVersion)
            if new_cloud_status[0] is None:
                return None, str(new_cloud_status[1])
            updateNewCloudStatus = updateNewCloud(ip, csrf2, cloud_url, aviVersion)
            if updateNewCloudStatus[0] is None:
                current_app.logger.error("Failed to update cloud " + str(updateNewCloudStatus[1]))
                return None, str(updateNewCloudStatus[1])
            with open("./newCloudInfo.json", "r") as file2:
                new_cloud_json = json.load(file2)
            uuid = None
            try:
                uuid = new_cloud_json["uuid"]
            except Exception:
                for re in new_cloud_json["results"]:
                    if re["name"] == Cloud.DEFAULT_CLOUD_NAME_VSPHERE:
                        uuid = re["uuid"]
            if uuid is None:
                current_app.logger.error(Cloud.DEFAULT_CLOUD_NAME_VSPHERE + " cloud not found")
                return None, "NOT_FOUND"
            ipNetMask = seperateNetmaskAndIp(self.spec.tkgsComponentSpec.aviMgmtNetwork.aviMgmtNetworkGatewayCidr)
            vrf = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.MANAGEMENT, ipNetMask[0], aviVersion)
            if vrf[0] is None or vrf[1] == "NOT_FOUND":
                current_app.logger.error("Vrf not found " + str(vrf[1]))
                return None, str(vrf[1])
            if vrf[1] != "Already_Configured":
                ad = addStaticRoute(ip, csrf2, vrf[0], ipNetMask[0], vrf[1], aviVersion)
                if ad[0] is None:
                    current_app.logger.error("Failed to add static route " + str(ad[1]))
                    return None, str(ad[1])
            ##########################################################
            vip_pg = self.spec.tkgsComponentSpec.tkgsVipNetwork.tkgsVipNetworkName
            get_vip = getNetworkUrl(ip, csrf2, vip_pg, Cloud.DEFAULT_CLOUD_NAME_VSPHERE, aviVersion)
            if get_vip[0] is None:
                return None, "Failed to get tkgs vip network " + str(get_vip[1])
            startIp_vip = self.spec.tkgsComponentSpec.tkgsVipNetwork.tkgsVipIpStartRange
            endIp_vip = self.spec.tkgsComponentSpec.tkgsVipNetwork.tkgsVipIpEndRange
            prefixIpNetmask_vip = seperateNetmaskAndIp(
                self.spec.tkgsComponentSpec.tkgsVipNetwork.tkgsVipNetworkGatewayCidr
            )
            getManagementDetails_vip = getNetworkDetails(
                ip,
                csrf2,
                get_vip[0],
                startIp_vip,
                endIp_vip,
                prefixIpNetmask_vip[0],
                prefixIpNetmask_vip[1],
                False,
                aviVersion,
            )
            if getManagementDetails_vip[0] is None:
                current_app.logger.error("Failed to get Tkgs vip network details " + str(getManagementDetails_vip[2]))
                return None, str(getManagementDetails_vip[2])
            if getManagementDetails_vip[0] == "AlreadyConfigured":
                current_app.logger.info("Ip pools are already configured for tkgs vip.")
            else:
                update_resp = updateNetworkWithIpPools(
                    ip, csrf2, get_vip[0], "managementNetworkDetails.json", aviVersion
                )
                if update_resp[0] != HTTPStatus.OK:
                    current_app.logger.error("Failed to update Tkgs vip details to cloud " + str(update_resp[1]))
                    return None, str(update_resp[1])
            get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
            if get_ipam[0] is None:
                current_app.logger.error("Failed to get se Ipam " + str(get_ipam[1]))
                return None, str(get_ipam[1])

            isGen = False
            if get_ipam[0] == "NOT_FOUND":
                isGen = True
                current_app.logger.info("Creating IPam " + Cloud.IPAM_NAME_VSPHERE)
                ipam = self.create_ipam(ip, csrf2, get_management[0], get_vip[0], Cloud.IPAM_NAME_VSPHERE, aviVersion)
                if ipam[0] is None:
                    current_app.logger.error("Failed to create Ipam " + str(ipam[1]))
                    return None, str(ipam[1])
                ipam_url = ipam[0]
            else:
                ipam_url = get_ipam[0]

            new_cloud_status = getDetailsOfNewCloudAddIpam(ip, csrf2, cloud_url, ipam_url, aviVersion)
            if new_cloud_status[0] is None:
                current_app.logger.error("Failed to get new cloud details" + str(new_cloud_status[1]))
                return None, str(new_cloud_status[1])
            updateIpam_re = updateIpam(ip, csrf2, cloud_url, aviVersion)
            if updateIpam_re[0] is None:
                current_app.logger.error("Failed to update Ipam to cloud " + str(updateIpam_re[1]))
                return None, str(updateIpam_re[1])
            cluster_name = self.spec.envSpec.vcenterDetails.vcenterCluster
            if str(cluster_name).__contains__("/"):
                cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]
            cluster_status = getClusterUrl(ip, csrf2, cluster_name, aviVersion)
            if cluster_status[0] is None:
                current_app.logger.error("Failed to get cluster details" + str(cluster_status[1]))
                return None, str(cluster_status[1])
            if cluster_status[0] == "NOT_FOUND":
                current_app.logger.error("Failed to get cluster details" + str(cluster_status[1]))
                return None, str(cluster_status[1])
            get_se_cloud = getSECloudStatus(ip, csrf2, aviVersion, Cloud.DEFAULT_SE_GROUP_NAME_VSPHERE)
            if get_se_cloud[0] is None:
                current_app.logger.error("Failed to get se cloud status " + str(get_se_cloud[1]))
                return None, str(get_se_cloud[1])
            se_engine_url = get_se_cloud[0]
            update = self.updateSeEngineDetails(
                ip, csrf2, se_engine_url, cluster_status[0], aviVersion, license_type=license_type
            )
            if update[0] is None:
                return None, update[1]
            ipNetMask_vip = prefixIpNetmask_vip
            vrf_vip = getVrfAndNextRoutId(ip, csrf2, uuid, VrfType.GLOBAL, ipNetMask_vip[0], aviVersion)
            if vrf_vip[0] is None or vrf_vip[1] == "NOT_FOUND":
                current_app.logger.error("Vrf not found " + str(vrf_vip[1]))
                return None, str(vrf_vip[1])
            if vrf_vip[1] != "Already_Configured":
                ad = addStaticRoute(ip, csrf2, vrf_vip[0], ipNetMask_vip[0], vrf_vip[1], aviVersion)
                if ad[0] is None:
                    current_app.logger.error("Failed to add static route " + str(ad[1]))
                    return None, str(ad[1])
            current_app.logger.debug(f"is gen {isGen}")
            return "SUCCESS", "CONFIGURED_TKGS_CLOUD"
        except Exception as e:
            return None, str(e)

    def create_ipam(self, ip, csrf2, managementNetworkUrl, vip_network, name, aviVersion):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        body = {
            "name": name,
            "internal_profile": {
                "ttl": 30,
                "usable_networks": [{"nw_ref": managementNetworkUrl}, {"nw_ref": vip_network}],
            },
            "allocate_ip_in_vrf": False,
            "type": "IPAMDNS_TYPE_INTERNAL",
            "gcp_profile": {"match_se_group_subnet": False, "use_gcp_network": False},
            "azure_profile": {"use_enhanced_ha": False, "use_standard_alb": False},
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/ipamdnsproviderprofile"
        response_csrf = RequestApiUtil.exec_req("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"

    def updateSeEngineDetails(self, ip, csrf2, seUrl, clusterUrl, aviVersion, license_type):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0],
        }
        essentials_body = {
            "self_se_election": False,
        }
        enterprise_body = {
            "self_se_election": True,
        }
        body = {
            "name": Cloud.DEFAULT_SE_GROUP_NAME_VSPHERE,
            "vcpus_per_se": 2,
            "memory_per_se": 4096,
            "algo": "PLACEMENT_ALGO_PACKED",
            "distribute_load_active_standby": False,
            "vcenter_datastores_include": True,
            "vcenter_datastore_mode": "VCENTER_DATASTORE_SHARED",
            "vcenter_clusters": {"include": True, "cluster_refs": [clusterUrl]},
        }
        update_body = essentials_body if license_type == "essentials" else enterprise_body
        body.update(update_body)
        json_object = json.dumps(body, indent=4)
        response_csrf = RequestApiUtil.exec_req("PUT", seUrl, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != HTTPStatus.OK:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], "SUCCESS"

    def enableWCP(self, ip, csrf2, aviVersion):
        try:
            sess = requests.request(
                "POST",
                "https://" + self.vCenter + "/rest/com/vmware/cis/session",
                auth=(self.vc_user, self.vc_password),
                verify=False,
            )
            if sess.status_code != HTTPStatus.OK:
                response = RequestApiUtil.create_json_object(
                    "Failed to fetch session ID for vCenter - " + self.vCenter,
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            else:
                vc_session = sess.json()["value"]

            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": vc_session,
            }
            id = self.tkgs_util.get_cluster_id(self.cluster_name)
            if id[1] != HTTPStatus.OK:
                return None, id[0]
            url = "https://" + self.vCenter + "/api/vcenter/namespace-management/clusters/" + str(id[0])
            response_csrf = RequestApiUtil.exec_req("GET", url, headers=header, verify=False)
            endpoint_ip = None
            isRuning = False
            if response_csrf.status_code != HTTPStatus.OK:
                if response_csrf.status_code == 400:
                    if (
                        response_csrf.json()["messages"][0]["default_message"]
                        == "Cluster with identifier " + str(id[0]) + " does "
                        "not have Workloads enabled."
                    ):
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
                except Exception:
                    isRuning = False

            if isRuning:
                current_app.logger.info("Wcp is already enabled")
            else:
                current_app.logger.info("Enabling Wcp..")
                control_plane_size = self.spec.tkgsComponentSpec.controlPlaneSize
                allowed_tkgs_size = ["TINY", "SMALL", "MEDIUM", "LARGE"]
                if not control_plane_size.upper() in allowed_tkgs_size:
                    return (
                        None,
                        "Allowed Control plane sizes [tkgsComponentSpec][controlPlaneSize] are TINY, SMALL,"
                        " MEDIUM, LARGE",
                    )
                image_storage_policy_name = self.spec.tkgsComponentSpec.tkgsStoragePolicySpec.imageStoragePolicy

                image_storage_policyId = self.vc_operation.get_policy_id(image_storage_policy_name)
                if image_storage_policyId[0] is None:
                    return None, image_storage_policyId[1]
                ephemeral_storage_policy_name = self.spec.tkgsComponentSpec.tkgsStoragePolicySpec.ephemeralStoragePolicy
                ephemeral_storage_policyId = self.vc_operation.get_policy_id(ephemeral_storage_policy_name)
                if ephemeral_storage_policyId[0] is None:
                    return None, ephemeral_storage_policyId[1]
                master_storage_policy_name = self.spec.tkgsComponentSpec.tkgsStoragePolicySpec.masterStoragePolicy
                master_storage_policyId = self.vc_operation.get_policy_id(master_storage_policy_name)
                if master_storage_policyId[0] is None:
                    return None, master_storage_policyId[1]
                str_enc_avi = str(self.spec.tkgsComponentSpec.aviComponents.aviPasswordBase64)
                base64_bytes_avi = str_enc_avi.encode("ascii")
                enc_bytes_avi = base64.b64decode(base64_bytes_avi)
                password_avi = enc_bytes_avi.decode("ascii").rstrip("\n")
                avi_fqdn = self.spec.tkgsComponentSpec.aviComponents.aviController01Fqdn
                master_dnsServers = self.spec.tkgsComponentSpec.tkgsMgmtNetworkSpec.tkgsMgmtNetworkDnsServers
                master_search_domains = self.spec.tkgsComponentSpec.tkgsMgmtNetworkSpec.tkgsMgmtNetworkSearchDomains
                master_ntp_servers = self.spec.tkgsComponentSpec.tkgsMgmtNetworkSpec.tkgsMgmtNetworkNtpServers
                worker_dns = self.spec.tkgsComponentSpec.tkgsPrimaryWorkloadNetwork.tkgsWorkloadDnsServers
                worker_ntps = self.spec.tkgsComponentSpec.tkgsPrimaryWorkloadNetwork.tkgsWorkloadNtpServers
                worker_cidr = (
                    self.spec.tkgsComponentSpec.tkgsPrimaryWorkloadNetwork.tkgsPrimaryWorkloadNetworkGatewayCidr
                )
                start = self.spec.tkgsComponentSpec.tkgsPrimaryWorkloadNetwork.tkgsPrimaryWorkloadNetworkStartRange
                end = self.spec.tkgsComponentSpec.tkgsPrimaryWorkloadNetwork.tkgsPrimaryWorkloadNetworkEndRange
                ip_cidr = seperateNetmaskAndIp(worker_cidr)
                count_of_ip = getCountOfIpAdress(worker_cidr, start, end)
                service_cidr = self.spec.tkgsComponentSpec.tkgsPrimaryWorkloadNetwork.tkgsWorkloadServiceCidr
                service_cidr_split = seperateNetmaskAndIp(service_cidr)
                worker_network_name = (
                    self.spec.tkgsComponentSpec.tkgsPrimaryWorkloadNetwork.tkgsPrimaryWorkloadPortgroupName
                )
                workload_network_name = (
                    self.spec.tkgsComponentSpec.tkgsPrimaryWorkloadNetwork.tkgsPrimaryWorkloadNetworkName
                )
                worker_network_id = getDvPortGroupId(
                    self.vCenter, self.vc_user, self.vc_password, worker_network_name, self.vc_data_center
                )
                if worker_network_id is None:
                    return None, "Failed to get worker dv port id"
                ###################################################
                master_management = self.spec.tkgsComponentSpec.tkgsMgmtNetworkSpec.tkgsMgmtNetworkGatewayCidr
                master_management_start = self.spec.tkgsComponentSpec.tkgsMgmtNetworkSpec.tkgsMgmtNetworkStartingIp
                master_management_ip_netmask = seperateNetmaskAndIp(master_management)
                mgmt_network_name = self.spec.tkgsComponentSpec.tkgsMgmtNetworkSpec.tkgsMgmtNetworkName
                try:
                    isProxyEnabled = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.enableProxy
                    if str(isProxyEnabled).lower() == "true":
                        proxyEnabled = True
                    else:
                        proxyEnabled = False
                except Exception:
                    proxyEnabled = False
                mgmt_network_id = getDvPortGroupId(
                    self.vCenter, self.vc_user, self.vc_password, mgmt_network_name, self.vc_data_center
                )
                if mgmt_network_id is None:
                    return None, "Failed to get management dv port id"
                subs_lib_name = self.spec.tkgsComponentSpec.tkgsMgmtNetworkSpec.subscribedContentLibraryName
                if not subs_lib_name:
                    lib = self.govc_operation.get_library_id(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY)
                else:
                    lib = self.govc_operation.get_library_id(subs_lib_name)
                if lib is None:
                    return None, "Failed to get subscribed lib id"
                cert = getAviCertificate(ip, csrf2, CertName.VSPHERE_CERT_NAME, aviVersion)
                if cert[0] is None or cert[0] == "NOT_FOUND":
                    return None, "Avi certificate not found"
                body = {
                    "default_kubernetes_service_content_library": lib,
                    "image_storage": {"storage_policy": image_storage_policyId[0]},
                    "ephemeral_storage_policy": ephemeral_storage_policyId[0],
                    "master_storage_policy": master_storage_policyId[0],
                    "load_balancer_config_spec": {
                        "address_ranges": [],
                        "avi_config_create_spec": {
                            "certificate_authority_chain": cert[0],
                            "password": password_avi,
                            "server": {"host": avi_fqdn, "port": 443},
                            "username": "admin",
                        },
                        "id": "tkgs-avi01",
                        "provider": "AVI",
                    },
                    "master_DNS": convertStringToCommaSeperated(master_dnsServers),
                    "master_DNS_search_domains": convertStringToCommaSeperated(master_search_domains),
                    "master_NTP_servers": convertStringToCommaSeperated(master_ntp_servers),
                    "master_management_network": {
                        "address_range": {
                            "address_count": 5,
                            "gateway": master_management_ip_netmask[0],
                            "starting_address": master_management_start,
                            "subnet_mask": cidr_to_netmask(master_management),
                        },
                        "mode": "STATICRANGE",
                        "network": mgmt_network_id,
                    },
                    "network_provider": "VSPHERE_NETWORK",
                    "service_cidr": {"address": service_cidr_split[0], "prefix": int(service_cidr_split[1])},
                    "size_hint": control_plane_size.upper(),
                    "worker_DNS": convertStringToCommaSeperated(worker_dns),
                    "worker_ntp_servers": convertStringToCommaSeperated(worker_ntps),
                    "workload_networks_spec": {
                        "supervisor_primary_workload_network": {
                            "network": workload_network_name,
                            "network_provider": "VSPHERE_NETWORK",
                            "vsphere_network": {
                                "address_ranges": [{"address": start, "count": count_of_ip}],
                                "gateway": ip_cidr[0],
                                "portgroup": worker_network_id,
                                "subnet_mask": cidr_to_netmask(worker_cidr),
                            },
                        }
                    },
                }
                if proxyEnabled:
                    httpProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpProxy
                    httpsProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpsProxy
                    noProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.noProxy
                    list_ = convertStringToCommaSeperated(noProxy)
                    body_u = {
                        "cluster_proxy_config": {
                            "http_proxy_config": httpProxy,
                            "https_proxy_config": httpsProxy,
                            "no_proxy_config": list_,
                            "proxy_settings_source": "CLUSTER_CONFIGURED",
                        }
                    }
                    body.update(body_u)
                url1 = (
                    "https://"
                    + self.vCenter
                    + "/api/vcenter/namespace-management/clusters/"
                    + str(id[0])
                    + "?action=enable"
                )
                json_object = json.dumps(body, indent=4)
                response_csrf = RequestApiUtil.exec_req("POST", url1, headers=header, data=json_object, verify=False)
                if response_csrf.status_code != 204:
                    return None, response_csrf.text
                count = 0
                found = False
                while count < 300:
                    response_csrf = RequestApiUtil.exec_req("GET", url, headers=header, verify=False)
                    try:
                        if response_csrf.json()["config_status"] == "RUNNING":
                            endpoint_ip = response_csrf.json()["api_server_cluster_endpoint"]
                            current_app.logger.debug(f"cluster API server endpoint IP {endpoint_ip}")
                            found = True
                            break
                        else:
                            if response_csrf.json()["config_status"] == "ERROR":
                                return None, "WCP status in ERROR"
                            current_app.logger.info("Cluster config status " + response_csrf.json()["config_status"])
                    except Exception:
                        pass
                    time.sleep(20)
                    count = count + 1
                    current_app.logger.info("Waited " + str(count * 20) + "s, retrying")
                if not found:
                    current_app.logger.error("Cluster is not running on waiting " + str(count * 20))
                    return None, "Failed"
            """if endpoint_ip is not None:
                current_app.logger.info("Setting up kubectl vsphere")
                time.sleep(30)
                configure_kubectl = configure_kubectl(endpoint_ip)
                if configure_kubectl[1] != HTTPStatus.OK:
                    return configure_kubectl[0], HTTPStatus.INTERNAL_SERVER_ERROR"""
            return "SUCCESS", "WCP_ENABLED"
        except Exception as e:
            return None, str(e)

    def configureTkgConfiguration(self, vCenter_user, vc_password, cluster_endpoint):
        current_app.logger.info("Getting current Tkgs current configuration")
        current_app.logger.info("Logging in to cluster " + cluster_endpoint)
        os.putenv("KUBECTL_VSPHERE_PASSWORD", vc_password)
        connect_command = [
            "kubectl",
            "vsphere",
            "login",
            "--server=" + cluster_endpoint,
            "--vsphere-username=" + vCenter_user,
            "--insecure-skip-tls-verify",
        ]
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            return None, str(output[0])
        switch_context = ["kubectl", "config", "use-context", cluster_endpoint]
        output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            return None, str(output[0])
        fileName = "./kube_config.yaml"
        os.system("rm -rf kube_config.yaml")
        command = ["kubectl", "get", "tkgserviceconfigurations", "tkg-service-configuration", "-o", "yaml"]
        proc = subprocess.run(command, stdout=subprocess.PIPE)
        FileHelper.write_to_file(proc.stdout.decode("utf-8"), fileName)
        try:
            cni = self.spec.tkgsComponentSpec.tkgServiceConfig.defaultCNI
            if cni:
                defaultCNI = cni
            else:
                defaultCNI = "antrea"
        except Exception:
            defaultCNI = "antrea"
        os.system("chmod +x ./common/injectValue.sh")
        command_ = ["sh", "./common/injectValue.sh", fileName, "change_cni", defaultCNI]
        runShellCommandAndReturnOutputAsList(command_)
        try:
            isProxyEnabled = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.enableProxy
            if str(isProxyEnabled).lower() == "true":
                proxyEnabled = True
            else:
                proxyEnabled = False
        except Exception:
            proxyEnabled = False
        if proxyEnabled:
            try:
                httpProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpProxy
                httpsProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.httpsProxy
                noProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.noProxy
                list_ = convertStringToCommaSeperated(noProxy)
                ytr = dict(proxy=dict(httpProxy=httpProxy, httpsProxy=httpsProxy, noProxy=list_))
                yaml = ruamel.yaml.YAML()
                cert_list = []
                with open(fileName, "r") as outfile:
                    cur_yaml = yaml.load(outfile)
                    cur_yaml["spec"].update(ytr)
                if cur_yaml:
                    with open(fileName, "w") as yamlfile:
                        yaml.indent(mapping=2, sequence=4, offset=2)
                        yaml.dump(cur_yaml, yamlfile)
                isProxy = self.spec.tkgsComponentSpec.tkgServiceConfig.proxySpec.proxyCert
                if isProxy:
                    cert = Path(isProxy).read_text()
                    string_bytes = cert.encode("ascii")
                    base64_bytes = base64.b64encode(string_bytes)
                    cert_base64 = base64_bytes.decode("ascii")
                    cert_list.append(dict(name="certProxy", data=cert_base64))
                proxyPath = self.spec.tkgsComponentSpec.tkgServiceConfig.additionalTrustedCAs.paths
                proxyEndpoints = self.spec.tkgsComponentSpec.tkgServiceConfig.additionalTrustedCAs.endpointUrls
                if proxyPath:
                    proxyCert = proxyPath
                    isProxyAddCert = True
                    isCaPath = True
                elif proxyEndpoints:
                    proxyCert = proxyEndpoints
                    isProxyAddCert = True
                    isCaPath = False
                else:
                    isProxyAddCert = False
                    isCaPath = False
                if isProxyAddCert:
                    count = 0
                    for certs in proxyCert:
                        count = count + 1
                        if isCaPath:
                            cert = Path(certs).read_text()
                            string_bytes = cert.encode("ascii")
                            base64_bytes = base64.b64encode(string_bytes)
                            cert_base64 = base64_bytes.decode("ascii")
                        else:
                            getBase64CertWriteToFile(certs, "443")
                            with open("cert.txt", "r") as file2:
                                cert_base64 = file2.readline()
                        cert_list.append(dict(name="cert" + str(count), data=cert_base64))
                ytr = dict(trust=dict(additionalTrustedCAs=cert_list))
                with open(fileName, "r") as outfile:
                    cur_yaml = yaml.load(outfile)
                    cur_yaml["spec"].update(ytr)
                if cur_yaml:
                    with open(fileName, "w") as yamlfile:
                        yaml.indent(mapping=2, sequence=4, offset=2)
                        yaml.dump(cur_yaml, yamlfile)
            except Exception as e:
                return None, str(e)
        else:
            command = ["sh", "./common/injectValue.sh", fileName, "delete_proxy"]
            runShellCommandAndReturnOutputAsList(command)
            command = ["sh", "./common/injectValue.sh", fileName, "delete_trust"]
            runShellCommandAndReturnOutputAsList(command)
        command = ["kubectl", "replace", "-f", fileName]
        runShellCommandAndReturnOutputAsList(command)
        return "SUCCESS", "Changed"


@vsphere_supervisor_cluster.route("/api/tanzu/vsphere/tkgmgmt/alb/config/wcp", methods=["POST"])
@token_required
def config_wcp(current_user):
    spec_json = request.get_json(force=True)
    spec: VsphereTkgsMasterSpec = VsphereTkgsMasterSpec.parse_obj(spec_json)
    super_visor = TkgsSupervisorCluster(spec)
    TkgsUtil(spec)
    pre = preChecks()
    if pre[1] != HTTPStatus.OK:
        current_app.logger.error(pre[0].json["msg"])
        response = RequestApiUtil.create_json_object(pre[0].json["msg"], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    env = envCheck()
    if env[1] != HTTPStatus.OK:
        current_app.logger.error("Wrong env provided " + env[0])
        response = RequestApiUtil.create_json_object(
            "Wrong env provided " + env[0], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    env = env[0]
    aviVersion = get_avi_version(env)
    license_type = "enterprise"
    if TkgsUtil.is_env_tkgs_wcp(spec, env):
        avi_fqdn = spec.tkgsComponentSpec.aviComponents.aviController01Fqdn
        license_type = str(spec.tkgsComponentSpec.aviComponents.typeOfLicense)
        if isAviHaEnabled(env):
            aviClusterFqdn = spec.tkgsComponentSpec.aviComponents.aviClusterFqdn
    if isAviHaEnabled(env):
        ip = aviClusterFqdn
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        response = RequestApiUtil.create_json_object(
            "Failed to get IP of avi controller", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR

    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        response = RequestApiUtil.create_json_object(
            "Failed to get csrf from new set password", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    if TkgsUtil.is_env_tkgs_wcp(spec, env):
        configTkgs = super_visor.config_tkgs_cloud(ip, csrf2, aviVersion, license_type=license_type)
        if configTkgs[0] is None:
            current_app.logger.error("Failed to config tkgs " + str(configTkgs[1]))
            response = RequestApiUtil.create_json_object(
                "Failed to config tkgs " + str(configTkgs[1]), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
            )
            return response, HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Configured wcp  successfully")
    response = RequestApiUtil.create_json_object("Configured wcp successfully", "SUCCESS", HTTPStatus.OK)
    return response, HTTPStatus.OK


@vsphere_supervisor_cluster.route("/api/tanzu/vsphere/enablewcp", methods=["POST"])
@token_required
def enable_wcp(current_user):
    spec_json = request.get_json(force=True)
    spec: VsphereTkgsMasterSpec = VsphereTkgsMasterSpec.parse_obj(spec_json)
    super_visor = TkgsSupervisorCluster(spec)
    tkgs_util = TkgsUtil(spec)
    kubectl_util = KubectlUtil()
    pre = preChecks()
    if pre[1] != HTTPStatus.OK:
        current_app.logger.error(pre[0].json["msg"])
        response = RequestApiUtil.create_json_object(pre[0].json["msg"], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    env = envCheck()
    if env[1] != HTTPStatus.OK:
        current_app.logger.error("Wrong env provided " + env[0])
        response = RequestApiUtil.create_json_object(
            "Wrong env provided " + env[0], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    env = env[0]
    saas_util: SaaSUtil = SaaSUtil(env, spec)
    if not TkgsUtil.is_env_tkgs_wcp(spec, env):
        current_app.logger.error("Wrong env provided, wcp can be only enabled on TKGS")
        response = RequestApiUtil.create_json_object(
            "Wrong env provided, wcp can be only enabled on TKGS", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    # aviVersion = get_avi_version(env)
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    subs_lib_name = spec.tkgsComponentSpec.tkgsMgmtNetworkSpec.subscribedContentLibraryName
    if not subs_lib_name:
        if verifyVcenterVersion("8"):
            thump_print = ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY_THUMBPRINT8
        else:
            thump_print = ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY_THUMBPRINT
        cLib = super_visor.govc_operation.create_subscribed_library(
            lib_name=ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY,
            url=ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY_URL,
            thumb_print=thump_print,
        )
        if cLib[0] is None:
            current_app.logger.error("Failed to create content library " + str(cLib[1]))
            response = RequestApiUtil.create_json_object(
                "Failed to create content library " + str(cLib[1]), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
            )
            return response, HTTPStatus.INTERNAL_SERVER_ERROR
    avi_fqdn = spec.tkgsComponentSpec.aviComponents.aviController01Fqdn
    if not avi_fqdn:
        controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
    else:
        controller_name = avi_fqdn
    current_app.logger.info(f"controller name {controller_name}")
    if isAviHaEnabled(env):
        ip = spec.tkgsComponentSpec.aviComponents.aviClusterFqdn
    else:
        ip = avi_fqdn
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        response = RequestApiUtil.create_json_object(
            "Failed to get IP of AVI controller", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        response = RequestApiUtil.create_json_object(
            "Failed to get csrf from new set password", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR

    avi_ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), avi_fqdn)
    if avi_ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        response = RequestApiUtil.create_json_object(
            "Failed to get IP of AVI controller", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    deployed_avi_version = obtain_avi_version(avi_ip, env)
    if deployed_avi_version[0] is None:
        current_app.logger.error("Failed to login and obtain AVI version" + str(deployed_avi_version[1]))
        response = RequestApiUtil.create_json_object(
            "Failed to login and obtain AVI version " + deployed_avi_version[1],
            "ERROR",
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    aviVersion = deployed_avi_version[0]

    enable = super_visor.enableWCP(ip, csrf2, aviVersion)
    if enable[0] is None:
        current_app.logger.error("Failed to enable WCP " + str(enable[1]))
        response = RequestApiUtil.create_json_object(
            "Failed to configure WCP " + str(enable[1]), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    isUp = checkAndWaitForAllTheServiceEngineIsUp(ip, Cloud.DEFAULT_CLOUD_NAME_VSPHERE, env, aviVersion)
    if isUp[0] is None:
        current_app.logger.error("All service engines are not up, check your network configuration " + str(isUp[1]))
        response = RequestApiUtil.create_json_object(
            "All service engines are not up, check your network configuration " + str(isUp[1]),
            "ERROR",
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Setting up kubectl Vsphere plugin...")
    url_ = "https://" + vcenter_ip + "/"
    sess = requests.request(
        "POST", url_ + "rest/com/vmware/cis/session", auth=(vcenter_username, password), verify=False
    )
    if sess.status_code != HTTPStatus.OK:
        response = RequestApiUtil.create_json_object(
            "Failed to fetch API server cluster endpoint - " + vcenter_ip, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        session_id = sess.json()["value"]

    header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": session_id}
    cluster_name = spec.envSpec.vcenterDetails.vcenterCluster
    id = tkgs_util.get_cluster_id(cluster_name)
    if id[1] != HTTPStatus.OK:
        return None, id[0]
    clusterip_resp = RequestApiUtil.exec_req(
        "GET", url_ + "api/vcenter/namespace-management/clusters/" + str(id[0]), verify=False, headers=header
    )
    if clusterip_resp.status_code != HTTPStatus.OK:
        response = RequestApiUtil.create_json_object(
            "Failed to fetch API server cluster endpoint - " + vcenter_ip, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR

    cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]

    status = False
    count = 0
    while count < 15 and not status:
        configure_kubectl = kubectl_util.configure_kubectl(cluster_endpoint)
        if configure_kubectl[1] != HTTPStatus.OK:
            current_app.logger.info("Getting connection timeout error. Waited " + str(count * 60) + "s")
            current_app.logger.info("Waiting for 1 min status == ready")
            count = count + 1
            time.sleep(60)
        else:
            status = True

    if count >= 15 and not status:
        current_app.logger.error(configure_kubectl[0])
        response = RequestApiUtil.create_json_object(configure_kubectl[0], "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
        return response, HTTPStatus.INTERNAL_SERVER_ERROR

    current_app.logger.info("Configured Wcp successfully")
    configTkgs, message = super_visor.configureTkgConfiguration(vcenter_username, password, cluster_endpoint)
    if configTkgs is None:
        response = RequestApiUtil.create_json_object(
            "Failed to configure TKGS service configuration " + str(message), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR

    if saas_util.check_tmc_enabled():
        tmc_register_response = saas_util.register_tmc_tkgs(vcenter_ip, vcenter_username, password)
        if tmc_register_response[1] != HTTPStatus.OK:
            current_app.logger.error("Supervisor cluster TMC registration failed " + str(tmc_register_response[1]))
            response = RequestApiUtil.create_json_object(
                "Supervisor cluster TMC registration failed " + str(tmc_register_response[1]),
                "ERROR",
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return response, HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("TMC registration successful")
    else:
        current_app.logger.info("Skipping TMC registration, as tmcAvailability is set to False")
    response = RequestApiUtil.create_json_object("onfigured WCP successfully", "SUCCESS", HTTPStatus.OK)
    return response, HTTPStatus.OK
