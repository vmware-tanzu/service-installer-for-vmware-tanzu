# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import shlex
import socket
import ssl
import struct
import time
from pathlib import Path
from time import ctime

import ntplib

# import OpenSSL
import requests
import ruamel
import yaml
from flask import current_app, jsonify, request
from pyVim import connect
from pyVmomi import vim
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.certificate_base64 import getBase64CertWriteToFile, repoAdd
from common.constants.tmc_api_constants import TmcConstants
from common.lib.avi.avi_template_operations import AVITemplateOperations
from common.operation.constants import (
    PLAN,
    VCF,
    AppName,
    Avi_Version,
    AviSize,
    CertName,
    ControllerLocation,
    Env,
    EnvType,
    Extension,
    KubernetesOva,
    MarketPlaceUrl,
    Paths,
    RegexPattern,
    ServiceName,
    Tkg_Extension_names,
    Tkg_version,
    Versions,
    VrfType,
)
from common.operation.ShellHelper import (
    grabKubectlCommand,
    grabPipeOutput,
    grabPipeOutputChagedDir,
    runProcess,
    runShellCommandAndReturnOutput,
    runShellCommandAndReturnOutputAsList,
    runShellCommandAndReturnOutputAsListWithChangedDir,
    runShellCommandWithPolling,
    verifyPodsAreRunning,
)
from common.operation.vcenter_operations import create_folder, createResourcePool
from common.replace_value import (
    generateVsphereConfiguredSubnets,
    generateVsphereConfiguredSubnetsForSe,
    generateVsphereConfiguredSubnetsForSeandVIP,
)
from common.util.file_helper import FileHelper
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.request_api_util import RequestApiUtil
from common.util.tanzu_util import TanzuUtil

from .constants.alb_api_constants import AlbEndpoint, AlbPayload
from .lib.govc_client import GovcClient
from .replace_value import replaceCertConfig, replaceValueSysConfig

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

TKGS_PROXY_CREDENTIAL_NAME = "sivt_credential"


def envCheck():
    try:
        env = request.headers["Env"]
    except Exception:
        current_app.logger.error("No env header passed")
        return "NO_ENV", 400
    if env is None:
        return "NO_ENV", 400
    if env == Env.VMC:
        pass
    elif env == Env.VSPHERE:
        pass
    elif env == Env.VCF:
        pass
    elif env == Env.VCD:
        pass
    else:
        return "WRONG_ENV", 500
    return env, 200


def preChecks():
    _env = envCheck()
    if _env[1] != 200:
        d = {
            "responseType": "ERROR",
            "msg": "Wrong env type provided " + _env[0] + " please specify vmc or vsphere",
            "STATUS_CODE": 500,
        }
        current_app.logger.error("Wrong env type provided " + _env[0] + " please specify vmc or vsphere")
        return jsonify(d), 500
    env = _env[0]
    if env == Env.VSPHERE or env == Env.VCF:
        try:
            if current_app.config["VC_PASSWORD"] is None:
                current_app.logger.info("Vc password")
            if current_app.config["VC_USER"] is None:
                current_app.logger.info("Vc user password")
            if current_app.config["VC_IP"] is None:
                current_app.logger.info("Vc ip")
            if current_app.config["VC_CLUSTER"] is None:
                current_app.logger.info("Vc Cluster")
            if current_app.config["VC_DATACENTER"] is None:
                current_app.logger.info("Vc Datacenter")
            if not isEnvTkgs_ns(env):
                if current_app.config["VC_DATASTORE"] is None:
                    current_app.logger.info("VC datastore")
        except Exception as e:
            d = {"responseType": "ERROR", "msg": "Un-Authorized " + str(e), "STATUS_CODE": 401}
            return jsonify(d), 401
    else:
        try:
            if current_app.config["access_token"] is None:
                current_app.logger.info("Access token not found")
            if current_app.config["ORG_ID"] is None:
                current_app.logger.info("ORG_ID not found")
            if current_app.config["SDDC_ID"] is None:
                current_app.logger.info("SDDC_ID not found")
            if current_app.config["NSX_REVERSE_PROXY_URL"] is None:
                current_app.logger.info("NSX_REVERSE_PROXY_URL not found")
            if current_app.config["VC_IP"] is None:
                current_app.logger.info("Vc ip not found")
            if current_app.config["VC_PASSWORD"] is None:
                current_app.logger.info("Vc cred not found")
            if current_app.config["VC_USER"] is None:
                current_app.logger.info("Vc user not found")
            if current_app.config["VC_CLUSTER"] is None:
                current_app.logger.info("Vc Cluster")
            if current_app.config["VC_DATACENTER"] is None:
                current_app.logger.info("Vc Datacenter")
            if current_app.config["VC_DATASTORE"] is None:
                current_app.logger.info("VC datastore")
        except Exception as e:
            d = {"responseType": "ERROR", "msg": f"Un-Authorized {e}", "STATUS_CODE": "401"}
            return jsonify(d), 401
    d = {"responseType": "SUCCESS", "msg": "Authorized", "STATUS_CODE": 200}
    return jsonify(d), 200


