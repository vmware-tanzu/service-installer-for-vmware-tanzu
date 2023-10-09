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
from constants.nsxt_constants import  VCF, NSXtCloud
from constants.constants import Cloud, ControllerLocation
from util.replace_value import generateVsphereConfiguredSubnets

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

    def getCloudConnectUser(self, ip, headers):
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

    def fetchTier1GatewayId(self,ip, headers, nsxt_credential):
        try:
            url = "https://" + ip + "/api/nsxt/tier1s"
            teir1name = self.jsonspec['envSpec']['vcenterDetails']["nsxtTier1RouterDisplayName"]
            address = self.jsonspec['envSpec']['vcenterDetails']["nsxtAddress"]
            body = {
                "host": address,
                "credentials_uuid": nsxt_credential
            }
            json_object = json.dumps(body, indent=4)
            response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            for library in response_csrf.json()["resource"]["nsxt_tier1routers"]:
                if library["name"] == teir1name:
                    return "Success", library["id"]
            return None, "TIER1_GATEWAY_ID_NOT_FOUND"
        except Exception as e:
            return None, str(e)


    def createCloudConnectUser(self, ip, headers):
        url = "https://" + ip + "/api/cloudconnectoruser"
        try:
            vcenter_username = self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(self.jsonspec['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode('ascii').rstrip("\n")

            str_enc_nsx = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtUserPasswordBase64"])
            base64_bytes_nsx = str_enc_nsx.encode('ascii')
            enc_bytes_nsx = base64.b64decode(base64_bytes_nsx)
            password_nsx = enc_bytes_nsx.decode('ascii').rstrip("\n")
            nsx_user = self.jsonspec['envSpec']['vcenterDetails']["nsxtUser"]
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
            cloud_user, status = self.getCloudConnectUser(ip, headers)
            if str(cloud_user) == "EXCEPTION" or str(cloud_user) == "API_FAILURE":
                return None, status
            if str(status) == "NO_CRED_FOUND" or str(status) == "EMPTY":
                logger.info("Creating Nsx and vcenter credential")
                list_body.append(body_vcenter)
                list_body.append(body_nsx)
            if str(cloud_user) == "ONE_CRED_FOUND":
                if str(status[0]) == "VCENTER_CRED_FOUND":
                    logger.info("Creating Nsx credentials")
                    status_["vcenterUUId"] = status[1]["uuid"]
                    list_body.append(body_nsx)
                elif str(status[0]) == "NSX_CRED_FOUND":
                    logger.info("Creating Vcenter credentials")
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


    def fetchContentLibrary(self, ip, headers, vcenter_credential):
        try:
            vc_Content_Library_name = self.jsonspec['envSpec']['vcenterDetails']["contentLibraryName"]
            if not vc_Content_Library_name:
                vc_Content_Library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
            vCenter = self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
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


    def fetchTier1GatewayId(self, ip, headers, nsxt_credential):
        try:
            url = "https://" + ip + "/api/nsxt/tier1s"
            teir1name = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtTier1RouterDisplayName"])
            address = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtAddress"])
            body = {
                "host": address,
                "credentials_uuid": nsxt_credential
            }
            json_object = json.dumps(body, indent=4)
            response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            for library in response_csrf.json()["resource"]["nsxt_tier1routers"]:
                if library["name"] == teir1name:
                    return "Success", library["id"]
            return None, "TIER1_GATEWAY_ID_NOT_FOUND"
        except Exception as e:
            return None, str(e)


    def fetchTransportZoneId(self, ip, headers, nsxt_credential):
        try:
            url = "https://" + ip + "/api/nsxt/transportzones"
            overlay = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtOverlay"])
            address = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtAddress"])
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


    def fetchVcenterId(self, ip, headers, nsxt_credential, tz_id):
        try:
            url = "https://" + ip + "/api/nsxt/vcenters"
            address = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtAddress"])
            address_vc = str(self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress'])
            body = {
                "host": address,
                "credentials_uuid": nsxt_credential,
                "transport_zone_id": tz_id
            }
            json_object = json.dumps(body, indent=4)
            import socket
            try:
                vc_ip = socket.gethostbyname(address_vc)
            except Exception as e:
                return None, str(e)
            response_csrf = requests.request("POST", url, headers=headers, data=json_object, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            for library in response_csrf.json()["resource"]["vcenter_ips"]:
                if library["vcenter_ip"]["addr"] == vc_ip:
                    return "Success", library["vcenter_ip"]["addr"]
            return None, "VC_NOT_FOUND"
        except Exception as e:
            return None, str(e)


    def fetchSegmentsId(self, ip, headers, nsxt_credential, tz_id, tier1_id):
        try:
            url = "https://" + ip + "/api/nsxt/segments"
            address = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtAddress"])
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
            avi_mgmt = self.jsonspec['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']
            tkg_cluster_vip_name = self.jsonspec['tkgComponentSpec']['tkgClusterVipNetwork'][
                'tkgClusterVipNetworkName']
            for library in response_csrf.json()["resource"]["nsxt_segments"]:
                if library["name"] == avi_mgmt:
                    segId["avi_mgmt"] = library["id"]
                elif library["name"] == tkg_cluster_vip_name:
                    segId["cluster_vip"] = library["id"]
                if len(segId) == 2:
                    break
            if len(segId) < 2:
                return None, "SEGMENT_NOT_FOUND " + str(segId)
            return "Success", segId
        except Exception as e:
            return None, str(e)


    def createNsxtCloud(self, ip, csrf2, aviVersion):
        try:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Cookie": csrf2[1],
                "referer": "https://" + ip + "/login",
                "x-avi-version": aviVersion,
                "x-csrftoken": csrf2[0]
            }
            cloud_connect_user, cred = self.createCloudConnectUser(ip, headers)
            if cloud_connect_user is None:
                return None, cred
            nsxt_cred = cred["nsxUUid"]
            zone, status_zone = self.fetchTransportZoneId(ip, headers, nsxt_cred)
            if zone is None:
                return None, status_zone
            tier1_id, status_tier1 = self.fetchTier1GatewayId(ip, headers, nsxt_cred)
            if tier1_id is None:
                return None, status_tier1
            tz_id, status_tz = self.fetchTransportZoneId(ip, headers, nsxt_cred)
            if tz_id is None:
                return None, status_tz
            seg_id, status_seg = self.fetchSegmentsId(ip, headers, nsxt_cred, status_tz, status_tier1)
            if seg_id is None:
                return None, status_seg
            status, value = self.getCloudConnectUser(ip, headers)
            address = str(self.jsonspec['envSpec']['vcenterDetails']["nsxtAddress"])
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
                                        "segment_id": status_seg["cluster_vip"],
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
                "obj_name_prefix": Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt"),
                "name": Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt"),
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


    def configureVcenterInNSXTCloud(self, ip, csrf2, cloud_url, aviVersion):
        VC_NAME = "SIVT_VC"
        url = "https://" + ip + "/api/vcenterserver"
        try:
            with open("./newCloudInfo.json", 'r') as file2:
                new_cloud_json = json.load(file2)
            cloud = Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt")
            uuid = None
            try:
                uuid = new_cloud_json["uuid"]
            except:
                for re in new_cloud_json["results"]:
                    if re["name"] == cloud:
                        uuid = re["uuid"]
            if uuid is None:
                logger.error(cloud + " cloud not found")
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
                cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
                for cluster in response_csrf.json()["resource"]["nsxt_clusters"]:
                    if cluster["name"] == cluster_name:
                        vc_info["cluster"] = cluster["vc_mobj_id"]
                        break
                return "SUCCESS", vc_info
            else:
                cloud_connect_user, cred = self.createCloudConnectUser(ip, headers)
                if cloud_connect_user is None:
                    return None, cred
                vcenter_credential = cred["vcenterUUId"]
                nsxt_credential = cred["nsxUUid"]
                vc_Content_Library_name = self.jsonspec['envSpec']['vcenterDetails']["contentLibraryName"]
                if not vc_Content_Library_name:
                    vc_Content_Library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
                library, status_lib = self.fetchContentLibrary(ip, headers, vcenter_credential)
                if library is None:
                    return None, status_lib
                tz_id, status_tz = self.fetchTransportZoneId(ip, headers, nsxt_credential)
                if tz_id is None:
                    return None, status_tz
                vc_id, status_vc = self.fetchVcenterId(ip, headers, nsxt_credential, status_tz)
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
                cluster_name = self.jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
                for cluster in response_csrf.json()["resource"]["nsxt_clusters"]:
                    if cluster["name"] == cluster_name:
                        vc_info["cluster"] = cluster["vc_mobj_id"]
                        break
                return "SUCCESS", vc_info
        except Exception as e:
            return None, str(e)


    def createIpam_nsxtCloud(self, ip, csrf2, managementNetworkUrl, vipNetwork, ipam_name, aviVersion):
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
                        },
                        {
                            "nw_ref": vipNetwork
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
            logger.error(str(e))
            return None, "Exception occurred while creation ipam profile for NSXT-T Cloud"


    def createDns_nsxtCloud(self, ip, csrf2, dns_domain, dns_profile_name, aviVersion):
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
            logger.error(str(e))
            return None, "Exception occurred while creation DNS profile for NSXT-T Cloud "


    def associate_ipam_nsxtCloud(self, ip, csrf2, aviVersion, nsxtCloud_uuid, ipamUrl, dnsUrl):
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
            logger.error(str(e))
            return None, "Exception occurred during association of DNS and IPAM profile with NSX-T Cloud"

    def createNsxtSECloud(self, ip, csrf2, newCloudUrl, seGroupName, nsx_cloud_info, aviVersion, se_prefix_name):
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
            "se_name_prefix": se_prefix_name,
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

    def getNsxTNetworkDetails(self, ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion):
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
            logger.info("Ip pools are not configured, configuring it")
        return "SUCCESS", 200, details