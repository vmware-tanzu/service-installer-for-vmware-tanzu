#!/usr/bin/env python
# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json
import os
import os.path
import ssl
import sys
import tarfile
import time
import logging
from flask import jsonify, request
from flask import Flask
import requests
from flask import current_app
from flask import Blueprint
from datetime import datetime, timedelta
import subprocess
# from common.model.ldapConfig import Ldap
from common.lib.govc_client import GovcClient
from common.util.local_cmd_helper import LocalCmdHelper

vcenter_precheck = Blueprint("vcenter_precheck", __name__, static_folder="prechecks")

# from src.aviConfig.vsphere_avi_config import vcenter_avi_config

logger = logging.getLogger(__name__)

from pyVim import connect
from pyVim.connect import Disconnect
from pyVmomi import vim
from pyVmomi import pbm, VmomiSupport, SoapStubAdapter
import atexit
import base64
# import env_variables
import requests
from flask import Flask, request
from pyVim.connect import Disconnect, SmartConnect
import ipaddress
import uuid

# sys.path.append("../")
from common.operation.vcenter_operations import get_dc, get_ds, get_obj
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from common.operation.ShellHelper import runShellCommandWithPolling,grabPipeOutput, runProcess, runShellCommandAndReturnOutputAsList
from common.operation.constants import Env, MarketPlaceUrl, Tkgs_Extension_Details, Versions
from common.session.session_acquire import login
from common.util.ssl_helper import decode_from_b64

from common.common_utilities import checkMachineCountForTsm, checkClusterSizeForTo, envCheck, \
    enableProxy, dockerLoginAndConnectivityCheck, getIpFromHost, is_ipv4, \
    downloadAviControllerAndPushToContentLibrary, verifyVCVersion, verify_host_count, \
    downloadAndPushKubernetesOvaMarketPlace, checkAirGappedIsEnabled, disableProxyWrapper, \
    proxy_check_and_env_setup, validate_proxy_starts_wit_http, isEnvTkgs_ns, isEnvTkgs_wcp, checTSMEnabled, \
    checkToEnabled, checkOSFlavorForTMC, checkTmcEnabled, getClusterID, isWcpEnabled, checkTanzuExtentionEnabled, \
    fetchNamespaceInfo, isAviHaEnabled, getAviIpFqdnDnsMapping, checkNtpServerValidity, verifyVcenterVersion, \
    configureKubectl, checkDataProtectionEnabled, validate_backup_location, validate_cluster_credential, \
    list_cluster_groups, checkEnableIdentityManagement, checkMachineCountForProdType, checkAVIPassword, \
    checkClusterNameDNSCompliant, ping_test, check_tanzu_license, check_nsxt_license, check_vsphere_license, \
    get_cluster, getNetwork

# check_tanzu_license, check_nsxt_license, check_vsphere_license

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
__author__ = 'Tasmiya'


@vcenter_precheck.route("/api/tanzu/enableproxy", methods=['POST'])
def enable_proxy():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    enable = enableProxy(env)
    if enable != 200:
        current_app.logger.error("Wrong value for ['arcasVm']['enableProxy'] is provided, provide either true/false")
        d = {
            "responseType": "ERROR",
            "msg": "Wrong value for ['arcasVm']['enableProxy'] is provided, provide either true/false",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured, proxy successfully",
        "STATUS_CODE": 200
    }
    current_app.logger.info("Pre-check performed Successfully")
    return jsonify(d), 200


@vcenter_precheck.route("/api/tanzu/disableproxy", methods=['POST'])
def disable_proxy():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    disable = disableProxyWrapper(env)
    if disable != 200:
        current_app.logger.error("Disabling proxy on service installer VM failed.")
        d = {
            "responseType": "ERROR",
            "msg": "Disabling proxy on service installer VM failed",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully deactivated proxy on service installer VM",
        "STATUS_CODE": 200
    }
    return jsonify(d), 200


