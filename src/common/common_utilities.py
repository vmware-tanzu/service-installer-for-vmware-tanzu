import base64
import fcntl
import ssl
import ipaddress
import json
import ntplib
from time import ctime
from common.operation.constants import AviSize, MarketPlaceUrl, ResourcePoolAndFolderName, Cloud, Versions, AkoType, \
    CIDR, PLAN, \
    TmcUser, \
    CertName, \
    Vcenter, VrfType, Repo, AppName, Type, VCF, ControllerLocation, KubernetesOva, EnvType, ServiceName, TKG_Package_Details
import os
import re
import socket
import struct
import time
from pathlib import Path
import OpenSSL
import requests
import ruamel
import yaml
from pyVim import connect

from common.certificate_base64 import getBase64CertWriteToFile, repoAdd
from common.operation.ShellHelper import runShellCommandAndReturnOutput, runShellCommandWithPolling, \
    grabKubectlCommand, \
    runShellCommandAndReturnOutputAsList, runProcess, verifyPodsAreRunning, grabPipeOutputChagedDir, \
    runShellCommandAndReturnOutputAsListWithChangedDir, grabPipeOutput, runProcessTmcMgmt
from common.operation.constants import Env, Avi_Version, Extentions, RegexPattern, Tkg_version, SAS
from common.operation.constants import Versions, CIDR, TmcUser, \
    CertName, \
    VrfType, Repo, AppName, Type, VCF, ControllerLocation, KubernetesOva, EnvType, Tkg_Extention_names, VeleroAPI
from common.operation.vcenter_operations import createResourcePool, create_folder
from common.replace_value import generateVsphereConfiguredSubnets, generateVsphereConfiguredSubnetsForSe
from common.replace_value import replaceValue
from flask import current_app, jsonify, request
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from ruamel import yaml as ryaml
from common.util.file_helper import FileHelper
from jinja2 import Template
from common.operation.constants import Paths
from tqdm import tqdm
from yaml import SafeLoader
from .constants.alb_api_constants import AlbPayload, AlbEndpoint
from .lib.govc_client import GovcClient
from .replace_value import replaceValueSysConfig, replaceCertConfig
from common.util.local_cmd_helper import LocalCmdHelper
from datetime import datetime

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def envCheck():
    try:
        env = request.headers['Env']
    except Exception:
        current_app.logger.error("No env headers passed")
        return "NO_ENV", 400
    if env is None:
        return "NO_ENV", 400
    if env == Env.VMC:
        pass
    elif env == Env.VSPHERE:
        pass
    elif env == Env.VCF:
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
            "ERROR_CODE": 500
        }
        current_app.logger.error("Wrong env type provided " + _env[0] + " please specify vmc or vsphere")
        return jsonify(d), 500
    env = _env[0]
    if env == Env.VSPHERE or env == Env.VCF:
        try:
            if current_app.config['VC_PASSWORD'] is None:
                current_app.logger.info("Vc password")
            if current_app.config['VC_USER'] is None:
                current_app.logger.info("Vc user password")
            if current_app.config['VC_IP'] is None:
                current_app.logger.info("Vc ip")
            if current_app.config['VC_CLUSTER'] is None:
                current_app.logger.info("Vc Cluster")
            if current_app.config['VC_DATACENTER'] is None:
                current_app.logger.info("Vc Datacenter")
            if not isEnvTkgs_ns(env):
                if current_app.config['VC_DATASTORE'] is None:
                    current_app.logger.info("Vc datastore")
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Un-Authorized " + str(e),
                "ERROR_CODE": 401
            }
            return jsonify(d), 401
    else:
        try:
            if current_app.config['access_token'] is None:
                current_app.logger.info("Access token not found")
            if current_app.config['ORG_ID'] is None:
                current_app.logger.info("ORG_ID not found")
            if current_app.config['SDDC_ID'] is None:
                current_app.logger.info("SDDC_ID not found")
            if current_app.config['NSX_REVERSE_PROXY_URL'] is None:
                current_app.logger.info("NSX_REVERSE_PROXY_URL not found")
            if current_app.config['VC_IP'] is None:
                current_app.logger.info("Vc ip not found")
            if current_app.config['VC_PASSWORD'] is None:
                current_app.logger.info("Vc cred not found")
            if current_app.config['VC_USER'] is None:
                current_app.logger.info("Vc user not found")
            if current_app.config['VC_CLUSTER'] is None:
                current_app.logger.info("Vc Cluster")
            if current_app.config['VC_DATACENTER'] is None:
                current_app.logger.info("Vc Datacenter")
            if current_app.config['VC_DATASTORE'] is None:
                current_app.logger.info("Vc datastore")
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": f"Un-Authorized {e}",
                "ERROR_CODE": "401"
            }
            return jsonify(d), 401
    d = {
        "responseType": "SUCCESS",
        "msg": "Authorized",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def createResourceFolderAndWait(vcenter_ip, vcenter_username, password,
                                cluster_name, data_center, resourcePoolName, folderName, parentResourcePool):
    try:
        isCreated4 = createResourcePool(vcenter_ip, vcenter_username, password,
                                        cluster_name,
                                        resourcePoolName, parentResourcePool, data_center)
        if isCreated4 is not None:
            current_app.logger.info("Created resource pool " + resourcePoolName)
    except Exception as e:
        current_app.logger.error("Failed to create resource pool " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    try:
        isCreated1 = create_folder(vcenter_ip, vcenter_username, password,
                                   data_center,
                                   folderName)
        if isCreated1 is not None:
            current_app.logger.info("Created  folder " + folderName)

    except Exception as e:
        current_app.logger.error("Failed to create folder " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create folder " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    find = validateFolderAndResourcesAvailable(folderName, resourcePoolName, vcenter_ip, vcenter_username, password,
                                               parentResourcePool)
    if not find:
        # current_app.logger.error("Failed to find folder and resources")
        errorMsg = "Failed to create resource pool " + resourcePoolName + ". Please check if " + resourcePoolName + \
                   " is already present in " + cluster_name + " and delete it before initiating deployment"
        current_app.logger.error(errorMsg)
        d = {
            "responseType": "ERROR",
            "msg": errorMsg,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "ERROR",
        "msg": "Created resources and  folder",
        "ERROR_CODE": 200
    }
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
                    output[0]).__contains__("/vm/" + folder):
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


def deployAndConfigureAvi(govc_client: GovcClient, vm_name, controller_ova_location, deploy_options, performOtherTask,
                          env, avi_version):
    try:
        data_center = current_app.config['VC_DATACENTER']
        data_center = data_center.replace(' ', "#remove_me#")
        if not govc_client.get_vm_ip(vm_name, datacenter_name=data_center):
            current_app.logger.info("Deploying avi controller..")
            govc_client.deploy_library_ova(location=controller_ova_location, name=vm_name, options=deploy_options)
            if env == Env.VMC:
                avi_size = request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviSize']
            elif isEnvTkgs_wcp(env):
                avi_size = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviSize']
            else:
                avi_size = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviSize']
            size = str(avi_size).lower()
            if size not in ["essentials", "small", "medium", "large"]:
                current_app.logger.error("Wrong avi size provided supported  essentials/small/medium/large " + avi_size)
                d = {
                    "responseType": "ERROR",
                    "msg": "Wrong avi size provided supported  essentials/small/medium/large " + avi_size,
                    "ERROR_CODE": 500
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
            change_VM_config = ["govc", "vm.change", "-dc=" + data_center.replace("#remove_me#", " "), "-vm=" + vm_name,
                                "-c=" + cpu,
                                "-m=" + memory]
            power_on = ["govc", "vm.power", "-dc=" + data_center.replace("#remove_me#", " "), "-on=true", vm_name]
            runProcess(change_VM_config)
            runProcess(power_on)
            ip = govc_client.get_vm_ip(vm_name, datacenter_name=data_center, wait_time='30m')
            if ip is None:
                current_app.logger.error("Failed to get ip of avi controller on waiting 30m")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get ip of avi controller on waiting 30m",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
    except Exception as e:
        current_app.logger.error("Failed to deploy  the vm from library due to " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy  the vm from library due to " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    ip = govc_client.get_vm_ip(vm_name, datacenter_name=data_center)[0]
    current_app.logger.info("Checking controller is up")
    if check_controller_is_up(ip) is None:
        current_app.logger.error("Controller service is not up")
        d = {
            "responseType": "ERROR",
            "msg": "Controller service is not up",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    deployed_avi_version = obtain_avi_version(ip, env)
    if deployed_avi_version[0] is None:
        current_app.logger.error("Failed to login and obtain avi version" + str(deployed_avi_version[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
            "ERROR_CODE": 500
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
            "msg": "Deployed avi version " + str(
                avi_version) + " is not supported, supported version is: " + avi_required,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if performOtherTask:
        csrf = obtain_first_csrf(ip)
        if csrf is None:
            current_app.logger.error("Failed to get First csrf value.")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get First csrf",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if csrf == "SUCCESS":
            current_app.logger.info("Password of appliance already changed")
        else:
            if set_avi_admin_password(ip, csrf, avi_version, env) is None:
                current_app.logger.error("Failed to set the avi admin password")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to set the avi admin password",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        csrf2 = obtain_second_csrf(ip, env)
        if csrf2 is None:
            current_app.logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Obtained csrf with new credential successfully")
        if get_system_configuration_and_set_values(ip, csrf2, avi_version, env) is None:
            current_app.logger.error("Failed to set the system configuration")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to set the system configuration",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Got system configuration successfully")
        if set_dns_ntp_smtp_settings(ip, csrf2, avi_version) is None:
            current_app.logger.error("Set Dns Ntp smtp failed.")
            d = {
                "responseType": "ERROR",
                "msg": "Set Dns Ntp smtp failed.",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Set DNs Ntp Smtp successfully")
        if disable_welcome_screen(ip, csrf2, avi_version, env) is None:
            current_app.logger.error("Failed to disable welcome screen")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to disable welcome screen",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Disable welcome screen successfully")
        backup_url = get_backup_configuration(ip, csrf2, avi_version)
        if backup_url[0] is None:
            current_app.logger.error("Failed to get backup configuration")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get backup configuration " + backup_url[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Got backup configuration successfully")
        current_app.logger.info("Set backup pass phrase")
        setBackup = setBackupPhrase(ip, csrf2, backup_url[0], avi_version, env)
        if setBackup[0] is None:
            current_app.logger.error("Failed to set backup pass phrase")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to set backup pass phrase " + str(setBackup[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured avi",
        "ERROR_CODE": 200
    }
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
        "x-csrftoken": csrf2[0]
    }
    with open('./detailsOfServiceEngine1.json', 'r') as openfile:
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
        "x-csrftoken": csrf2[0]
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
        "x-csrftoken": csrf2[0]
    }

    try:
        data_center = current_app.config['VC_DATACENTER']
        info, status = get_avi_cluster_info(ip, csrf2, aviVersion)
        if info is None:
            return None, "Failed to get cluster info " + str(status)
        if isEnvTkgs_wcp(env):
            avi_ip = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Ip']
            avi_ip2 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Ip']
            avi_ip3 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Ip']
            clusterIp = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterIp']
        elif env == Env.VMC:
            avi_ip = ip
            avi_ip2 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME2, datacenter_name=data_center)[0]
            if avi_ip2 is None:
                return None, "Failed to get 2nd controller ip"
            avi_ip3 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME3, datacenter_name=data_center)[0]
            if avi_ip3 is None:
                return None, "Failed to get 3rd controller ip"
            clusterIp = request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviClusterIp']
        else:
            avi_ip = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Ip']
            avi_ip2 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Ip']
            avi_ip3 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Ip']
            clusterIp = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviClusterIp']
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
            except:
                pass
        if avi_ip in _list and avi_ip2 in _list and avi_ip3 in _list:
            current_app.logger.info("Avi HA cluster is already configured")
            return "SUCCESS", "Avi HA cluster is already configured"
        current_app.logger.info("Forming Ha cluster")
        payload = AlbPayload.AVI_HA_CLUSTER.format(cluster_uuid=info["uuid"], cluster_name="Alb-Cluster",
                                                   cluster_ip1=avi_ip, vm_uuid_get=_cluster["vm_uuid"],
                                                   vm_mor_get=_cluster["vm_mor"],
                                                   vm_hostname_get=_cluster["vm_hostname"], cluster_ip2=avi_ip2,
                                                   cluster_ip3=avi_ip3, tennat_uuid_get=info["tenant_uuid"],
                                                   virtual_ip_get=clusterIp)
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
            except:
                pass
            time.sleep(10)
            current_app.logger.info("Waited " + str(count * 10) + "s for getting cluster ips, retrying")
            count = count + 1

        if avi_ip not in list_of_nodes or avi_ip2 not in list_of_nodes or not avi_ip3 in list_of_nodes:
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
                    current_app.logger.info("Checking node " + str(node_statuses[0]["mgmt_ip"]) + " state: " + str(
                        node_statuses[0]["state"]))
                    current_app.logger.info("Checking node " + str(node_statuses[1]["mgmt_ip"]) + " state: " + str(
                        node_statuses[1]["state"]))
                    current_app.logger.info("Checking node " + str(node_statuses[2]["mgmt_ip"]) + " state: " + str(
                        node_statuses[2]["state"]))
                    current_app.logger.info(
                        "***********************************************************************************")
                    if node_statuses[0]["state"] == "CLUSTER_ACTIVE" and node_statuses[1][
                        "state"] == "CLUSTER_ACTIVE" and node_statuses[2]["state"] == "CLUSTER_ACTIVE":
                        all_up = True
                        break
            except:
                pass
            runtime = runtime + 1
            time.sleep(10)
        if not all_up:
            return None, "All nodes are not in active atate on wating 30 min"
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
        "x-csrftoken": csrf2[0]
    }
    url = "https://" + ip + "/api/sslkeyandcertificate"
    json_object = json.dumps(body, indent=4)
    response_csrf = requests.request("GET", url, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for re in response_csrf.json()["results"]:
            if re['name'] == name:
                return re["url"], "SUCCESS"
        return "NOT_FOUND", "SUCCESS"


def import_ssl_certificate(ip, csrf2, certificate, certificate_key, env, avi_version):
    body = AlbPayload.IMPORT_CERT.format(cert=certificate, cert_key=certificate_key)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0]
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
        dic['issuer_common_name'] = output['certificate']['issuer']['common_name']
        dic['issuer_distinguished_name'] = output['certificate']['issuer']['distinguished_name']
        dic['subject_common_name'] = output['certificate']['subject']['common_name']
        dic['subject_organization_unit'] = output['certificate']['subject']['organization_unit']
        dic['subject_organization'] = output['certificate']['subject']['organization']
        dic['subject_locality'] = output['certificate']['subject']['locality']
        dic['subject_state'] = output['certificate']['subject']['state']
        dic['subject_country'] = output['certificate']['subject']['country']
        dic['subject_distinguished_name'] = output['certificate']['subject']['distinguished_name']
        dic['not_after'] = output['certificate']['not_after']
        dic['cert_name'] = certName
        return dic, "SUCCESS"


def create_imported_ssl_certificate(ip, csrf2, dic, cer, key, env, avi_version):
    if env == Env.VMC:
        certName = CertName.NAME
    else:
        certName = CertName.VSPHERE_CERT_NAME
    body = AlbPayload.IMPORTED_CERTIFICATE.format(cert=cer, subject_common_name=dic['subject_common_name'],
                                                  org_unit=dic['subject_organization_unit'],
                                                  org=dic['subject_organization'], location=dic['subject_locality'],
                                                  state_name=dic['subject_state'], country_name=dic['subject_country'],
                                                  distinguished_name=dic['subject_distinguished_name'],
                                                  not_after_time=dic['not_after'], cert_name=certName, cert_key=key)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0]
    }
    url = AlbEndpoint.CRUD_SSL_CERT.format(ip=ip)
    response_csrf = requests.request("POST", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 201:
        return None, response_csrf.text
    else:
        return response_csrf.json()["url"], "SUCCESS"


def generate_ssl_certificate(ip, csrf2, avi_version):
    ips = [ip]
    data_center = current_app.config['VC_DATACENTER']
    if isAviHaEnabled(Env.VMC):
        govc_client = GovcClient(current_app.config, LocalCmdHelper())
        avi_ip2 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME2, datacenter_name=data_center)
        if avi_ip2 is None:
            return None, "Failed to get 2nd controller ip"
        avi_ip3 = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME3, datacenter_name=data_center)
        if avi_ip3 is None:
            return None, "Failed to get 3rd controller ip"
        clusterIp = request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviClusterIp']
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
        "x-csrftoken": csrf2[0]
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
            avi_fqdn2 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Fqdn']
            avi_ip2 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Ip']
            avi_fqdn3 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Fqdn']
            avi_ip3 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Ip']
            clusterIp = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviClusterIp']
            cluster_fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']["aviClusterFqdn"]
        else:
            avi_fqdn2 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Fqdn']
            avi_ip2 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Ip']
            avi_fqdn3 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Fqdn']
            avi_ip3 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Ip']
            clusterIp = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviClusterIp']
            cluster_fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
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
        "x-csrftoken": csrf2[0]
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
        "x-csrftoken": csrf2[0]
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
        replaceCertConfig("systemConfig.json", "portal_configuration", "sslkeyandcertificate_refs",
                          generated_ssl_url)
        return response_csrf.json()["url"], "SUCCESS"


def replaceWithNewCert(ip, csrf2, aviVersion):
    with open("./systemConfig.json", 'r') as file2:
        json_object = json.load(file2)

    json_object_mo = json.dumps(json_object, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
        "x-csrftoken": seconcsrf[0]
    }
    if env == Env.VMC:
        str_enc_avi_backup = str(
            request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviBackupPassPhraseBase64'])
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi_backup = str(
                request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviBackupPassphraseBase64'])
        else:
            str_enc_avi_backup = str(
                request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviBackupPassphraseBase64'])
    base64_bytes_avi_backup = str_enc_avi_backup.encode('ascii')
    enc_bytes_avi_backup = base64.b64decode(base64_bytes_avi_backup)
    password_avi_backup = enc_bytes_avi_backup.decode('ascii').rstrip("\n")
    body = {
        "add": {"backup_passphrase": password_avi_backup}
    }
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
        "x-csrftoken": second_csrf[0]
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
        "x-csrftoken": second_csrf[0]
    }
    body = AlbPayload.WELCOME_SCREEN_UPDATE.format(tenant_vrf=json.dumps(env == Env.VMC))
    response_csrf = requests.request("PATCH", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None
    else:
        return "SUCCESS"


def set_dns_ntp_smtp_settings(ip, second_csrf, avi_version):
    with open('./systemConfig1.json', 'r') as openfile:
        json_object = json.load(openfile)
    url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": second_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": second_csrf[0]
    }
    json_object_m = json.dumps(json_object, indent=4)
    response_csrf = requests.request("PUT", url, headers=headers, data=json_object_m, verify=False)
    if response_csrf.status_code != 200:
        return None
    else:
        return "SUCCESS"


def get_system_configuration_and_set_values(ip, second_csrf, avi_version, env):
    url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": second_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": second_csrf[0]
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None
    os.system("rm -rf ./systemConfig1.json")
    json_object = json.dumps(response_csrf.json(), indent=4)
    if env == Env.VMC:
        ntp = request.get_json(force=True)['envVariablesSpec']['ntpServersIp']
        dns = request.get_json(force=True)['envVariablesSpec']['dnsServersIp']
        search_domain = request.get_json(force=True)['envVariablesSpec']['searchDomains']
    else:
        ntp = request.get_json(force=True)['envSpec']['infraComponents']['ntpServers']
        dns = request.get_json(force=True)['envSpec']['infraComponents']['dnsServersIp']
        search_domain = request.get_json(force=True)['envSpec']['infraComponents']['searchDomains']
    with open("./systemConfig1.json", "w") as outfile:
        outfile.write(json_object)
    replaceValueSysConfig("./systemConfig1.json", "default_license_tier", "name", "ENTERPRISE")
    replaceValueSysConfig("./systemConfig1.json", "email_configuration", "smtp_type", "SMTP_NONE")
    replaceValueSysConfig("./systemConfig1.json", "dns_configuration", "false",
                          dns)
    replaceValueSysConfig("./systemConfig1.json", "ntp_configuration", "ntp",
                          ntp)
    replaceValueSysConfig("./systemConfig1.json", "dns_configuration", "search_domain",
                          search_domain)
    if isEnvTkgs_wcp(env):
        replaceValueSysConfig("./systemConfig1.json", "portal_configuration", "allow_basic_authentication",
                              "true")
    return "SUCCESS"


def set_avi_admin_password(ip, first_csrf, avi_version, env):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": first_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": first_csrf[0]
    }
    if env == Env.VMC:
        str_enc_avi = str(request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviPasswordBase64'])
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi = str(
                request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
        else:
            str_enc_avi = str(
                request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
    base64_bytes_avi = str_enc_avi.encode('ascii')
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode('ascii').rstrip("\n")
    payload = {"old_password": "58NFaGDJm(PJH0G",
               "password": password_avi,
               "username": "admin"
               }
    modified_payload = json.dumps(payload, indent=4)
    url = "https://" + ip + "/api/useraccount"
    response_csrf = requests.request("PUT", url, headers=headers, data=modified_payload, verify=False)
    if response_csrf.status_code != 200:
        return None
    else:
        return "SUCCESS"


def obtain_second_csrf(ip, env):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if env == Env.VMC:
        str_enc_avi = str(request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviPasswordBase64'])
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi = str(
                request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
        else:
            str_enc_avi = str(
                request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
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
    current_app.config['csrftoken'] = cookiesString['csrftoken']
    return cookiesString['csrftoken'], cookies_string


def obtain_avi_version(ip, env):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if env == Env.VMC:
        str_enc_avi = str(request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviPasswordBase64'])
    else:
        if isEnvTkgs_wcp(env):
            str_enc_avi = str(
                request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
        else:
            str_enc_avi = str(
                request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
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


def obtain_first_csrf(ip):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "username": "admin",
        "password": "58NFaGDJm(PJH0G"
    }
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
    return cookiesString['csrftoken'], cookies_string


def check_controller_is_up(ip):
    url = "https://" + str(ip)
    headers = {
        "Content-Type": "application/json"
    }
    payload = {}
    response_login = None
    count = 0
    status = None
    try:
        response_login = requests.request("GET", url, headers=headers, data=payload, verify=False)
        status = response_login.status_code
    except:
        pass
    while (status != 200 or status is None) and count < 150:
        count = count + 1
        try:
            response_login = requests.request("GET", url, headers=headers, data=payload, verify=False)
            if response_login.status_code == 200:
                break
        except:
            pass
        current_app.logger.info("Waited for  " + str(count * 10) + "s, retrying.")
        time.sleep(10)
    if response_login is not None:
        if response_login.status_code != 200:
            return None
        else:
            current_app.logger.info("Controller is up and running in   " + str(count * 10) + "s.")
            return "UP"
    else:
        current_app.logger.error("Controller is not reachable even after " + str(count * 10) + "s wait")
        return None


def proxy_check_and_env_setup(env):
    if checkTmcEnabled(env) and (
            checkMgmtProxyEnabled(env) or checkSharedServiceProxyEnabled(env) or checkWorkloadProxyEnabled(env)):
        return 500
    else:
        return 200


def check_arcas_proxy_enabled(env):
    if env == Env.VMC:
        enableArcasProxy = "false"
    elif env == Env.VSPHERE or env == Env.VCF:
        try:
            enableArcasProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['enableProxy'])
        except Exception as e:
            enableArcasProxy = "false"
    else:
        return False
    if enableArcasProxy.lower() == "true":
        return True
    else:
        return False


def enableProxy(env):
    try:
        if env == Env.VMC:
            enable_arcas_proxy = "false"
        elif env == Env.VSPHERE or env == Env.VCF:
            if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
                enable_arcas_proxy = "false"
            else:
                enable_arcas_proxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['enableProxy'])
        else:
            current_app.logger.info("Wrong env type " + env)
            return 500
        if enable_arcas_proxy.lower() == "true":
            httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['httpProxy'])
            httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['httpsProxy'])
            noProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['noProxy'])
            if noProxy:
                noProxy = ", " + noProxy
            os.environ["http_proxy"] = httpProxy
            os.environ["https_proxy"] = httpsProxy
            os.environ["no_proxy"] = "localhost,127.0.0.1" + noProxy
            if not os.path.isfile("./proxy.bak"):
                back_command = ["cp", "/etc/sysconfig/proxy", "./proxy.bak"]
                runShellCommandAndReturnOutputAsList(back_command)
            data = f'''PROXY_ENABLED="yes"
HTTP_PROXY="{httpProxy}"
HTTPS_PROXY="{httpsProxy}"
NO_PROXY="localhost,127.0.0.1{noProxy}"
    '''
            proxy_file = {
                "file_name": "/etc/sysconfig/proxy",
                "docker_file": "/etc/systemd/system/docker.service.d/http-proxy.conf"
            }
            with open(proxy_file["file_name"], 'w') as f:
                f.write(data)
            if not os.path.isdir("/etc/systemd/system/docker.service.d"):
                command = ["mkdir", "/etc/systemd/system/docker.service.d"]
                runShellCommandAndReturnOutputAsList(command)
            command_touch = ["touch", "/etc/systemd/system/docker.service.d/http-proxy.conf"]
            runShellCommandAndReturnOutputAsList(command_touch)
            docker_data = f'''[Service]
Environment="HTTP_PROXY={httpProxy}"
Environment="HTTPS_PROXY={httpsProxy}"
Environment="NO_PROXY=localhost,127.0.0.1{noProxy}"
            '''
            with open(proxy_file["docker_file"], 'w') as f:
                f.write(docker_data)
            docker_reload = ["systemctl", "daemon-reload"]
            runShellCommandAndReturnOutputAsList(docker_reload)
            docker_restart = ["systemctl", "restart", "docker"]
            runShellCommandAndReturnOutputAsList(docker_restart)
            return 200
        elif enable_arcas_proxy.lower() == "false":
            current_app.logger.info("SIVT VM proxy setting is disabled")
            return 200
        else:
            current_app.logger.info("Wrong value of SIVT VM proxy enable is provided " + enable_arcas_proxy)
            return 500
    except Exception as e:
        if str(e).__contains__("proxySpec"):
            return 200
        else:
            return 500


def validate_proxy_starts_wit_http(env, isShared, isWorkload):
    if checkMgmtProxyEnabled(env):
        httpMgmtProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['httpProxy'])
        httpsMgmtProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['httpsProxy'])
        if not httpMgmtProxy.startswith("http://") or not httpsMgmtProxy.startswith("http://"):
            return "management"
    if checkSharedServiceProxyEnabled(env) and isShared:
        httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['httpProxy'])
        httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['httpsProxy'])
        if not httpProxy.startswith("http://") or not httpsProxy.startswith("http://"):
            return "shared"
    if checkWorkloadProxyEnabled(env) and isWorkload:
        httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['httpProxy'])
        httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['httpsProxy'])
        if not httpProxy.startswith("http://") or not httpsProxy.startswith("http://"):
            return "workload"
    try:
        enableArcasProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['enableProxy'])
    except:
        return "Success"
    if enableArcasProxy.lower() == "true":
        httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['httpProxy'])
        httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['httpsProxy'])
        if not httpProxy.startswith("http://") or not httpsProxy.startswith("http://"):
            return "arcas"
    return "Success"


