#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os, sys
import re
import traceback
import json
from util import cmd_runner
from pathlib import Path
import base64
import logging
from constants.constants import Paths, ControllerLocation, KubernetesOva, MarketPlaceUrl, VrfType, \
    ClusterType, TmcUser, RegexPattern, SAS, AppName, UpgradeVersions, Repo, Env, Extentions, Tkg_Extention_names, \
    Tkg_version, TKG_Package_Details, TKGCommands
from util.extensions_helper import check_fluent_bit_http_endpoint_enabled, check_fluent_bit_splunk_endpoint_endpoint_enabled, \
    check_fluent_bit_syslog_endpoint_enabled, check_fluent_bit_elastic_search_endpoint_enabled, check_fluent_bit_kafka_endpoint_endpoint_enabled
from util.logger_helper import LoggerHelper
import requests
from util.avi_api_helper import getProductSlugId
from util.replace_value import replaceValueSysConfig, replaceValue
from util.file_helper import FileHelper
from util.ShellHelper import runShellCommandAndReturnOutput, runShellCommandAndReturnOutputAsList,\
    runProcess, grabKubectlCommand, verifyPodsAreRunning, grabPipeOutput
from util.cmd_helper import CmdHelper
from util.cmd_runner import RunCmd
import time
from jinja2 import Template
import yaml
from ruamel import yaml as ryaml
from datetime import datetime
from util.vcenter_operations import createResourcePool, create_folder
from util.tkg_util import TkgUtil
import subprocess
import pathlib
import tarfile
from pyVim import connect


logger = LoggerHelper.get_logger('common_utils')
logging.getLogger("paramiko").setLevel(logging.WARNING)

def checkenv(jsonspec):
    vcpass_base64 = jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
    password = CmdHelper.decode_base64(vcpass_base64)
    vcenter_username = jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
    vcenter_ip = jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    rcmd = RunCmd()
    cmd = 'govc ls'
    try:
        check_connection = rcmd.run_cmd_output(cmd)
        return check_connection
    except Exception:
        return None