@vcenter_precheck.route("/api/tanzu/precheck", methods=['POST'])
def precheck_env():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    cmd_doc_start = ["systemctl", "start", "docker"]
    try:
        runShellCommandWithPolling(cmd_doc_start)
    except:
        pass
    cmd_doc = ["systemctl", "enable", "docker"]
    runShellCommandWithPolling(cmd_doc)
    try:
        enable = enableProxy(env)
        if enable != 200:
            current_app.logger.error(
                "Wrong value for ['arcasVm']['enableProxy'] is provided, provide either true/false")
            d = {
                "responseType": "ERROR",
                "msg": "Wrong value for ['arcasVm']['enableProxy'] is provided, provide either true/false",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "Failed while checking ['proxySpec']['arcasVm'] proxy details, please re-check input JSON file",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500

    login()

    try:
        with open(r'/tmp/skipPrecheck.txt', 'r') as file:
            skip_precheck = file.read()
        if skip_precheck.lower() == "true":
            skip_precheck = True
        else:
            skip_precheck = False
    except:
        skip_precheck = False

    if not skip_precheck:
        current_app.logger.info("Performing pre-checks on environment")

        try:
            if env == Env.VSPHERE:
                shared_cluster_name = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceClusterName']
            elif env == Env.VCF:
                shared_cluster_name = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceClusterName']
            elif env == Env.VMC:
                shared_cluster_name = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedClusterName']

            if shared_cluster_name:
                isShared = True
            else:
                isShared = False
        except Exception as e:
            isShared = False

        try:
            if env == Env.VSPHERE:
                workload_cluster_name = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']
            elif env == Env.VCF:
                workload_cluster_name = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']
            elif env == Env.VMC:
                workload_cluster_name = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadClusterName']

            if workload_cluster_name:
                isWorkload = True
            else:
                isWorkload = False
        except Exception as e:
            isWorkload = False

        val = validate_proxy_starts_wit_http(env, isShared, isWorkload)
        if val != "Success":
            current_app.logger.error(
                "Error: Unsupported Proxy protocol found for " + val + ", The Proxy URLs must start with http://")
            d = {
                "responseType": "ERROR",
                "msg": "Error: Unsupported Proxy protocol found for " + val + ", The Proxy URLs must start with http://",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        doc = dockerLoginAndConnectivityCheck(env)
        if doc[1] != 200:
            current_app.logger.error(str(doc[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": str(doc[0].json['msg']),
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        if not checkAirGappedIsEnabled(env):
            if not (isEnvTkgs_wcp(env) or isEnvTkgs_ns(env)):
                if checkTmcEnabled(env):
                    osFlavor = checkOSFlavorForTMC(env, isShared, isWorkload)
                    if osFlavor[1] != 200:
                        current_app.logger.info(str(osFlavor[0].json['msg']))
                        d = {
                            "responseType": "ERROR",
                            "msg": str(osFlavor[0].json['msg']),
                            "STATUS_CODE": 500
                        }
                        return jsonify(d), 500

        if not (isEnvTkgs_wcp(env) or isEnvTkgs_ns(env)):
            if isWorkload:
                to = checkClusterSizeForTo(env)
                if to[1] != 200:
                    current_app.logger.debug(str(to[0].json['msg']))
                    # d = {
                    #     "responseType": "ERROR",
                    #     "msg": str(to[0].json['msg']),
                    #     "STATUS_CODE": 500
                    # }
                    # return jsonify(d), 500
                tsm = checkMachineCountForTsm(env)
                if tsm[1] != 200:
                    current_app.logger.debug("Recommended to use atleast 3 worker machine count for TSM integration")
                #     d = {
                #         "responseType": "ERROR",
                #         "msg": str(tsm[0].json['msg']),
                #         "STATUS_CODE": 500
                #     }
                #     return jsonify(d), 500
            if isShared or isWorkload:
                prod_machine_count = checkMachineCountForProdType(env, isShared, isWorkload)
                if prod_machine_count[1] != 200:
                    current_app.logger.error(str(prod_machine_count[0].json['msg']))
                    d = {
                        "responseType": "ERROR",
                        "msg": str(prod_machine_count[0].json['msg']),
                        "STATUS_CODE": 500
                    }
                    return jsonify(d), 500
        os.system("cp common/vsphere-overlay.yaml " + Env.YTT_FILE_LOCATION)
        os.putenv("HOME", "/root")
        cmd = ["sudo", "sysctl", "net/netfilter/nf_conntrack_max=131072"]
        runShellCommandWithPolling(cmd)
        si = None
        errors = []
        license_check_status = licensePrechecks(env)
        if license_check_status[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": license_check_status[0].json["msg"],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        if env == Env.VSPHERE or env == Env.VCF:
            vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
            if not is_ipv4(vCenter):
                ip = getIpFromHost(vCenter)
                if ip is None:
                    current_app.logger.error('Failed to fetch VC ip')
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to fetch VC ip",
                        "STATUS_CODE": 500
                    }
                    return jsonify(d), 500
            vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
            vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
            vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
            if not isEnvTkgs_ns(env):
                vCenter_datastore = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatastore']
                ntp_server = request.get_json(force=True)['envSpec']['infraComponents']['ntpServers']
            if env == Env.VSPHERE:
                if isEnvTkgs_wcp(env):
                    portGroups = [
                        request.get_json(force=True)['tkgsComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName'],
                        request.get_json(force=True)['tkgsComponentSpec']['tkgsVipNetwork']['tkgsVipNetworkName'],
                        request.get_json(force=True)['tkgsComponentSpec']['tkgsMgmtNetworkSpec'][
                            'tkgsMgmtNetworkName'],
                        request.get_json(force=True)['tkgsComponentSpec']['tkgsPrimaryWorkloadNetwork'][
                            'tkgsPrimaryWorkloadPortgroupName']]
                elif not isEnvTkgs_ns(env):
                    portGroups = [
                        request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName'],
                        request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtNetworkName'],
                        request.get_json(force=True)['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName']]
                    if isWorkload:
                        portGroups.append(
                            request.get_json(force=True)['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkName'])
                        portGroups.append(request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadNetworkName'])

        elif env == Env.VMC:
            vCenter = current_app.config['VC_IP']
            vCenter_user = current_app.config['VC_USER']
            VC_PASSWORD = current_app.config['VC_PASSWORD']
            ntp_server = request.get_json(force=True)['envVariablesSpec']['ntpServersIp']
            if not (vCenter or vCenter_user or VC_PASSWORD):
                current_app.logger.error('Failed to fetch VC details')
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to find VC details",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500

            vCenter_datacenter = request.get_json(force=True)['envSpec']['sddcDatacenter']
            vCenter_cluster = request.get_json(force=True)['envSpec']['sddcCluster']
            vCenter_datastore = request.get_json(force=True)['envSpec']['sddcDatastore']

        try:
            si = connect.SmartConnectNoSSL(host=vCenter, user=vCenter_user, pwd=VC_PASSWORD)
            content = si.RetrieveContent()
            vcVersion = content.about.version
            try:
                if str(vcVersion).startswith("8"):
                    current_app.logger.error("Deployment of TKG 1.7.0 on vSphere 8.0 is not supported")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Deployment of 1.7.0 on vSphere 8.0 is not supported",
                        "STATUS_CODE": 500
                    }
                    return jsonify(d), 500
            except Exception as e:
                current_app.logger.error(str(e))
                d = {
                    "responseType": "ERROR",
                    "msg": "Pre-check failed " + str(e),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            try:
                if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
                    version_check = verifyVCVersion(vcVersion)
                    if version_check[0] is None:
                        current_app.logger.error(version_check[1])
                        d = {
                            "responseType": "ERROR",
                            "msg": version_check[1],
                            "STATUS_CODE": 500
                        }
                        return jsonify(d), 500
                    current_app.logger.info("Successfully verified vCenter Version " + vcVersion)
            except Exception as e:
                current_app.logger.error(e)
                d = {
                    "responseType": "ERROR",
                    "msg": "Pre-check failed " + str(e),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            # if datacenter itself is not found, pre-check fail
            try:
                datacenter = get_dc(si, vCenter_datacenter)
            except Exception as e:
                current_app.logger.error(e)
                d = {
                    "responseType": "ERROR",
                    "msg": "Pre-check failed " + str(e),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500

            try:
                cluster_obj = get_cluster(si, datacenter, vCenter_cluster)
                if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
                    hostCount = verify_host_count(cluster_obj)
                    if hostCount[0] is None:
                        current_app.logger.error(hostCount[1])
                        d = {
                            "responseType": "ERROR",
                            "msg": hostCount[1],
                            "STATUS_CODE": 500
                        }
                        return jsonify(d), 500
                    current_app.logger.info("Successfully verified number of hosts on cluster: " + vCenter_cluster)
            except Exception as e:
                errors.append(e)

            if not isEnvTkgs_ns(env):
                try:
                    get_ds(si, datacenter, vCenter_datastore)
                except Exception as e:
                    errors.append(e)

                if env == Env.VSPHERE:
                    try:
                        for portgroup in portGroups:
                            getNetwork(datacenter, portgroup)
                    except Exception as e:
                        errors.append(e)

            if errors:
                current_app.logger.error("Pre-check failed with following errors")
                for error in errors:
                    current_app.logger.error(error)
                d = {
                    "responseType": "ERROR",
                    "msg": "Pre-check failed " + str(errors),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500

        except IOError as e:
            atexit.register(Disconnect, si)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to connect to vCenter. " + str(e),
                "STATUS_CODE": 500
            }
            current_app.logger.error("Failed to connect to vCenter. " + str(e))
            return jsonify(d), 500

        current_app.logger.info("Validating time synchronization between ESXi and vCenters")
        vcenter_time = si.CurrentTime()
        current_app.logger.info("vCenter " + vCenter + " current time: " + str(vcenter_time))
        cluster_obj = get_cluster(si, datacenter, vCenter_cluster)
        esxis = cluster_obj.host
        for es in esxis:
            date_time_mgr = es.configManager.dateTimeSystem
            date_time = date_time_mgr.QueryDateTime()
            current_app.logger.info("Host " + es.name + " current time: " + str(date_time))
            if vcenter_time > date_time:
                time_difference = (vcenter_time - date_time).total_seconds()
            else:
                time_difference = (date_time - vcenter_time).total_seconds()
            if time_difference > float(300):
                current_app.logger.warn("Time difference between ESXi host " + es.name +
                                        " and vCenter is greater than 5 minutes. This will lead to deployment failures,"
                                        " it's recommended to fix this issue before proceeding with deployment")
                time.sleep(15)
        current_app.logger.info("Time synchronization validation completed")

        if isEnvTkgs_ns(env):
            refreshToken = ""
        elif env == Env.VSPHERE or env == Env.VCF:
            refreshToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
        elif env == Env.VMC:
            refreshToken = request.get_json(force=True)['marketplaceSpec']['refreshToken']
        if not refreshToken:
            current_app.logger.info("MarketPlace refreshToken is not provided")
        else:
            token_valdity = validateMarketplaceRefreshToken()
            if token_valdity[1] != 200:
                # if not ('msg' in token_valdity[0]):
                current_app.logger.error(
                    "Marketplace token validation failed. Please ensure connectivity to external networks.")
                d = {
                    "responseType": "ERROR",
                    "msg": "Marketplace token validation failed. Please ensure connectivity to external networks.",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
        os.putenv("GOVC_URL", "https://" + vCenter + "/sdk")
        os.putenv("GOVC_USERNAME", vCenter_user)
        os.putenv("GOVC_PASSWORD", VC_PASSWORD)
        os.putenv("GOVC_INSECURE", "true")
        # else:
        # down = downloadAviControllerAndPushToContentLibrary(vCenter, vCenter_user, VC_PASSWORD, env)
        # if down[0] is None:
        # current_app.logger.error(down[1])
        # d = {
        # "responseType": "ERROR",
        # "msg": down[1],
        # "STATUS_CODE": 500
        # }
        # return jsonify(d), 500
        # customer = request.get_json(force=True)['envSpec']['resource-spec']['avi-pulse-jwt-token']
        # password = request.get_json(force=True)['envSpec']['resource-spec']['avi-pulse-jwt-token']
        # if not customer or not password:
        # current_app.logger.info("Customer connect user/password not provided")
        # else:
        # Kubernetes download
        # if isEnvTkgs(env):
        # current_app.logger.info("Photon checks not required")
        # else:
        # push = downloadAndPushKubernetesOvaMarketPlace(env)
        # if push[0] is None:
        # current_app.logger.error(push[1])
        # d = {
        # "responseType": "ERROR",
        # "msg": push[1],
        # "STATUS_CODE": 500
        # }
        # return jsonify(d), 500
        if isEnvTkgs_wcp(env):
            hadrs_status = verifyHADRS(content, vCenter_cluster)
            if hadrs_status[1] != 200:
                current_app.logger.error(hadrs_status[0])
                d = {
                    "responseType": "ERROR",
                    "msg": hadrs_status[0],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            namespace_status = checkClusterNamespace(vCenter, vCenter_user, VC_PASSWORD, vCenter_cluster)
            if namespace_status[1] != 200:
                current_app.logger.error(namespace_status[0])
                d = {
                    "responseType": "ERROR",
                    "msg": namespace_status[0],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Ping check on Supervisor control plane VMs' management network interfaces Ips")
            mgmt_ping_status = pingCheckTkgsMgmtStartIp()
            if not mgmt_ping_status[0]:
                current_app.logger.error(mgmt_ping_status[1])
                d = {
                    "responseType": "ERROR",
                    "msg": mgmt_ping_status[1],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            if checkTmcEnabled(env):
                current_app.logger.info("Checking whether Supervisor cluster name is DNS Compliant")
                supervisor_cluster_name = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                    'tmcSupervisorClusterName']
                dns_compliant = checkClusterNameDNSCompliant(supervisor_cluster_name, env)
                if not dns_compliant[0]:
                    current_app.logger.error("Failed while checking if Supervisor cluster name is DNS Compliant")
                    d = {
                        "responseType": "ERROR",
                        "msg": dns_compliant[1],
                        "STATUS_CODE": 500
                    }
                    return jsonify(d), 500

        elif isEnvTkgs_ns(env):
            current_app.logger.info("Checking if WCP is enabled on selected cluster...")
            cluster_id = getClusterID(vCenter, vCenter_user, VC_PASSWORD, vCenter_cluster)
            if cluster_id[1] != 200:
                current_app.logger.error(cluster_id[0])
                d = {
                    "responseType": "ERROR",
                    "msg": cluster_id[0],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500

            cluster_id = cluster_id[0]
            wcp_status = isWcpEnabled(cluster_id)
            if wcp_status[0]:
                current_app.logger.info("WCP check passed.")
            else:
                current_app.logger.error("WCP is not enabled on the given cluster - " + vCenter_cluster)
                d = {
                    "responseType": "ERROR",
                    "msg": "WCP is not enabled on the given cluster - " + vCenter_cluster,
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            if checTSMEnabled(env) or checkToEnabled(env):
                worker_size = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['workerNodeCount']
                if int(worker_size) < 3:
                    current_app.logger.error("Minimum required number of worker nodes for SaaS integrations is 3, "
                                             "and recommended size is medium and above")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Minimum required number of worker nodes for SaaS integrations is 3,"
                               " and recommended size is medium and above",
                        "STATUS_CODE": 500
                    }
                    return jsonify(d), 500
                else:
                    current_app.logger.info("Worker nodes requirement check passed for TSM and TO.")
            else:
                current_app.logger.info("TSM and TO not is enabled.")

            current_app.logger.info("Checking User-Managed Packages' compatibility with provided workload cluster version")
            if verifyVcenterVersion(Versions.VCENTER_UPDATE_TWO):
                supported_versions = Tkgs_Extension_Details.SUPPORTED_VERSIONS_U2
            else:
                supported_versions = Tkgs_Extension_Details.SUPPORTED_VERSIONS_U3

            cluster_version = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterVersion']
            if not cluster_version.startswith('v'):
                cluster_version = 'v' + cluster_version
            if cluster_version not in supported_versions:
                current_app.logger.warn("Provided Tanzu K8s version is not validated for User-Managed"
                                        " Packages such as Harbor, Prometheus and Grafana - " + cluster_version)
            else:
                current_app.logger.info("Provided Tanzu K8s version is validated for User-Managed "
                                        "Packages such as Harbor, Prometheus and Grafana - " + cluster_version)

            policy_validation = checkWorkloadStoragePolicies(env)
            if policy_validation[0] is None:
                current_app.logger.error(policy_validation[1])
                d = {
                    "responseType": "ERROR",
                    "msg": "Storage Policy validation failed for workload cluster",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            else:
                current_app.logger.info(policy_validation[1])
            current_app.logger.info("Checking whether Workload cluster name is DNS Compliant")
            supervisor_cluster_name = \
                request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec'][
                    'tkgsVsphereWorkloadClusterName']
            dns_compliant = checkClusterNameDNSCompliant(supervisor_cluster_name, env)
            if not dns_compliant[0]:
                current_app.logger.error("Failed while checking if Supervisor cluster name is DNS Compliant")
                d = {
                    "responseType": "ERROR",
                    "msg": dns_compliant[1],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
        if not isEnvTkgs_ns(env):
            current_app.logger.info("Checking if NTP server is valid")
            valid_ntp_server = validityOfNtpServer(ntp_server=ntp_server)
            # Checking Validity of NTP Server
            if not valid_ntp_server[0]:
                current_app.logger.error(valid_ntp_server[1])
                d = {
                    "responseType": "ERROR",
                    "msg": valid_ntp_server[1],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500

        if not isEnvTkgs_ns(env):
            current_app.logger.info("NSX ALB Password complexity check..")
            password_check = checkAVIPassword(env)
            if not password_check[0]:
                current_app.logger.error("NSX ALB Password and Backup passphrase must contain a combination of 3: "
                                         "Uppercase character, Lowercase character, Numeric or Special Character.")
                d = {
                    "responseType": "ERROR",
                    "msg": "Password complexity check failed for NSX ALB",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500

        if not (isEnvTkgs_ns(env) or env == Env.VMC):
            # Ping test on AVI Controller IP
            current_app.logger.info("Checking ping response for AVI Controller IPs")
            ping_test_avi_ip = pingCheckAviControllerIp()
            if not ping_test_avi_ip[0]:
                current_app.logger.error(ping_test_avi_ip[1])
                d = {
                    "responseType": "ERROR",
                    "msg": ping_test_avi_ip[1],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500

            # Checking DNS Resolution of AVI FQDN
            current_app.logger.info("Checking that the AVI Load balancer FQDN and "
                                    "IP addresses are valid and can be resolved successfully.")
            avi_ip_fqdn_check = checkAVIFqdnDNSResolution()
            if not avi_ip_fqdn_check[0]:
                current_app.logger.error(avi_ip_fqdn_check[1])

        veleroResponse = veleroPrechecks(env, isShared, isWorkload)
        if veleroResponse[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": veleroResponse[0].json["msg"],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Data protection pre-requisites validated successfully")

        current_app.logger.info("Validating given VM Storage Policies for encryption...")
        if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
            encryption_validation = validatePolicies(si, env)
            if not encryption_validation[0]:
                current_app.logger.error(encryption_validation[1])
                current_app.logger.error("Deployment with encrypted storage policies is not supported. "
                                         "Please disable encryption on given policies")
                d = {
                    "responseType": "ERROR",
                    "msg": "Storage Policy validation failed.",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info(encryption_validation[1])

        current_app.logger.info("Pre-check performed Successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Pre-check performed Successfully",
            "STATUS_CODE": 200
        }
        return jsonify(d), 200
    else:
        current_app.logger.warn("Skipping Pre-checks for environment may lead to failure in deployment. "
                                "Make sure to remove \"--skip_precheck\" option from arcas command to perform pre-checks")
        d = {
            "responseType": "SUCCESS",
            "msg": "Pre-check of environment has been skipped",
            "STATUS_CODE": 200
        }
        return jsonify(d), 200


@vcenter_precheck.route("/api/tanzu/validateIP", methods=['POST'])
def validateip():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    errors = []
    current_app.logger.info("Performing IP Validation")
    if env == Env.VSPHERE or env == Env.VCF:
        avi_mgmt_cidr = request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork'][
            'aviMgmtNetworkGatewayCidr']
        tkg_mgmt_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtGatewayCidr']
        tkg_mgmt_data_cidr = request.get_json(force=True)['tkgMgmtDataNetwork']['tkgMgmtDataNetworkGatewayCidr']
        tkg_work_data_cidr = request.get_json(force=True)['tkgWorkloadDataNetwork'][
            'tkgWorkloadDataNetworkGatewayCidr']
        tkg_work_comp_cidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadGatewayCidr']

        if ipaddress.IPv4Address(request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork'][
                                     'aviMgmtServiceIpStartRange']) in ipaddress.IPv4Network(avi_mgmt_cidr,
                                                                                             False) and \
                ipaddress.IPv4Address(request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork'][
                                          'aviMgmtServiceIpEndRange']) in ipaddress.IPv4Network(avi_mgmt_cidr,
                                                                                                False):
            current_app.logger.info('aviMgmtNetwork IP validation passed')
        else:
            errors.append("aviMgmtNetwork IP Validation failed")

        if ipaddress.IPv4Address(request.get_json(force=True)['tkgMgmtDataNetwork'][
                                     'tkgMgmtAviServiceIpStartRange']) in ipaddress.IPv4Network(tkg_mgmt_data_cidr,
                                                                                                False) and \
                ipaddress.IPv4Address(request.get_json(force=True)['tkgMgmtDataNetwork'][
                                          'tkgMgmtAviServiceIpEndRange']) in ipaddress.IPv4Network(
            tkg_mgmt_data_cidr, False):
            current_app.logger.info('tkgMgmtDataNetwork IP validation passed')
        else:
            errors.append("tkgMgmtDataNetwork IP Validation failed")

        if ipaddress.IPv4Address(request.get_json(force=True)['tkgWorkloadDataNetwork'][
                                     'tkgWorkloadAviServiceIpStartRange']) in ipaddress.IPv4Network(
            tkg_work_data_cidr, False) and \
                ipaddress.IPv4Address(request.get_json(force=True)['tkgWorkloadDataNetwork'][
                                          'tkgWorkloadAviServiceIpEndRange']) in ipaddress.IPv4Network(
            tkg_work_data_cidr, False):
            current_app.logger.info('tkgWorkloadDataNetwork IP validation passed')
        else:
            errors.append("tkgWorkloadDataNetwork IP Validation failed")

    elif env == Env.VMC:
        tkg_shared_cidr = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
            'tkgSharedGatewayCidr']
        avi_mgmt_nw_cidr = request.get_json(force=True)['componentSpec']['aviMgmtNetworkSpec'][
            'aviMgmtGatewayCidr']
        tkg_mgmt_data_cidr = request.get_json(force=True)['componentSpec']['tkgMgmtDataNetworkSpec'][
            'tkgMgmtDataGatewayCidr']
        tkg_work_data_cidr = request.get_json(force=True)['componentSpec']['tkgWorkloadDataNetworkSpec'][
            'tkgWorkloadDataGatewayCidr']
        tkg_workload_cidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
            'tkgWorkloadGatewayCidr']

        if ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                                     'tkgSharedDhcpStartRange']) in ipaddress.IPv4Network(tkg_shared_cidr, False) and \
                ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                                          'tkgSharedDhcpEndRange']) in ipaddress.IPv4Network(tkg_shared_cidr, False):
            current_app.logger.info('tkgSharedServiceSpec IP validation passed')
        else:
            errors.append("tkgSharedServiceSpec IP Validation failed")

        if ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['aviMgmtNetworkSpec'][
                                     'aviMgmtDhcpStartRange']) in ipaddress.IPv4Network(avi_mgmt_nw_cidr, False) and \
                ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['aviMgmtNetworkSpec'][
                                          'aviMgmtDhcpEndRange']) in ipaddress.IPv4Network(avi_mgmt_nw_cidr, False):
            current_app.logger.info('aviMgmtNetworkSpec IP validation passed')
        else:
            errors.append("aviMgmtNetworkSpec IP Validation failed")

        if ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['tkgMgmtDataNetworkSpec'][
                                     'tkgMgmtDataDhcpStartRange']) in ipaddress.IPv4Network(tkg_mgmt_data_cidr,
                                                                                            False) and \
                ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['tkgMgmtDataNetworkSpec'][
                                          'tkgMgmtDataDhcpEndRange']) in ipaddress.IPv4Network(tkg_mgmt_data_cidr,
                                                                                               False):

            current_app.logger.info('tkgMgmtDataNetworkSpec IP validation passed')
        else:
            errors.append("tkgMgmtDataNetworkSpec IP Validation failed")

        if ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['tkgWorkloadDataNetworkSpec'][
                                     'tkgWorkloadDataDhcpStartRange']) in ipaddress.IPv4Network(tkg_work_data_cidr,
                                                                                                False) and \
                ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['tkgWorkloadDataNetworkSpec'][
                                          'tkgWorkloadDataDhcpEndRange']) in ipaddress.IPv4Network(
            tkg_work_data_cidr, False):
            current_app.logger.info('tkgWorkloadDataNetworkSpec IP validation passed')
        else:
            errors.append("tkgWorkloadDataNetworkSpec IP Validation failed")

        if ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                                     'tkgWorkloadDhcpStartRange']) in ipaddress.IPv4Network(tkg_workload_cidr,
                                                                                            False) and \
                ipaddress.IPv4Address(request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                                          'tkgWorkloadDhcpEndRange']) in ipaddress.IPv4Network(tkg_workload_cidr,
                                                                                               False):
            current_app.logger.info('tkgWorkloadSpec IP validation passed')
        else:
            errors.append("tkgWorkloadSpec Validation IP failed")

    if errors:
        current_app.logger.error("IP Validation failed with following errors")
        for error in errors:
            current_app.logger.error(error)
        d = {
            "responseType": "ERROR",
            "msg": "pre-check failed " + str(errors),
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    else:
        d = {
            "responseType": "SUCCESS",
            "msg": "IP Validation is Successful",
            "STATUS_CODE": 200
        }
        current_app.logger.info("IP Validation is Successful")
        return jsonify(d), 200


@vcenter_precheck.route("/api/tanzu/validateTMCRefreshToken", methods=['POST'])
def validateTMCRefreshToken():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    try:
        if env == Env.VSPHERE or env == Env.VCF:
            tmc_availability = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                'tmcAvailability']
            if tmc_availability.lower() == 'false':
                current_app.logger.info("Skipping TMC refresh token validation as tmcAvailability is set to false")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Skipping TMC refresh token validation as tmcAvailability is set to false",
                    "STATUS_CODE": 200
                }
                return jsonify(d), 200
            else:
                TMC_TOKEN = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                    'tmcRefreshToken']
        elif env == Env.VMC:
            TMC_TOKEN = request.get_json(force=True)["saasEndpoints"]['tmcDetails']['tmcRefreshToken']

        if not TMC_TOKEN:
            current_app.logger.error("TMC refresh token is found null, please enter a valid TMC token")
            d = {
                "responseType": "ERROR",
                "msg": "TMC refresh token is found null, please enter a valid TMC token",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        validateStatus = validateToken(TMC_TOKEN, ['VMware Tanzu Mission Control'])
        if validateStatus[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": validateStatus[0],
                "STATUS_CODE": validateStatus[1]
            }
            current_app.logger.error(validateStatus[0])
            return jsonify(d), validateStatus[1]
        else:
            d = {
                "responseType": "SUCCESS",
                "msg": "TMC refresh token validation Passed",
                "STATUS_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcenter_precheck.route("/api/tanzu/validateSDDCRefreshToken", methods=['POST'])
def validateSDDCRefreshToken():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    try:
        if env == Env.VMC:
            SDDC_TOKEN = request.get_json(force=True)['envSpec']['sddcRefreshToken']
            if not SDDC_TOKEN:
                current_app.logger.error("SDDC refresh token is found null, please enter a valid SDDC token")
                d = {
                    "responseType": "ERROR",
                    "msg": "SDDC refresh token is found null, please enter a valid SDDC token",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            sddc_validateStatus = validateToken(SDDC_TOKEN, ['VMware Cloud on AWS'])
            if sddc_validateStatus[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": sddc_validateStatus[0],
                    "STATUS_CODE": sddc_validateStatus[1]
                }
                current_app.logger.error(sddc_validateStatus[0])
                return jsonify(d), sddc_validateStatus[1]
            d = {
                "responseType": "SUCCESS",
                "msg": "SDDC refresh token validation Passed",
                "STATUS_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcenter_precheck.route("/api/tanzu/validateMarketplaceRefreshToken", methods=['POST'])
def validateMarketplaceRefreshToken():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    try:
        if env == Env.VMC:
            REFRESH_TOKEN = request.get_json(force=True)['marketplaceSpec']['refreshToken']
        elif env == Env.VSPHERE or env == Env.VCF or env == Env.VCD:
            REFRESH_TOKEN = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
            if not REFRESH_TOKEN:
                current_app.logger.error(
                    "Marketplace refresh token is found null, please enter a valid marketplace token")
                d = {
                    "responseType": "ERROR",
                    "msg": "Marketplace refresh token is found null, please enter a valid marketplace token",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500

        current_app.logger.info("Logging into MarketPlace using provided refresh token...")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "refreshToken": REFRESH_TOKEN
        }
        json_object = json.dumps(payload, indent=4)
        sess = requests.request("POST", MarketPlaceUrl.URL + "/api/v1/user/login", headers=headers,
                                data=json_object, verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Unable to login to MarketPlace using provided refresh token, please enter a valid marketplace token",
                "STATUS_CODE": 500
            }
            current_app.logger.error(
                "Unable to login to MarketPlace using provided refresh token, please enter a valid marketplace token")
            return jsonify(d), 500
        else:
            current_app.logger.info("Marketplace refresh token validation Passed")
            d = {
                "responseType": "SUCCESS",
                "msg": "Marketplace refresh token validation Passed",
                "STATUS_CODE": 200
            }
        return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcenter_precheck.route("/api/tanzu/pingTestSupervisorControlPlane", methods=['POST'])
def pingTestSupervisorControlPlane():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    current_app.logger.info("Ping check on Supervisor control plane VMs' management network interfaces Ips")
    mgmt_ping_status = pingCheckTkgsMgmtStartIp()
    if not mgmt_ping_status[0]:
        current_app.logger.error(mgmt_ping_status[1])
        d = {
            "responseType": "ERROR",
            "msg": mgmt_ping_status[1],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info("Pinged successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Ping test for Supervisor control plane VMs' PASSED",
        "STATUS_CODE": 200
    }
    return jsonify(d), 200


@vcenter_precheck.route("/api/tanzu/aviNameResolution", methods=['POST'])
def aviNameResolution():
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env provided " + env[0],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    env = env[0]
    if env == Env.VCD:
        current_app.config['VC_IP'] = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterAddress']
        current_app.config['VC_USER'] = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterSsoUser']
        current_app.config['VC_PASSWORD'] = decode_from_b64(
            str(request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['vcenterDetails']['vcenterSsoPasswordBase64']))
    elif not (isEnvTkgs_ns(env) or env == Env.VMC):
        current_app.config['VC_IP'] = request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterAddress"]
        current_app.config['VC_USER'] = request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoUser"]
        current_app.config['VC_PASSWORD'] = decode_from_b64(
            request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        # vCenter = current_app.config['VC_IP']
        # vc_user = current_app.config['VC_USER']
        # vc_password = current_app.config['VC_PASSWORD']
        current_app.logger.info("Checking ping response for AVI Controller IPs")
        ping_test_avi_ip = pingCheckAviControllerIp()
        if not ping_test_avi_ip[0]:
            current_app.logger.error(ping_test_avi_ip[1])
            d = {
                "responseType": "ERROR",
                "msg": ping_test_avi_ip[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Ping test successful")
        ## Name Resolution
        current_app.logger.info("Checking that the AVI Load balancer's FQDN and "
                                "IP addresses are valid and can be resolved successfully.")
        avi_ip_fqdn_check = checkAVIFqdnDNSResolution()
        if not avi_ip_fqdn_check[0]:
            current_app.logger.error(avi_ip_fqdn_check[1])
            d = {
                "responseType": "ERROR",
                "msg": avi_ip_fqdn_check[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
    current_app.logger.info("Successfully found name resolution of NSX ALB FQDN with controller IP")
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully found name resolution of NSX ALB FQDN with controller IP",
        "STATUS_CODE": 200
    }
    return jsonify(d), 200


def validateToken(token, serviceList):
    try:
        url = "https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize?refresh_token=" + token
        headers = {}
        payload = {}
        response_login = requests.request("POST", url, headers=headers, data=payload, verify=False)
        if response_login.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": serviceList[0] + " login failed using Refresh_Token ",
                "STATUS_CODE": 500
            }
            body = json.dumps(response_login)
            if 'message' in body:
                error = body['message']
            else:
                error = 'unknown error'
            current_app.logger.error(serviceList[0] + " login failed using Refresh_Token - %s: %s" %
                                     token, error)
            return error, 500
        access_token = response_login.json()["access_token"]

        url = "https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/details"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': "bearer " + access_token
        }
        payload = {
            "tokenValue": token
        }
        body = json.dumps(payload, indent=4)
        response_org = requests.request("POST", url, headers=headers, data=body, verify=False)
        if response_org.status_code != 200:
            return response_org.text, 500
        ORG_ID = None
        ORG_ID = response_org.json()['orgId']
        if ORG_ID is None:
            return "Failed to get org id using Refresh_Token - " + token, 500
        current_app.logger.info("Successfully retrieved ORG ID details for token: " + token)
        validity = response_org.json()['expiresAt']

        if checkDateExpiry(validity) == False:
            error = "Refresh token is already expired on %s. Please add new refresh token. " % datetime.fromtimestamp(
                validity / 1000)
            return error, 500

        url = "https://console.cloud.vmware.com/csp/gateway/am/api/loggedin/user/orgs/" + ORG_ID + "/info"
        headers = {
            'Content-Type': 'application/json',
            'csp-auth-token': access_token
        }
        payload = {}
        services = requests.request("GET", url, headers=headers, data=payload, verify=False)
        if services.status_code != 200:
            return "Failed to execute API to fetch services", 500

        matched_services = []
        services_json = services.json()
        for service in serviceList:
            for component in services_json['userOrgInfo'][0]['servicesDef']:
                if component['serviceDisplayName'] == service:
                    matched_services.append(service)

        if serviceList != matched_services:
            error = "User with refresh token %s does not have access to %s service/s " % (token, serviceList)
            return error, 500

        return "Refresh token Validation Passed", 200

    except Exception as e:
        current_app.logger.error(e)
        raise Exception(e)


def checkDateExpiry(expiryDate):
    expiryDate = datetime.fromtimestamp(expiryDate / 1000)
    validTime = (expiryDate - datetime.now()) / timedelta(hours=1)
    if validTime < 4:
        return False
    else:
        return True


def verifyHADRS(content, clusterName):
    cluster_obj = get_obj(content, [vim.ClusterComputeResource], clusterName)
    if not cluster_obj:
        msg = "Cluster NOT found, please provide correct cluster name"
        current_app.logger.error(msg)
        d = {
            "responseType": "ERROR",
            "msg": msg,
            "STATUS_CODE": 500
        }
        return jsonify(d), 500

    drs_enabled = cluster_obj.configuration.drsConfig.enabled
    if not drs_enabled:
        msg = "DRS is not enabled on cluster: " + clusterName
        current_app.logger.error(msg)
        d = {
            "responseType": "ERROR",
            "msg": msg,
            "STATUS_CODE": 500
        }
        return jsonify(d), 500

    ha_enabled = cluster_obj.configuration.dasConfig.enabled
    if not ha_enabled:
        msg = "HA is not enabled on cluster: " + clusterName
        current_app.logger.error(msg)
        d = {
            "responseType": "ERROR",
            "msg": msg,
            "STATUS_CODE": 500
        }
        return jsonify(d), 500

    d = {
        "responseType": "SUCCESS",
        "msg": "HA and DRS is enabled on cluster: " + clusterName,
        "STATUS_CODE": 200
    }
    return jsonify(d), 200


def checkClusterNamespace(vCenter, vCenter_user, VC_PASSWORD, cluster):
    url = "https://" + vCenter + "/"
    if not (vCenter_user or VC_PASSWORD):
        d = {
            "responseType": "ERROR",
            "msg": "vCenter credentials not found",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500

    cluster_id = getClusterID(vCenter, vCenter_user, VC_PASSWORD, cluster)
    if cluster_id[1] != 200:
        current_app.logger.error(cluster_id[0].json["msg"])
        d = {
            "responseType": "ERROR",
            "msg": cluster_id[0].json["msg"],
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
    try:
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        else:
            vc_session = sess.json()['value']

        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": vc_session
        }

        payload = {"cluster": cluster_id[0],
                   "network_provider": "VSPHERE_NETWORK"
                   }
        namespace_compatible = requests.request("GET",
                                                url + "api/vcenter/namespace-management/distributed-switch-compatibility",
                                                headers=header, params=payload, verify=False)
        if namespace_compatible.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch vSphere Namespace compatibility status with VDS for the given cluster- " + cluster,
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        if namespace_compatible.json()[0]["compatible"]:
            d = {
                "responseType": "SUCCESS",
                "msg": "vSphere Namespace compatible with VDS for the given cluster " + cluster,
                "STATUS_CODE": 200
            }
            return jsonify(d), 200
        else:
            d = {
                "responseType": "ERROR",
                "msg": "vSphere Namespace is not compatible with VDS for the given cluster " + cluster,
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "vSphere Namespace is not compatible with VDS for the given cluster " + cluster,
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


def isWcpEnabled(cluster_id):
    vcenter_ip = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
    vcenter_username = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
    str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
    base64_bytes = str_enc.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password = enc_bytes.decode('ascii').rstrip("\n")
    if not (vcenter_ip or vcenter_username or password):
        return None, "Failed to fetch VC details"

    sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                         auth=(vcenter_username, password), verify=False)
    if sess.status_code != 200:
        current_app.logger.error("Connection to vCenter failed")
        return None, "Connection to vCenter failed"
    else:
        vc_session = sess.json()['value']

    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "vmware-api-session-id": vc_session
    }
    url = "https://" + vcenter_ip + "/api/vcenter/namespace-management/clusters/" + cluster_id
    response_csrf = requests.request("GET", url, headers=header, verify=False)
    if response_csrf.status_code != 200:
        if response_csrf.status_code == 400:
            if response_csrf.json()["messages"][0][
                "default_message"] == "Cluster with identifier " + cluster_id + " does " \
                                                                                "not have Workloads enabled.":
                return False, None

    elif response_csrf.json()["config_status"] == "RUNNING":
        return True, response_csrf.json()
    else:
        return False, None


def getClusterVersionsFullList(vCenter, vcenter_username, password, cluster):
    try:
        cluster_id = getClusterID(vCenter, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[0])
            d = {
                "responseType": "ERROR",
                "msg": cluster_id[0],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        cluster_id = cluster_id[0]

        wcp_status = isWcpEnabled(cluster_id)
        if wcp_status[0]:
            endpoint_ip = wcp_status[1]['api_server_cluster_endpoint']
        else:
            current_app.logger.error("WCP not enabled on given cluster - " + cluster)

        current_app.logger.info("Setting up kubectl vsphere plugin...")
        configure_kubectl = configureKubectl(endpoint_ip)
        if configure_kubectl[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": configure_kubectl[0],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("logging into cluster - " + endpoint_ip)
        os.putenv("KUBECTL_VSPHERE_PASSWORD", password)
        connect_command = ["kubectl", "vsphere", "login", "--server=" + endpoint_ip,
                           "--vsphere-username=" + vcenter_username,
                           "--insecure-skip-tls-verify"]
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            current_app.logger.error("Failed while connecting to Supervisor Cluster ")
            d = {
                "responseType": "ERROR",
                "msg": "Failed while connecting to Supervisor Cluster",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        switch_context = ["kubectl", "config", "use-context", endpoint_ip]
        output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            current_app.logger.error("Failed to use context " + str(output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to use context " + str(output[0]),
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        get_versions_command = ["kubectl", "get", "tkr"]
        versions_output = runShellCommandAndReturnOutputAsList(get_versions_command)
        if versions_output[1] != 0:
            current_app.logger.error("Failed to fetch cluster versions " + str(versions_output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch cluster versions " + str(versions_output[0]),
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        return versions_output[0], 200
    except Exception as e:
        current_app.logger.error("Exception occurred while fetching cluster versions list - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching cluster versions list- " + str(e),
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


def checkClusterVersionCompatibility(vc_ip, vc_user, vc_password, cluster_name, version):
    cluster_versions = getClusterVersionsFullList(vc_ip, vc_user, vc_password, cluster_name)
    if cluster_versions[1] != 200:
        return False, cluster_versions[0]
    else:
        for entry in cluster_versions[0]:
            value_list = entry.split()
            if value_list[1] == version[1:]:
                if (value_list[2] and value_list[3]) == "True":
                    return True, "VERSION_FOUND"
                else:
                    return False, "Incompatible cluster version provided for workload creation - " + version
        else:
            return False, "Provided version not found in cluster versions list - " + version


def GetPbmConnection(vpxdStub):
    VmomiSupport.GetRequestContext()["vcSessionCookie"] = \
        vpxdStub.cookie.split('"')[1]
    hostname = vpxdStub.host.split(":")[0]
    pbm_stub = SoapStubAdapter(
        host=hostname,
        version="pbm.version.version1",
        path="/pbm/sdk",
        poolSize=0,
        sslContext=ssl._create_unverified_context())
    pbm_si = pbm.ServiceInstance("ServiceInstance", pbm_stub)
    pbm_content = pbm_si.RetrieveContent()
    return pbm_content


def validatePolicies(si, env):
    policies = []
    if isEnvTkgs_wcp(env):
        policies.append(str(request.get_json(force=True)["tkgsComponentSpec"]["tkgsStoragePolicySpec"]["imageStoragePolicy"]))
        policies.append(str(request.get_json(force=True)["tkgsComponentSpec"]["tkgsStoragePolicySpec"]["ephemeralStoragePolicy"]))
        policies.append(str(request.get_json(force=True)["tkgsComponentSpec"]["tkgsStoragePolicySpec"]["masterStoragePolicy"]))
    elif isEnvTkgs_ns(env):
        namespace_specs = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereNamespaceStorageSpec']

        for storage_policy in namespace_specs:
            policies.append(storage_policy['storagePolicy'])
    else:
        return False, "Wrong environment type provided for storage policies validation - " + env

    policies = [*set(policies)]   # remove duplicates
    pbmContent = GetPbmConnection(si._stub)
    pm = pbmContent.profileManager
    profileIds = pm.PbmQueryProfile(resourceType=pbm.profile.ResourceType(
        resourceType="STORAGE"), profileCategory="REQUIREMENT"
    )
    profiles = []
    if len(profileIds) > 0:
        profiles = pm.PbmRetrieveContent(profileIds=profileIds)

    for policy_name in policies:
        for profile in profiles:
            if profile.name == policy_name:
                #current_app.logger.info("Name: %s " % profile.name)
                #current_app.logger.info("ID: %s " % profile.profileId.uniqueId)
                #current_app.logger.info("Description: %s " % profile.description)
                if hasattr(profile.constraints, 'subProfiles'):
                    subprofiles = profile.constraints.subProfiles
                    for subprofile in subprofiles:
                        #current_app.logger.info("RuleSetName: %s " % subprofile.name)
                        capabilities = subprofile.capability
                        if is_encrypted_policy(capabilities, policy_name):
                            return False, policy_name + " is encrypted!"

    return True, "Provided storage policies are not encrypted."


def is_encrypted_policy(capabilities, policy):
    current_app.logger.info("Found below properties for - " + policy)
    for capability in capabilities:
        for constraint in capability.constraint:
            if hasattr(constraint, 'propertyInstance'):
                for propertyInstance in constraint.propertyInstance:
                    try:
                        current_app.logger.info("\tKey: %s Value: %s" % (propertyInstance.id,
                                                                         propertyInstance.value))
                        uuid.UUID(str(propertyInstance.id))
                        return True
                    except ValueError:
                        pass

    return False


def checkWorkloadStoragePolicies(env):
    try:
        namespace_specs = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereNamespaceStorageSpec']

        namespace_policies = []
        not_found_policies = []

        if not namespace_specs:
            namespace_details = fetchNamespaceInfo(env)
            if namespace_details[1] != 200:
                return None, "Storage policies list is empty for Supervisor Namespace"
            else:
                namespace_policies = namespace_details[0].json["STORAGE_POLICIES"]
        else:
            for storage_policy in namespace_specs:
                namespace_policies.append(storage_policy['storagePolicy'])

        allowed_clases = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['allowedStorageClasses']

        default_storage_class = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['defaultStorageClass']

        node_storage_class = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['nodeStorageClass']

        for policy in allowed_clases:
            if policy not in namespace_policies:
                not_found_policies.append("allowedStorageClasses for workload cluster: " +
                                          policy + " not added to supervisor namespace")

        if default_storage_class not in allowed_clases:
            not_found_policies.append("defaultStorageClass for workload cluster: " +
                                      default_storage_class + " not added to allowedStorageClasses")

        if node_storage_class not in allowed_clases:
            not_found_policies.append("nodeStorageClass for workload cluster: " +
                                      node_storage_class + " not added to allowedStorageClasses")

        if not_found_policies:
            return None, not_found_policies
        else:
            return "SUCCESS", "Storage Policy Validation for workload cluster PASSED"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while validating storage policies for workload cluster"


def checkAVIFqdnDNSResolution():
    try:
        env = envCheck()
        env = env[0]
        avi_controller_fqdn_ip_dict = dict()
        dns_server = request.get_json(force=True)['envSpec']['infraComponents']['dnsServersIp']
        if isAviHaEnabled(env):
            if isEnvTkgs_wcp(env):
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-01 Fqdn and IP"
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Fqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-02 Fqdn and IP"
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Fqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-03 Fqdn and IP"
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterFqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterIp']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller Cluster Fqdn and IP"
            elif env == Env.VCD:
                fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']
                ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-01 Fqdn and IP"
                fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController02Fqdn']
                ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController02Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-02 Fqdn and IP"
                fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController03Fqdn']
                ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController03Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-03 Fqdn and IP"
                fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterFqdn']
                ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviClusterIp']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller Cluster Fqdn and IP"
            elif env == Env.VSPHERE or env == Env.VCF:
                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-01 Fqdn and IP"
                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Fqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-02 Fqdn and IP"
                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Fqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-03 Fqdn and IP"
                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviClusterIp']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller Cluster Fqdn and IP"
        else:
            if isEnvTkgs_wcp(env):
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-01 Fqdn and IP"
            elif env == Env.VCD:
                deploy_avi = str(request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['deployAvi'])
                if deploy_avi.lower() == "true":
                    fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']
                    ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Ip']
                else:
                    fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterFqdn']
                    ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterIp']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-01 Fqdn and IP"
            elif env == Env.VSPHERE or env == Env.VCF:
                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Ip']
                if fqdn and ip:
                    avi_controller_fqdn_ip_dict[fqdn] = ip
                else:
                    return False, "Provide NSX ALB Controller node-01 Fqdn and IP"

        if dns_server:
            try:
                with open(r'/opt/vmware/arcas/tools/isharbor.txt', 'r') as file:
                    isharbor_requested = file.read()
                if isharbor_requested.strip("\n").strip("\r").strip() == "true":
                    with open(r'/opt/vmware/arcas/tools/harbor_fqdn.txt', 'r') as file:
                        data = file.read()
                    fqdn = data.strip("\n").strip("\r").strip()
                    main_command = ["ifconfig", "eth0"]
                    sub_command = ["awk", '/inet addr/ {gsub("addr:", "", $2); print $2}']
                    command = grabPipeOutput(main_command, sub_command)
                    avi_controller_fqdn_ip_dict[fqdn] = command[0]
                    requiredChecking = True
                    msg = "FQDN and Ip entries successfully validated on DNS Server"
                else:
                    requiredChecking = False
            except:
                requiredChecking = False
            avi_ip_fqdn_dns_entry = getAviIpFqdnDnsMapping(avi_controller_fqdn_ip_dict, dns_server.split(','))
            if avi_ip_fqdn_dns_entry[1] != 200:
                return False, avi_ip_fqdn_dns_entry[0]
            else:
                if requiredChecking:
                    return True, msg
                else:
                    return True, "NSX ALB FQDN and Ip entries successfully validated on DNS Server"
        else:
            return False, "Please provide Valid DNS Server"

    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while verifying DNS Server and AVI FQDN and IP Resolution"


def validityOfNtpServer(ntp_server):
    try:
        if ntp_server:
            ntp_server = ntp_server.split(',')
            valid_ntp_server = checkNtpServerValidity(ntp_server)
            if valid_ntp_server[1] != 200:
                return False, valid_ntp_server[0]
            else:
                return True, "Successfully checked for valid NTP Server."
        else:
            return False, "Please provide Valid NTP Server"

    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while verifying NTP Server"


def pingCheckTkgsMgmtStartIp():
    try:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterAddress"]
        vc_user = request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoUser"]
        vc_password = decode_from_b64(
            request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        # vCenter = current_app.config['VC_IP']
        # vc_user = current_app.config['VC_USER']
        # vc_password = current_app.config['VC_PASSWORD']
        sess = requests.post("https://" + vCenter + "/rest/com/vmware/cis/session", auth=(vc_user, vc_password),
                             verify=False)
        if sess.status_code != 200:
            return False, "Failed to fetch session ID for vCenter - " + vCenter,
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
            return False, id[0]

        url = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + str(id[0])
        response_csrf = requests.request("GET", url, headers=header, verify=False)

        isRunning = False
        if response_csrf.status_code != 200:
            if response_csrf.status_code == 400:
                if response_csrf.json()["messages"][0]["default_message"] == "Cluster with identifier " + str(
                        id[0]) + " does " \
                                 "not have Workloads enabled.":
                    pass
                else:
                    return False, response_csrf.text
            else:
                return False, response_csrf.text
        else:
            try:
                if response_csrf.json()["config_status"] == "RUNNING":
                    isRunning = True
                else:
                    isRunning = False
                if response_csrf.json()["config_status"] == "ERROR":
                    return False, "WCP is enabled but in ERROR state"
            except:
                isRunning = False

        if isRunning:
            current_app.logger.info("Wcp is already enabled")
            return True, "WCP is already enabled, skipping ping test for  Supervisor control plane VM IPs"
        start_ip = request.get_json(force=True)['tkgsComponentSpec']['tkgsMgmtNetworkSpec']['tkgsMgmtNetworkStartingIp']
        counter = 0
        start = int(ipaddress.IPv4Address(start_ip))
        for i in range(start, int(2 ** 32) + 1):
            ip = str(ipaddress.IPv4Address(i))
            if counter < 5:
                current_app.logger.info("Ping check on: " + ip)
                if ping_test("ping -c 1 " + ip) != 0:
                    counter = counter + 1
                else:
                    return False, "IP address " + ip + " is responding to ping. Please ensure that the IP is unused"
            else:
                current_app.logger.info("All 5 consecutive Supervisor control plane VMs' management network "
                                        "interfaces Ips did not respond to ping.")
                return True, "All 5 consecutive Supervisor control plane VMs' management network interfaces Ips did " \
                             "not respond to ping. "
        return True, "All 5 consecutive Supervisor control plane VMs' management network interfaces Ips did not " \
                     "respond to ping. "
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while pinging Supervisor control plane VMs' management network interfaces Ips"


def pingCheckAviControllerIp():
    try:
        env = envCheck()
        env = env[0]
        govc_client = GovcClient(current_app.config, LocalCmdHelper())
        if isAviHaEnabled(env):
            if isEnvTkgs_wcp(env):
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node01 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node01 IP: " + ip + " is responding to ping."
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Fqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        if ping_test("ping -c 1 " + ip) == 0:
                            current_app.logger.info("NSX ALB Controller Node02 vm not found, verifying with ping test")
                            return False, "NSX ALB Controller node02 IP: " + ip + " is responding to ping."
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Fqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node03 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node03 IP: " + ip + " is responding to ping."
            elif env == Env.VCD:
                fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']
                ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node01 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node01 IP: " + ip + " is responding to ping."

                fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController02Fqdn']
                ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController02Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node02 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node02 IP: " + ip + " is responding to ping."

                fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController03Fqdn']
                ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController03Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node03 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node03 IP: " + ip + " is responding to ping."
            elif env == Env.VSPHERE or env == Env.VCF:
                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node01 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node01 IP: " + ip + " is responding to ping."

                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Fqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node02 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node02 IP: " + ip + " is responding to ping."

                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Fqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node03 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node03 IP: " + ip + " is responding to ping."
        else:
            if isEnvTkgs_wcp(env):
                fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
                ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node01 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node01 IP: " + ip + " is responding to ping."
            elif env == Env.VCD:
                deploy_avi = str(request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['deployAvi'])
                if deploy_avi.lower() == "true":
                    fqdn = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Fqdn']
                    ip = request.get_json(force=True)['envSpec']['aviCtrlDeploySpec']['aviComponentsSpec']['aviController01Ip']
                    if fqdn and ip:
                        if not govc_client.find_vms_by_name(vm_name=fqdn):
                            current_app.logger.info("NSX ALB Controller Node01 vm not found, verifying with ping test")
                            if ping_test("ping -c 1 " + ip) == 0:
                                return False, "NSX ALB Controller node01 IP: " + ip + " is responding to ping."
            elif env == Env.VSPHERE or env == Env.VCF:
                fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
                ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Ip']
                if fqdn and ip:
                    if not govc_client.find_vms_by_name(vm_name=fqdn):
                        current_app.logger.info("NSX ALB Controller Node01 vm not found, verifying with ping test")
                        if ping_test("ping -c 1 " + ip) == 0:
                            return False, "NSX ALB Controller node01 IP: " + ip + " is responding to ping."
        return True, "Ping test successful on AVI Controller IPs"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while pinging AVI Controller IPs"


def veleroPrechecks(env, isShared, isWorkload):
    try:
        current_app.logger.info("checking pre-requisites for data protection")
        if not isEnvTkgs_wcp(env):
            if isWorkload or isEnvTkgs_ns(env):
                current_app.logger.info("checking pre-requisites for workload cluster data protection")
                if checkDataProtectionEnabled(env, "workload"):
                    valid_backup = validate_backup_location(env, "workload")
                    if not valid_backup[0]:
                        current_app.logger.error(valid_backup[1])
                        d = {
                            "responseType": "ERROR",
                            "msg": valid_backup[1],
                            "STATUS_CODE": 500
                        }
                        return jsonify(d), 500
                    current_app.logger.info(valid_backup[1])
                    valid_credential = validate_cluster_credential(env, "workload")
                    if not valid_credential[0]:
                        current_app.logger.error(valid_credential[1])
                        d = {
                            "responseType": "ERROR",
                            "msg": valid_credential[1],
                            "STATUS_CODE": 500
                        }
                        return jsonify(d), 500
                    current_app.logger.info(valid_credential[1])
                else:
                    current_app.logger.info("Data protection not enabled for workload cluster")

            if not isEnvTkgs_ns(env) and isShared:
                current_app.logger.info("checking pre-requisites for shared cluster data protection")
                if checkDataProtectionEnabled(env, "shared"):
                    valid_backup = validate_backup_location(env, "shared")
                    if not valid_backup[0]:
                        current_app.logger.error(valid_backup[1])
                        d = {
                            "responseType": "ERROR",
                            "msg": valid_backup[1],
                            "STATUS_CODE": 500
                        }
                        return jsonify(d), 500
                    current_app.logger.info(valid_backup[1])
                    valid_credential = validate_cluster_credential(env, "shared")
                    if not valid_credential[0]:
                        current_app.logger.error(valid_credential[1])
                        d = {
                            "responseType": "ERROR",
                            "msg": valid_credential[1],
                            "STATUS_CODE": 500
                        }
                        return jsonify(d), 500
                    current_app.logger.info(valid_credential[1])
                else:
                    current_app.logger.info("Data protection not enabled for shared cluster")
        else:
            current_app.logger.info("skipping data protection pre-checks for WCP")

        d = {
            "responseType": "SUCCESS",
            "msg": "Data protection prerequisites validated successfully",
            "STATUS_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while validating data protection prerequisites",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


def licensePrechecks(env):
    try:
        current_app.logger.info("Checking License Expiration status")
        current_app.logger.info("Logging into vCenter API with supplied credentials ")
        if env == Env.VSPHERE or env == Env.VCF:
            vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
            vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
        elif env == Env.VMC:
            vCenter = current_app.config['VC_IP']
            vCenter_user = current_app.config['VC_USER']
            VC_PASSWORD = current_app.config['VC_PASSWORD']
        else:
            current_app.logger.error("ERROR: Unsupported env type provided")
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Unsupported env type provided",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        vc_service_instance = get_si(vCenter, vCenter_user, VC_PASSWORD)
        if not vc_service_instance[1]:
            current_app.logger.error("Failed to retrieve Service Instance from the provided vCenter details")
            current_app.logger.debug(vc_service_instance[0])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to retrieve Service Instance from the provided vCenter details",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        vc_service_instance = vc_service_instance[0]
        atexit.register(Disconnect, vc_service_instance)
        content = vc_service_instance.RetrieveContent()
        licenseAssignmentManager = content.licenseManager.licenseAssignmentManager
        assignedLicenses = licenseAssignmentManager.QueryAssignedLicenses()
        if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
            tanzu_license_status = check_tanzu_license(assignedLicenses)
            if not tanzu_license_status[1]:
                current_app.logger.error("ERROR: Got error while validating Tanzu Standard License Expiration")
                current_app.logger.error(tanzu_license_status[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "ERROR: Got error while validating Tanzu Standard License Expiration",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Tanzu Standard license expiration is successfully validated")
            current_app.logger.info("Tanzu Standard license will expire at: " + tanzu_license_status[0])
        if env == Env.VCF:
            nsxt_license_status = check_nsxt_license(assignedLicenses)
            if not nsxt_license_status[1]:
                current_app.logger.error("ERROR: Got error while validating NSXT License Expiration")
                current_app.logger.error(nsxt_license_status[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "ERROR: Got error while validating NSXT License Expiration",
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("NSXT license expiration is successfully validated")
            current_app.logger.info("NSXT license will expire at: " + nsxt_license_status[0])
        vsphere_license_status = check_vsphere_license(assignedLicenses)
        if not vsphere_license_status[1]:
            current_app.logger.error("ERROR: Got error while validating vSphere License Expiration")
            current_app.logger.error(vsphere_license_status[0])
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Got error while validating vSphere License Expiration",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("vCenter Server license expiration is successfully validated")
        current_app.logger.info("vCenter Server license will expire at: " + vsphere_license_status[0])
        d = {

            "responseType": "SUCCESS",
            "msg": "Licenses validated successfully",
            "STATUS_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while validating license expiration",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


def get_si(host, user, password):
    # PyVMomi work to get all VMs on VC
    try:
        service_instance = None
        # TODO UPDATE PORT Number here, used 443 hardcoded
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.verify_mode = ssl.CERT_NONE
        service_instance = SmartConnect(host=host, user=user, pwd=password, port=int('443'), sslContext=context)

        if not service_instance:
            current_app.logger.error("Could not connect to the specified vCenter host using specified username "
                                     "and password")
            return None, False
        else:
            return service_instance, True
    except Exception as e:
        current_app.logger.error("Exception occured while connecting to specified vCenter host")
        current_app.logger.debug(str(e))
        return str(e), False


# @vcenter_precheck.route("/api/tanzu/verifyLdapConnect", methods=['POST'])
# def verify_ldap_connect():
#     env = envCheck()
#     if env[1] != 200:
#         current_app.logger.error("Wrong env provided " + env[0])
#         d = {
#             "responseType": "ERROR",
#             "msg": "Wrong env provided " + env[0],
#             "STATUS_CODE": 500
#         }
#         return jsonify(d), 500
#     env = env[0]
#     ldap_obj = Ldap()
#     ldap_connect_status = ldap_operation(ldap_obj, 'CONNECT', env, isbinded=False)
#     if ldap_connect_status[0]:
#         current_app.logger.info("Successfully connected to LDAP Server")
#         d = {
#             'responseType': 'SUCCESS',
#             'msg': ldap_connect_status[1],
#             'STATUS_CODE': 200
#         }
#         return jsonify(d), 200
#     else:
#         current_app.logger.error("Failed to connect to LDAP Server")
#         d = {
#             'responseType': 'ERROR',
#             'msg': ldap_connect_status[1],
#             'STATUS_CODE': 500
#         }
#         return jsonify(d), 500


# @vcenter_precheck.route("/api/tanzu/verifyLdapBind", methods=['POST'])
# def verify_ldap_bind():
#     env = envCheck()
#     if env[1] != 200:
#         current_app.logger.error("Wrong env provided " + env[0])
#         d = {
#             "responseType": "ERROR",
#             "msg": "Wrong env provided " + env[0],
#             "STATUS_CODE": 500
#         }
#         return jsonify(d), 500
#     env = env[0]
#     ldap_obj = Ldap()
#     ldap_bind_status = ldap_operation(ldap_obj, 'BIND', env, isbinded=False)
#     if ldap_bind_status[0]:
#         current_app.logger.info("Successfully connected to LDAP Server")
#         d = {
#             'responseType': 'SUCCESS',
#             'msg': ldap_bind_status[1],
#             'STATUS_CODE': 200
#         }
#         return jsonify(d), 200
#     else:
#         current_app.logger.error("Failed to connect to LDAP Server")
#         d = {
#             'responseType': 'ERROR',
#             'msg': ldap_bind_status[1],
#             'STATUS_CODE': 500
#         }
#         return jsonify(d), 500


# @vcenter_precheck.route("/api/tanzu/verifyLdapUserSearch", methods=['POST'])
# def verify_ldap_user_search():
#     env = envCheck()
#     if env[1] != 200:
#         current_app.logger.error("Wrong env provided " + env[0])
#         d = {
#             "responseType": "ERROR",
#             "msg": "Wrong env provided " + env[0],
#             "STATUS_CODE": 500
#         }
#         return jsonify(d), 500
#     env = env[0]
#     ldap_obj = Ldap()
#     ldap_user_search_status = ldap_operation(ldap_obj, 'USER_SEARCH', env, isbinded=False)
#     if ldap_user_search_status[0]:
#         current_app.logger.info("Successfully connected to LDAP Server")
#         d = {
#             'responseType': 'SUCCESS',
#             'msg': ldap_user_search_status[1],
#             'STATUS_CODE': 200
#         }
#         return jsonify(d), 200
#     else:
#         current_app.logger.error("Failed to connect to LDAP Server")
#         d = {
#             'responseType': 'ERROR',
#             'msg': ldap_user_search_status[1],
#             'STATUS_CODE': 500
#         }
#         return jsonify(d), 500


# @vcenter_precheck.route("/api/tanzu/verifyLdapGroupSearch", methods=['POST'])
# def verify_ldap_group_search():
#     env = envCheck()
#     if env[1] != 200:
#         current_app.logger.error("Wrong env provided " + env[0])
#         d = {
#             "responseType": "ERROR",
#             "msg": "Wrong env provided " + env[0],
#             "STATUS_CODE": 500
#         }
#         return jsonify(d), 500
#     env = env[0]
#     ldap_obj = Ldap()
#     ldap_group_search_status = ldap_operation(ldap_obj, 'GROUP_SEARCH', env, isbinded=False)
#     if ldap_group_search_status[0]:
#         current_app.logger.info("Successfully connected to LDAP Server")
#         d = {
#             'responseType': 'SUCCESS',
#             'msg': ldap_group_search_status[1],
#             'STATUS_CODE': 200
#         }
#         return jsonify(d), 200
#     else:
#         current_app.logger.error("Failed to connect to LDAP Server")
#         d = {
#             'responseType': 'ERROR',
#             'msg': ldap_group_search_status[1],
#             'STATUS_CODE': 500
#         }
#         return jsonify(d), 500


# @vcenter_precheck.route("/api/tanzu/verifyLdapCloseConnection", methods=['POST'])
# def verify_ldap_close_connection():
#     env = envCheck()
#     if env[1] != 200:
#         current_app.logger.error("Wrong env provided " + env[0])
#         d = {
#             "responseType": "ERROR",
#             "msg": "Wrong env provided " + env[0],
#             "STATUS_CODE": 500
#         }
#         return jsonify(d), 500
#     env = env[0]
#     ldap_obj = Ldap()
#     ldap_close_connection_status = ldap_operation(ldap_obj, 'DISCONNECT', env, isbinded=False)
#     if ldap_close_connection_status[0]:
#         current_app.logger.info("Successfully connected to LDAP Server")
#         d = {
#             'responseType': 'SUCCESS',
#             'msg': ldap_close_connection_status[1],
#             'STATUS_CODE': 200
#         }
#         return jsonify(d), 200
#     else:
#         current_app.logger.error("Failed to connect to LDAP Server")
#         d = {
#             'responseType': 'ERROR',
#             'msg': ldap_close_connection_status[1],
#             'STATUS_CODE': 500
#         }
#         return jsonify(d), 500
