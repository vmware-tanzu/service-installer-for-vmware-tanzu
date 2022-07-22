import sys
import requests
import logging
from flask import Blueprint, current_app, jsonify, request
from jinja2 import Template

sys.path.append(".../")
from common.operation.constants import Paths
from common.operation.vcenter_operations import createResourcePool, create_folder, checkforIpAddress, getSi, \
    getMacAddresses
from common.operation.constants import ResourcePoolAndFolderName, Cloud, Versions, AkoType, CIDR, PLAN, TmcUser, \
    CertName, \
    Vcenter, Env, Avi_Version, SegmentsName, GroupNameCgw, FirewallRuleCgw, Policy_Name, ServiceName, VCF
from common.common_utilities import form_avi_ha_cluster, isAviHaEnabled, isEnvTkgs_wcp, createVipService, preChecks, \
    grabNsxtHeaders, \
    createResourceFolderAndWait, \
    deployAndConfigureAvi, \
    get_avi_version, \
    envCheck, manage_avi_certificates, createNsxtSegment, seperateNetmaskAndIp, createGroup, createFirewallRule, \
    getTier1Details, createVcfDhcpServer, getNetworkIp, get_ip_address, is_ipv4, getESXIips, updateDefaultRule, \
    getIpFromHost, downloadAviController, obtain_avi_version