def createSubscribedLibrary(vcenter_ip, vcenter_username, password, jsonspec):
    try:
        os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
        os.putenv("GOVC_USERNAME", vcenter_username)
        os.putenv("GOVC_PASSWORD", password)
        os.putenv("GOVC_INSECURE", "true")
        url = "https://wp-content.vmware.com/v2/latest/lib.json"
        rcmd = cmd_runner.RunCmd()
        data_center = str(jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter'])
        data_store = str(jsonspec['envSpec']['vcenterDetails']['vcenterDatastore'])
        find_command = ["govc", "library.ls"]
        output = rcmd.runShellCommandAndReturnOutputAsList(find_command)
        if str(output[0]).__contains__(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY):
            logger.info(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY + " is already present")
        else:
            create_command = ["govc", "library.create", "-sub=" + url, "-ds=" + data_store, "-dc=" + data_center,
                              "-sub-autosync=true", "-sub-ondemand=true",
                              ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY]
            output = rcmd.runShellCommandAndReturnOutputAsList(create_command)
            if output[1] != 0:
                return None, "Failed to create content library"
            logger.info("Content library created successfully")
    except Exception as e:
        logger.info("Error: {}".format(e))
        return None, "Failed"
    return "SUCCESS", "LIBRARY"

def download_upgrade_binaries(binary, refreshToken):

    # TODO: redudant download method. replace to single one with filename and targetted binary
    rcmd = cmd_runner.RunCmd()
    filename = binary
    solutionName = KubernetesOva.MARKETPLACE_KUBERNETES_SOLUTION_NAME
    logger.debug(("Solution Name: {}".format(solutionName)))
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
    slug = "true"
    _solutionName = getProductSlugId(MarketPlaceUrl.TANZU_PRODUCT, headers)
    if _solutionName[0] is None:
        return None, "Failed to find product on Marketplace " + str(_solutionName[1])
    solutionName = _solutionName[0]
    product = requests.get(
        MarketPlaceUrl.API_URL + "/products/" + solutionName + "?isSlug=" + slug + "&ownorg=false",
        headers=headers,
        verify=False)

    if product.status_code != 200:
        return None, "Failed to Obtain Product ID"
    else:
        product_id = product.json()['response']['data']['productid']
        for metalist in product.json()['response']['data']['metafilesList']:
            binary_targetted = metalist["metafileobjectsList"][0]['filename']
            app_version = metalist['appversion']

            if app_version in UpgradeVersions.TARGET_VERSION:
                logger.info("Binary: {}".format(binary_targetted))
                logger.info("appversion: {}".format(app_version))

                if binary in binary_targetted:
                    logger.info("Found the binary....")
                    objectid = metalist["metafileobjectsList"][0]['fileid']
                    binaryName = metalist["metafileobjectsList"][0]['filename']
                    metafileid = metalist['metafileid']
                    logger.info("Binary Downloading...: {}".format(binaryName))
                    logger.info("appversion Downloading..: {}".format(app_version))

    if (objectid or binaryName or app_version or metafileid) is None:
        return None, "Failed to find the file details in Marketplace"

    logger.info("Downloading binary " + binaryName)

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

    curl_inspect_cmd = 'curl -I -X GET {} --output /tmp/resp.txt'.format(download_url)
    rcmd.run_cmd_only(curl_inspect_cmd)
    with open('/tmp/resp.txt', 'r') as f:
        data_read = f.read()
    if 'HTTP/1.1 200 OK' in data_read:
        logger.info('Proceed to Download')
        binary_path = "/tmp/" + filename
        curl_download_cmd = 'curl -X GET {d_url} --output {tmp_path}'.format(d_url=download_url,
                                                                             tmp_path=binary_path)
        rcmd.run_cmd_only(curl_download_cmd)
    else:
        logger.info('Error in presigned url/key: {} '.format(data_read.split('\n')[0]))
        return None, "Invalid key/url"

    return filename, "Kubernetes OVA download successful"

def getOvaMarketPlace(filename, refreshToken, version, baseOS, upgrade):

    rcmd = cmd_runner.RunCmd()
    ovaName = None
    app_version = None
    metafileid = None
    # get base tanzu version for right ova to be downloaded
    tanzu_targetted_version = KubernetesOva.TARGET_VERSION
    filename = filename + ".ova"
    solutionName = KubernetesOva.MARKETPLACE_KUBERNETES_SOLUTION_NAME
    logger.debug(("Solution Name: {}".format(solutionName)))
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
            ovaname = metalist["metafileobjectsList"][0]['filename']
            if upgrade:
                # todo: Change targetted version to get from desired state
                #version:  tkg: 1.5.3
                if metalist['appversion'] in UpgradeVersions.TARGET_VERSION:
                    if metalist["version"] == version[1:] and str(metalist["groupname"]).strip(
                             "\t") == ova_groupname:
                         objectid = metalist["metafileobjectsList"][0]['fileid']
                         ovaName = metalist["metafileobjectsList"][0]['filename']
                         app_version = metalist['appversion']
                         metafileid = metalist['metafileid']
                         break

            else:
                # tanzu_targetted_version since we have grouped ova's under marketplace
                # under versions
                if metalist['appversion'] == tanzu_targetted_version:
                    if metalist["version"] == version[1:] and str(metalist["groupname"]).strip("\t")\
                            == ova_groupname:
                        objectid = metalist["metafileobjectsList"][0]['fileid']
                        ovaName = metalist["metafileobjectsList"][0]['filename']
                        app_version = metalist['appversion']
                        metafileid = metalist['metafileid']
                        break
    logger.info("---------------------")
    logger.info("ovaName: {ovaName} app_version: {app_version} metafileid: {metafileid}".format(ovaName=ovaName,
                                                                                                app_version=app_version,
                                                                                                metafileid=metafileid))
    if (objectid or ovaName or app_version or metafileid) is None:
        return None, "Failed to find the file details in Marketplace"

    logger.info("Downloading kubernetes ova - " + ovaName)

    payload = {
        "eulaAccepted": "true",
        "appVersion": app_version,
        "metafileid": metafileid,
        "metafileobjectid": objectid
    }

    json_object = json.dumps(payload, indent=4).replace('\"true\"', 'true')
    logger.info('--------')
    logger.info('Marketplaceurl: {url} data: {data}'.format(url=MarketPlaceUrl.URL, data=json_object))
    presigned_url = requests.request("POST",
                                     MarketPlaceUrl.URL + "/api/v1/products/" + product_id + "/download",
                                     headers=headers, data=json_object, verify=False)
    logger.info('presigned_url: {}'.format(presigned_url))
    logger.info('presigned_url text: {}'.format(presigned_url.text))
    if presigned_url.status_code != 200:
        return None, "Failed to obtain pre-signed URL"
    else:
        download_url = presigned_url.json()["response"]["presignedurl"]

    curl_inspect_cmd = 'curl -I -X GET {} --output /tmp/resp.txt'.format(download_url)
    rcmd.run_cmd_only(curl_inspect_cmd)
    with open('/tmp/resp.txt', 'r') as f:
        data_read = f.read()
    if 'HTTP/1.1 200 OK' in data_read:
        logger.info('Proceed to Download')
        ova_path = "/tmp/" + filename
        curl_download_cmd = 'curl -X GET {d_url} --output {tmp_path}'.format(d_url=download_url,
                                                                             tmp_path=ova_path)
        rcmd.run_cmd_only(curl_download_cmd)
    else:
        logger.info('Error in presigned url/key: {} '.format(data_read.split('\n')[0]))
        return None, "Invalid key/url"

    return filename, "Kubernetes OVA download successful"


def downloadAndPushToVCMarketPlace(file, datacenter, datastore, networkName, clusterName,
                                   refresToken, ovaVersion, ovaOS, jsonspec, upgrade):
    my_file = Path("/tmp/" + file + ".ova")
    rcmd = cmd_runner.RunCmd()
    if not my_file.exists():
        logger.info("Downloading kubernetes ova from MarketPlace")
        download_status = getOvaMarketPlace(file, refresToken, ovaVersion, ovaOS, upgrade)
        if download_status[0] is None:
            return None, download_status[1]
        logger.info("Kubernetes ova downloaded  at location " + "/tmp/" + file)
    else:
        logger.info("Kubernetes ova is already downloaded")
    kube_config = FileHelper.read_resource(Paths.KUBE_OVA_CONFIG)
    kube_config_file = "/tmp/kubeova.json"
    FileHelper.write_to_file(kube_config, kube_config_file)
    replaceValueSysConfig(kube_config_file, "Name", "name", file)
    replaceValue(kube_config_file, "NetworkMapping", "Network", networkName)
    logger.info("Pushing " + file + " to vcenter and making as template")
    vcenter_ip = jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
    vcenter_username = jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
    enc_password = jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
    password = CmdHelper.decode_base64(enc_password)
    os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_username)
    os.putenv("GOVC_PASSWORD", password)
    os.putenv("GOVC_INSECURE", "true")
    command_template = ["govc", "import.ova", "-options", kube_config_file, "-dc="+datacenter,
                        "-ds=" + datastore, "-pool=" + clusterName + "/Resources",
                        "/tmp/" + file + ".ova"]
    output = rcmd.runShellCommandAndReturnOutputAsList(command_template)
    if output[1] != 0:
        return None, "Failed export kubernetes ova to vCenter"
    return "SUCCESS", "DEPLOYED"

def downloadAndPushKubernetesOvaMarketPlace(jsonspec, version, baseOS, upgrade=False):
    try:
        rcmd = cmd_runner.RunCmd()
        networkName = str(jsonspec["tkgComponentSpec"]["tkgMgmtComponents"]["tkgMgmtNetworkName"])
        data_store = str(jsonspec['envSpec']['vcenterDetails']['vcenterDatastore'])
        vCenter_datacenter = jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        vCenter_cluster = jsonspec['envSpec']['vcenterDetails']['vcenterCluster']
        refToken = jsonspec['envSpec']['marketplaceSpec']['refreshToken']
        if not upgrade:
            if baseOS == "photon":
                file = KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + version
                template = KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + version
            elif baseOS == "ubuntu":
                file = KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + version
                template = KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + version
            else:
                return None, "Invalid ova type " + baseOS
        else:
            if baseOS == "photon":
                file = UpgradeVersions.PHOTON_KUBERNETES_FILE_NAME
                template = UpgradeVersions.PHOTON_KUBERNETES_TEMPLATE_FILE_NAME
            elif baseOS == "ubuntu":
                file = UpgradeVersions.UBUNTU_KUBERNETES_FILE_NAME
                template = UpgradeVersions.UBUNTU_KUBERNETES__TEMPLATE_FILE_NAME
            else:
                return None, "Invalid ova type " + baseOS
        govc_command = ["govc", "ls", "/" + vCenter_datacenter + "/vm"]
        output = rcmd.runShellCommandAndReturnOutputAsList(govc_command)
        if str(output[0]).__contains__(template):
            logger.info(template + " is already present in vcenter")
            return "SUCCESS", "ALREADY_PRESENT"
        logger.info("Template is not present. proceeding to download from marketplace...")
        if not refToken:
            logger.error("MarketPlace refresh token is not provided,"
                         "and unable to locate required template. Please place the required "
                         "template or provide marketplace token Existing...")
            return None, "No required template available"

        download = downloadAndPushToVCMarketPlace(file, vCenter_datacenter, data_store, networkName,
                                                          vCenter_cluster, refToken,
                                                          version, baseOS, jsonspec, upgrade)
        if download[0] is None:

            return None, download[1]
        return "SUCCESS", "DEPLOYED"

    except Exception as e:
        return None, str(e)

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
                logger.info("Folder and resources are available")
                return True
        else:
            if str(output[0]).__contains__("/Resources/" + resources) and str(output[0]).__contains__("/vm/" + folder):
                logger.info("Folder and resources are available")
                return True
        time.sleep(5)
        count = count + 1
    return False

