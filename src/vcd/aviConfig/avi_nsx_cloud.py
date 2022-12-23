import sys
import time
import requests
import base64
import json
from tqdm import tqdm
from src.common.operation.constants import ResourcePoolAndFolderName, Cloud, AkoType, CIDR, TmcUser, Type, Avi_Version, \
    RegexPattern, Env, KubernetesOva, NSXtCloud, VrfType
from src.common.replace_value import generateVsphereConfiguredSubnets
import os
from src.common.operation.constants import ControllerLocation, Tkg_version
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)




def getVrfAndNextRoutId(data, ip, csrf2, cloudUuid, type, routIp, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {}
    routId = 0
    url = "https://" + ip + "/api/vrfcontext/?name.in=" + type + "&cloud_ref.uuid=" + cloudUuid
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        liist = []
        for re in response_csrf.json()['results']:
            if re['name'] == type:
                try:
                    for st in re['static_routes']:
                        liist.append(int(st['route_id']))
                        print(st['next_hop']['addr'])
                        print(routIp)
                        if st['next_hop']['addr'] == routIp:
                            return re['url'], "Already_Configured"
                    liist.sort()
                    routId = int(liist[-1]) + 1
                except:
                    pass
                if type == VrfType.MANAGEMENT:
                    routId = 1
                return re['url'], routId
            else:
                return None, "NOT_FOUND"
        return None, "NOT_FOUND"


def getSECloudStatus(data, ip, csrf2, aviVersion, seGroupName):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {}
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/serviceenginegroup"
    response_csrf = requests.request("GET", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for re in response_csrf.json()["results"]:
            if re['name'] == seGroupName:
                return re["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def seperateNetmaskAndIp(cidr):
    return str(cidr).split("/")


def addStaticRoute(data, ip, csrf2, vrfUrl, routeIp, routId, aviVersion):
    if routId == 0:
        routId = 1
    body = {
        "add": {
            "static_routes": [
                {
                    "prefix": {
                        "ip_addr": {
                            "addr": "0.0.0.0",
                            "type": "V4"
                        },
                        "mask": 0
                    },
                    "next_hop": {
                        "addr": routeIp,
                        "type": "V4"
                    },
                    "route_id": routId
                }
            ]
        }
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    url = vrfUrl
    json_object = json.dumps(body, indent=4)
    response_csrf = requests.request("PATCH", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return "SUCCESS", 200


def getCloudStatus(data, ip, csrf2, aviVersion, cloudName):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {}
    url = "https://" + ip + "/api/cloud"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for re in response_csrf.json()["results"]:
            if re['name'] == cloudName:
                os.system("rm -rf newCloudInfo.json")
                with open("./newCloudInfo.json", "w") as outfile:
                    json.dump(response_csrf.json(), outfile)
                return re["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def createNsxtSECloud(data, ip, csrf2, newCloudUrl, seGroupName, nsx_cloud_info, aviVersion):
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
        "min_scaleout_per_vs": 2,
        "max_scaleout_per_vs": 4,
        "max_se": 10,
        "vcpus_per_se": 2,
        "memory_per_se": 4096,
        "disk_per_se": 40,
        "se_deprovision_delay": 120,
        "auto_rebalance": False,
        "se_name_prefix": "Sivt",
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": False,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_ANY",
        "cpu_reserve": False,
        "mem_reserve": True,
        "ha_mode": "HA_MODE_SHARED_PAIR",
        "algo": "PLACEMENT_ALGO_PACKED",
        "buffer_se": 1,
        "active_standby": False,
        "placement_mode": "PLACEMENT_MODE_AUTO",
        "use_hyperthreaded_cores": True,
        "se_hyperthreaded_mode": "SE_CPU_HT_AUTO",
        "vs_scaleout_timeout": 600,
        "vs_scalein_timeout": 30,
        "vss_placement": {
            "num_subcores": 4,
            "core_nonaffinity": 2
        },
        "realtime_se_metrics": {
            "enabled": False,
            "duration": 30
        },
        "se_dos_profile": {
            "thresh_period": 5
        },
        "distribute_vnics": False,
        "cloud_ref": newCloudUrl,
        "vcenter_datastores": [

        ],
        "license_tier": "ENTERPRISE",
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
        "name": seGroupName,
        "vcenters": [
            {
                "vcenter_ref": nsx_cloud_info["vcenter_url"],
                "nsxt_clusters": {
                    "include": True,
                    "cluster_ids": [
                        nsx_cloud_info["cluster"]
                    ]
                },
                "clusters": [

                ]
            }
        ]
    }
    url = "https://" + ip + "/api/serviceenginegroup"
    json_object = json.dumps(body, indent=4)
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def getNewBody(data, newCloudUrl, seGroupName):
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
        "se_name_prefix": "Avi",
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


def createSECloud_Arch(data, ip, csrf2, newCloudUrl, seGroupName, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    json_object = getNewBody(newCloudUrl, seGroupName)
    url = "https://" + ip + "/api/serviceenginegroup"
    response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def getIpam(data, ip, csrf2, name, aviVersion):
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


def createIpam_nsxtCloud(data, ip, csrf2, managementNetworkUrl, ipam_name, aviVersion):
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {
            "internal_profile": {
                "usable_networks": [
                    {
                        "nw_ref": managementNetworkUrl
                    }
                ]
            },
            "allocate_ip_in_vrf": False,
            "type": "IPAMDNS_TYPE_INTERNAL",
            "name": ipam_name
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/ipamdnsproviderprofile"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], response_csrf.json()["uuid"], "SUCCESS"
    except Exception as e:
        print("ERROR: " + str(e))
        return None, "Exception occurred while creation ipam profile for NSXT-T Cloud"


def getNsxTNetworkDetails(data, ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion):
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
    os.system("rm -rf managementNetworkDetails.json")
    with open("./managementNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    with open("./managementNetworkDetails.json") as f:
        data = json.load(f)
    dic = dict(dhcp_enabled=False)
    data.update(dic)
    with open("./managementNetworkDetails.json", 'w') as f:
        json.dump(data, f)
    generateVsphereConfiguredSubnets("managementNetworkDetails.json", startIp, endIp, prefixIp,
                                     int(netmask))
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        # vim_ref has been removed for NSX-T cloud
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        return "AlreadyConfigured", 200, details
    except Exception as e:
        print("ERROR: Ip pools are not configured configuring it")
    return "SUCCESS", 200, details


def associate_ipam_nsxtCloud(data, ip, csrf2, aviVersion, nsxtCloud_uuid, ipamUrl, dnsUrl):
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}

        url = "https://" + ip + "/api/cloud/" + nsxtCloud_uuid
        cloud_details_response = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if cloud_details_response.status_code != 200:
            return None, "Failed to fetch IPAM details for NSXT Cloud"

        # append ipam details to response
        ipam_details = {"ipam_provider_ref": ipamUrl, "dns_provider_ref": dnsUrl}
        json_response = cloud_details_response.json()
        json_response.update(ipam_details)
        json_object = json.dumps(json_response, indent=4)

        response = requests.request("PUT", url, headers=headers, data=json_object, verify=False)
        if response.status_code != 200:
            return None, response.text

        return "SUCCESS", "IPAM/DNS association with NSXT Cloud completed"
    except Exception as e:
        print("ERROR: " + str(e))
        return None, "Exception occurred during association of DNS and IPAM profile with NSX-T Cloud"


def createDns_nsxtCloud(data, ip, csrf2, dns_domain, dns_profile_name, aviVersion):
    try:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {
            "internal_profile": {
                "ttl": 30,
                "dns_service_domain": [
                    {
                        "pass_through": True,
                        "domain_name": dns_domain
                    }
                ]
            },
            "type": "IPAMDNS_TYPE_INTERNAL_DNS",
            "name": dns_profile_name
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/ipamdnsproviderprofile"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            return response_csrf.json()["url"], response_csrf.json()["uuid"], "SUCCESS"
    except Exception as e:
        print("ERROR: " + str(e))
        return None, "Exception occurred while creation DNS profile for NSXT-T Cloud "


def obtain_second_csrf(data, ip):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    str_enc_avi = str(data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviPasswordBase64'])
    base64_bytes_avi = str_enc_avi.encode('ascii')
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode('ascii').rstrip("\n")
    payload = {
        "username": "admin",
        "password": password_avi
    }
    modified_payload = json.dumps(payload, indent=4)
    response_csrf = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
    if response_csrf.status_code != 200:
        return None
    cookies_string = ""
    cookiesString = requests.utils.dict_from_cookiejar(response_csrf.cookies)
    for key, value in cookiesString.items():
        cookies_string += key + "=" + value + "; "
    return cookiesString['csrftoken'], cookies_string


def obtain_avi_version(data, ip):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    str_enc_avi = str(data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviPasswordBase64'])
    base64_bytes_avi = str_enc_avi.encode('ascii')
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode('ascii').rstrip("\n")
    payload = {
        "username": "admin",
        "password": password_avi
    }
    modified_payload = json.dumps(payload, indent=4)
    response_avi = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
    if response_avi.status_code != 200:
        default = {
            "username": "admin",
            "password": "58NFaGDJm(PJH0G"
        }
        modified_payload = json.dumps(default, indent=4)
        response_avi = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
        if response_avi.status_code != 200:
            return None, response_avi.text
    return response_avi.json()["version"]["Version"], 200


def waitForCloudPlacementReady(data, ip, csrf2, name, aviVersion):
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
        raise AssertionError("Failed to get cloud " + name + " uuid")
    status_url = "https://" + ip + "/api/cloud/" + uuid + "/status"
    count = 0
    response_csrf = None
    while count < 60:
        response_csrf = requests.request("GET", status_url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, "Failed", "Error"
        try:
            print("INFO: " + name + " cloud state " + response_csrf.json()["state"])
            if response_csrf.json()["state"] == "CLOUD_STATE_PLACEMENT_READY":
                break
        except:
            pass
        count = count + 1
        time.sleep(10)
        print("INFO: Waited for " + str(count * 10) + "s retrying")
    if response_csrf is None:
        print("ERROR: Waited for " + str(count * 10) + "s default cloud status")
        raise AssertionError("ERROR: Waited for " + str(count * 10) + "s default cloud status")
    return "SUCCESS", "READY", response_csrf.json()["state"]


def fetchTier1GatewayId(data, ip, headers, nsxt_credential):
    try:
        url = "https://" + ip + "/api/nsxt/tier1s"
        teir1name = str(data['envSpec']['aviNsxCloudSpec']['aviSeTier1Details']["nsxtTier1SeMgmtNetworkName"])
        address = str(data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtAddress"])
        body = {
            "host": address,
            "credentials_uuid": nsxt_credential
        }
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        print(response_csrf.json())
        for library in response_csrf.json()["resource"]["nsxt_tier1routers"]:
            if library["name"] == teir1name:
                return "Success", library["id"]
        return None, "TIER1_GATEWAY_ID_NOT_FOUND"
    except Exception as e:
        return None, str(e)


def createNsxtCloud(data, ip, csrf2, aviVersion):
    try:
        cloudName = data['envSpec']['aviNsxCloudSpec']['aviNsxCloudName']
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        cloud_connect_user, cred = createCloudConnectUser(data, ip, headers)
        if cloud_connect_user is None:
            return None, cred
        nsxt_cred = cred["nsxUUid"]
        zone, status_zone = fetchTransportZoneId(data, ip, headers, nsxt_cred)
        if zone is None:
            return None, status_zone
        tier1_id, status_tier1 = fetchTier1GatewayId(data, ip, headers, nsxt_cred)
        if tier1_id is None:
            return None, status_tier1
        tz_id, status_tz = fetchTransportZoneId(data, ip, headers, nsxt_cred)
        if tz_id is None:
            return None, status_tz
        seg_id, status_seg = fetchSegmentsId(data, ip, headers, nsxt_cred, status_tz, status_tier1)
        if seg_id is None:
            return None, status_seg
        status, value = getCloudConnectUser(data, ip, headers)
        address = str(data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtAddress"])
        if isinstance(value, tuple):
            nsx_url = value[2]
        else:
            nsx_url = value["nsx_user_url"]
        body = {
            "dhcp_enabled": True,
            "dns_resolution_on_se": False,
            "enable_vip_on_all_interfaces": False,
            "enable_vip_static_routes": False,
            "ip6_autocfg_enabled": False,
            "maintenance_mode": False,
            "mtu": 1500,
            "nsxt_configuration": {
                "site_id": "default",
                "domain_id": "default",
                "enforcementpoint_id": "default",
                "automate_dfw_rules": False,
                "data_network_config": {
                    "transport_zone": status_zone,
                    "tz_type": "OVERLAY",
                    "tier1_segment_config": {
                        "segment_config_mode": "TIER1_SEGMENT_MANUAL",
                        "manual": {
                            "tier1_lrs": [
                                {
                                    "segment_id": status_seg["avi_mgmt"],
                                    "tier1_lr_id": status_tier1
                                }
                            ]
                        }
                    }
                },
                "management_network_config": {
                    "transport_zone": status_zone,
                    "tz_type": "OVERLAY",
                    "overlay_segment": {
                        "segment_id": status_seg["avi_mgmt"],
                        "tier1_lr_id": status_tier1
                    }
                },
                "nsxt_credentials_ref": nsx_url,
                "nsxt_url": address
            },
            "obj_name_prefix": cloudName,
            "name": cloudName,
            "prefer_static_routes": False,
            "state_based_dns_registration": True,
            "vmc_deployment": False,
            "vtype": "CLOUD_NSXT"
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + ip + "/api/cloud"
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 201:
            return None, response_csrf.text
        else:
            os.system("rm -rf newCloudInfo.json")
            with open("./newCloudInfo.json", "w") as outfile:
                json.dump(response_csrf.json(), outfile)
            return response_csrf.json()["url"], "SUCCESS"
    except Exception as e:
        return None, str(e)


def getCloudConnectUser(data, ip, headers):
    url = "https://" + ip + "/api/cloudconnectoruser"
    payload = {}
    try:
        response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return "API_FAILURE", response_csrf.text
        vcenterCred = False
        nsxCred = False
        uuid = {}
        list_ = response_csrf.json()["results"]
        if len(list_) == 0:
            return "EMPTY", "EMPTY"
        for result in list_:
            if result["name"] == NSXtCloud.VCENTER_CREDENTIALS:
                uuid["vcenterUUId"] = result["uuid"]
                uuid["vcenter_user_url"] = result["url"]
                vcenterCred = True
            if result["name"] == NSXtCloud.NSXT_CREDENTIALS:
                uuid["nsxUUid"] = result["uuid"]
                uuid["nsx_user_url"] = result["url"]
                nsxCred = True
        if vcenterCred and nsxCred:
            return "BOTH_CRED_CREATED", uuid
        found = False
        if vcenterCred:
            found = True
            tuple_ = "VCENTER_CRED_FOUND", uuid["vcenterUUId"], uuid["vcenter_user_url"]
        if nsxCred:
            found = True
            tuple_ = "NSX_CRED_FOUND", uuid["nsxUUid"], uuid["nsx_user_url"]
        if found:
            return "ONE_CRED_FOUND", tuple_
        return "NO_CRED_FOUND", "NO_CRED_FOUND"
    except Exception as e:
        return "EXCEPTION", "Failed " + str(e)


def fetchSegmentsId(data, ip, headers, nsxt_credential, tz_id, tier1_id):
    try:
        url = "https://" + ip + "/api/nsxt/segments"
        address = str(data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtAddress"])
        body = {
            "host": address,
            "credentials_uuid": nsxt_credential,
            "transport_zone_id": tz_id,
            "tier1_id": tier1_id
        }
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        segId = {}
        avi_mgmt = data['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkName']
        # tkg_cluster_vip_name = data['tkgComponentSpec']['tkgClusterVipNetwork'][
        # 'tkgClusterVipNetworkName']
        for library in response_csrf.json()["resource"]["nsxt_segments"]:
            if library["name"] == avi_mgmt:
                segId["avi_mgmt"] = library["id"]
            # elif library["name"] == tkg_cluster_vip_name:
            # segId["cluster_vip"] = library["id"]
            if len(segId) == 1:
                break
        if len(segId) < 1:
            return None, "SEGMENT_NOT_FOUND " + str(segId)
        return "Success", segId
    except Exception as e:
        return None, str(e)


def fetchTransportZoneId(data, ip, headers, nsxt_credential):
    try:
        url = "https://" + ip + "/api/nsxt/transportzones"
        overlay = str(data['envSpec']['aviNsxCloudSpec']['aviSeTier1Details']["nsxtOverlay"])
        address = str(data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtAddress"])
        body = {
            "host": address,
            "credentials_uuid": nsxt_credential
        }
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        for library in response_csrf.json()["resource"]["nsxt_transportzones"]:
            if library["name"] == overlay and library["tz_type"] == "OVERLAY":
                return "Success", library["id"]
        return None, "TRANSPORT_ZONE_ID_NOT_FOUND"
    except Exception as e:
        return None, str(e)


def createCloudConnectUser(data, ip, headers):
    url = "https://" + ip + "/api/cloudconnectoruser"
    try:
        vcenter_username = data['envSpec']['aviNsxCloudSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(data['envSpec']['aviNsxCloudSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")

        str_enc_nsx = str(data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtUserPasswordBase64"])
        base64_bytes_nsx = str_enc_nsx.encode('ascii')
        enc_bytes_nsx = base64.b64decode(base64_bytes_nsx)
        password_nsx = enc_bytes_nsx.decode('ascii').rstrip("\n")
        nsx_user = data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtUser"]
        list_body = []
        body_nsx = {
            "name": NSXtCloud.NSXT_CREDENTIALS,
            "nsxt_credentials": {
                "username": nsx_user,
                "password": password_nsx
            }
        }
        body_vcenter = {
            "name": NSXtCloud.VCENTER_CREDENTIALS,
            "vcenter_credentials": {
                "username": vcenter_username,
                "password": password
            }
        }
        status_ = {}
        body_vcenter = json.dumps(body_vcenter, indent=4)
        body_nsx = json.dumps(body_nsx, indent=4)
        cloud_user, status = getCloudConnectUser(data, ip, headers)
        if str(cloud_user) == "EXCEPTION" or str(cloud_user) == "API_FAILURE":
            return None, status
        if str(status) == "NO_CRED_FOUND" or str(status) == "EMPTY":
            print("INFO: Creating Nsx and vcenter credential")
            list_body.append(body_vcenter)
            list_body.append(body_nsx)
        if str(cloud_user) == "ONE_CRED_FOUND":
            if str(status[0]) == "VCENTER_CRED_FOUND":
                print("INFO: Creating Nsx credentials")
                status_["vcenterUUId"] = status[1]["uuid"]
                list_body.append(body_nsx)
            elif str(status[0]) == "NSX_CRED_FOUND":
                print("INFO: Creating Vcenter credentials")
                status_["nsxUUid"] = status[1]["uuid"]
                list_body.append(body_vcenter)
        if str(cloud_user) != "BOTH_CRED_CREATED":
            for body in list_body:
                response_csrf = requests.request("POST", url, headers=headers, data=body, verify=False)
                if response_csrf.status_code != 201:
                    return None, response_csrf.text
                try:
                    nsx = response_csrf.json()["nsxt_credentials"]
                    status_["nsxUUid"] = response_csrf.json()["uuid"]
                except:
                    pass
                try:
                    vcenter = response_csrf.json()["vcenter_credentials"]
                    status_["vcenterUUId"] = response_csrf.json()["uuid"]
                except:
                    pass
                time.sleep(10)
            if len(status_) < 2:
                return None, "INSUFFICIENT_ITEMS " + str(status_)
            return "SUCCESS", status_
        else:
            return "SUCCESS", status
    except Exception as e:
        return None, str(e)


def getNetworkUrl(data, ip, csrf2, name, aviVersion):
    cloudName = data['envSpec']['aviNsxCloudSpec']['aviNsxCloudName']
    with open("./newCloudInfo.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except:
        cloud_name = cloudName
        for re in new_cloud_json["results"]:
            if re["name"] == cloud_name:
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
            response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code == 200:
                if response_csrf.json()["count"] > 1:
                    break
            count = count + 1
            time.sleep(10)
            print("INFO: Waited for " + str(count * 10) + "s retrying")
        if response_csrf is None:
            print("ERROR: Waited for " + str(count * 10) + "s but service engine is not up")
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
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=payload, verify=False)
                    for se in response_csrf.json()["results"]:
                        if se["config"]["name"] == name:
                            return se["config"]["url"], se["config"]["uuid"], "FOUND", "SUCCESS"
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
        return None, "NOT_FOUND", "Failed"
    except KeyError:
        return None, "NOT_FOUND", "Failed"


# def updateVipNetworkIpPools(ip, csrf2, get_vip, aviVersion):
# try:
# startIp = data["tkgComponentSpec"]['tkgClusterVipNetwork'][
# "tkgClusterVipIpStartRange"]
# endIp = data["tkgComponentSpec"]['tkgClusterVipNetwork'][
# "tkgClusterVipIpEndRange"]
# prefixIpNetmask = seperateNetmaskAndIp(
# data["tkgComponentSpec"]['tkgClusterVipNetwork'][
# "tkgClusterVipNetworkGatewayCidr"])
# getVIPNetworkDetails = getNSXTNetworkDetailsVip(ip, csrf2, get_vip[0], startIp, endIp, prefixIpNetmask[0],
# prefixIpNetmask[1], aviVersion)
# if getVIPNetworkDetails[0] is None:
# raise AssertionError("Failed to get VIP network details " + str(getVIPNetworkDetails[2]))
# if getVIPNetworkDetails[0] == "AlreadyConfigured":
# print("INFO: Vip Ip pools are already configured.")
# ip_pre = getVIPNetworkDetails[2]["subnet_ip"] + "/" + str(getVIPNetworkDetails[2]["subnet_mask"])
# else:
# update_resp = updateNetworkWithIpPools(ip, csrf2, get_vip[0], "vipNetworkDetails.json",
# aviVersion)
# if update_resp[0] != 200:
# raise AssertionError("Failed to update VIP network ip pools " + str(update_resp[1]))
# ip_pre = update_resp[2]["subnet_ip"] + "/" + str(update_resp[2]["subnet_mask"])
# with open("vip_ip.txt", "w") as e:
# e.write(ip_pre)
# print("INFO: Updated VIP IP pools successfully")
# except Exception as e:
# raise AssertionError("Failed to update VIP IP pools " + str(e))


def fetchContentLibrary(data, ip, headers, vcenter_credential):
    try:
        vc_Content_Library_name = data["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["serviceEngineGroup"]["vcenterPlacementDetails"]["vcenterContentSeLibrary"]
        if not vc_Content_Library_name:
            vc_Content_Library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
        vCenter = data['envSpec']['aviNsxCloudSpec']['vcenterDetails']['vcenterAddress']
        url = "https://" + ip + "/api/vcenter/contentlibraries"
        body = {
            "host": vCenter,
            "credentials_uuid": vcenter_credential
        }
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        for library in response_csrf.json()["resource"]["vcenter_clibs"]:
            if library["name"] == vc_Content_Library_name:
                return "Success", library["id"]
        return None, "CONTENT_LIBRARY_NOT_FOUND"
    except Exception as e:
        return None, str(e)


def fetchVcenterId(data, ip, headers, nsxt_credential, tz_id):
    try:
        url = "https://" + ip + "/api/nsxt/vcenters"
        address = str(data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtAddress"])
        body = {
            "host": address,
            "credentials_uuid": nsxt_credential,
            "transport_zone_id": tz_id
        }
        json_object = json.dumps(body, indent=4)
        response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        for library in response_csrf.json()["resource"]["vcenter_ips"]:
            return "Success", library["vcenter_ip"]["addr"]
        return None, "TIER_1_GATEWAY_ID_NOT_FOUND"
    except Exception as e:
        return None, str(e)


def configureVcenterInNSXTCloud(data, ip, csrf2, cloud_url, aviVersion):
    VC_NAME = "SIVT_VC"
    cloudName = data['envSpec']['aviNsxCloudSpec']['aviNsxCloudName']
    url = "https://" + ip + "/api/vcenterserver"
    try:
        with open("./newCloudInfo.json", 'r') as file2:
            new_cloud_json = json.load(file2)
        cloud = cloudName
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except:
            for re in new_cloud_json["results"]:
                if re["name"] == cloud:
                    uuid = re["uuid"]
        if uuid is None:
            print("ERROR:  " + cloud + " cloud not found")
            return None, cloud + "NOT_FOUND"
        get_url = "https://" + ip + "/api/vcenterserver/?cloud_ref.uuid=" + uuid
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        payload = {}
        response_csrf = requests.request("GET", get_url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        vc_info = {}
        found = False
        try:
            for vc in response_csrf.json()["results"]:
                if vc["name"] == VC_NAME:
                    vc_info["vcenter_url"] = vc["url"]
                    vc_info["vc_uuid"] = vc["uuid"]
                    found = True
                    break
        except:
            found = False
        if found:
            cluster_url = "https://" + ip + "/api/nsxt/clusters"
            payload = {
                "cloud_uuid": uuid,
                "vcenter_uuid": vc_info["vc_uuid"]
            }
            payload = json.dumps(payload, indent=4)
            response_csrf = requests.request("POST", cluster_url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            cluster_name = data["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["serviceEngineGroup"]["vcenterPlacementDetails"]["vcenterCluster"]
            for cluster in response_csrf.json()["resource"]["nsxt_clusters"]:
                if cluster["name"] == cluster_name:
                    vc_info["cluster"] = cluster["vc_mobj_id"]
                    break
            return "SUCCESS", vc_info
        else:
            cloud_connect_user, cred = createCloudConnectUser(data, ip, headers)
            if cloud_connect_user is None:
                return None, cred
            vcenter_credential = cred["vcenterUUId"]
            nsxt_credential = cred["nsxUUid"]
            vc_Content_Library_name = data["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["serviceEngineGroup"]["vcenterPlacementDetails"]["vcenterContentSeLibrary"]
            if not vc_Content_Library_name:
                vc_Content_Library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
            library, status_lib = fetchContentLibrary(data, ip, headers, vcenter_credential)
            if library is None:
                return None, status_lib
            tz_id, status_tz = fetchTransportZoneId(data, ip, headers, nsxt_credential)
            if tz_id is None:
                return None, status_tz
            vc_id, status_vc = fetchVcenterId(data, ip, headers, nsxt_credential, status_tz)
            if vc_id is None:
                return None, status_vc
            payload = {
                "cloud_ref": cloud_url,
                "content_lib": {
                    "id": status_lib,
                    "name": vc_Content_Library_name
                },
                "name": VC_NAME,
                "tenant_ref": "https://" + ip + "/api/tenant/admin",
                "vcenter_credentials_ref": "https://" + ip + "/api/cloudconnectoruser/" + vcenter_credential,
                "vcenter_url": status_vc
            }
            payload = json.dumps(payload, indent=4)
            response_csrf = requests.request("POST", url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code != 201:
                return None, response_csrf.text
            vc_info["vcenter_url"] = response_csrf.json()["url"]
            vc_info["vc_uuid"] = response_csrf.json()["uuid"]
            cluster_url = "https://" + ip + "/api/nsxt/clusters"
            payload = {
                "cloud_uuid": uuid,
                "vcenter_uuid": vc_info["vc_uuid"]
            }
            payload = json.dumps(payload, indent=4)
            response_csrf = requests.request("POST", cluster_url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            cluster_name = data["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["serviceEngineGroup"]["vcenterPlacementDetails"]["vcenterCluster"]
            for cluster in response_csrf.json()["resource"]["nsxt_clusters"]:
                if cluster["name"] == cluster_name:
                    vc_info["cluster"] = cluster["vc_mobj_id"]
                    break
            return "SUCCESS", vc_info
    except Exception as e:
        return None, str(e)


def updateNetworkWithIpPools(data, ip, csrf2, managementNetworkUrl, fileName, aviVersion):
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
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        count = 0
        if response_csrf.text.__contains__(
                "Cannot edit network properties till network sync from Service Engines is complete"):
            while count < 10:
                time.sleep(60)
                response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
                if response_csrf.status_code == 200:
                    break
                print("INFO: waited for " + str(count * 60) + "s sync to complete")
                count = count + 1
        else:
            return 500, response_csrf.text, details
    details["subnet_ip"] = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
    details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
    return 200, "SUCCESS", details


def isAviHaEnabled(data):
    try:
        enable_avi_ha = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['enableAviHa']
        if str(enable_avi_ha).lower() == "true":
            return True
        else:
            return False
    except:
        return False


def nsx_cloud_creation(file, deploy_se):
    with open(file, "r") as out:
        data = json.load(out)
    isDeployNsxCloud = data['envSpec']['aviNsxCloudSpec']['configureAviNsxtCloud']
    isAviDeploy = data['envSpec']['aviCtrlDeploySpec']['deployAvi']
    if isAviDeploy == "false":
        avi_fqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']
        ip = avi_fqdn
    else:
        avi_fqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']
        if isAviHaEnabled(data):
            aviClusterFqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']
            ip = aviClusterFqdn
        else:
            ip = avi_fqdn
    csrf2 = obtain_second_csrf(data, ip)
    if csrf2 is None:
        print("ERROR: Failed to get csrf from new set password")
        return "Failed", 500
    deployed_avi_version = obtain_avi_version(data, ip)
    if deployed_avi_version[0] is None:
        print("ERROR: Failed to login and obtain avi version" + str(deployed_avi_version[1]))
        return "Failed", 500
    aviVersion = deployed_avi_version[0]
    default = waitForCloudPlacementReady(data, ip, csrf2, "Default-Cloud", aviVersion)
    if default[0] is None:
        print("ERROR: Failed to get default cloud status")
        return "Failed", 500
    cloudName = data['envSpec']['aviNsxCloudSpec']['aviNsxCloudName']
    get_cloud = getCloudStatus(data, ip, csrf2, aviVersion, cloudName)
    if get_cloud[0] is None:
        print("ERROR: Failed to get cloud status " + str(get_cloud[1]))
        return "Failed", 500
    isGen = False
    if get_cloud[0] == "NOT_FOUND":
        isGen = True
        if isDeployNsxCloud == "true":
            print("INFO: Creating New cloud " + cloudName)
            seg_status = createNsxtSegment(data)
            if seg_status[0] is None:
                print("ERROR: Failed to create SE Management Segment " + str(seg_status[1]))
            cloud = createNsxtCloud(data, ip, csrf2, aviVersion)
            if cloud[0] is None:
                print("ERROR: Failed to create cloud " + str(cloud[1]))
                return "Failed", 500
            cloud_url = cloud[0]
        else:
            print("ERROR: User opted not to create cloud, but it is not found " + cloudName)
            return "Failed", 500
    else:
        cloud_url = get_cloud[0]
    if isGen:
        for i in tqdm(range(60), desc="Waiting…", ascii=False, ncols=75):
            time.sleep(1)
    if deploy_se:
        state = create_service_engine_group(data, ip, csrf2, aviVersion, cloud_url)
        if state is None:
            return "Failed", 500
        print("INFO: Configured se cloud successfully")
    else:
        print("INFO: Configured nsx cloud successfully")
    return "SUCCESS", 200


def getCloudSate(file):
    with open(file, "r") as out:
        data = json.load(out)
    isAviDeploy = data['envSpec']['aviCtrlDeploySpec']['deployAvi']
    if isAviDeploy == "false":
        avi_fqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']
        ip = avi_fqdn
    else:
        avi_fqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']
        if isAviHaEnabled(data):
            aviClusterFqdn = data['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']
            ip = aviClusterFqdn
        else:
            ip = avi_fqdn
    csrf2 = obtain_second_csrf(data, ip)
    if csrf2 is None:
        print("ERROR: Failed to get csrf from new set password")
        return "Failed", 500
    deployed_avi_version = obtain_avi_version(data, ip)
    if deployed_avi_version[0] is None:
        print("ERROR: Failed to login and obtain avi version" + str(deployed_avi_version[1]))
        return "Failed", 500
    aviVersion = deployed_avi_version[0]
    default = waitForCloudPlacementReady(data, ip, csrf2, "Default-Cloud", aviVersion)
    if default[0] is None:
        print("ERROR: Failed to get default cloud status")
        return "Failed", 500
    cloudName = data['envSpec']['aviNsxCloudSpec']['aviNsxCloudName']
    get_cloud = getCloudStatus(data, ip, csrf2, aviVersion, cloudName)
    if get_cloud[0] is None:
        print("ERROR: Failed to get cloud status " + str(get_cloud[1]))
        return "Failed", 500
    if get_cloud[0] == "NOT_FOUND":
        return "NOT_FOUND"
    else:
        return "FOUND"


def create_service_engine_group(data, ip, csrf2, aviVersion, cloud_url):
    create_se = data['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['createSeGroup']
    seGroupName = data['envSpec']['cseSpec']['svcOrgVdcSpec']['serviceEngineGroup']['serviceEngineGroupName']
    if create_se == "true":
        get_se_cloud = getSECloudStatus(data, ip, csrf2, aviVersion, seGroupName)
        if get_se_cloud[0] is None:
            print("ERROR: Failed to get se cloud status " + str(get_se_cloud[1]))
            return None
        if get_se_cloud[0] == "NOT_FOUND":

            print("INFO: Creating New se cloud " + seGroupName)
            nsx_cloud_info = configureVcenterInNSXTCloud(data, ip, csrf2, cloud_url, aviVersion)
            if nsx_cloud_info[0] is None:
                print("ERROR: Failed to configure vcenter in cloud " + str(nsx_cloud_info[1]))
                return None

            cloud_se = createNsxtSECloud(data, ip, csrf2, cloud_url, seGroupName, nsx_cloud_info[1], aviVersion)
            if cloud_se[0] is None:
                print("ERROR: Failed to create se cloud " + str(cloud_se[1]))
                return None
            print("INFO: Waiting for  3m  for se to be up.")
            time.sleep(180)
        else:
            print("INFO: " + seGroupName + " already created")
    else:
        get_se_cloud = getSECloudStatus(data, ip, csrf2, aviVersion, seGroupName)
        if get_se_cloud[0] is None:
            print("ERROR: Failed to get se cloud status " + str(get_se_cloud[1]))
            return None
        if get_se_cloud[0] == "NOT_FOUND":
            print("ERROR: " + seGroupName + " not  found, but  user opted not to create.")
            return None
    return "SUCCESS"


def grabNsxtHeaders(data):
    try:
        str_enc = str(data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtUserPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")

        ecod_bytes = (data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtUser"] + ":" + password).encode(
            "ascii")
        ecod_bytes = base64.b64encode(ecod_bytes)
        address = str(data['envSpec']['aviNsxCloudSpec']['nsxDetails']["nsxtAddress"])
        ecod_string = ecod_bytes.decode("ascii")
        headers = {'Authorization': (
                'Basic ' + ecod_string)}
        return "SUCCESS", headers, address
    except Exception as e:
        return None, str(e), None


def getList(headers, url):
    payload = {}
    list_all_segments_url = url
    list_all_segments_response = requests.request("GET", list_all_segments_url, headers=headers,
                                                  data=payload,
                                                  verify=False)
    if list_all_segments_response.status_code != 200:
        return list_all_segments_response.text, list_all_segments_response.status_code

    return list_all_segments_response.json()["results"], 200


def getTransportZone(address, transport_zone_name, headers_):
    try:
        url = "https://" + address + "/api/v1/transport-zones/"
        payload = {}
        tzone_response = requests.request("GET", url, headers=headers_,
                                          data=payload,
                                          verify=False)
        if tzone_response.status_code != 200:
            return None, tzone_response.text
        for tzone in tzone_response.json()["results"]:
            if str(tzone["transport_type"]) == "OVERLAY" and str(tzone["display_name"]) == transport_zone_name:
                return tzone["id"], "FOUND"
        return None, "NOT_FOUND"
    except Exception as e:
        return None, str(e)


def getTier1Details(headers_, t1_router):
    uri = "https://" + headers_[2] + "/policy/api/v1/infra/tier-1s"
    response = requests.request(
        "GET", uri, headers=headers_[1], verify=False)
    if response.status_code != 200:
        return None, response.status_code
    teir1name = str(t1_router)
    for tr in response.json()["results"]:
        if str(tr["display_name"]).lower() == teir1name.lower():
            return tr["path"], "FOUND"
    return None, "NOT_FOUND"


def checkObjectIsPresentAndReturnPath(listOfSegments, name):
    try:
        for segmentName in listOfSegments:
            if segmentName['display_name'] == name:
                return True, segmentName['path']
    except:
        return False, None
    return False, None


def convertStringToCommaSeperated(strA):
    strA = strA.split(",")
    list = []
    for s in strA:
        list.append(s.replace(" ", ""))
    return list


def getNetworkIp(gatewayAddress):
    ipNet = seperateNetmaskAndIp(gatewayAddress)
    ss = ipNet[0].split(".")
    return ss[0] + "." + ss[1] + "." + ss[2] + ".0" + "/" + ipNet[1]


def createNsxtSegment(data):
    try:
        gatewayAddress = data['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkGatewayCidr']
        dhcpStart = data['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkDhcpStartRange']
        dhcpEnd = data['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkDhcpEndRange']
        segementName = data['envSpec']['aviNsxCloudSpec']['aviSeMgmtNetwork']['aviSeMgmtNetworkName']
        dnsServers = str(data['envSpec']['infraComponents']["ntpServers"])
        network = getNetworkIp(gatewayAddress)
        isDhcp = False
        headers_ = grabNsxtHeaders(data)
        if headers_[0] is None:
            print("ERROR: Failed to get NSXT info " + str(headers_[1]))
            return None, str(headers_[1])
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            return None, str(output[0])
        overlay = str(data['envSpec']['aviNsxCloudSpec']['aviSeTier1Details']['nsxtOverlay'])
        ntp_servers = str(data['envSpec']['infraComponents']["ntpServers"])
        trz = getTransportZone(headers_[2], overlay, headers_[1])
        if trz[0] is None:
            return None, str(trz[1])
        t1_router = str(data['envSpec']['aviNsxCloudSpec']['aviSeTier1Details']['nsxtTier1SeMgmtNetworkName'])
        tier_path = getTier1Details(headers_, t1_router)
        if tier_path[0] is None:
            return None, str(tier_path[1])
        if not checkObjectIsPresentAndReturnPath(output[0], segementName)[0]:
            print("INFO: Creating segment " + segementName)
            url = "https://" + headers_[2] + "/policy/api/v1/infra/segments/" + segementName
            if isDhcp:
                payload = {
                    "display_name": segementName,
                    "subnets": [
                        {
                            "gateway_address": gatewayAddress,
                            "dhcp_ranges": [
                                dhcpStart + "-" + dhcpEnd
                            ],
                            "dhcp_config": {
                                "resource_type": "SegmentDhcpV4Config",
                                "lease_time": 86400,
                                "dns_servers": convertStringToCommaSeperated(dnsServers),
                                "options": {
                                    "others": [
                                        {
                                            "code": 42,
                                            "values": convertStringToCommaSeperated(ntp_servers)
                                        }
                                    ]
                                }
                            },
                            "network": network
                        }
                    ],
                    "connectivity_path": tier_path[0],
                    "transport_zone_path": "/infra/sites/default/enforcement-points/default/transport-zones/" + str(
                        trz[0]),
                    "id": segementName
                }
            else:
                payload = {
                    "display_name": segementName,
                    "subnets": [
                        {
                            "gateway_address": gatewayAddress
                        }
                    ],
                    "replication_mode": "MTEP",
                    "transport_zone_path": "/infra/sites/default/enforcement-points/default/transport-zones/" + str(
                        trz[0]),
                    "admin_state": "UP",
                    "advanced_config": {
                        "address_pool_paths": [
                        ],
                        "multicast": True,
                        "urpf_mode": "STRICT",
                        "connectivity": "ON"
                    },
                    "connectivity_path": tier_path[0],
                    "id": segementName
                }
            headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
            payload_modified = json.dumps(payload, indent=4)
            dhcp_create = requests.request("PUT", url,
                                           headers=headers_[1],
                                           data=payload_modified,
                                           verify=False)
            if dhcp_create.status_code != 200:
                print("ERROR: " + dhcp_create.text)
                return None, dhcp_create.text
            msg_text = "Created " + segementName
            print("INFO: " + msg_text)
            print("INFO: Waiting for 1 min for status == ready")
            time.sleep(60)
        else:
            msg_text = segementName + " is already created"
            print("INFO: " + msg_text)
        return "SUCCESS", msg_text

    except Exception as e:
        print("ERROR: Failed to create NSXT segment " + str(e))
        return None, str(e)
