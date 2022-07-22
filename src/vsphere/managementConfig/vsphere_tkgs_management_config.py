import logging
from flask import jsonify, request
from flask import current_app
import sys
import time
import requests
import base64
import json
import subprocess
import ruamel

logger = logging.getLogger(__name__)
sys.path.append(".../")
from common.operation.constants import CertName, ResourcePoolAndFolderName, Cloud, AkoType, CIDR, TmcUser, Type, \
    Avi_Version, \
    RegexPattern, Env, ControllerLocation
import os
from pathlib import Path
from common.certificate_base64 import getBase64CertWriteToFile
from common.common_utilities import getClusterID, getAviCertificate, getLibraryId, getCountOfIpAdress, \
    seperateNetmaskAndIp, \
    cidr_to_netmask, \
    convertStringToCommaSeperated, getPolicyID, updateNewCloud, preChecks, registerWithTmc, \
    get_avi_version, runSsh, \
    getCloudStatus, \
    getSECloudStatus, envCheck, getClusterStatusOnTanzu, getVipNetworkIpNetMask, getVrfAndNextRoutId, addStaticRoute, \
    VrfType, checkMgmtProxyEnabled, enableProxy, checkAirGappedIsEnabled, loadBomFile, grabPortFromUrl, \
    grabHostFromUrl, getNetworkUrl, getClusterUrl, getIpam, seperateNetmaskAndIp, getDetailsOfNewCloudAddIpam, \
    updateIpam, getNetworkDetails, getDetailsOfNewCloud, convertStringToCommaSeperated, updateNetworkWithIpPools, \
    updateNewCloud, configureKubectl