def disable_proxy():
    os.unsetenv("http_proxy")
    os.unsetenv("https_proxy")
    os.unsetenv("no_proxy")
    os.system("cat > /etc/sysconfig/proxy << EOF\n"
              "PROXY_ENABLED=\"no\"\n"
              "HTTP_PROXY=\"\"\n"
              "HTTPS_PROXY=\"\"\n"
              "FTP_PROXY=\"\"\n"
              "GOPHER_PROXY=\"\"\n"
              "SOCKS_PROXY=\"\"\n"
              "SOCKS5_SERVER=\"\"\n"
              "NO_PROXY=\"localhost, 127.0.0.1\"\n"
              "EOF")
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
                    request.get_json(force=True)['envSpec']['proxySpec']['arcasVm']['disable-proxy'])
        else:
            current_app.logger.info("Wrong env type " + env)
            return 500
        if disableArcasProxy.lower() == "true":
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)
            os.environ.pop('no_proxy', None)
            # os.unsetenv("https_proxy")
            # os.unsetenv("no_proxy")
            if os.path.isfile("./proxy.bak"):
                os.system("rm -rf /etc/sysconfig/proxy")
                os.system("cp ./proxy.bak /etc/sysconfig/proxy")
            if os.path.isfile("/etc/systemd/system/docker.service.d/http-proxy.conf"):
                os.system("rm -rf /etc/systemd/system/docker.service.d/http-proxy.conf")
                os.system("systemctl daemon-reload")
                os.system("systemctl restart docker")
            return 200
        elif disableArcasProxy.lower() == "false":
            current_app.logger.info("Arcas vm proxy setting is disabled")
            return 200
        else:
            current_app.logger.info("Arcas VM proxy disablement failed.")
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
            mgmt_proxy = request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['enableProxy']
        except:
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
            shared_proxy = request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['enableProxy']
        except:
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
            workload_proxy = request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['enableProxy']
        except:
            return False
    if workload_proxy.lower() == "true":
        return True
    else:
        return False