def createResourceFolderAndWait(
    vcenter_ip, vcenter_username, password, cluster_name, data_center, resourcePoolName, folderName, parentResourcePool
):
    try:
        isCreated4 = createResourcePool(
            vcenter_ip, vcenter_username, password, cluster_name, resourcePoolName, parentResourcePool, data_center
        )
        if isCreated4 is not None:
            current_app.logger.info("Created resource pool" + resourcePoolName)
    except Exception as e:
        current_app.logger.error("Failed to create resource pool " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create resource pool " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500

    try:
        isCreated1 = create_folder(vcenter_ip, vcenter_username, password, data_center, folderName)
        if isCreated1 is not None:
            current_app.logger.info("Created folder " + folderName)

    except Exception as e:
        current_app.logger.error("Failed to create folder " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create folder " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
    find = validateFolderAndResourcesAvailable(
        folderName, resourcePoolName, vcenter_ip, vcenter_username, password, parentResourcePool
    )
    if not find:
        # current_app.logger.error("Failed to find folder and resources")
        errorMsg = (
            "Failed to create resource pool "
            + resourcePoolName
            + ". Please check if "
            + resourcePoolName
            + " is already present in "
            + cluster_name
            + " and delete it before initiating deployment"
        )
        current_app.logger.error(errorMsg)
        d = {"responseType": "ERROR", "msg": errorMsg, "STATUS_CODE": 500}
        return jsonify(d), 500
    d = {"responseType": "ERROR", "msg": "Created resources and  folder", "STATUS_CODE": 200}
    return jsonify(d), 200


def validateFolderAndResourcesAvailable(folder, resources, vcenter_ip, vcenter_username, password, parent_resourcepool):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    find_command = ["govc", "find", "-name", folder]
    count = 0
    while count < 120:
        output = runShellCommandAndReturnOutputAsList(find_command)
        if parent_resourcepool:
            if str(output[0]).__contains__("/Resources/" + parent_resourcepool + "/" + resources) and str(
                output[0]
            ).__contains__("/vm/" + folder):
                current_app.logger.info("Folder and resources are available")
                return True
        else:
            if str(output[0]).__contains__("/Resources/" + resources) and str(output[0]).__contains__("/vm/" + folder):
                current_app.logger.info("Folder and resources are available")
                return True
        time.sleep(5)
        count = count + 1
    return False


def validateNetworkAvailable(netWorkName, vcenter_ip, vcenter_username, password):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    find_command = ["govc", "find", "-name", netWorkName]
    count = 0
    while count < 120:
        output = runShellCommandAndReturnOutputAsList(find_command)
        if str(output[0]).__contains__("/network/" + netWorkName):
            current_app.logger.info("Network is available")
            return True
        time.sleep(5)
        count = count + 1
    return False


def deployAndConfigureAvi(
    govc_client: GovcClient, vm_name, controller_ova_location, deploy_options, performOtherTask, env, avi_version, spec
):
    try:
        data_center = current_app.config["VC_DATACENTER"]
        data_center = data_center.replace(" ", "#remove_me#")

        deploy_new_controller = False
        fetched_ip = govc_client.get_vm_ip(vm_name, datacenter_name=data_center)
        if fetched_ip is None:
            deploy_new_controller = True
        else:
            current_app.logger.info("Received IP: " + fetched_ip[0] + " for VM: " + vm_name)
            current_app.logger.info("Checking if controller with IP : " + fetched_ip[0] + " is already UP")
            check_controller_up = check_controller_is_up(fetched_ip[0], only_check=True)
            if check_controller_up is None:
                current_app.logger.error(
                    "Controller with IP: " + fetched_ip[0] + " is not UP, recommended to cleanup"
                    " or use a different FQDN for the "
                    "controller VM"
                )
                d = {"responseType": "ERROR", "msg": "Controller is already deployed but is not UP", "STATUS_CODE": 500}
                return jsonify(d), 500
            else:
                deploy_new_controller = False
                current_app.logger.info("Controller is already deployed and is UP and Running")

        if deploy_new_controller:
            current_app.logger.info("Deploying AVI controller..")
            govc_client.deploy_library_ova(location=controller_ova_location, name=vm_name, options=deploy_options)
            if env == Env.VMC:
                avi_size = request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviSize"]
            elif isEnvTkgs_wcp(env):
                avi_size = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviSize"]
            else:
                avi_size = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviSize"]
            size = str(avi_size).lower()
            if size not in ["essentials", "small", "medium", "large"]:
                current_app.logger.error("Wrong AVI size provided, supported essentials/small/medium/large " + avi_size)
                d = {
                    "responseType": "ERROR",
                    "msg": "Wrong avi size provided, supported essentials/small/medium/large " + avi_size,
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            if size == "essentials":
                cpu = AviSize.ESSENTIALS["cpu"]
                memory = AviSize.ESSENTIALS["memory"]
            elif size == "small":
                cpu = AviSize.SMALL["cpu"]
                memory = AviSize.SMALL["memory"]
            elif size == "medium":
                cpu = AviSize.MEDIUM["cpu"]
                memory = AviSize.MEDIUM["memory"]
            elif size == "large":
                cpu = AviSize.LARGE["cpu"]
                memory = AviSize.LARGE["memory"]
            change_VM_config = [
                "govc",
                "vm.change",
                "-dc=" + data_center.replace("#remove_me#", " "),
                "-vm=" + vm_name,
                "-c=" + cpu,
                "-m=" + memory,
            ]
            power_on = ["govc", "vm.power", "-dc=" + data_center.replace("#remove_me#", " "), "-on=true", vm_name]
            runProcess(change_VM_config)
            runProcess(power_on)
            ip = govc_client.get_vm_ip(vm_name, datacenter_name=data_center, wait_time="30m")
            if ip is None:
                current_app.logger.error("Failed to get IP of AVI controller on waiting 30m")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get IP of AVI controller on waiting 30m",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
    except Exception as e:
        current_app.logger.error("Failed to deploy the VM from library due to " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy the VM from library due to " + str(e),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500

    ip = govc_client.get_vm_ip(vm_name, datacenter_name=data_center)[0]
    current_app.logger.info("Checking controller is up")
    if check_controller_is_up(ip) is None:
        current_app.logger.error("Controller service is not up")
        d = {"responseType": "ERROR", "msg": "Controller service is not up", "STATUS_CODE": 500}
        return jsonify(d), 500
    deployed_avi_version = obtain_avi_version(ip, env)
    if deployed_avi_version[0] is None:
        current_app.logger.error("Failed to login and obtain AVI version" + str(deployed_avi_version[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to login and obtain AVI version " + deployed_avi_version[1],
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    avi_version = deployed_avi_version[0]
    if env == Env.VMC:
        avi_required = Avi_Version.VMC_AVI_VERSION
    elif isEnvTkgs_wcp(env) and verifyVcenterVersion(Versions.VCENTER_UPDATE_THREE):
        avi_required = Avi_Version.AVI_VERSION_UPDATE_THREE
    elif isEnvTkgs_wcp(env) and not verifyVcenterVersion(Versions.VCENTER_UPDATE_THREE):
        avi_required = Avi_Version.AVI_VERSION_UPDATE_TWO
    else:
        avi_required = Avi_Version.VSPHERE_AVI_VERSION
    if str(avi_version) != avi_required:
        d = {
            "responseType": "ERROR",
            "msg": "Deployed avi version "
            + str(avi_version)
            + " is not supported, supported version is: "
            + avi_required,
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    if performOtherTask:
        csrf = obtain_first_csrf(ip)
        if csrf is None:
            current_app.logger.error("Failed to get First csrf value.")
            d = {"responseType": "ERROR", "msg": "Failed to get First csrf", "STATUS_CODE": 500}
            return jsonify(d), 500
        if csrf == "SUCCESS":
            current_app.logger.info("Password of appliance already changed")
        else:
            if set_avi_admin_password(ip, csrf, avi_version, env) is None:
                current_app.logger.error("Failed to set the AVI admin password")
                d = {"responseType": "ERROR", "msg": "Failed to set the avi admin password", "STATUS_CODE": 500}
                return jsonify(d), 500
        csrf2 = obtain_second_csrf(ip, env)
        if csrf2 is None:
            current_app.logger.error("Failed to get csrf from new set password")
            d = {"responseType": "ERROR", "msg": "Failed to get csrf from new set password", "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            current_app.logger.info("Obtained csrf with new credential successfully")
        if get_system_configuration_and_set_values(ip, csrf2, avi_version, env, spec) is None:
            current_app.logger.error("Failed to set the system configuration")
            d = {"responseType": "ERROR", "msg": "Failed to set the system configuration", "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            current_app.logger.info("Fetched system configuration successfully")
        if set_dns_ntp_smtp_settings(ip, csrf2, avi_version) is None:
            current_app.logger.error("Set DNS NTP SMTP failed.")
            d = {"responseType": "ERROR", "msg": "Set DNS NTP SMTP failed.", "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            current_app.logger.info("Set DNS NTP SMTP successfully")
        if disable_welcome_screen(ip, csrf2, avi_version, env) is None:
            current_app.logger.error("Failed to deactivate welcome screen")
            d = {"responseType": "ERROR", "msg": "Failed to deactivate welcome screen", "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            current_app.logger.info("Deactivate welcome screen successfully")
        backup_url = get_backup_configuration(ip, csrf2, avi_version)
        if backup_url[0] is None:
            current_app.logger.error("Failed to get backup configuration")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get backup configuration " + backup_url[1],
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Fetched backup configuration successfully")
        current_app.logger.info("Set backup pass phrase")
        setBackup = setBackupPhrase(ip, csrf2, backup_url[0], avi_version, env)
        if setBackup[0] is None:
            current_app.logger.error("Failed to set backup pass phrase")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to set backup pass phrase " + str(setBackup[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Configured AVI", "STATUS_CODE": 200}
    return jsonify(d), 200


def get_avi_version(env):
    if env == Env.VMC:
        version = Avi_Version.VMC_AVI_VERSION
    else:
        version = Avi_Version.VSPHERE_AVI_VERSION
    return version


def changeSeGroupAndSetInterfaces(ip, csrf2, urlFromServiceEngine, aviVersion):
    url = urlFromServiceEngine
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    with open("./detailsOfServiceEngine1.json", "r") as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False, timeout=600)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), 200


def get_avi_cluster_info(ip, csrf2, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    url = AlbEndpoint.AVI_HA.format(ip=ip)
    try:
        response_csrf = requests.request("GET", url, headers=headers, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        return response_csrf.json(), "SUCCESS"
    except Exception as e:
        return None, str(e)


def form_avi_ha_cluster(ip, env, govc_client, aviVersion):
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        return None, "Failed to get csrf from new set password"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }

    try:
        data_center = current_app.config["VC_DATACENTER"]
        info, status = get_avi_cluster_info(ip, csrf2, aviVersion)
        if info is None:
            return None, "Failed to get cluster info " + str(status)
        if isEnvTkgs_wcp(env):
            avi_ip = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController01Ip"]
            avi_ip2 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController02Ip"]
            avi_ip3 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController03Ip"]
            clusterIp = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviClusterIp"]
        elif env == Env.VMC:
            avi_ip = ip
            avi_ip2 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME2, datacenter_name=data_center)[0]
            if avi_ip2 is None:
                return None, "Failed to get 2nd controller ip"
            avi_ip3 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME3, datacenter_name=data_center)[0]
            if avi_ip3 is None:
                return None, "Failed to get 3rd controller ip"
            clusterIp = request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviClusterIp"]
        else:
            avi_ip = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Ip"]
            avi_ip2 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController02Ip"]
            avi_ip3 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController03Ip"]
            clusterIp = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviClusterIp"]
        nodes = info["nodes"]
        _list = []
        _cluster = {}
        for node in nodes:
            try:
                _list.append(node["ip"]["addr"])
                if str(node["ip"]["addr"]) == avi_ip:
                    _cluster["vm_uuid"] = node["vm_uuid"]
                    _cluster["vm_mor"] = node["vm_mor"]
                    _cluster["vm_hostname"] = node["vm_hostname"]
            except Exception:
                pass
        if avi_ip in _list and avi_ip2 in _list and avi_ip3 in _list:
            current_app.logger.info("AVI HA cluster is already configured")
            return "SUCCESS", "Avi HA cluster is already configured"
        current_app.logger.info("Forming Ha cluster")
        payload = AlbPayload.AVI_HA_CLUSTER.format(
            cluster_uuid=info["uuid"],
            cluster_name="Alb-Cluster",
            cluster_ip1=avi_ip,
            vm_uuid_get=_cluster["vm_uuid"],
            vm_mor_get=_cluster["vm_mor"],
            vm_hostname_get=_cluster["vm_hostname"],
            cluster_ip2=avi_ip2,
            cluster_ip3=avi_ip3,
            tennat_uuid_get=info["tenant_uuid"],
            virtual_ip_get=clusterIp,
        )
        url = AlbEndpoint.AVI_HA.format(ip=ip)
        response_csrf = requests.request("PUT", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        count = 0
        list_of_nodes = []
        while count < 180:
            try:
                response_csrf = requests.request("GET", url, headers=headers, verify=False)
                if len(response_csrf.json()["nodes"]) == 3:
                    for node in response_csrf.json()["nodes"]:
                        list_of_nodes.append(node["ip"]["addr"])
                    break
            except Exception:
                pass
            time.sleep(10)
            current_app.logger.info("Waited " + str(count * 10) + "s for getting cluster ips, retrying")
            count = count + 1

        # if avi_ip not in list_of_nodes or avi_ip2 not in list_of_nodes or not avi_ip3 in list_of_nodes:
        if avi_ip and avi_ip2 and avi_ip3 in list_of_nodes:
            current_app.logger.info("Avi IPs avilable")
        else:
            return None, "Failed to form the cluster ips not found in nodes list"
        current_app.logger.info("Getting cluster runtime status")
        runtime = 0
        run_time_url = AlbEndpoint.AVI_HA_RUNTIME.format(ip=ip)
        all_up = False
        while runtime < 180:
            try:
                response_csrf = requests.request("GET", run_time_url, headers=headers, verify=False)
                if response_csrf.status_code != 200:
                    return None, "Failed to get cluster runtime status " + (str(response_csrf.text))
                node_statuses = response_csrf.json()["node_states"]
                if node_statuses is not None:
                    current_app.logger.info(
                        "Checking node "
                        + str(node_statuses[0]["mgmt_ip"])
                        + " state: "
                        + str(node_statuses[0]["state"])
                    )
                    current_app.logger.info(
                        "Checking node "
                        + str(node_statuses[1]["mgmt_ip"])
                        + " state: "
                        + str(node_statuses[1]["state"])
                    )
                    current_app.logger.info(
                        "Checking node "
                        + str(node_statuses[2]["mgmt_ip"])
                        + " state: "
                        + str(node_statuses[2]["state"])
                    )
                    current_app.logger.info(
                        "***********************************************************************************"
                    )
                    if (
                        node_statuses[0]["state"] == "CLUSTER_ACTIVE"
                        and node_statuses[1]["state"] == "CLUSTER_ACTIVE"
                        and node_statuses[2]["state"] == "CLUSTER_ACTIVE"
                    ):
                        all_up = True
                        break
            except Exception:
                pass
            runtime = runtime + 1
            time.sleep(10)
        if not all_up:
            return None, "All nodes are not in active state on waiting 30 min"
        return "SUCCESS", "Successfully formed Ha Cluster"
    except Exception as e:
        return None, str(e)


def get_ssl_certificate_status(ip, csrf2, name, aviVersion):
    body = {}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    url = "https://" + ip + "/api/sslkeyandcertificate"
    json_object = json.dumps(body, indent=4)
    response_csrf = requests.request("GET", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for res in response_csrf.json()["results"]:
            if res["name"] == name:
                return res["url"], "SUCCESS"
        return "NOT_FOUND", "SUCCESS"


def import_ssl_certificate(ip, csrf2, certificate, certificate_key, env, avi_version):
    body = AlbPayload.IMPORT_CERT.format(cert=certificate, cert_key=certificate_key)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0],
    }
    if env == Env.VMC:
        certName = CertName.NAME
    else:
        certName = CertName.VSPHERE_CERT_NAME
    url = AlbEndpoint.IMPORT_SSL_CERTIFICATE.format(ip=ip)
    response_csrf = requests.request("POST", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        output = response_csrf.json()
        dic = {}
        dic["issuer_common_name"] = output["certificate"]["issuer"]["common_name"]
        dic["issuer_distinguished_name"] = output["certificate"]["issuer"]["distinguished_name"]
        dic["subject_common_name"] = output["certificate"]["subject"]["common_name"]
        dic["subject_organization_unit"] = output["certificate"]["subject"]["organization_unit"]
        dic["subject_organization"] = output["certificate"]["subject"]["organization"]
        dic["subject_locality"] = output["certificate"]["subject"]["locality"]
        dic["subject_state"] = output["certificate"]["subject"]["state"]
        dic["subject_country"] = output["certificate"]["subject"]["country"]
        dic["subject_distinguished_name"] = output["certificate"]["subject"]["distinguished_name"]
        dic["not_after"] = output["certificate"]["not_after"]
        dic["cert_name"] = certName
        return dic, "SUCCESS"


def create_imported_ssl_certificate(ip, csrf2, dic, cer, key, env, avi_version):
    if env == Env.VMC:
        certName = CertName.NAME
    else:
        certName = CertName.VSPHERE_CERT_NAME
    body = AlbPayload.IMPORTED_CERTIFICATE.format(
        cert=cer,
        subject_common_name=dic["subject_common_name"],
        org_unit=dic["subject_organization_unit"],
        org=dic["subject_organization"],
        location=dic["subject_locality"],
        state_name=dic["subject_state"],
        country_name=dic["subject_country"],
        distinguished_name=dic["subject_distinguished_name"],
        not_after_time=dic["not_after"],
        cert_name=certName,
        cert_key=key,
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0],
    }
    url = AlbEndpoint.CRUD_SSL_CERT.format(ip=ip)
    response_csrf = requests.request("POST", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def generate_ssl_certificate(ip, csrf2, avi_version):
    ips = [ip]
    data_center = current_app.config["VC_DATACENTER"]
    if isAviHaEnabled(Env.VMC):
        govc_client = GovcClient(current_app.config, LocalCmdHelper())
        avi_ip2 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME2, datacenter_name=data_center)
        if avi_ip2 is None:
            return None, "Failed to get 2nd controller ip"
        avi_ip3 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME3, datacenter_name=data_center)
        if avi_ip3 is None:
            return None, "Failed to get 3rd controller ip"
        clusterIp = request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviClusterIp"]
        ips.append(avi_ip2)
        ips.append(avi_ip3)
        ips.append(clusterIp)
    san = json.dumps(ips)
    body = AlbPayload.SELF_SIGNED_CERT.format(name=CertName.NAME, common_name=CertName.COMMON_NAME, san_list=san)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0],
    }
    url = AlbEndpoint.CRUD_SSL_CERT.format(ip=ip)
    response_csrf = requests.request("POST", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def generate_ssl_certificate_vsphere(ip, csrf2, avi_fqdn, avi_version):
    common_name = avi_fqdn
    ips = [str(ip), common_name]
    if isAviHaEnabled(Env.VSPHERE) or isAviHaEnabled(Env.VCF):
        if isEnvTkgs_wcp(Env.VSPHERE):
            avi_fqdn2 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController02Fqdn"]
            avi_ip2 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController02Ip"]
            avi_fqdn3 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController03Fqdn"]
            avi_ip3 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController03Ip"]
            clusterIp = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviClusterIp"]
            cluster_fqdn = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviClusterFqdn"]
        else:
            avi_fqdn2 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController02Fqdn"]
            avi_ip2 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController02Ip"]
            avi_fqdn3 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController03Fqdn"]
            avi_ip3 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController03Ip"]
            clusterIp = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviClusterIp"]
            cluster_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviClusterFqdn"]
        ips.append(avi_ip2)
        ips.append(avi_fqdn2)
        ips.append(avi_ip3)
        ips.append(avi_fqdn3)
        ips.append(clusterIp)
        ips.append(cluster_fqdn)
        common_name = cluster_fqdn
    san = json.dumps(ips)
    body = AlbPayload.SELF_SIGNED_CERT.format(name=CertName.VSPHERE_CERT_NAME, common_name=common_name, san_list=san)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0],
    }
    url = AlbEndpoint.CRUD_SSL_CERT.format(ip=ip)
    response_csrf = requests.request("POST", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def get_current_cert_config(ip, csrf2, generated_ssl_url, avi_version):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        os.system("rm -rf systemConfig.json")
        with open("./systemConfig.json", "w") as outfile:
            outfile.write(json_object)
        replaceCertConfig("systemConfig.json", "portal_configuration", "sslkeyandcertificate_refs", generated_ssl_url)
        return response_csrf.json()["url"], "SUCCESS"


def replaceWithNewCert(ip, csrf2, aviVersion):
    with open("./systemConfig.json", "r") as file2:
        json_object = json.load(file2)

    json_object_mo = json.dumps(json_object, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    url = "https://" + ip + "/api/systemconfiguration/?include_name="
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_mo, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return "SUCCESS", 200


def setBackupPhrase(ip, seconcsrf, url_backup, aviVersion, env):
    url = url_backup
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": seconcsrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": seconcsrf[0],
    }
    if env == Env.VMC:
        str_enc_avi_backup = str(
            request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviBackupPassPhraseBase64"]
        )
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi_backup = str(
                request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviBackupPassphraseBase64"]
            )
        else:
            str_enc_avi_backup = str(
                request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviBackupPassphraseBase64"]
            )
    base64_bytes_avi_backup = str_enc_avi_backup.encode("ascii")
    enc_bytes_avi_backup = base64.b64decode(base64_bytes_avi_backup)
    password_avi_backup = enc_bytes_avi_backup.decode("ascii").rstrip("\n")
    body = {"add": {"backup_passphrase": password_avi_backup}}
    json_object = json.dumps(body, indent=4)
    response_csrf = requests.request("PATCH", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], 200


def get_backup_configuration(ip, second_csrf, avi_version):
    url = "https://" + ip + "/api/backupconfiguration"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": second_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": second_csrf[0],
    }
    body = {}
    json_object = json.dumps(body, indent=4)
    response_csrf = requests.request("GET", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json()["results"][0]["url"], 200


def disable_welcome_screen(ip, second_csrf, avi_version, env):
    url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": second_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": second_csrf[0],
    }
    body = AlbPayload.WELCOME_SCREEN_UPDATE.format(tenant_vrf=json.dumps(env == Env.VMC))
    response_csrf = requests.request("PATCH", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None
    else:
        return "SUCCESS"


def set_dns_ntp_smtp_settings(ip, second_csrf, avi_version):
    with open("./systemConfig1.json", "r") as openfile:
        json_object = json.load(openfile)
    url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": second_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": second_csrf[0],
    }
    json_object_m = json.dumps(json_object, indent=4)
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        return None
    else:
        return "SUCCESS"


def get_system_configuration_and_set_values(ip, second_csrf, avi_version, env, spec):
    from common.util.common_utils import CommonUtils

    url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": second_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": second_csrf[0],
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None
    os.system("rm -rf ./systemConfig1.json")
    json_object = json.dumps(response_csrf.json(), indent=4)
    if env == Env.VMC:
        ntp = request.get_json(force=True)["envVariablesSpec"]["ntpServersIp"]
        dns = request.get_json(force=True)["envVariablesSpec"]["dnsServersIp"]
        search_domain = request.get_json(force=True)["envVariablesSpec"]["searchDomains"]
    else:
        ntp = request.get_json(force=True)["envSpec"]["infraComponents"]["ntpServers"]
        dns = request.get_json(force=True)["envSpec"]["infraComponents"]["dnsServersIp"]
        search_domain = request.get_json(force=True)["envSpec"]["infraComponents"]["searchDomains"]
    with open("./systemConfig1.json", "w") as outfile:
        outfile.write(json_object)
    avi_license_type = CommonUtils.get_avi_license_type(env, spec)
    current_app.logger.info(f"setting up avi license as {avi_license_type}")
    if avi_license_type.lower() == "essentials":
        replaceValueSysConfig("./systemConfig1.json", "default_license_tier", "name", "ESSENTIALS")
    else:
        replaceValueSysConfig("./systemConfig1.json", "default_license_tier", "name", "ENTERPRISE")
    replaceValueSysConfig("./systemConfig1.json", "email_configuration", "smtp_type", "SMTP_NONE")
    replaceValueSysConfig("./systemConfig1.json", "dns_configuration", "false", dns)
    replaceValueSysConfig("./systemConfig1.json", "ntp_configuration", "ntp", ntp)
    replaceValueSysConfig("./systemConfig1.json", "dns_configuration", "search_domain", search_domain)
    if isEnvTkgs_wcp(env):
        replaceValueSysConfig("./systemConfig1.json", "portal_configuration", "allow_basic_authentication", "true")
    return "SUCCESS"


def set_avi_admin_password(ip, first_csrf, avi_version, env):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": first_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": first_csrf[0],
    }
    if env == Env.VMC:
        str_enc_avi = str(request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviPasswordBase64"])
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi = str(request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviPasswordBase64"])
        else:
            str_enc_avi = str(request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviPasswordBase64"])
    base64_bytes_avi = str_enc_avi.encode("ascii")
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode("ascii").rstrip("\n")
    payload = {"old_password": "58NFaGDJm(PJH0G", "password": password_avi, "username": "admin"}
    modified_payload = json.dumps(payload, indent=4)
    url = "https://" + ip + "/api/useraccount"
    response_csrf = requests.request("PUT", url, headers=headers, data=modified_payload, verify=False)
    if response_csrf.status_code != 200:
        return None
    else:
        return "SUCCESS"


def obtain_second_csrf(ip, env):
    url = "https://" + str(ip) + "/login"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if env == Env.VMC:
        str_enc_avi = str(request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviPasswordBase64"])
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi = str(request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviPasswordBase64"])
        else:
            str_enc_avi = str(request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviPasswordBase64"])
    base64_bytes_avi = str_enc_avi.encode("ascii")
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode("ascii").rstrip("\n")
    payload = {"username": "admin", "password": password_avi}
    modified_payload = json.dumps(payload, indent=4)
    response_csrf = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
    if response_csrf.status_code != 200:
        return None
    cookies_string = ""
    cookiesString = requests.utils.dict_from_cookiejar(response_csrf.cookies)
    for key, value in cookiesString.items():
        cookies_string += key + "=" + value + "; "
    current_app.config["csrftoken"] = cookiesString["csrftoken"]
    return cookiesString["csrftoken"], cookies_string


def obtain_avi_version(ip, env):
    url = "https://" + str(ip) + "/login"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if env == Env.VMC:
        str_enc_avi = str(request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviPasswordBase64"])
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi = str(request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviPasswordBase64"])
        else:
            str_enc_avi = str(request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviPasswordBase64"])
    base64_bytes_avi = str_enc_avi.encode("ascii")
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode("ascii").rstrip("\n")
    payload = {"username": "admin", "password": password_avi}
    modified_payload = json.dumps(payload, indent=4)
    response_avi = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
    if response_avi.status_code != 200:
        default = {"username": "admin", "password": "58NFaGDJm(PJH0G"}
        modified_payload = json.dumps(default, indent=4)
        response_avi = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
        if response_avi.status_code != 200:
            return None, response_avi.text
    return response_avi.json()["version"]["Version"], 200


def obtain_first_csrf(ip):
    url = "https://" + str(ip) + "/login"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"username": "admin", "password": "58NFaGDJm(PJH0G"}
    modified_payload = json.dumps(payload, indent=4)
    response_csrf = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
    if response_csrf.status_code != 200:
        if str(response_csrf.text).__contains__("Invalid credentials"):
            return "SUCCESS"
        else:
            return None
    cookies_string = ""
    cookiesString = requests.utils.dict_from_cookiejar(response_csrf.cookies)
    for key, value in cookiesString.items():
        cookies_string += key + "=" + value + "; "
    return cookiesString["csrftoken"], cookies_string


def check_controller_is_up(ip, only_check=False):
    url = "https://" + str(ip)
    headers = {"Content-Type": "application/json"}
    payload = {}
    response_login = None
    count = 0
    status = None
    try:
        response_login = requests.request("GET", url, headers=headers, data=payload, verify=False)
        status = response_login.status_code
    except Exception:
        pass

    if only_check:
        if status != 200 or status is None:
            return None
        else:
            return "UP"
    final_elapsed_time = 0
    while (status != 200 or status is None) and count < 150:
        count = count + 1
        elapsed_time = 0
        try:
            response_login = requests.request("GET", url, headers=headers, data=payload, verify=False)
            elapsed_time = RequestApiUtil.fetch_elapsed_time(response_login)
            final_elapsed_time += elapsed_time
            if response_login.status_code == 200:
                break
        except Exception:
            pass
        current_app.logger.info("Waited for  " + str(count * 10 + elapsed_time) + "s, retrying.")
        time.sleep(10)

    if response_login is not None:
        if response_login.status_code != 200:
            return None
        else:
            current_app.logger.info("Controller is up and running in   " + str(count * 10 + final_elapsed_time) + "s.")
            return "UP"
    else:
        current_app.logger.error(
            "Controller is not reachable even after " + str(count * 10 + final_elapsed_time) + "s wait"
        )
        return None


def proxy_check_and_env_setup(env):
    if checkTmcEnabled(env) and (
        checkMgmtProxyEnabled(env) or checkSharedServiceProxyEnabled(env) or checkWorkloadProxyEnabled(env)
    ):
        return 500
    else:
        return 200


def check_arcas_proxy_enabled(env):
    if env == Env.VMC:
        enableArcasProxy = "false"
    elif env == Env.VSPHERE or env == Env.VCF:
        try:
            enableArcasProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["enableProxy"])
        except Exception:
            enableArcasProxy = "false"
    else:
        return False
    if enableArcasProxy.lower() == "true":
        return True
    else:
        return False


def checkAviL7EnabledForShared(env):
    if env == Env.VCF:
        try:
            enable_L7 = str(
                request.get_json(force=True)["tkgComponentSpec"]["tkgSharedserviceSpec"]["tkgSharedserviceEnableAviL7"]
            )
        except Exception:
            enable_L7 = "false"
    elif env == Env.VSPHERE:
        try:
            enable_L7 = str(
                request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgSharedserviceEnableAviL7"]
            )
        except Exception:
            enable_L7 = "false"
    elif env == Env.VMC:
        try:
            enable_L7 = str(
                request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"]["tkgSharedserviceEnableAviL7"]
            )
        except Exception:
            enable_L7 = "false"
    else:
        enable_L7 = "false"
    if enable_L7.lower() == "true":
        return True
    return False


def checkAviL7EnabledForWorkload(env):
    if env == Env.VCF or env == Env.VSPHERE:
        try:
            enable_L7 = str(request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadEnableAviL7"])
        except Exception:
            enable_L7 = "false"
    elif env == Env.VMC:
        try:
            enable_L7 = str(request.get_json(force=True)["componentSpec"]["tkgWorkloadSpec"]["tkgWorkloadEnableAviL7"])
        except Exception:
            enable_L7 = "false"
    else:
        enable_L7 = "false"
    if enable_L7.lower() == "true":
        return True
    return False


def enableProxy(env):
    try:
        if env == Env.VMC:
            enable_arcas_proxy = "false"
        elif isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
            enable_arcas_proxy = str(
                request.get_json(force=True)["tkgsComponentSpec"]["tkgServiceConfig"]["proxySpec"]["enableProxy"]
            )
        elif env == Env.VSPHERE or env == Env.VCF:
            enable_arcas_proxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["enableProxy"])
        else:
            current_app.logger.info("Wrong env type " + env)
            return 500, "Wrong Env Passed"
        if enable_arcas_proxy.lower() == "true":
            if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
                httpProxy = str(
                    request.get_json(force=True)["tkgsComponentSpec"]["tkgServiceConfig"]["proxySpec"]["httpProxy"]
                )
                httpsProxy = str(
                    request.get_json(force=True)["tkgsComponentSpec"]["tkgServiceConfig"]["proxySpec"]["httpsProxy"]
                )
                noProxy = str(
                    request.get_json(force=True)["tkgsComponentSpec"]["tkgServiceConfig"]["proxySpec"]["noProxy"]
                )
                noProxy = noProxy.strip("\n").strip(" ").strip("\r")
            else:
                httpProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["httpProxy"])
                httpsProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["httpsProxy"])
                noProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["noProxy"])
                noProxy = noProxy.strip("\n").strip(" ").strip("\r")
            if noProxy:
                noProxy = ", " + noProxy
            os.environ["http_proxy"] = httpProxy
            os.environ["https_proxy"] = httpsProxy
            os.environ["no_proxy"] = "localhost,127.0.0.1" + noProxy
            if not os.path.isfile("./proxy.bak"):
                back_command = ["cp", "/etc/sysconfig/proxy", "./proxy.bak"]
                runShellCommandAndReturnOutputAsList(back_command)
            data = f"""PROXY_ENABLED="yes"
HTTP_PROXY="{httpProxy}"
HTTPS_PROXY="{httpsProxy}"
NO_PROXY="localhost,127.0.0.1{noProxy}"
    """
            proxy_file = {
                "file_name": "/etc/sysconfig/proxy",
                "docker_file": "/etc/systemd/system/docker.service.d/http-proxy.conf",
            }
            with open(proxy_file["file_name"], "w") as f:
                f.write(data)
            if not os.path.isdir("/etc/systemd/system/docker.service.d"):
                command = ["mkdir", "/etc/systemd/system/docker.service.d"]
                runShellCommandAndReturnOutputAsList(command)
            command_touch = ["touch", "/etc/systemd/system/docker.service.d/http-proxy.conf"]
            runShellCommandAndReturnOutputAsList(command_touch)
            docker_data = f"""[Service]
Environment="HTTP_PROXY={httpProxy}"
Environment="HTTPS_PROXY={httpsProxy}"
Environment="NO_PROXY=localhost,127.0.0.1{noProxy}"
            """
            with open(proxy_file["docker_file"], "w") as f:
                f.write(docker_data)
            docker_reload = ["systemctl", "daemon-reload"]
            runShellCommandAndReturnOutputAsList(docker_reload)
            docker_restart = ["systemctl", "restart", "docker"]
            runShellCommandAndReturnOutputAsList(docker_restart)
            return 200, "Successfully enabled proxy"
        elif enable_arcas_proxy.lower() == "false":
            current_app.logger.info("SIVT VM proxy setting is deactivated")
            return 200, "SIVT VM proxy setting is deactivated"
        else:
            current_app.logger.info("Wrong value of SIVT VM proxy enable is provided " + enable_arcas_proxy)
            return 500, "Wrong value provided for SIVT VM enableProxy, supported values are: true/false"
    except Exception as e:
        if str(e).__contains__("proxySpec"):
            return 200, "Success"
        else:
            return 500, "EXCEPTION: " + str(e)


def validate_proxy_starts_wit_http(env, isShared, isWorkload):
    if checkMgmtProxyEnabled(env):
        httpMgmtProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgMgmt"]["httpProxy"])
        httpsMgmtProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgMgmt"]["httpsProxy"])
        if not httpMgmtProxy.startswith("http://") or not httpsMgmtProxy.startswith("http://"):
            return "management"
    if checkSharedServiceProxyEnabled(env) and isShared:
        httpProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgSharedservice"]["httpProxy"])
        httpsProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgSharedservice"]["httpsProxy"])
        if not httpProxy.startswith("http://") or not httpsProxy.startswith("http://"):
            return "shared"
    if checkWorkloadProxyEnabled(env) and isWorkload:
        httpProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgWorkload"]["httpProxy"])
        httpsProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["tkgWorkload"]["httpsProxy"])
        if not httpProxy.startswith("http://") or not httpsProxy.startswith("http://"):
            return "workload"
    try:
        enableArcasProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["enableProxy"])
    except Exception:
        return "Success"
    if enableArcasProxy.lower() == "true":
        httpProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["httpProxy"])
        httpsProxy = str(request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["httpsProxy"])
        if not httpProxy.startswith("http://") or not httpsProxy.startswith("http://"):
            return "arcas"
    return "Success"


def disable_proxy():
    os.unsetenv("http_proxy")
    os.unsetenv("https_proxy")
    os.unsetenv("no_proxy")
    os.system(
        "cat > /etc/sysconfig/proxy << EOF\n"
        'PROXY_ENABLED="no"\n'
        'HTTP_PROXY=""\n'
        'HTTPS_PROXY=""\n'
        'FTP_PROXY=""\n'
        'GOPHER_PROXY=""\n'
        'SOCKS_PROXY=""\n'
        'SOCKS5_SERVER=""\n'
        'NO_PROXY="localhost, 127.0.0.1"\n'
        "EOF"
    )
    if os.path.isfile("/etc/systemd/system/docker.service.d/http-proxy.conf"):
        os.system("rm -rf /etc/systemd/system/docker.service.d/http-proxy.conf")
        os.system("systemctl daemon-reload")
        os.system("systemctl restart docker")


def disableProxyWrapper(env):
    try:
        if env == Env.VMC:
            disableArcasProxy = "false"
        elif env == Env.VSPHERE or env == Env.VCF:
            if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
                disableArcasProxy = "false"
            else:
                disableArcasProxy = str(
                    request.get_json(force=True)["envSpec"]["proxySpec"]["arcasVm"]["disable-proxy"]
                )
        else:
            current_app.logger.info("Wrong env type " + env)
            return 500
        if disableArcasProxy.lower() == "true":
            os.environ.pop("http_proxy", None)
            os.environ.pop("https_proxy", None)
            os.environ.pop("no_proxy", None)
            if os.path.isfile("./proxy.bak"):
                os.system("rm -rf /etc/sysconfig/proxy")
                os.system("cp ./proxy.bak /etc/sysconfig/proxy")
            if os.path.isfile("/etc/systemd/system/docker.service.d/http-proxy.conf"):
                os.system("rm -rf /etc/systemd/system/docker.service.d/http-proxy.conf")
                os.system("systemctl daemon-reload")
                os.system("systemctl restart docker")
            return 200
        elif disableArcasProxy.lower() == "false":
            current_app.logger.info("Arcas vm proxy setting is deactivated")
            return 200
        else:
            current_app.logger.info("Arcas VM proxy deactivation failed.")
            return 500
    except Exception as e:
        if str(e).__contains__("proxySpec"):
            return 200
        else:
            return 500


def checkMgmtProxyEnabled(env):
    if env == Env.VMC:
        mgmt_proxy = "false"
    else:
        try:
            mgmt_proxy = request.get_json(force=True)["envSpec"]["proxySpec"]["tkgMgmt"]["enableProxy"]
        except Exception:
            return False
    if mgmt_proxy.lower() == "true":
        return True
    else:
        return False


def checkSharedServiceProxyEnabled(env):
    if env == Env.VMC:
        shared_proxy = "false"
    else:
        try:
            shared_proxy = request.get_json(force=True)["envSpec"]["proxySpec"]["tkgSharedservice"]["enableProxy"]
        except Exception:
            return False
    if shared_proxy.lower() == "true":
        return True
    else:
        return False


def checkWorkloadProxyEnabled(env):
    if env == Env.VMC:
        workload_proxy = "false"
    else:
        try:
            workload_proxy = request.get_json(force=True)["envSpec"]["proxySpec"]["tkgWorkload"]["enableProxy"]
        except Exception:
            return False
    if workload_proxy.lower() == "true":
        return True
    else:
        return False


def checkTmcEnabled(env):
    if env == Env.VMC:
        try:
            tmc_required = str(request.get_json(force=True)["saasEndpoints"]["tmcDetails"]["tmcAvailability"])
        except Exception:
            return False
    else:
        try:
            tmc_required = str(
                request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcAvailability"]
            )
        except Exception:
            return False
    if tmc_required.lower() == "true":
        return True
    else:
        return False


def manage_avi_certificates(ip, avi_version, env, avi_fqdn, cert_name):
    if env == Env.VMC:
        str_enc_avi = str(request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviPasswordBase64"])
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi = str(request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviPasswordBase64"])
        else:
            str_enc_avi = str(request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviPasswordBase64"])
    base64_bytes_avi = str_enc_avi.encode("ascii")
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode("ascii").rstrip("\n")
    avi_template = AVITemplateOperations(ip, password_avi, None)
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        d = {"responseType": "ERROR", "msg": "Failed to get csrf from new password", "STATUS_CODE": 500}
        return jsonify(d), 500, False
    try:
        if env == Env.VMC:
            avi_cert = request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviCertPath"]
            avi_key = request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviCertKeyPath"]
            license_key = ""
        elif isEnvTkgs_wcp(env):
            avi_cert = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviCertPath"]
            avi_key = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviCertKeyPath"]
            license_key = ""
        else:
            avi_cert = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviCertPath"]
            avi_key = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviCertKeyPath"]
            license_key = ""
    except Exception:
        avi_cert = ""
        avi_key = ""
        license_key = ""
    if avi_cert and avi_key:
        exist = True
        msg1 = ""
        msg2 = ""
        if not Path(avi_cert).exists():
            exist = False
            msg1 = "Certificate does not exist, please copy certificate file to location " + avi_cert
        if not Path(avi_key).exists():
            exist = False
            msg2 = "Certificate key does not exist, please copy key file to location " + avi_key
        if not exist:
            current_app.logger.error(msg1 + " " + msg2)
            d = {"responseType": "ERROR", "msg": msg1 + " " + msg2, "STATUS_CODE": 500}
            return jsonify(d), 500, False
        key_name = Path(avi_key).name
        cert_file_name = Path(avi_cert).name
        commmand_delete_key = ["rm", "-rf", key_name]
        commmand_delete_cert = ["rm", "-rf", cert_file_name]
        runShellCommandAndReturnOutputAsList(commmand_delete_cert)
        runShellCommandAndReturnOutputAsList(commmand_delete_key)
        current_app.logger.info("Converting pem to one line")
        comand_exe = ["chmod", "+x", "./common/pem_to_one_line_converter.sh"]
        runShellCommandAndReturnOutputAsList(comand_exe)
        commmand_one_line_cert = ["sh", "./common/pem_to_one_line_converter.sh", avi_cert, cert_file_name]
        runShellCommandAndReturnOutputAsList(commmand_one_line_cert)
        cer = Path(cert_file_name).read_text().strip("\n")
        avi_controller_cert = cer
        commmand_one_line_key = ["sh", "./common/pem_to_one_line_converter.sh", avi_key, key_name]
        runShellCommandAndReturnOutputAsList(commmand_one_line_key)
        key = Path(key_name).read_text().strip("\n")
        avi_controller_cert_key = key
        if not avi_controller_cert or not avi_controller_cert_key:
            current_app.logger.error("Certificate or key provided is empty")
            d = {"responseType": "ERROR", "msg": "Certificate or key provided is empty", "STATUS_CODE": 500}
            return jsonify(d), 500, False
        import_cert, error = import_ssl_certificate(
            ip, csrf2, avi_controller_cert, avi_controller_cert_key, env, avi_version
        )
        if import_cert is None:
            current_app.logger.error("AVI cert import failed " + str(error))
            d = {"responseType": "ERROR", "msg": "AVI cert import failed " + str(error), "STATUS_CODE": 500}
            return jsonify(d), 500, False
        cert_name = import_cert["cert_name"]
    get_cert = get_ssl_certificate_status(ip, csrf2, cert_name, avi_version)
    if get_cert[0] is None:
        current_app.logger.error("Failed to get certificate status " + str(get_cert[1]))
        d = {"responseType": "ERROR", "msg": "Failed to get certificate status " + str(get_cert[1]), "STATUS_CODE": 500}
        return jsonify(d), 500, False

    if get_cert[0] == "NOT_FOUND":
        current_app.logger.info("Generating cert")
        if avi_cert and avi_key:
            res = create_imported_ssl_certificate(ip, csrf2, import_cert, cer, key, env, avi_version)
        else:
            if env == Env.VMC:
                res = generate_ssl_certificate(ip, csrf2, avi_version)
            else:
                res = generate_ssl_certificate_vsphere(ip, csrf2, avi_fqdn, avi_version)
        url = res[0]
        if res[0] is None:
            current_app.logger.error("Failed to generate the ssl certificate")
            d = {"responseType": "ERROR", "msg": "Failed to generate the ssl certificate " + res[1], "STATUS_CODE": 500}
            return jsonify(d), 500, False
    else:
        url = get_cert[0]
    get_cert = get_current_cert_config(ip, csrf2, url, avi_version)
    if get_cert[0] is None:
        current_app.logger.error("Failed to get current certificate")
        d = {"responseType": "ERROR", "msg": "Failed to get current certificate " + get_cert[1], "STATUS_CODE": 500}
        return jsonify(d), 500, False
    current_app.logger.info("Replacing cert")
    replace_cert = replaceWithNewCert(ip, csrf2, avi_version)
    if replace_cert[0] is None:
        current_app.logger.error("Failed replace the certificate" + replace_cert[1])
        d = {"responseType": "ERROR", "msg": "Failed replace the certificate " + replace_cert[1], "STATUS_CODE": 500}
        return jsonify(d), 500, False
    if license_key:
        res, status = avi_template._configure_alb_license(license_key)
        if res is None:
            current_app.logger.error("Failed to apply licenses " + str(status))
            d = {"responseType": "ERROR", "msg": "Failed to apply licenses " + str(status), "STATUS_CODE": 500}
            return jsonify(d), 500, False
        current_app.logger.info(status)
    d = {"responseType": "SUCCESS", "msg": "Certificate managed successfully", "STATUS_CODE": 200}
    return jsonify(d), 200, True


def getCloudStatus(ip, csrf2, aviVersion, cloudName):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    url = "https://" + ip + "/api/cloud"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for res in response_csrf.json()["results"]:
            if res["name"] == cloudName:
                os.system("rm -rf newCloudInfo.json")
                with open("./newCloudInfo.json", "w") as outfile:
                    json.dump(response_csrf.json(), outfile)
                return res["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def seperateNetmaskAndIp(cidr):
    return str(cidr).split("/")


def getSECloudStatus(ip, csrf2, aviVersion, seGroupName):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    json_object = json.dumps(body, indent=4)
    url = "https://" + ip + "/api/serviceenginegroup"
    response_csrf = requests.request("GET", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for res in response_csrf.json()["results"]:
            if res["name"] == seGroupName:
                return res["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def runSsh(vc_user):
    os.system("rm -rf /root/.ssh/id_rsa")
    os.system("ssh-keygen -t rsa -b 4096 -C '" + vc_user + "' -f /root/.ssh/id_rsa -N ''")
    os.system("eval $(ssh-agent)")
    os.system("ssh-add /root/.ssh/id_rsa")
    with open("/root/.ssh/id_rsa.pub", "r") as f:
        re = f.readline()
    return re


def getVipNetworkIpNetMask(ip, csrf2, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    url = "https://" + ip + "/api/network"
    try:
        response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            for res in response_csrf.json()["results"]:
                if res["name"] == name:
                    for sub in res["configured_subnets"]:
                        return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]), "SUCCESS"
            else:
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=body, verify=False)
                    for res in response_csrf.json()["results"]:
                        if res["name"] == name:
                            for sub in res["configured_subnets"]:
                                return (
                                    str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]),
                                    "SUCCESS",
                                )
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
        return "NOT_FOUND", "FAILED"
    except KeyError:
        return "NOT_FOUND", "FAILED"


def getVrfAndNextRoutId(ip, csrf2, cloudUuid, type, routIp, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    routId = 0
    url = "https://" + ip + "/api/vrfcontext/?name.in=" + type + "&cloud_ref.uuid=" + cloudUuid
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        liist = []
        for res in response_csrf.json()["results"]:
            if res["name"] == type:
                try:
                    for st in res["static_routes"]:
                        liist.append(int(st["route_id"]))
                        print(st["next_hop"]["addr"])
                        print(routIp)
                        if st["next_hop"]["addr"] == routIp:
                            return res["url"], "Already_Configured"
                    liist.sort()
                    routId = int(liist[-1]) + 1
                except Exception:
                    pass
                if type == VrfType.MANAGEMENT:
                    routId = 1
                return res["url"], routId
            else:
                return None, "NOT_FOUND"
        return None, "NOT_FOUND"


def addStaticRoute(ip, csrf2, vrfUrl, routeIp, routId, aviVersion):
    if routId == 0:
        routId = 1
    body = {
        "add": {
            "static_routes": [
                {
                    "prefix": {"ip_addr": {"addr": "0.0.0.0", "type": "V4"}, "mask": 0},
                    "next_hop": {"addr": routeIp, "type": "V4"},
                    "route_id": routId,
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
        "x-csrftoken": csrf2[0],
    }
    url = vrfUrl
    json_object = json.dumps(body, indent=4)
    response_csrf = requests.request("PATCH", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return "SUCCESS", 200


def checkAirGappedIsEnabled(env):
    if env == Env.VMC:
        air_gapped = ""
    else:
        try:
            air_gapped = request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepository"]
        except Exception:
            return False
    if not air_gapped.lower():
        return False
    else:
        return True


def checkEnableIdentityManagement(env):
    try:
        if not isEnvTkgs_ns(env) and not isEnvTkgs_wcp(env):
            if env == Env.VMC:
                idm = request.get_json(force=True)["componentSpec"]["identityManagementSpec"]["identityManagementType"]
            elif env == Env.VSPHERE or env == Env.VCF:
                idm = request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"][
                    "identityManagementType"
                ]
            if (idm.lower() == "oidc") or (idm.lower() == "ldap"):
                return True
            else:
                return False
        else:
            return False
    except Exception:
        return False


def argapPrecheck(env):
    if checkTmcEnabled(env) and checkAirGappedIsEnabled(env):
        return 500
    if Tkg_version.TKG_VERSION == "1.3":
        if checkTmcEnabled(env) and checkSharedServiceProxyEnabled(env):
            return 500
        if checkTmcEnabled(env) and checkMgmtProxyEnabled(env):
            return 500
        if checkTmcEnabled(env) and checkWorkloadProxyEnabled(env):
            return 500
        if checkTmcEnabled(env) and check_arcas_proxy_enabled(env):
            return 500
    return 200


def checkAnyProxyIsEnabled(env):
    if checkSharedServiceProxyEnabled(env):
        return True
    if checkMgmtProxyEnabled(env):
        return True
    if checkWorkloadProxyEnabled(env):
        return True
    if check_arcas_proxy_enabled(env):
        return True
    return False


def dockerLoginAndConnectivityCheck(env):
    if argapPrecheck(env) != 200:
        current_app.logger.error("TMC configuration is not supported on air gapped and proxy enabled environment")
        d = {
            "responseType": "ERROR",
            "msg": "TMC configuration is not supported on air gapped and proxy enabled environment",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    if checkAirGappedIsEnabled(env):
        air_gapped_repo = str(
            request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepository"]
        )
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        if not air_gapped_repo:
            current_app.logger.error("No repository provided")
            d = {"responseType": "ERROR", "msg": "No repository provided", "STATUS_CODE": 500}
            return jsonify(d), 500
        os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        repository = request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepository"]
        if str(repository).startswith("http://"):
            pass
        elif str(repository).startswith("https://"):
            pass
        else:
            current_app.logger.error(
                "Invalid url provided, url must start with http:// or https://, but found  " + repository
            )
            d = {
                "responseType": "ERROR",
                "msg": "Invalid url provided url must start with http:// or https://, but found " + repository,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        try:
            response_csrf = requests.request("GET", repository, headers=headers, data={}, verify=False)
            if response_csrf.status_code != 200:
                current_app.logger.error("No connectivity to repository " + repository)
                d = {"responseType": "ERROR", "msg": "No connectivity to repository " + repository, "STATUS_CODE": 500}
                return jsonify(d), 500
        except Exception as e:
            current_app.logger.error("No connectivity to repository " + str(e))
            d = {"responseType": "ERROR", "msg": "No connectivity to repository " + str(e), "STATUS_CODE": 500}
            return jsonify(d), 500
        isSelfsinged = str(
            request.get_json(force=True)["envSpec"]["customRepositorySpec"]["tkgCustomImageRepositoryPublicCaCert"]
        )
        if isSelfsinged.lower() == "false":
            isAlreadyAdded = False
            try:
                with open("isCertAdded.txt", "r") as e:
                    data = e.read()
                if data.strip("\n").strip("\r").strip() == "true":
                    isAlreadyAdded = True
                else:
                    isAlreadyAdded = False
            except Exception:
                pass
            if not isAlreadyAdded:
                repoAdd(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
                getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
                with open("cert.txt", "r") as file2:
                    repo_cert = file2.readline()
                repo_certificate = repo_cert
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
                try:
                    cmd_doc = ["systemctl", "restart", "docker"]
                    runShellCommandWithPolling(cmd_doc)
                except Exception as e:
                    current_app.logger.error("Failed to restart docker " + str(e))
                    d = {"responseType": "ERROR", "msg": "Failed to restart docker " + str(e), "STATUS_CODE": 500}
                    return jsonify(d), 500
                current_app.logger.info("Docker restarted, waiting for 2 min for all pods to be up and running")
                with open("isCertAdded.txt", "w") as e:
                    e.write("true")
                time.sleep(120)
        else:
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
        try:
            repo_usename = request.get_json(force=True)["envSpec"]["customRepositorySpec"][
                "tkgCustomImageRepositoryUsername"
            ]
            repo_password = request.get_json(force=True)["envSpec"]["customRepositorySpec"][
                "tkgCustomImageRepositoryPasswordBase64"
            ]
            base64_bytes = repo_password.encode("ascii")
            enc_bytes = base64.b64decode(base64_bytes)
            repo_password = enc_bytes.decode("ascii").rstrip("\n")
        except Exception:
            repo_password = ""
            repo_usename = ""
        if repo_usename and repo_password:
            list_command = ["docker", "login", repository, "-u", repo_usename, "-p", repo_password]
            sta = runShellCommandAndReturnOutputAsList(list_command)
            if sta[1] != 0:
                current_app.logger.error("Docker login failed " + str(sta[0]))
                d = {"responseType": "ERROR", "msg": "Docker login failed " + str(sta[0]), "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Docker login success")
            d = {"responseType": "SUCCESS", "msg": "Docker login success", "STATUS_CODE": 200}
            return jsonify(d), 200
        current_app.logger.info("Airgapped precheck successful")
        d = {"responseType": "SUCCESS", "msg": "Airgapped pre-check successful", "STATUS_CODE": 200}
        return jsonify(d), 200
    else:
        d = {"responseType": "SUCCESS", "msg": "Air gapped not enabled", "STATUS_CODE": 200}
        return jsonify(d), 200


def is_compliant_deployment():
    env_spec = request.get_json(force=True)["envSpec"]
    if "compliantSpec" in env_spec and env_spec["compliantSpec"]["compliantDeployment"].lower() == "false":
        return False
    elif "compliantSpec" in env_spec and env_spec["compliantSpec"]["compliantDeployment"].lower() == "true":
        return True
    else:
        return False


def loadBomFile():
    if is_compliant_deployment():
        bom_file = Extension.FIPS_BOM_LOCATION_14
    else:
        bom_file = Extension.BOM_LOCATION_14
    try:
        with open(bom_file, "r") as stream:
            try:
                data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                current_app.logger.error("Failed to find key " + str(exc))
                return None
            return data
    except Exception as e:
        current_app.logger.error("Failed to read bom file " + str(e))
        return None


def grabPortFromUrl(url):
    m = re.search(RegexPattern.URL_REGEX_PORT, url)
    if not m.group("port"):
        return "443"
    else:
        return m.group("port")


def grabHostFromUrl(url):
    m = re.search(RegexPattern.URL_REGEX_PORT, url)
    if not m.group("host"):
        return None
    else:
        return m.group("host")


def checkTanzuExtensionEnabled():
    try:
        tanzu_ext = str(request.get_json(force=True)["tanzuExtensions"]["enableExtensions"])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def checkPromethusEnabled():
    try:
        tanzu_ext = str(request.get_json(force=True)["tanzuExtensions"]["monitoring"]["enableLoggingExtension"])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_syslog_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)["tanzuExtensions"]["logging"]["syslogEndpoint"]["enableSyslogEndpoint"]
        )
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_http_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)["tanzuExtensions"]["logging"]["httpEndpoint"]["enableHttpEndpoint"]
        )
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_elastic_search_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)["tanzuExtensions"]["logging"]["elasticSearchEndpoint"][
                "enableElasticSearchEndpoint"
            ]
        )
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_kafka_endpoint_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)["tanzuExtensions"]["logging"]["kafkaEndpoint"]["enableKafkaEndpoint"]
        )
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_splunk_endpoint_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)["tanzuExtensions"]["logging"]["splunkEndpoint"]["enableSplunkEndpoint"]
        )
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def waitForProcess(list1, podName):
    time.sleep(30)
    count_cert = 0
    running = False
    while count_cert < 60:
        cert_state = runShellCommandAndReturnOutputAsList(list1)
        time.sleep(30)
        if verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RECONCILE_SUCCEEDED):
            running = True
            break
        count_cert = count_cert + 1
        current_app.logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    if not running:
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500, count_cert
    current_app.logger.info("Successfully running " + podName)
    d = {"responseType": "SUCCESS", "msg": "Successfully running" + podName, "STATUS_CODE": 200}
    return jsonify(d), 200, count_cert


def waitForProcessWithStatus(list1, podName, status):
    count_cert = 0
    running = False
    while count_cert < 60:
        cert_state = runShellCommandAndReturnOutputAsList(list1)
        time.sleep(30)
        if verifyPodsAreRunning(podName, cert_state[0], status):
            running = True
            break
        count_cert = count_cert + 1
        current_app.logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    if not running:
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500, count_cert
    current_app.logger.info("Successfully running " + podName)
    d = {"responseType": "SUCCESS", "msg": "Successfully running" + podName, "STATUS_CODE": 200}
    return jsonify(d), 200, count_cert


def installCertManagerAndContour(env, cluster_name, repo_address, service_name):
    podRunninng = ["tanzu", "cluster", "list", "--include-management-cluster", "-A"]
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if not verifyPodsAreRunning(cluster_name, command_status[0], RegexPattern.running):
        current_app.logger.error(cluster_name + " is not deployed")
        d = {"responseType": "ERROR", "msg": cluster_name + " is not deployed", "STATUS_CODE": 500}
        return jsonify(d), 500
    if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env):
        mgmt = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcSupervisorClusterName"]
    else:
        mgmt = TanzuUtil.get_management_cluster()
        if mgmt is None:
            current_app.logger.error("Failed to get management cluster")
            d = {"responseType": "ERROR", "msg": "Failed to get management cluster", "STATUS_CODE": 500}
            return jsonify(d), 500
    if str(mgmt).strip() == cluster_name.strip():
        switch = TanzuUtil.switch_to_management_context(cluster_name.strip())
        if switch[1] != 200:
            current_app.logger.info(switch[0])
            d = {"responseType": "ERROR", "msg": switch[0], "STATUS_CODE": 500}
            return jsonify(d), 500
    else:
        if isEnvTkgs_ns(env):
            name_space = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
                "tkgsVsphereWorkloadClusterSpec"
            ]["tkgsVsphereNamespaceName"]
            commands_shared = ["tanzu", "cluster", "kubeconfig", "get", cluster_name, "--admin", "-n", name_space]
        else:
            commands_shared = ["tanzu", "cluster", "kubeconfig", "get", cluster_name, "--admin"]
        kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kubeContextCommand_shared is None:
            current_app.logger.error("Failed to get switch to " + cluster_name + " cluster context command")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to " + cluster_name + " context command",
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
        status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
        if status[1] != 0:
            current_app.logger.error("Failed to get switch to shared cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to " + cluster_name + " context " + str(status[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

    status_ = TanzuUtil().check_repository_added()
    if status_[1] != 200:
        current_app.logger.error(str(status_[0]))
        d = {"responseType": "ERROR", "msg": str(status_[0]), "STATUS_CODE": 500}
        return jsonify(d), 500
    install = installExtensionFor14(service_name, cluster_name, env)
    if install[1] != 200:
        return install[0], install[1]
    current_app.logger.info("Configured cert-manager and contour extensions successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured cert-manager and contour extensions successfully",
        "STATUS_CODE": 200,
    }
    return jsonify(d), 200


def waitForGrepProcess(list1, list2, podName, dir):
    time.sleep(30)
    count_cert = 0
    running = False
    try:
        while count_cert < 60:
            cert_state = grabPipeOutputChagedDir(list1, list2, dir)
            if verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING):
                running = True
                break
            time.sleep(30)
            count_cert = count_cert + 1
            current_app.logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    except Exception as e:
        current_app.logger.error("Failed to verify pod running " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to verify pod running", "STATUS_CODE": 500}
        return jsonify(d), 500, count_cert
    if not running:
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500, count_cert
    d = {"responseType": "ERROR", "msg": "Successfully running " + podName + " ", "STATUS_CODE": 200}
    return jsonify(d), 200, count_cert


def waitForGrepProcessWithoutChangeDir(list1, list2, podName, status):
    time.sleep(30)
    count_cert = 0
    running = False
    try:
        while count_cert < 60:
            cert_state = grabPipeOutput(list1, list2)
            if verifyPodsAreRunning(podName, cert_state[0], status):
                running = True
                break
            time.sleep(30)
            count_cert = count_cert + 1
            current_app.logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    except Exception as e:
        current_app.logger.error("Failed to verify pod running " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to verify pod running", "STATUS_CODE": 500}
        return jsonify(d), 500, count_cert
    if not running:
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500, count_cert
    d = {"responseType": "ERROR", "msg": "Successfully running " + podName + " ", "STATUS_CODE": 200}
    return jsonify(d), 200, count_cert


def changeRepo(repo_address):
    repo_address = repo_address.replace("https://", "").replace("http://", "")
    list_type = ["cert-manager-cainjector", "cert-manager", "cert-manager-webhook"]

    if not repo_address.endswith("/"):
        repo_address = repo_address + "/"
    for type_cert in list_type:
        repo = None
        if type_cert == "cert-manager-cainjector":
            repo = repo_address + Extension.CERT_MANAGER_CA_INJECTOR
        elif type_cert == "cert-manager":
            repo = repo_address + Extension.CERT_MANAGER_CONTROLLER
        elif type_cert == "cert-manager-webhook":
            repo = repo_address + Extension.CERT_MANAGER_WEB_HOOK
        change_repo = (
            "./common/injectValue.sh "
            + Extension.CERT_MANAGER_LOCATION
            + "/03-cert-manager.yaml"
            + " cert "
            + repo
            + " "
            + type_cert
        )
        os.system(change_repo)
    current_app.logger.info("Changed repo of cert manager Successfully")
    d = {"responseType": "SUCCESS", "msg": "Changed repo of cert manager Successfully", "STATUS_CODE": 200}
    return jsonify(d), 200


def deployExtension(extensionYaml, appName, nameSpace, extensionLocation):
    command_harbor_apply = ["kubectl", "apply", "-f", extensionYaml]
    state_harbor_apply = runShellCommandAndReturnOutputAsListWithChangedDir(command_harbor_apply, extensionLocation)
    if state_harbor_apply[1] == 500:
        current_app.logger.error("Failed to apply " + str(state_harbor_apply[0]))
        d = {"responseType": "ERROR", "msg": "Failed to apply " + str(state_harbor_apply[0]), "STATUS_CODE": 500}
        return jsonify(d), 500

    listCommand = ["kubectl", "get", "app", appName, "-n", nameSpace]
    st = waitForProcess(listCommand, appName)
    if st[1] != 200:
        return st[0], st[1]
    else:
        current_app.logger.info(appName + " deployed, and is up and running")
        d = {"responseType": "SUCCESS", "msg": appName + " deployed, and is up and running", "STATUS_CODE": 200}
        return jsonify(d), 200


def createRbacUsers(clusterName, isMgmt, env, cluster_admin_users, admin_users, edit_users, view_users):
    try:
        if isMgmt:
            switch = TanzuUtil.switch_to_management_context(clusterName)
            if switch[1] != 200:
                current_app.logger.info(switch[0])
                d = {"responseType": "ERROR", "msg": switch[0], "STATUS_CODE": 500}
                return jsonify(d), 500
        else:
            switch = TanzuUtil().switch_to_context(clusterName)
            if switch[1] != 200:
                current_app.logger.info(switch[0].json["msg"])
                d = {"responseType": "ERROR", "msg": switch[0].json["msg"], "STATUS_CODE": 500}
                return jsonify(d), 500
        if isMgmt:
            exportCmd = [
                "tanzu",
                "management-cluster",
                "kubeconfig",
                "get",
                clusterName,
                "--export-file",
                Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig",
            ]
        else:
            exportCmd = [
                "tanzu",
                "cluster",
                "kubeconfig",
                "get",
                clusterName,
                "--export-file",
                Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig",
            ]

        output = runShellCommandAndReturnOutputAsList(exportCmd)
        if output[1] == 0:
            current_app.logger.info(
                "Exported kubeconfig at  " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig"
            )
        else:
            current_app.logger.error(
                "Failed to export config file to " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig"
            )
            current_app.logger.error(output[0])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to export config file to " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig",
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        rbac_dict = dict()
        rbac_dict.update({"cluster-admin": cluster_admin_users})
        rbac_dict.update({"admin": admin_users})
        rbac_dict.update({"edit": edit_users})
        rbac_dict.update({"view": view_users})

        for key in rbac_dict:
            users = rbac_dict[key]
            if users:
                users_list = users.split(",")
                for username in users_list:
                    current_app.logger.info("Checking if Cluster Role binding exists for the user: " + username)
                    main_command = ["kubectl", "get", "clusterrolebindings"]
                    sub_command = ["grep", username + "-crb"]
                    output = grabPipeOutput(main_command, sub_command)
                    if output[1] == 0:
                        if output[0].__contains__(key):
                            current_app.logger.info(key + " role binding for user: " + username + " already exists!")
                            continue
                    current_app.logger.info("Creating Cluster Role binding for user: " + username)
                    listOfCmd = [
                        "kubectl",
                        "create",
                        "clusterrolebinding",
                        username + "-crb",
                        "--clusterrole",
                        key,
                        "--user",
                        username,
                    ]
                    output = runShellCommandAndReturnOutputAsList(listOfCmd)
                    if output[1] == 0:
                        current_app.logger.info("Created RBAC for user: " + username + " SUCCESSFULLY")
                        current_app.logger.info(
                            "Kubeconfig file has been generated and stored at "
                            + Paths.CLUSTER_PATH
                            + clusterName
                            + "/"
                            + "crb-kubeconfig"
                        )
                    else:
                        current_app.logger.error("Failed to created Cluster Role Binding for user: " + username)
                        current_app.logger.error(output[0])
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to created Cluster Role Binding for user: " + username,
                            "STATUS_CODE": 500,
                        }
                        return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "Created RBAC successfully for all the provided users",
            "STATUS_CODE": 200,
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.info("Some error occurred while creating cluster role bindings" + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Some error occurred while creating cluster role bindings",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500


def installExtensionFor14(service_name, cluster, env):
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    service = service_name
    if service == "certmanager" or service == "all":
        sub_command = ["grep", AppName.CERT_MANAGER]
        command_cert = grabPipeOutput(main_command, sub_command)
        if not verifyPodsAreRunning(AppName.CERT_MANAGER, command_cert[0], RegexPattern.RECONCILE_SUCCEEDED):
            state = TanzuUtil.get_version_of_package("cert-manager.tanzu.vmware.com")
            if state is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Version of package cert-manager.tanzu.vmware.com",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Installing cert manager - " + state)

            verify_ns = ["kubectl", "get", "ns"]
            out = runShellCommandAndReturnOutputAsList(verify_ns)
            for item in out[0]:
                if f"{AppName.CERT_MANAGER}-package" in item:
                    break
            else:
                create_ns_cmd = ["kubectl", "create", "ns", f"{AppName.CERT_MANAGER}-package"]
                runProcess(create_ns_cmd)

            install_command = [
                "tanzu",
                "package",
                "install",
                AppName.CERT_MANAGER,
                "--package",
                "cert-manager.tanzu.vmware.com",
                "--namespace",
                f"{AppName.CERT_MANAGER}-package",
                "--version",
                state,
            ]
            states = runShellCommandAndReturnOutputAsList(install_command)
            if states[1] != 0:
                current_app.logger.error(
                    AppName.CERT_MANAGER + " installation command failed. Checking for reconciliation status.."
                )
            certManagerStatus = waitForGrepProcessWithoutChangeDir(
                main_command, sub_command, AppName.CERT_MANAGER, RegexPattern.RECONCILE_SUCCEEDED
            )
            if certManagerStatus[1] == 500:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to bring cert-manager " + str(certManagerStatus[0].json["msg"]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Configured Cert manager successfully")
            if service != "all":
                d = {"responseType": "SUCCESS", "msg": "Configured Cert manager successfully", "STATUS_CODE": 200}
                return jsonify(d), 200
        else:
            current_app.logger.info("Cert manager is already running")
            if service != "all":
                d = {"responseType": "SUCCESS", "msg": "Cert manager is already running", "STATUS_CODE": 200}
                return jsonify(d), 200
    if service == "ingress" or service == "all":
        if not isEnvTkgs_ns(env):
            podRunninng_ako_main = ["kubectl", "get", "pods", "-A"]
            podRunninng_ako_grep = ["grep", AppName.AKO]
            command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
            if not verifyPodsAreRunning(AppName.AKO, command_status_ako[0], RegexPattern.RUNNING):
                d = {
                    "responseType": "ERROR",
                    "msg": "Ako pod is not running " + str(command_status_ako[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        sub_command = ["grep", AppName.CONTOUR]
        command_cert = grabPipeOutput(main_command, sub_command)
        if not verifyPodsAreRunning(AppName.CONTOUR, command_cert[0], RegexPattern.RECONCILE_SUCCEEDED):
            createContourDataValues(cluster)
            state = TanzuUtil.get_version_of_package("contour.tanzu.vmware.com")
            if state is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Version of package contour.tanzu.vmware.com",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Installing contour - " + state)
            # Changed for glasgow
            verify_ns = ["kubectl", "get", "ns"]
            out = runShellCommandAndReturnOutputAsList(verify_ns)
            for item in out[0]:
                if "tanzu-system-ingress" in item:
                    break
            else:
                create_ns_cmd = ["kubectl", "create", "ns", "tanzu-system-ingress"]
                runProcess(create_ns_cmd)

            out = runShellCommandAndReturnOutputAsList(verify_ns)
            for item in out[0]:
                if "tanzu-contour-ingress" in item:
                    break
            else:
                create_ns_cmd = ["kubectl", "create", "ns", "tanzu-contour-ingress"]
                runProcess(create_ns_cmd)

            install_command = [
                "tanzu",
                "package",
                "install",
                AppName.CONTOUR,
                "--package",
                "contour.tanzu.vmware.com",
                "--version",
                state,
                "--values-file",
                Paths.CLUSTER_PATH + cluster + "/contour-data-values.yaml",
                "--namespace",
                "tanzu-contour-ingress",
            ]
            states = runShellCommandAndReturnOutputAsList(install_command)
            if states[1] != 0:
                for r in states[0]:
                    current_app.logger.error(r)
                current_app.logger.info(
                    AppName.CONTOUR + " install command failed. Checking for reconciliation status..."
                )
            certManagerStatus = waitForGrepProcessWithoutChangeDir(
                main_command, sub_command, AppName.CONTOUR, RegexPattern.RECONCILE_SUCCEEDED
            )
            if certManagerStatus[1] == 500:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to bring contour " + str(certManagerStatus[0].json["msg"]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            if service != "all":
                current_app.logger.info("Contour deployed and is up and running")
                d = {"responseType": "SUCCESS", "msg": "Contour deployed and is up and running", "STATUS_CODE": 200}
                return jsonify(d), 200
        else:
            current_app.logger.info("Contour is already up and running")
            d = {"responseType": "SUCCESS", "msg": "Contour is already up and running", "STATUS_CODE": 200}
            return jsonify(d), 200
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured cert-manager and contour extensions successfully",
        "STATUS_CODE": 200,
    }
    return jsonify(d), 200


def createContourDataValues(clusterName):
    data = dict(
        infrastructure_provider="vsphere",
        namespace="tanzu-system-ingress",
        contour=dict(
            configFileContents={},
            useProxyProtocol=False,
            replicas=2,
            pspNames="vmware-system-restricted",
            logLevel="info",
        ),
        envoy=dict(
            service=dict(
                type="LoadBalancer",
                annotations={},
                nodePorts=dict(http=0, https=0),
                externalTrafficPolicy="replace",
                disableWait=False,
            ),
            hostPorts=dict(enable=True, http=80, https=443),
            hostNetwork=False,
            terminationGracePeriodSeconds=300,
            logLevel="info",
            pspNames="vmware-system-restricted",
        ),
        certificates=dict(duration="8760h", renewBefore="360h"),
    )

    with open("/tmp/tmp_contour-data-values.yaml", "w") as outfile:
        outfile.write("---\n")
        yaml1 = ruamel.yaml.YAML()
        yaml1.indent(mapping=2, sequence=4, offset=3)
        yaml1.dump(data, outfile)

    with open("/tmp/tmp_contour-data-values.yaml", "r") as f1:
        content = f1.read()
    content = re.sub(r"'", "", content)

    with open(Paths.CLUSTER_PATH + clusterName + "/contour-data-values.yaml", "w") as f2:
        f2.write(content)
    command2 = [
        "./common/injectValue.sh",
        Paths.CLUSTER_PATH + clusterName + "/contour-data-values.yaml",
        "remove_policy_contour",
    ]
    runShellCommandAndReturnOutputAsList(command2)


def createOverlayYaml(repository, clusterName):
    if not repository.endswith("/"):
        repository = repository + "/"
    os.system("rm -rf " + Paths.CLUSTER_PATH + "/harbor-overlay.yaml")
    os.system("chmod +x ./common/injectValue.sh")
    repository = (
        repository
        + "harbor/notary-signer-photon@sha256:4dfbf3777c26c615acfb466b98033c0406766692e9c32f3bb08873a0295e24d1"
    )
    os.system("cp ./common/harbor-overlay.yaml" + Paths.CLUSTER_PATH + "/harbor-overlay.yaml")
    os.system("./common/injectValue.sh " + Paths.CLUSTER_PATH + "/harbor-overlay.yaml overlay " + repository)


def getNetworkFolder(netWorkName, vcenter_ip, vcenter_username, password):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    find_command = ["govc", "find", "-name", netWorkName]
    count = 0
    net = ""
    while count < 120:
        output = runShellCommandAndReturnOutputAsList(find_command)
        if str(output[0]).__contains__(netWorkName) and str(output[0]).__contains__("/network"):
            for o in output[0]:
                if str(o).__contains__("/network"):
                    net = o
                    break
            if net:
                current_app.logger.info("Network is available " + str(net))
                return net
        time.sleep(5)
        count = count + 1
    return None


def checkMachineCountForProdType(env, isShared, isWorkload):
    try:
        if env == Env.VMC:
            if isShared:
                shared_deployment_type = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
                    "tkgSharedserviceDeploymentType"
                ]
                shared_worker_count = request.get_json(force=True)["componentSpec"]["tkgSharedServiceSpec"][
                    "tkgSharedserviceWorkerMachineCount"
                ]
            if isWorkload:
                workload_deployment_type = request.get_json(force=True)["componentSpec"]["tkgWorkloadSpec"][
                    "tkgWorkloadDeploymentType"
                ]
                workload_worker_count = request.get_json(force=True)["componentSpec"]["tkgWorkloadSpec"][
                    "tkgWorkloadWorkerMachineCount"
                ]
        elif env == Env.VSPHERE:
            if isShared:
                shared_deployment_type = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                    "tkgSharedserviceDeploymentType"
                ]
                shared_worker_count = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                    "tkgSharedserviceWorkerMachineCount"
                ]
            if isWorkload:
                workload_deployment_type = request.get_json(force=True)["tkgWorkloadComponents"][
                    "tkgWorkloadDeploymentType"
                ]
                workload_worker_count = request.get_json(force=True)["tkgWorkloadComponents"][
                    "tkgWorkloadWorkerMachineCount"
                ]
        elif env == Env.VCF:
            if isShared:
                shared_deployment_type = request.get_json(force=True)["tkgComponentSpec"]["tkgSharedserviceSpec"][
                    "tkgSharedserviceDeploymentType"
                ]
                shared_worker_count = request.get_json(force=True)["tkgComponentSpec"]["tkgSharedserviceSpec"][
                    "tkgSharedserviceWorkerMachineCount"
                ]
            if isWorkload:
                workload_deployment_type = request.get_json(force=True)["tkgWorkloadComponents"][
                    "tkgWorkloadDeploymentType"
                ]
                workload_worker_count = request.get_json(force=True)["tkgWorkloadComponents"][
                    "tkgWorkloadWorkerMachineCount"
                ]
        if isShared:
            if shared_deployment_type.lower() == PLAN.PROD_PLAN:
                current_app.logger.info("Verifying worker machine count for shared services cluster")
                if int(shared_worker_count) < 3:
                    current_app.logger.error(
                        "Min worker machine count for a prod deployment plan on shared services cluster is 3!"
                    )
                    d = {
                        "responseType": "ERROR",
                        "msg": "Min worker machine count for a prod deployment plan on shared services cluster is 3!",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                current_app.logger.info("Successfully validated worker machine count for shared services cluster")
        if isWorkload:
            if workload_deployment_type.lower() == PLAN.PROD_PLAN:
                current_app.logger.info("Verifying worker machine count for workload cluster")
                if int(workload_worker_count) < 3:
                    current_app.logger.error(
                        "Min worker machine count for a prod on workload cluster deployment plan is 3!"
                    )
                    d = {
                        "responseType": "ERROR",
                        "msg": "Min worker machine count for a prod deployment plan on workload cluster is 3!",
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
                current_app.logger.info("Successfully validated worker machine count for workload cluster")
        d = {"responseType": "SUCCESS", "msg": "Successfully validated worker machine count", "STATUS_CODE": 200}
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {"responseType": "ERROR", "msg": "Not found key " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500


def createVcfDhcpServer():
    try:
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            current_app.logger.error("Failed to get NSXT info " + str(headers_[1]))
            d = {"responseType": "ERROR", "msg": "Failed to get NSXT info " + str(headers_[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/dhcp-server-configs"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            current_app.logger.error("Failed to get DHCP info on NSXT " + str(output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get DHCP info on NSXT " + str(output[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        tier_path = getTier1Details(headers_)
        if tier_path[0] is None:
            d = {"responseType": "ERROR", "msg": "Failed to get Tier1 details " + str(tier_path[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        url = "https://" + headers_[2] + "/policy/api/v1" + str(tier_path[0])
        dhcp_state = requests.request("GET", url, headers=headers_[1], verify=False)
        if dhcp_state.status_code != 200:
            d = {"responseType": "ERROR", "msg": dhcp_state.text, "STATUS_CODE": dhcp_state.status_code}
            current_app.logger.error(dhcp_state.text)
            return jsonify(d), dhcp_state.status_code
        dhcp_present = False
        try:
            length = len(dhcp_state.json()["dhcp_config_paths"])
            if length > 0:
                dhcp_present = True
        except Exception:
            pass
        if not dhcp_present:
            if not checkObjectIsPresentAndReturnPath(output[0], VCF.DHCP_SERVER_NAME)[0]:
                url = "https://" + headers_[2] + "/policy/api/v1/infra/dhcp-server-configs/" + VCF.DHCP_SERVER_NAME
                payload = {
                    "display_name": VCF.DHCP_SERVER_NAME,
                    "resource_type": "DhcpServerConfig",
                    "lease_time": 86400,
                    "id": VCF.DHCP_SERVER_NAME,
                }
                headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
                payload_modified = json.dumps(payload, indent=4)
                dhcp_create = requests.request("PUT", url, headers=headers_[1], data=payload_modified, verify=False)
                if dhcp_create.status_code != 200:
                    d = {"responseType": "ERROR", "msg": dhcp_create.text, "STATUS_CODE": dhcp_create.status_code}
                    current_app.logger.error(dhcp_create.text)
                    return jsonify(d), dhcp_create.status_code
                msg_text = "Created DHCP server " + VCF.DHCP_SERVER_NAME
                current_app.logger.info(msg_text)
            else:
                msg_text = VCF.DHCP_SERVER_NAME + " DHCP server is already created"
                current_app.logger.info(msg_text)
        else:
            msg_text = "DHCP server is already present in tier1"
        d = {"responseType": "SUCCESS", "msg": msg_text, "STATUS_CODE": 200}
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Failed to create DHCP server " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create DHCP server " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500


def createNsxtSegment(segementName, gatewayAddress, dhcpStart, dhcpEnd, dnsServers, network, isDhcp):
    try:
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            current_app.logger.error("Failed to get NSXT info " + str(headers_[1]))
            d = {"responseType": "ERROR", "msg": "Failed to get NSXT info " + str(headers_[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            d = {"responseType": "ERROR", "msg": "Failed to get list of segments " + str(output[0]), "STATUS_CODE": 500}
            return jsonify(d), 500
        overlay = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtOverlay"])
        ntp_servers = str(request.get_json(force=True)["envSpec"]["infraComponents"]["ntpServers"])
        trz = getTransportZone(headers_[2], overlay, headers_[1])
        if trz[0] is None:
            d = {"responseType": "ERROR", "msg": "Failed to get transport zone ID " + str(trz[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        tier_path = getTier1Details(headers_)
        if tier_path[0] is None:
            d = {"responseType": "ERROR", "msg": "Failed to get Tier1 details " + str(tier_path[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        if not checkObjectIsPresentAndReturnPath(output[0], segementName)[0]:
            current_app.logger.info("Creating segment " + segementName)
            url = "https://" + headers_[2] + "/policy/api/v1/infra/segments/" + segementName
            if isDhcp:
                payload = {
                    "display_name": segementName,
                    "subnets": [
                        {
                            "gateway_address": gatewayAddress,
                            "dhcp_ranges": [dhcpStart + "-" + dhcpEnd],
                            "dhcp_config": {
                                "resource_type": "SegmentDhcpV4Config",
                                "lease_time": 86400,
                                "dns_servers": convertStringToCommaSeperated(dnsServers),
                                "options": {
                                    "others": [{"code": 42, "values": convertStringToCommaSeperated(ntp_servers)}]
                                },
                            },
                            "network": network,
                        }
                    ],
                    "connectivity_path": tier_path[0],
                    "transport_zone_path": "/infra/sites/default/enforcement-points/default/transport-zones/"
                    + str(trz[0]),
                    "id": segementName,
                }
            else:
                payload = {
                    "display_name": segementName,
                    "subnets": [{"gateway_address": gatewayAddress}],
                    "replication_mode": "MTEP",
                    "transport_zone_path": "/infra/sites/default/enforcement-points/default/transport-zones/"
                    + str(trz[0]),
                    "admin_state": "UP",
                    "advanced_config": {
                        "address_pool_paths": [],
                        "multicast": True,
                        "urpf_mode": "STRICT",
                        "connectivity": "ON",
                    },
                    "connectivity_path": tier_path[0],
                    "id": segementName,
                }
            headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
            payload_modified = json.dumps(payload, indent=4)
            dhcp_create = requests.request("PUT", url, headers=headers_[1], data=payload_modified, verify=False)
            if dhcp_create.status_code != 200:
                d = {"responseType": "ERROR", "msg": dhcp_create.text, "STATUS_CODE": dhcp_create.status_code}
                current_app.logger.error(dhcp_create.text)
                return jsonify(d), dhcp_create.status_code
            msg_text = "Created " + segementName
            current_app.logger.info(msg_text)
            current_app.logger.info("Waiting for 1 min for status == ready")
            time.sleep(60)
        else:
            msg_text = segementName + " is already created"
            current_app.logger.info(msg_text)
        d = {"responseType": "SUCCESS", "msg": msg_text, "STATUS_CODE": 200}
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error("Failed to create Nsxt segment " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to create NSXT segment " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500


def grabNsxtHeaders():
    try:
        str_enc = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtUserPasswordBase64"])
        base64_bytes = str_enc.encode("ascii")
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode("ascii").rstrip("\n")

        ecod_bytes = (request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtUser"] + ":" + password).encode(
            "ascii"
        )
        ecod_bytes = base64.b64encode(ecod_bytes)
        address = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtAddress"])
        ecod_string = ecod_bytes.decode("ascii")
        headers = {"Authorization": ("Basic " + ecod_string)}
        return "SUCCESS", headers, address
    except Exception as e:
        return None, str(e), None


def getList(headers, url):
    payload = {}
    list_all_segments_url = url
    list_all_segments_response = requests.request(
        "GET", list_all_segments_url, headers=headers, data=payload, verify=False
    )
    if list_all_segments_response.status_code != 200:
        return list_all_segments_response.text, list_all_segments_response.status_code

    return list_all_segments_response.json()["results"], 200


def checkObjectIsPresentAndReturnPath(listOfSegments, name):
    try:
        for segmentName in listOfSegments:
            if segmentName["display_name"] == name:
                return True, segmentName["path"]
    except Exception:
        return False, None
    return False, None


def convertStringToCommaSeperated(strA):
    strA = strA.split(",")
    list = []
    for s in strA:
        list.append(s.replace(" ", ""))
    return list


def getTransportZone(address, transport_zone_name, headers_):
    try:
        url = "https://" + address + "/api/v1/transport-zones/"
        payload = {}
        tzone_response = requests.request("GET", url, headers=headers_, data=payload, verify=False)
        if tzone_response.status_code != 200:
            return None, tzone_response.text
        for tzone in tzone_response.json()["results"]:
            if str(tzone["transport_type"]) == "OVERLAY" and str(tzone["display_name"]) == transport_zone_name:
                return tzone["id"], "FOUND"
        return None, "NOT_FOUND"
    except Exception as e:
        return None, str(e)


def getListOfTransportZone(address, headers_):
    try:
        url = "https://" + address + "/api/v1/transport-zones/"
        payload = {}
        tzone_response = requests.request("GET", url, headers=headers_, data=payload, verify=False)
        if tzone_response.status_code != 200:
            return None, tzone_response.text
        tz_zone = []
        for tzone in tzone_response.json()["results"]:
            if str(tzone["transport_type"]) == "OVERLAY":
                tz_zone.append(str(tzone["display_name"]))
        if len(tz_zone) < 1:
            return None, "NOT_FOUND"
        else:
            return tz_zone, "FOUND"
    except Exception as e:
        return None, str(e)


def createGroup(groupName, segmentName, isIp, ipaddresses):
    try:
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            d = {"responseType": "ERROR", "msg": "Failed to get NSXT info " + str(headers_[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        domainName = getDomainName(headers_, "default")
        if domainName[0] is None:
            d = {"responseType": "ERROR", "msg": "Failed to get domain name " + str(domainName[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            d = {"responseType": "ERROR", "msg": "Failed to get list of domain " + str(output[0]), "STATUS_CODE": 500}
            return jsonify(d), 500
        if segmentName is not None:
            uri_ = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
            seg_output = getList(headers_[1], uri_)
            if seg_output[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get list of segments " + str(seg_output[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            seg_obj = checkObjectIsPresentAndReturnPath(seg_output[0], segmentName)
            if not seg_obj[0]:
                d = {"responseType": "ERROR", "msg": "Failed to find the segment " + segmentName, "STATUS_CODE": 500}
                return jsonify(d), 500
        url = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups/" + groupName
        headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
        isPresent = False
        lis_ip = []
        try:
            get_group = requests.request("GET", url, headers=headers_[1], verify=False)
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
        except Exception:
            isPresent = False
        if ipaddresses is not None:
            for ip_ in convertStringToCommaSeperated(ipaddresses):
                lis_ip.append(ip_)
        else:
            lis_ip.append(seg_obj[1])
        obj = checkObjectIsPresentAndReturnPath(output[0], groupName)
        if not obj[0] or not isPresent:
            current_app.logger.info("Creating group " + groupName)
            url = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups/" + groupName
            if isIp == "true":
                if not isPresent and obj[0]:
                    payload = {
                        "display_name": groupName,
                        "expression": [{"resource_type": "IPAddressExpression", "ip_addresses": lis_ip}],
                        "resource_type": "Group",
                        "_revision": int(revision_id),
                    }
                else:
                    payload = {
                        "display_name": groupName,
                        "expression": [
                            {
                                "resource_type": "IPAddressExpression",
                                "ip_addresses": convertStringToCommaSeperated(ipaddresses),
                            }
                        ],
                        "id": groupName,
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
                            "resource_type": "Condition",
                        }
                    ],
                    "id": groupName,
                }
            else:
                if not isPresent and obj[0]:
                    payload = {
                        "display_name": groupName,
                        "expression": [{"resource_type": "PathExpression", "paths": lis_ip}],
                        "resource_type": "Group",
                        "_revision": int(revision_id),
                    }
                else:
                    payload = {
                        "display_name": groupName,
                        "expression": [{"resource_type": "PathExpression", "paths": [seg_obj[1]]}],
                        "id": groupName,
                    }
            headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
            payload_modified = json.dumps(payload, indent=4)
            dhcp_create = requests.request("PUT", url, headers=headers_[1], data=payload_modified, verify=False)
            if dhcp_create.status_code != 200:
                d = {"responseType": "ERROR", "msg": dhcp_create.text, "STATUS_CODE": dhcp_create.status_code}
                current_app.logger.error(dhcp_create.text)
                return jsonify(d), dhcp_create.status_code
            msg_text = "Created group " + groupName
            path = dhcp_create.json()["path"]
        else:
            path = obj[1]
            msg_text = groupName + " group is already created."
        current_app.logger.info(msg_text)
        d = {"responseType": "SUCCESS", "msg": msg_text, "path": path, "STATUS_CODE": 200}
        return jsonify(d), 200
    except Exception as e:
        d = {"responseType": "ERROR", "msg": "Failed to create group " + groupName + " " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500


def getDomainName(headers, domainName):
    url = "https://" + headers[2] + "/policy/api/v1/infra/domains/"
    response = requests.request("GET", url, headers=headers[1], verify=False)
    if response.status_code != 200:
        return None, response.text
    for domain in response.json()["results"]:
        if str(domain["display_name"]) == domainName:
            return domain["display_name"], "FOUND"
    return None, "NOT_FOUND"


def createVipService(serviceName, port):
    headers_ = grabNsxtHeaders()
    if headers_[0] is None:
        d = {"responseType": "ERROR", "msg": "Failed to get NSXT info " + str(headers_[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    service = isServiceCreated(headers_, serviceName)
    if service[0] is None:
        if service[1] != "NOT_FOUND":
            d = {"responseType": "ERROR", "msg": "Failed to get service info " + str(service[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            url = "https://" + headers_[2] + "/policy/api/v1/infra/services/" + serviceName
            headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
            payload = {
                "service_entries": [
                    {
                        "display_name": serviceName,
                        "resource_type": "L4PortSetServiceEntry",
                        "l4_protocol": "TCP",
                        "destination_ports": convertStringToCommaSeperated(port),
                    }
                ],
                "display_name": serviceName,
                "id": serviceName,
            }
            payload_modified = json.dumps(payload, indent=4)
            response = requests.request("PUT", url, headers=headers_[1], data=payload_modified, verify=False)
            if response.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create service " + str(response.text),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        message = "Service created successfully"
    else:
        message = "Service is already created " + service[0]
    current_app.logger.info(message)
    d = {"responseType": "ERROR", "msg": message, "STATUS_CODE": 200}
    return jsonify(d), 200


def isServiceCreated(header, serviceName):
    url = "https://" + header[2] + "/policy/api/v1/infra/services"
    response = requests.request("GET", url, headers=header[1], verify=False)
    if response.status_code != 200:
        return None, response.text
    for service in response.json()["results"]:
        if service["display_name"] == serviceName:
            return service["display_name"], "FOUND"
    return None, "NOT_FOUND"


def createFirewallRule(policyName, ruleName, rulePayLoad):
    headers_ = grabNsxtHeaders()
    if headers_[0] is None:
        d = {"responseType": "ERROR", "msg": "Failed to get NSXT info " + str(headers_[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    policy = getPolicy(headers_, policyName)
    if policy[0] is None:
        if policy[1] != "NOT_FOUND":
            d = {"responseType": "ERROR", "msg": "Failed to get policy " + str(policy[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        else:
            current_app.logger.info("Creating policy " + policyName)
            tier_path = getTier1Details(headers_)
            if tier_path[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
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
                                                "source_groups": ["ANY"],
                                                "sequence_number": 10,
                                                "destination_groups": ["ANY"],
                                                "services": ["ANY"],
                                                "profiles": ["ANY"],
                                                "scope": [tier_path[0]],
                                                "action": "ALLOW",
                                                "direction": "IN_OUT",
                                                "logged": False,
                                                "disabled": False,
                                                "notes": "",
                                                "tag": "",
                                                "ip_protocol": "IPV4_IPV6",
                                            },
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
            payload_modified = json.dumps(payload, indent=4)
            headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
            response = requests.request("PATCH", url, headers=headers_[1], data=payload_modified, verify=False)
            if response.status_code != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to create policy " + str(response.text),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
    else:
        current_app.logger.info(policyName + " policy is already created")
    list_fw = getListOfFirewallRule(headers_, policyName)
    if list_fw[0] is None:
        d = {"responseType": "ERROR", "msg": "Failed to get list of firewalls " + str(list_fw[1]), "STATUS_CODE": 500}
        return jsonify(d), 500
    if not checkObjectIsPresentAndReturnPath(list_fw[0], ruleName)[0]:
        current_app.logger.info("Creating firewall rule " + ruleName)
        rule_payload_modified = json.dumps(rulePayLoad, indent=4)
        url = (
            "https://"
            + headers_[2]
            + "/policy/api/v1/infra/domains/default/gateway-policies/"
            + policyName
            + "/rules/"
            + ruleName
        )
        headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
        response = requests.request("PUT", url, headers=headers_[1], data=rule_payload_modified, verify=False)
        if response.status_code != 200:
            d = {"responseType": "ERROR", "msg": "Failed to create rule " + str(response.text), "STATUS_CODE": 500}
            return jsonify(d), 500
        msg_text = ruleName + " rule created successfully"
    else:
        msg_text = ruleName + " rule is already created"
    current_app.logger.info(msg_text)
    d = {"responseType": "SUCCESS", "msg": msg_text, "STATUS_CODE": 200}
    return jsonify(d), 200


def getListOfFirewallRule(headers, policyName):
    url = "https://" + headers[2] + "/policy/api/v1/infra/domains/default/gateway-policies/" + policyName + "/rules"
    response = requests.request("GET", url, headers=headers[1], verify=False)
    if response.status_code != 200:
        return None, response.text
    return response.json()["results"], "FOUND"


def updateDefaultRule(policyName):
    try:
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            d = {"responseType": "ERROR", "msg": "Failed to get NSXT info " + str(headers_[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        list_fw = getListOfFirewallRule(headers_, policyName)
        if list_fw[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get list of firewalls " + str(list_fw[1]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        sequence = None
        for rule in list_fw[0]:
            if rule["display_name"] == "default_rule":
                sequence = rule["sequence_number"]
                break
        if sequence is None:
            d = {"responseType": "ERROR", "msg": "Failed to get sequence number of default rule ", "STATUS_CODE": 500}
            return jsonify(d), 500
        tier_path = getTier1Details(headers_)
        if tier_path[0] is None:
            d = {"responseType": "ERROR", "msg": "Failed to get Tier1 details " + str(tier_path[1]), "STATUS_CODE": 500}
            return jsonify(d), 500
        url = (
            "https://"
            + headers_[2]
            + "/policy/api/v1/infra/domains/default/gateway-policies/"
            + policyName
            + "/rules/default_rule"
        )
        payload = {
            "sequence_number": sequence,
            "source_groups": ["ANY"],
            "services": ["ANY"],
            "logged": False,
            "destination_groups": ["ANY"],
            "scope": [tier_path[0]],
            "action": "DROP",
        }
        payload_modified = json.dumps(payload, indent=4)
        headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})
        response = requests.request("PATCH", url, headers=headers_[1], data=payload_modified, verify=False)
        if response.status_code != 200:
            d = {"responseType": "ERROR", "msg": "Failed to create policy " + str(response.text), "STATUS_CODE": 500}
            return jsonify(d), 500
        d = {"responseType": "SUCCESS", "msg": "Successfully updated default rule", "STATUS_CODE": 200}
        return jsonify(d), 200
    except Exception as e:
        d = {"responseType": "ERROR", "msg": "Failed to update default rule " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500


def fetchTMCHeaders(env):
    if env == Env.VMC:
        refreshToken = request.get_json(force=True)["saasEndpoints"]["tmcDetails"]["tmcRefreshToken"]
        tmc_url = request.get_json(force=True)["saasEndpoints"]["tmcDetails"]["tmcInstanceURL"]
    else:
        refreshToken = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcRefreshToken"]
        tmc_url = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tmcDetails"]["tmcInstanceURL"]

    if not tmc_url or not refreshToken:
        return None, "TMC details missing"

    if not tmc_url.endswith("/"):
        tmc_url = tmc_url + "/"

    # url = VeleroAPI.GET_ACCESS_TOKEN.format(tmc_token=refreshToken)
    url = TmcConstants.TMC_LOGIN_API.format(refresh_token=refreshToken)
    headers = {}
    payload = {}
    response_login = requests.request("POST", url, headers=headers, data=payload, verify=False)
    if response_login.status_code != 200:
        current_app.logger.error("TMC login failed using Refresh_Token - %s" % refreshToken)
        return None, "TMC Login failed using Refresh_Token " + refreshToken

    access_token = response_login.json()["access_token"]

    headers = {"Content-Type": "application/json", "Authorization": access_token}

    return headers, tmc_url


def getPolicy(headers, policyName):
    url = "https://" + headers[2] + "/policy/api/v1/infra/domains/default/gateway-policies"
    response = requests.request("GET", url, headers=headers[1], verify=False)
    if response.status_code != 200:
        return None, response.text
    try:
        for pol in response.json()["results"]:
            if pol["display_name"] == policyName:
                return pol["display_name"], "FOUND"
        return None, "NOT_FOUND"
    except Exception:
        return None, "NOT_FOUND"


def getTier1Details(headers_):
    uri = "https://" + headers_[2] + "/policy/api/v1/infra/tier-1s"
    response = requests.request("GET", uri, headers=headers_[1], verify=False)
    if response.status_code != 200:
        return None, response.status_code
    teir1name = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["nsxtTier1RouterDisplayName"])
    for tr in response.json()["results"]:
        if str(tr["display_name"]).lower() == teir1name.lower():
            return tr["path"], "FOUND"
    return None, "NOT_FOUND"


def getNetworkIp(gatewayAddress):
    ipNet = seperateNetmaskAndIp(gatewayAddress)
    ss = ipNet[0].split(".")
    return ss[0] + "." + ss[1] + "." + ss[2] + ".0" + "/" + ipNet[1]


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(
        fcntl.ioctl(s.fileno(), 0x8915, struct.pack("256s", ifname[:15].encode("utf-8")))[20:24]  # SIOCGIFADDR
    )


def is_ipv4(string):
    try:
        ipaddress.IPv4Network(string)
        return True
    except ValueError:
        return False


def getIpFromHost(vcenter):
    try:
        return socket.gethostbyname(vcenter)
    except Exception:
        return None


def getHostFromIP(ip):
    try:
        host = socket.gethostbyaddr(ip)
        return list(host)[0]
    except Exception:
        return None


def getESXIips():
    try:
        str_enc = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode("ascii")
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode("ascii").rstrip("\n")

        ecod_bytes = (
            request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterSsoUser"] + ":" + password
        ).encode("ascii")
        ecod_bytes = base64.b64encode(ecod_bytes)
        address = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterAddress"])
        ecod_string = ecod_bytes.decode("ascii")
        uri = "https://" + address + "/api/session"
        headers = {"Authorization": ("Basic " + ecod_string)}
        response = requests.request("POST", uri, headers=headers, verify=False)
        if response.status_code != 201:
            return None, response.status_code
        url = "https://" + address + "/api/vcenter/host"
        header = {"vmware-api-session-id": response.json()}
        response = requests.request("GET", url, headers=header, verify=False)
        if response.status_code != 200:
            return None, response.text
        ips = ""
        for esx in response.json():
            if not is_ipv4(esx):
                ips += getIpFromHost(esx["name"]) + ","
            else:
                ips += esx["name"] + ","
        if not ips:
            return None, "EMPTY"
        return ips.strip(","), "SUCCESS"
    except Exception as e:
        return None, str(e)


def verify_host_count(vCenter_cluster):
    try:
        count = len(vCenter_cluster.host)
        if count >= 3:
            return "SUCCESS", 200
        else:
            return None, vCenter_cluster.name + " has less than 3 hosts."
    except Exception as e:
        return None, str(e)


def verifyVCVersion(vcVersion):
    try:
        baseVersionArr = Versions.vcenter.split(".")
        vcVersionArr = vcVersion.split(".")
        i = 0
        for str in vcVersionArr:
            if int(str) > int(baseVersionArr[i]):
                return "SUCCESS", 200
            elif int(str) == int(baseVersionArr[i]):
                i = i + 1
            else:
                return None, "vCenter Version must be greater than or equal to " + Versions.vcenter
        return "SUCCESS", 200
    except Exception as e:
        return None, str(e)


def verifyVcenterVersion(version):
    vCenter = current_app.config["VC_IP"]
    vCenter_user = current_app.config["VC_USER"]
    VC_PASSWORD = current_app.config["VC_PASSWORD"]
    si = connect.SmartConnectNoSSL(host=vCenter, user=vCenter_user, pwd=VC_PASSWORD)
    content = si.RetrieveContent()
    vcVersion = content.about.version
    if vcVersion.startswith(version):
        return True
    else:
        return False


def file_as_bytes(file):
    with file:
        return file.read()


def getOvaMarketPlace(filename, refreshToken, version, baseOS):
    filename = filename + ".ova"
    solutionName = KubernetesOva.MARKETPLACE_KUBERNETES_SOLUTION_NAME
    if baseOS == "photon":
        ova_groupname = KubernetesOva.MARKETPLACE_PHOTON_GROUPNAME
    else:
        ova_groupname = KubernetesOva.MARKETPLACE_UBUTNU_GROUPNAME

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {"refreshToken": refreshToken}
    json_object = json.dumps(payload, indent=4)
    sess = requests.request(
        "POST", MarketPlaceUrl.URL + "/api/v1/user/login", headers=headers, data=json_object, verify=False
    )
    if sess.status_code != 200:
        return None, "Failed to login and obtain csp-auth-token"
    else:
        token = sess.json()["access_token"]

    headers = {"Accept": "application/json", "Content-Type": "application/json", "csp-auth-token": token}

    objectid = None
    ovaName = None
    app_version = None
    metafileid = None
    slug = "true"

    _solutionName = getProductSlugId(MarketPlaceUrl.TANZU_PRODUCT, headers)
    if _solutionName[0] is None:
        return None, "Failed to find product on Marketplace " + str(_solutionName[1])
    solutionName = _solutionName[0]
    product = requests.get(
        MarketPlaceUrl.API_URL + "/products/" + solutionName + "?isSlug=" + slug + "&ownorg=false",
        headers=headers,
        verify=False,
    )

    if product.status_code != 200:
        return None, "Failed to Obtain Product ID"
    else:
        product_id = product.json()["response"]["data"]["productid"]
        for metalist in product.json()["response"]["data"]["metafilesList"]:
            if metalist["version"] == version[1:] and str(metalist["groupname"]).strip("\t") == ova_groupname:
                objectid = metalist["metafileobjectsList"][0]["fileid"]
                ovaName = metalist["metafileobjectsList"][0]["filename"]
                app_version = metalist["appversion"]
                metafileid = metalist["metafileid"]

    if (objectid or ovaName or app_version or metafileid) is None:
        return None, "Failed to find the file details in Marketplace"

    current_app.logger.info("Downloading kubernetes ova - " + ovaName)

    payload = {
        "eulaAccepted": "true",
        "appVersion": app_version,
        "metafileid": metafileid,
        "metafileobjectid": objectid,
    }

    json_object = json.dumps(payload, indent=4).replace('"true"', "true")
    presigned_url = requests.request(
        "POST",
        MarketPlaceUrl.URL + "/api/v1/products/" + product_id + "/download",
        headers=headers,
        data=json_object,
        verify=False,
    )
    if presigned_url.status_code != 200:
        return None, "Failed to obtain pre-signed URL"
    else:
        download_url = presigned_url.json()["response"]["presignedurl"]

    response_csfr = requests.request("GET", download_url, headers=headers, verify=False, timeout=600)
    if response_csfr.status_code != 200:
        return None, response_csfr.text
    else:
        os.system("rm -rf " + "/tmp/" + filename)
        with open(r"/tmp/" + filename, "wb") as f:
            f.write(response_csfr.content)

    return filename, "Kubernetes OVA download successful"


def isEnvTkgs_wcp(env):
    try:
        if env == Env.VSPHERE:
            tkgs = str(request.get_json(force=True)["envSpec"]["envType"])
            if tkgs.lower() == EnvType.TKGS_WCP:
                return True
            else:
                return False
        else:
            return False
    except KeyError:
        return False


def isEnvTkgs_ns(env):
    try:
        if env == Env.VSPHERE:
            tkgs = str(request.get_json(force=True)["envSpec"]["envType"])
            if tkgs.lower() == EnvType.TKGS_NS:
                return True
            else:
                return False
        else:
            return False
    except KeyError:
        return False


def isEnvTkgm(env):
    try:
        if env == Env.VSPHERE:
            tkgs = str(request.get_json(force=True)["envSpec"]["envType"])
            if tkgs.lower() == EnvType.TKGM:
                return True
            else:
                return False
        else:
            return True
    except KeyError:
        return False


def check_tkgs_proxy_enabled():
    proxyEnabled = False
    try:
        isProxyEnabled = request.get_json(force=True)["tkgsComponentSpec"]["tkgServiceConfig"]["proxySpec"][
            "enableProxy"
        ]
        if str(isProxyEnabled).lower() == "true":
            proxyEnabled = True
        else:
            proxyEnabled = False

        return proxyEnabled
    except Exception:
        return False


def getSub_tumbprint():
    current_app.logger.info("Fetching thumbprint for subscribed content library repo")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    wrappedSocket = ssl.wrap_socket(sock)
    # url = "https://wp-content.vmware.com/v2/latest/lib.json"
    url = "wp-content.vmware.com"
    try:
        wrappedSocket.connect(url, 443)
    except Exception:
        current_app.logger.error("Connection to " + url + " failed")
        return 500

    der_cert_bin = wrappedSocket.getpeercert(True)

    # Thumbprint
    thumb_sha1 = hashlib.sha1(der_cert_bin).hexdigest()
    wrappedSocket.close()
    if thumb_sha1:
        thumb_sha1 = thumb_sha1.upper()
        thumb_sha1 = ":".join(thumb_sha1[i : i + 2] for i in range(0, len(thumb_sha1), 2))
        current_app.logger.info("SHA1 for subscribed content library repo: " + thumb_sha1)
        return thumb_sha1
    else:
        current_app.logger.error("Failed to obtain SHA1 for the repo")
        return 500


def getNetworkUrl(ip, csrf2, name, cloudName, aviVersion):
    with open("./newCloudInfo.json", "r") as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except KeyError:
        for res in new_cloud_json["results"]:
            if res["name"] == cloudName:
                uuid = res["uuid"]
    if uuid is None:
        return None, "Failed", "ERROR"
    url = "https://" + ip + "/api/network-inventory/?cloud_ref.uuid=" + uuid
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
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
            current_app.logger.info("Waited for " + str(count * 10) + "s retrying")
        if response_csrf is None:
            current_app.logger.info("Waited for " + str(count * 10) + "s but service engine is not up")
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


def getNetworkDetails(
    ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask, isSeRequired, aviVersion, env="vsphere"
):
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    details = {}
    if response_csrf.status_code != 200:
        details["error"] = response_csrf.text
        return None, "Failed", details
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        details["vim_ref"] = response_csrf.json()["vimgrnw_ref"]
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        return "AlreadyConfigured", 200, details
    except Exception:
        current_app.logger.info("Ip pools are not configured, configuring it")

    os.system("rm -rf managementNetworkDetails.json")
    with open("./managementNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    if isSeRequired:
        generateVsphereConfiguredSubnetsForSe("managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))
    else:
        if env == Env.VSPHERE:
            generateVsphereConfiguredSubnets("managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))
        else:
            generateVsphereConfiguredSubnetsForSeandVIP(
                "managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask)
            )

    return "SUCCESS", 200, details


def getDetailsOfNewCloud(ip, csrf2, newCloudUrl, vim_ref, captured_ip, captured_mask, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    url = newCloudUrl
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        os.system("rm -rf detailsOfNewCloud.json")
        with open("./detailsOfNewCloud.json", "w") as outfile:
            outfile.write(json_object)
        replaceValueSysConfig("detailsOfNewCloud.json", "vcenter_configuration", "management_network", vim_ref)
        ip_val = dict(ip_addr=dict(addr=captured_ip, type="V4"), mask=captured_mask)
        replaceValueSysConfig("detailsOfNewCloud.json", "vcenter_configuration", "management_ip_subnet", ip_val)
        return response_csrf.json(), "SUCCESS"


def updateNetworkWithIpPools(ip, csrf2, managementNetworkUrl, fileName, aviVersion):
    with open(fileName, "r") as openfile:
        json_object = json.load(openfile)
    json_object_m = json.dumps(json_object, indent=4)
    url = managementNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    details = {}
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        count = 0
        if response_csrf.text.__contains__(
            "Cannot edit network properties till network sync from Service Engines is complete"
        ):
            while count < 10:
                time.sleep(60)
                response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
                if response_csrf.status_code == 200:
                    break
                current_app.logger.info("waited for " + str(count * 60) + "s sync to complete")
                count = count + 1
        else:
            return 500, response_csrf.text, details
    details["subnet_ip"] = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
    details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
    details["vimref"] = response_csrf.json()["vimgrnw_ref"]
    return 200, "SUCCESS", details


def getDetailsOfNewCloudAddIpam(ip, csrf2, newCloudUrl, ipamUrl, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    url = newCloudUrl
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_object = json.dumps(response_csrf.json(), indent=4)
        os.system("rm -rf detailsOfNewCloudIpam.json")
        with open("./detailsOfNewCloudIpam.json", "w") as outfile:
            outfile.write(json_object)
        with open("detailsOfNewCloudIpam.json") as f:
            data = json.load(f)
        data["ipam_provider_ref"] = ipamUrl
        with open("detailsOfNewCloudIpam.json", "w") as f:
            json.dump(data, f)
        return response_csrf.json(), "SUCCESS"


def updateNewCloud(ip, csrf2, newCloudUrl, aviVersion):
    with open("./detailsOfNewCloud.json", "r") as file2:
        new_cloud_json = json.load(file2)
    json_object = json.dumps(new_cloud_json, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), "SUCCESS"


def getClusterUrl(ip, csrf2, cluster_name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    url = "https://" + ip + "/api/vimgrclusterruntime"
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for cluster in response_csrf.json()["results"]:
            if cluster["name"] == cluster_name:
                return cluster["url"], "SUCCESS"

        return "NOT_FOUND", "FAILED"


def getIpam(ip, csrf2, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    url = "https://" + ip + "/api/ipamdnsproviderprofile"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for res in response_csrf.json()["results"]:
            if res["name"] == name:
                return res["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def getStoragePolicies(vCenter, vCenter_user, VC_PASSWORD):
    url = "https://" + vCenter + "/"
    try:
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        else:
            vc_session = sess.json()["value"]

        header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": vc_session}
        storage_policies = requests.request("GET", url + "api/vcenter/storage/policies", headers=header, verify=False)
        if storage_policies.status_code != 200:
            d = {"responseType": "ERROR", "msg": "Failed to fetch storage policies", "STATUS_CODE": 500}
            return jsonify(d), 500

        return storage_policies.json(), 200

    except Exception as e:
        current_app.logger.error(e)
        d = {"responseType": "ERROR", "msg": "Exception occurred while fetching storage policies", "STATUS_CODE": 500}
        return jsonify(d), 500


def getPolicyID(policyname, vcenter, vc_user, vc_password):
    try:
        policies = getStoragePolicies(vcenter, vc_user, vc_password)
        for policy in policies[0]:
            if policy["name"] == policyname:
                return policy["policy"], 200
        else:
            current_app.logger.error("Provided policy not found - " + policyname)
            return None, 500
    except Exception as e:
        current_app.logger.error(e)
        return None, 500


def cidr_to_netmask(cidr):
    try:
        return str(ipaddress.IPv4Network(cidr, False).netmask)
    except Exception as e:
        current_app.logger.error(e)
        return None


def getCountOfIpAdress(gatewayCidr, start, end):
    from ipaddress import ip_interface, ip_network

    list1 = list(ip_network(gatewayCidr, False).hosts())
    count = 0
    for item in list1:
        if ip_interface(item) > ip_interface(end):
            break
        if ip_interface(item) >= ip_interface(start):
            count = count + 1
    return count


def getLibraryId(vcenter, vcenterUser, vcenterPassword, libName):
    os.putenv("GOVC_URL", "https://" + vcenter + "/sdk")
    os.putenv("GOVC_USERNAME", vcenterUser)
    os.putenv("GOVC_PASSWORD", vcenterPassword)
    os.putenv("GOVC_INSECURE", "true")
    list1 = ["govc", "library.info", "/" + libName]
    list2 = ["grep", "-w", "ID"]
    libId = grabPipeOutput(list1, list2)
    if libId[1] != 0:
        current_app.logger.error(libId[0])
        return None
    return libId[0].replace("ID:", "").strip()


def updateIpam(ip, csrf2, newCloudUrl, aviVersion):
    with open("./detailsOfNewCloudIpam.json", "r") as file2:
        new_cloud_json = json.load(file2)
    json_object = json.dumps(new_cloud_json, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), "SUCCESS"


def getAviCertificate(ip, csrf2, certName, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    body = {}
    url = "https://" + ip + "/api/sslkeyandcertificate"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        current_app.logger.error("Failed to get certificate " + response_csrf.text)
        return None, response_csrf.text
    else:
        for res in response_csrf.json()["results"]:
            if res["name"] == certName:
                return res["certificate"]["certificate"], "SUCCESS"
    return "NOT_FOUND", "FAILED"


def checkAndWaitForAllTheServiceEngineIsUp(ip, clodName, env, aviVersion):
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new password")
        return None, "Failed to get csrf from new password"
    with open("./newCloudInfo.json", "r") as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except Exception:
        for res in new_cloud_json["results"]:
            if res["name"] == clodName:
                uuid = res["uuid"]
    if uuid is None:
        return None, "Failed", "ERROR"
    url = "https://" + ip + "/api/serviceengine-inventory/?cloud_ref.uuid=" + str(uuid)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    payload = {}
    count = 0
    seCount = 0
    response_csrf = None
    current_app.logger.info("Checking if all services are up.")
    while count < 60:
        try:
            current_app.logger.info("Waited for " + str(count * 10) + "s retrying")
            response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
            length = len(response_csrf.json()["results"])
            if response_csrf.status_code == 200:
                for se in response_csrf.json()["results"]:
                    if str(se["runtime"]["se_connected"]).strip().lower() == "true":
                        seCount = seCount + 1
                        if seCount == length:
                            break
            if seCount == length:
                break
        except Exception:
            pass
        count = count + 1
        time.sleep(10)
    if response_csrf is None:
        current_app.logger.info("Waited for " + str(count * 10) + "s but service engine is not up")
        return None, "Failed", "ERROR"
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    elif count >= 59:
        return None, "NOT_FOUND", "TIME_OUT"
    else:
        current_app.logger.info("All services are up and running")
        return "SUCCESS", "CHECKED", "UP"


def supervisorTMC(vcenter_user, VC_PASSWORD, cluster_ip):
    command = ["tanzu", "config", "server", "list"]
    server_list = runShellCommandAndReturnOutputAsList(command)
    if server_list[1] != 0:
        return " Failed to get list of logins " + str(server_list[0]), 500
    if str(server_list[0]).__contains__(cluster_ip):
        delete_response = TanzuUtil.delete_config_server(cluster_ip)
        if delete_response[1] != 200:
            current_app.logger.info("Server config delete failed")
            return "Server config delete failed", 500
    current_app.logger.info("Logging in to cluster " + cluster_ip)
    os.putenv("KUBECTL_VSPHERE_PASSWORD", VC_PASSWORD)
    connect_command = [
        "kubectl",
        "vsphere",
        "login",
        "--server=" + cluster_ip,
        "--vsphere-username=" + vcenter_user,
        "--insecure-skip-tls-verify",
    ]
    output = runShellCommandAndReturnOutputAsList(connect_command)
    if output[1] != 0:
        return " Failed while connecting to Supervisor Cluster", 500
    switch_context = ["kubectl", "config", "use-context", cluster_ip]
    output = runShellCommandAndReturnOutputAsList(switch_context)
    if output[1] != 0:
        return " Failed to use  context " + str(output[0]), 500

    switch_context = [
        "tanzu",
        "login",
        "--name",
        cluster_ip,
        "--kubeconfig",
        "/root/.kube/config",
        "--context",
        cluster_ip,
    ]
    output = runShellCommandAndReturnOutputAsList(switch_context)
    if output[1] != 0:
        return " Failed to switch context to Supervisor Cluster " + str(output[0]), 500
    return "SUCCESS", 200


"""def getClusterId(vc_session, clusterName, vcenter_ip):
    url = "https://" + vcenter_ip + "/api/vcenter/cluster"
    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "vmware-api-session-id": vc_session
    }
    try:
        response_csfr = requests.request("GET", url, headers=header, verify=False)
        if response_csfr.status_code != 200:
            return None, "Failed to get cluster list " + str(response_csfr.text)
        for cluster in response_csfr.json():
            if cluster['name'] == clusterName:
                return cluster['cluster'], "FOUND"
        return None, "NOT_FOUND"
    except Exception  as e:
        return None, str(e)"""


def getClusterID(vCenter, vCenter_user, VC_PASSWORD, cluster):
    url = "https://" + vCenter + "/"
    try:
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        else:
            session_id = sess.json()["value"]

        vcenter_datacenter = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterDatacenter"]
        if str(vcenter_datacenter).__contains__("/"):
            vcenter_datacenter = vcenter_datacenter[vcenter_datacenter.rindex("/") + 1 :]
        if str(cluster).__contains__("/"):
            cluster = cluster[cluster.rindex("/") + 1 :]
        datcenter_resp = requests.get(
            url + "api/vcenter/datacenter?names=" + vcenter_datacenter,
            verify=False,
            headers={"vmware-api-session-id": session_id},
        )
        if datcenter_resp.status_code != 200:
            current_app.logger.error(datcenter_resp.json())
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch datacenter ID for datacenter - " + vcenter_datacenter,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        datacenter_id = datcenter_resp.json()[0]["datacenter"]

        clusterID_resp = requests.get(
            url + "api/vcenter/cluster?names=" + cluster + "&datacenters=" + datacenter_id,
            verify=False,
            headers={"vmware-api-session-id": session_id},
        )
        if clusterID_resp.status_code != 200:
            current_app.logger.error(clusterID_resp.json())
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch cluster ID for cluster - " + cluster,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        return clusterID_resp.json()[0]["cluster"], 200

    except Exception as e:
        current_app.logger.error(e)
        d = {"responseType": "ERROR", "msg": "Failed to fetch cluster ID for cluster - " + cluster, "STATUS_CODE": 500}
        return jsonify(d), 500


def getBodyResourceSpec(cpu_limit, memory_limit, storage_limit):
    resource_spec = dict()
    if cpu_limit:
        resource_spec.update({"cpu_limit": cpu_limit})
    if memory_limit:
        resource_spec.update({"memory_limit": memory_limit})
    if storage_limit:
        resource_spec.update({"storage_request_limit": storage_limit})
    return resource_spec


def getProductSlugId(productName, headers):
    try:
        product = requests.get(MarketPlaceUrl.PRODUCT_SEARCH_URL, headers=headers, verify=False)
        if product.status_code != 200:
            return None, "Failed to search  product " + productName + " on Marketplace."
        for pro in product.json()["response"]["dataList"]:
            if str(pro["displayname"]) == productName:
                return str(pro["slug"]), "SUCCESS"
    except Exception as e:
        return None, str(e)


def isAviHaEnabled(env):
    try:
        if env == Env.VCD:
            deploy_avi = str(request.get_json(force=True)["envSpec"]["aviCtrlDeploySpec"]["deployAvi"])
            if deploy_avi.lower() == "false":
                enable_avi_ha = "false"
            else:
                enable_avi_ha = str(
                    request.get_json(force=True)["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["enableAviHa"]
                )
        elif env == Env.VMC:
            enable_avi_ha = request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["enableAviHa"]
        elif isEnvTkgs_wcp(env):
            enable_avi_ha = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["enableAviHa"]
        else:
            enable_avi_ha = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["enableAviHa"]
        if str(enable_avi_ha).lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def connect_to_workload(vCenter, vcenter_username, password, cluster, workload_name):
    try:
        current_app.logger.info("Connecting to workload cluster...")
        cluster_id = getClusterID(vCenter, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[0])
            return None, cluster_id[0].json["msg"]

        cluster_namespace = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
            "tkgsVsphereWorkloadClusterSpec"
        ]["tkgsVsphereNamespaceName"]
        cluster_id = cluster_id[0]
        wcp_status = isWcpEnabled(cluster_id)
        if wcp_status[0]:
            endpoint_ip = wcp_status[1]["api_server_cluster_endpoint"]
        else:
            return None, "Failed to obtain cluster endpoint IP on given cluster - " + workload_name
        current_app.logger.info("logging into cluster - " + endpoint_ip)
        os.putenv("KUBECTL_VSPHERE_PASSWORD", password)
        connect_command = [
            "kubectl",
            "vsphere",
            "login",
            "--vsphere-username",
            vcenter_username,
            "--server",
            endpoint_ip,
            "--tanzu-kubernetes-cluster-name",
            workload_name,
            "--tanzu-kubernetes-cluster-namespace",
            cluster_namespace,
            "--insecure-skip-tls-verify",
        ]
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            current_app.logger.error(output[0])
            return None, "Failed to login to cluster endpoint - " + endpoint_ip

        switch_context = ["kubectl", "config", "use-context", workload_name]
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            current_app.logger.error(context_output[0])
            return None, "Failed to login to cluster context - " + workload_name
        return "SUCCESS", "Successfully connected to workload cluster"
    except Exception:
        return None, "Exception occurred while connecting to workload cluster"


def isWcpEnabled(cluster_id):
    vcenter_ip = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterAddress"]
    vcenter_username = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterSsoUser"]
    str_enc = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterSsoPasswordBase64"])
    base64_bytes = str_enc.encode("ascii")
    enc_bytes = base64.b64decode(base64_bytes)
    password = enc_bytes.decode("ascii").rstrip("\n")
    if not (vcenter_ip or vcenter_username or password):
        return False, "Failed to fetch VC details"

    sess = requests.post(
        "https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session", auth=(vcenter_username, password), verify=False
    )
    if sess.status_code != 200:
        current_app.logger.error("Connection to vCenter failed")
        return False, "Connection to vCenter failed"
    else:
        vc_session = sess.json()["value"]

    header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": vc_session}
    url = "https://" + vcenter_ip + "/api/vcenter/namespace-management/clusters/" + cluster_id
    response_csrf = requests.request("GET", url, headers=header, verify=False)
    if response_csrf.status_code != 200:
        if response_csrf.status_code == 400:
            if (
                response_csrf.json()["messages"][0]["default_message"]
                == "Cluster with identifier " + cluster_id + " does "
                "not have Workloads enabled."
            ):
                return False, None

    elif response_csrf.json()["config_status"] == "RUNNING":
        return True, response_csrf.json()
    else:
        return False, None


def isClusterRunning(vcenter_ip, vcenter_username, password, cluster, workload_name):
    try:
        current_app.logger.info("Check if cluster is in running state - " + workload_name)

        cluster_id = getClusterID(vcenter_ip, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[0])
            d = {"responseType": "ERROR", "msg": cluster_id[0], "STATUS_CODE": 500}
            return jsonify(d), 500

        cluster_id = cluster_id[0]

        wcp_status = isWcpEnabled(cluster_id)
        if wcp_status[0]:
            endpoint_ip = wcp_status[1]["api_server_cluster_endpoint"]
        else:
            current_app.logger.error("WCP not enabled on given cluster - " + cluster)
            d = {"responseType": "ERROR", "msg": "WCP not enabled on given cluster - " + cluster, "STATUS_CODE": 500}
            return jsonify(d), 500

        current_app.logger.info("logging into cluster - " + endpoint_ip)
        os.putenv("KUBECTL_VSPHERE_PASSWORD", password)
        connect_command = [
            "kubectl",
            "vsphere",
            "login",
            "--server=" + endpoint_ip,
            "--vsphere-username=" + vcenter_username,
            "--insecure-skip-tls-verify",
        ]
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            current_app.logger.error("Failed while connecting to Supervisor Cluster ")
            d = {"responseType": "ERROR", "msg": "Failed while connecting to Supervisor Cluster", "STATUS_CODE": 500}
            return jsonify(d), 500
        switch_context = ["kubectl", "config", "use-context", endpoint_ip]
        output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            current_app.logger.error("Failed to use  context " + str(output[0]))
            d = {"responseType": "ERROR", "msg": "Failed to use context " + str(output[0]), "STATUS_CODE": 500}
            return jsonify(d), 500

        name_space = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
            "tkgsVsphereWorkloadClusterSpec"
        ]["tkgsVsphereNamespaceName"]
        cluster_kind = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
            "tkgsVsphereWorkloadClusterSpec"
        ]["tkgsVsphereWorkloadClusterKind"]
        if cluster_kind == EnvType.TKGS_CLUSTER_CLASS_KIND:
            get_cluster_command = ["tanzu", "cluster", "list"]
        else:
            get_cluster_command = ["kubectl", "get", "tkc", "-n", name_space]
        clusters_output = runShellCommandAndReturnOutputAsList(get_cluster_command)
        if clusters_output[1] != 0:
            current_app.logger.error("Failed to fetch cluster running status " + str(clusters_output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch cluster running status " + str(clusters_output[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        index = None
        for item in range(len(clusters_output[0])):
            if clusters_output[0][item].split()[0] == workload_name:
                index = item
                break

        if index is None:
            current_app.logger.error("Unable to find cluster - " + workload_name)
            d = {"responseType": "ERROR", "msg": "Unable to find cluster - " + workload_name, "STATUS_CODE": 500}
            return jsonify(d), 500

        output = clusters_output[0][index].split()
        if cluster_kind == EnvType.TKGS_CLUSTER_CLASS_KIND:
            if not (output[2] == "running"):
                current_app.logger.error("Failed to fetch workload cluster running status " + str(clusters_output[0]))
                current_app.logger.error("Found below Cluster status - " + output[2])
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch workload cluster running status " + str(clusters_output[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        else:
            if not ((output[5] == "True" or output[5] == "running") and output[6] == "True"):
                current_app.logger.error("Failed to fetch workload cluster running status " + str(clusters_output[0]))
                current_app.logger.error("Found below Cluster status - ")
                current_app.logger.error("READY: " + str(output[5]) + " and TKR COMPATIBLE: " + str(output[6]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to fetch workload cluster running status " + str(clusters_output[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500

        d = {"responseType": "SUCCESS", "msg": "Workload cluster is in running status.", "STATUS_CODE": 200}
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching the status of workload cluster",
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500


def getAviIpFqdnDnsMapping(avi_controller_fqdn_ip_dict, dns_server):
    try:
        for dns in dns_server:
            dns = dns.strip()
            for avi_fqdn, avi_ip in avi_controller_fqdn_ip_dict.items():
                listOfCmd = ["dig", f"@{dns}", avi_fqdn, "+short"]
                fqdn_ip_map = runShellCommandAndReturnOutputAsList(listOfCmd)
                current_app.logger.info(fqdn_ip_map)
                for ip in fqdn_ip_map[0]:
                    if not ip and not str(ip).__contains__(avi_ip):
                        return "DNS Entry not found for : " + avi_fqdn, 500
                    else:
                        current_app.logger.info("Found DNS entry for " + avi_fqdn + " : " + ip)
                        # avi_controller_fqdn_ip_dict.pop(avi_fqdn)
        return "Successfully validated NSX ALB Fqdn and Ip entry on DNS Server", 200
    except Exception:
        return None, 500


def checkNtpServerValidity(ntp_server):
    try:
        for ntp in ntp_server:
            ntp_obj = ntplib.NTPClient()
            response = ntp_obj.request(ntp.strip())
            if response:
                current_app.logger.info(ctime(response.tx_time))
                current_app.logger.info("Successfully validated NTP Server " + ntp)
            else:
                current_app.logger.info("Failed in validating NTP Server")
                return "Failed in validating NTP Server", 500
        return "Successfully validated NTP Server", 200
    except Exception as e:
        return str(e), 500


def fetchNamespaceInfo(env):
    try:
        if env == Env.VSPHERE:
            vCenter = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterAddress"]
            vCenter_user = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterSsoUser"]
            str_enc = str(request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode("ascii")
            enc_bytes = base64.b64decode(base64_bytes)
            VC_PASSWORD = enc_bytes.decode("ascii").rstrip("\n")
            name_space = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
                "tkgsVsphereNamespaceName"
            ]

            if not (vCenter or vCenter_user or VC_PASSWORD):
                current_app.logger.error("Failed to fetch VC details")
                d = {"responseType": "ERROR", "msg": "Failed to find VC details", "STATUS_CODE": 500}
                return jsonify(d), 500
        else:
            current_app.logger.error("Wrong environment provided to fetch namespace details")
            d = {
                "responseType": "ERROR",
                "msg": "Wrong environment provided to fetch namespace details",
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        url = "https://" + vCenter + "/"
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        else:
            vc_session = sess.json()["value"]

        header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": vc_session}
        namespace_response = requests.request(
            "GET", url + "api/vcenter/namespaces/instances/" + name_space, headers=header, verify=False
        )
        if namespace_response.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch details for namespace - " + name_space,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        storage_policies = []
        if namespace_response.json()["config_status"] != "RUNNING":
            current_app.logger.error("Selected namespace is not in running state - " + name_space)
            d = {
                "responseType": "ERROR",
                "msg": "Selected namespace is not in running state - " + name_space,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        for policy in namespace_response.json()["storage_specs"]:
            storage_policies.append(policy["policy"])
        vm_classes = namespace_response.json()["vm_service_spec"]["vm_classes"]
        policy_names = []
        policies = getStoragePolicies(vCenter, vCenter_user, VC_PASSWORD)
        for id in storage_policies:
            for policy in policies[0]:
                if policy["policy"] == id:
                    policy_names.append(policy["name"])

        if not policy_names:
            current_app.logger.error("Policy names list found empty for given namespace - " + name_space)
            d = {
                "responseType": "ERROR",
                "msg": "Policy names list found empty for given namespace - " + name_space,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        if not vm_classes:
            current_app.logger.error("VM Classes list found empty for given namespace - " + name_space)
            d = {
                "responseType": "ERROR",
                "msg": "VM Classes list found empty for given namespace - " + name_space,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        current_app.logger.info("Found namespace details successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Found namespace details successfully - " + name_space,
            "STATUS_CODE": 200,
            "VM_CLASSES": vm_classes,
            "STORAGE_POLICIES": policy_names,
        }
        return jsonify(d), 200
    except Exception:
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching details for namespace - " + name_space,
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500


def fluent_bit_enabled(env):
    if isEnvTkgs_ns(env) or env == Env.VSPHERE or env == Env.VMC:
        if check_fluent_bit_splunk_endpoint_endpoint_enabled():
            return True, Tkg_Extension_names.FLUENT_BIT_SPLUNK
        elif check_fluent_bit_http_endpoint_enabled():
            return True, Tkg_Extension_names.FLUENT_BIT_HTTP
        elif check_fluent_bit_syslog_endpoint_enabled():
            return True, Tkg_Extension_names.FLUENT_BIT_SYSLOG
        elif check_fluent_bit_elastic_search_endpoint_enabled():
            return True, Tkg_Extension_names.FLUENT_BIT_ELASTIC
        elif check_fluent_bit_kafka_endpoint_endpoint_enabled():
            return True, Tkg_Extension_names.FLUENT_BIT_KAFKA
        else:
            return False, None
    else:
        current_app.logger.error("Wrong env type provided for Fluent-bit installation")
        return False, None


def deploy_fluent_bit(end_point, cluster):
    try:
        current_app.logger.info("Deploying Fluent-bit extension on cluster - " + cluster)
        if not createClusterFolder(cluster):
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + cluster,
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        os.system("chmod +x ./common/injectValue.sh")
        copy_template_command = ["cp", Paths.VSPHERE_FLUENT_BIT_YAML, Paths.CLUSTER_PATH + cluster]
        copy_output = runShellCommandAndReturnOutputAsList(copy_template_command)
        if copy_output[1] != 0:
            current_app.logger.error("Failed to copy template file to : " + Paths.CLUSTER_PATH + cluster)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to copy template file to : " + Paths.CLUSTER_PATH + cluster,
                "ERROR_CODE": 500,
            }
            return json.dumps(d), 500
        yamlFile = Paths.CLUSTER_PATH + cluster + "/fluent_bit_data_values.yaml"
        namespace = "package-tanzu-system-logging"
        extra_ns = "tanzu-fluent-bit-logging"
        extension = Tkg_Extension_names.FLUENT_BIT.lower()
        appName = AppName.FLUENT_BIT
        extension_validate_command = ["kubectl", "get", "app", appName, "-n", extra_ns]
        command_fluent_bit = runShellCommandAndReturnOutputAsList(extension_validate_command)
        if not verifyPodsAreRunning(appName, command_fluent_bit[0], RegexPattern.RECONCILE_SUCCEEDED):
            version = TanzuUtil.get_version_of_package(Tkg_Extension_names.FLUENT_BIT.lower() + ".tanzu.vmware.com")
            current_app.logger.info(f"Deploying {extension} {version}")
            if version is None:
                current_app.logger.error("Failed Capture the available Fluent bit version")
                d = {"responseType": "ERROR", "msg": "Capture the available Fluent bit version", "STATUS_CODE": 500}
                return jsonify(d), 500
        env = envCheck()
        env = env[0]
        global_ns = "tkg-system"
        if isEnvTkgs_ns(env) and checkTmcEnabled(env):
            global_ns = "tanzu-package-repo-global"
        get_repo = [
            "kubectl",
            "-n",
            global_ns,
            "get",
            "packages",
            extension + ".tanzu.vmware.com." + version,
            "-o",
            "jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}'",
        ]

        get_repo_state = runShellCommandAndReturnOutput(get_repo)
        if get_repo_state[1] != 0:
            current_app.logger.error("Failed to get extension yaml copy " + str(get_repo_state[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get extension yaml copy " + str(get_repo_state[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        my_file = Path("./cacrtbase64d.crt")
        generate_file = [
            "imgpkg",
            "pull",
            "-b",
            get_repo_state[0].replace("'", "").strip(),
            "-o",
            "/tmp/" + extension + "-package",
        ]
        if my_file.exists():
            generate_file.extend(
                [
                    "--registry-ca-cert-path",
                    "./cacrtbase64d.crt",
                ]
            )
        generate_file_state = runShellCommandAndReturnOutputAsList(generate_file)
        if generate_file_state[1] != 0:
            current_app.logger.error("Failed to generate extension yaml copy " + str(generate_file_state[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to generate extension yaml copy " + str(generate_file_state[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        command_yaml_copy = ["cp", "/tmp/" + extension + "-package/config/values.yaml", yamlFile]
        copy_state = runShellCommandAndReturnOutputAsList(command_yaml_copy)
        if copy_state[1] != 0:
            current_app.logger.error("Failed to copy extension yaml " + str(copy_state[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to copy extension yaml " + str(copy_state[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        if not os.path.exists(yamlFile):
            current_app.logger.error("Failed to copy extension yaml " + str(copy_state[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to copy extension yaml " + str(copy_state[0]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

        command2 = ["./common/injectValue.sh", yamlFile, "remove"]
        runShellCommandAndReturnOutputAsList(command2)
        update_response = updateDataFile(end_point, yamlFile)
        if not update_response:
            d = {"responseType": "ERROR", "msg": "Failed to update data values file", "STATUS_CODE": 500}
            return jsonify(d), 500
        # Changed for glasgow
        verify_ns = ["kubectl", "get", "ns"]
        out = runShellCommandAndReturnOutputAsList(verify_ns)
        for item in out[0]:
            if namespace in item:
                break
        else:
            create_ns_cmd = ["kubectl", "create", "ns", namespace]
            runProcess(create_ns_cmd)

        out = runShellCommandAndReturnOutputAsList(verify_ns)
        for item in out[0]:
            if extra_ns in item:
                break
        else:
            create_ns_cmd = ["kubectl", "create", "ns", extra_ns]
            runProcess(create_ns_cmd)

        deploy_fluent_bit_command = [
            "tanzu",
            "package",
            "install",
            Tkg_Extension_names.FLUENT_BIT.lower(),
            "--package",
            Tkg_Extension_names.FLUENT_BIT.lower() + ".tanzu.vmware.com",
            "--version",
            version,
            "--values-file",
            yamlFile,
            "--namespace",
            extra_ns,
        ]
        state_extension_apply = runShellCommandAndReturnOutputAsList(deploy_fluent_bit_command)
        if state_extension_apply[1] != 0:
            current_app.logger.error(
                Tkg_Extension_names.FLUENT_BIT.lower() + " install command failed. "
                "Checking for reconciliation status..."
            )

        extension_validate_command = ["kubectl", "get", "app", Tkg_Extension_names.FLUENT_BIT.lower(), "-n", extra_ns]

        found = False
        count = 0
        command_ext_bit = runShellCommandAndReturnOutputAsList(extension_validate_command)
        if verifyPodsAreRunning(
            Tkg_Extension_names.FLUENT_BIT.lower(), command_ext_bit[0], RegexPattern.RECONCILE_SUCCEEDED
        ):
            found = True

        while not found and count < 20:
            command_ext_bit = runShellCommandAndReturnOutputAsList(extension_validate_command)
            if verifyPodsAreRunning(
                Tkg_Extension_names.FLUENT_BIT.lower(), command_ext_bit[0], RegexPattern.RECONCILE_SUCCEEDED
            ):
                found = True
                break
            count = count + 1
            time.sleep(30)
            current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")

        if found:
            d = {"responseType": "SUCCESS", "msg": "Fluent-bit installation completed successfully", "STATUS_CODE": 200}
            return jsonify(d), 200
        else:
            current_app.logger.error("Fluent-bit deployment is not completed even after " + str(count * 30) + "s wait")
            d = {"responseType": "ERROR", "msg": "Fluent-bit installation failed", "STATUS_CODE": 500}
            return jsonify(d), 500
    except Exception as e:
        current_app.logger.error("Exception occurred while deploying fluent-bit - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while deploying fluent-bit - " + str(e),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500


def checkFluentBitInstalled():
    extension = Tkg_Extension_names.FLUENT_BIT.lower()
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    sub_command = ["grep", extension]
    output = grabPipeOutput(main_command, sub_command)

    if verifyPodsAreRunning(extension, output[0], RegexPattern.RECONCILE_SUCCEEDED):
        return True, output[0].split()[3] + " " + output[0].split()[4]
    elif verifyPodsAreRunning(extension, output[0], RegexPattern.RECONCILE_FAILED):
        return True, output[0].split()[3] + " " + output[0].split()[4]
    else:
        return False, None


def updateDataFile(fluent_endpoint, dataFile):
    try:
        output_str = None
        if fluent_endpoint == Tkg_Extension_names.FLUENT_BIT_HTTP:
            host = request.get_json(force=True)["tanzuExtensions"]["logging"]["httpEndpoint"]["httpEndpointAddress"]
            port = request.get_json(force=True)["tanzuExtensions"]["logging"]["httpEndpoint"]["httpEndpointPort"]
            uri = request.get_json(force=True)["tanzuExtensions"]["logging"]["httpEndpoint"]["httpEndpointUri"]
            header = request.get_json(force=True)["tanzuExtensions"]["logging"]["httpEndpoint"][
                "httpEndpointHeaderKeyValue"
            ]
            output_str = """
    [OUTPUT]
    Name            http
    Match           *
    Host            %s
    Port            %s
    URI             %s
    Header          %s
    Format          json
    tls             On
    tls.verify      off
            """ % (
                host,
                port,
                uri,
                header,
            )
        elif fluent_endpoint == Tkg_Extension_names.FLUENT_BIT_SYSLOG:
            host = request.get_json(force=True)["tanzuExtensions"]["logging"]["syslogEndpoint"]["syslogEndpointAddress"]
            port = request.get_json(force=True)["tanzuExtensions"]["logging"]["syslogEndpoint"]["syslogEndpointPort"]
            mode = request.get_json(force=True)["tanzuExtensions"]["logging"]["syslogEndpoint"]["syslogEndpointMode"]
            format = request.get_json(force=True)["tanzuExtensions"]["logging"]["syslogEndpoint"][
                "syslogEndpointFormat"
            ]
            output_str = """
    [OUTPUT]
    Name            syslog
    Match           *
    Host            %s
    Port            %s
    Mode            %s
    Syslog_Format   %s
    Syslog_Hostname_key  tkg_cluster
    Syslog_Appname_key   pod_name
    Syslog_Procid_key    container_name
    Syslog_Message_key   message
    Syslog_SD_key        k8s
    Syslog_SD_key        labels
    Syslog_SD_key        annotations
    Syslog_SD_key        tkg
            """ % (
                host,
                port,
                mode,
                format,
            )
        elif fluent_endpoint == Tkg_Extension_names.FLUENT_BIT_KAFKA:
            broker = request.get_json(force=True)["tanzuExtensions"]["logging"]["kafkaEndpoint"][
                "kafkaBrokerServiceName"
            ]
            topic = request.get_json(force=True)["tanzuExtensions"]["logging"]["kafkaEndpoint"]["kafkaTopicName"]
            output_str = """
    [OUTPUT]
    Name           kafka
    Match          *
    Brokers        %s
    Topics         %s
    Timestamp_Key  @timestamp
    Retry_Limit    false
    rdkafka.log.connection.close false
    rdkafka.queue.buffering.max.kbytes 10240
    rdkafka.request.required.acks   1
            """ % (
                broker,
                topic,
            )
        else:
            current_app.logger.error("Provided endpoint is not supported by SIVT - " + fluent_endpoint)
            return False

        current_app.logger.info("Printing " + fluent_endpoint + " endpoint details ")
        current_app.logger.info(output_str)
        inject_sc = ["sh", "./common/injectValue.sh", dataFile, "inject_output_fluent", output_str.strip()]
        inject_sc_response = runShellCommandAndReturnOutput(inject_sc)
        if inject_sc_response[1] == 500:
            current_app.logger.error("Command to update output endpoint failed")
            return False
        return True

    except Exception as e:
        current_app.logger.error(str(e))
        return False


def createClusterFolder(clusterName):
    try:
        command = ["mkdir", "-p", Paths.CLUSTER_PATH + clusterName + "/"]
        create_output = runShellCommandAndReturnOutputAsList(command)
        if create_output[1] != 0:
            return False
        else:
            return True
    except Exception:
        current_app.logger.error("Exception occurred while creating directory - " + Paths.CLUSTER_PATH + clusterName)
        return False


def checkAVIPassword(env):
    try:
        if env == Env.VSPHERE or env == Env.VCF:
            if isEnvTkgs_wcp(env):
                avi_pass = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviPasswordBase64"]
                avi_backup_pass = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"][
                    "aviBackupPassphraseBase64"
                ]
            else:
                avi_pass = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviPasswordBase64"]
                avi_backup_pass = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"][
                    "aviBackupPassphraseBase64"
                ]
        elif env == Env.VMC:
            avi_pass = request.get_json(force=True)["componentSpec"]["aviComponentSpec"]["aviPasswordBase64"]
            avi_backup_pass = request.get_json(force=True)["componentSpec"]["aviComponentSpec"][
                "aviBackupPassPhraseBase64"
            ]
        # avi_pass conversion from b64
        base64_bytes_avi = avi_pass.encode("ascii")
        enc_bytes_avi = base64.b64decode(base64_bytes_avi)
        avi_pass = enc_bytes_avi.decode("ascii").rstrip("\n")
        # avi_backup_pass conversion from b64
        base64_bytes_avi = avi_backup_pass.encode("ascii")
        enc_bytes_avi = base64.b64decode(base64_bytes_avi)
        avi_backup_pass = enc_bytes_avi.decode("ascii").rstrip("\n")

        # Check min length is 8
        if len(avi_pass) < 8 or len(avi_backup_pass) < 8:
            current_app.logger.error("The minimum length for AVI password and AVI Backup passphrase is 8!")
            return False, "The minimum length for AVI password and AVI Backup passphrase is 8!"

        # Check if password contains uppercase character
        match_count = 0
        pat_upper = re.compile("[A-Z]+")
        upper_match = re.search(pat_upper, avi_pass)
        if upper_match:
            match_count = match_count + 1
        pat_lower = re.compile("[a-z]+")
        lower_match = re.search(pat_lower, avi_pass)
        if lower_match:
            match_count = match_count + 1
        pat_digit = re.compile("[0-9]+")
        digit_match = re.search(pat_digit, avi_pass)
        if digit_match:
            match_count = match_count + 1
        pat_special = re.compile("[@_!#$%^&*()<>?/\|}{~:]")
        special_match = re.search(pat_special, avi_pass)
        if special_match:
            match_count = match_count + 1
        if match_count <= 3:
            current_app.logger.error(
                "NSX ALB Password must contain a combination of 3: Uppercase character,\
                     Lowercase character, Numeric or Special Character."
            )
            return (
                False,
                "AVI Password must contain a combination of 3: Uppercase character, \
                    Lowercase character, Numeric or Special Character.",
            )
        else:
            current_app.logger.info("NSX ALB Password passed the complexity check")
        match_count = 0
        upper_match = re.search(pat_upper, avi_backup_pass)
        if upper_match:
            match_count = match_count + 1
        lower_match = re.search(pat_lower, avi_backup_pass)
        if lower_match:
            match_count = match_count + 1
        digit_match = re.search(pat_digit, avi_backup_pass)
        if digit_match:
            match_count = match_count + 1
        special_match = re.search(pat_special, avi_backup_pass)
        if special_match:
            match_count = match_count + 1
        if match_count <= 3:
            current_app.logger.error(
                "NSX ALB Backup Passphrase must contain a combination of 3:\
                     Uppercase character, Lowercase character, Numeric or Special Character."
            )
            return (
                False,
                "NSX ALB Backup Passphrase must contain a combination of 3:\
                     Uppercase character, Lowercase character, Numeric or Special Character.",
            )
        else:
            current_app.logger.info("NSX ALB Backup Password passed the complexity check")
        return True, "Successfully validated password complexity checks for NSX ALB"
    except Exception as e:
        current_app.logger.error("NSX ALB Password and Backup passphrase is not matching the complexity")
        current_app.logger.error(
            "NSX ALB Password must contain a combination of 3: Uppercase character,\
                 Lowercase character, Numeric or Special Character."
        )
        return False, str(e)


def checkClusterNameDNSCompliant(cluster_name, env):
    try:
        dns_pat = re.compile("^[a-z0-9][a-z0-9-.]{0,40}[a-z0-9]$")
        compliant_match = re.search(dns_pat, cluster_name)
        if compliant_match:
            return True, "Successfully validated cluster name: " + cluster_name + " is DNS Compliant"
        else:
            current_app.logger.error(
                "Cluster name must start and end with a letter or number, \
                    and can contain only lowercase letters, numbers, and hyphens."
            )
            return False, "cluster name: " + cluster_name + " is not DNS Compliant"
    except Exception as e:
        current_app.logger.error("Failed to verify cluster name : " + cluster_name + " is DNS Compliant")
        return False, str(e)


def getNetworkDetailsVip(ip, csrf2, vipNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion, env="vsphere"):
    url = vipNetworkUrl
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0],
    }
    env = envCheck()
    env = env[0]
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    details = {}
    if response_csrf.status_code != 200:
        details["error"] = response_csrf.text
        return None, "Failed", details
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        if env == Env.VSPHERE:
            details["vim_ref"] = response_csrf.json()["vimgrnw_ref"]
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        return "AlreadyConfigured", 200, details
    except Exception:
        current_app.logger.info("Ip pools are not configured configuring it")

    os.system("rm -rf vipNetworkDetails.json")
    with open("./vipNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    if env == Env.VSPHERE:
        generateVsphereConfiguredSubnets("vipNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))
    if env == Env.VCF:
        generateVsphereConfiguredSubnetsForSeandVIP("vipNetworkDetails.json", startIp, endIp, prefixIp, int(netmask))

    return "SUCCESS", 200, details


def create_virtual_service(
    ip, csrf2, avi_cloud_uuid, se_name, vip_network_url, se_count, tier_id, vrf_url_tier1, avi_version
):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0],
    }
    env = envCheck()
    env = env[0]
    body = {}
    url = AlbEndpoint.AVI_SERVICE_ENGINE.format(ip=ip, se_name=se_name, avi_cloud_uuid=avi_cloud_uuid)
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        json_out = response_csrf.json()["results"][0]

        cloud_ref = json_out["cloud_ref"]
        service_engine_group_url = json_out["url"]
        se_uuid = json_out["uuid"]
        type = VrfType.GLOBAL
        cloud_ref_ = cloud_ref[cloud_ref.rindex("/") + 1 :]
        se_group_url = AlbEndpoint.AVI_SE_GROUP.format(ip=ip, cloud_ref=cloud_ref_, service_engine_uuid=se_uuid)
        response = requests.request("GET", se_group_url, headers=headers, data=body, verify=False)
        if response.status_code != 200:
            return None, response.text
        createVs = False
        try:
            service_engines = response.json()["results"][0]["serviceengines"]
            if len(service_engines) > (se_count - 1):
                current_app.logger.info("Required service engines are already created")
            else:
                createVs = True
        except Exception:
            createVs = True
        if createVs:
            current_app.logger.info("Creating virtual service")
            vrf_get_url = "https://" + ip + "/api/vrfcontext/?name.in=" + type + "&cloud_ref.uuid=" + avi_cloud_uuid
            response_csrf = requests.request("GET", vrf_get_url, headers=headers, data=body, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            vrf_url = ""
            for res in response_csrf.json()["results"]:
                if res["name"] == type:
                    vrf_url = res["url"]
                    break
            if not vrf_url:
                return None, "VRF_URL_NOT_FOUND"
            startIp = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                "tkgClusterVipIpStartRange"
            ]
            endIp = request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(
                request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                    "tkgClusterVipNetworkGatewayCidr"
                ]
            )
            getVIPNetworkDetails = getNetworkDetailsVip(
                ip, csrf2, vip_network_url, startIp, endIp, prefixIpNetmask[0], prefixIpNetmask[1], avi_version, env
            )
            if getVIPNetworkDetails[0] is None:
                return None, "Failed to get vip network details " + str(getVIPNetworkDetails[2])
            if getVIPNetworkDetails[0] == "AlreadyConfigured":
                current_app.logger.info("Vip Ip pools are already configured.")
                ip_pre = getVIPNetworkDetails[2]["subnet_ip"]
                mask = getVIPNetworkDetails[2]["subnet_mask"]
            else:
                return None, "Vip Ip pools are not configured."
            virtual_service_vip_url = AlbEndpoint.AVI_VIRTUAL_SERVICE_VIP.format(ip=ip)
            response = requests.request("GET", virtual_service_vip_url, headers=headers, data=body, verify=False)
            if response.status_code != 200:
                return None, response.text
            isVipCreated = False
            vip_url = ""
            try:
                for r in response.json()["results"]:
                    if r["name"] == ServiceName.SIVT_SERVICE_VIP:
                        isVipCreated = True
                        vip_url = r["url"]
                        break
            except Exception:
                current_app.logger.info("No virtual service vip created")
            if not isVipCreated:
                if env == Env.VCF:
                    body = AlbPayload.VIRTUAL_SERVICE_NSX_VIP.format(
                        cloud_ref=cloud_ref,
                        virtual_service_name_vip=ServiceName.SIVT_SERVICE_VIP,
                        vrf_context_ref=vrf_url_tier1,
                        network_ref=vip_network_url,
                        addr=ip_pre,
                        mask=mask,
                        tier_1_gw_uuid=tier_id,
                    )
                else:
                    body = AlbPayload.VIRTUAL_SERVICE_VIP.format(
                        cloud_ref=cloud_ref,
                        virtual_service_name_vip=ServiceName.SIVT_SERVICE_VIP,
                        vrf_context_ref=vrf_url,
                        network_ref=vip_network_url,
                        addr=ip_pre,
                        mask=mask,
                    )
                response = requests.request("POST", virtual_service_vip_url, headers=headers, data=body, verify=False)
                if response.status_code != 201:
                    return None, response.text
                vip_url = response.json()["url"]
            if not vip_url:
                return None, "virtual service vip url not found"
            virtual_service_url = AlbEndpoint.AVI_VIRTUAL_SERVICE.format(ip=ip)
            response = requests.request("GET", virtual_service_url, headers=headers, data=body, verify=False)
            if response.status_code != 200:
                return None, response.text
            isVsCreated = False
            try:
                for r in response.json()["results"]:
                    if r["name"] == ServiceName.SIVT_SERVICE:
                        isVsCreated = True
                        break
            except Exception:
                current_app.logger.info("No virtual service created")
            if not isVsCreated:
                if env == Env.VCF:
                    body = AlbPayload.NSX_VIRTUAL_SERVICE.format(
                        cloud_ref=cloud_ref,
                        se_group_ref=service_engine_group_url,
                        vsvip_ref=vip_url,
                        tier_1_vrf_context_url=vrf_url_tier1,
                    )
                else:
                    body = AlbPayload.VIRTUAL_SERVICE.format(
                        cloud_ref=cloud_ref, se_group_ref=service_engine_group_url, vsvip_ref=vip_url
                    )
                response = requests.request("POST", virtual_service_url, headers=headers, data=body, verify=False)
                if response.status_code != 201:
                    return None, response.text
            body = {}
            counter = 0
            counter_se = 0
            initialized = False
            try:
                if se_count == 2:
                    for i in range(1):
                        while counter_se < 90:
                            response = requests.request("GET", se_group_url, headers=headers, data=body, verify=False)
                            if response.status_code != 200:
                                return None, response.text
                            config = response.json()["results"][0]
                            try:
                                seurl = config["serviceengines"][i]
                                initialized = True
                                break
                            except Exception:
                                current_app.logger.info(
                                    "Waited " + str(counter_se * 10) + "s for service engines to be " "initialized"
                                )
                            counter_se = counter_se + 1
                            time.sleep(30)
                        if not initialized:
                            return None, "Service engines not initialized  in 45m"
                        current_app.logger.info("Checking status of service engine " + str(seurl))
                        response = requests.request("GET", seurl, headers=headers, data=body, verify=False)
                        if response.status_code != 200:
                            return None, response.text
                        isConnected = False
                        try:
                            status = response.json()["se_connected"]
                            while not status and counter < 60:
                                response = requests.request("GET", seurl, headers=headers, data=body, verify=False)
                                if response.status_code != 200:
                                    return None, response.text
                                status = response.json()["se_connected"]
                                if status:
                                    isConnected = True
                                    break
                                counter = counter + 1
                                time.sleep(30)
                                current_app.logger.info(
                                    "Waited " + str(counter * 30) + "s,to check se  connected status retrying"
                                )
                            if not isConnected:
                                return (
                                    None,
                                    "Waited "
                                    + str(counter * 30)
                                    + "s,to check se  connected and is not in connected state",
                                )
                            else:
                                current_app.logger.info(str(seurl) + " is  now in connected state")
                            counter = 0
                        except Exception as e:
                            return None, str(e)

                if se_count == 4:
                    for i in range(2, 3):
                        seurl = config["serviceengines"][i]
                        current_app.logger.info("Checking status of service engine " + str(seurl))
                        response = requests.request("GET", seurl, headers=headers, data=body, verify=False)
                        if response.status_code != 200:
                            return None, response.text
                        current_app.logger.info(response.json())
                        isConnected = False
                        try:
                            status = response.json()["se_connected"]
                            while not status and counter < 60:
                                response = requests.request("GET", seurl, headers=headers, data=body, verify=False)
                                if response.status_code != 200:
                                    return None, response.text
                                if status:
                                    isConnected = True
                                    break
                                counter = counter + 1
                                time.sleep(10)
                                current_app.logger.info(
                                    "Waited " + str(counter * 10) + "s,to check se  connected status retrying"
                                )
                            if not isConnected:
                                return (
                                    None,
                                    "Waited "
                                    + str(counter * 10)
                                    + "s,to check se  connected and is not in connected state",
                                )
                        except Exception as e:
                            return None, str(e)
            except Exception as e:
                return None, str(e)
            try:
                current_app.logger.info("Deleting Virtual service")
                response = requests.request("GET", virtual_service_vip_url, headers=headers, data=body, verify=False)
                if response.status_code != 200:
                    return None, response.text
                vip_url = ""
                try:
                    for r in response.json()["results"]:
                        if r["name"] == ServiceName.SIVT_SERVICE_VIP:
                            vip_url = r["url"]
                            break
                except Exception:
                    current_app.logger.info("No virtual service vip created")
                vs_url = ""
                virtual_service_url = AlbEndpoint.AVI_VIRTUAL_SERVICE.format(ip=ip)
                response = requests.request("GET", virtual_service_url, headers=headers, data=body, verify=False)
                try:
                    for r in response.json()["results"]:
                        if r["name"] == ServiceName.SIVT_SERVICE:
                            vs_url = r["url"]
                            break
                except Exception:
                    current_app.logger.info("No virtual service created")
                requests.request("DELETE", vs_url, headers=headers, data=body, verify=False)
                requests.request("DELETE", vip_url, headers=headers, data=body, verify=False)
            except Exception:
                pass
            return "SUCCESS", "Required Service engines successfully created"
        else:
            return "SUCCESS", "Required Service engines are already present"


def isRunningInDocker():
    KEY = os.environ.get("AM_I_IN_A_DOCKER_CONTAINER", "No")
    if KEY == "Yes":
        return True
    else:
        return False


def ping_check_gateways(env):
    try:
        ip_addr = []
        if env == Env.VSPHERE or env == Env.VCF:
            if isEnvTkgs_wcp(env):
                ip_addr.append(
                    request.get_json(force=True)["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"]
                )
                ip_addr.append(
                    request.get_json(force=True)["tkgsComponentSpec"]["tkgsVipNetwork"]["tkgsVipNetworkGatewayCidr"]
                )
                ip_addr.append(
                    request.get_json(force=True)["tkgsComponentSpec"]["tkgsMgmtNetworkSpec"][
                        "tkgsMgmtNetworkGatewayCidr"
                    ]
                )
                ip_addr.append(
                    request.get_json(force=True)["tkgsComponentSpec"]["tkgsPrimaryWorkloadNetwork"][
                        "tkgsPrimaryWorkloadNetworkGatewayCidr"
                    ]
                )
            elif isEnvTkgs_ns(env):
                workload_nw_cidr = request.get_json(force=True)["tkgsComponentSpec"]["tkgsWorkloadNetwork"][
                    "tkgsWorkloadNetworkGatewayCidr"
                ]
                if workload_nw_cidr:
                    ip_addr.append(workload_nw_cidr)
            else:
                ip_addr.append(
                    request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"]
                )
                ip_addr.append(
                    request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtGatewayCidr"]
                )
                if not env == Env.VCF:
                    ip_addr.append(request.get_json(force=True)["tkgMgmtDataNetwork"]["tkgMgmtDataNetworkGatewayCidr"])
                    ip_addr.append(
                        request.get_json(force=True)["tkgWorkloadDataNetwork"]["tkgWorkloadDataNetworkGatewayCidr"]
                    )
                    ip_addr.append(request.get_json(force=True)["tkgWorkloadComponents"]["tkgWorkloadGatewayCidr"])
                ip_addr.append(
                    request.get_json(force=True)["tkgComponentSpec"]["tkgClusterVipNetwork"][
                        "tkgClusterVipNetworkGatewayCidr"
                    ]
                )
        elif env == Env.VMC:
            ip_addr.append(request.get_json(force=True)["componentSpec"]["aviMgmtNetworkSpec"]["aviMgmtGatewayCidr"])
            ip_addr.append(
                request.get_json(force=True)["componentSpec"]["tkgClusterVipNetwork"]["tkgClusterVipNetworkGatewayCidr"]
            )
            ip_addr.append(request.get_json(force=True)["componentSpec"]["aviMgmtNetworkSpec"]["aviMgmtGatewayCidr"])
            ip_addr.append(
                request.get_json(force=True)["componentSpec"]["tkgMgmtDataNetworkSpec"]["tkgMgmtDataGatewayCidr"]
            )

        if not ip_addr and isEnvTkgs_ns(env):
            return True

        # remove duplicate CIDRs
        ip_addr = [*set(ip_addr)]

        for ip in ip_addr:
            if ping_test("ping -c 1 " + ip.split("/")[0]) != 0:
                current_app.logger.warn(
                    "Ping test failed for "
                    + ip
                    + " gateway. It is Recommended to fix this before proceeding with deployment"
                )
                time.sleep(30)
            else:
                current_app.logger.info("Ping test passed for gateway - " + ip)

        return True
    except Exception as e:
        current_app.logger.warn("Exception occurred while performing ping test on gateway IPs")
        current_app.logger.warn(str(e))
        return True


def ping_test(string_command):
    try:
        command = string_command.split(" ")
        l, o = runShellCommandAndReturnOutputAsList(command)
        s = l[4].replace(" ", "")
        if s.__contains__(",100.0%packetloss,"):
            return 1
        elif s.__contains__(",0%packetloss,"):
            return 0
        else:
            return 1
    except Exception:
        return 1


def check_files_type(files):
    """
    helper function to list pem files
    """
    list_of_pem_files = []
    for fl in files:
        if not os.path.splitext(fl)[1] == ".pem":
            list_of_pem_files.append(files)
    if len(list_of_pem_files) == 0:
        return "correct"
    else:
        return list_of_pem_files


def add_ytt_overlays(cert_files):
    lines_array = ""
    ytt_path = os.path.join(Env.UPDATED_YTT_FILE_LOCATION, "photon-ubuntu-universal-overlay.yaml")
    current_app.logger.info(f"Creating overlay file {ytt_path} for custom cert certificate")
    with open("./common/photon-ubuntu-universal-overlay-sample.yaml", "r") as stream:
        lines_array = stream.readlines()
        for i, line in enumerate(lines_array):
            if '#@ arr = ["tkg-custom-cert01.pem", "tkg-custom-cert02.pem"]' in line:
                split_string = " = ["
                start = line.split(split_string)[0] + " = ["
                end_string = ""
                for f in cert_files[:-1]:
                    f_name = os.path.split(f)[1]
                    end_string += f'"{f_name}",'
                last_file_name = os.path.split(cert_files[-1])[1]
                end_string += f'"{last_file_name}"]\n'
                print(start + end_string)
                lines_array[i] = start + end_string
    with open(ytt_path, "w") as stream:
        stream.writelines(lines_array)


def copy_pem_files_to_vsphere_ytt(cert_files):
    for file in cert_files:
        fl = file
        if os.path.splitext(fl)[1] == ".pem":
            if os.path.exists(fl):
                current_app.logger.info(
                    f"Copying cert files from {fl} to vsphere ytt location " f"{Env.UPDATED_YTT_FILE_LOCATION}"
                )
                copy_command = "cp {source_file} {destination_file}".format(
                    source_file=fl, destination_file=Env.UPDATED_YTT_FILE_LOCATION
                )
                cmd = shlex.split(copy_command)
                runShellCommandAndReturnOutputAsList(cmd)
            else:
                current_app.logger.error(f"cert files {fl} not exists")
                return False
        else:
            current_app.logger.error(f"{fl} doesn't have .pem extension")
            return False
    return True


def create_certs_in_ytt_config():
    try:
        cert_file_location = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"]["tkgCustomCertsPath"]
        if len(cert_file_location) == 0:
            # if file exist delete it.
            ytt_path = os.path.join(Env.UPDATED_YTT_FILE_LOCATION, "photon-ubuntu-universal-overlay.yaml")
            os.system(f"rm {ytt_path}")
            current_app.logger.info("Custom Cert files location has not been provided for custom certificates")
            return True, "Completed"
        current_app.logger.info(f"Reading cert/pem files from {cert_file_location} for shared service cluster")
        pem_files = check_files_type(cert_file_location)
        if pem_files != "correct":
            current_app.logger.error(f"{pem_files} doesn't have .pem extension")
            return False, f"{pem_files} doesn't have .pem extension"
        else:
            current_app.logger.info(f"{pem_files} pem/cert files found at {cert_file_location}")
            cert_file_location_var = cert_file_location
            if not copy_pem_files_to_vsphere_ytt(cert_file_location_var):
                return False, "Error in copying pem files"
            add_ytt_overlays(cert_file_location_var)
            return True, "Completed"

    except Exception as e:
        return None, str(e)


def add_harbor_cert_in_overlays(cert_file):
    lines_array = ""
    ytt_path = os.path.join(Env.UPDATED_YTT_FILE_LOCATION, "photon-ubuntu-universal-overlay.yaml")
    current_app.logger.info(f"Updating overlay file {ytt_path} for harbor cert certificate")
    if not os.path.exists(ytt_path):
        current_app.logger.info(f"{ytt_path} file with harbor certificate not exist, so creating it.")
        add_ytt_overlays([cert_file])
    else:
        current_app.logger.info(f"Appending harbor certificate to the existing {ytt_path} file.")
        with open(ytt_path, "r") as stream:
            lines_array = stream.readlines()
            for i, line in enumerate(lines_array):
                if "#@ arr = " in line:
                    # add file to the end
                    file_name = f', "{cert_file}"]'
                    lines_array[i] = line.replace("]", file_name)
        with open(ytt_path, "w") as stream:
            stream.writelines(lines_array)


def copy_harbor_cert_to_ytt_config():
    try:
        harbor_file = "harbor.pem"
        ytt_harbor_file = os.path.join(Env.UPDATED_YTT_FILE_LOCATION, harbor_file)
        create_cert_command_list = [
            "kubectl",
            "get",
            "secret",
            "harbor-tls",
            "-n",
            "tanzu-system-registry",
            "-o=go-template='{{index .data \"tls.crt\"}}'",
        ]
        output = runShellCommandAndReturnOutput(create_cert_command_list)
        if output[1] != 0:
            return None, "Unable to fetch cert files from harbor"
        else:
            current_app.logger.info(f"Going to write harbor certificate at {ytt_harbor_file}.")
            harbor_pem = base64.b64decode(output[0]).decode("utf-8")
            with open(ytt_harbor_file, "w") as fh:
                fh.write(harbor_pem)
        current_app.logger.info("Harbor certificate has been fetched successfully.")
        add_harbor_cert_in_overlays(harbor_file)
        return True, "Completed"
    except Exception as e:
        return None, str(e)


def get_cluster(si, datacenter, name):
    """
    Pick a cluster by its name.
    """
    view_manager = si.content.viewManager
    container = view_manager.CreateContainerView(datacenter, [vim.ClusterComputeResource], True)
    try:
        h_name = []
        for host in container.view:
            rp = host.name
            if rp:
                folder_name = rp
                fp = host.parent
                while fp is not None and fp.name is not None and fp != si.content.rootFolder:
                    folder_name = fp.name + "/" + folder_name
                    try:
                        fp = fp.parent
                    except BaseException:
                        break
                folder_name = "/" + folder_name
                if name:
                    if str(folder_name).endswith(name):
                        content = si.RetrieveContent()
                        return content.searchIndex.FindByInventoryPath(folder_name)
                first_rp = folder_name[folder_name.find("/host") + 6 :]
                if first_rp:
                    h_name.append(first_rp.strip("/"))
        if h_name:
            return h_name
    finally:
        container.Destroy()


def getNetwork(datacenter, name):
    if name is not None:
        networks = datacenter.networkFolder.childEntity
        for network in networks:
            if network.name == name:
                return network
            elif hasattr(network, "childEntity"):
                ports = network.childEntity
                for item in ports:
                    if item.name == name:
                        return item
        raise Exception("Failed to find port group named: %s" % name)
    else:
        network_list = []
        try:
            for port in datacenter.networkFolder.childEntity:
                if hasattr(port, "childEntity"):
                    ports = port.childEntity
                    for item in ports:
                        network_list.append(item.name)
                else:
                    network_list.append(port.name)
            return network_list
        except Exception:
            raise Exception("Encountered errors while fetching networks: %s" % datacenter.name)


def update_template_in_ova():
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


def getVCthumbprint():
    current_app.logger.info("Fetching VC thumbprint")
    env = envCheck()[0]
    try:
        if env == Env.VMC:
            vCenter = current_app.config["VC_IP"]
        else:
            vCenter = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterAddress"]
    except Exception:
        current_app.logger.error("Failed to fetch VC details")
        return 500
    if not vCenter:
        current_app.logger.error("Failed to fetch VC details")
        return 500

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    wrappedSocket = ssl.wrap_socket(sock)
    try:
        wrappedSocket.connect((vCenter, 443))
    except Exception:
        current_app.logger.error("vCenter connection failed")
        return 500

    der_cert_bin = wrappedSocket.getpeercert(True)

    # Thumbprint
    thumb_sha1 = hashlib.sha1(der_cert_bin).hexdigest()
    wrappedSocket.close()
    if thumb_sha1:
        thumb_sha1 = thumb_sha1.upper()
        thumb_sha1 = ":".join(thumb_sha1[i : i + 2] for i in range(0, len(thumb_sha1), 2))
        current_app.logger.info("SHA1 : " + thumb_sha1)
        return thumb_sha1
    else:
        current_app.logger.error("Failed to obtain VC SHA1")
        return 500


def fetchContentLibrary(ip, headers, vcenter_credential):
    try:
        vc_Content_Library_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["contentLibraryName"]
        if not vc_Content_Library_name:
            vc_Content_Library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
        vCenter = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterAddress"]
        vCenterUser = current_app.config["VC_USER"]
        vCenterPassword = current_app.config["VC_PASSWORD"]
        url = "https://" + ip + "/api/vimgrvcenterruntime/retrieve/contentlibraries"
        body = {
            "host": vCenter,
            "username": vCenterUser,
            "password": vCenterPassword,
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