from common.operation.vcenter_operations import getDvPortGroupId
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def configTkgsCloud(ip, csrf2, aviVersion):
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
            current_app.logger.info(" vcenter details are already updated to cloud " + Cloud.DEFAULT_CLOUD_NAME_VSPHERE)
        except:
            current_app.logger.info("Updating vcenter details to cloud " + Cloud.DEFAULT_CLOUD_NAME_VSPHERE)
            datacenter = current_app.config['VC_DATACENTER']
            if str(datacenter).__contains__("/"):
                datacenter = datacenter[datacenter.rindex("/") + 1:]
            body = {
                "name": Cloud.DEFAULT_CLOUD_NAME_VSPHERE,
                "vtype": "CLOUD_VCENTER",
                "vcenter_configuration": {
                    "privilege": "WRITE_ACCESS",
                    "deactivate_vm_discovery": False,
                    "vcenter_url": current_app.config['VC_IP'],
                    "username": current_app.config['VC_USER'],
                    "password": current_app.config['VC_PASSWORD'],
                    "datacenter": datacenter
                }
            }
            json_object = json.dumps(body, indent=4)
            url = cloud_url
            current_app.logger.info("Waiting for 1 min status == ready")
            time.sleep(60)
            response_csrf = requests.request("PUT", url, headers=headers, data=json_object, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            else:
                os.system("rm -rf newCloudInfo.json")
                with open("./newCloudInfo.json", "w") as outfile:
                    json.dump(response_csrf.json(), outfile)
        mgmt_pg = request.get_json(force=True)['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']
        get_management = getNetworkUrl(ip, csrf2, mgmt_pg, Cloud.DEFAULT_CLOUD_NAME_VSPHERE, aviVersion)
        if get_management[0] is None:
            return None, "Failed to get avi management network " + str(get_management[1])
        startIp = request.get_json(force=True)["tkgsComponentSpec"]["aviMgmtNetwork"][
            "aviMgmtServiceIpStartRange"]
        endIp = request.get_json(force=True)["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtServiceIpEndRange"]
        prefixIpNetmask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
        getManagementDetails = getNetworkDetails(ip, csrf2, get_management[0], startIp, endIp, prefixIpNetmask[0],
                                                 prefixIpNetmask[1], True, aviVersion)
        if getManagementDetails[0] is None:
            current_app.logger.error("Failed to get management network details " + str(getManagementDetails[2]))
            return None, str(getManagementDetails[2])
        if getManagementDetails[0] == "AlreadyConfigured":
            current_app.logger.info("Ip pools are already configured.")
            vim_ref = getManagementDetails[2]["vim_ref"]
            ip_pre = getManagementDetails[2]["subnet_ip"]
            mask = getManagementDetails[2]["subnet_mask"]
        else:
            update_resp = updateNetworkWithIpPools(ip, csrf2, get_management[0], "managementNetworkDetails.json",
                                                   aviVersion)
            if update_resp[0] != 200:
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
            current_app.logger.error(Cloud.DEFAULT_CLOUD_NAME_VSPHERE + " cloud not found")
            return None, "NOT_FOUND"
        ipNetMask = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"])
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
        vip_pg = request.get_json(force=True)['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipNetworkName']
        get_vip = getNetworkUrl(ip, csrf2, vip_pg, Cloud.DEFAULT_CLOUD_NAME_VSPHERE, aviVersion)
        if get_vip[0] is None:
            return None, "Failed to get tkgs vip network " + str(get_vip[1])
        startIp_vip = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVipNetwork"]["tkgsVipIpStartRange"]
        endIp_vip = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVipNetwork"]["tkgsVipIpEndRange"]
        prefixIpNetmask_vip = seperateNetmaskAndIp(
            request.get_json(force=True)["tkgsComponentSpec"]["tkgsVipNetwork"]["tkgsVipNetworkGatewayCidr"])
        getManagementDetails_vip = getNetworkDetails(ip, csrf2, get_vip[0], startIp_vip, endIp_vip,
                                                     prefixIpNetmask_vip[0],
                                                     prefixIpNetmask_vip[1], False, aviVersion)
        if getManagementDetails_vip[0] is None:
            current_app.logger.error("Failed to get tkgs vip network details " + str(getManagementDetails_vip[2]))
            return None, str(getManagementDetails_vip[2])
        if getManagementDetails_vip[0] == "AlreadyConfigured":
            current_app.logger.info("Ip pools are already configured for tkgs vip.")
        else:
            update_resp = updateNetworkWithIpPools(ip, csrf2, get_vip[0], "managementNetworkDetails.json",
                                                   aviVersion)
            if update_resp[0] != 200:
                current_app.logger.error("Failed to update tkgs vip details to cloud " + str(update_resp[1]))
                return None, str(update_resp[1])
        get_ipam = getIpam(ip, csrf2, Cloud.IPAM_NAME_VSPHERE, aviVersion)
        if get_ipam[0] is None:
            current_app.logger.error("Failed to get se Ipam " + str(get_ipam[1]))
            return None, str(get_ipam[1])

        isGen = False
        if get_ipam[0] == "NOT_FOUND":
            isGen = True
            current_app.logger.info("Creating IPam " + Cloud.IPAM_NAME_VSPHERE)
            ipam = createIpam(ip, csrf2, get_management[0], get_vip[0], Cloud.IPAM_NAME_VSPHERE,
                              aviVersion)
            if ipam[0] is None:
                current_app.logger.error("Failed to create ipam " + str(ipam[1]))
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
            current_app.logger.error("Failed to update ipam to cloud " + str(updateIpam_re[1]))
            return None, str(updateIpam_re[1])
        cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
        if str(cluster_name).__contains__("/"):
            cluster_name = cluster_name[cluster_name.rindex("/") + 1:]
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
        update = updateSeEngineDetails(ip, csrf2, se_engine_url, cluster_status[0], aviVersion)
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
        return "SUCCESS", "CONFIGURED_TKGS_CLOUD"
    except Exception as e:
        return None, str(e)


def createIpam(ip, csrf2, managementNetworkUrl, vip_network, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
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
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def updateSeEngineDetails(ip, csrf2, seUrl, clusterUrl, aviVersion):
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


def enableWCP(ip, csrf2, aviVersion):
    try:
        vCenter = current_app.config['VC_IP']
        vc_user = current_app.config['VC_USER']
        vc_password = current_app.config['VC_PASSWORD']
        vc_data_center = current_app.config['VC_DATACENTER']
        sess = requests.post("https://" + vCenter + "/rest/com/vmware/cis/session", auth=(vc_user, vc_password),
                             verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            vc_session = sess.json()['value']

        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": vc_session
        }
        cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
        id = getClusterID(vCenter, vc_user, vc_password, cluster_name)
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
            current_app.logger.info("Wcp is already enabled")
        else:
            current_app.logger.info("Enabling Wcp..")
            control_plane_size = request.get_json(force=True)["tkgsComponentSpec"]["controlPlaneSize"]
            allowed_tkgs_size = ["TINY", "SMALL", "MEDIUM", "LARGE"]
            if not control_plane_size.upper() in allowed_tkgs_size:
                return None, \
                       "Allowed Control plane sizes [tkgsComponentSpec][controlPlaneSize] are TINY, SMALL, MEDIUM, LARGE"
            image_storage_policy_name = request.get_json(force=True)["tkgsComponentSpec"]["tkgsStoragePolicySpec"][
                "imageStoragePolicy"]
            image_storage_policyId = getPolicyID(image_storage_policy_name, vCenter, vc_user, vc_password)
            if image_storage_policyId[0] is None:
                return None, image_storage_policyId[1]
            ephemeral_storage_policy_name = \
                request.get_json(force=True)["tkgsComponentSpec"]["tkgsStoragePolicySpec"][
                    "ephemeralStoragePolicy"]
            ephemeral_storage_policyId = getPolicyID(ephemeral_storage_policy_name, vCenter, vc_user, vc_password)
            if ephemeral_storage_policyId[0] is None:
                return None, ephemeral_storage_policyId[1]
            master_storage_policy_name = \
                request.get_json(force=True)["tkgsComponentSpec"]["tkgsStoragePolicySpec"][
                    "masterStoragePolicy"]
            master_storage_policyId = getPolicyID(master_storage_policy_name, vCenter, vc_user, vc_password)
            if master_storage_policyId[0] is None:
                return None, master_storage_policyId[1]
            str_enc_avi = str(
                request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
            base64_bytes_avi = str_enc_avi.encode('ascii')
            enc_bytes_avi = base64.b64decode(base64_bytes_avi)
            password_avi = enc_bytes_avi.decode('ascii').rstrip("\n")
            avi_fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
            master_dnsServers = request.get_json(force=True)['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                'tkgsMgmtNetworkDnsServers']
            master_search_domains = request.get_json(force=True)['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                'tkgsMgmtNetworkSearchDomains']
            master_ntp_servers = request.get_json(force=True)['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                'tkgsMgmtNetworkNtpServers']
            worker_dns = request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                'tkgsWorkloadDnsServers']
            worker_ntps = request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                'tkgsWorkloadNtpServers']
            worker_cidr = request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                'tkgsPrimaryWorkloadNetworkGatewayCidr']
            start = request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                'tkgsPrimaryWorkloadNetworkStartRange']
            end = request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                'tkgsPrimaryWorkloadNetworkEndRange']
            ip_cidr = seperateNetmaskAndIp(worker_cidr)
            count_of_ip = getCountOfIpAdress(worker_cidr, start, end)
            service_cidr = request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                'tkgsWorkloadServiceCidr']
            service_cidr_split = seperateNetmaskAndIp(service_cidr)
            worker_network_name = request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                'tkgsPrimaryWorkloadPortgroupName']
            workload_network_name = request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                'tkgsPrimaryWorkloadNetworkName']
            worker_network_id = getDvPortGroupId(vCenter, vc_user, vc_password, worker_network_name, vc_data_center)
            if worker_network_id is None:
                return None, "Failed to get worker dv port id"
            ###################################################
            master_management = request.get_json(force=True)['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                'tkgsMgmtNetworkGatewayCidr']
            master_management_start = request.get_json(force=True)['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                'tkgsMgmtNetworkStartingIp']
            master_management_ip_netmask = seperateNetmaskAndIp(master_management)
            mgmt_network_name = request.get_json(force=True)['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                'tkgsMgmtNetworkName']
            mgmt_network_id = getDvPortGroupId(vCenter, vc_user, vc_password, mgmt_network_name, vc_data_center)
            if mgmt_network_id is None:
                return None, "Failed to get management dv port id"
            lib = getLibraryId(vCenter, vc_user, vc_password, ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY)
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
            url1 = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + str(id[0]) + "?action=enable"
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
                        current_app.logger.info("Cluster config status " + response_csrf.json()["config_status"])
                except:
                    pass
                time.sleep(20)
                count = count + 1
                current_app.logger.info("Waited " + str(count * 20) + "s, retrying")
            if not found:
                current_app.logger.error("Cluster is not running on waiting " + str(count * 20))
                return None, "Failed"
        '''if endpoint_ip is not None:
            current_app.logger.info("Setting up kubectl vsphere")
            time.sleep(30)
            configure_kubectl = configureKubectl(endpoint_ip)
            if configure_kubectl[1] != 200:
                return configure_kubectl[0], 500'''
        return "SUCCESS", "WCP_ENABLED"
    except Exception as e:
        return None, str(e)


def configureTkgConfiguration(vCenter_user, vc_password, cluster_endpoint):
    current_app.logger.info("Getting current Tkgs current configuration")
    current_app.logger.info("Logging in to cluster " + cluster_endpoint)
    os.putenv("KUBECTL_VSPHERE_PASSWORD", vc_password)
    connect_command = ["kubectl", "vsphere", "login", "--server=" + cluster_endpoint,
                       "--vsphere-username=" + vCenter_user,
                       "--insecure-skip-tls-verify"]
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
    with open(fileName, "w") as file_:
        proc = subprocess.run(command, stdout=subprocess.PIPE)
        file_.write(proc.stdout.decode('utf-8'))

    try:
        cni = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['defaultCNI']
        if cni:
            defaultCNI = cni
        else:
            defaultCNI = "antrea"
    except:
        defaultCNI = "antrea"
    os.system("chmod +x ./common/injectValue.sh")
    command_ = ["sh", "./common/injectValue.sh", fileName, "change_cni", defaultCNI]
    runShellCommandAndReturnOutputAsList(command_)
    try:
        isProxyEnabled = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['enableProxy']
        if str(isProxyEnabled).lower() == "true":
            proxyEnabled = True
        else:
            proxyEnabled = False
    except:
        proxyEnabled = False
    if proxyEnabled:
        try:
            httpProxy = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['httpProxy']
            httpsProxy = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['httpsProxy']
            noProxy = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['noProxy']
            list_ = convertStringToCommaSeperated(noProxy)
            ytr = dict(proxy=dict(httpProxy=httpProxy, httpsProxy=httpsProxy, noProxy=list_))
            yaml = ruamel.yaml.YAML()
            cert_list  = []
            with open(fileName, 'r') as outfile:
                cur_yaml = yaml.load(outfile)
                cur_yaml['spec'].update(ytr)
            if cur_yaml:
                with open(fileName, 'w') as yamlfile:
                    yaml.indent(mapping=2, sequence=4, offset=2)
                    yaml.dump(cur_yaml, yamlfile)
            isProxy = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['proxyCert']
            if isProxy:
                cert = Path(isProxy).read_text()
                string_bytes = cert.encode("ascii")
                base64_bytes = base64.b64encode(string_bytes)
                cert_base64 = base64_bytes.decode("ascii")
                cert_list.append(dict(name="certProxy", data=cert_base64))
            proxyPath = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs']['paths']
            proxyEndpoints = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs']['endpointUrls']
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
                        with open('cert.txt', 'r') as file2:
                            cert_base64 = file2.readline()
                    cert_list.append(dict(name="cert" + str(count), data=cert_base64))
            ytr = dict(trust=dict(additionalTrustedCAs=cert_list))
            with open(fileName, 'r') as outfile:
                cur_yaml = yaml.load(outfile)
                cur_yaml['spec'].update(ytr)
            if cur_yaml:
                with open(fileName, 'w') as yamlfile:
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