from common.operation.constants import ControllerLocation
from common.util.file_helper import FileHelper
from common.lib.govc_client import GovcClient
from common.util.local_cmd_helper import LocalCmdHelper
from requests.packages.urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(__name__)
vcenter_avi_config = Blueprint("vcenter_avi_config", __name__, static_folder="aviConfig")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@vcenter_avi_config.route("/api/tanzu/vsphere/alb", methods=['POST'])
def aviConfig_vsphere():
    avi_dep = aviDeployment_vsphere()
    if avi_dep[1] != 200:
        current_app.logger.error(str(avi_dep[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy avi " + str(avi_dep[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    avi_cert = aviCertManagement_vsphere()
    if avi_cert[1] != 200:
        current_app.logger.error(str(avi_cert[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to manage  avi cert " + str(avi_cert[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Avi configured Successfully",
        "ERROR_CODE": 200
    }
    current_app.logger.info("Avi configured Successfully ")
    return jsonify(d), 200


@vcenter_avi_config.route("/api/tanzu/vsphere/alb/vcf_pre_config", methods=['POST'])
def avi_vcf_pre_config():
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": pre[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    if env == Env.VCF:
        try:
            gatewayAddress = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceGatewayCidr']
            dhcpStart = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceDhcpStartRange']
            dhcpEnd = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceDhcpEndRange']
            dnsServers = request.get_json(force=True)['envSpec']['infraComponents']['dnsServersIp']
            network = getNetworkIp(gatewayAddress)
            shared_network_name = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceNetworkName']
            shared_segment = createNsxtSegment(shared_network_name, gatewayAddress,
                                               dhcpStart,
                                               dhcpEnd, dnsServers, network, True)
            if shared_segment[1] != 200:
                current_app.logger.error("Failed to create shared segments" + str(shared_segment[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create shared segments" + str(shared_segment[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            dhcp = createVcfDhcpServer()
            if dhcp[1] != 200:
                current_app.logger.error("Failed to create dhcp server " + str(dhcp[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create dhcp server " + str(dhcp[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            cluster_wip = request.get_json(force=True)['tkgComponentSpec']['tkgClusterVipNetwork'][
                'tkgClusterVipNetworkName']
            gatewayAddress = request.get_json(force=True)['tkgComponentSpec']['tkgClusterVipNetwork'][
                'tkgClusterVipNetworkGatewayCidr']
            network = getNetworkIp(gatewayAddress)
            segment = createNsxtSegment(cluster_wip,
                                        gatewayAddress,
                                        dhcpStart,
                                        dhcpEnd, dnsServers, network, False)
            if segment[1] != 200:
                current_app.logger.error(
                    "Failed to create  segments " + cluster_wip + " " + str(segment[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create shared segment " + cluster_wip + " " + str(segment[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            mgmt_data = request.get_json(force=True)['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName']
            gatewayAddress = request.get_json(force=True)['tkgMgmtDataNetwork']['tkgMgmtDataNetworkGatewayCidr']
            network = getNetworkIp(gatewayAddress)
            segment = createNsxtSegment(mgmt_data,
                                        gatewayAddress,
                                        dhcpStart,
                                        dhcpEnd, dnsServers, network, False)
            if segment[1] != 200:
                current_app.logger.error("Failed to create  segments " + mgmt_data + " " + str(segment[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create shared segment " + mgmt_data + " " + str(segment[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            avi_mgmt = request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork'][
                'aviMgmtNetworkName']
            avi_gatewayAddress = request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork'][
                'aviMgmtNetworkGatewayCidr']
            segment = createNsxtSegment(avi_mgmt,
                                        avi_gatewayAddress,
                                        dhcpStart,
                                        dhcpEnd, dnsServers, network, False)
            if segment[1] != 200:
                current_app.logger.error("Failed to create  segments " + avi_mgmt + " " + str(segment[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create shared segment " + avi_mgmt + " " + str(segment[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            ip = get_ip_address("eth0")
            if ip is None:
                current_app.logger.error("Failed to get arcas vm ip")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get arcas vm ip",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            arcas_group = createGroup(VCF.ARCAS_GROUP, None,
                                      "true", ip)
            if arcas_group[1] != 200:
                current_app.logger.error(
                    "Failed to create  group " + VCF.ARCAS_GROUP + " " + str(
                        arcas_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group " + VCF.ARCAS_GROUP + " " + str(
                        arcas_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            arcas_svc = createVipService(ServiceName.ARCAS_SVC, "8888")
            if arcas_svc[1] != 200:
                current_app.logger.error(
                    "Failed to create service " + ServiceName.ARCAS_SVC + " " + str(
                        arcas_svc[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create service " + ServiceName.ARCAS_SVC + " " + str(
                        arcas_svc[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            arcas_svc = createVipService(ServiceName.ARCAS_BACKEND_SVC, "5000")
            if arcas_svc[1] != 200:
                current_app.logger.error(
                    "Failed to create service " + ServiceName.ARCAS_BACKEND_SVC + " " + str(
                        arcas_svc[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create service " + ServiceName.ARCAS_BACKEND_SVC + " " + str(
                        arcas_svc[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            avi_mgmt_group = createGroup(GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW, avi_mgmt,
                                         False, None)
            if avi_mgmt_group[1] != 200:
                current_app.logger.error(
                    "Failed to create  group " + GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW + " " + str(
                        avi_mgmt_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW + " " + str(
                        avi_mgmt_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            cluster_vip_group = createGroup(GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW, cluster_wip,
                                            False, None)
            if cluster_vip_group[1] != 200:
                current_app.logger.error(
                    "Failed to create  group " + GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW + " " + str(
                        cluster_vip_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create  group " + GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW + " " + str(
                        cluster_vip_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            shared_service_group = createGroup(GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW,
                                               shared_network_name, False, None)
            if shared_service_group[1] != 200:
                current_app.logger.error(
                    "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW + " " + str(
                        shared_service_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create  group " + GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW + " " + str(
                        shared_service_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            mgmt = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtNetworkName']
            mgmt_group = createGroup(GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW, mgmt, False, None)
            if mgmt_group[1] != 200:
                current_app.logger.error(
                    "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW + " " + str(
                        mgmt_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW + " " + str(
                        mgmt_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            dns = request.get_json(force=True)['envSpec']['infraComponents']['dnsServersIp']
            dns_group = createGroup(GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group,
                                    None, "true", dns)
            if dns_group[1] != 200:
                current_app.logger.error(
                    "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group + " " + str(
                        dns_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group + " " + str(
                        dns_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            ntp = request.get_json(force=True)['envSpec']['infraComponents']['ntpServers']
            ntp_group = createGroup(GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group,
                                    None, "true", ntp)
            if ntp_group[1] != 200:
                current_app.logger.error(
                    "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group + " " + str(
                        ntp_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group + " " + str(
                        ntp_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
            if not is_ipv4(vCenter):
                vCenter = getIpFromHost(vCenter)
                if vCenter is None:
                    current_app.logger.error('Failed to fetch VC ip')
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to fetch VC ip",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            vc_group = createGroup(GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group,
                                   None, "true", vCenter)
            if vc_group[1] != 200:
                current_app.logger.error(
                    "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group + " " + str(
                        vc_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group " + GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group + " " + str(
                        vc_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            ips = getESXIips()
            if ips[0] is None:
                current_app.logger.error(
                    "Failed to create get esxi ip " + ips[1])
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create get esxi ip " + ips[1],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            esx_group = createGroup(VCF.ESXI_GROUP,
                                    None, "true", ips[0])
            if esx_group[1] != 200:
                current_app.logger.error(
                    "Failed to create group " + VCF.ESXI_GROUP + " " + str(
                        esx_group[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create group " + VCF.ESXI_GROUP + " " + str(
                        esx_group[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            headers_ = grabNsxtHeaders()
            if headers_[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to nsxt info " + str(headers_[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            teir1 = getTier1Details(headers_)
            if teir1[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to tier1 details" + str(headers_[1]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_UI,
                       "logged": False,
                       "source_groups": ["ANY"],
                       "destination_groups": [
                           arcas_group[0].json["path"]],
                       "services": ["/infra/services/SSH", "/infra/services/" + ServiceName.ARCAS_SVC],
                       "scope": [teir1[0]]
                       }
            arcas_fw = createFirewallRule(Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_UI, payload)
            if arcas_fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_UI + " " + str(
                        arcas_fw[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_UI + " " + str(
                        arcas_fw[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_BACKEND,
                       "logged": False,
                       "source_groups": ["ANY"],
                       "destination_groups": [
                           arcas_group[0].json["path"]],
                       "services": ["/infra/services/" + ServiceName.ARCAS_BACKEND_SVC],
                       "scope": [teir1[0]]
                       }
            arcas_fw = createFirewallRule(Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_BACKEND,
                                          payload)
            if arcas_fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_ARCAS_BACKEND + " " + str(
                        arcas_fw[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + GroupNameCgw.DISPLAY_NAME_VCF_ARCAS_BACKEND + " " + str(
                        arcas_fw[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_DNS,
                       "logged": False,
                       "source_groups": [avi_mgmt_group[0].json["path"],
                                         mgmt_group[0].json["path"],
                                         shared_service_group[0].json["path"]],
                       "destination_groups": [
                           dns_group[0].json["path"]],
                       "services": ["/infra/services/DNS", "/infra/services/DNS-UDP"],
                       "scope": [teir1[0]]
                       }
            fw = createFirewallRule(Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_DNS, payload)
            if fw[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_DNS + " " + str(
                        fw[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + GroupNameCgw.DISPLAY_NAME_VCF_TKG_and_AVI_DNS + " " + str(
                        fw[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_NTP,
                       "logged": False,
                       "source_groups": [avi_mgmt_group[0].json["path"],
                                         mgmt_group[0].json["path"],
                                         shared_service_group[0].json["path"]],
                       "destination_groups": [
                           ntp_group[0].json["path"]],
                       "services": ["/infra/services/NTP"],
                       "scope": [teir1[0]]
                       }
            fw_vip = createFirewallRule(Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_NTP,
                                        payload)
            if fw_vip[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_NTP + " " + str(
                        fw_vip[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_NTP + " " + str(
                        fw_vip[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_vCenter,
                       "logged": False,
                       "source_groups": [avi_mgmt_group[0].json["path"],
                                         mgmt_group[0].json["path"],
                                         shared_service_group[0].json["path"]],
                       "destination_groups": [
                           vc_group[0].json["path"]],
                       "services": ["/infra/services/HTTPS"],
                       "scope": [teir1[0]]
                       }
            fw_vip = createFirewallRule(Policy_Name.POLICY_NAME,
                                        FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_vCenter, payload)
            if fw_vip[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_vCenter + " " + str(
                        fw_vip[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_vCenter + " " + str(
                        fw_vip[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": VCF.ESXI_FW,
                       "logged": False,
                       "source_groups": [mgmt_group[0].json["path"],
                                         avi_mgmt_group[0].json["path"]],
                       "destination_groups": [
                           esx_group[0].json["path"]],
                       "services": ["/infra/services/HTTPS"],
                       "scope": [teir1[0]]
                       }
            fw_esx = createFirewallRule(Policy_Name.POLICY_NAME,
                                        VCF.ESXI_FW, payload)
            if fw_esx[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + VCF.ESXI_FW + " " + str(
                        fw_esx[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + VCF.ESXI_FW + " " + str(
                        fw_esx[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_Internet,
                       "logged": False,
                       "source_groups": [mgmt_group[0].json["path"],
                                         shared_service_group[0].json["path"]],
                       "destination_groups": ["ANY"],
                       "services": ["ANY"],
                       "scope": [teir1[0]]
                       }
            fw_vip = createFirewallRule(Policy_Name.POLICY_NAME,
                                        FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_Internet, payload)
            if fw_vip[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_Internet + " " + str(
                        fw_vip[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_AVI_to_Internet + " " + str(
                        fw_vip[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_TKGtoAVIMgmt,
                       "logged": False,
                       "source_groups": [
                           mgmt_group[0].json["path"],
                           shared_service_group[0].json["path"]],
                       "destination_groups": [
                           avi_mgmt_group[0].json["path"]],
                       "services": ["/infra/services/HTTPS","/infra/services/ICMP-ALL"],
                       "scope": [teir1[0]]
                       }
            fw_vip = createFirewallRule(Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_TKGtoAVIMgmt,
                                        payload)
            if fw_vip[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_TKGtoAVIMgmt + " " + str(
                        fw_vip[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_and_TKGtoAVIMgmt + " " + str(
                        fw_vip[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            vip = createVipService(ServiceName.KUBE_VIP_VCF_SERVICE, "6443")
            if vip[1] != 200:
                current_app.logger.error(
                    "Failed to create service " + ServiceName.KUBE_VIP_VCF_SERVICE + " " + str(
                        vip[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create service " + ServiceName.KUBE_VIP_VCF_SERVICE + " " + str(
                        vip[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            payload = {"action": "ALLOW",
                       "display_name": FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_CLUSTER_VIP_CGW,
                       "logged": False,
                       "source_groups": [
                           mgmt_group[0].json["path"],
                           shared_service_group[0].json["path"]],
                       "destination_groups": [
                           cluster_vip_group[0].json["path"]],
                       "services": ["/infra/services/" + ServiceName.KUBE_VIP_VCF_SERVICE],
                       "scope": [teir1[0]]
                       }
            fw_vip = createFirewallRule(Policy_Name.POLICY_NAME, FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_CLUSTER_VIP_CGW,
                                        payload)
            if fw_vip[1] != 200:
                current_app.logger.error(
                    "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_CLUSTER_VIP_CGW + " " + str(
                        fw_vip[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create firewall " + FirewallRuleCgw.DISPLAY_NAME_VCF_TKG_CLUSTER_VIP_CGW + " " + str(
                        fw_vip[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            update = updateDefaultRule(Policy_Name.POLICY_NAME)
            if update[1] != 200:
                current_app.logger.error(
                    "Failed to default rule " + str(update[0].json["msg"]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to default rule " + str(update[0].json["msg"]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        except Exception as e:
            current_app.logger.error("Failed to configure vcf " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to configure vcf " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    current_app.logger.info("VCF pre configuration successful.")
    d = {
        "responseType": "ERROR",
        "msg": "VCF pre configuration successful.",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@vcenter_avi_config.route("/api/tanzu/vsphere/alb/config", methods=['POST'])
def aviDeployment_vsphere():
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": pre[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    refreshToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
    if refreshToken:
        download_status = downloadAviController(env)
        if download_status[1] != 200:
            current_app.logger.error(download_status[0])
            d = {
                "responseType": "ERROR",
                "msg": download_status[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    else:
        current_app.logger.info(
            "MarketPlace refresh token is not provided, skipping the download of AVI Controller OVA")
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    if isEnvTkgs_wcp(env):
        parent_resourcepool = ""
    else:
        parent_resourcepool = current_app.config['RESOURCE_POOL']
    create = createResourceFolderAndWait(vcenter_ip, vcenter_username, password,
                                         cluster_name, data_center, ResourcePoolAndFolderName.AVI_RP_VSPHERE,
                                         ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE, parent_resourcepool)
    if create[1] != 200:
        current_app.logger.error("Failed to create resource pool and folder " + create[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(create[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    try:
        if isEnvTkgs_wcp(env):
            control_plan = "dev"
            avi_fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
            avi_ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Ip']
            if isAviHaEnabled(env):
                avi_fqdn2 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Fqdn']
                avi_ip2 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Ip']
                avi_fqdn3 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Fqdn']
                avi_ip3 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Ip']
            mgmgt_name = request.get_json(force=True)['tkgsComponentSpec']['aviMgmtNetwork'][
                'aviMgmtNetworkName']
            mgmt_cidr = request.get_json(force=True)['tkgsComponentSpec']['aviMgmtNetwork'][
                'aviMgmtNetworkGatewayCidr']
        else:
            control_plan = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgMgmtDeploymentType']
            avi_fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
            avi_ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Ip']
            if isAviHaEnabled(env):
                avi_fqdn2 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Fqdn']
                avi_ip2 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Ip']
                avi_fqdn3 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Fqdn']
                avi_ip3 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Ip']
            mgmgt_name = request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName']
            mgmt_cidr = request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork'][
                'aviMgmtNetworkGatewayCidr']
    except Exception as e:
        current_app.logger.error("Failed to get input " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get input " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if str(control_plan) == "prod":
        control_plan = "dev"
    if isAviHaEnabled(env):
        if not avi_fqdn or not avi_fqdn2 or not avi_fqdn3:
            current_app.logger.error("Avi fqdn not provided, for ha mode 3 fqdns are required")
            d = {
                "responseType": "ERROR",
                "msg": "Avi fqdn not provided, for ha mode 3 fqdns are required",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    if not avi_fqdn:
        current_app.logger.error("Avi fqdn not provided")
        d = {
            "responseType": "ERROR",
            "msg": "Avi fqdn not provided",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if str(control_plan).lower() == "dev":
        if not avi_ip:
            controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
            if isAviHaEnabled(env):
                controller_name2 = ControllerLocation.CONTROLLER_NAME_VSPHERE2
                controller_name3 = ControllerLocation.CONTROLLER_NAME_VSPHERE3
            netmask = ''
            ip = ''
            gateway = ''
        else:
            if not mgmt_cidr:
                current_app.logger.error("Mgmt cidr not provided")
                d = {
                    "responseType": "ERROR",
                    "msg": "Mgmt cidr not provided",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            gateway, netmask = seperateNetmaskAndIp(mgmt_cidr)
            ip = avi_ip
            controller_name = avi_fqdn
            if isAviHaEnabled(env):
                controller_name2 = avi_fqdn2
                controller_name3 = avi_fqdn3
                ip2 = avi_ip2
                ip3 = avi_ip3
        fqdn = avi_fqdn
        if isAviHaEnabled(env):
            fqdn2 = avi_fqdn2
            fqdn3 = avi_fqdn3
        deploy_options = Template(FileHelper.read_resource(Paths.VSPHERE_ALB_DEPLOY_J2))
        FileHelper.write_to_file(
            deploy_options.render(ip=ip, netmask=netmask, gateway=gateway, fqdn=fqdn,
                                  network=mgmgt_name, vm_name=controller_name),
            Paths.VSPHERE_ALB_DEPLOY_JSON)
        if isAviHaEnabled(env):
            FileHelper.write_to_file(
                deploy_options.render(ip=ip2, netmask=netmask, gateway=gateway, fqdn=fqdn2,
                                      network=mgmgt_name, vm_name=controller_name2),
                Paths.VSPHERE_ALB_DEPLOY_JSON2)
            FileHelper.write_to_file(
                deploy_options.render(ip=ip3, netmask=netmask, gateway=gateway, fqdn=fqdn3,
                                      network=mgmgt_name, vm_name=controller_name3),
                Paths.VSPHERE_ALB_DEPLOY_JSON3)
        controller_location = "/" + current_app.config['VC_CONTENT_LIBRARY_NAME'] + "/" + current_app.config[
            'VC_AVI_OVA_NAME']
        controller_location = controller_location.replace(' ', "#remove_me#")
        data_center = "/"+data_center.replace(' ', "#remove_me#")
        data_store = data_store.replace(' ', "#remove_me#")
        if parent_resourcepool is not None:
            rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + parent_resourcepool + "/" + ResourcePoolAndFolderName.AVI_RP_VSPHERE
        else:
            rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.AVI_RP_VSPHERE
        rp_pool = rp_pool.replace(' ', "#remove_me#")
        options = f"-options {Paths.VSPHERE_ALB_DEPLOY_JSON} -dc={data_center} -ds={data_store} -folder={ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE} -pool=/{rp_pool}"
        if isAviHaEnabled(env):
            options2 = f"-options {Paths.VSPHERE_ALB_DEPLOY_JSON2} -dc={data_center} -ds={data_store} -folder={ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE} -pool=/{rp_pool}"
            options3 = f"-options {Paths.VSPHERE_ALB_DEPLOY_JSON3} -dc={data_center} -ds={data_store} -folder={ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE} -pool=/{rp_pool}"
    else:
        current_app.logger.error("Currently other then dev plan is not supported")
        d = {
            "responseType": "ERROR",
            "msg": "Currently other then dev plan is not supported",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    avi_version = get_avi_version(env)
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    dep = deployAndConfigureAvi(govc_client=govc_client, vm_name=controller_name,
                                controller_ova_location=controller_location, deploy_options=options,
                                performOtherTask=True, env=env,
                                avi_version=avi_version)
    if dep[1] != 200:
        current_app.logger.error("Failed to deploy and configure avi " + str(dep[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy and configure avi  " + str(dep[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if isAviHaEnabled(env):
        current_app.logger.info("Deploying 2nd avi controller")
        dep2 = deployAndConfigureAvi(govc_client=govc_client, vm_name=controller_name2,
                                     controller_ova_location=controller_location, deploy_options=options2,
                                     performOtherTask=False, env=env,
                                     avi_version=avi_version)
        if dep2[1] != 200:
            current_app.logger.error("Failed to deploy and configure avi 2nd controller  " + str(dep2[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy and configure avi  " + str(dep2[0].json['msg']),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Deploying 3rd avi controller")
        dep3 = deployAndConfigureAvi(govc_client=govc_client, vm_name=controller_name3,
                                     controller_ova_location=controller_location, deploy_options=options3,
                                     performOtherTask=False, env=env,
                                     avi_version=avi_version)
        if dep3[1] != 200:
            current_app.logger.error("Failed to deploy and configure avi 2nd controller  " + str(dep3[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy and configure avi  " + str(dep3[0].json['msg']),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        res, status = form_avi_ha_cluster(ip, env, None, avi_version)
        if res is None:
            current_app.logger.error("Failed to form avi ha cluster " + str(status))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to form avi ha cluster " + str(status),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully deployed and configured avi",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@vcenter_avi_config.route("/api/tanzu/vsphere/alb/certcreation", methods=['POST'])
def aviCertManagement_vsphere():
    try:
        if current_app.config['VC_PASSWORD'] is None:
            current_app.logger.info("Vc password")
        if current_app.config['VC_USER'] is None:
            current_app.logger.info("Vc user password")
        if current_app.config['VC_IP'] is None:
            current_app.logger.info("Vc ip")
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Un-Authorized " + str(e),
            "ERROR_CODE": 401
        }
        current_app.logger.error("Un-Authorized " + str(e))
        return jsonify(d), 401
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    if isEnvTkgs_wcp(env):
        avi_fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
    else:
        avi_fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
    if not avi_fqdn:
        current_app.logger.error("Avi fqdn not provided")
        d = {
            "responseType": "ERROR",
            "msg": "Avi fqdn not provided",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), avi_fqdn)
    if ip is None:
        current_app.logger.error("Failed to get ip of avi controller")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ip of avi controller",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    deployed_avi_version = obtain_avi_version(ip, env)
    if deployed_avi_version[0] is None:
        current_app.logger.error("Failed to login and obtain avi version"+str(deployed_avi_version[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    aviVersion = deployed_avi_version[0]
    cert = manage_avi_certificates(ip, aviVersion, env, avi_fqdn, CertName.VSPHERE_CERT_NAME)
    if cert[1] != 200:
        current_app.logger.error("Failed to mange-certificate " + cert[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to mange-certificate " + cert[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    isGen = cert[2]
    if isGen:
        current_app.logger.info("Generated and replaced the certificate successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Generated and replaced the certificate successfully",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        current_app.logger.info("Certificate is already generated")
        d = {
            "responseType": "SUCCESS",
            "msg": "Certificate is already generated",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def seperateNetmaskAndIp(cidr):
    return str(cidr).split("/")