def createResourceFolderAndWait(vcenter_ip, vcenter_username, password,
                                cluster_name, data_center, resourcePoolName, folderName,
                                parentResourcePool):
    try:
        isCreated4 = createResourcePool(vcenter_ip, vcenter_username, password,
                                        cluster_name,
                                        resourcePoolName, parentResourcePool)
        if isCreated4 is not None:
            logger.info("Created resource pool " + resourcePoolName)
    except Exception as e:
        logger.error("Failed to create resource pool " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(e),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

    try:
        isCreated1 = create_folder(vcenter_ip, vcenter_username, password,
                                   data_center,
                                   folderName)
        if isCreated1 is not None:
            logger.info("Created  folder " + folderName)

    except Exception as e:
        logger.error("Failed to create folder " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create folder " + str(e),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    find = validateFolderAndResourcesAvailable(folderName, resourcePoolName, vcenter_ip,
                                               vcenter_username, password, parentResourcePool)
    if not find:
        logger.error("Failed to find folder and resources")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to find folder and resources",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    d = {
        "responseType": "ERROR",
        "msg": "Created resources and  folder",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200

def untar_binary(target_tar, dest_path='/tmp/'):
    """
    untar .tar or .tgz file to /tmp/<tarfile>
    :param tarfile:
    :return:
    """
    tar = tarfile.open(target_tar)
    tar.extractall(path=dest_path)
    tar.close()

def locate_binary_tmp(search_dir, filestring):

    installer_file = None
    for fpath in pathlib.Path(search_dir).glob('**/*'):
        fabs_path = fpath
        if filestring in str(fabs_path):
            installer_file = fabs_path
            break
    return installer_file

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

def getVrfAndNextRoutId(ip, csrf2, cloudUuid, typen, routIp, aviVersion):
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
    url = "https://" + ip + "/api/vrfcontext/?name.in=" + typen + "&cloud_ref.uuid=" + cloudUuid
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text
    else:
        liist = []
        for re in response_csrf.json()['results']:
            if re['name'] == typen:
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
                if typen == VrfType.MANAGEMENT:
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


def getSeNewBody(newCloudUrl, seGroupName, clusterUrl, dataStore):
    body = {
        "max_vs_per_se": 10,
        "min_scaleout_per_vs": 2,
        "max_scaleout_per_vs": 4,
        "max_se": 10,
        "vcpus_per_se": 2,
        "memory_per_se": 4096,
        "disk_per_se": 15,
        "max_cpu_usage": 80,
        "min_cpu_usage": 30,
        "se_deprovision_delay": 120,
        "auto_rebalance": False,
        "se_name_prefix": "Avi",
        "vs_host_redundancy": True,
        "vcenter_folder": "AviSeFolder",
        "vcenter_datastores_include": True,
        "vcenter_datastore_mode": "VCENTER_DATASTORE_SHARED",
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
        "vcenter_datastores": [{
            "datastore_name": dataStore
        }],
        "service_ip_subnets": [],
        "auto_rebalance_criteria": [],
        "auto_rebalance_capacity_per_se": [],
        "vcenter_clusters": {
            "include": True,
            "cluster_refs": [
                clusterUrl
            ]
        },
        "license_tier": "ENTERPRISE",
        "license_type": "LIC_CORES",
        "se_bandwidth_type": "SE_BANDWIDTH_UNLIMITED",
        "name": seGroupName
    }
    return json.dumps(body, indent=4)

def getClusterStatusOnTanzu(management_cluster, typen):
    try:
        if typen == "management":
            listn = ["tanzu", "management-cluster", "get"]
        else:
            listn = ["tanzu", "cluster", "get"]
        o = runShellCommandAndReturnOutput(listn)
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

def runSsh(vc_user):
    os.system("rm -rf /root/.ssh/id_rsa")
    os.system("ssh-keygen -t rsa -b 4096 -C '" + vc_user + "' -f /root/.ssh/id_rsa -N ''")
    os.system("eval $(ssh-agent)")
    os.system("ssh-add /root/.ssh/id_rsa")
    with open('/root/.ssh/id_rsa.pub', 'r') as f:
        re = f.readline()
    return re

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
                logger.info("Network is available " + str(net))
                return net
        time.sleep(5)
        count = count + 1
    return None

def template14deployYaml(cluster_name, clusterPlan, datacenter, dataStorePath,
                         folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool,
                         vsphereServer, sshKey, vsphereUseName, machineCount, size, typen, vsSpec,
                         jsonspec):
    deploy_yaml = FileHelper.read_resource(Paths.TKG_CLUSTER_14_SPEC_J2)
    t = Template(deploy_yaml)
    datacenter = "/" + datacenter
    control_plane_vcpu = ""
    control_plane_disk_gb = ""
    # control_plane_mem_gb = ""
    control_plane_mem_mb = ""
    osName = ""
    try:
        if typen == ClusterType.SHARED:
            clustercidr = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceClusterCidr
            servicecidr = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceServiceCidr
            size_selection = vsSpec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceSize
            if str(size_selection).lower() == "custom":
                control_plane_vcpu = jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceCpuSize']
                control_plane_disk_gb = jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceStorageSize']
                control_plane_mem_gb = jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceMemorySize']
                control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
            try:
                osName = str(jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceBaseOs'])
                kubeVersion = str(jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceKubeVersion'])
                logger.debug("Targetted Kube Version: {}".format(kubeVersion))
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
        elif typen == ClusterType.WORKLOAD:
            clustercidr = vsSpec.tkgWorkloadComponents.tkgWorkloadClusterCidr
            servicecidr = vsSpec.tkgWorkloadComponents.tkgWorkloadServiceCidr
            size_selection = vsSpec.tkgWorkloadComponents.tkgWorkloadSize
            if str(size_selection).lower() == "custom":
                control_plane_vcpu = jsonspec['tkgWorkloadComponents']['tkgWorkloadCpuSize']
                control_plane_disk_gb = jsonspec['tkgWorkloadComponents']['tkgWorkloadStorageSize']
                control_plane_mem_gb = jsonspec['tkgWorkloadComponents']['tkgWorkloadMemorySize']
                control_plane_mem_mb = str(int(control_plane_mem_gb) * 1024)
            try:
                osName = str(jsonspec['tkgWorkloadComponents']['tkgWorkloadBaseOs'])
                kubeVersion = str(
                    jsonspec['tkgWorkloadComponents']['tkgWorkloadKubeVersion'])
            except Exception as e:
                raise Exception("Keyword " + str(e) + "  not found in input file")
    except Exception:
        logger.error("Error in yaml parsing for cluster creation")
        logger.error(traceback.format_exc())

    if osName == "photon":
        osVersion = "3"
    elif osName == "ubuntu":
        osVersion = "20.04"
    else:
        raise Exception("Wrong os name provided")

    air_gapped_repo = ""
    repo_certificate = ""
    FileHelper.write_to_file(
        t.render(config=vsSpec, clustercidr=clustercidr, sharedClusterName=cluster_name,
                 clusterPlan=clusterPlan, servicecidr=servicecidr, datacenter=datacenter,
                 dataStorePath=dataStorePath, folderPath=folderPath, mgmt_network=mgmt_network,
                 vspherePassword=vspherePassword,
                 sharedClusterResourcePool=sharedClusterResourcePool,
                 vsphereServer=vsphereServer, sshKey=sshKey, vsphereUseName=vsphereUseName,
                 controlPlaneSize=size, machineCount=machineCount, workerSize=size, type=type,
                 air_gapped_repo=air_gapped_repo, repo_certificate=repo_certificate, osName=osName,
                 osVersion=osVersion, size=size_selection, control_plane_vcpu=control_plane_vcpu,
                 control_plane_disk_gb=control_plane_disk_gb,
                 control_plane_mem_mb=control_plane_mem_mb), cluster_name + ".yaml")


def deployCluster(cluster_name, clusterPlan, datacenter, dataStorePath,
                  folderPath, mgmt_network, vspherePassword, sharedClusterResourcePool,
                  vsphereServer, sshKey, vsphereUseName, machineCount, size, typen, vsSpec,
                  jsonspec):
    try:
        if not getClusterStatusOnTanzu(cluster_name, "cluster"):
            template14deployYaml(cluster_name, clusterPlan, datacenter, dataStorePath,
                                 folderPath, mgmt_network, vspherePassword,
                                 sharedClusterResourcePool, vsphereServer, sshKey, vsphereUseName,
                                 machineCount, size, typen, vsSpec, jsonspec)
            logger.info("Deploying " + cluster_name + "cluster")
            os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
            logger.info("---------- yaml---------")
            logger.info(cluster_name)
            logger.info("------------------------------")
            listOfCmd = ["tanzu", "cluster", "create", "-f", cluster_name + ".yaml", "-v", "6"]
            runProcess(listOfCmd)
            return "SUCCESS", 200
        else:
            return "SUCCESS", 200
    except Exception as e:
        logger.error("Error Encountered: {}".format(traceback.format_exc()))
        return None, str(e)

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

def generateTmcProxyYaml(name_of_proxy, httpProxy_, httpsProxy_, noProxyList_, httpUserName_, httpPassword_,
                         httpsUserName_,
                         httpsPassword_):
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
    with open('tmc_proxy.yaml', 'w') as outfile:
        yaml1 = ryaml.YAML()
        yaml1.indent(mapping=2, sequence=4, offset=2)
        yaml1.dump(data, outfile)

def checkClusterStateOnTmc(cluster, ifManagement):
    try:
        if ifManagement:
            clist = ["tmc", "managementcluster", "get", cluster]
        else:
            li_ = returnListOfTmcCluster(cluster)
            clist = ["tmc", "cluster", "get", li_[0], "-m", li_[1], "-p", li_[2]]
        o = runShellCommandAndReturnOutput(clist)
        if o[1] == 0:
            l = yaml.safe_load(o[0])
            try:
                status = str(l["status"]["conditions"]["Agent-READY"]["status"])
            except:
                status = str(l["status"]["conditions"]["READY"]["status"])
            try:
                typen = str(l["status"]["conditions"]["Agent-READY"]["type"])
            except:
                typen = str(l["status"]["conditions"]["READY"]["type"])
            health = str(l["status"]["health"])
            if status == "TRUE":
                logger.info("Management cluster status " + status)
            else:
                logger.error("Management cluster status " + status)
                return "Failed", 500
            if typen == "READY":
                logger.info("Management cluster type " + typen)
            else:
                logger.error("Management cluster type " + typen)
                return "Failed", 500
            if health == "HEALTHY":
                logger.info("Management cluster health " + health)
            else:
                logger.error("Management cluster health " + health)
                return "Failed", 500
            return "SUCCESS", 200
        else:
            return None, o[0]
    except Exception as e:
        return None, str(e)

def checkTmcRegister(cluster, ifManagement):
    try:
        if ifManagement:
            nlist = ["tmc", "managementcluster", "list"]
        else:
            nlist = ["tmc", "cluster", "list"]
        o = runShellCommandAndReturnOutput(nlist)
        if o[0].__contains__(cluster):
            logger.info("here ")
            state = checkClusterStateOnTmc(cluster, ifManagement)
            if state[0] == "SUCCESS":
                return True
            else:
                return False
        else:
            return False
    except:
        return False

def registerWithTmcOnSharedAndWorkload(jsonspec, clusterName, cls_type):
    try:

        if not checkTmcRegister(clusterName, False):
            file = "kubeconfig_cluster.yaml"
            os.system("rm -rf " + file)
            os.putenv("TMC_API_TOKEN", jsonspec['envSpec']["saasEndpoints"]['tmcDetails']['tmcRefreshToken'])
            user = TmcUser.USER_VSPHERE
            listOfCmdTmcLogin = ["tmc", "login", "--no-configure", "-name", user]
            runProcess(listOfCmdTmcLogin)
            logger.info("Registering to tmc on cluster " + clusterName)
            tmc_command = ["tanzu", "cluster", "kubeconfig", "get", clusterName, "--admin", "--export-file",
                           file]
            runProcess(tmc_command)
            logger.info("Got kubeconfig successfully")
            logger.info("Attaching cluster to tmc")
            listOfCommandAttach = ["tmc", "cluster", "attach", "--name", clusterName, "--cluster-group", "default",
                                       "-k", file, "--force"]
            try:
                runProcess(listOfCommandAttach)
            except:
                d = {
                    "responseType": "ERROR",
                    "msg": "Filed to attach " + clusterName + "  to tmc",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            d = {
                "responseType": "SUCCESS",
                "msg": clusterName + " cluster attached to tmc successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        else:
            d = {
                "responseType": "SUCCESS",
                "msg": clusterName + " Cluster is already attached to tmc",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Tmc registration failed on cluster " + clusterName + " " + str(e),
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

def checkToEnabled(to_enable):
    try:
        if str(to_enable).lower() == "true":
            return True
        else:
            return False
    except:
        return False

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

def switchToManagementContext(clusterName):
    commands_shared = ["tanzu", "management-cluster", "kubeconfig", "get", clusterName, "--admin"]
    kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand_shared is None:
        logger.error("Failed get admin cluster context of cluster " + clusterName)
        d = {
            "responseType": "ERROR",
            "msg": "Failed get admin cluster context of cluster " + clusterName,
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
    if status[1] != 0:
        logger.error("Failed to switch to" + clusterName + "cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to switch to " + clusterName + " cluster context " + str(status[0]),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

    logger.info("Switched to " + clusterName + " context")
    d = {
        "responseType": "ERROR",
        "msg": "Switched to " + clusterName + " context",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200

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
            logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    except Exception as e:
        logger.error(" Failed to verify pod running ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to verify pod running",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500, count_cert
    if not running:
        logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500, count_cert
    d = {
        "responseType": "ERROR",
        "msg": "Successfully running " + podName + " ",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200, count_cert

def createContourDataValues():
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
    with open('./contour-data-values.yaml', 'w') as outfile:
        outfile.write("---\n")
        yaml1 = ryaml.YAML()
        yaml1.indent(mapping=2, sequence=4, offset=3)
        yaml1.dump(data, outfile)

def installExtentionFor14():
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    service = 'all'
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
                return json.dumps(d), 500
            logger.info("Installing cert manager - " + state)
            install_command = ["tanzu", "package", "install", AppName.CERT_MANAGER, "--package-name",
                               "cert-manager.tanzu.vmware.com", "--namespace", "package-" + AppName.CERT_MANAGER,
                               "--version", state,
                               "--create-namespace"]
            states = runShellCommandAndReturnOutputAsList(install_command)
            if states[1] != 0:
                logger.error(
                    AppName.CERT_MANAGER + " installation command failed. Checking for reconciliation status..")
            certManagerStatus = waitForGrepProcessWithoutChangeDir(main_command, sub_command, AppName.CERT_MANAGER,
                                                                   RegexPattern.RECONCILE_SUCCEEDED)
            if certManagerStatus[1] == 500:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to bring certmanager " + str(certManagerStatus[0].json['msg']),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            logger.info("Configured Cert manager successfully")
            if service != "all":
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Configured Cert manager successfully",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200
        else:
            logger.info("Cert manager is already running")
            if service != "all":
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Cert manager is already running",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200
    if service == "ingress" or service == "all":

        sub_command = ["grep", AppName.CONTOUR]
        command_cert = grabPipeOutput(main_command, sub_command)
        if not verifyPodsAreRunning(AppName.CONTOUR, command_cert[0], RegexPattern.RECONCILE_SUCCEEDED):
            createContourDataValues()
            state = getVersionOfPackage("contour.tanzu.vmware.com")
            if state is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Version of package contour.tanzu.vmware.com",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            logger.info("Installing contour - " + state)
            install_command = ["tanzu", "package", "install", AppName.CONTOUR, "--package-name",
                               "contour.tanzu.vmware.com", "--version", state, "--values-file",
                               "./contour-data-values.yaml", "--namespace", "package-tanzu-system-contour",
                               "--create-namespace"]
            states = runShellCommandAndReturnOutputAsList(install_command)
            if states[1] != 0:
                for r in states[0]:
                    logger.error(r)
                logger.info(
                    AppName.CONTOUR + " install command failed. Checking for reconciliation status...")
            certManagerStatus = waitForGrepProcessWithoutChangeDir(main_command, sub_command, AppName.CONTOUR,
                                                                   RegexPattern.RECONCILE_SUCCEEDED)
            if certManagerStatus[1] == 500:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to bring contour " + str(certManagerStatus[0].json['msg']),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if service != "all":
                logger.info("Contour deployed and is up and running")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Contour deployed and is up and running",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200
        else:
            logger.info("Contour is already up and running")
            d = {
                "responseType": "SUCCESS",
                "msg": "Contour is already up and running",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured cert-manager and contour extensions successfully",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200


def getClusterID(vCenter, vCenter_user, VC_PASSWORD, cluster):
    url = "https://" + vCenter + "/"
    try:
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            d = {
                "reponseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        else:
            session_id = sess.json()['value']

        clusterID_resp = requests.get(url + "api/vcenter/cluster?names=" + cluster, verify=False, headers={
            "vmware-api-session-id": session_id
        })
        if clusterID_resp.status_code != 200:
            logger.error(clusterID_resp.json())
            d = {
                "reponseType": "ERROR",
                "msg": "Failed to fetch cluster ID for cluster - " + cluster,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        return clusterID_resp.json()[0]['cluster'], 200

    except Exception as e:
        logger.error(e)
        d = {
            "reponseType": "ERROR",
            "msg": "Failed to fetch cluster ID for cluster - " + cluster,
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

def switchToContext(clusterName):

    commands_shared = ["tanzu", "cluster", "kubeconfig", "get", clusterName, "--admin"]
    kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
    if kubeContextCommand_shared is None:
        logger.error("Failed get admin cluster context of cluster " + clusterName)
        d = {
            "responseType": "ERROR",
            "msg": "Failed get admin cluster context of cluster " + clusterName,
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
    status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
    if status[1] != 0:
        logger.error("Failed to switch to" + clusterName + "cluster context " + str(status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to switch to " + clusterName + " cluster context " + str(status[0]),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

    logger.info("Switched to " + clusterName + " context")
    d = {
        "responseType": "ERROR",
        "msg": "Switched to " + clusterName + " context",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200

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
            logger.info("Tanzu " + sas + " is not integrated")
            return False
        else:
            if pr:
                logger.error(o[0])
                return False
        l = yaml.safe_load(o[0])
        integration = str(l["status"]["integrationWorkload"])
        if integration != "OK":
            logger.info("integrationWorkload status " + integration)
            return False
        else:
            logger.info("integrationWorkload status " + integration)
        tmcAdapter = str(l["status"]["tmcAdapter"])
        if tmcAdapter != "OK":
            logger.info("tmcAdapter status " + tmcAdapter)
            return False
        else:
            logger.info("tmcAdapter status " + tmcAdapter)
        return True
    except Exception as e:
        if pr:
            logger.error(str(e))
        return False

def checkTmcEnabled(tmc_state):

    if tmc_state.lower() == "true":
        return True
    else:
        return False

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
            "configurations": {
                "enableNamespaceExclusions": True,
                "namespaceExclusions": [
                    {
                        "match": exact,
                        "type": "EXACT"
                    },
                    {
                        "match": partial,
                        "type": "START_WITH"
                    }
                ]
            }
        }
    }
    os.system("rm -rf " + fileName)
    with open(fileName, 'w') as f:
        json.dump(tsmJson, f)

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
        logger.info("Waited for  " + str(count_cert * 30) + "s, retrying.")
    if not running:
        logger.error(podName + " is not running on waiting " + str(count_cert * 30) + "s")
        d = {
            "responseType": "ERROR",
            "msg": podName + " is not running on waiting " + str(count_cert * 30) + "s",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500, count_cert
    logger.info("Successfully running " + podName)
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully running" + podName,
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200, count_cert

def integrateSas(cluster_name, jsonspec, sasType):
    vcenter_ip = jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
    vcenter_username = jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
    str_enc = str(jsonspec['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
    base64_bytes = str_enc.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password = enc_bytes.decode('ascii').rstrip("\n")
    cluster = jsonspec["envSpec"]["vcenterDetails"]["vcenterCluster"]
    command = ["tmc", "managementcluster", "list"]
    output = runShellCommandAndReturnOutputAsList(command)
    if output[1] != 0:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to fetch management cluster list",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    logger.info(output[0])
    if cluster_name in output[0]:
        d = {
            "responseType": "ERROR",
            "msg": "Tanzu " + sasType + " registration is not supported on management cluster",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    context = switchToContext(cluster_name)
    if context[1] != 200:
        return context[0], context[1]
    li_ = returnListOfTmcCluster(cluster_name)
    if not isSasRegistred(cluster_name, li_[1], li_[2], False, sasType):
        logger.info("Registering to tanzu " + sasType)
        tmc_state = jsonspec['envSpec']["saasEndpoints"]['tmcDetails']['tmcAvailability']
        if not checkTmcEnabled(tmc_state):
            d = {
                "responseType": "ERROR",
                "msg": "Tmc is not enabled, tmc must be enabled to register tanzu " + sasType,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        if sasType == SAS.TO:
            fileName = "to_json.json"
            toUrl = jsonspec["envSpec"]["saasEndpoints"]["tanzuObservabilityDetails"]["tanzuObservabilityUrl"]
            toToken = jsonspec["envSpec"]["saasEndpoints"]["tanzuObservabilityDetails"]["tanzuObservabilityRefreshToken"]
            generateToJsonFile(li_[1], li_[2], cluster_name, toUrl, toToken)
        elif sasType == SAS.TSM:
            fileName = "tsm_json.json"
            exact = jsonspec['tkgWorkloadComponents']["namespaceExclusions"]["exactName"]
            partial = jsonspec['tkgWorkloadComponents']["namespaceExclusions"]["startsWith"]
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
            logger.info("waited for " + str(count*10) + "s for registration to complete... retrying")
        if not registered:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to register tanzu " + sasType + " to " + cluster_name,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Tanzu " + sasType + " is integrated successfully to cluster " + cluster_name,
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200
    else:
        d = {
            "responseType": "SUCCESS",
            "msg": "Tanzu " + sasType + " is already registered to " + cluster_name,
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200


def registerTSM(cluster_name, jsonspec, size):
    try:
        if size.lower() == "medium" or size.lower() == "small":
            d = {
                "responseType": "ERROR",
                "msg": "Tanzu service mesh integration is not supported on cluster size small or medium",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        st = integrateSas(cluster_name, jsonspec, SAS.TSM)
        return st[0], st[1]
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to register Tanzu Service Mesh " + str(e),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

def registerTanzuObservability(cluster_name, to_enable, size, jsonspec):
    try:

        if checkToEnabled(to_enable):
            if size.lower() == "medium" or size.lower() == "small":
                d = {
                    "responseType": "ERROR",
                    "msg": "Tanzu Observability integration is not supported on cluster size small or medium",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            logger.info('Starting Tanzu Observability Integration')
            st = integrateSas(cluster_name, jsonspec, SAS.TO)
            return st[0].json, st[1]
        else:
            d = {
                "responseType": "SUCCESS",
                "msg": "Taznu observability is disabled",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
    except Exception as e:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to register tanzu Observability " + str(e),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

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


def checkAirGappedIsEnabled(env, jsonspec):
    if env == Env.VMC:
        air_gapped = ""
    else:
        try:
            air_gapped = jsonspec['envSpec']['customRepositorySpec'][
                'tkgCustomImageRepository']
        except:
            return False
    if not air_gapped.lower():
        return False
    else:
        return True

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
        logger.error("Failed to run get version list is empty")
        return None
    version = None
    for li in list_h:
        if li.__contains__(str(max(release_dates))):
            version = li.split(" ")[4]
            break
    if version is None or not version:
        logger.error("Failed to get version string is empty")
        return None
    return version


def isClusterRunning(vcenter_ip, vcenter_username, password, cluster, workload_name, jsonspec):
    try:
        logger.info("Check if cluster is in running state - " + workload_name)

        cluster_id = getClusterID(vcenter_ip, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            logger.error(cluster_id[0])
            d = {
                "responseType": "ERROR",
                "msg": cluster_id[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        cluster_id = cluster_id[0]

        wcp_status = isWcpEnabled(cluster_id)
        if wcp_status[0]:
            endpoint_ip = wcp_status[1]['api_server_cluster_endpoint']
        else:
            logger.error("WCP not enabled on given cluster - " + cluster)
            d = {
                "responseType": "ERROR",
                "msg": "WCP not enabled on given cluster - " + cluster,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        logger.info("logging into cluster - " + endpoint_ip)
        os.putenv("KUBECTL_VSPHERE_PASSWORD", password)
        connect_command = ["kubectl", "vsphere", "login", "--server=" + endpoint_ip,
                           "--vsphere-username=" + vcenter_username,
                           "--insecure-skip-tls-verify"]
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            logger.error("Failed while connecting to Supervisor Cluster ")
            d = {
                "responseType": "ERROR",
                "msg": "Failed while connecting to Supervisor Cluster",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        switch_context = ["kubectl", "config", "use-context", endpoint_ip]
        output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            logger.error("Failed to use  context " + str(output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to use  context " + str(output[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        name_space = jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
        get_cluster_command = ["kubectl", "get", "tkc", "-n", name_space]
        clusters_output = runShellCommandAndReturnOutputAsList(get_cluster_command)
        if clusters_output[1] != 0:
            logger.error("Failed to fetch cluster running status " + str(clusters_output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch cluster running status " + str(clusters_output[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        index = None
        for item in range(len(clusters_output[0])):
            if clusters_output[0][item].split()[0] == workload_name:
                index = item
                break

        if index is None:
            logger.error("Unable to find cluster - " + workload_name)
            d = {
                "responseType": "ERROR",
                "msg": "Unable to find cluster - " + workload_name,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        output = clusters_output[0][index].split()
        if not ((output[5] == "True" or output[5] == "running") and output[6] == "True"):
            logger.error("Failed to fetch workload cluster running status " + str(clusters_output[0]))
            logger.error("Found below Cluster status - ")
            logger.error("READY: " + str(output[5]) + " and TKR COMPATIBLE: " + str(output[6]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch workload cluster running status " + str(clusters_output[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "Workload cluster is in running status.",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200
    except Exception as e:
        logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching the status of workload cluster",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

def isWcpEnabled(cluster_id, jsonspec):
    vcenter_ip = jsonspec['envSpec']['vcenterDetails']['vcenterAddress']
    vcenter_username = jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser']
    str_enc = str(jsonspec['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
    base64_bytes = str_enc.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password = enc_bytes.decode('ascii').rstrip("\n")
    if not (vcenter_ip or vcenter_username or password):
        return False, "Failed to fetch VC details"

    sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                         auth=(vcenter_username, password), verify=False)
    if sess.status_code != 200:
        logger.error("Connection to vCenter failed")
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



def connect_to_workload(vCenter, vcenter_username, password, cluster, workload_name, jsonspec):
    try:
        logger.info("Connecting to workload cluster...")
        cluster_id = getClusterID(vCenter, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            logger.error(cluster_id[0])
            return None, cluster_id[0].json['msg']

        cluster_namespace = jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
        cluster_id = cluster_id[0]
        wcp_status = isWcpEnabled(cluster_id, jsonspec)
        if wcp_status[0]:
            endpoint_ip = wcp_status[1]['api_server_cluster_endpoint']
        else:
            return None, "Failed to obtain cluster endpoint IP on given cluster - " + workload_name
        logger.info("logging into cluster - " + endpoint_ip)
        os.putenv("KUBECTL_VSPHERE_PASSWORD", password)
        connect_command = ["kubectl", "vsphere", "login", "--vsphere-username", vcenter_username, "--server",
                           endpoint_ip,
                           "--tanzu-kubernetes-cluster-name", workload_name, "--tanzu-kubernetes-cluster-namespace",
                           cluster_namespace, "--insecure-skip-tls-verify"]
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            logger.error(output[0])
            return None, "Failed to login to cluster endpoint - " + endpoint_ip

        switch_context = ["kubectl", "config", "use-context", workload_name]
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            logger.error(context_output[0])
            return None, "Failed to login to cluster context - " + workload_name
        return "SUCCESS", "Successfully connected to workload cluster"
    except Exception as e:
        return None, "Exception occurred while connecting to workload cluster"
        
def verifyCluster(cluster_name):
    podRunninng = ["tanzu", "cluster", "list", "--include-management-cluster"]
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if not verifyPodsAreRunning(cluster_name, command_status[0], RegexPattern.running):
        return False
    else:
        return True

def checkRepositoryAdded(env, jsonspec):
    if checkAirGappedIsEnabled(env, jsonspec):
        try:
            validate_command = ["tanzu", "package", "repository", "list", "-A"]

            status = runShellCommandAndReturnOutputAsList(validate_command)
            if status[1] != 0:
                logger.error("Failed to run validate repository added command " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to run validate repository added command " + str(str[0]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            REPOSITORY_URL = jsonspec['envSpec']['customRepositorySpec'][
                'tkgCustomImageRepository']
            REPOSITORY_URL = str(REPOSITORY_URL).replace("https://", "").replace("http://", "")
            if not str(status[0]).__contains__(REPOSITORY_URL):
                list_command = ["tanzu", "package", "repository", "add", Repo.NAME, "--url", REPOSITORY_URL, "-n",
                                "tkg-custom-image-repository", "--create-namespace"]
                status = runShellCommandAndReturnOutputAsList(list_command)
                if status[1] != 0:
                    logger.error("Failed to run command to add repository " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run command to add repository " + str(str[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                status = runShellCommandAndReturnOutputAsList(validate_command)
                if status[1] != 0:
                    logger.error("Failed to run validate repository added command " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run validate repository added command " + str(str[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            else:
                logger.info(REPOSITORY_URL + " is already added")
            logger.info("Successfully  added repository " + REPOSITORY_URL)
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully  added repository " + REPOSITORY_URL,
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to add repository " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    else:
        try:
            validate_command = ["tanzu", "package", "repository", "list", "-n", TKG_Package_Details.NAMESPACE]
            status = runShellCommandAndReturnOutputAsList(validate_command)
            if status[1] != 0:
                logger.error("Failed to run validate repository added command " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to run validate repository added command " + str(str[0]),
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            if not str(status[0]).__contains__(TKG_Package_Details.STANDARD_PACKAGE_URL):
                list_command = ["tanzu", "package", "repository", "add", TKG_Package_Details.REPO_NAME, "--url",
                                TKG_Package_Details.REPOSITORY_URL, "-n",
                                TKG_Package_Details.NAMESPACE]
                status = runShellCommandAndReturnOutputAsList(list_command)
                if status[1] != 0:
                    logger.error("Failed to run command to add repository " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run command to add repository " + str(str[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                status = runShellCommandAndReturnOutputAsList(validate_command)
                if status[1] != 0:
                    logger.error("Failed to run validate repository added command " + str(status[0]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to run validate repository added command " + str(str[0]),
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
            else:
                logger.info(TKG_Package_Details.REPOSITORY_URL + " is already added")
            logger.info("Successfully  added repository " + TKG_Package_Details.REPOSITORY_URL)
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully validated repository " + TKG_Package_Details.REPOSITORY_URL,
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        except Exception as e:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to validate tanzu standard repository status" + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500



def installCertManagerAndContour(env, cluster_name, repo_address, service_name, jsonspec):
    podRunninng = ["tanzu", "cluster", "list", "--include-management-cluster"]
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if not verifyPodsAreRunning(cluster_name, command_status[0], RegexPattern.running):
        logger.error(cluster_name + " is not deployed")
        d = {
            "responseType": "ERROR",
            "msg": cluster_name + " is not deployed",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    if TkgUtil.isEnvTkgs_ns(jsonspec) or TkgUtil.isEnvTkgs_wcp(jsonspec):
        mgmt = jsonspec['envSpec']["saasEndpoints"]['tmcDetails']['tmcSupervisorClusterName']
    else:
        mgmt = getManagementCluster()
        if mgmt is None:
            logger.error("Failed to get management cluster")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get management cluster",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    if str(mgmt).strip() == cluster_name.strip():
        switch = switchToManagementContext(cluster_name.strip())
        if switch[1] != 200:
            logger.info(switch[0].json['msg'])
            d = {
                "responseType": "ERROR",
                "msg": switch[0].json['msg'],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    else:
        if TkgUtil.isEnvTkgs_ns(jsonspec):
            name_space = jsonspec['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
            commands_shared = ["tanzu", "cluster", "kubeconfig", "get", cluster_name, "--admin", "-n", name_space]
        else:
            commands_shared = ["tanzu", "cluster", "kubeconfig", "get", cluster_name, "--admin"]
        kubeContextCommand_shared = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kubeContextCommand_shared is None:
            logger.error("Failed to get switch to " + cluster_name + " cluster context command")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to " + cluster_name + " context command",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        lisOfSwitchContextCommand_shared = str(kubeContextCommand_shared).split(" ")
        status = runShellCommandAndReturnOutputAsList(lisOfSwitchContextCommand_shared)
        if status[1] != 0:
            logger.error("Failed to get switch to shared cluster context " + str(status[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get switch to " + cluster_name + " context " + str(status[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
   
    if Tkg_version.TKG_VERSION == "1.5":
        status_ = checkRepositoryAdded(env, jsonspec)
        if status_[1] != 200:
            logger.error(str(status_[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": str(status_[0].json['msg']),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        install = installExtentionFor14(service_name, cluster_name, env)
        if install[1] != 200:
            return install[0], install[1]
    logger.info("Configured cert-manager and contour successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured cert-manager and contour extensions successfully",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200

def loadBomFile():
    try:
        with open(Extentions.BOM_LOCATION_14, "r") as stream:
            try:
                data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                logger.error("Failed to find key " + str(exc))
                return None
            return data
    except Exception as e:
        logger.error("Failed to read bom file " + str(e))
        return None


def updateDataFile(fluent_endpoint, dataFile, jsonspec):
    try:
        output_str = None
        if fluent_endpoint == Tkg_Extention_names.FLUENT_BIT_HTTP:
            host = jsonspec['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointAddress']
            port = jsonspec['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointPort']
            uri = jsonspec['tanzuExtensions']['logging']['httpEndpoint']['httpEndpointUri']
            header = jsonspec['tanzuExtensions']['logging']['httpEndpoint'][
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
            host = jsonspec['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointAddress']
            port = jsonspec['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointPort']
            mode = jsonspec['tanzuExtensions']['logging']['syslogEndpoint']['syslogEndpointMode']
            format = jsonspec['tanzuExtensions']['logging']['syslogEndpoint'][
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
            broker = jsonspec['tanzuExtensions']['logging']['kafkaEndpoint'][
                'kafkaBrokerServiceName']
            topic = jsonspec['tanzuExtensions']['logging']['kafkaEndpoint']['kafkaTopicName']
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
            logger.error("Provided endpoint is not supported by SIVT - " + fluent_endpoint)
            return False

        logger.info("Printing " + fluent_endpoint + " endpoint details ")
        logger.info(output_str)
        inject_sc = ["sh", "./common/injectValue.sh", dataFile, "inject_output_fluent", output_str.strip()]
        inject_sc_response = runShellCommandAndReturnOutput(inject_sc)
        if inject_sc_response[1] == 500:
            logger.error("Command to update output endpoint failed")
            return False
        return True

    except Exception as e:
        logger.error(str(e))
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
        logger.error("Exception occurred while creating directory - " + Paths.CLUSTER_PATH + clusterName)
        return False

def deploy_fluent_bit(end_point, cluster, jsonspec):
    try:
        logger.info("Deploying Fluent-bit extension on cluster - " + cluster)
        if not createClusterFolder(cluster):
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + cluster,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        copy_template_command = ["cp", Paths.VSPHERE_FLUENT_BIT_YAML, Paths.CLUSTER_PATH + cluster]
        copy_output = runShellCommandAndReturnOutputAsList(copy_template_command)
        if copy_output[1] != 0:
            logger.error("Failed to copy template file to : " + Paths.CLUSTER_PATH + cluster)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to copy template file to : " + Paths.CLUSTER_PATH + cluster,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        yamlFile = Paths.CLUSTER_PATH + cluster + "/fluent_bit_data_values.yaml"
        namespace = "package-tanzu-system-logging"
        update_response = updateDataFile(end_point, yamlFile, jsonspec)
        if not update_response:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to update data values file",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        version = getVersionOfPackage(Tkg_Extention_names.FLUENT_BIT.lower() + ".tanzu.vmware.com")
        if version is None:
            logger.error("Failed Capture the available Prometheus version")
            d = {
                "responseType": "ERROR",
                "msg": "Capture the available Prometheus version",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        deploy_fluent_bit_command = ["tanzu", "package", "install", Tkg_Extention_names.FLUENT_BIT.lower(),
                                     "--package-name", Tkg_Extention_names.FLUENT_BIT.lower() + ".tanzu.vmware.com",
                                     "--version", version, "--values-file", yamlFile, "--namespace", namespace,
                                     "--create-namespace"]
        state_extention_apply = runShellCommandAndReturnOutputAsList(deploy_fluent_bit_command)
        if state_extention_apply[1] != 0:
           logger.error(Tkg_Extention_names.FLUENT_BIT.lower() + " install command failed. "
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
            logger.info("Waited for  " + str(count * 30) + "s, retrying.")

        if found:
            d = {
                "responseType": "SUCCESS",
                "msg": "Fluent-bit installation completed successfully",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        else:
            logger.error("Fluent-bit deployment is not completed even after " + str(count * 30) + "s wait")
            d = {
                "responseType": "ERROR",
                "msg": "Fluent-bit installation failed",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    except Exception as e:
        logger.error("Exception occurred while deploying fluent-bit - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while deploying fluent-bit - " + str(e),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500


def fluent_bit_enabled(env, jsonspec):
    if TkgUtil.isEnvTkgs_ns(jsonspec) or env == Env.VSPHERE or env == Env.VMC:
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
        logger.error("Wrong env type provided for Fluent bit installation")
        return False, None


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