def checkTmcEnabled(env):
    if env == Env.VMC:
        try:
            tmc_required = str(request.get_json(force=True)["saasEndpoints"]['tmcDetails']['tmcAvailability'])
        except:
            return False
    else:
        try:
            tmc_required = str(
                request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails']['tmcAvailability'])
        except:
            return False
    if tmc_required.lower() == "true":
        return True
    else:
        return False


def manage_avi_certificates(ip, avi_version, env, avi_fqdn, cert_name):
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get csrf from new set password",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, False
    try:
        if env == Env.VMC:
            avi_cert = request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviCertPath']
            avi_key = request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviCertKeyPath']
            license_key = ""
        elif isEnvTkgs_wcp(env):
            avi_cert = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviCertPath']
            avi_key = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviCertKeyPath']
            license_key = ""
        else:
            avi_cert = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviCertPath']
            avi_key = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviCertKeyPath']
            license_key = ""
    except:
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
            d = {
                "responseType": "ERROR",
                "msg": msg1 + " " + msg2,
                "ERROR_CODE": 500
            }
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
            d = {
                "responseType": "ERROR",
                "msg": "Certificate or key provided is empty",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500, False
        import_cert, error = import_ssl_certificate(ip, csrf2, avi_controller_cert, avi_controller_cert_key, env,
                                                    avi_version)
        if import_cert is None:
            current_app.logger.error("Avi cert import failed " + str(error))
            d = {
                "responseType": "ERROR",
                "msg": "Avi cert import failed " + str(error),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500, False
        cert_name = import_cert['cert_name']
    get_cert = get_ssl_certificate_status(ip, csrf2, cert_name, avi_version)
    if get_cert[0] is None:
        current_app.logger.error("Failed to get certificate status " + str(get_cert[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get certificate status " + str(get_cert[1]),
            "ERROR_CODE": 500
        }
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
            d = {
                "responseType": "ERROR",
                "msg": "Failed to generate the ssl certificate " + res[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500, False
    else:
        url = get_cert[0]
    get_cert = get_current_cert_config(ip, csrf2, url, avi_version)
    if get_cert[0] is None:
        current_app.logger.error("Failed to get current certificate")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get current certificate " + get_cert[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, False
    current_app.logger.info("Replacing cert")
    replace_cert = replaceWithNewCert(ip, csrf2, avi_version)
    if replace_cert[0] is None:
        current_app.logger.error("Failed replace the certificate" + replace_cert[1])
        d = {
            "responseType": "ERROR",
            "msg": "Failed replace the certificate " + replace_cert[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, False
    if license_key:
        res, status = configure_alb_licence(ip, csrf2, license_key, avi_version)
        if res is None:
            current_app.logger.error("Failed to apply licesnce " + str(status))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to apply licesnce " + str(status),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500, False
        current_app.logger.info(status)
    d = {
        "responseType": "SUCCESS",
        "msg": "Certificate managed successfully",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200, True


def configure_alb_licence(ip, csrf2, license_key, avi_version):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0]
    }
    body = AlbPayload.LICENSE.format(serial_number=license_key)
    url = AlbEndpoint.LICENSE_URL.format(ip=ip)
    response_csrf = requests.request("GET", url, headers=headers, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    licenses = response_csrf.json()["licenses"]
    for license in licenses:
        if license["license_string"] == license_key:
            return "SUCESS", "Already license is applied"
    response_csrf = requests.request("PUT", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    response_csrf = requests.request("GET", url, headers=headers, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    licenses = response_csrf.json()["licenses"]
    for license in licenses:
        if license["license_string"] == license_key:
            return "SUCESS", "License is applied successfully"
    return None, "Failed to apply License"


def registerWithTmc(management_cluster, env, isProxy, type, clusterGroup):
    if not checkTmcRegister(management_cluster, True):
        proxy_cred_state = createProxyCredentialsTMC(env=env, clusterName=management_cluster, isProxy=isProxy,
                                                     type=type, register=True)
        if proxy_cred_state[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": proxy_cred_state[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        proxy_name = "arcas-" + management_cluster + "-tmc-proxy"

        if str(isProxy).lower() == "true":
            current_app.logger.info("Registering to tmc with proxy")
            listOfCommandRegister = ["tmc", "managementcluster", "register", management_cluster, "-c", clusterGroup,
                                     "-p",
                                     "TKG", "--proxy-name", proxy_name,
                                     "-k", "kubeconfig.yaml"]
        else:
            current_app.logger.info("Registering to tmc")
            listOfCommandRegister = ["tmc", "managementcluster", "register", management_cluster, "-c", clusterGroup,
                                     "-p",
                                     "TKG",
                                     "-k", "kubeconfig.yaml"]

        register_output = runProcessTmcMgmt(listOfCommandRegister)
        if register_output == "FAIL":
            current_app.logger.error("Failed to register Management Cluster with TMC")
            current_app.logger.info("Continuing registration to apply the Tanzu Mission Control resource manifest to complete registration")
            listOfCommandRegister.append("--continue-bootstrap")
            runProcess(listOfCommandRegister)

        current_app.logger.info("Registered to tmc")
        current_app.logger.info("Waiting for 2 min for health status = ready…")
        for i in tqdm(range(120), desc="Waiting for health status…", ascii=False, ncols=75):
            time.sleep(1)
        state = checkClusterStateOnTmc(management_cluster, True)
        if state[0] == "SUCCESS":
            current_app.logger.info("Registered to tmc successfully")
            return "SUCCESS", 200
        else:
            return None, state[1]
    else:
        current_app.logger.info("Management cluster is already registered with tmc")
        return "SUCCESS", 200


def checkTmcRegister(cluster, ifManagement):
    try:
        if ifManagement:
            list = ["tmc", "managementcluster", "list"]
        else:
            list = ["tmc", "cluster", "list"]
        o = runShellCommandAndReturnOutput(list)
        if o[0].__contains__(cluster):
            current_app.logger.info("here ")
            state = checkClusterStateOnTmc(cluster, ifManagement)
            if state[0] == "SUCCESS":
                return True
            else:
                return False
        else:
            return False
    except:
        return False


def returnListOfTmcCluster(cluster):
    list_ = ["tmc", "cluster", "list"]
    s = runShellCommandAndReturnOutputAsList(list_)
    li_ = []
    for s_ in s[0]:
        if str(s_).__contains__(cluster):
            for l in s_.split(" "):
                if l:
                    li_.append(l)
    return li_


def checkClusterStateOnTmc(cluster, ifManagement):
    try:
        if ifManagement:
            list = ["tmc", "managementcluster", "get", cluster]
        else:
            li_ = returnListOfTmcCluster(cluster)
            list = ["tmc", "cluster", "get", li_[0], "-m", li_[1], "-p", li_[2]]
        o = runShellCommandAndReturnOutput(list)
        if o[1] == 0:
            l = yaml.safe_load(o[0])
            try:
                status = str(l["status"]["conditions"]["Agent-READY"]["status"])
            except:
                status = str(l["status"]["conditions"]["READY"]["status"])
            try:
                type = str(l["status"]["conditions"]["Agent-READY"]["type"])
            except:
                type = str(l["status"]["conditions"]["READY"]["type"])
            health = str(l["status"]["health"])
            if status == "TRUE":
                current_app.logger.info("Management cluster status " + status)
            else:
                current_app.logger.error("Management cluster status " + status)
                return "Failed", 500
            if type == "READY":
                current_app.logger.info("Management cluster type " + type)
            else:
                current_app.logger.error("Management cluster type " + type)
                return "Failed", 500
            if health == "HEALTHY":
                current_app.logger.info("Management cluster health " + health)
            else:
                current_app.logger.error("Management cluster health " + health)
                return "Failed", 500
            return "SUCCESS", 200
        else:
            return None, o[0]
    except Exception as e:
        return None, str(e)


def getCloudStatus(ip, csrf2, aviVersion, cloudName):
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


def seperateNetmaskAndIp(cidr):
    return str(cidr).split("/")


def getSECloudStatus(ip, csrf2, aviVersion, seGroupName):
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


def runSsh(vc_user):
    os.system("rm -rf /root/.ssh/id_rsa")
    os.system("ssh-keygen -t rsa -b 4096 -C '" + vc_user + "' -f /root/.ssh/id_rsa -N ''")
    os.system("eval $(ssh-agent)")
    os.system("ssh-add /root/.ssh/id_rsa")
    with open('/root/.ssh/id_rsa.pub', 'r') as f:
        re = f.readline()
    return re


def getClusterStatusOnTanzu(management_cluster, type):
    try:
        if type == "management":
            list = ["tanzu", "management-cluster", "get"]
        else:
            list = ["tanzu", "cluster", "get"]
        o = runShellCommandAndReturnOutput(list)
        if o[1] == 0:
            try:
                if o[0].__contains__(management_cluster) and o[0].__contains__("running"):
                    return True
                else:
                    return False
            except:
                return False
        else:
            return False
    except:
        return False


def getVipNetworkIpNetMask(ip, csrf2, name, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {}
    url = "https://" + ip + "/api/network"
    try:
        response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            for re in response_csrf.json()["results"]:
                if re['name'] == name:
                    for sub in re["configured_subnets"]:
                        return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]), "SUCCESS"
            else:
                next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                while len(next_url) > 0:
                    response_csrf = requests.request("GET", next_url, headers=headers, data=body, verify=False)
                    for re in response_csrf.json()["results"]:
                        if re['name'] == name:
                            for sub in re["configured_subnets"]:
                                return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(
                                    sub["prefix"]["mask"]), "SUCCESS"
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


def addStaticRoute(ip, csrf2, vrfUrl, routeIp, routId, aviVersion):
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


def checkAirGappedIsEnabled(env):
    if env == Env.VMC:
        air_gapped = ""
    else:
        try:
            air_gapped = request.get_json(force=True)['envSpec']['customRepositorySpec'][
                'tkgCustomImageRepository']
        except:
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
                    "identityManagementType"]
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
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if checkAirGappedIsEnabled(env):
        air_gapped_repo = str(
            request.get_json(force=True)['envSpec']['customRepositorySpec']['tkgCustomImageRepository'])
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        if not air_gapped_repo:
            current_app.logger.error("No repository provided")
            d = {
                "responseType": "ERROR",
                "msg": "No repository provided",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        repository = request.get_json(force=True)['envSpec']['customRepositorySpec']['tkgCustomImageRepository']
        if str(repository).startswith("http://"):
            pass
        elif str(repository).startswith("https://"):
            pass
        else:
            current_app.logger.error(
                "Invalid url provided, url must start with http:// or https:// but found  " + repository)
            d = {
                "responseType": "ERROR",
                "msg": "Invalid url provided url must start with http:// or https:// but found " + repository,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        try:
            response_csrf = requests.request("GET", repository, headers=headers, data={}, verify=False)
            if response_csrf.status_code != 200:
                current_app.logger.error("No connectivity  to repository " + repository)
                d = {
                    "responseType": "ERROR",
                    "msg": "No connectivity  to repository " + repository,
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        except Exception as e:
            current_app.logger.error("No connectivity  to repository " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "No connectivity  to repository " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        isSelfsinged = str(request.get_json(force=True)['envSpec']['customRepositorySpec'][
                               'tkgCustomImageRepositoryPublicCaCert'])
        s = air_gapped_repo[:air_gapped_repo.find("/")]
        if isSelfsinged.lower() == "false":
            repoAdd(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
            try:
                cmd_doc = ["systemctl", "restart", "docker"]
                runShellCommandWithPolling(cmd_doc)
            except Exception as e:
                current_app.logger.error("Failed to restart docker " + str(e))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to restart docker " + str(e),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
            with open('cert.txt', 'r') as file2:
                repo_cert = file2.readline()
            repo_certificate = repo_cert
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
        else:
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
        try:
            repo_usename = request.get_json(force=True)['envSpec']['customRepositorySpec'][
                'tkgCustomImageRepositoryUsername']
            repo_password = request.get_json(force=True)['envSpec']['customRepositorySpec'][
                'tkgCustomImageRepositoryPasswordBase64']
            base64_bytes = repo_password.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            repo_password = enc_bytes.decode('ascii').rstrip("\n")
        except Exception as e:
            repo_password = ""
            repo_usename = ""
        if repo_usename and repo_password:
            list_command = ["docker", "login", repository, "-u", repo_usename, "-p", repo_password]
            sta = runShellCommandAndReturnOutputAsList(list_command)
            if sta[1] != 0:
                current_app.logger.error("Docker login failed " + str(sta[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Docker login failed " + str(sta[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Docker login success")
            d = {
                "responseType": "SUCCESS",
                "msg": "Docker login success",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        current_app.logger.info("Airgapped precheck successfull")
        d = {
            "responseType": "SUCCESS",
            "msg": "Airgapped pre-check successful",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        d = {
            "responseType": "SUCCESS",
            "msg": "Air gapped not enabled",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def loadBomFile():
    try:
        with open(Extentions.BOM_LOCATION_14, "r") as stream:
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
    if not m.group('port'):
        return "443"
    else:
        return m.group('port')


def grabHostFromUrl(url):
    m = re.search(RegexPattern.URL_REGEX_PORT, url)
    if not m.group('host'):
        return None
    else:
        return m.group('host')


def checkTanzuExtentionEnabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)['tanzuExtensions']['enableExtensions'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def checkPromethusEnabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)['tanzuExtensions']['monitoring']['enableLoggingExtension'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_syslog_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint']['enableSyslogEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_http_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint']['enableHttpEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_elastic_search_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)['tanzuExtensions']['logging']['elasticSearchEndpoint'][
                'enableElasticSearchEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_kafka_endpoint_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)['tanzuExtensions']['logging']['kafkaEndpoint']['enableKafkaEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_splunk_endpoint_endpoint_enabled():
    try:
        tanzu_ext = str(
            request.get_json(force=True)['tanzuExtensions']['logging']['splunkEndpoint']['enableSplunkEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def switchToContext(clusterName, env):
    if isEnvTkgs_ns(env):
        name_space = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
        commands_shared = ["tanzu", "cluster", "kubeconfig", "get", clusterName, "--admin", "-n", name_space]
    else:
        commands_shared = ["tanzu", "cluster", "kubeconfig", "get", clusterName, "--admin"]
    kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand_shared is None:
        current_app.logger.error("Failed get admin cluster context of cluster " + clusterName)
        d = {
            "responseType": "ERROR",
            "msg": "Failed get admin cluster context of cluster " + clusterName,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
    if status[1] != 0:
        current_app.logger.error("Failed to switch to" + clusterName + "cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to switch to " + clusterName + " cluster context " + str(status[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info("Switched to " + clusterName + " context")
    d = {
        "responseType": "ERROR",
        "msg": "Switched to " + clusterName + " context",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def switchToManagementContext(clusterName):
    commands_shared = ["tanzu", "management-cluster", "kubeconfig", "get", clusterName, "--admin"]
    kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand_shared is None:
        current_app.logger.error("Failed get admin cluster context of cluster " + clusterName)
        d = {
            "responseType": "ERROR",
            "msg": "Failed get admin cluster context of cluster " + clusterName,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
    if status[1] != 0:
        current_app.logger.error("Failed to switch to" + clusterName + "cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to switch to " + clusterName + " cluster context " + str(status[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info("Switched to " + clusterName + " context")
    d = {
        "responseType": "ERROR",
        "msg": "Switched to " + clusterName + " context",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def waitForProcess(list1, podName):
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
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    current_app.logger.info("Successfully running " + podName)
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully running" + podName,
        "ERROR_CODE": 200
    }
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
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    current_app.logger.info("Successfully running " + podName)
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully running" + podName,
        "ERROR_CODE": 200
    }
    return jsonify(d), 200, count_cert


def verifyCluster(cluster_name):
    podRunninng = ["tanzu", "cluster", "list", "--include-management-cluster"]
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if not verifyPodsAreRunning(cluster_name, command_status[0], RegexPattern.running):
        return False
    else:
        return True


def installCertManagerAndContour(env, cluster_name, repo_address, service_name):
    podRunninng = ["tanzu", "cluster", "list", "--include-management-cluster"]
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if not verifyPodsAreRunning(cluster_name, command_status[0], RegexPattern.running):
        current_app.logger.error(cluster_name + " is not deployed")
        d = {
            "responseType": "ERROR",
            "msg": cluster_name + " is not deployed",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env):
        mgmt = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails']['tmcSupervisorClusterName']
    else:
        mgmt = getManagementCluster()
        if mgmt is None:
            current_app.logger.error("Failed to get management cluster")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get management cluster",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    if str(mgmt).strip() == cluster_name.strip():
        switch = switchToManagementContext(cluster_name.strip())
        if switch[1] != 200:
            current_app.logger.info(switch[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": switch[0].json['msg'],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    else:
        if isEnvTkgs_ns(env):
            name_space = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
            commands_shared = ["tanzu", "cluster", "kubeconfig", "get", cluster_name, "--admin", "-n", name_space]
        else:
            commands_shared = ["tanzu", "cluster", "kubeconfig", "get", cluster_name, "--admin"]
        kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kubeContextCommand_shared is None:
            current_app.logger.error("Failed to get switch to " + cluster_name + " cluster context command")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to " + cluster_name + " context command",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
        status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
        if status[1] != 0:
            current_app.logger.error("Failed to get switch to shared cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to " + cluster_name + " context " + str(status[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    if Tkg_version.TKG_VERSION == "1.3":
        state = extentionDeploy13(service_name, repo_address)
        if state[1] != 200:
            return state[0], state[1]
    if Tkg_version.TKG_VERSION == "1.5":
        status_ = checkRepositoryAdded(env)
        if status_[1] != 200:
            current_app.logger.error(str(status_[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": str(status_[0].json['msg']),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        install = installExtentionFor14(service_name, cluster_name, env)
        if install[1] != 200:
            return install[0], install[1]
    current_app.logger.info("Configured cert-manager and contour successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured cert-manager and contour extentions successfully",
        "ERROR_CODE": 200
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
        current_app.logger.error(" Failed to verify pod running ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to verify pod running",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    if not running:
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    d = {
        "responseType": "ERROR",
        "msg": "Successfully running " + podName + " ",
        "ERROR_CODE": 200
    }
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
        current_app.logger.error(" Failed to verify pod running ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to verify pod running",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    if not running:
        current_app.logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500, count_cert
    d = {
        "responseType": "ERROR",
        "msg": "Successfully running " + podName + " ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200, count_cert


def checkCertManagerRunning():
    list1 = ["kubectl", "get", "pods", "-A"]
    list2 = ["grep", "cert-manager"]
    dir = Extentions.TKG_EXTENTION_LOCATION
    podName = "cert-manager"
    try:
        cert_state = grabPipeOutputChagedDir(list1, list2, dir)
        if cert_state[1] != 0:
            current_app.logger.error("Failed to get " + podName + " " + cert_state[0])
            return False
        if verifyPodsAreRunning(podName, cert_state[0], RegexPattern.RUNNING):
            current_app.logger.info("Cert Manager is Running.")
            return True
    except Exception as e:
        return False
    return False


def changeRepo(repo_address):
    repo_address = repo_address.replace("https://", "").replace("http://", "")
    list_type = ["cert-manager-cainjector", "cert-manager", "cert-manager-webhook"]

    if not repo_address.endswith("/"):
        repo_address = repo_address + "/"
    for type_cert in list_type:
        repo = None
        if type_cert == "cert-manager-cainjector":
            repo = repo_address + Extentions.CERT_MANAGER_CA_INJECTOR
        elif type_cert == "cert-manager":
            repo = repo_address + Extentions.CERT_MANAGER_CONTROLLER
        elif type_cert == "cert-manager-webhook":
            repo = repo_address + Extentions.CERT_MANAGER_WEB_HOOK
        change_repo = "./common/injectValue.sh " + Extentions.CERT_MANAGER_LOCATION + "/03-cert-manager.yaml" + " cert " + repo + " " + type_cert
        os.system(change_repo)
    current_app.logger.info("Changed repo of cert manager Successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Changed repo of cert manager Successfully",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def deployExtention(extentionYaml, appName, nameSpace, extentionLocation):
    command_harbor_apply = ["kubectl", "apply", "-f", extentionYaml]
    state_harbor_apply = runShellCommandAndReturnOutputAsListWithChangedDir(
        command_harbor_apply,
        extentionLocation)
    if state_harbor_apply[1] == 500:
        current_app.logger.error(
            "Failed to apply " + str(state_harbor_apply[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to apply " + str(state_harbor_apply[0]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    listCommand = ["kubectl", "get", "app", appName, "-n", nameSpace]
    st = waitForProcess(listCommand, appName)
    if st[1] != 200:
        return st[0], st[1]
    else:
        current_app.logger.info(appName + " deployed, and is up and running")
        d = {
            "responseType": "SUCCESS",
            "msg": appName + " deployed, and is up and running",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def getManagementCluster():
    try:
        command = ["tanzu", "cluster", "list", "--include-management-cluster"]
        status = runShellCommandAndReturnOutput(command)
        mcs = status[0].split("\n")
        for mc in mcs:
            if str(mc).__contains__("management") and str(mc).__contains__("running"):
                return str(mc).split(" ")[2].strip()

        return None
    except Exception as e:
        return None


def createProxyCredentialsTMC(env, clusterName, isProxy, type, register=True):
    try:
        if register and type != "management":
            file = "kubeconfig_cluster.yaml"
            os.system("rm -rf " + file)
        pod_cidr = ""
        service_cidr = ""
        if env == Env.VMC:
            os.putenv("TMC_API_TOKEN",
                      request.get_json(force=True)["saasEndpoints"]['tmcDetails']['tmcRefreshToken'])
            user = TmcUser.USER
            if type == "management":
                pod_cidr = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterCidr']
                service_cidr = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtServiceCidr']
            elif type == "shared":
                pod_cidr = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceClusterCidr']
                service_cidr = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceServiceCidr']
            elif type == "workload":
                pod_cidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterCidr']
                service_cidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadServiceCidr']
        else:
            os.putenv("TMC_API_TOKEN",
                      request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                          'tmcRefreshToken'])
            user = TmcUser.USER_VSPHERE
            if type == "management":
                pod_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterCidr']
                service_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgMgmtServiceCidr']
            elif type == "shared":
                if env == Env.VSPHERE:
                    pod_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                        'tkgSharedserviceClusterCidr']
                    service_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                        'tkgSharedserviceServiceCidr']
                elif env == Env.VCF:
                    pod_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                        'tkgSharedserviceClusterCidr']
                    service_cidr = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                        'tkgSharedserviceServiceCidr']
            elif type == "workload":
                pod_cidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterCidr']
                service_cidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadServiceCidr']

        listOfCmdTmcLogin = ["tmc", "login", "--no-configure", "-name", user]
        runProcess(listOfCmdTmcLogin)
        if register and type != "management":
            current_app.logger.info("Registering to tmc on cluster " + clusterName)
            tmc_command = ["tanzu", "cluster", "kubeconfig", "get", clusterName, "--admin", "--export-file",
                           file]
            runProcess(tmc_command)
            current_app.logger.info("Got kubeconfig successfully")

        if str(isProxy).lower() == "true":
            current_app.logger.info("Attaching cluster to tmc using proxy command")
            name = "arcas-" + clusterName + "-tmc-proxy"

            if type == "workload":
                httpProxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['httpProxy'])
                httpsProxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['httpsProxy'])
                noProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['noProxy'])
            elif type == "shared":
                httpProxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['httpProxy'])
                httpsProxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['httpsProxy'])
                noProxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['noProxy'])
            elif type == "management":
                httpProxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['httpProxy'])
                httpsProxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['httpsProxy'])
                noProxy = str(
                    request.get_json(force=True)['envSpec']['proxySpec']['tkgMgmt']['noProxy'])

            if noProxy:
                noProxy = noProxy + ", " + pod_cidr + ", " + service_cidr
            try:
                if '@' in httpProxy:
                    http_proxy = httpProxy.split(":")
                    http_user = http_proxy[1].replace("//", "")
                    http_user = requests.utils.unquote(http_user)
                    _base64_bytes = http_user.encode('ascii')
                    _enc_bytes = base64.b64encode(_base64_bytes)
                    http_user = _enc_bytes.decode('ascii')

                    http_password = http_proxy[2].split("@")[0]
                    http_password = requests.utils.unquote(http_password)
                    _base64_bytes = http_password.encode('ascii')
                    _enc_bytes = base64.b64encode(_base64_bytes)
                    http_password = _enc_bytes.decode('ascii')
                else:
                    http_user = ""
                    http_password = ""

                if '@' in httpsProxy:
                    https_proxy = httpsProxy.split(":")
                    https_user = https_proxy[1].replace("//", "")
                    https_user = requests.utils.unquote(https_user)
                    _base64_bytes = https_user.encode('ascii')
                    _enc_bytes = base64.b64encode(_base64_bytes)
                    https_user = _enc_bytes.decode('ascii')

                    https_password = https_proxy[2].split("@")[0]
                    https_password = requests.utils.unquote(https_password)
                    _base64_bytes = https_password.encode('ascii')
                    _enc_bytes = base64.b64encode(_base64_bytes)
                    https_password = _enc_bytes.decode('ascii')
                else:
                    https_user = ""
                    https_password = ""

            except Exception as e:
                d = {
                    "responseType": "ERROR",
                    "msg": "Proxy url must be in the format http://<Proxy_User>:<URI_EncodedProxy_Password>@<Proxy_IP>:<Proxy_Port> or http://<Proxy_IP>:<Proxy_Port> ",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            generateTmcProxyYaml(name, httpProxy, httpsProxy, noProxy, http_user, http_password, https_user,
                                 https_password)
            credential = ["tmc", "account", "credential", "create", "-f", "tmc_proxy.yaml"]
            state_cred = runShellCommandAndReturnOutput(credential)
            if state_cred[1] != 0:
                current_app.logger.error("Failed to run create credential" + str(state_cred[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to run validate repository added command " + str(state_cred[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Successfully created credentials for TMC Proxy")
            return name, 200
        current_app.logger.info("Proxy credential configuration not required")
        return "Proxy credential configuration not required", 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Proxy credential creation on TMC failed for cluster " + clusterName + " " + str(e),
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def registerWithTmcOnSharedAndWorkload(env, clusterName, isProxy, type):
    try:
        if not checkTmcRegister(clusterName, False):
            proxy_cred_state = createProxyCredentialsTMC(env=env, clusterName=clusterName,
                                                         isProxy=isProxy, type=type, register=True)
            if proxy_cred_state[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": proxy_cred_state[0],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            name = "arcas-" + clusterName + "-tmc-proxy"

            if str(isProxy).lower() == "true":
                listOfCommandAttach = ["tmc", "cluster", "attach", "--name", clusterName, "--cluster-group", "default",
                                       "-k",
                                       file, "--proxy-name", name]
            else:
                current_app.logger.info("Attaching cluster to tmc")
                listOfCommandAttach = ["tmc", "cluster", "attach", "--name", clusterName, "--cluster-group", "default",
                                       "-k",
                                       file, "--force"]
            try:
                runProcess(listOfCommandAttach)
            except:
                d = {
                    "responseType": "ERROR",
                    "msg": "Filed to attach " + clusterName + "  to tmc",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            d = {
                "responseType": "SUCCESS",
                "msg": clusterName + " cluster attached to tmc successfully",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        else:
            d = {
                "responseType": "SUCCESS",
                "msg": clusterName + " Cluster is already attached to tmc",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Tmc registration failed on cluster " + clusterName + " " + str(e),
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def checkRepositoryAdded(env):
    if checkAirGappedIsEnabled(env):
        try:
            validate_command = ["tanzu", "package", "repository", "list", "-A"]

            status = runShellCommandAndReturnOutputAsList(validate_command)
            if status[1] != 0:
                current_app.logger.error("Failed to run validate repository added command " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to run validate repository added command " + str(str[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            REPOSITORY_URL = request.get_json(force=True)['envSpec']['customRepositorySpec'][
                'tkgCustomImageRepository']
            REPOSITORY_URL = str(REPOSITORY_URL).replace("https://", "").replace("http://", "")
            if not str(status[0]).__contains__(REPOSITORY_URL):
                list_command = ["tanzu", "package", "repository", "add", Repo.NAME, "--url", REPOSITORY_URL, "-n",
                                "tkg-custom-image-repository", "--create-namespace"]
                status = runShellCommandAndReturnOutputAsList(list_command)
                if status[1] != 0:
                    current_app.logger.error("Failed to run command to add repository " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run command to add repository " + str(str[0]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                status = runShellCommandAndReturnOutputAsList(validate_command)
                if status[1] != 0:
                    current_app.logger.error("Failed to run validate repository added command " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run validate repository added command " + str(str[0]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                current_app.logger.info(REPOSITORY_URL + " is already added")
            current_app.logger.info("Successfully  added repository " + REPOSITORY_URL)
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully  added repository " + REPOSITORY_URL,
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to add repository " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    else:
        try:
            validate_command = ["tanzu", "package", "repository", "list", "-n", TKG_Package_Details.NAMESPACE]
            status = runShellCommandAndReturnOutputAsList(validate_command)
            if status[1] != 0:
                current_app.logger.error("Failed to run validate repository added command " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to run validate repository added command " + str(str[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if not str(status[0]).__contains__(TKG_Package_Details.STANDARD_PACKAGE_URL):
                list_command = ["tanzu", "package", "repository", "add", TKG_Package_Details.REPO_NAME, "--url",
                                TKG_Package_Details.REPOSITORY_URL, "-n",
                                TKG_Package_Details.NAMESPACE]
                status = runShellCommandAndReturnOutputAsList(list_command)
                if status[1] != 0:
                    current_app.logger.error("Failed to run command to add repository " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run command to add repository " + str(str[0]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                status = runShellCommandAndReturnOutputAsList(validate_command)
                if status[1] != 0:
                    current_app.logger.error("Failed to run validate repository added command " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run validate repository added command " + str(str[0]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                current_app.logger.info(TKG_Package_Details.REPOSITORY_URL + " is already added")
            current_app.logger.info("Successfully  added repository " + TKG_Package_Details.REPOSITORY_URL)
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully validated repository " + TKG_Package_Details.REPOSITORY_URL,
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to validate tanzu standard repository status" + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500


def checkPinnipedInstalled():
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    sub_command = ["grep", AppName.PINNIPED]
    command_pinniped = grabPipeOutput(main_command, sub_command)
    if not verifyPodsAreRunning(AppName.PINNIPED, command_pinniped[0], RegexPattern.RECONCILE_SUCCEEDED):
        count_pinniped = 0
        found = False
        command_status_pinniped = grabPipeOutput(main_command, sub_command)
        while not verifyPodsAreRunning(AppName.PINNIPED, command_status_pinniped[0],
                                       RegexPattern.RECONCILE_SUCCEEDED) and count_pinniped < 20:
            command_status_pinniped = grabPipeOutput(main_command, sub_command)
            if verifyPodsAreRunning(AppName.PINNIPED, command_status_pinniped[0], RegexPattern.RECONCILE_SUCCEEDED):
                found = True
                break
            count_pinniped = count_pinniped + 1
            time.sleep(30)
            current_app.logger.info("Waited for  " + str(count_pinniped * 30) + "s, retrying.")
        if not found:
            current_app.logger.error(
                "Pinniped is not in RECONCILE SUCCEEDED state on waiting " + str(count_pinniped * 30))
            d = {
                "responseType": "ERROR",
                "msg": "Pinniped is not in RECONCILE SUCCEEDED state on waiting " + str(count_pinniped * 30),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    current_app.logger.info("Successfully validated Pinniped installation")
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully validated Pinniped installation",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def checkPinnipedServiceStatus():
    try:
        listOfCmd = ["kubectl", "get", "svc", "-n", "pinniped-supervisor"]
        output = runShellCommandAndReturnOutputAsList(listOfCmd)
        line1 = output[0][0].split()
        line2 = output[0][1].split()
        if str(line1[3]) == 'EXTERNAL-IP':
            try:
                ip = ipaddress.ip_address(str(line2[3]))
                current_app.logger.info("Successfully retrieved Load Balancers' External IP: " + str(line2[3]))
                current_app.logger.info(
                    "Update the callback URI with the Load Balancers' External IP: " + str(line2[3]))
                return "Load Balancers' External IP: " + str(line2[3]), 200
            except Exception as e:
                current_app.logger.error("Failed to retrieve Load Balancers' External IP")
                current_app.logger.error(str(e))
                return "Failed to retrieve Load Balancers' External IP", 500
        return "Failed to retrieve Load Balancers' External IP", 500
    except:
        return "Failed to retrieve Load Balancers' External IP", 500


def checkPinnipedDexServiceStatus():
    try:
        listOfCmd = ["kubectl", "get", "svc", "-n", "tanzu-system-auth"]
        output = runShellCommandAndReturnOutputAsList(listOfCmd)
        line1 = output[0][0].split()
        line2 = output[0][1].split()
        if str(line1[3]) == 'EXTERNAL-IP':
            try:
                ip = ipaddress.ip_address(str(line2[3]))
                current_app.logger.info("Successfully retrieved dexsvc Load Balancers' External IP: " + str(line2[3]))
                return "dexsvc Load Balancers' External IP: " + str(line2[3]), 200
            except Exception as e:
                current_app.logger.error(str(e))
                current_app.logger.error("Failed to retrieve dexsvc Load Balancers' External IP")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to retrieve dexsvc Load Balancers' External IP",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        return "Failed to retrieve dexsvc Load Balancers' External IP", 500
    except:
        return "Failed to retrieve dexsvc Load Balancers' External IP", 500


def createRbacUsers(clusterName, isMgmt, env, cluster_admin_users, admin_users, edit_users, view_users):
    try:
        if isMgmt:
            switch = switchToManagementContext(clusterName)
            if switch[1] != 200:
                current_app.logger.info(switch[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": switch[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        else:
            switch = switchToContext(clusterName, env=env)
            if switch[1] != 200:
                current_app.logger.info(switch[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": switch[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        if isMgmt:
            exportCmd = ["tanzu", "management-cluster", "kubeconfig", "get",
                         clusterName, "--export-file",
                         Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig"]
        else:
            exportCmd = ["tanzu", "cluster", "kubeconfig", "get",
                         clusterName, "--export-file",
                         Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig"]

        output = runShellCommandAndReturnOutputAsList(exportCmd)
        if output[1] == 0:
            current_app.logger.info(
                "Exported kubeconfig at  " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig")
        else:
            current_app.logger.error(
                "Failed to export config file to " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig")
            current_app.logger.error(output[0])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to export config file to " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig",
                "ERROR_CODE": 500
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
                    listOfCmd = ["kubectl", "create", "clusterrolebinding", username + "-crb",
                                 "--clusterrole", key, "--user", username]
                    output = runShellCommandAndReturnOutputAsList(listOfCmd)
                    if output[1] == 0:
                        current_app.logger.info("Created RBAC for user: " + username + " SUCCESSFULLY")
                        current_app.logger.info("Kubeconfig file has been generated and stored at " +
                                                Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig")
                    else:
                        current_app.logger.error("Failed to created Cluster Role Binding for user: " + username)
                        current_app.logger.error(output[0])
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to created Cluster Role Binding for user: " + username,
                            "ERROR_CODE": 500
                        }
                        return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "Created RBAC successfully for all the provided users",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.info("Some error occurred while creating cluster role bindings")
        d = {
            "responseType": "ERROR",
            "msg": "Some error occurred while creating cluster role bindings",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def installExtentionFor14(service_name, cluster, env):
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    service = service_name
    if service == "certmanager" or service == "all":
        sub_command = ["grep", AppName.CERT_MANAGER]
        command_cert = grabPipeOutput(main_command, sub_command)
        if not verifyPodsAreRunning(AppName.CERT_MANAGER, command_cert[0], RegexPattern.RECONCILE_SUCCEEDED):
            state = getVersionOfPackage("cert-manager.tanzu.vmware.com")
            if state is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Version of package cert-manager.tanzu.vmware.com",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Installing cert manager - " + state)
            install_command = ["tanzu", "package", "install", AppName.CERT_MANAGER, "--package-name",
                               "cert-manager.tanzu.vmware.com", "--namespace", "package-" + AppName.CERT_MANAGER,
                               "--version", state,
                               "--create-namespace"]
            states = runShellCommandAndReturnOutputAsList(install_command)
            if states[1] != 0:
                current_app.logger.error(
                    AppName.CERT_MANAGER + " installation command failed. Checking for reconciliation status..")
            certManagerStatus = waitForGrepProcessWithoutChangeDir(main_command, sub_command, AppName.CERT_MANAGER,
                                                                   RegexPattern.RECONCILE_SUCCEEDED)
            if certManagerStatus[1] == 500:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to bring cert-manager " + str(certManagerStatus[0].json['msg']),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Configured Cert manager successfully")
            if service != "all":
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Configured Cert manager successfully",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200
        else:
            current_app.logger.info("Cert manager is already running")
            if service != "all":
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Cert manager is already running",
                    "ERROR_CODE": 200
                }
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
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        sub_command = ["grep", AppName.CONTOUR]
        command_cert = grabPipeOutput(main_command, sub_command)
        if not verifyPodsAreRunning(AppName.CONTOUR, command_cert[0], RegexPattern.RECONCILE_SUCCEEDED):
            createContourDataValues(cluster)
            state = getVersionOfPackage("contour.tanzu.vmware.com")
            if state is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Version of package contour.tanzu.vmware.com",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Installing contour - " + state)
            install_command = ["tanzu", "package", "install", AppName.CONTOUR, "--package-name",
                               "contour.tanzu.vmware.com", "--version", state, "--values-file",
                               Paths.CLUSTER_PATH + cluster + "/contour-data-values.yaml", "--namespace",
                               "package-tanzu-system-contour",
                               "--create-namespace"]
            states = runShellCommandAndReturnOutputAsList(install_command)
            if states[1] != 0:
                for r in states[0]:
                    current_app.logger.error(r)
                current_app.logger.info(
                    AppName.CONTOUR + " install command failed. Checking for reconciliation status...")
            certManagerStatus = waitForGrepProcessWithoutChangeDir(main_command, sub_command, AppName.CONTOUR,
                                                                   RegexPattern.RECONCILE_SUCCEEDED)
            if certManagerStatus[1] == 500:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to bring contour " + str(certManagerStatus[0].json['msg']),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if service != "all":
                current_app.logger.info("Contour deployed and is up and running")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Contour deployed and is up and running",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200
        else:
            current_app.logger.info("Contour is already up and running")
            d = {
                "responseType": "SUCCESS",
                "msg": "Contour is already up and running",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured cert-manager and contour extentions successfully",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def getVersionOfPackage(packageName):
    list_h = []
    cert_package_cmd = ["tanzu", "package", "available", "list", packageName, "-A"]
    ss = runShellCommandAndReturnOutputAsList(cert_package_cmd)
    release_dates = []
    for s in ss[0]:
        if not s.__contains__("Retrieving package versions for " + packageName + "..."):
            if not s.__contains__("Waited for"):
                for nn in s.split("\n"):
                    if nn:
                        if not nn.split()[2].__contains__("RELEASED-AT"):
                            release_date = datetime.fromisoformat(nn.split()[2]).date()
                            release_dates.append(release_date)
                            list_h.append(nn)
    if len(list_h) == 0:
        current_app.logger.error("Failed to run get version list is empty")
        return None
    version = None
    for li in list_h:
        if li.__contains__(str(max(release_dates))):
            version = li.split(" ")[4]
            break
    if version is None or not version:
        current_app.logger.error("Failed to get version string is empty")
        return None
    return version


def createContourDataValues(clusterName):
    data = dict(
        infrastructure_provider='vsphere',
        namespace='tanzu-system-ingress',
        contour=dict(
            configFileContents={},
            useProxyProtocol=False,
            replicas=2,
            pspNames="vmware-system-restricted",
            logLevel="info"
        ),
        envoy=dict(
            service=dict(
                type='LoadBalancer',
                annotations={},
                nodePorts=dict(http="null", https="null"),
                externalTrafficPolicy='Cluster',
                disableWait=False),
            hostPorts=dict(enable=True, http=80, https=443),
            hostNetwork=False,
            terminationGracePeriodSeconds=300,
            logLevel="info",
            pspNames="null"
        ),
        certificates=dict(duration='8760h', renewBefore='360h')
    )
    with open(Paths.CLUSTER_PATH + clusterName + '/contour-data-values.yaml', 'w') as outfile:
        outfile.write("---\n")
        yaml1 = ruamel.yaml.YAML()
        yaml1.indent(mapping=2, sequence=4, offset=3)
        yaml1.dump(data, outfile)


def extentionDeploy13(service_name, repo_address):
    os.system("chmod +x common/injectValue.sh")
    load_bom = loadBomFile()
    if load_bom is None:
        current_app.logger.error("Failed to load the bom data ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to load the bom data",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    service = service_name
    if service == "certmanager" or service == "all":
        if not checkCertManagerRunning():
            repo_status = changeRepo(repo_address)
            if repo_status[1] != 200:
                current_app.logger.error(repo_status[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": repo_status[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Install Cert Manger")
            command_cert_manager = ["kubectl", "apply", "-f", "cert-manager/"]
            state = runShellCommandAndReturnOutputAsListWithChangedDir(command_cert_manager,
                                                                       Extentions.TKG_EXTENTION_LOCATION)
            if state[1] != 0:
                for i in tqdm(range(150), desc="Waiting…", ascii=False, ncols=75):
                    time.sleep(1)
                state2 = runShellCommandAndReturnOutputAsListWithChangedDir(command_cert_manager,
                                                                            Extentions.TKG_EXTENTION_LOCATION)
                if state2[1] != 0:
                    current_app.logger.error("Failed to apply certmanager " + str(state2[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to apply certmanager " + str(state2[0]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                current_app.logger.info(state[0])
            list1 = ["kubectl", "get", "pods", "-A"]
            list2 = ["grep", "cert-manager"]
            if waitForGrepProcess(list1, list2, "cert-manager", Extentions.TKG_EXTENTION_LOCATION)[1] == 500:
                current_app.logger.error("Failed to apply cert-manager " + state[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply cert-manager " + str(state[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            list1 = ["kubectl", "get", "pods", "-A"]
            list2 = ["grep", "kapp"]
            wait = waitForGrepProcess(list1, list2, "kapp", Extentions.TKG_EXTENTION_LOCATION)
            if wait[1] == 500:
                current_app.logger.error("Failed to apply kapp " + str(wait[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply kapp " + str(wait[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if wait[2] > 30:
                for i in tqdm(range(150), desc="Waiting…", ascii=False, ncols=75):
                    time.sleep(1)
            current_app.logger.info("Configured Cert manager successfully")
            if service != "all":
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Configured Cert manager successfully",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200
        else:
            current_app.logger.info("Cert manager is already running")
            if service != "all":
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Cert manager is already running",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200
    if service == "ingress" or service == "all":
        contour_validate_command = ["kubectl", "get", "app", "contour", "-n", "tanzu-system-ingress"]
        command_contour = runShellCommandAndReturnOutputAsList(contour_validate_command)
        if not verifyPodsAreRunning("contour", command_contour[0], RegexPattern.RECONCILE_SUCCEEDED):
            current_app.logger.info("Deploying contour..")
            command_contour = ["kubectl", "apply", "-f", "namespace-role.yaml"]
            state_contour = runShellCommandAndReturnOutputAsListWithChangedDir(command_contour,
                                                                               Extentions.CONTOUR_LOCATION)
            if state_contour[1] != 0:
                for i in tqdm(range(120), desc="Waiting for tanzu-system-ingress name space available …", ascii=False,
                              ncols=75):
                    time.sleep(1)
                state_contour = runShellCommandAndReturnOutputAsListWithChangedDir(command_contour,
                                                                                   Extentions.CONTOUR_LOCATION)
                if state_contour[1] != 0:
                    current_app.logger.error("Failed to apply countour " + str(state_contour[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to apply contour " + str(state_contour[0]),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                current_app.logger.info(state_contour[0])
            if repo_address.endswith("/"):
                repo_address = repo_address.rstrip("/")
            repo_address = repo_address.replace("https://", "").replace("http://", "")
            change_repo_contour = ["sh", "./common/injectValue.sh",
                                   Extentions.CONTOUR_LOCATION + "/vsphere/contour-data-values-lb.yaml.example",
                                   "contour", repo_address]

            state_change_repo_contour = runShellCommandAndReturnOutput(change_repo_contour)
            if state_change_repo_contour[1] != 0:
                current_app.logger.error("Failed to change contour repo " + str(state_change_repo_contour[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to change contour repo " + str(state_change_repo_contour[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            try:
                envoy_tag = load_bom['components']['envoy'][0]['images']['envoyImage']['tag']
                contor_tag = load_bom['components']['contour'][0]['images']['contourImage']['tag']
            except Exception as e:
                current_app.logger.error("Failed to get tag " + str(e))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get tag  " + str(e),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            os.system(
                "./common/injectValue.sh " + Extentions.CONTOUR_LOCATION + "/vsphere/contour-data-values-lb.yaml.example "
                                                                           "envoy_tag " + envoy_tag)
            os.system(
                "./common/injectValue.sh " + Extentions.CONTOUR_LOCATION + "/vsphere/contour-data-values-lb.yaml.example "
                                                                           "contour_tag " + contor_tag)
            command_contour_copy = ["cp", "./vsphere/contour-data-values-lb.yaml.example",
                                    "./vsphere/contour-data-values.yaml"]
            state_contour_copy = runShellCommandAndReturnOutputAsListWithChangedDir(command_contour_copy,
                                                                                    Extentions.CONTOUR_LOCATION)
            if state_contour_copy[1] != 0:
                current_app.logger.error("Failed to apply contour copy " + str(state_contour_copy[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply contour copy " + str(state_contour_copy[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            else:
                current_app.logger.info(state_contour_copy[0])
            command_contour_secret = ["kubectl", "create", "secret", "generic", "contour-data-values",
                                      "--from-file=values.yaml=vsphere/contour-data-values.yaml", "-n",
                                      "tanzu-system-ingress"]
            state_contour_secret = runShellCommandAndReturnOutputAsListWithChangedDir(command_contour_secret,
                                                                                      Extentions.CONTOUR_LOCATION)
            if state_contour_copy[1] != 0:
                current_app.logger.error("Failed to apply contour secret " + str(state_contour_secret[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply contour secret " + str(state_contour_secret[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            change_repo_contour_extention = ["sh", "./common/injectValue.sh",
                                             Extentions.CONTOUR_LOCATION + "/contour-extension.yaml",
                                             "app_extention", repo_address + "/" + Extentions.APP_EXTENTION]
            state_change_repo_contour_extention = runShellCommandAndReturnOutput(change_repo_contour_extention)
            if state_change_repo_contour_extention[1] != 0:
                current_app.logger.error(
                    "Failed to change contour repo in extension file " + str(state_change_repo_contour_extention[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to change contour repo in extension file  " + str(
                        state_change_repo_contour_extention[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            command_contour = ["kubectl", "apply", "-f", "contour-extension.yaml"]
            command_contour_out = runShellCommandAndReturnOutputAsListWithChangedDir(command_contour,
                                                                                     Extentions.CONTOUR_LOCATION)
            if command_contour_out[1] != 0:
                current_app.logger.error("Failed to apply contour" + str(command_contour_out[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply contour" + str(command_contour_out[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Validating contour app is running")
            list1 = ["kubectl", "get", "app", "contour", "-n", "tanzu-system-ingress"]
            contourStatus = waitForProcess(list1, "contour")
            if contourStatus[1] == 500:
                current_app.logger.error("Failed bring up contour " + str(contourStatus[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to apply contour secret " + str(contourStatus[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            else:
                if service != "all":
                    current_app.logger.error("Contour deployed and is up and running")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Contour deployed and is up and running",
                        "ERROR_CODE": 200
                    }
                    return jsonify(d), 200
        else:
            current_app.logger.info("Contour is up and running")
            if service != "all":
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Contour is up and running",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200

    d = {
        "responseType": "SUCCESS",
        "msg": "All extentions configured on 1.3 version of tanzu",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def createOverlayYaml(repository, clusterName):
    if not repository.endswith("/"):
        repository = repository + "/"
    os.system("rm -rf " + Paths.CLUSTER_PATH + "/harbor-overlay.yaml")
    os.system("chmod +x ./common/injectValue.sh")
    repository = repository + "harbor/notary-signer-photon@sha256:4dfbf3777c26c615acfb466b98033c0406766692e9c32f3bb08873a0295e24d1"
    os.system("cp ./common/harbor-overlay.yaml" + Paths.CLUSTER_PATH + "/harbor-overlay.yaml")
    os.system(
        "./common/injectValue.sh " + Paths.CLUSTER_PATH + "/harbor-overlay.yaml overlay " + repository)


def deployCluster(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                  folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                  sshKey, vsphereUseName, machineCount, size, env, type, vsSpec):
    try:
        if not getClusterStatusOnTanzu(sharedClusterName, "cluster"):
            kubeVersion = generateClusterYaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                                              folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool,
                                              vsphereServer,
                                              sshKey, vsphereUseName, machineCount, size, env, type, vsSpec)
            current_app.logger.info("Deploying " + sharedClusterName + "cluster")
            os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
            if Tkg_version.TKG_VERSION == "1.5":
                #if checkAirGappedIsEnabled(env):
                    #full_name = getKubeVersionFullNameNoCompatibilityCheck(kubeVersion)
                    #if full_name[1] != 200:
                        #current_app.logger.error("Failed to fetch full name for tkr version: " + kubeVersion)
                        #return None, "Failed to fetch full name for tkr version: " + kubeVersion
                    #else:
                        #current_app.logger.info("Successfully fetched complete name for tkr version: " + kubeVersion)
                        #kubeVersion = full_name[0]
                listOfCmd = ["tanzu", "cluster", "create", "-f",
                             Paths.CLUSTER_PATH + sharedClusterName + "/" + sharedClusterName + ".yaml", "--tkr",
                             kubeVersion,
                             "-v", "6"]
            else:
                listOfCmd = ["tanzu", "cluster", "create", "-f", sharedClusterName + ".yaml", "-v", "6"]
            runProcess(listOfCmd)
            return "SUCCESS", 200
        else:
            return "SUCCESS", 200
    except Exception as e:
        return None, str(e)


def generateClusterYaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                        folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                        sshKey, vsphereUseName, machineCount, size, env, type, vsSpec):
    if Tkg_version.TKG_VERSION == "1.5":
        return template14deployYaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                                    folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                                    sshKey, vsphereUseName, machineCount, size, env, type, vsSpec)
        # cluster14Yaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
        # folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
        # sshKey, vsphereUseName, machineCount, size, env, type)
    elif Tkg_version.TKG_VERSION == "1.3":
        template13deployYaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                             folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                             sshKey, vsphereUseName, machineCount, size, env, type, vsSpec)
        cluster13Yaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                      folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                      sshKey, vsphereUseName, machineCount, size, env, type)


def cluster14Yaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                  folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                  sshKey, vsphereUseName, machineCount, size, env, type):
    yaml_data = """\
    CLUSTER_CIDR: %s
    CLUSTER_NAME: %s
    CLUSTER_PLAN: %s
    ENABLE_CEIP_PARTICIPATION: "true"
    ENABLE_MHC: "true"
    IDENTITY_MANAGEMENT_TYPE: none
    INFRASTRUCTURE_PROVIDER: vsphere
    SERVICE_CIDR: %s
    TKG_HTTP_PROXY_ENABLED: %s
    DEPLOY_TKG_ON_VSPHERE7: "true"
    VSPHERE_DATACENTER: /%s
    VSPHERE_DATASTORE: %s
    VSPHERE_FOLDER: %s
    VSPHERE_NETWORK: %s
    VSPHERE_PASSWORD: <encoded:%s>
    VSPHERE_RESOURCE_POOL: %s
    VSPHERE_SERVER: %s
    VSPHERE_SSH_AUTHORIZED_KEY: %s

    VSPHERE_USERNAME: %s
    CONTROLPLANE_SIZE: %s
    WORKER_MACHINE_COUNT: %s
    WORKER_SIZE: %s
    VSPHERE_INSECURE: "true"
    ENABLE_AUDIT_LOGGING: "true"
    ENABLE_DEFAULT_STORAGE_CLASS: "true"
    ENABLE_AUTOSCALER: "false"
    AVI_CONTROL_PLANE_HA_PROVIDER: "true"
    OS_ARCH: amd64
    OS_NAME: %s
    OS_VERSION: %s
    """
    with open(sharedClusterName + ".yaml", 'w') as outfile:
        if env == Env.VSPHERE:
            if type == Type.SHARED:
                clustercidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceClusterCidr']
                servicecidr = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceServiceCidr']
                try:
                    osName = str(request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                                     'tkgSharedserviceBaseOs'])
                    kubeVersion = str(request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                                          'tkgSharedserviceKubeVersion'])
                except Exception as e:
                    raise Exception("Keyword " + str(e) + "  not found in input file")
            elif type == Type.WORKLOAD:
                clustercidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterCidr']
                servicecidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadServiceCidr']
                try:
                    osName = str(request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadBaseOs'])
                    kubeVersion = str(
                        request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadKubeVersion'])
                except Exception as e:
                    raise Exception("Keyword " + str(e) + "  not found in input file")
        elif env == Env.VCF:
            if type == Type.SHARED:
                clustercidr = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceClusterCidr']
                servicecidr = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceServiceCidr']
                try:
                    osName = str(request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                                     'tkgSharedserviceBaseOs'])
                    kubeVersion = str(request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                                          'tkgSharedserviceKubeVersion'])
                except Exception as e:
                    raise Exception("Keyword " + str(e) + "  not found in input file")
            elif type == Type.WORKLOAD:
                clustercidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterCidr']
                servicecidr = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadServiceCidr']
                try:
                    osName = str(request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadBaseOs'])
                    kubeVersion = str(
                        request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadKubeVersion'])
                except Exception as e:
                    raise Exception("Keyword " + str(e) + "  not found in input file")
        elif env == Env.VMC:
            if type == Type.SHARED:
                clustercidr = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceClusterCidr']
                servicecidr = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceServiceCidr']
                try:
                    osName = str(request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                                     'tkgSharedserviceBaseOs'])
                    kubeVersion = str(request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                                          'tkgSharedserviceKubeVersion'])
                except Exception as e:
                    raise Exception("Keyword " + str(e) + "  not found in input file")
            elif type == Type.WORKLOAD:
                clustercidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadClusterCidr']
                servicecidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadServiceCidr']
                try:
                    osName = str(
                        request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadBaseOs'])
                    kubeVersion = str(request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                                          'tkgWorkloadKubeVersion'])
                except Exception as e:
                    raise Exception("Keyword " + str(e) + "  not found in input file")
        if osName == "photon":
            osVersion = "3"
        elif osName == "ubuntu":
            osVersion = "20.04"
        else:
            raise Exception("Wrong os name provided")
        if type == Type.SHARED and checkSharedServiceProxyEnabled(env):
            yaml_str_proxy = """
    TKG_HTTP_PROXY: %s
    TKG_HTTPS_PROXY: %s
    TKG_NO_PROXY: %s
            """
            proxy_str = yaml_data + yaml_str_proxy
            httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['httpProxy'])
            httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['httpsProxy'])
            noProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['noProxy'])
            formatted = proxy_str % (
                clustercidr, sharedClusterName, clusterPlan, servicecidr, "true"
                ,
                datacenter,
                dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                sshKey,
                vsphereUseName, size, machineCount, size, osName, osVersion, httpProxy, httpsProxy, noProxy)
        elif type == Type.WORKLOAD and checkWorkloadProxyEnabled(env):
            yaml_str_proxy = """
    TKG_HTTP_PROXY: %s
    TKG_HTTPS_PROXY: %s
    TKG_NO_PROXY: %s
            """
            proxy_str = yaml_data + yaml_str_proxy
            httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['httpProxy'])
            httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['httpsProxy'])
            noProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['noProxy'])
            formatted = proxy_str % (
                clustercidr, sharedClusterName, clusterPlan, servicecidr, "true"
                ,
                datacenter,
                dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                sshKey,
                vsphereUseName, size, machineCount, size, osName, osVersion, httpProxy, httpsProxy, noProxy)
        elif checkAirGappedIsEnabled(env):
            yaml_str_airgapped = """
    TKG_CUSTOM_IMAGE_REPOSITORY: %s
            """
            airgapped_str = yaml_data + yaml_str_airgapped
            air_gapped_repo = str(
                request.get_json(force=True)['envSpec']['customRepositorySpec']['tkgCustomImageRepository'])
            air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
            os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
            isSelfsinged = str(request.get_json(force=True)['envSpec']['customRepositorySpec'][
                                   'tkgCustomImageRepositoryPublicCaCert'])
            if isSelfsinged.lower() == "false":
                s = """
    TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY: "False"
    TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE: %s
                """
                airgapped_str = airgapped_str + s
                url = air_gapped_repo[:air_gapped_repo.find("/")]
                getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
                with open('cert.txt', 'r') as file2:
                    repo_cert = file2.readline()
                repo_certificate = repo_cert
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
                formatted = airgapped_str % (
                    clustercidr, sharedClusterName, clusterPlan, servicecidr, "false"
                    ,
                    datacenter,
                    dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                    sshKey,
                    vsphereUseName, size, machineCount, size, osName, osVersion, air_gapped_repo, repo_certificate)
            else:
                s = """
    TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY: "False"
                """
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                airgapped_str = airgapped_str + s
                formatted = airgapped_str % (
                    clustercidr, sharedClusterName, clusterPlan, servicecidr, "false"
                    ,
                    datacenter,
                    dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                    sshKey,
                    vsphereUseName, size, machineCount, size, osName, osVersion, air_gapped_repo)
        else:
            disable_proxy()
            formatted = yaml_data % (
                clustercidr, sharedClusterName, clusterPlan, servicecidr, "false"
                ,
                datacenter,
                dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                sshKey,
                vsphereUseName, size, machineCount, size, osName, osVersion)
        data1 = ryaml.load(formatted, Loader=ryaml.RoundTripLoader)
        ryaml.dump(data1, outfile, Dumper=ryaml.RoundTripDumper, indent=2)
    return kubeVersion


def template14deployYaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                         folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                         sshKey, vsphereUseName, machineCount, size, env, type, vsSpec):
    if env == Env.VMC:
        deploy_yaml = FileHelper.read_resource(Paths.TKG_VMC_CLUSTER_14_SPEC_J2)
        ciep = str(request.get_json(force=True)["ceipParticipation"])
    else:
        deploy_yaml = FileHelper.read_resource(Paths.TKG_CLUSTER_14_SPEC_J2)
        ciep = str(request.get_json(force=True)['envSpec']["ceipParticipation"])
    t = Template(deploy_yaml)
    datacenter = "/" + datacenter
    control_plane_vcpu = ""
    control_plane_disk_gb = ""
    control_plane_mem_gb = ""
    control_plane_mem_mb = ""

    proxyCert = ""
    if env == Env.VSPHERE or Env.VCF:
        if type == Type.SHARED:
            try:
                proxyCert_raw = request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['proxyCert']
                base64_bytes = base64.b64encode(proxyCert_raw.encode("utf-8"))
                proxyCert = str(base64_bytes, "utf-8")
                isProxyCert = "true"
            except:
                isProxyCert = "false"
                current_app.logger.info("Proxy certificare for  shared is not provided")
        elif type == Type.WORKLOAD:
            try:
                proxyCert_raw = request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['proxyCert']
                base64_bytes = base64.b64encode(proxyCert_raw.encode("utf-8"))
                proxyCert = str(base64_bytes, "utf-8")
                isProxyCert = "true"
            except:
                isProxyCert = "false"
                current_app.logger.info("Proxy certificare for  workload is not provided")
    if env == Env.VSPHERE:
        if type == Type.SHARED:
            clustercidr = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceClusterCidr
            servicecidr = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceServiceCidr
            size_selection = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceSize
            if str(size_selection).lower() == "custom":
                control_plane_vcpu = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceCpuSize']
                control_plane_disk_gb = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceStorageSize']
                control_plane_mem_gb = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceMemorySize']
                control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
            try:
                osName = str(request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                                 'tkgSharedserviceBaseOs'])
                kubeVersion = str(request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                                      'tkgSharedserviceKubeVersion'])
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
        elif type == Type.WORKLOAD:
            clustercidr = vsSpec.tkgWorkloadComponents.tkgWorkloadClusterCidr
            servicecidr = vsSpec.tkgWorkloadComponents.tkgWorkloadServiceCidr
            size_selection = vsSpec.tkgWorkloadComponents.tkgWorkloadSize
            if str(size_selection).lower() == "custom":
                control_plane_vcpu = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadCpuSize']
                control_plane_disk_gb = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadStorageSize']
                control_plane_mem_gb = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadMemorySize']
                control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
            try:
                osName = str(request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadBaseOs'])
                kubeVersion = str(
                    request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadKubeVersion'])
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
    elif env == Env.VCF:
        if type == Type.SHARED:
            clustercidr = vsSpec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceClusterCidr
            servicecidr = vsSpec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceServiceCidr
            size_selection = vsSpec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceSize
            if str(size_selection).lower() == "custom":
                control_plane_vcpu = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceCpuSize']
                control_plane_disk_gb = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceStorageSize']
                control_plane_mem_gb = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceMemorySize']
                control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
            try:
                osName = str(request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                                 'tkgSharedserviceBaseOs'])
                kubeVersion = str(request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                                      'tkgSharedserviceKubeVersion'])
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
        elif type == Type.WORKLOAD:
            clustercidr = vsSpec.tkgWorkloadComponents.tkgWorkloadClusterCidr
            servicecidr = vsSpec.tkgWorkloadComponents.tkgWorkloadServiceCidr
            size_selection = vsSpec.tkgWorkloadComponents.tkgWorkloadSize
            if str(size_selection).lower() == "custom":
                control_plane_vcpu = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadCpuSize']
                control_plane_disk_gb = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadStorageSize']
                control_plane_mem_gb = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadMemorySize']
                control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
            try:
                osName = str(request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadBaseOs'])
                kubeVersion = str(
                    request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadKubeVersion'])
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
    elif env == Env.VMC:
        if type == Type.SHARED:
            clustercidr = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                'tkgSharedserviceClusterCidr']
            servicecidr = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                'tkgSharedserviceServiceCidr']
            size_selection = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                'tkgSharedserviceSize']
            if str(size_selection).lower() == "custom":
                control_plane_vcpu = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceCpuSize']
                control_plane_disk_gb = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceStorageSize']
                control_plane_mem_gb = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceMemorySize']
                control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
            try:
                osName = str(request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                                 'tkgSharedserviceBaseOs'])
                kubeVersion = str(request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                                      'tkgSharedserviceKubeVersion'])
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
        elif type == Type.WORKLOAD:
            clustercidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                'tkgWorkloadClusterCidr']
            servicecidr = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                'tkgWorkloadServiceCidr']
            size_selection = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                'tkgWorkloadSize']
            if str(size_selection).lower() == "custom":
                control_plane_vcpu = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadCpuSize']
                control_plane_disk_gb = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadStorageSize']
                control_plane_mem_gb = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadMemorySize']
                control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
            try:
                osName = str(
                    request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadBaseOs'])
                kubeVersion = str(request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                                      'tkgWorkloadKubeVersion'])
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
    if osName == "photon":
        osVersion = "3"
    elif osName == "ubuntu":
        osVersion = "20.04"
    else:
        raise Exception("Wrong os name provided")

    air_gapped_repo = ""
    repo_certificate = ""
    if checkEnableIdentityManagement(env):
        if env == Env.VSPHERE or env == Env.VCF:
            identity_mgmt_type = str(
                request.get_json(force=True)["tkgComponentSpec"]["identityManagementSpec"][
                    "identityManagementType"])
        elif env == Env.VMC:
            identity_mgmt_type = str(
                request.get_json(force=True)["componentSpec"]["identityManagementSpec"][
                    "identityManagementType"])
    else:
        identity_mgmt_type = ""
    if checkAirGappedIsEnabled(env):
        air_gapped_repo = vsSpec.envSpec.customRepositorySpec.tkgCustomImageRepository
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
        url = air_gapped_repo[:air_gapped_repo.find("/")]
        getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
        with open('cert.txt', 'r') as file2:
            repo_cert = file2.readline()
        repo_certificate = repo_cert
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
    FileHelper.write_to_file(
        t.render(config=vsSpec, clustercidr=clustercidr, sharedClusterName=sharedClusterName, clusterPlan=clusterPlan,
                 servicecidr=servicecidr, datacenter=datacenter, dataStorePath=dataStorePath,
                 folderPath=folderPath, ceip=ciep, isProxyCert=isProxyCert, proxyCert=proxyCert,
                 mgmt_network=mgmt_network, vspherePassword=vspherePassword,
                 sharedClusterResourcePool=sharedClusterResourcePool,
                 vsphereServer=vsphereServer, sshKey=sshKey, vsphereUseName=vsphereUseName, controlPlaneSize=size,
                 machineCount=machineCount, workerSize=size, type=type,
                 air_gapped_repo=air_gapped_repo, repo_certificate=repo_certificate, osName=osName,
                 osVersion=osVersion, size=size_selection, control_plane_vcpu=control_plane_vcpu,
                 control_plane_disk_gb=control_plane_disk_gb, control_plane_mem_mb=control_plane_mem_mb,
                 identity_mgmt_type=identity_mgmt_type),
        Paths.CLUSTER_PATH + sharedClusterName + "/" + sharedClusterName + ".yaml")
    return kubeVersion


def cluster13Yaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                  folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                  sshKey, vsphereUseName, machineCount, size, env, type):
    yaml_data = """\
    CLUSTER_CIDR: %s
    CLUSTER_NAME: %s
    CLUSTER_PLAN: %s
    ENABLE_CEIP_PARTICIPATION: "true"
    ENABLE_MHC: "true"
    IDENTITY_MANAGEMENT_TYPE: none
    INFRASTRUCTURE_PROVIDER: vsphere
    SERVICE_CIDR: %s
    TKG_HTTP_PROXY_ENABLED: %s
    VSPHERE_CONTROL_PLANE_ENDPOINT: %s
    DEPLOY_TKG_ON_VSPHERE7: "true"
    VSPHERE_DATACENTER: /%s
    VSPHERE_DATASTORE: %s
    VSPHERE_FOLDER: %s
    VSPHERE_NETWORK: %s
    VSPHERE_PASSWORD: <encoded:%s>
    VSPHERE_RESOURCE_POOL: %s
    VSPHERE_SERVER: %s
    VSPHERE_SSH_AUTHORIZED_KEY: %s

    VSPHERE_USERNAME: %s
    CONTROLPLANE_SIZE: %s
    WORKER_MACHINE_COUNT: %s
    WORKER_SIZE: %s
    VSPHERE_INSECURE: true
    """
    sharedClusterEndPoint = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
        'tkgSharedservice-controlplane-ip']
    with open(sharedClusterName + ".yaml", 'w') as outfile:
        if type == Type.SHARED and checkSharedServiceProxyEnabled(env):
            yaml_str_proxy = """
    TKG_HTTP_PROXY: %s
    TKG_HTTPS_PROXY: %s
    TKG_NO_PROXY: %s
            """
            proxy_str = yaml_data + yaml_str_proxy
            httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['httpProxy'])
            httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['httpsProxy'])
            noProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgSharedservice']['noProxy'])
            formatted = proxy_str % (
                CIDR.SHARED_CLUSTER_CIDR, sharedClusterName, clusterPlan, CIDR.SHARED_SERVICE_CIDR, "true",
                sharedClusterEndPoint,
                datacenter,
                dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                sshKey,
                vsphereUseName, size, machineCount, size, httpProxy, httpsProxy, noProxy)
        elif type == Type.WORKLOAD and checkWorkloadProxyEnabled(env):
            yaml_str_proxy = """
    TKG_HTTP_PROXY: %s
    TKG_HTTPS_PROXY: %s
    TKG_NO_PROXY: %s
            """
            proxy_str = yaml_data + yaml_str_proxy
            httpProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['httpProxy'])
            httpsProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['httpsProxy'])
            noProxy = str(request.get_json(force=True)['envSpec']['proxySpec']['tkgWorkload']['noProxy'])
            formatted = proxy_str % (
                CIDR.SHARED_CLUSTER_CIDR, sharedClusterName, clusterPlan, CIDR.SHARED_SERVICE_CIDR, "true",
                sharedClusterEndPoint,
                datacenter,
                dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                sshKey,
                vsphereUseName, size, machineCount, size, httpProxy, httpsProxy, noProxy)
        elif checkAirGappedIsEnabled(env):
            yaml_str_airgapped = """
    TKG_CUSTOM_IMAGE_REPOSITORY: %s
            """
            airgapped_str = yaml_data + yaml_str_airgapped
            air_gapped_repo = str(
                request.get_json(force=True)['envSpec']['customRepositorySpec']['tkgCustomImageRepository'])
            air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
            os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
            isSelfsinged = str(request.get_json(force=True)['envSpec']['customRepositorySpec'][
                                   'tkgCustomImageRepositoryPublicCaCert'])
            if isSelfsinged.lower() == "false":
                s = """
    TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY: "False"
    TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE: %s
                """
                airgapped_str = airgapped_str + s
                url = air_gapped_repo[:air_gapped_repo.find("/")]
                getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
                with open('cert.txt', 'r') as file2:
                    repo_cert = file2.readline()
                repo_certificate = repo_cert
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
                formatted = airgapped_str % (
                    CIDR.SHARED_CLUSTER_CIDR, sharedClusterName, clusterPlan, CIDR.SHARED_SERVICE_CIDR, "false",
                    sharedClusterEndPoint,
                    datacenter,
                    dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                    sshKey,
                    vsphereUseName, size, machineCount, size, air_gapped_repo, repo_certificate)
            else:
                s = """
    TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY: "False"
                """
                os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
                airgapped_str = airgapped_str + s
                formatted = airgapped_str % (
                    CIDR.SHARED_CLUSTER_CIDR, sharedClusterName, clusterPlan, CIDR.SHARED_SERVICE_CIDR, "false",
                    sharedClusterEndPoint,
                    datacenter,
                    dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                    sshKey,
                    vsphereUseName, size, machineCount, size, air_gapped_repo)
        else:
            disable_proxy()
            formatted = yaml_data % (
                CIDR.SHARED_CLUSTER_CIDR, sharedClusterName, clusterPlan, CIDR.SHARED_SERVICE_CIDR, "false",
                sharedClusterEndPoint,
                datacenter,
                dataStorePath, folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                sshKey,
                vsphereUseName, size, machineCount, size)
        data1 = ryaml.load(formatted, Loader=ryaml.RoundTripLoader)
        ryaml.dump(data1, outfile, Dumper=ryaml.RoundTripDumper, indent=2)
    return ""


def template13deployYaml(sharedClusterName, clusterPlan, datacenter, dataStorePath,
                         folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool, vsphereServer,
                         sshKey, vsphereUseName, machineCount, size, env, type, vsSpec):
    sharedClusterEndPoint = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
        'tkgSharedservice-controlplane-ip']
    deploy_yaml = FileHelper.read_resource(Paths.TKG_CLUSTER_13_SPEC_J2)
    datacenter = "/" + datacenter
    t = Template(deploy_yaml)
    air_gapped_repo = ""
    repo_certificate = ""
    if checkAirGappedIsEnabled(env):
        air_gapped_repo = vsSpec.envSpec.customRepositorySpec.tkgCustomImageRepository
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
        url = air_gapped_repo[:air_gapped_repo.find("/")]
        getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
        with open('cert.txt', 'r') as file2:
            repo_cert = file2.readline()
        repo_certificate = repo_cert
        os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
    FileHelper.write_to_file(
        t.render(config=vsSpec, sharedClusterName=sharedClusterName, clusterPlan=clusterPlan,
                 sharedClusterEndPoint=sharedClusterEndPoint,
                 datacenter=datacenter, dataStorePath=dataStorePath, folderPath=folderPath,
                 mgmt_network=mgmt_network,
                 vspherePassword=vspherePassword, sharedClusterResourcePool=sharedClusterResourcePool,
                 vsphereServer=vsphereServer,
                 sshKey=sshKey, vsphereUseName=vsphereUseName, controlPlaneSize=size,
                 machineCount=machineCount, workerSize=size,
                 air_gapped_repo=air_gapped_repo, repo_certificate=repo_certificate), sharedClusterName + ".yaml")


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


def registerTanzuObservability(cluster_name, env, size):
    try:
        if checkToEnabled(env):
            if isEnvTkgs_ns(env):
                if int(size) < 3:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Minimum required number of worker nodes to SaaS integrations is 3, "
                               "and recommended size is medium and above",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                if size.lower() == "medium" or size.lower() == "small":
                    # d = {
                    #     "responseType": "ERROR",
                    #     "msg": "Tanzu Observability integration is not supported on cluster size small or medium",
                    #     "ERROR_CODE": 500
                    # }
                    # return jsonify(d), 500
                    current_app.logger.debug("Recommended to use large/extra-large for Tanzu Observability integration")
            st = inegrateSas(cluster_name, env, SAS.TO)
            return st[0].json, st[1]
        else:
            d = {
                "responseType": "SUCCESS",
                "msg": "Tanzu observability is disabled",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to register tanzu Observability " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def registerTSM(cluster_name, env, size):
    try:
        if checTSMEnabled(env):
            if isEnvTkgs_ns(env):
                if int(size) < 3:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Minimum required number of worker nodes to SaaS integrations is 3, "
                               "and recommended size is medium and above",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                if size.lower() == "medium" or size.lower() == "small":
                    # d = {
                    #     "responseType": "ERROR",
                    #     "msg": "Tanzu service mesh integration is not supported on cluster size small or medium",
                    #     "ERROR_CODE": 500
                    # }
                    # return jsonify(d), 500
                    current_app.logger.debug("Recommended to use large/extra-large for Tanzu service mesh integration")
            st = inegrateSas(cluster_name, env, SAS.TSM)
            return st[0], st[1]
        else:
            d = {
                "responseType": "SUCCESS",
                "msg": "Tanzu Service Mesh is disabled",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to register Tanzu Service Mesh " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def inegrateSas(cluster_name, env, sasType):
    if isEnvTkgs_ns(env):
        vcenter_ip = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vcenter_username = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")
        cluster = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
        cluster_status = isClusterRunning(vcenter_ip, vcenter_username, password, cluster, cluster_name)
        if cluster_status[1] != 200:
            return cluster_status[0], cluster_status[1]
        command = ["tmc", "managementcluster", "list"]
        output = runShellCommandAndReturnOutputAsList(command)
        if output[1] != 0:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch management cluster list",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if cluster_name in output[0]:
            d = {
                "responseType": "ERROR",
                "msg": "Tanzu " + sasType + " registration is not supported on management cluster",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        context = connect_to_workload(vcenter_ip, vcenter_username, password, cluster, cluster_name)
        if context[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": context[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    else:
        context = switchToContext(cluster_name, env)
        if context[1] != 200:
            return context[0], context[1]
    li_ = returnListOfTmcCluster(cluster_name)
    if not isSasRegistred(cluster_name, li_[1], li_[2], False, sasType):
        current_app.logger.info("Registering to tanzu " + sasType)
        if not checkTmcEnabled(env):
            d = {
                "responseType": "ERROR",
                "msg": "Tmc is not enabled, tmc must be enabled to register tanzu " + sasType,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if not isEnvTkgs_ns(env):
            if not verifyCluster(cluster_name):
                d = {
                    "responseType": "ERROR",
                    "msg": cluster_name + " is not registered to Tmc, cluster  must be registered to tmc first to resgister tanzu " + sasType,
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if getManagementCluster() == cluster_name:
                d = {
                    "responseType": "ERROR",
                    "msg": "Tanzu " + sasType + " registration is not supported on management cluster",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        if checkClusterStateOnTmc(cluster_name, False) is None:
            d = {
                "responseType": "ERROR",
                "msg": "Cluster on tmc is not in healthy state " + cluster_name,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if sasType == SAS.TO:
            fileName = "to_json.json"
            if env == Env.VMC:
                toUrl = request.get_json(force=True)["saasEndpoints"]["tanzuObservabilityDetails"][
                    "tanzuObservabilityUrl"]
                toToken = request.get_json(force=True)["saasEndpoints"]["tanzuObservabilityDetails"][
                    "tanzuObservabilityRefreshToken"]
            elif env == Env.VSPHERE or env == Env.VCF:
                toUrl = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tanzuObservabilityDetails"][
                    "tanzuObservabilityUrl"]
                toToken = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tanzuObservabilityDetails"][
                    "tanzuObservabilityRefreshToken"]
            generateToJsonFile(li_[1], li_[2], cluster_name, toUrl, toToken)
        elif sasType == SAS.TSM:
            fileName = "tsm_json.json"
            if env == Env.VMC:
                exact = request.get_json(force=True)["componentSpec"]["tkgWorkloadSpec"]["namespaceExclusions"][
                    "exactName"]
                partial = request.get_json(force=True)["componentSpec"]["tkgWorkloadSpec"]["namespaceExclusions"][
                    "startsWith"]
            elif env == Env.VSPHERE or env == Env.VCF:
                if isEnvTkgs_ns(env):
                    exact = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        "tkgsVsphereWorkloadClusterSpec"]["namespaceExclusions"]["exactName"]
                    partial = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        "tkgsVsphereWorkloadClusterSpec"]["namespaceExclusions"]["startsWith"]
                else:
                    exact = request.get_json(force=True)['tkgWorkloadComponents']["namespaceExclusions"]["exactName"]
                    partial = request.get_json(force=True)['tkgWorkloadComponents']["namespaceExclusions"]["startsWith"]
            generateTSMJsonFile(li_[1], li_[2], cluster_name, exact, partial)
        command_create = ["tmc", "cluster", "integration", "create", "-f", fileName]
        state = runShellCommandAndReturnOutput(command_create)
        if sasType == SAS.TO:
            command_kube = ["kubectl", "get", "pods", "-n", "tanzu-observability-saas"]
            pods = ["wavefront"]
        elif sasType == SAS.TSM:
            command_kube = ["kubectl", "get", "pods", "-n", "vmware-system-tsm"]
            pods = ["allspark", "installer-job", "k8s-cluster-manager", "tsm-agent-operator"]
        for pod in pods:
            st = waitForProcessWithStatus(command_kube, pod, RegexPattern.RUNNING)
            if st[1] != 200:
                return st[0].json, st[1]
        count = 0
        registered = False
        while count < 180:
            if isSasRegistred(cluster_name, li_[1], li_[2], False, sasType):
                registered = True
                break
            time.sleep(10)
            count = count + 1
            current_app.logger.info("waited for " + str(count * 10) + "s for registration to complete... retrying")
        if not registered:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to register tanzu " + sasType + " to " + cluster_name,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Tanzu " + sasType + " is integrated successfully to cluster " + cluster_name,
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        d = {
            "responseType": "SUCCESS",
            "msg": "Tanzu " + sasType + " is already registered to " + cluster_name,
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def generateToJsonFile(management_cluster, provisioner_name, cluster_name, toUrl, toSecrets):
    fileName = "to_json.json"
    toJson = {
        "full_name": {
            "provisionerName": provisioner_name,
            "clusterName": cluster_name,
            "managementClusterName": management_cluster,
            "name": "tanzu-observability-saas"
        },
        "spec": {
            "configurations": {
                "url": toUrl
            },
            "secrets": {
                "token": toSecrets
            }
        }
    }
    os.system("rm -rf " + fileName)
    with open(fileName, 'w') as f:
        json.dump(toJson, f)


def generateTSMJsonFile(management_cluster, provisioner_name, cluster_name, exact, partial):
    fileName = "tsm_json.json"
    tsmJson = {
        "full_name": {
            "provisionerName": provisioner_name,
            "managementClusterName": management_cluster,
            "clusterName": cluster_name,
            "name": "tanzu-service-mesh"
        },
        "spec": {
            "configurations": ""
        }
    }
    if not (exact and partial):
        configurations = {"enableNamespaceExclusions": False}
    else:
        configurations = {"enableNamespaceExclusions": True}
        configurations.update({"namespaceExclusions": []})
        if exact:
            configurations["namespaceExclusions"].append({"match": exact, "type": "EXACT"})
        if partial:
            configurations["namespaceExclusions"].append({"match": partial, "type": "START_WITH"})
    tsmJson['spec'].update({"configurations": configurations})
    os.system("rm -rf " + fileName)
    with open(fileName, 'w') as f:
        json.dump(tsmJson, f)


def isSasRegistred(clusterName, management, provisoner, pr, sasType):
    try:
        sas = ""
        if sasType == SAS.TO:
            sas = SAS.TO
            command = ["tmc", "cluster", "integration", "get", "tanzu-observability-saas", "--cluster-name",
                       clusterName,
                       "-m",
                       management, "-p", provisoner]
        elif sasType == SAS.TSM:
            sas = SAS.TSM
            command = ["tmc", "cluster", "integration", "get", "tanzu-service-mesh", "--cluster-name", clusterName,
                       "-m", management, "-p", provisoner]
        o = runShellCommandAndReturnOutput(command)
        if str(o[0]).__contains__("NotFound"):
            current_app.logger.info("Tanzu " + sas + " is not integrated")
            return False
        else:
            if pr:
                current_app.logger.error(o[0])
                return False
        l = yaml.safe_load(o[0])
        integration = str(l["status"]["integrationWorkload"])
        if integration != "OK":
            current_app.logger.info("integrationWorkload status " + integration)
            return False
        else:
            current_app.logger.info("integrationWorkload status " + integration)
        tmcAdapter = str(l["status"]["tmcAdapter"])
        if tmcAdapter != "OK":
            current_app.logger.info("tmcAdapter status " + tmcAdapter)
            return False
        else:
            current_app.logger.info("tmcAdapter status " + tmcAdapter)
        return True
    except Exception as e:
        if pr:
            current_app.logger.error(str(e))
        return False


def checkToEnabled(env):
    try:
        to = False
        if env == Env.VMC:
            to = request.get_json(force=True)["saasEndpoints"]["tanzuObservabilityDetails"][
                "tanzuObservabilityAvailability"]
        elif env == Env.VSPHERE or env == Env.VCF:
            to = request.get_json(force=True)["envSpec"]["saasEndpoints"]["tanzuObservabilityDetails"][
                "tanzuObservabilityAvailability"]
        if str(to).lower() == "true":
            return True
        else:
            return False
    except:
        return False


def checkClusterSizeForTo(env):
    current_app.logger.info("Recommend to use Tanzu Observability and Tanzu Service Mesh integration with cluster size large or extra-large")
    isTo = checkToEnabled(env)
    isTsm = checTSMEnabled(env)
    if isTo or isTsm:
        if not checkTmcEnabled(env):
            d = {
                "responseType": "ERROR",
                "msg": "TMC is not enabled, for SaaS integration TMC must be enabled",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if env == Env.VMC:
            size = str(request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadSize'])
        elif env == Env.VSPHERE or env == Env.VCF:
            # if isEnvTkgs_ns(env):
            # size = str(request.get_json(force=True)['tkgsComponentSpec']['controlPlaneSize'])
            # else:
            size = str(request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadSize'])
        if size.lower() == "medium" or size.lower() == "small":
            if isTo:
                msg_text = "Recommend to use Tanzu Observability integration with cluster size large or extra-large"
            elif isTsm:
                msg_text = "Recommend to use Tanzu Observability integration with cluster size large or extra-large"
            d = {
                "responseType": "ERROR",
                "msg": msg_text,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Cluster size verified",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        if isTo:
            msg_text = "Tanzu Observability integration is disabled"
        elif isTsm:
            msg_text = "Tanzu Service Mesh integration is disabled"
        else:
            msg_text = "Both Tanzu Service Mesh and  Tanzu Observability integration is disabled"
        d = {
            "responseType": "SUCCESS",
            "msg": msg_text,
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def checTSMEnabled(env):
    try:
        if env == Env.VMC:
            isTsm = str(request.get_json(force=True)["componentSpec"]["tkgWorkloadSpec"][
                            "tkgWorkloadTsmIntegration"])
        elif env == Env.VSPHERE or env == Env.VCF:
            if isEnvTkgs_ns(env):
                isTsm = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    "tkgsVsphereWorkloadClusterSpec"]["tkgWorkloadTsmIntegration"]
            else:
                isTsm = str(request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadTsmIntegration'])
        if isTsm.lower() == "true":
            return True
        else:
            return False
    except Exception as e:
        return False


def checkMachineCountForTsm(env):
    if checTSMEnabled(env):
        try:
            if env == Env.VMC:
                machineCount_workload = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadWorkerMachineCount']
            elif env == Env.VSPHERE or env == Env.VCF:
                machineCount_workload = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadWorkerMachineCount']
            if int(machineCount_workload) < 3:
                d = {
                    "responseType": "ERROR",
                    "msg": "Tanzu Service Mesh integration is not supported for machine count less then 3  for workload cluster",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Not found key " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Tanzu Service Mesh cluster size verified",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        d = {
            "responseType": "SUCCESS",
            "msg": "Tanzu Service Mesh integration is disabled",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def checkMachineCountForProdType(env, isShared, isWorkload):
    try:
        if env == Env.VMC:
            if isShared:
                shared_deployment_type = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceDeploymentType']
                shared_worker_count = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceWorkerMachineCount']
            if isWorkload:
                workload_deployment_type = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadDeploymentType']
                workload_worker_count = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadWorkerMachineCount']
        elif env == Env.VSPHERE:
            if isShared:
                shared_deployment_type = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceDeploymentType']
                shared_worker_count = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                    'tkgSharedserviceWorkerMachineCount']
            if isWorkload:
                workload_deployment_type = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadDeploymentType']
                workload_worker_count = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadWorkerMachineCount']
        elif env == Env.VCF:
            if isShared:
                shared_deployment_type = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceDeploymentType']
                shared_worker_count = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                    'tkgSharedserviceWorkerMachineCount']
            if isWorkload:
                workload_deployment_type = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadDeploymentType']
                workload_worker_count = request.get_json(force=True)['tkgWorkloadComponents'][
                    'tkgWorkloadWorkerMachineCount']
        if isShared:
            if shared_deployment_type.lower() == PLAN.PROD_PLAN:
                current_app.logger.info("Verifying worker machine count for shared services cluster")
                if int(shared_worker_count) < 3:
                    current_app.logger.error(
                        "Min worker machine count for a prod deployment plan on shared services cluster is 3!")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Min worker machine count for a prod deployment plan on shared services cluster is 3!",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                current_app.logger.info("Successfully validated worker machine count for shared services cluster")
        if isWorkload:
            if workload_deployment_type.lower() == PLAN.PROD_PLAN:
                current_app.logger.info("Verifying worker machine count for workload cluster")
                if int(workload_worker_count) < 3:
                    current_app.logger.error(
                        "Min worker machine count for a prod on workload cluster deployment plan is 3!")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Min worker machine count for a prod deployment plan on workload cluster is 3!",
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
                current_app.logger.info("Successfully validated worker machine count for workload cluster")
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully validated worker machine count",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Not found key " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def generateTmcProxyYaml(name_of_proxy, httpProxy_, httpsProxy_, noProxyList_, httpUserName_, httpPassword_,
                         httpsUserName_,
                         httpsPassword_):
    if httpUserName_ and httpPassword_ and httpsUserName_ and httpsPassword_:
        os.system("rm -rf tmc_proxy.yaml")
        data = dict(
            fullName=dict(
                name=name_of_proxy,
            ),
            meta=dict(dict(annotations=dict(httpProxy=httpProxy_, httpsProxy=httpsProxy_,
                                            noProxyList=noProxyList_, proxyDescription="tmc_proxy"))),
            spec=dict(capability="PROXY_CONFIG", data=dict(
                keyValue=dict(
                    data=dict(httpPassword=httpPassword_, httpUserName=httpUserName_, httpsPassword=httpsPassword_,
                              httpsUserName=httpsUserName_)))),
            type=dict(kind="Credential", package="vmware.tanzu.manage.v1alpha1.account.credential", version="v1alpha1")
        )
    else:
        os.system("rm -rf tmc_proxy.yaml")
        data = dict(
            fullName=dict(
                name=name_of_proxy,
            ),
            meta=dict(dict(annotations=dict(httpProxy=httpProxy_, httpsProxy=httpsProxy_,
                                            noProxyList=noProxyList_, proxyDescription="tmc_proxy"))),
            spec=dict(capability="PROXY_CONFIG", data=dict(
                keyValue=dict(
                    data=dict()))),
            type=dict(kind="Credential", package="vmware.tanzu.manage.v1alpha1.account.credential", version="v1alpha1")
        )

    with open('tmc_proxy.yaml', 'w') as outfile:
        yaml1 = ryaml.YAML()
        yaml1.indent(mapping=2, sequence=4, offset=2)
        yaml1.dump(data, outfile)


def createVcfDhcpServer():
    try:
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            current_app.logger.error("Failed to nsxt info " + str(headers_[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to nsxt info " + str(headers_[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/dhcp-server-configs"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            current_app.logger.error("Failed to get DHCP info on NSXT " + str(output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get DHCP info on NSXT " + str(output[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        tier_path = getTier1Details(headers_)
        if tier_path[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
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
            current_app.logger.error(dhcp_state.text)
            return jsonify(d), dhcp_state.status_code
        dhcp_present = False
        try:
            length = len(dhcp_state.json()["dhcp_config_paths"])
            if length > 0:
                dhcp_present = True
        except:
            pass
        if not dhcp_present:
            if not checkObjectIsPresentAndReturnPath(output[0], VCF.DHCP_SERVER_NAME)[0]:
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
                    current_app.logger.error(dhcp_create.text)
                    return jsonify(d), dhcp_create.status_code
                msg_text = "Created DHCP server " + VCF.DHCP_SERVER_NAME
                current_app.logger.info(msg_text)
            else:
                msg_text = VCF.DHCP_SERVER_NAME + " dhcp server is already created"
                current_app.logger.info(msg_text)
        else:
            msg_text = "Dhcp server is already present in tier1"
        d = {
            "responseType": "SUCCESS",
            "msg": msg_text,
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Failed to create Dhcp server " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create Dhcp server " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def createNsxtSegment(segementName, gatewayAddress, dhcpStart, dhcpEnd, dnsServers, network, isDhcp):
    try:
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            current_app.logger.error("Failed to nsxt info " + str(headers_[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to nsxt info " + str(headers_[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get list of segments " + str(output[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        overlay = str(request.get_json(force=True)['envSpec']['vcenterDetails']["nsxtOverlay"])
        ntp_servers = str(request.get_json(force=True)['envSpec']['infraComponents']["ntpServers"])
        trz = getTransportZone(headers_[2], overlay, headers_[1])
        if trz[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get transport zone id " + str(trz[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        tier_path = getTier1Details(headers_)
        if tier_path[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                "ERROR_CODE": 500
            }
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
                d = {
                    "responseType": "ERROR",
                    "msg": dhcp_create.text,
                    "ERROR_CODE": dhcp_create.status_code
                }
                current_app.logger.error(dhcp_create.text)
                return jsonify(d), dhcp_create.status_code
            msg_text = "Created " + segementName
            current_app.logger.info(msg_text)
            current_app.logger.info("Waiting for 1 min for status == ready")
            time.sleep(60)
        else:
            msg_text = segementName + " is already created"
            current_app.logger.info(msg_text)
        d = {
            "responseType": "SUCCESS",
            "msg": msg_text,
            "ERROR_CODE": 200
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error("Failed to create Nsxt segment " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create Nsxt segment " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def grabNsxtHeaders():
    try:
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["nsxtUserPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")

        ecod_bytes = (request.get_json(force=True)['envSpec']['vcenterDetails']["nsxtUser"] + ":" + password).encode(
            "ascii")
        ecod_bytes = base64.b64encode(ecod_bytes)
        address = str(request.get_json(force=True)['envSpec']['vcenterDetails']["nsxtAddress"])
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


def getListOfTransportZone(address, headers_):
    try:
        url = "https://" + address + "/api/v1/transport-zones/"
        payload = {}
        tzone_response = requests.request("GET", url, headers=headers_,
                                          data=payload,
                                          verify=False)
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
            d = {
                "responseType": "ERROR",
                "msg": "Failed to nsxt info " + str(headers_[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        domainName = getDomainName(headers_, "default")
        if domainName[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get domain name " + str(domainName[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/domains/" + domainName[0] + "/groups"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get list of domain " + str(output[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if segmentName is not None:
            uri_ = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
            seg_output = getList(headers_[1], uri_)
            if seg_output[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get list of segments " + str(seg_output[0]),
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            seg_obj = checkObjectIsPresentAndReturnPath(seg_output[0], segmentName)
            if not seg_obj[0]:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to find the segment " + segmentName,
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
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
                                "ip_addresses": convertStringToCommaSeperated(ipaddresses)
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
                current_app.logger.error(dhcp_create.text)
                return jsonify(d), dhcp_create.status_code
            msg_text = "Created group " + groupName
            path = dhcp_create.json()["path"]
        else:
            path = obj[1]
            msg_text = groupName + " group is already created."
        current_app.logger.info(msg_text)
        d = {
            "responseType": "SUCCESS",
            "msg": msg_text,
            "path": path,
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create group " + groupName + " " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def getDomainName(headers, domainName):
    url = "https://" + headers[2] + "/policy/api/v1/infra/domains/"
    response = requests.request(
        "GET", url, headers=headers[1], verify=False)
    if response.status_code != 200:
        return None, response.text
    for domain in response.json()["results"]:
        if str(domain["display_name"]) == domainName:
            return domain["display_name"], "FOUND"
    return None, "NOT_FOUND"


def createVipService(serviceName, port):
    headers_ = grabNsxtHeaders()
    if headers_[0] is None:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to nsxt info " + str(headers_[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    service = isServiceCreated(headers_, serviceName)
    if service[0] is None:
        if service[1] != "NOT_FOUND":
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get service info " + str(service[1]),
                "ERROR_CODE": 500
            }
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
                        "destination_ports": convertStringToCommaSeperated(port)
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
                return jsonify(d), 500
        message = "Service created successfully"
    else:
        message = "Service is already created " + service[0]
    current_app.logger.info(message)
    d = {
        "responseType": "ERROR",
        "msg": message,
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def isServiceCreated(header, serviceName):
    url = "https://" + header[2] + "/policy/api/v1/infra/services"
    response = requests.request(
        "GET", url, headers=header[1], verify=False)
    if response.status_code != 200:
        return None, response.text
    for service in response.json()["results"]:
        if service["display_name"] == serviceName:
            return service["display_name"], "FOUND"
    return None, "NOT_FOUND"


def createFirewallRule(policyName, ruleName, rulePayLoad):
    headers_ = grabNsxtHeaders()
    if headers_[0] is None:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to nsxt info " + str(headers_[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    policy = getPolicy(headers_, policyName)
    if policy[0] is None:
        if policy[1] != "NOT_FOUND":
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get policy " + str(policy[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Creating policy " + policyName)
            tier_path = getTier1Details(headers_)
            if tier_path[0] is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                    "ERROR_CODE": 500
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
                return jsonify(d), 500
    else:
        current_app.logger.info(policyName + " policy is already created")
    list_fw = getListOfFirewallRule(headers_, policyName)
    if list_fw[0] is None:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get list of firewalls " + str(list_fw[1]),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if not checkObjectIsPresentAndReturnPath(list_fw[0], ruleName)[0]:
        current_app.logger.info("Creating firewall rule " + ruleName)
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
            return jsonify(d), 500
        msg_text = ruleName + " rule created successfully"
    else:
        msg_text = ruleName + " rule is already created"
    current_app.logger.info(msg_text)
    d = {
        "responseType": "SUCCESS",
        "msg": msg_text,
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def getListOfFirewallRule(headers, policyName):
    url = "https://" + headers[2] + "/policy/api/v1/infra/domains/default/gateway-policies/" + policyName + "/rules"
    response = requests.request(
        "GET", url, headers=headers[1], verify=False)
    if response.status_code != 200:
        return None, response.text
    return response.json()["results"], "FOUND"


def updateDefaultRule(policyName):
    try:
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to nsxt info " + str(headers_[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        list_fw = getListOfFirewallRule(headers_, policyName)
        if list_fw[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get list of firewalls " + str(list_fw[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
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
            return jsonify(d), 500
        tier_path = getTier1Details(headers_)
        if tier_path[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get Tier1 details " + str(tier_path[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
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
            "action": "DROP"
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
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully updated default rule",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to update default rule " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def getPolicy(headers, policyName):
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


def getTier1Details(headers_):
    uri = "https://" + headers_[2] + "/policy/api/v1/infra/tier-1s"
    response = requests.request(
        "GET", uri, headers=headers_[1], verify=False)
    if response.status_code != 200:
        return None, response.status_code
    teir1name = str(request.get_json(force=True)['envSpec']['vcenterDetails']["nsxtTier1RouterDisplayName"])
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
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15].encode('utf-8'))
    )[20:24])


def is_ipv4(string):
    try:
        ipaddress.IPv4Network(string)
        return True
    except ValueError:
        return False


def getIpFromHost(vcenter):
    try:
        return socket.gethostbyname(vcenter)
    except Exception as e:
        return None


def getESXIips():
    try:
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")

        ecod_bytes = (request.get_json(force=True)['envSpec']['vcenterDetails'][
                          "vcenterSsoUser"] + ":" + password).encode(
            "ascii")
        ecod_bytes = base64.b64encode(ecod_bytes)
        address = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterAddress"])
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
        baseVersionArr = Versions.vcenter.split('.')
        vcVersionArr = vcVersion.split('.')
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


def downloadAviControllerAndPushToContentLibrary(vcenter_ip, vcenter_username, password, env):
    try:
        os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
        os.putenv("GOVC_USERNAME", vcenter_username)
        os.putenv("GOVC_PASSWORD", password)
        os.putenv("GOVC_INSECURE", "true")
        if env == Env.VMC:
            res = pushAviToContenLibraryMarketPlace(env)
            if res[0] is None:
                return res[0], res[1]
        else:
            if not checkAirGappedIsEnabled(env):
                res = pushAviToContenLibraryMarketPlace(env)
                if res[0] is None:
                    return res[0], res[1]
            else:
                find_command = ["govc", "library.ls"]
                output = runShellCommandAndReturnOutputAsList(find_command)
                VC_Content_Library_name = request.get_json(force=True)['envSpec']['vcenterDetails'][
                    "contentLibraryName"]
                VC_AVI_OVA_NAME = request.get_json(force=True)['envSpec']['vcenterDetails']["aviOvaName"]
                if str(output[0]).__contains__(VC_Content_Library_name):
                    current_app.logger.info(VC_Content_Library_name + " is already present")
                else:
                    text = VC_Content_Library_name + "is not present, for internet restricted env please create " \
                                                     "content library, and import avi controller to it. "
                    current_app.logger.error(text)
                    return None, text
                find_command = ["govc", "library.ls", "/" + VC_Content_Library_name + "/"]
                output = runShellCommandAndReturnOutputAsList(find_command)
                if output[1] != 0:
                    return None, "Failed to find items in content library"
                if str(output[0]).__contains__(VC_AVI_OVA_NAME):
                    current_app.logger.info(VC_AVI_OVA_NAME + " avi controller is already present in content library")
                else:
                    current_app.logger.error(VC_AVI_OVA_NAME + " need to be present in content library for internet "
                                                               "restricted env, please push avi "
                                                               "controller to content library.")
                    return None, VC_AVI_OVA_NAME + " not present in the content library " + VC_Content_Library_name
        return "SUCCESS", 200
    except Exception as e:
        return None, str(e)


def pushAviToContenLibrary(env):
    try:
        find_command = ["govc", "library.ls", "/" + ControllerLocation.CONTROLLER_CONTENT_LIBRARY + "/"]
        output = runShellCommandAndReturnOutputAsList(find_command)
        if str(output[0]).__contains__(ControllerLocation.CONTROLLER_NAME):
            current_app.logger.info("Avi controller is already present in content library")
            return "SUCCESS", 200
    except:
        pass
    my_file = Path("/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova")
    if env == Env.VMC:
        avi_jwt_token = str(request.get_json(force=True)['resourceSpec']['aviPulseJwtToken'])
        data_store = str(request.get_json(force=True)['envSpec']['sddcDatastore'])
        data_center = str(request.get_json(force=True)['envSpec']['sddcDatacenter'])
        avi_version = Avi_Version.VMC_AVI_VERSION
    else:
        data_store = str(request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatastore'])
        data_center = str(request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter'])
        avi_jwt_token = str(
            request.get_json(force=True)['envSpec']['resourceSpec']["aviPulseJwtToken"])
        avi_version = Avi_Version.VSPHERE_AVI_VERSION
    if my_file.exists():
        current_app.logger.info("Avi ova is already downloaded")
    else:
        current_app.logger.info("Downloading avi controller.")
        get_access_token_url = "https://portal.avipulse.vmware.com/portal/controller/auth/refresh_jwt_token/"
        header = {'Content-Type': "application/json",
                  'x-portal-accesstoken': "temp"}
        body = {
            "jwt_token": avi_jwt_token
        }
        json_object = json.dumps(body, indent=4)
        response = requests.request(
            "POST", get_access_token_url, headers=header, data=json_object, verify=False)
        if response.status_code != 200:
            return None, response.text
        avi_access_token = response.json()["access_token"]
        get_release_id_url = "https://portal.avipulse.vmware.com/portal/softwares/?search_param=" + avi_version
        header = {'x-portal-accesstoken': avi_access_token}
        response = requests.request(
            "GET", get_release_id_url, headers=header, verify=False)
        if response.status_code != 200:
            return None, response.text
        id_avi = response.json()["result"]["major_version"][0]["id"]
        if id_avi is None:
            return None, "ID_NOT_FOUND"
        get_product_id_url = "https://portal.avipulse.vmware.com/portal/softwares/" + id_avi
        response = requests.request(
            "GET", get_product_id_url, headers=header, verify=False)
        if response.status_code != 200:
            return None, response.text
        list_of_product = response.json()["result"]["software_detail_list"]
        id_ = None
        found = False
        for product in list_of_product:
            if product["ecosystem_name"] == "VMware":
                for product_id in product["ecosystem_software_list"]:
                    if product_id["software_name"] == "Controller OVA":
                        id_ = product_id["software_id"]
                        found = True
                        break
            if found:
                break
        if id_ is None:
            return None, "SOFTWARE_ID_NOT_FOUND"
        get_download_url = "https://portal.avipulse.vmware.com/portal/softwares/downloads/" + id_avi + "/" + id_
        response = requests.request(
            "GET", get_download_url, headers=header, verify=False)
        if response.status_code != 200:
            return None, response.text
        download_url = response.json()["url"]
        response_csrf = requests.request("GET", download_url, verify=False, timeout=600)
        if response_csrf.status_code != 200:
            return None, response_csrf.text
        else:
            os.system("rm -rf " + "/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova")
            with open(r'/tmp/' + ControllerLocation.CONTROLLER_NAME + '.ova', 'wb') as f:
                f.write(response_csrf.content)
            current_app.logger.info(
                "Avi ova downloaded  at location " + "/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova")
    find_command = ["govc", "library.ls"]
    output = runShellCommandAndReturnOutputAsList(find_command)
    if str(output[0]).__contains__(ControllerLocation.CONTROLLER_CONTENT_LIBRARY):
        current_app.logger.info(ControllerLocation.CONTROLLER_CONTENT_LIBRARY + " is already present")
    else:
        find_command = ["govc", "library.create", "-ds=" + data_store, "-dc=" + data_center,
                        ControllerLocation.CONTROLLER_CONTENT_LIBRARY]
        output = runShellCommandAndReturnOutputAsList(find_command)
        if output[1] != 0:
            return None, "Failed to create content library"
    find_command = ["govc", "library.ls", "/" + ControllerLocation.CONTROLLER_CONTENT_LIBRARY + "/"]
    output = runShellCommandAndReturnOutputAsList(find_command)
    if output[1] != 0:
        return None, "Failed to find items in content library"
    if str(output[0]).__contains__(ControllerLocation.CONTROLLER_NAME):
        current_app.logger.info("Avi controller is already present in content library")
    else:
        current_app.logger.info("Pushing Avi controller to content library")
        import_command = ["govc", "library.import", ControllerLocation.CONTROLLER_CONTENT_LIBRARY,
                          "/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova"]
        output = runShellCommandAndReturnOutputAsList(import_command)
        if output[1] != 0:
            return None, "Failed to upload avi controller to content library"
    return "SUCCESS", 200


def verifyVcenterVersion(version):
    vCenter = current_app.config['VC_IP']
    vCenter_user = current_app.config['VC_USER']
    VC_PASSWORD = current_app.config['VC_PASSWORD']
    si = connect.SmartConnectNoSSL(host=vCenter, user=vCenter_user, pwd=VC_PASSWORD)
    content = si.RetrieveContent()
    vcVersion = content.about.version
    if vcVersion.startswith(version):
        return True
    else:
        return False


def pushAviToContenLibraryMarketPlace(env):
    try:
        find_command = ["govc", "library.ls", "/" + ControllerLocation.CONTROLLER_CONTENT_LIBRARY + "/"]
        output = runShellCommandAndReturnOutputAsList(find_command)
        if str(output[0]).__contains__(ControllerLocation.CONTROLLER_NAME):
            current_app.logger.info("Avi controller is already present in content library")
            return "SUCCESS", 200
    except:
        pass
    my_file = Path("/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova")
    if env == Env.VMC:
        data_store = str(request.get_json(force=True)['envSpec']['sddcDatastore'])
        data_center = str(request.get_json(force=True)['envSpec']['sddcDatacenter'])
        avi_version = Avi_Version.VMC_AVI_VERSION
        refToken = request.get_json(force=True)['marketplaceSpec']['refreshToken']
    else:
        data_center = str(request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter'])
        data_store = str(request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatastore'])
        refToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
        if isEnvTkgs_wcp(env) and verifyVcenterVersion(Versions.VCENTER_UPDATE_THREE):
            avi_version = Avi_Version.AVI_VERSION_UPDATE_THREE
        elif isEnvTkgs_wcp(env) and not verifyVcenterVersion(Versions.VCENTER_UPDATE_THREE):
            avi_version = Avi_Version.AVI_VERSION_UPDATE_TWO
        else:
            avi_version = Avi_Version.VSPHERE_AVI_VERSION
    # my_file = Path("/tmp/" + ControllerLocation.CONTROLLER_NAME + "-" + avi_version + ".ova")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "refreshToken": refToken
    }
    json_object = json.dumps(payload, indent=4)
    sess = requests.request("POST", MarketPlaceUrl.URL + "/api/v1/user/login", headers=headers,
                            data=json_object, verify=False)
    if sess.status_code != 200:
        return None, "Failed to login and obtain csp-auth-token"
    else:
        token = sess.json()["access_token"]
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "csp-auth-token": token
    }
    if my_file.exists():
        current_app.logger.info("Avi ova is already downloaded")
    else:
        current_app.logger.info("Downloading avi controller from MarketPlace...")
        solutionName = ControllerLocation.MARKETPLACE_AVI_SOLUTION_NAME
        # if str(MarketPlaceUrl.API_URL).__contains__("stg"):
        #    slug = "false"
        # else:
        slug = "true"
        _solutionName = getProductSlugId(MarketPlaceUrl.AVI_PRODUCT, headers)
        current_app.logger.info("Retrieved solution name from MarketPlace...")
        if _solutionName[0] is None:
            return None, "Failed to find product on Marketplace " + str(_solutionName[1])
        solutionName = _solutionName[0]
        product = requests.get(MarketPlaceUrl.API_URL + "/products/" +
                               solutionName + "?isSlug=" + slug + "&ownorg=false", headers=headers, verify=False)
        if product.status_code != 200:
            return None, "Failed to Obtain Product ID"
        else:
            ls = []
            product_id = product.json()['response']['data']['productid']
            for metalist in product.json()['response']['data']['productdeploymentfilesList']:
                if metalist["appversion"] == avi_version:
                    objectid = metalist['fileid']
                    filename = metalist['name']
                    ls.append(filename)
                    break
        payload = {
            "deploymentFileId": objectid,
            "eulaAccepted": "true",
            "productId": product_id
        }
        current_app.logger.info("Retrieved product ID from MarketPlace...")
        json_object = json.dumps(payload, indent=4).replace('\"true\"', 'true')
        presigned_url = requests.request("POST",
                                         MarketPlaceUrl.URL + "/api/v1/products/" + product_id + "/download",
                                         headers=headers, data=json_object, verify=False)
        if presigned_url.status_code != 200:
            return None, "Failed to obtain pre-signed URL"
        else:
            download_url = presigned_url.json()["response"]["presignedurl"]
        current_app.logger.info("Retrieved download URL from MarketPlace...")
        current_app.logger.info("Download will take about 5 minutes to complete...")
        current_app.logger.info("Downloaded avi controller will be saved to /tmp on SIVT VM")
        response_csfr = requests.request("GET", download_url, headers=headers, verify=False, timeout=600)
        if response_csfr.status_code != 200:
            return None, response_csfr.text
        else:
            command = ["rm", "-rf", ls[0]]
            runShellCommandAndReturnOutputAsList(command)
            with open(ls[0], 'wb') as f:
                f.write(response_csfr.content)
        command = ["mv", ls[0], "/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova"]
        runShellCommandAndReturnOutputAsList(command)
        current_app.logger.info(
            "Avi ova downloaded  at location " + "/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova")
    find_command = ["govc", "library.ls"]
    output = runShellCommandAndReturnOutputAsList(find_command)
    if str(output[0]).__contains__(ControllerLocation.CONTROLLER_CONTENT_LIBRARY):
        current_app.logger.info(ControllerLocation.CONTROLLER_CONTENT_LIBRARY + " is already present")
    else:
        find_command = ["govc", "library.create", "-ds=" + data_store, "-dc=" + data_center,
                        ControllerLocation.CONTROLLER_CONTENT_LIBRARY]
        output = runShellCommandAndReturnOutputAsList(find_command)
        if output[1] != 0:
            return None, "Failed to create content library"
    find_command = ["govc", "library.ls", "/" + ControllerLocation.CONTROLLER_CONTENT_LIBRARY + "/"]
    output = runShellCommandAndReturnOutputAsList(find_command)
    if output[1] != 0:
        return None, "Failed to find items in content library"
    if str(output[0]).__contains__(ControllerLocation.CONTROLLER_NAME):
        current_app.logger.info("Avi controller is already present in content library")
    else:
        current_app.logger.info("Pushing Avi controller to content library")
        import_command = ["govc", "library.import", ControllerLocation.CONTROLLER_CONTENT_LIBRARY,
                          "/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova"]
        output = runShellCommandAndReturnOutputAsList(import_command)
        if output[1] != 0:
            return None, "Failed to upload avi controller to content library"
    return "SUCCESS", 200


'''def downloadAndPushKubernetesOva(env):
    try:
        if checkAirGappedIsEnabled(env):
            vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
            template = KubernetesOva.PHOTON_KUBERNETES_TEMPLATE_FILE_NAME
        elif checkAnyProxyIsEnabled(env):
            vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
            template = KubernetesOva.PHOTON_KUBERNETES_TEMPLATE_FILE_NAME
        else:
            if env == Env.VMC:
                networkName = str(
                    request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName'])
                data_store = str(request.get_json(force=True)['envSpec']['sddcDatastore'])
                kube_ova = str(request.get_json(force=True)['resourceSpec']['kubernetesOva'])
                vCenter_datacenter = request.get_json(force=True)['envSpec']['sddcDatacenter']
                customer_connect_user = request.get_json(force=True)['resourceSpec']['customerConnectUser']
                customer_connect_pass = request.get_json(force=True)['resourceSpec'][
                    'customerConnectPasswordBase64']
                base64_bytes = customer_connect_pass.encode('ascii')
                enc_bytes = base64.b64decode(base64_bytes)
                customer_connect_pass = enc_bytes.decode('ascii').rstrip("\n")
            else:
                if isEnvTkgs_wcp(env):
                    networkName = str(
                        request.get_json(force=True)["tkgsComponentSpec"]["tkgsMgmtNetworkSpec"][
                            "tkgsMgmtNetworkName"])
                else:
                    networkName = str(
                        request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                            "tkgMgmtNetworkName"])
                data_store = str(request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatastore'])
                if isEnvTkgs_wcp(env):
                    kube_ova = "photon"
                else:
                    kube_ova = str(request.get_json(force=True)['envSpec']['marketplaceSpec']['kubernetes-ova'])
                vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
                vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
                customer_connect_user = request.get_json(force=True)['envSpec']['resource-spec'][
                    'customer-connect-user']
                customer_connect_pass = request.get_json(force=True)['envSpec']['resource-spec'][
                    'customer-connect-password-base64']
                base64_bytes = customer_connect_pass.encode('ascii')
                enc_bytes = base64.b64decode(base64_bytes)
                customer_connect_pass = enc_bytes.decode('ascii').rstrip("\n")
            if kube_ova == "photon":
                file = KubernetesOva.PHOTON_KUBERNETES_FILE_NAME
                template = KubernetesOva.PHOTON_KUBERNETES_TEMPLATE_FILE_NAME
            elif kube_ova == "ubuntu":
                file = KubernetesOva.UBUNTU_KUBERNETES_FILE_NAME
                template = KubernetesOva.UBUNTU_KUBERNETES__TEMPLATE_FILE_NAME
            else:
                return None, "Invalid ova type " + kube_ova
        govc_command = ["govc", "ls", "/" + vCenter_datacenter + "/vm"]
        output = runShellCommandAndReturnOutputAsList(govc_command)
        if str(output[0]).__contains__(template):
            current_app.logger.info(template + " is already present in vcenter")
            return "SUCCESS", "ALREADY_PRESENT"
        if env == Env.VMC:
            download = downloadAndPushToVC(file, template, customer_connect_user, customer_connect_pass, data_store,
                                           networkName)
            if download[0] is None:
                return None, download[1]
        else:
            if checkAirGappedIsEnabled(env) or checkAnyProxyIsEnabled(env):
                govc_command = ["govc", "ls", "/" + vCenter_datacenter + "/vm"]
                output = runShellCommandAndReturnOutputAsList(govc_command)
                if not str(output[0]).__contains__(template):
                    current_app.logger.info("For internet resticted or proxy env please upload kube ova to the vcenter")
                    return None, template + " UPLOAD_OVA_TO_VCENTER"
            else:
                download = downloadAndPushToVC(file, template, customer_connect_user, customer_connect_pass, data_store,
                                               networkName)
                if download[0] is None:
                    return None, download[1]

        return "SUCCESS", "DEPLOYED"
    except Exception as e:
        return None, str(e)'''


def downloadAndPushKubernetesOvaMarketPlace(env, version, baseOS):
    try:
        # if checkAirGappedIsEnabled(env):
        #     vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
        #     vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
        #     # template = KubernetesOva.PHOTON_KUBERNETES_TEMPLATE_FILE_NAME
        #     refToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
        # elif checkAnyProxyIsEnabled(env):
        #     vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
        #     vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
        #     # template = KubernetesOva.PHOTON_KUBERNETES_TEMPLATE_FILE_NAME
        #     refToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
        # else:
        if env == Env.VMC:
            networkName = str(
                request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtNetworkName'])
            data_store = str(request.get_json(force=True)['envSpec']['sddcDatastore'])
            # kube_ova = str(request.get_json(force=True)['resource-spec']['kubernetes-ova'])
            vCenter_datacenter = request.get_json(force=True)['envSpec']['sddcDatacenter']
            vCenter_cluster = request.get_json(force=True)['envSpec']['sddcCluster']
            refToken = request.get_json(force=True)['marketplaceSpec']['refreshToken']
        elif env == Env.VSPHERE or env == Env.VCF:
            if isEnvTkgs_wcp(env):
                networkName = str(
                    request.get_json(force=True)["tkgsComponentSpec"]["tkgsMgmtNetworkSpec"][
                        "tkgMgmtNetworkName"])
            else:
                networkName = str(
                    request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                        "tkgMgmtNetworkName"])
            data_store = str(request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatastore'])
            if isEnvTkgs_wcp(env):
                baseOS = "photon"
                version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION
            # else:
            # kube_ova = str(request.get_json(force=True)['envSpec']['marketplaceSpec']['kubernetes-ova'])
            vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
            vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
            refToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
        else:
            return None, "Invalid Env provided " + env

        if baseOS == "photon":
            file = KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + version
            template = KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + version
        elif baseOS == "ubuntu":
            file = KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + version
            template = KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + version
        else:
            return None, "Invalid ova type " + baseOS
        govc_command = ["govc", "ls", "/" + vCenter_datacenter + "/vm"]
        output = runShellCommandAndReturnOutputAsList(govc_command)
        if str(output[0]).__contains__(template):
            current_app.logger.info(template + " is already present in vcenter")
            return "SUCCESS", "ALREADY_PRESENT"

        if env == Env.VMC:
            download = downloadAndPushToVCMarketPlace(file, vCenter_datacenter, data_store, networkName,
                                                      vCenter_cluster, refToken,
                                                      version, baseOS)
            if download[0] is None:
                return None, download[1]
        else:
            if checkAirGappedIsEnabled(env):
                # govc_command = ["govc", "ls", "/" + vCenter_datacenter + "/vm"]
                # output = runShellCommandAndReturnOutputAsList(govc_command)
                # if not str(output[0]).__contains__(template):
                current_app.logger.info("For Internet Restricted Env please upload kube ova to the vcenter")
            else:
                download = downloadAndPushToVCMarketPlace(file, vCenter_datacenter, data_store, networkName,
                                                          vCenter_cluster, refToken,
                                                          version, baseOS)
                if download[0] is None:
                    return None, download[1]
        return "SUCCESS", "DEPLOYED"
    except Exception as e:
        return None, str(e)


'''def downloadAndPushToVC(file, template, customer_connect_user, customer_connect_pass, datastore, networkName):
    my_file = Path("/tmp/" + file)
    if not my_file.exists():
        current_app.logger.info("Downloading kubernetes ova.")
        os.environ["VMWUSER"] = customer_connect_user
        os.environ["VMWPASS"] = customer_connect_pass
        command = ["vmw-cli"]
        try:
            runShellCommandAndReturnOutputAsList(command)
        except:
            command_docker_pull = ["docker", "image", "load", "-i", "./common/resource/vmw.tgz"]
            output = runShellCommandAndReturnOutputAsList(command_docker_pull)
            if output[1] != 0:
                return None, "Failed to pull vmw-cli image"
            os.system("chmod 755 ./common/resource/vmw-cli")
            os.system("cp ./common/resource/vmw-cli /usr/local/bin/")
        command_download = ["vmw-cli", "ls", "vmware_tanzu_kubernetes_grid"]
        output = runShellCommandAndReturnOutputAsList(command_download)
        if output[1] != 0:
            return None, "Failed list customer connect file"
        command_download = ["vmw-cli", "cp", file]
        output = runShellCommandAndReturnOutputAsList(command_download)
        if output[1] != 0:
            return None, "Failed to download"
        os.system("mv " + file + " /tmp")
    else:
        current_app.logger.info("Kubenetes ova is already downloaded")
    replaceValueSysConfig("./common/resource/kubeova.json", "Name", "name", template)
    replaceValue("./common/resource/kubeova.json", "NetworkMapping", "Network",
                 networkName)
    current_app.logger.info("Pushing " + file + " to vcenter and making as template")
    command_template = ["govc", "import.ova", "-options", "./common/resource/kubeova.json", "-ds=" + datastore,
                        "/tmp/" + file]
    output = runShellCommandAndReturnOutputAsList(command_template)
    if output[1] != 0:
        return None, "Failed to download"
    return "SUCCESS", "DEPLOYED"'''


def downloadAndPushToVCMarketPlace(file, datacenter, datastore, networkName, clusterName, refresToken, ovaVersion,
                                   ovaOS):
    my_file = Path("/tmp/" + file + ".ova")
    if not my_file.exists():
        current_app.logger.info("Downloading kubernetes ova from MarketPlace")
        download_status = getOvaMarketPlace(file, refresToken, ovaVersion, ovaOS)
        if download_status[0] is None:
            return None, download_status[1]
        current_app.logger.info("Kubernetes ova downloaded  at location " + "/tmp/" + file)
    else:
        current_app.logger.info("Kubernetes ova is already downloaded")
    replaceValueSysConfig("./common/resource/kubeova.json", "Name", "name", file)
    replaceValue("./common/resource/kubeova.json", "NetworkMapping", "Network", networkName)
    current_app.logger.info("Pushing " + file + " to vcenter and making as template")
    command_template = ["govc", "import.ova", "-options", "./common/resource/kubeova.json", "-dc=" + datacenter,
                        "-ds=" + datastore,
                        "-pool=" + clusterName + "/Resources", "/tmp/" + file + ".ova"]
    output = runShellCommandAndReturnOutputAsList(command_template)
    if output[1] != 0:
        return None, "Failed export kubernetes ova to vCenter"
    return "SUCCESS", "DEPLOYED"


def getOvaMarketPlace(filename, refreshToken, version, baseOS):
    filename = filename + ".ova"
    solutionName = KubernetesOva.MARKETPLACE_KUBERNETES_SOLUTION_NAME
    if baseOS == "photon":
        ova_groupname = KubernetesOva.MARKETPLACE_PHOTON_GROUPNAME
    else:
        ova_groupname = KubernetesOva.MARKETPLACE_UBUTNU_GROUPNAME

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "refreshToken": refreshToken
    }
    json_object = json.dumps(payload, indent=4)
    sess = requests.request("POST", MarketPlaceUrl.URL + "/api/v1/user/login", headers=headers,
                            data=json_object, verify=False)
    if sess.status_code != 200:
        return None, "Failed to login and obtain csp-auth-token"
    else:
        token = sess.json()["access_token"]

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "csp-auth-token": token
    }

    objectid = None
    # if str(MarketPlaceUrl.API_URL).__contains__("stg"):
    # slug = "false"
    # else:
    slug = "true"

    _solutionName = getProductSlugId(MarketPlaceUrl.TANZU_PRODUCT, headers)
    if _solutionName[0] is None:
        return None, "Failed to find product on Marketplace " + str(_solutionName[1])
    solutionName = _solutionName[0]
    product = requests.get(
        MarketPlaceUrl.API_URL + "/products/" + solutionName + "?isSlug=" + slug + "&ownorg=false", headers=headers,
        verify=False)

    if product.status_code != 200:
        return None, "Failed to Obtain Product ID"
    else:
        product_id = product.json()['response']['data']['productid']
        for metalist in product.json()['response']['data']['metafilesList']:
            if metalist["version"] == version[1:] and str(metalist["groupname"]).strip("\t") == ova_groupname:
                objectid = metalist["metafileobjectsList"][0]['fileid']
                ovaName = metalist["metafileobjectsList"][0]['filename']
                app_version = metalist['appversion']
                metafileid = metalist['metafileid']

    if (objectid or ovaName or app_version or metafileid) is None:
        return None, "Failed to find the file details in Marketplace"

    current_app.logger.info("Downloading kubernetes ova - " + ovaName)

    payload = {
        "eulaAccepted": "true",
        "appVersion": app_version,
        "metafileid": metafileid,
        "metafileobjectid": objectid
    }

    json_object = json.dumps(payload, indent=4).replace('\"true\"', 'true')
    presigned_url = requests.request("POST",
                                     MarketPlaceUrl.URL + "/api/v1/products/" + product_id + "/download",
                                     headers=headers, data=json_object, verify=False)
    if presigned_url.status_code != 200:
        return None, "Failed to obtain pre-signed URL"
    else:
        download_url = presigned_url.json()["response"]["presignedurl"]

    response_csfr = requests.request("GET", download_url, headers=headers, verify=False, timeout=600)
    if response_csfr.status_code != 200:
        return None, response_csfr.text
    else:
        os.system("rm -rf " + "/tmp/" + filename)
        with open(r'/tmp/' + filename, 'wb') as f:
            f.write(response_csfr.content)

    return filename, "Kubernetes OVA download successful"


'''def isEnvTkgs(env):
    try:
        if env == Env.VSPHERE:
            tkgs = str(request.get_json(force=True)['envSpec']['envType'])
            if tkgs.lower().__contains__(EnvType.TKGS):
                return True
            else:
                return False
        else:
            return False
    except KeyError:
        return False'''


def isEnvTkgs_wcp(env):
    try:
        if env == Env.VSPHERE:
            tkgs = str(request.get_json(force=True)['envSpec']['envType'])
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
            tkgs = str(request.get_json(force=True)['envSpec']['envType'])
            if tkgs.lower() == EnvType.TKGS_NS:
                return True
            else:
                return False
        else:
            return False
    except KeyError:
        return False


def createSubscribedLibrary(vcenter_ip, vcenter_username, password, env):
    try:
        os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
        os.putenv("GOVC_USERNAME", vcenter_username)
        os.putenv("GOVC_PASSWORD", password)
        os.putenv("GOVC_INSECURE", "true")
        url = "https://wp-content.vmware.com/v2/latest/lib.json"
        if env == Env.VMC:
            data_store = str(request.get_json(force=True)['envSpec']['sddcDatastore'])
            data_center = str(request.get_json(force=True)['envSpec']['sddcDatacenter'])
        else:
            data_center = str(request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter'])
            data_store = str(request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatastore'])
        find_command = ["govc", "library.ls"]
        output = runShellCommandAndReturnOutputAsList(find_command)

        if str(output[0]).__contains__(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY):
            current_app.logger.info(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY + " is already present")
        else:
            create_command = ["govc", "library.create", "-sub=" + url, "-ds=" + data_store, "-dc=" + data_center,
                              "-sub-autosync=true", "-sub-ondemand=true",
                              ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY]
            output = runShellCommandAndReturnOutputAsList(create_command)
            if output[1] != 0:
                return None, "Failed to create content library"
            current_app.logger.info("Content library created successfully")
    except Exception as e:
        return None, "Failed"
    return "SUCCESS", "LIBRARY"


def getNetworkUrl(ip, csrf2, name, cloudName, aviVersion):
    with open("./newCloudInfo.json", 'r') as file2:
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


def getNetworkDetails(ip, csrf2, managementNetworkUrl, startIp, endIp, prefixIp, netmask, isSeRequired, aviVersion):
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
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        details["vim_ref"] = response_csrf.json()["vimgrnw_ref"]
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        return "AlreadyConfigured", 200, details
    except Exception as e:
        current_app.logger.info("Ip pools are not configured configuring it")

    os.system("rm -rf managementNetworkDetails.json")
    with open("./managementNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    if isSeRequired:
        generateVsphereConfiguredSubnetsForSe("managementNetworkDetails.json", startIp, endIp, prefixIp,
                                              int(netmask))
    else:
        generateVsphereConfiguredSubnets("managementNetworkDetails.json", startIp, endIp, prefixIp,
                                         int(netmask))
    return "SUCCESS", 200, details


def getDetailsOfNewCloud(ip, csrf2, newCloudUrl, vim_ref, captured_ip, captured_mask, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
                current_app.logger.info("waited for " + str(count * 60) + "s sync to complete")
                count = count + 1
        else:
            return 500, response_csrf.text, details
    details["subnet_ip"] = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
    details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
    details["vimref"] = response_csrf.json()["vimgrnw_ref"]
    return 200, "SUCCESS", details


def updateNewCloud(ip, csrf2, newCloudUrl, aviVersion):
    with open("./detailsOfNewCloud.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    json_object = json.dumps(new_cloud_json, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    response_csrf = requests.request("PUT", newCloudUrl, headers=headers, data=json_object, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        return response_csrf.json(), "SUCCESS"


def getDetailsOfNewCloudAddIpam(ip, csrf2, newCloudUrl, ipamUrl, aviVersion):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
        with open("detailsOfNewCloudIpam.json", 'w') as f:
            json.dump(data, f)
        return response_csrf.json(), "SUCCESS"


def updateNewCloud(ip, csrf2, newCloudUrl, aviVersion):
    with open("./detailsOfNewCloud.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    json_object = json.dumps(new_cloud_json, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
        "x-csrftoken": csrf2[0]
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
        "x-csrftoken": csrf2[0]
    }
    body = {}
    url = "https://" + ip + "/api/ipamdnsproviderprofile"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        for re in response_csrf.json()["results"]:
            if re['name'] == name:
                return re["url"], "SUCCESS"
    return "NOT_FOUND", "SUCCESS"


def getStoragePolicies(vCenter, vCenter_user, VC_PASSWORD):
    url = "https://" + vCenter + "/"
    try:
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
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
        storage_policies = requests.request("GET", url + "api/vcenter/storage/policies", headers=header, verify=False)
        if storage_policies.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch storage policies",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        return storage_policies.json(), 200

    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching storage policies",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def getPolicyID(policyname, vcenter, vc_user, vc_password):
    try:
        policies = getStoragePolicies(vcenter, vc_user, vc_password)
        for policy in policies[0]:
            if policy["name"] == policyname:
                return policy['policy'], 200
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
    from ipaddress import ip_network, ip_interface

    list1 = list(ip_network(gatewayCidr, False).hosts())
    count = 0
    for l in list1:
        if ip_interface(l) > ip_interface(end):
            break
        if ip_interface(l) >= ip_interface(start):
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
    with open("./detailsOfNewCloudIpam.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    json_object = json.dumps(new_cloud_json, indent=4)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
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
        "x-csrftoken": csrf2[0]
    }
    body = {}
    url = "https://" + ip + "/api/sslkeyandcertificate"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        current_app.logger.error("Failed to get certificate " + response_csrf.text)
        return None, response_csrf.text
    else:
        for re in response_csrf.json()["results"]:
            if re['name'] == certName:
                return re["certificate"]["certificate"], "SUCCESS"
    return "NOT_FOUND", "FAILED"


def checkAndWaitForAllTheServiceEngineIsUp(ip, clodName, env, aviVersion):
    csrf2 = obtain_second_csrf(ip, env)
    if csrf2 is None:
        current_app.logger.error("Failed to get csrf from new set password")
        return None, "Failed to get csrf from new set password"
    with open("./newCloudInfo.json", 'r') as file2:
        new_cloud_json = json.load(file2)
    uuid = None
    try:
        uuid = new_cloud_json["uuid"]
    except:
        for re in new_cloud_json["results"]:
            if re["name"] == clodName:
                uuid = re["uuid"]
    if uuid is None:
        return None, "Failed", "ERROR"
    url = "https://" + ip + "/api/serviceengine-inventory/?cloud_ref.uuid=" + str(uuid)
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
    seCount = 0
    response_csrf = None
    current_app.logger.info("Checking all service are up or not.")
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
        except:
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
        current_app.logger.info("All service are up and running")
        return "SUCCESS", "CHECKED", "UP"


def validatePem(pemcert):
    try:
        root_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pemcert)
        store = OpenSSL.crypto.X509Store()
        store.add_cert(root_cert)
        store_ctx = OpenSSL.crypto.X509StoreContext(store, root_cert)
        validity = store_ctx.verify_certificate()
        if validity is None or True:
            return True
    except Exception as e:
        current_app.logger.error(e)
        return False


def configureKubectl(clusterIp):
    os.system("mkdir tempDir")
    url = "https://" + clusterIp + "/wcp/plugin/linux-amd64/vsphere-plugin.zip"
    response = requests.get(url, verify=False)
    if response.status_code != 200:
        current_app.logger.error("vsphere-plugin.zip download failed")
        return None, response.text
    with open(r'/tmp/vsphere-plugin.zip', 'wb') as f:
        f.write(response.content)
    create_command = ["unzip", "/tmp/vsphere-plugin.zip", "-d", "tempDir"]
    output = runShellCommandAndReturnOutputAsList(create_command)
    if output[1] != 0:
        return None, "Failed to unzip vsphere-plugin.zip"
    os.system("mv -f /opt/vmware/arcas/src/tempDir/bin/* /usr/local/bin/")
    os.system("chmod +x /usr/local/bin/kubectl-vsphere")
    return "SUCCESS", 200


def deleteConfigServer(cluster_endpoint):
    list_config = ["tanzu", "config", "server", "list"]
    list_output = runShellCommandAndReturnOutputAsList(list_config)
    if list_output[1] != 0:
        return " Failed to use  context " + str(list_output[0]), 500

    if str(list_output[0]).__contains__(cluster_endpoint):
        delete_config = ["tanzu", "config", "server", "delete", cluster_endpoint, "-y"]
        delete_output = runShellCommandAndReturnOutputAsList(delete_config)
        if delete_output[1] != 0:
            return " Failed to use  context " + str(delete_output[0]), 500
        return "Cluster config deleted successfully", 200
    else:
        return "Cluster config not added", 200


def supervisorTMC(vcenter_user, VC_PASSWORD, cluster_ip):
    command = ["tanzu", "config", "server", "list"]
    server_list = runShellCommandAndReturnOutputAsList(command)
    if server_list[1] != 0:
        return " Failed to get list of logins " + str(server_list[0]), 500
    if str(server_list[0]).__contains__(cluster_ip):
        delete_response = deleteConfigServer(cluster_ip)
        if delete_response[1] != 200:
            current_app.logger.info("Server config delete failed")
            return "Server config delete failed", 500
    current_app.logger.info("Logging in to cluster " + cluster_ip)
    os.putenv("KUBECTL_VSPHERE_PASSWORD", VC_PASSWORD)
    connect_command = ["kubectl", "vsphere", "login", "--server=" + cluster_ip, "--vsphere-username=" + vcenter_user,
                       "--insecure-skip-tls-verify"]
    output = runShellCommandAndReturnOutputAsList(connect_command)
    if output[1] != 0:
        return " Failed while connecting to Supervisor Cluster", 500
    switch_context = ["kubectl", "config", "use-context", cluster_ip]
    output = runShellCommandAndReturnOutputAsList(switch_context)
    if output[1] != 0:
        return " Failed to use  context " + str(output[0]), 500

    switch_context = ["tanzu", "login", "--name", cluster_ip, "--kubeconfig", "/root/.kube/config", "--context",
                      cluster_ip]
    output = runShellCommandAndReturnOutputAsList(switch_context)
    if output[1] != 0:
        return " Failed to switch context to Supervisor Cluster " + str(output[0]), 500
    return "SUCCESS", 200


def registerTMCTKGs(vCenter, vCenter_user, VC_PASSWORD):
    url = "https://" + vCenter + "/"
    try:
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            session_id = sess.json()['value']

        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": session_id
        }
        cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
        id = getClusterID(vCenter, vCenter_user, VC_PASSWORD, cluster_name)
        if id[1] != 200:
            return None, id[0]
        clusterip_resp = requests.get(url + "api/vcenter/namespace-management/clusters/" + str(id[0]), verify=False,
                                      headers=header)
        if clusterip_resp.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch API server cluster endpoint - " + vCenter,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]

        configure_kubectl = configureKubectl(cluster_endpoint)
        if configure_kubectl[1] != 200:
            return configure_kubectl[0], 500

        supervisor_tmc = supervisorTMC(vCenter_user, VC_PASSWORD, cluster_endpoint)
        if supervisor_tmc[1] != 200:
            return supervisor_tmc[0], 500
        supervisor_cluster = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
            'tmcSupervisorClusterName']
        if checkTmcRegister(supervisor_cluster, True):
            current_app.logger.info(supervisor_cluster + " is already registered")
        else:
            clusterGroup = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                'tmcSupervisorClusterGroupName']
            if not clusterGroup:
                clusterGroup = "default"
            os.putenv("TMC_API_TOKEN",
                      request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails']['tmcRefreshToken'])
            listOfCmdTmcLogin = ["tmc", "login", "--no-configure", "-name", "tkgvsphere-automation"]
            runProcess(listOfCmdTmcLogin)
            listOfCommandRegister = ["tmc", "managementcluster", "register", supervisor_cluster, "-c", clusterGroup,
                                     "-p",
                                     "TKGS"]
            generateYaml = runShellCommandAndReturnOutput(listOfCommandRegister)
            if generateYaml[1] != 0:
                return " Failed to register Supervisor Cluster " + str(generateYaml[0]), 500
            main_command = ["kubectl", "get", "ns"]
            sub_command = ["grep", "svc-tmc"]
            command_cert = grabPipeOutput(main_command, sub_command)
            if command_cert[1] != 0:
                return "Failed to get namespace details", 500
            namespace = command_cert[0].split("\\s")[0].strip()
            os.system("chmod +x ./common/injectValue.sh")
            os.system("./common/injectValue.sh " + "k8s-register-manifest.yaml" + " inject_namespace " + namespace)
            command = ["kubectl", "apply", "-f", "k8s-register-manifest.yaml"]
            state = runShellCommandAndReturnOutputAsList(command)
            if state[1] != 0:
                return "Failed to apply k8s-register-manifest.yaml file", 500

            current_app.logger.info("Waiting for TMC registration to complete... ")
            time.sleep(300)
            wait_status = waitForTMCRegistration(supervisor_cluster)
            if wait_status[1] != 200:
                current_app.logger.error(wait_status[0])
                return wait_status[0], 500
        return "TMC Register Successful", 200

    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Register Supervisor Cluster to TMC",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def waitForTMCRegistration(super_cls):
    registered = False
    count = 0
    register_status_command = ["tmc", "managementcluster", "get", super_cls]
    register_status = runShellCommandAndReturnOutput(register_status_command)
    if register_status[1] != 0:
        return "Failed to obtain register status for TMC", 500
    else:
        yaml_ouptput = yaml.load(register_status[0], Loader=SafeLoader)
        if yaml_ouptput["status"]["health"] == "HEALTHY" and \
                yaml_ouptput["status"]["conditions"]["READY"]["status"].lower() == "true":
            registered = True

    while not registered and count < 30:
        register_status_command = ["tmc", "managementcluster", "get", super_cls]
        register_status = runShellCommandAndReturnOutput(register_status_command)
        if register_status[1] != 0:
            return "Failed to obtain register status for TMC", 500
        else:
            yaml_ouptput = yaml.load(register_status[0], Loader=SafeLoader)
            if yaml_ouptput["status"]["health"] == "HEALTHY" and \
                    yaml_ouptput["status"]["conditions"]["READY"]["status"].lower() == "true":
                registered = True
                break
            else:
                current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")
                count = count + 1
                time.sleep(30)
    if not registered:
        current_app.logger.error("TMC registration still did not complete " + str(count * 30))
        d = {
            "responseType": "ERROR",
            "msg": "TMC registration still did not complete " + str(count * 30),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    else:
        return "TMC Registration successful", 200


def get_alias_name(storage_id):
    command = ["kubectl", "describe", "sc"]
    policy_list = runShellCommandAndReturnOutput(command)
    if policy_list[1] != 0:
        return None, "Failed to get list of policies " + str(policy_list[0]), 500
    ss = str(policy_list[0]).split("\n")
    for s in range(len(ss)):
        if ss[s].__contains__("storagePolicyID=" + storage_id):
            alias = ss[s - 4].replace("Name:", "").strip()
            current_app.logger.info("Alias name " + alias)
            return alias, "SUCCESS"
    return None, "NOT_FOUND"


'''def getClusterId(vc_session, clusterName, vcenter_ip):
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
        return None, str(e)'''


def getClusterID(vCenter, vCenter_user, VC_PASSWORD, cluster):
    url = "https://" + vCenter + "/"
    try:
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            session_id = sess.json()['value']

        vcenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
        if str(vcenter_datacenter).__contains__("/"):
            vcenter_datacenter = vcenter_datacenter[vcenter_datacenter.rindex("/") + 1:]
        if str(cluster).__contains__("/"):
            cluster = cluster[cluster.rindex("/") + 1:]
        datcenter_resp = requests.get(url + "api/vcenter/datacenter?names=" + vcenter_datacenter, verify=False,
                                      headers={"vmware-api-session-id": session_id})
        if datcenter_resp.status_code != 200:
            current_app.logger.error(datcenter_resp.json())
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch datacenter ID for datacenter - " + vcenter_datacenter,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        datacenter_id = datcenter_resp.json()[0]['datacenter']

        clusterID_resp = requests.get(url + "api/vcenter/cluster?names=" + cluster + "&datacenters=" + datacenter_id,
                                      verify=False, headers={"vmware-api-session-id": session_id})
        if clusterID_resp.status_code != 200:
            current_app.logger.error(clusterID_resp.json())
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch cluster ID for cluster - " + cluster,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        return clusterID_resp.json()[0]['cluster'], 200

    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to fetch cluster ID for cluster - " + cluster,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def downloadAviController(env):
    if env == Env.VSPHERE or env == Env.VCF:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterAddress"]
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoUser"]
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
        refreshToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
    elif env == Env.VMC:
        vCenter = current_app.config['VC_IP']
        vCenter_user = current_app.config['VC_USER']
        VC_PASSWORD = current_app.config['VC_PASSWORD']
        refreshToken = request.get_json(force=True)['marketplaceSpec']['refreshToken']
    os.putenv("GOVC_URL", "https://" + vCenter + "/sdk")
    os.putenv("GOVC_USERNAME", vCenter_user)
    os.putenv("GOVC_PASSWORD", VC_PASSWORD)
    os.putenv("GOVC_INSECURE", "true")

    if not refreshToken:
        current_app.logger.info("refreshToken not provided")
    else:
        down = downloadAviControllerAndPushToContentLibrary(vCenter, vCenter_user, VC_PASSWORD, env)
        if down[0] is None:
            current_app.logger.error(down[1])
            d = {
                "responseType": "ERROR",
                "msg": down[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Avi controller download successful",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


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
        product = requests.get(
            MarketPlaceUrl.PRODUCT_SEARCH_URL, headers=headers,
            verify=False)
        if product.status_code != 200:
            return None, "Failed to search  product " + productName + " on Marketplace."
        for pro in product.json()["response"]["dataList"]:
            if str(pro["displayname"]) == productName:
                return str(pro["slug"]), "SUCCESS"
    except Exception as e:
        return None, str(e)


def isAviHaEnabled(env):
    try:
        if env == Env.VMC:
            enable_avi_ha = request.get_json(force=True)['componentSpec']['aviComponentSpec']['enableAviHa']
        elif isEnvTkgs_wcp(env):
            enable_avi_ha = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['enableAviHa']
        else:
            enable_avi_ha = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['enableAviHa']
        if str(enable_avi_ha).lower() == "true":
            return True
        else:
            return False
    except:
        return False


def checkOSFlavorForTMC(env, isShared, isWorkload):
    if env == Env.VMC:
        mgmt_os = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtBaseOs']
        if isShared:
            shared_os = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec']['tkgSharedserviceBaseOs']
        if isWorkload:
            wrkl_os = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadBaseOs']
    elif env == Env.VSPHERE:
        mgmt_os = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtBaseOs']
        if isShared:
            shared_os = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceBaseOs']
        if isWorkload:
            wrkl_os = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadBaseOs']
    elif env == Env.VCF:
        mgmt_os = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtBaseOs']
        if isShared:
            shared_os = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceBaseOs']
        if isWorkload:
            wrkl_os = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadBaseOs']
    else:
        d = {
            "responseType": "ERROR",
            "msg": "Invalid env provided",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    if (mgmt_os.lower() == 'photon') and (not isShared or shared_os.lower() == 'photon') and (
            not isWorkload or wrkl_os.lower() == 'photon'):
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully validated Kubernetes OVA images are photon",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        d = {
            "responseType": "ERROR",
            "msg": "Only photon images are supported with TMC",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def getNetworkPathTMC(networkName, vcenter_ip, vcenter_username, password):
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    find_command = ["govc", "find", "-name", networkName]
    count = 0
    net = ""
    while count < 120:
        output = runShellCommandAndReturnOutputAsList(find_command)
        if str(output[0]).__contains__(networkName) and str(output[0]).__contains__("/network"):
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


def getKubeVersionFullName(kube_version):
    try:
        listOfCmd = ["kubectl", "get", "tkr"]
        kube_version_full = runShellCommandAndReturnOutputAsList(listOfCmd)
        lu = []
        for version in kube_version_full[0]:
            if str(version).__contains__(kube_version) and str(version).__contains__("True"):
                list_ = version.split(" ")
                for l in list_:
                    if l:
                        lu.append(l)
                current_app.logger.info(lu)
                return lu[1], 200
        return None, 500
    except:
        return None, 500


def getKubeVersionFullNameNoCompatibilityCheck(kube_version):
    try:
        listOfCmd = ["kubectl", "get", "tkr"]
        kube_version_full = runShellCommandAndReturnOutputAsList(listOfCmd)
        lu = []
        for version in kube_version_full[0]:
            if str(version).__contains__(kube_version):
                list_ = version.split(" ")
                for l in list_:
                    if l:
                        lu.append(l)
                current_app.logger.info(lu)
                return lu[1], 200
        return None, 500
    except:
        return None, 500


def connect_to_workload(vCenter, vcenter_username, password, cluster, workload_name):
    try:
        current_app.logger.info("Connecting to workload cluster...")
        cluster_id = getClusterID(vCenter, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[0])
            return None, cluster_id[0].json['msg']

        cluster_namespace = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
        cluster_id = cluster_id[0]
        wcp_status = isWcpEnabled(cluster_id)
        if wcp_status[0]:
            endpoint_ip = wcp_status[1]['api_server_cluster_endpoint']
        else:
            return None, "Failed to obtain cluster endpoint IP on given cluster - " + workload_name
        current_app.logger.info("logging into cluster - " + endpoint_ip)
        os.putenv("KUBECTL_VSPHERE_PASSWORD", password)
        connect_command = ["kubectl", "vsphere", "login", "--vsphere-username", vcenter_username, "--server",
                           endpoint_ip,
                           "--tanzu-kubernetes-cluster-name", workload_name, "--tanzu-kubernetes-cluster-namespace",
                           cluster_namespace, "--insecure-skip-tls-verify"]
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
    except Exception as e:
        return None, "Exception occurred while connecting to workload cluster"


def isWcpEnabled(cluster_id):
    vcenter_ip = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
    vcenter_username = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
    str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
    base64_bytes = str_enc.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password = enc_bytes.decode('ascii').rstrip("\n")
    if not (vcenter_ip or vcenter_username or password):
        return False, "Failed to fetch VC details"

    sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                         auth=(vcenter_username, password), verify=False)
    if sess.status_code != 200:
        current_app.logger.error("Connection to vCenter failed")
        return False, "Connection to vCenter failed"
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


def isClusterRunning(vcenter_ip, vcenter_username, password, cluster, workload_name):
    try:
        current_app.logger.info("Check if cluster is in running state - " + workload_name)

        cluster_id = getClusterID(vcenter_ip, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[0])
            d = {
                "responseType": "ERROR",
                "msg": cluster_id[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        cluster_id = cluster_id[0]

        wcp_status = isWcpEnabled(cluster_id)
        if wcp_status[0]:
            endpoint_ip = wcp_status[1]['api_server_cluster_endpoint']
        else:
            current_app.logger.error("WCP not enabled on given cluster - " + cluster)
            d = {
                "responseType": "ERROR",
                "msg": "WCP not enabled on given cluster - " + cluster,
                "ERROR_CODE": 500
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
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        switch_context = ["kubectl", "config", "use-context", endpoint_ip]
        output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            current_app.logger.error("Failed to use  context " + str(output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to use  context " + str(output[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        name_space = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
        get_cluster_command = ["kubectl", "get", "tkc", "-n", name_space]
        clusters_output = runShellCommandAndReturnOutputAsList(get_cluster_command)
        if clusters_output[1] != 0:
            current_app.logger.error("Failed to fetch cluster running status " + str(clusters_output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch cluster running status " + str(clusters_output[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        index = None
        for item in range(len(clusters_output[0])):
            if clusters_output[0][item].split()[0] == workload_name:
                index = item
                break

        if index is None:
            current_app.logger.error("Unable to find cluster - " + workload_name)
            d = {
                "responseType": "ERROR",
                "msg": "Unable to find cluster - " + workload_name,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        output = clusters_output[0][index].split()
        if not ((output[5] == "True" or output[5] == "running") and output[6] == "True"):
            current_app.logger.error("Failed to fetch workload cluster running status " + str(clusters_output[0]))
            current_app.logger.error("Found below Cluster status - ")
            current_app.logger.error("READY: " + str(output[5]) + " and TKR COMPATIBLE: " + str(output[6]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch workload cluster running status " + str(clusters_output[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "Workload cluster is in running status.",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching the status of workload cluster",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def getAviIpFqdnDnsMapping(avi_controller_fqdn_ip_dict, dns_server):
    try:
        for dns in dns_server:
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
    except:
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
            vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
            vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
            name_space = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereNamespaceName']

            if not (vCenter or vCenter_user or VC_PASSWORD):
                current_app.logger.error('Failed to fetch VC details')
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to find VC details",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
        else:
            current_app.logger.error("Wrong environment provided to fetch namespace details")
            d = {
                "responseType": "ERROR",
                "msg": "Wrong environment provided to fetch namespace details",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        url = "https://" + vCenter + "/"
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
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
        namespace_response = requests.request("GET", url + "api/vcenter/namespaces/instances/" + name_space,
                                              headers=header, verify=False)
        if namespace_response.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch details for namespace - " + name_space,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        storage_policies = []
        if namespace_response.json()["config_status"] != "RUNNING":
            current_app.logger.error("Selected namespace is not in running state - " + name_space)
            d = {
                "responseType": "ERROR",
                "msg": "Selected namespace is not in running state - " + name_space,
                "ERROR_CODE": 500
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
            current_app.logger.error("Policy names list found empty for give namesapce - " + name_space)
            d = {
                "responseType": "ERROR",
                "msg": "Policy names list found empty for give namesapce - " + name_space,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        if not vm_classes:
            current_app.logger.error("VM Classes list found empty for give namespace - " + name_space)
            d = {
                "responseType": "ERROR",
                "msg": "VM Classes list found empty for give namespace - " + name_space,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("Found namespace details successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Found namespace details successfully - " + name_space,
            "ERROR_CODE": 200,
            "VM_CLASSES": vm_classes,
            "STORAGE_POLICIES": policy_names
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fteching details for namespace - " + name_space,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def fluent_bit_enabled(env):
    if isEnvTkgs_ns(env) or env == Env.VSPHERE or env == Env.VMC:
        if check_fluent_bit_splunk_endpoint_endpoint_enabled():
            return True, Tkg_Extention_names.FLUENT_BIT_SPLUNK
        elif check_fluent_bit_http_endpoint_enabled():
            return True, Tkg_Extention_names.FLUENT_BIT_HTTP
        elif check_fluent_bit_syslog_endpoint_enabled():
            return True, Tkg_Extention_names.FLUENT_BIT_SYSLOG
        elif check_fluent_bit_elastic_search_endpoint_enabled():
            return True, Tkg_Extention_names.FLUENT_BIT_ELASTIC
        elif check_fluent_bit_kafka_endpoint_endpoint_enabled():
            return True, Tkg_Extention_names.FLUENT_BIT_KAFKA
        else:
            return False, None
    else:
        current_app.logger.error("Wrong env type provided for Fluent bit installation")
        return False, None


def deploy_fluent_bit(end_point, cluster):
    try:
        current_app.logger.info("Deploying Fluent-bit extension on cluster - " + cluster)
        if not createClusterFolder(cluster):
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + cluster,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        copy_template_command = ["cp", Paths.VSPHERE_FLUENT_BIT_YAML, Paths.CLUSTER_PATH + cluster]
        copy_output = runShellCommandAndReturnOutputAsList(copy_template_command)
        if copy_output[1] != 0:
            current_app.logger.error("Failed to copy template file to : " + Paths.CLUSTER_PATH + cluster)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to copy template file to : " + Paths.CLUSTER_PATH + cluster,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        yamlFile = Paths.CLUSTER_PATH + cluster + "/fluent_bit_data_values.yaml"
        namespace = "package-tanzu-system-logging"
        update_response = updateDataFile(end_point, yamlFile)
        if not update_response:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update data values file",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        version = getVersionOfPackage(Tkg_Extention_names.FLUENT_BIT.lower() + ".tanzu.vmware.com")
        if version is None:
            current_app.logger.error("Failed Capture the available Prometheus version")
            d = {
                "responseType": "ERROR",
                "msg": "Capture the available Prometheus version",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        deploy_fluent_bit_command = ["tanzu", "package", "install", Tkg_Extention_names.FLUENT_BIT.lower(),
                                     "--package-name", Tkg_Extention_names.FLUENT_BIT.lower() + ".tanzu.vmware.com",
                                     "--version", version, "--values-file", yamlFile, "--namespace", namespace,
                                     "--create-namespace"]
        state_extention_apply = runShellCommandAndReturnOutputAsList(deploy_fluent_bit_command)
        if state_extention_apply[1] != 0:
            current_app.logger.error(Tkg_Extention_names.FLUENT_BIT.lower() + " install command failed. "
                                                                              "Checking for reconciliation status...")

        extention_validate_command = ["kubectl", "get", "app", Tkg_Extention_names.FLUENT_BIT.lower(), "-n", namespace]

        found = False
        count = 0
        command_ext_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
        if verifyPodsAreRunning(Tkg_Extention_names.FLUENT_BIT.lower(), command_ext_bit[0],
                                RegexPattern.RECONCILE_SUCCEEDED):
            found = True

        while not found and count < 20:
            command_ext_bit = runShellCommandAndReturnOutputAsList(extention_validate_command)
            if verifyPodsAreRunning(Tkg_Extention_names.FLUENT_BIT.lower(), command_ext_bit[0],
                                    RegexPattern.RECONCILE_SUCCEEDED):
                found = True
                break
            count = count + 1
            time.sleep(30)
            current_app.logger.info("Waited for  " + str(count * 30) + "s, retrying.")

        if found:
            d = {
                "responseType": "SUCCESS",
                "msg": "Fluent-bit installation completed successfully",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        else:
            current_app.logger.error("Fluent-bit deployment is not completed even after " + str(count * 30) + "s wait")
            d = {
                "responseType": "ERROR",
                "msg": "Fluent-bit installation failed",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    except Exception as e:
        current_app.logger.error("Exception occurred while deploying fluent-bit - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while deploying fluent-bit - " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def checkFluentBitInstalled():
    extension = Tkg_Extention_names.FLUENT_BIT.lower()
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
        if fluent_endpoint == Tkg_Extention_names.FLUENT_BIT_HTTP:
            host = request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointAddress']
            port = request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort']
            uri = request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri']
            header = request.get_json(force=True)['tanzuExtensions']['logging']['httpEndpoint'][
                'httpEndpointHeaderKeyValue']
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
            """ % (host, port, uri, header)
        elif fluent_endpoint == Tkg_Extention_names.FLUENT_BIT_SYSLOG:
            host = request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointAddress']
            port = request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointPort']
            mode = request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointMode']
            format = request.get_json(force=True)['tanzuExtensions']['logging']['syslogEndpoint'][
                'syslogEndpointFormat']
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
            """ % (host, port, mode, format)
        elif fluent_endpoint == Tkg_Extention_names.FLUENT_BIT_KAFKA:
            broker = request.get_json(force=True)['tanzuExtensions']['logging']['kafkaEndpoint'][
                'kafkaBrokerServiceName']
            topic = request.get_json(force=True)['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName']
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
            """ % (broker, topic)
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
    except Exception as e:
        current_app.logger.error("Exception occurred while creating directory - " + Paths.CLUSTER_PATH + clusterName)
        return False


def validate_backup_location(env, clusterType):
    try:
        if isEnvTkgs_ns(env) and clusterType.lower() == "shared":
            return False, "Invalid inputs provided for validation of data backup location"
        if env == Env.VMC:
            if clusterType.lower() == "shared":
                backup_location = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedClusterBackupLocation']
                cluster_group = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedserviceClusterGroupName']
            elif clusterType.lower() == "workload":
                backup_location = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadClusterBackupLocation']
                cluster_group = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadClusterGroupName']
            else:
                return False, "Invalid cluster type provided"
        else:
            if clusterType.lower() == "shared":
                if not isEnvTkgs_ns(env) and not isEnvTkgs_wcp(env):
                    if env == Env.VCF:
                        backup_location = request.get_json(force=True)['tkgComponentSpec']["tkgSharedserviceSpec"][
                            'tkgSharedClusterBackupLocation']
                        cluster_group = request.get_json(force=True)['tkgComponentSpec']["tkgSharedserviceSpec"][
                            'tkgSharedserviceClusterGroupName']
                    else:
                        backup_location = request.get_json(force=True)['tkgComponentSpec']["tkgMgmtComponents"][
                            "tkgSharedClusterBackupLocation"]
                        cluster_group = request.get_json(force=True)['tkgComponentSpec']["tkgMgmtComponents"][
                            'tkgSharedserviceClusterGroupName']
            elif clusterType.lower() == "workload":
                if isEnvTkgs_ns(env):
                    backup_location = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        'tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterBackupLocation']
                    cluster_group = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        "tkgsVsphereWorkloadClusterSpec"]["tkgsWorkloadClusterGroupName"]
                else:
                    backup_location = request.get_json(force=True)['tkgWorkloadComponents'][
                        'tkgWorkloadClusterBackupLocation']
                    cluster_group = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterGroupName']
            else:
                return False, "Invalid cluster type provided"

        if not backup_location:
            return False, "Backup location is None"

        if not cluster_group:
            return False, "cluster_group is None"

        clusterGroups = list_cluster_groups(env)
        if not clusterGroups[0]:
            return False, clusterGroups[1]

        if cluster_group not in clusterGroups[1]:
            return False, "Cluster Group " + cluster_group + " not found"

        tmc_header = fetchTMCHeaders(env)
        if tmc_header[0] is None:
            return False, tmc_header[1]

        headers = tmc_header[0]
        tmc_url = tmc_header[1]

        url = VeleroAPI.GET_LOCATION_INFO.format(tmc_url=tmc_url, location=backup_location)

        response = requests.request("GET", url, headers=headers, verify=False)
        if response.status_code == 404:
            return False, "Provided backup location for " + backup_location + " not found for " + clusterType + " cluster"
        elif response.status_code != 200:
            current_app.logger.error(response.json())
            return False, "Failed to fetch backup locations for data protection"

        if response.json()["backupLocation"]["status"]["phase"] == "READY":
            current_app.logger.info(backup_location + " backup location is valid")
        else:
            return False, backup_location + " backup location status is " + response.json()["backupLocation"]["status"][
                "phase"]

        current_app.logger.info("Proceeding to check if backup location is associated with provided cluster group")
        assigned_groups = response.json()["backupLocation"]["spec"]["assignedGroups"]
        for group in assigned_groups:
            if group["clustergroup"]["name"] == cluster_group:
                return True, "Cluster group and backup location association validated"

        return False, "Cluster group " + cluster_group + " is not assigned to backup location " + backup_location

    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while validating backup location"


def validate_cluster_credential(env, clusterType):
    try:
        if isEnvTkgs_ns(env) and clusterType.lower() == "shared":
            return False, "Invalid environment type provided for validation of data protection credentials"
        if env == Env.VMC:
            if clusterType.lower() == "shared":
                credential_name = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedClusterCredential']
                backup_location = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                    'tkgSharedClusterBackupLocation']
            elif clusterType.lower() == "workload":
                credential_name = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadClusterCredential']
                backup_location = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                    'tkgWorkloadClusterBackupLocation']
            else:
                return False, "Invalid cluster type provided"
        else:
            if clusterType.lower() == "shared":
                if not isEnvTkgs_ns(env) and not isEnvTkgs_wcp(env):
                    if env == Env.VCF:
                        credential_name = request.get_json(force=True)['tkgComponentSpec']["tkgSharedserviceSpec"][
                            'tkgSharedClusterCredential']
                        backup_location = request.get_json(force=True)['tkgComponentSpec']["tkgSharedserviceSpec"][
                            'tkgSharedClusterBackupLocation']
                    else:
                        credential_name = request.get_json(force=True)['tkgComponentSpec']["tkgMgmtComponents"][
                            "tkgSharedClusterCredential"]
                        backup_location = request.get_json(force=True)['tkgComponentSpec']["tkgMgmtComponents"][
                            "tkgSharedClusterBackupLocation"]
            elif clusterType.lower() == "workload":
                if isEnvTkgs_ns(env):
                    credential_name = request.get_json(force=True)['tkgsComponentSpec'][
                        "tkgsVsphereNamespaceSpec"][
                        'tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterCredential']
                    backup_location = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                        'tkgsVsphereWorkloadClusterSpec']['tkgWorkloadClusterBackupLocation']
                else:
                    credential_name = request.get_json(force=True)['tkgWorkloadComponents'][
                        'tkgWorkloadClusterCredential']
                    backup_location = request.get_json(force=True)['tkgWorkloadComponents'][
                        'tkgWorkloadClusterBackupLocation']
            else:
                return False, "Invalid cluster type provided"

        if not credential_name:
            return False, "Cluster Credential Name not found"

        tmc_header = fetchTMCHeaders(env)
        if tmc_header[0] is None:
            return False, tmc_header[1]

        headers = tmc_header[0]
        tmc_url = tmc_header[1]

        url = VeleroAPI.GET_CRED_INFO.format(tmc_url=tmc_url, credential=credential_name)

        response = requests.request("GET", url, headers=headers, verify=False)
        if response.status_code == 404:
            return False, "Provided credential name for data protection not found"
        elif response.status_code != 200:
            current_app.logger.error(response.json())
            return False, "Failed to fetch provided credential for data protection"

        if response.json()["credential"]["status"]["phase"] == "CREATED":
            current_app.logger.info(credential_name + " credential is valid")
        else:
            return False, credential_name + " cluster credential status is " + response.json()["credential"]["status"][
                "phase"]

        current_app.logger.info("Proceeding to check if credential " + credential_name +
                                "is associated with selected backup location " + backup_location)

        url = VeleroAPI.GET_LOCATION_INFO.format(tmc_url=tmc_url, location=backup_location)

        response = requests.request("GET", url, headers=headers, verify=False)
        if response.status_code == 404:
            return False, "Provided backup location for " + backup_location + "not found"

        if response.json()["backupLocation"]["spec"]["credential"]["name"] == credential_name:
            return True, "Credential " + credential_name + " validated successfully against backup location " + backup_location

        return False, "Credential " + credential_name + " is not associated with " + backup_location
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while validating cluster credential"


def list_cluster_groups(env):
    try:
        tmc_header = fetchTMCHeaders(env)
        if tmc_header[0] is None:
            return False, tmc_header[1]

        headers = tmc_header[0]
        tmc_url = tmc_header[1]

        cluster_groups = []
        url = VeleroAPI.LIST_CLUSTER_GROUPS.format(tmc_url=tmc_url)
        response = requests.request("GET", url, headers=headers, verify=False)
        if response.status_code != 200:
            current_app.logger.error(response.json())
            return False, "Failed to fetch cluster groups for data protection"

        for group in response.json()["clusterGroups"]:
            cluster_groups.append(group["fullName"]["name"])

        return True, cluster_groups
    except Exception as e:
        current_app.logger.error("Exception occurred while fetching cluster groups")
        return False, str(e)


def checkDataProtectionEnabled(env, type):
    if type == "shared":
        if env == Env.VMC:
            is_enabled = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec'][
                'tkgSharedserviceEnableDataProtection']
        elif env == Env.VCF:
            is_enabled = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceEnableDataProtection']
        elif env == Env.VSPHERE:
            is_enabled = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceEnableDataProtection']
    elif type == "workload":
        if isEnvTkgs_ns(env):
            is_enabled = request.get_json(force=True)["tkgsComponentSpec"]["tkgsVsphereNamespaceSpec"][
                "tkgsVsphereWorkloadClusterSpec"]["tkgsWorkloadEnableDataProtection"]
        elif env == Env.VCF or env == Env.VSPHERE:
            is_enabled = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadEnableDataProtection']
        elif env == Env.VMC:
            is_enabled = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec'][
                'tkgWorkloadEnableDataProtection']
    if is_enabled.lower() == "true":
        return True
    else:
        return False


def isDataprotectionEnabled(tmc_url, headers, payload, cluster):
    url = VeleroAPI.ENABLE_DP.format(tmc_url=tmc_url, cluster=cluster)
    status = requests.request("GET", url, headers=headers, data=payload, verify=False)
    try:
        if status.status_code == 200:
            if status.json()["dataProtections"][0]["status"]["phase"] == "READY":
                return True
            elif status.json()["dataProtections"][0]["status"]["phase"] == "ERROR":
                current_app.logger.error("Data protection is enabled but its status is ERROR")
                current_app.logger.error(status.json()["dataProtections"][0]["status"]["phaseInfo"])
                return True
        else:
            return False
    except Exception as e:
        return False


def enable_data_protection(env, cluster, mgmt_cluster):
    try:
        tmc_header = fetchTMCHeaders(env)
        if tmc_header[0] is None:
            return False, tmc_header[1]

        headers = tmc_header[0]
        tmc_url = tmc_header[1]

        current_app.logger.info("Enabling data protection on cluster " + cluster)
        url = VeleroAPI.GET_CLUSTER_INFO.format(tmc_url=tmc_url, cluster=cluster)

        if isEnvTkgs_ns(env):
            provisionerName = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
        else:
            provisionerName = "default"

        payload = {
            "full_name.managementClusterName": mgmt_cluster,
            "full_name.provisionerName": provisionerName
        }

        response = requests.request("GET", url, headers=headers, params=payload, verify=False)
        if response.status_code != 200:
            current_app.logger.error(response.json())
            return False, "Failed to fetch cluster details to enable data protection"

        orgId = response.json()["cluster"]["fullName"]["orgId"]
        url = VeleroAPI.ENABLE_DP.format(tmc_url=tmc_url, cluster=cluster)

        payload = {
            "dataProtection": {
                "fullName": {
                    "orgId": orgId,
                    "managementClusterName": mgmt_cluster,
                    "provisionerName": provisionerName,
                    "clusterName": cluster
                },
                "spec": {
                }
            }
        }

        json_payload = json.dumps(payload, indent=4)

        if not isDataprotectionEnabled(tmc_url, headers, json_payload, cluster):

            enable_response = requests.request("POST", url, headers=headers, data=json_payload, verify=False)
            if enable_response.status_code != 200:
                current_app.logger.error(enable_response.json())
                return False, "Failed to enable data protection on cluster " + cluster

            count = 0
            enabled = False

            status = requests.request("GET", url, headers=headers, data=json_payload, verify=False)
            try:
                if status.json()["dataProtections"][0]["status"]["phase"] == "READY":
                    enabled = True
                else:
                    current_app.logger.info("Waiting for data protection enablement to complete...")
            except:
                pass

            while count < 90 and not enabled:
                status = requests.request("GET", url, headers=headers, data=json_payload, verify=False)
                if status.json()["dataProtections"][0]["status"]["phase"] == "READY":
                    enabled = True
                    break
                elif status.json()["dataProtections"][0]["status"]["phase"] == "ERROR":
                    current_app.logger.error("Data protection is enabled but its status is ERROR")
                    current_app.logger.error(status.json()["dataProtections"][0]["status"]["phaseInfo"])
                    enabled = True
                    break
                else:
                    current_app.logger.info("Data protection status "
                                            + status.json()["dataProtections"][0]["status"]["phase"])
                    current_app.logger.info("Waited for " + str(count * 10) + "s, retrying...")
                    time.sleep(10)
                    count = count + 1

            if not enabled:
                current_app.logger.error("Data protection not enabled even after " + str(count * 10) + "s wait")
                return False, "Timed out waiting for data protection to be enabled"
            else:
                return True, "Data protection on cluster " + cluster + " enabled successfully"
        else:
            return True, "Data protection is already enabled on cluster " + cluster
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception enabled while enabling data protection on cluster"


def fetchTMCHeaders(env):
    if env == Env.VMC:
        refreshToken = request.get_json(force=True)['saasEndpoints']['tmcDetails']['tmcRefreshToken']
        tmc_url = request.get_json(force=True)['saasEndpoints']['tmcDetails']['tmcInstanceURL']
    else:
        refreshToken = request.get_json(force=True)['envSpec']['saasEndpoints']['tmcDetails']['tmcRefreshToken']
        tmc_url = request.get_json(force=True)['envSpec']['saasEndpoints']['tmcDetails']['tmcInstanceURL']

    if not tmc_url or not refreshToken:
        return None, "TMC details missing"

    if not tmc_url.endswith("/"):
        tmc_url = tmc_url + "/"

    url = VeleroAPI.GET_ACCESS_TOKEN.format(tmc_token=refreshToken)
    headers = {}
    payload = {}
    response_login = requests.request("POST", url, headers=headers, data=payload, verify=False)
    if response_login.status_code != 200:
        current_app.logger.error("TMC login failed using Refresh_Token - %s" % refreshToken)
        return None, "TMC Login failed using Refresh_Token " + refreshToken

    access_token = response_login.json()["access_token"]

    headers = {
        'Content-Type': 'application/json',
        'Authorization': access_token
    }

    return headers, tmc_url


def checkAVIPassword(env):
    try:
        if env == Env.VSPHERE or env == Env.VCF:
            if isEnvTkgs_wcp(env):
                avi_pass = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviPasswordBase64']
                avi_backup_pass = request.get_json(force=True)['tkgsComponentSpec']['aviComponents'][
                    'aviBackupPassphraseBase64']
            else:
                avi_pass = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviPasswordBase64']
                avi_backup_pass = request.get_json(force=True)['tkgComponentSpec']['aviComponents'][
                    'aviBackupPassphraseBase64']
        elif env == Env.VMC:
            avi_pass = request.get_json(force=True)['componentSpec']['aviComponentSpec']['aviPasswordBase64']
            avi_backup_pass = request.get_json(force=True)['componentSpec']['aviComponentSpec'][
                'aviBackupPassPhraseBase64']
        # avi_pass conversion from b64
        base64_bytes_avi = avi_pass.encode('ascii')
        enc_bytes_avi = base64.b64decode(base64_bytes_avi)
        avi_pass = enc_bytes_avi.decode('ascii').rstrip("\n")
        # avi_backup_pass conversion from b64
        base64_bytes_avi = avi_backup_pass.encode('ascii')
        enc_bytes_avi = base64.b64decode(base64_bytes_avi)
        avi_backup_pass = enc_bytes_avi.decode('ascii').rstrip("\n")

        # Check min length is 8
        if len(avi_pass) < 8 or len(avi_backup_pass) < 8:
            current_app.logger.error("The minimum length for AVI password and AVI Backup passphrase is 8!")
            return False, "The minimum length for AVI password and AVI Backup passphrase is 8!"

        # Check if password contains uppercase character
        match_count = 0
        pat_upper = re.compile('[A-Z]+')
        upper_match = re.search(pat_upper, avi_pass)
        if upper_match:
            match_count = match_count + 1
        pat_lower = re.compile('[a-z]+')
        lower_match = re.search(pat_lower, avi_pass)
        if lower_match:
            match_count = match_count + 1
        pat_digit = re.compile('[0-9]+')
        digit_match = re.search(pat_digit, avi_pass)
        if digit_match:
            match_count = match_count + 1
        pat_special = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        special_match = re.search(pat_special, avi_pass)
        if special_match:
            match_count = match_count + 1
        if match_count <= 3:
            current_app.logger.error(
                "NSX ALB Password must contain a combination of 3: Uppercase character, Lowercase character, Numeric or Special Character.")
            return False, "AVI Password must contain a combination of 3: Uppercase character, Lowercase character, Numeric or Special Character."
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
                "NSX ALB Backup Passphrase must contain a combination of 3: Uppercase character, Lowercase character, Numeric or Special Character.")
            return False, "NSX ALB Backup Passphrase must contain a combination of 3: Uppercase character, Lowercase character, Numeric or Special Character."
        else:
            current_app.logger.info("NSX ALB Backup Password passed the complexity check")
        return True, "Successfully validated password complexity checks for NSX ALB"
    except Exception as e:
        current_app.logger.error("NSX ALB Password and Backup passphrase is not matching the complexity")
        current_app.logger.error(
            "NSX ALB Password must contain a combination of 3: Uppercase character, Lowercase character, Numeric or Special Character.")
        return False, str(e)


def checkClusterNameDNSCompliant(cluster_name, env):
    try:
        dns_pat = re.compile('^[a-z0-9][a-z0-9-.]{0,40}[a-z0-9]$')
        compliant_match = re.search(dns_pat, cluster_name)
        if compliant_match:
            return True, "Successfully validated cluster name: " + cluster_name + " is DNS Compliant"
        else:
            current_app.logger.error(
                "Cluster name must start and end with a letter or number, and can contain only lowercase letters, numbers, and hyphens.")
            return False, "cluster name: " + cluster_name + " is not DNS Compliant"
    except Exception as e:
        current_app.logger.error("Failed to verify cluster name : " + cluster_name + " is DNS Compliant")
        return False, str(e)


# def ldap_operation(ldap_obj, operation_type, env, isbinded=False):
#     try:
#         if operation_type == 'CONNECT':
#             return ldap_connect(env, ldap_obj, isbinded)
#         elif operation_type == 'BIND':
#             return ldap_bind(env, ldap_obj, isbinded)
#         elif operation_type == 'USER_SEARCH':
#             return ldap_user_search(env, ldap_obj, isbinded)
#         elif operation_type == 'GROUP_SEARCH':
#             return ldap_group_search(env, ldap_obj, isbinded)
#         elif operation_type == 'DISCONNECT':
#             return ldap_unbind(env, ldap_obj, isbinded)
#     except Exception as e:
#         return False, str(e)

# def ldap_connect(env, ldap_obj, isbinded):
#     try:
#         if not (env == Env.VMC):
#             try:
#                 ldap_endpoint_ip = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapEndpointIp']
#                 ldap_port = int(request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapEndpointPort'])
#                 root_ca = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapRootCAData']
#             except Exception as e:
#                 if not root_ca:
#                     current_app.logger.error("Please provide ldapEndpointIp and "
#                                              "ldapEndpointPort to connect to LDAP Server")
#                     return False, str(e)
#         if env == Env.VMC:
#             try:
#                 ldap_endpoint_ip = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapEndpointIp']
#                 ldap_port = int(request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapEndpointPort'])
#                 root_ca = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapRootCAData']
#             except Exception as e:
#                 if not root_ca:
#                     current_app.logger.error("Please provide ldapEndpointIp and "
#                                             "ldapEndpointPort to connect to LDAP Server")
#                     return False, str(e)
#         if root_ca:
#             return ldap_obj.set_ldap_server_with_cert(ldap_endpoint_ip, ldap_port, root_ca)
#         else:
#             return ldap_obj.set_ldap_server_insecure(ldap_endpoint_ip, ldap_port)

#     except Exception as e:
#         current_app.logger.error("Exception while connecting to the LDAP Server")
#         return False, str(e)


# def ldap_bind(env, ldap_obj, isbinded):
#     try:
#         if not (env == Env.VMC):
#             try:
#                 ldap_bind_pw = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapBindPW']
#                 ldap_bind_dn = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapBindDN']
#             except Exception as e:
#                 current_app.logger.error("Please provide ldapBindPW and "
#                                          "ldapBindDN to bind to LDAP Server")
#                 return False, str(e)
#         if env == Env.VMC:
#             try:
#                 ldap_bind_pw = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapBindPW']
#                 ldap_bind_dn = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapBindDN']
#             except Exception as e:

#                 current_app.logger.error("Please provide ldapBindPW and "
#                                         "ldapBindDN to bind to LDAP Server")
#                 return False, str(e)
#         if not isbinded:
#             ldap_connect_response = ldap_connect(env, ldap_obj, isbinded=True)
#             if ldap_connect_response[0]:
#                 ldap_bind_response = ldap_obj.set_ldap_connection(ldap_bind_dn, ldap_bind_pw)
#                 if ldap_bind_response[0]:
#                     ldap_unbind(env, ldap_obj)
#                 return ldap_bind_response
#             else:
#                 return ldap_connect_response
#         else:
#             ldap_bind_response = ldap_obj.set_ldap_connection(ldap_bind_dn, ldap_bind_pw)
#             return ldap_bind_response
#     except Exception as e:
#         current_app.logger.error("Exception while bindinng to the LDAP Server")
#         return False, str(e)

# def ldap_user_search(env, ldap_obj, isbinded):
#     try:
#         if not (env == Env.VMC):
#             try:
#                 ldap_user_search_base_dn = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapUserSearchBaseDN']
#                 ldap_user_search_filter = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapUserSearchFilter']
#                 ldap_user_search_uname = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapUserSearchUsername']
#                 test_user = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapTestUserName']
#             except Exception as e:
#                 if not ldap_user_search_filter:
#                     ldap_user_search_filter = ""
#                 if not ldap_user_search_base_dn:
#                     ldap_user_search_base_dn = ""
#                 if not ldap_user_search_uname:
#                     ldap_user_search_uname = ""
#                 if not test_user:
#                     test_user = ""
#         if env == Env.VMC:
#             try:
#                 ldap_user_search_base_dn = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapUserSearchBaseDN']
#                 ldap_user_search_filter = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapUserSearchFilter']
#                 ldap_user_search_uname = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapUserSearchUsername']
#                 test_user = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapTestUserName']
#             except Exception as e:
#                 if not ldap_user_search_filter:
#                     ldap_user_search_filter = ""
#                 if not ldap_user_search_base_dn:
#                     ldap_user_search_base_dn = ""
#                 if not ldap_user_search_uname:
#                     ldap_user_search_uname = ""
#                 if not test_user:
#                     test_user = ""
#         if not isbinded:
#             ldap_connect_response = ldap_connect(env, ldap_obj, isbinded=True)
#             if ldap_connect_response[0]:
#                 ldap_bind_response = ldap_bind(env, ldap_obj, isbinded=True)
#                 if ldap_bind_response[0]:
#                     ldap_user_search_response = ldap_obj.ldap_user_search(ldap_user_search_base_dn,
#                                                                           ldap_user_search_filter,
#                                                                           ldap_user_search_uname,
#                                                                           test_user)
#                     if not ldap_user_search_response[0]:
#                         current_app.logger.error("Retrieved User List: " + ldap_user_search_response[2])
#                     ldap_unbind(env, ldap_obj, isbinded=True)
#                     current_app.logger.error("Failed to perform user search on LDAP server")
#                     current_app.logger.error(ldap_user_search_response[1])
#                     return ldap_user_search_response
#                 else:
#                     current_app.logger.error("Failed to bind to LDAP server")
#                     current_app.logger.error(ldap_bind_response[1])
#                     return ldap_bind_response
#             else:
#                 current_app.logger.error("Failed to connect to LDAP server")
#                 current_app.logger.error(ldap_connect_response[1])
#                 return ldap_connect_response
#         else:
#             ldap_user_search_response = ldap_obj.ldap_user_search(ldap_user_search_base_dn,
#                                                                   ldap_user_search_filter,
#                                                                   ldap_user_search_uname,
#                                                                   test_user)
#             # current_app.logger.info(ldap_user_search_response[2])
#             if not ldap_user_search_response[0]:
#                 current_app.logger.error("Retrieved User List: " + ldap_user_search_response[2])
#             return ldap_user_search_response
#     except Exception as e:
#         current_app.logger.error("Exception while performing user search on the LDAP Server")
#         current_app.logger.error(str(e))
#         return False, str(e)


# def ldap_group_search(env, ldap_obj, isbinded):
#     try:
#         if not (env == Env.VMC):
#             try:
#                 ldap_grp_search_base_dn = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchBaseDN']
#                 ldap_grp_search_filter = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchFilter']
#                 ldap_grp_search_user_attr = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchUserAttr']
#                 ldap_grp_search_grp_attr = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchGroupAttr']
#                 ldap_grp_search_name_attr = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchNameAttr']
#                 test_group = request.get_json(force=True)['tkgComponentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapTestGroupName']
#             except Exception as e:
#                 if not ldap_grp_search_base_dn:
#                     ldap_grp_search_base_dn = ""
#                 if not ldap_grp_search_filter:
#                     ldap_grp_search_filter = ""
#                 if not ldap_grp_search_user_attr:
#                     ldap_grp_search_user_attr = ""
#                 if not ldap_grp_search_grp_attr:
#                     ldap_grp_search_grp_attr = ""
#                 if not ldap_grp_search_name_attr:
#                     ldap_grp_search_name_attr = ""
#                 if not test_group:
#                     test_group = ""
#         if env == Env.VMC:
#             try:
#                 ldap_grp_search_base_dn = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchBaseDN']
#                 ldap_grp_search_filter = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchFilter']
#                 ldap_grp_search_user_attr = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchUserAttr']
#                 ldap_grp_search_grp_attr = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchGroupAttr']
#                 ldap_grp_search_name_attr = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapGroupSearchNameAttr']
#                 test_group = request.get_json(force=True)['componentSpec']['identityManagementSpec'][
#                     'ldapSpec']['ldapTestGroupName']
#             except Exception as e:
#                 if not ldap_grp_search_base_dn:
#                     ldap_grp_search_base_dn = ""
#                 if not ldap_grp_search_filter:
#                     ldap_grp_search_filter = ""
#                 if not ldap_grp_search_user_attr:
#                     ldap_grp_search_user_attr = ""
#                 if not ldap_grp_search_grp_attr:
#                     ldap_grp_search_grp_attr = ""
#                 if not ldap_grp_search_name_attr:
#                     ldap_grp_search_name_attr = ""
#                 if not test_group:
#                     test_group = ""
#         if not isbinded:
#             ldap_connect_response = ldap_connect(env, ldap_obj, isbinded=True)
#             if ldap_connect_response[0]:
#                 ldap_bind_response = ldap_bind(env, ldap_obj, isbinded=True)
#                 if ldap_bind_response[0]:
#                     ldap_group_search_response = ldap_obj.ldap_group_search(ldap_grp_search_base_dn, ldap_grp_search_filter,
#                                                                             ldap_grp_search_user_attr, ldap_grp_search_grp_attr,
#                                                                             ldap_grp_search_name_attr, test_group)
#                     if not ldap_group_search_response[0]:
#                         current_app.logger.error("Retrieved Group List: " + ldap_group_search_response[2])
#                     ldap_unbind(env, ldap_obj)
#                     return ldap_group_search_response
#                 else:
#                     return ldap_bind_response
#             else:
#                 return ldap_connect_response
#         else:
#             ldap_group_search_response = ldap_obj.ldap_group_search(ldap_grp_search_base_dn, ldap_grp_search_filter,
#                                                                     ldap_grp_search_user_attr, ldap_grp_search_grp_attr,
#                                                                     ldap_grp_search_name_attr, test_group)
#             if not ldap_group_search_response[0]:
#                 current_app.logger.error("Retrieved Group List: " + ldap_group_search_response[2])
#             return ldap_group_search_response
#     except Exception as e:
#         current_app.logger.error("Exception while performing group search on the LDAP Server")
#         return False, str(e)


# def ldap_unbind(env, ldap_obj, isbinded):
#     try:
#         return ldap_obj.unbind_ldap_connection()
#     except Exception as e:
#         current_app.logger.error("Exception while unbinding to the LDAP Server")
#         return False, str(e)


def getNetworkDetailsVip(ip, csrf2, vipNetworkUrl, startIp, endIp, prefixIp, netmask, aviVersion):
    url = vipNetworkUrl
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
    try:
        add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_ip"] = add
        details["vim_ref"] = response_csrf.json()["vimgrnw_ref"]
        details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
        return "AlreadyConfigured", 200, details
    except Exception as e:
        current_app.logger.info("Ip pools are not configured configuring it")

    os.system("rm -rf vipNetworkDetails.json")
    with open("./vipNetworkDetails.json", "w") as outfile:
        json.dump(response_csrf.json(), outfile)
    generateVsphereConfiguredSubnets("vipNetworkDetails.json", startIp, endIp, prefixIp,
                                     int(netmask))
    return "SUCCESS", 200, details


def create_virtual_service(ip, csrf2, avi_cloud_uuid, se_name, vip_network_url, se_count, avi_version):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0]
    }
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
        cloud_ref_ = cloud_ref[cloud_ref.rindex("/") + 1:]
        se_group_url = AlbEndpoint.AVI_SE_GROUP.format(ip=ip, cloud_ref=cloud_ref_, service_engine_uuid=se_uuid)
        response = requests.request("GET", se_group_url, headers=headers, data=body, verify=False)
        if response.status_code != 200:
            return None, response.text
        createVs = False
        try:
            service_engines = response.json()["results"][0]["serviceengines"]
            if len(service_engines) > (se_count - 1):
                current_app.logger.info("Required service engines are already creeated")
            else:
                createVs = True
        except:
            createVs = True
        if createVs:
            current_app.logger.info("Creating  virtual service")
            vrf_get_url = "https://" + ip + "/api/vrfcontext/?name.in=" + type + "&cloud_ref.uuid=" + avi_cloud_uuid
            response_csrf = requests.request("GET", vrf_get_url, headers=headers, data=body, verify=False)
            if response_csrf.status_code != 200:
                return None, response_csrf.text
            vrf_url = ""
            for re in response_csrf.json()['results']:
                if re['name'] == type:
                    vrf_url = re["url"]
                    break
            if not vrf_url:
                return None, "VRF_URL_NOT_FOUND"
            startIp = request.get_json(force=True)["tkgComponentSpec"]['tkgClusterVipNetwork'][
                "tkgClusterVipIpStartRange"]
            endIp = request.get_json(force=True)["tkgComponentSpec"]['tkgClusterVipNetwork'][
                "tkgClusterVipIpEndRange"]
            prefixIpNetmask = seperateNetmaskAndIp(
                request.get_json(force=True)["tkgComponentSpec"]['tkgClusterVipNetwork'][
                    "tkgClusterVipNetworkGatewayCidr"])
            getVIPNetworkDetails = getNetworkDetailsVip(ip, csrf2, vip_network_url, startIp, endIp, prefixIpNetmask[0],
                                                        prefixIpNetmask[1], avi_version)
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
            except:
                current_app.logger.info("No virtual service vip created")
            if not isVipCreated:
                body = AlbPayload.VIRTUAL_SERVICE_VIP.format(cloud_ref=cloud_ref,
                                                             virtual_service_name_vip=ServiceName.SIVT_SERVICE_VIP,
                                                             vrf_context_ref=vrf_url
                                                             , network_ref=vip_network_url, addr=ip_pre, mask=mask)
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
            except:
                current_app.logger.info("No virtual service created")
            if not isVsCreated:
                body = AlbPayload.VIRTUAL_SERVICE.format(cloud_ref=cloud_ref,
                                                         se_group_ref=service_engine_group_url
                                                         , vsvip_ref=vip_url)
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
                        while counter_se < 60:
                            response = requests.request("GET", se_group_url, headers=headers, data=body, verify=False)
                            if response.status_code != 200:
                                return None, response.text
                            config = response.json()["results"][0]
                            try:
                                seurl = config["serviceengines"][i]
                                initialized = True
                                break
                            except:
                                current_app.logger.info(
                                    "Waited " + str(counter_se * 10) + "s for service engines to be "
                                                                       "initialized")
                            counter_se = counter_se + 1
                            time.sleep(30)
                        if not initialized:
                            return None, "Service engines not initialized  in 30m"
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
                                    "Waited " + str(counter * 30) + "s,to check se  connected status retrying")
                            if not isConnected:
                                return None, "Waited " + str(
                                    counter * 30) + "s,to check se  connected and is not in connected state"
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
                                    "Waited " + str(counter * 10) + "s,to check se  connected status retrying")
                            if not isConnected:
                                return None, "Waited " + str(
                                    counter * 10) + "s,to check se  connected and is not in connected state"
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
                except:
                    current_app.logger.info("No virtual service vip created")
                vs_url = ""
                virtual_service_url = AlbEndpoint.AVI_VIRTUAL_SERVICE.format(ip=ip)
                response = requests.request("GET", virtual_service_url, headers=headers, data=body, verify=False)
                try:
                    for r in response.json()["results"]:
                        if r["name"] == ServiceName.SIVT_SERVICE:
                            vs_url = r["url"]
                            break
                except:
                    current_app.logger.info("No virtual service created")
                requests.request("DELETE", vs_url, headers=headers, data=body, verify=False)
                requests.request("DELETE", vip_url, headers=headers, data=body, verify=False)
            except Exception as e:
                pass
            return "SUCCESS", "Required Service engines sucessfully  created"
        else:
            return "SUCCESS", "Required Service engines are already present"
