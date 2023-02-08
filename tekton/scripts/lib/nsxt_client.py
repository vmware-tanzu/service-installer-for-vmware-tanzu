    #  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import json
import os
from pathlib import Path
import time
import ipaddress
import socket
from pathlib import Path
from constants.constants import Paths
import base64
import requests
import struct
import time
import fcntl
from model.run_config import RunConfig

from util.logger_helper import LoggerHelper
from constants.nsxt_constants import  VCF

logger = LoggerHelper.get_logger(Path(__file__).stem)


class NsxtClient:
    def __init__(self, run_config: RunConfig):
        self.run_config = run_config
        self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)

        with open(self.jsonpath) as f:
            self.jsonspec = json.load(f)


    def checkObjectIsPresentAndReturnPath(self,listOfSegments, name):
        try:
            for segmentName in listOfSegments:
                if segmentName['display_name'] == name:
                    return True, segmentName['path']
        except:
            return False, None
        return False, None


    def convertStringToCommaSeperated(self, strA):
        strA = strA.split(",")
        list = []
        for s in strA:
            list.append(s.replace(" ", ""))
        return list


    def getTransportZone(self, address, transport_zone_name, headers_):
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

    def getList(self, headers, url):
        payload = {}
        list_all_segments_url = url
        list_all_segments_response = requests.request("GET", list_all_segments_url, headers=headers,
                                                    data=payload,
                                                    verify=False)
        if list_all_segments_response.status_code != 200:
            return list_all_segments_response.text, list_all_segments_response.status_code

        return list_all_segments_response.json()["results"], 200

    def createNsxtSegment(self, segementName, gatewayAddress, dhcpStart, dhcpEnd, dnsServers, network, isDhcp):
        try:
            headers_ = self.grabNsxtHeaders()
            if headers_[0] is None:
                logger.error("Failed to nsxt info " + str(headers_[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to nsxt info " + str(headers_[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            uri = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
            output = self.getList(headers_[1], uri)
            if output[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get list of segments " + str(output[0]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            overlay = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtOverlay"])
            ntp_servers = str(self.jsonspec['envSpec']['infraComponents']["ntpServers"])
            trz = self.getTransportZone(headers_[2], overlay, headers_[1])
            if trz[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get transport zone id " + str(trz[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            tier_path = self.getTier1Details(headers_)
            if tier_path[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            if not self.checkObjectIsPresentAndReturnPath(output[0], segementName)[0]:
                logger.info("Creating segment " + segementName)
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
                                    "dns_servers": self.convertStringToCommaSeperated(dnsServers),
                                    "options": {
                                        "others": [
                                            {
                                                "code": 42,
                                                "values": self.convertStringToCommaSeperated(ntp_servers)
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
                    d = {
                        "responseType": "ERROR",
                        "msg": dhcp_create.text,
                        "ERROR_CODE": dhcp_create.status_code
                    }
                    logger.error(dhcp_create.text)
                    return  d, dhcp_create.status_code
                msg_text = "Created " + segementName
                logger.info(msg_text)
                logger.info("Waiting for 1 min for status == ready")
                time.sleep(60)
            else:
                msg_text = segementName + " is already created"
                logger.info(msg_text)
            d = {
                "responseType": "SUCCESS",
                "msg": msg_text,
                "ERROR_CODE": 200
            }
            return  d, 200

        except Exception as e:
            logger.error("Failed to create Nsxt segment " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create Nsxt segment " + str(e),
                "ERROR_CODE": 500
            }
            return  d, 500


    def grabNsxtHeaders(self):
        try:
            str_enc = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtUserPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode('ascii').rstrip("\n")

            ecod_bytes = (self.jsonspec['envSpec']['vcenterDetails']["nsxtUser"] + ":" + password).encode(
                "ascii")
            ecod_bytes = base64.b64encode(ecod_bytes)
            address = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtAddress"])
            ecod_string = ecod_bytes.decode("ascii")
            headers = {'Authorization': (
                    'Basic ' + ecod_string)}
            return "SUCCESS", headers, address
        except Exception as e:
            return None, str(e), None


    def createVcfDhcpServer(self):
        try:
            headers_ = self.grabNsxtHeaders()
            if headers_[0] is None:
                logger.error("Failed to nsxt info " + str(headers_[1]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to nsxt info " + str(headers_[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            uri = "https://" + headers_[2] + "/policy/api/v1/infra/dhcp-server-configs"
            output = self.getList(headers_[1], uri)
            if output[1] != 200:
                logger.error("Failed to get DHCP info on NSXT " + str(output[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get DHCP info on NSXT " + str(output[0]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            tier_path = self.getTier1Details(headers_)
            if tier_path[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            url = "https://" + headers_[2] + "/policy/api/v1" + str(tier_path[0])
            dhcp_state = requests.request("GET", url,
                                        headers=headers_[1],
                                        verify=False)
            if dhcp_state.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": dhcp_state.text,
                    "ERROR_CODE": dhcp_state.status_code
                }
                logger.error(dhcp_state.text)
                return  d, dhcp_state.status_code
            dhcp_present = False
            try:
                length = len(dhcp_state.json()["dhcp_config_paths"])
                if length > 0:
                    dhcp_present = True
            except:
                pass
            if not dhcp_present:
                if not self.checkObjectIsPresentAndReturnPath(output[0], VCF.DHCP_SERVER_NAME)[0]:
                    url = "https://" + headers_[2] + "/policy/api/v1/infra/dhcp-server-configs/" + VCF.DHCP_SERVER_NAME
                    payload = {
                        "display_name": VCF.DHCP_SERVER_NAME,
                        "resource_type": "DhcpServerConfig",
                        "lease_time": 86400,
                        "id": VCF.DHCP_SERVER_NAME
                    }
                    headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
                    payload_modified = json.dumps(payload, indent=4)
                    dhcp_create = requests.request("PUT", url,
                                                headers=headers_[1],
                                                data=payload_modified,
                                                verify=False)
                    if dhcp_create.status_code != 200:
                        d = {
                            "responseType": "ERROR",
                            "msg": dhcp_create.text,
                            "ERROR_CODE": dhcp_create.status_code
                        }
                        logger.error(dhcp_create.text)
                        return  d, dhcp_create.status_code
                    msg_text = "Created DHCP server " + VCF.DHCP_SERVER_NAME
                    logger.info(msg_text)
                else:
                    msg_text = VCF.DHCP_SERVER_NAME + " dhcp server is already created"
                    logger.info(msg_text)
            else:
                msg_text = "Dhcp server is already present in tier1"
            d = {
                "responseType": "SUCCESS",
                "msg": msg_text,
                "ERROR_CODE": 200
            }
            return  d, 200
        except Exception as e:
            logger.error("Failed to create Dhcp server " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create Dhcp server " + str(e),
                "ERROR_CODE": 500
            }
            return  d, 500


    def getPolicy(self, headers, policyName):
        url = "https://" + headers[2] + "/policy/api/v1/infra/domains/default/gateway-policies"
        response = requests.request(
            "GET", url, headers=headers[1], verify=False)
        if response.status_code != 200:
            return None, response.text
        try:
            for pol in response.json()["results"]:
                if pol["display_name"] == policyName:
                    return pol["display_name"], "FOUND"
            return None, "NOT_FOUND"
        except Exception:
            return None, "NOT_FOUND"

    def getTier1Details(self, headers_):
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/tier-1s"
        response = requests.request(
            "GET", uri, headers=headers_[1], verify=False)
        if response.status_code != 200:
            return None, response.status_code
        teir1name = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtTier1RouterDisplayName"])
        for tr in response.json()["results"]:
            if str(tr["display_name"]).lower() == teir1name.lower():
                return tr["path"], "FOUND"
        return None, "NOT_FOUND"



    def getNetworkIp(self, gatewayAddress):
        ipNet = self.seperateNetmaskAndIp(gatewayAddress)
        ss = ipNet[0].split(".")
        return ss[0] + "." + ss[1] + "." + ss[2] + ".0" + "/" + ipNet[1]

    def getDomainName(self, headers, domainName):
        url = "https://" + headers[2] + "/policy/api/v1/infra/domains/"
        response = requests.request(
            "GET", url, headers=headers[1], verify=False)
        if response.status_code != 200:
            return None, response.text
        for domain in response.json()["results"]:
            if str(domain["display_name"]) == domainName:
                return domain["display_name"], "FOUND"
        return None, "NOT_FOUND"


    def seperateNetmaskAndIp(self, cidr):
        return str(cidr).split("/")


    def get_ip_address(self, ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15].encode('utf-8'))
        )[20:24])


    def createGroup(self, groupName, segmentName, isIp, ipaddresses):
        try:
            headers_ = self.grabNsxtHeaders()
            if headers_[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to nsxt info " + str(headers_[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            domainName = self.getDomainName(headers_, "default")
            if domainName[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get domain name " + str(domainName[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            uri = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups"
            output = self.getList(headers_[1], uri)
            if output[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get list of domain " + str(output[0]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            if segmentName is not None:
                uri_ = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
                seg_output = self.getList(headers_[1], uri_)
                if seg_output[1] != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get list of segments " + str(seg_output[0]),
                        "ERROR_CODE": 500
                    }
                    return  d, 500
                seg_obj = self.checkObjectIsPresentAndReturnPath(seg_output[0], segmentName)
                if not seg_obj[0]:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to find the segment " + segmentName,
                        "ERROR_CODE": 500
                    }
                    return  d, 500
            url = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups/" + groupName
            headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
            isPresent = False
            lis_ip = []
            try:
                get_group = requests.request("GET", url,
                                            headers=headers_[1],
                                            verify=False)
                results = get_group.json()
                revision_id = results["_revision"]
                for expression in results["expression"]:
                    if isIp == "true":
                        for _ip in expression["ip_addresses"]:
                            lis_ip.append(_ip)
                            if str(_ip) == str(ipaddresses):
                                isPresent = True
                                break
                    else:
                        for path in expression["paths"]:
                            lis_ip.append(path)
                            if str(seg_obj[1]) == str(path):
                                isPresent = True
                                break
                    if isPresent:
                        break
            except:
                isPresent = False
            if ipaddresses is not None:
                for ip_ in self.convertStringToCommaSeperated(ipaddresses):
                    lis_ip.append(ip_)
            else:
                lis_ip.append(seg_obj[1])
            obj = self.checkObjectIsPresentAndReturnPath(output[0], groupName)
            if not obj[0] or not isPresent:
                logger.info("Creating group " + groupName)
                url = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups/" + groupName
                if isIp == "true":
                    if not isPresent and obj[0]:
                        payload = {
                            "display_name": groupName,
                            "expression": [{
                                "resource_type": "IPAddressExpression",
                                "ip_addresses": lis_ip
                            }],
                            "resource_type": "Group",
                            "_revision": int(revision_id)
                        }
                    else:
                        payload = {
                            "display_name": groupName,
                            "expression": [
                                {
                                    "resource_type": "IPAddressExpression",
                                    "ip_addresses": self.convertStringToCommaSeperated(ipaddresses)
                                }
                            ],
                            "id": groupName
                        }
                elif isIp == "vc":
                    payload = {
                        "display_name": groupName,
                        "expression": [
                            {
                                "value": ipaddresses,
                                "member_type": "VirtualMachine",
                                "key": "OSName",
                                "operator": "EQUALS",
                                "resource_type": "Condition"
                            }
                        ],
                        "id": groupName
                    }
                else:
                    if not isPresent and obj[0]:
                        payload = {
                            "display_name": groupName,
                            "expression": [{
                                "resource_type": "PathExpression",
                                "paths": lis_ip
                            }],
                            "resource_type": "Group",
                            "_revision": int(revision_id)
                        }
                    else:
                        payload = {
                            "display_name": groupName,
                            "expression": [
                                {
                                    "resource_type": "PathExpression",
                                    "paths": [
                                        seg_obj[1]
                                    ]
                                }
                            ],
                            "id": groupName
                        }
                headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
                payload_modified = json.dumps(payload, indent=4)
                dhcp_create = requests.request("PUT", url,
                                            headers=headers_[1],
                                            data=payload_modified,
                                            verify=False)
                if dhcp_create.status_code != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": dhcp_create.text,
                        "ERROR_CODE": dhcp_create.status_code
                    }
                    logger.error(dhcp_create.text)
                    return  d, dhcp_create.status_code
                msg_text = "Created group " + groupName
                path = dhcp_create.json()["path"]
            else:
                path = obj[1]
                msg_text = groupName + " group is already created."
            logger.info(msg_text)
            d = {
                "responseType": "SUCCESS",
                "msg": msg_text,
                "path": path,
                "ERROR_CODE": 200
            }
            return  d, 200
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create group " + groupName + " " + str(e),
                "ERROR_CODE": 500
            }
            return  d, 500


    def isServiceCreated(self, header, serviceName):
        url = "https://" + header[2] + "/policy/api/v1/infra/services"
        response = requests.request(
            "GET", url, headers=header[1], verify=False)
        if response.status_code != 200:
            return None, response.text
        for service in response.json()["results"]:
            if service["display_name"] == serviceName:
                return service["display_name"], "FOUND"
        return None, "NOT_FOUND"


    def createVipService(self, serviceName, port):
        headers_ = self.grabNsxtHeaders()
        if headers_[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to nsxt info " + str(headers_[1]),
                "ERROR_CODE": 500
            }
            return  d, 500
        service = self.isServiceCreated(headers_, serviceName)
        if service[0] is None:
            if service[1] != "NOT_FOUND":
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get service info " + str(service[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            else:
                url = "https://" + headers_[2] + "/policy/api/v1/infra/services/" + serviceName
                headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
                payload = {
                    "service_entries": [
                        {
                            "display_name": serviceName,
                            "resource_type": "L4PortSetServiceEntry",
                            "l4_protocol": "TCP",
                            "destination_ports": self.convertStringToCommaSeperated(port)
                        }
                    ],
                    "display_name": serviceName,
                    "id": serviceName
                }
                payload_modified = json.dumps(payload, indent=4)
                response = requests.request(
                    "PUT", url, headers=headers_[1], data=payload_modified, verify=False)
                if response.status_code != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to create service " + str(response.text),
                        "ERROR_CODE": 500
                    }
                    return  d, 500
            message = "Service created successfully"
        else:
            message = "Service is already created " + service[0]
        logger.info(message)
        d = {
            "responseType": "ERROR",
            "msg": message,
            "ERROR_CODE": 200
        }
        return  d, 200

    def getListOfFirewallRule(self, headers, policyName):
        url = "https://" + headers[2] + "/policy/api/v1/infra/domains/default/gateway-policies/" + policyName + "/rules"
        response = requests.request(
            "GET", url, headers=headers[1], verify=False)
        if response.status_code != 200:
            return None, response.text
        return response.json()["results"], "FOUND"


    def createFirewallRule(self, policyName, ruleName, rulePayLoad):
        headers_ = self.grabNsxtHeaders()
        if headers_[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to nsxt info " + str(headers_[1]),
                "ERROR_CODE": 500
            }
            return  d, 500
        policy = self.getPolicy(headers_, policyName)
        if policy[0] is None:
            if policy[1] != "NOT_FOUND":
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get policy " + str(policy[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            else:
                logger.info("Creating policy " + policyName)
                tier_path = self.getTier1Details(headers_)
                if tier_path[0] is None:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                        "ERROR_CODE": 500
                    }
                    return  d, 500
                url = "https://" + headers_[2] + "/policy/api/v1/infra"
                payload = {
                    "resource_type": "Infra",
                    "children": [
                        {
                            "resource_type": "ChildResourceReference",
                            "id": "default",
                            "target_type": "Domain",
                            "children": [
                                {
                                    "resource_type": "ChildGatewayPolicy",
                                    "marked_for_delete": False,
                                    "GatewayPolicy": {
                                        "resource_type": "GatewayPolicy",
                                        "display_name": policyName,
                                        "id": policyName,
                                        "marked_for_delete": False,
                                        "tcp_strict": True,
                                        "stateful": True,
                                        "locked": False,
                                        "category": "LocalGatewayRules",
                                        "sequence_number": 10,
                                        "children": [
                                            {
                                                "resource_type": "ChildRule",
                                                "marked_for_delete": False,
                                                "Rule": {
                                                    "display_name": "default_rule",
                                                    "id": "default_rule",
                                                    "resource_type": "Rule",
                                                    "marked_for_delete": False,
                                                    "source_groups": [
                                                        "ANY"
                                                    ],
                                                    "sequence_number": 10,
                                                    "destination_groups": [
                                                        "ANY"
                                                    ],
                                                    "services": [
                                                        "ANY"
                                                    ],
                                                    "profiles": [
                                                        "ANY"
                                                    ],
                                                    "scope": [
                                                        tier_path[0]
                                                    ],
                                                    "action": "ALLOW",
                                                    "direction": "IN_OUT",
                                                    "logged": False,
                                                    "disabled": False,
                                                    "notes": "",
                                                    "tag": "",
                                                    "ip_protocol": "IPV4_IPV6"
                                                }
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
                payload_modified = json.dumps(payload, indent=4)
                headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
                response = requests.request(
                    "PATCH", url, headers=headers_[1], data=payload_modified, verify=False)
                if response.status_code != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to create policy " + str(response.text),
                        "ERROR_CODE": 500
                    }
                    return  d, 500
        else:
            logger.info(policyName + " policy is already created")
        list_fw = self.getListOfFirewallRule(headers_, policyName)
        if list_fw[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get list of firewalls " + str(list_fw[1]),
                "ERROR_CODE": 500
            }
            return  d, 500
        if not self.checkObjectIsPresentAndReturnPath(list_fw[0], ruleName)[0]:
            logger.info("Creating firewall rule " + ruleName)
            rule_payload_modified = json.dumps(rulePayLoad, indent=4)
            url = "https://" + headers_[
                2] + "/policy/api/v1/infra/domains/default/gateway-policies/" + policyName + "/rules/" + ruleName
            headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
            response = requests.request(
                "PUT", url, headers=headers_[1], data=rule_payload_modified, verify=False)
            if response.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create rule " + str(response.text),
                    "ERROR_CODE": 500
                }
                return  d, 500
            msg_text = ruleName + " rule created successfully"
        else:
            msg_text = ruleName + " rule is already created"
        logger.info(msg_text)
        d = {
            "responseType": "SUCCESS",
            "msg": msg_text,
            "ERROR_CODE": 200
        }
        return  d, 200

    def is_ipv4(self, string):
        try:
            ipaddress.IPv4Network(string)
            return True
        except ValueError:
            return False


    def getIpFromHost(self, vcenter):
        try:
            return socket.gethostbyname(vcenter)
        except Exception as e:
            return None


    def getESXIips(self):
        try:
            str_enc = str(self.jsonspec['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode('ascii').rstrip("\n")

            ecod_bytes = (self.jsonspec['envSpec']['vcenterDetails'][
                            "vcenterSsoUser"] + ":" + password).encode(
                "ascii")
            ecod_bytes = base64.b64encode(ecod_bytes)
            address = str(self.jsonspec['envSpec']['vcenterDetails']["vcenterAddress"])
            ecod_string = ecod_bytes.decode("ascii")
            uri = "https://" + address + "/api/session"
            headers = {'Authorization': (
                    'Basic ' + ecod_string)}
            response = requests.request(
                "POST", uri, headers=headers, verify=False)
            if response.status_code != 201:
                return None, response.status_code
            url = "https://" + address + "/api/vcenter/host"
            header = {'vmware-api-session-id': response.json()}
            response = requests.request(
                "GET", url, headers=header, verify=False)
            if response.status_code != 200:
                return None, response.text
            ips = ""
            for esx in response.json():
                if not self.is_ipv4(esx):
                    ips += self.getIpFromHost(esx["name"]) + ","
                else:
                    ips += esx["name"] + ","
            if not ips:
                return None, "EMPTY"
            return ips.strip(","), "SUCCESS"
        except Exception as e:
            return None, str(e)

    def updateDefaultRule(self, policyName):
        try:
            headers_ = self.grabNsxtHeaders()
            if headers_[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to nsxt info " + str(headers_[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            list_fw = self.getListOfFirewallRule(headers_, policyName)
            if list_fw[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get list of firewalls " + str(list_fw[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            sequence = None
            for rule in list_fw[0]:
                if rule["display_name"] == "default_rule":
                    sequence = rule["sequence_number"]
                    break
            if sequence is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get sequnece number of default rule ",
                    "ERROR_CODE": 500
                }
                return  d, 500
            tier_path = self.getTier1Details(headers_)
            if tier_path[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                    "ERROR_CODE": 500
                }
                return  d, 500
            url = "https://" + headers_[
                2] + "/policy/api/v1/infra/domains/default/gateway-policies/" + policyName + "/rules/default_rule"
            payload = {
                "sequence_number": sequence,
                "source_groups": [
                    "ANY"
                ],
                "services": [
                    "ANY"
                ],
                "logged": False,
                "destination_groups": [
                    "ANY"
                ],
                "scope": [
                    tier_path[0]
                ],
                "action": "ALLOW"
            }
            payload_modified = json.dumps(payload, indent=4)
            headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
            response = requests.request(
                "PATCH", url, headers=headers_[1], data=payload_modified, verify=False)
            if response.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create policy " + str(response.text),
                    "ERROR_CODE": 500
                }
                return  d, 500
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully updated default rule",
                "ERROR_CODE": 200
            }
            return  d, 200
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update default rule " + str(e),
                "ERROR_CODE": 500
            }
            return  d, 500

