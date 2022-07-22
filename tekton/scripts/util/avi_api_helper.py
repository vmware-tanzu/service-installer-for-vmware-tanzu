#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import json
import os
import time
from pathlib import Path
from util import cmd_runner
import base64
import requests
import urllib3
from util.ShellHelper import runProcess
from constants.api_payloads import AlbPayload
from constants.constants import ControllerLocation, MarketPlaceUrl, AviSize, CertName, Avi_Version, Versions
from constants.alb_api_constants import AlbPayload, AlbEndpoint
from util.cmd_helper import CmdHelper
from util.logger_helper import LoggerHelper
from util.govc_client import GovcClient
from util.replace_value import replaceValueSysConfig, replaceCertConfig
from util.vcenter_operations import verifyVcenterVersion
from util.tkg_util import TkgUtil

logger = LoggerHelper.get_logger(Path(__file__).stem)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Reference: https://github.com/vmware/alb-sdk/blob/eng/python/avi/sdk/README.md


class AviApiSpec:
    params = dict()
    """Ref:
        https://docs.ansible.com/ansible/latest/collections/community/network/avi_api_version_module.html#ansible-collections-community-network-avi-api-version-module
    """

    def __init__(
            self,
            ip,
            username="admin",
            password="58NFaGDJm(PJH0G",
            api_version="16.4.4",
            tenant="",
            tenant_uuid="",
            token="",
            session_id="",
            csrftoken="",
    ) -> None:
        self.params = dict(
            controller=ip,
            username=username,
            password=password,
            old_password="58NFaGDJm(PJH0G",
            api_version=api_version,
            tenant=tenant,
            tenant_uuid=tenant_uuid,
            port=None,
            timeout=300,
            token=token,
            session_id=session_id,
            csrftoken=csrftoken,
        )

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

def pushAviToContenLibraryMarketPlace(jsonspec):
    rcmd = cmd_runner.RunCmd()
    try:
        find_command = "govc library.ls /{}/".format(ControllerLocation.CONTROLLER_CONTENT_LIBRARY)
        logger.info('Running find for existing library')
        output = rcmd.run_cmd_output(find_command)
        logger.info('Library found: {}'.format(output))
        if str(output).__contains__(ControllerLocation.CONTROLLER_NAME):
            logger.info("Avi controller is already present in content library")
            return "SUCCESS", 200
    except:
        pass
    my_file = Path("/tmp/" + ControllerLocation.CONTROLLER_NAME + ".ova")
    data_center = jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
    data_store = jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
    reftoken = jsonspec['envSpec']['marketplaceSpec']['refreshToken']
    avi_version = ControllerLocation.VSPHERE_AVI_VERSION
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "refreshToken": reftoken
    }
    json_object = json.dumps(payload, indent=4)
    sess = requests.request("POST", MarketPlaceUrl.URL + "/api/v1/user/login", headers=headers,
                            data=json_object, verify=False)
    logger.info('Session details: {}'.format(sess.status_code))
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
        logger.info("Avi ova is already downloaded")
    else:
        logger.info("Downloading avi controller from MarketPlace")
        slug = "true"
        _solutionName = getProductSlugId(MarketPlaceUrl.AVI_PRODUCT, headers)
        logger.info('Solution name from marketplace: {}'.format(_solutionName))
        if _solutionName[0] is None:
            return None, "Failed to find product on Marketplace " + str(_solutionName[1])
        solutionName = _solutionName[0]
        product = requests.get(MarketPlaceUrl.API_URL + "/products/" +
                               solutionName + "?isSlug=" + slug + "&ownorg=false", headers=headers,
                               verify=False)
        if product.status_code != 200:
            return None, "Failed to Obtain Product ID"
        else:
            ls = []
            product_id = product.json()['response']['data']['productid']
            logger.info('Product ID: {}'.format(product_id))
            for metalist in product.json()['response']['data']['productdeploymentfilesList']:
                if metalist["appversion"] == avi_version:
                    objectid = metalist['fileid']
                    filename = metalist['name']
                    ls.append(filename)
                    logger.info('filename: {}'.format(filename))
                    logger.info("obj id: {objectid} filename: {filename} avi_version: {avi_version}".format(objectid=objectid,
                                                                                 filename=filename,
                                                                                 avi_version=avi_version))
                    logger.info("PRODUCT ID: {product_id}".format(product_id=product_id))
                    break
        payload = {
            "deploymentFileId": objectid,
            "eulaAccepted": "true",
            "productId": product_id
        }

        json_object = json.dumps(payload, indent=4).replace('\"true\"', 'true')
        logger.info('header: {}'.format(headers))
        logger.info('data: {}'.format(json_object))
        presigned_url = requests.request("POST",
                                         MarketPlaceUrl.URL + "/api/v1/products/" + product_id + "/download",
                                         headers=headers, data=json_object, verify=False)
        if presigned_url.status_code != 200:
            logger.error('Error on request. Code: {}\n Error: {}'.format(presigned_url.status_code,
                                                                         presigned_url.text))
            return None, "Failed to obtain pre-signed URL"
        else:
            download_url = presigned_url.json()["response"]["presignedurl"]

        curl_inspect_cmd = 'curl -I -X GET {} --output /tmp/resp.txt'.format(download_url)
        rcmd.run_cmd_only(curl_inspect_cmd)
        with open('/tmp/resp.txt', 'r') as f:
            data_read = f.read()
        if 'HTTP/1.1 200 OK' in data_read:
            logger.info('Proceed to Download')
            ova_path = "/tmp/" + ControllerLocation.CONTENT_LIBRARY_OVA_NAME + ".ova"
            curl_download_cmd = 'curl -X GET {d_url} --output {tmp_path}'.format(d_url=download_url,
                                                                                 tmp_path=ova_path)
            rcmd.run_cmd_only(curl_download_cmd)
        else:
            logger.info('Error in presigned url/key: {} '.format(data_read.split('\n')[0]))
            return None, "Invalid key/url"
        logger.info("Avi ova downloaded  at location: {}".format(ova_path))

    find_command = "govc library.ls"
    output = rcmd.run_cmd_output(find_command)
    if str(output).__contains__(ControllerLocation.CONTROLLER_CONTENT_LIBRARY):
        logger.info(ControllerLocation.CONTROLLER_CONTENT_LIBRARY + " is already present")
    else:
        find_command = "govc library.create -ds={ds} -dc={dc} {libraryname}".format(ds=data_store,
                                                                                    dc=data_center,
                                                                                    libraryname=ControllerLocation.CONTROLLER_CONTENT_LIBRARY)
        output = rcmd.run_cmd_output(find_command)
        if 'error' in output:
            return None, "Failed to create content library"
    find_command = ["govc", "library.ls", "/" + ControllerLocation.CONTROLLER_CONTENT_LIBRARY + "/"]
    output = rcmd.runShellCommandAndReturnOutputAsList(find_command)
    if output[1] != 0:
        return None, "Failed to find items in content library"
    if str(output[0]).__contains__(ControllerLocation.CONTROLLER_NAME):
        logger.info("Avi controller is already present in content library")
    else:
        logger.info("Pushing Avi controller to content library")
        import_command = ["govc", "library.import", ControllerLocation.CONTROLLER_CONTENT_LIBRARY,
                          ova_path]
        output = rcmd.runShellCommandAndReturnOutputAsList(import_command)
        if output[1] != 0:
            return None, "Failed to upload avi controller to content library"
    return "SUCCESS", 200

def downloadAviControllerAndPushToContentLibrary(vcenter_ip, vcenter_username, password, jsonspec):
    try:
        os.putenv("GOVC_URL", "https://" + vcenter_ip + "/sdk")
        os.putenv("GOVC_USERNAME", vcenter_username)
        os.putenv("GOVC_PASSWORD", password)
        os.putenv("GOVC_INSECURE", "true")
        rcmd = cmd_runner.RunCmd()
        logger.info('Check if library is already present')
        VC_Content_Library_name = jsonspec['envSpec']['vcenterDetails']["contentLibraryName"]
        VC_AVI_OVA_NAME = jsonspec['envSpec']['vcenterDetails']["aviOvaName"]
        find_command = ["govc", "library.ls", "/" + VC_Content_Library_name + "/"]
        output = rcmd.runShellCommandAndReturnOutputAsList(find_command)
        if str(output[0]).__contains__(VC_Content_Library_name):
            logger.info(VC_Content_Library_name + " is already present")
        else:
            logger.info(VC_Content_Library_name + " is not present in the content library")
            res = pushAviToContenLibraryMarketPlace(jsonspec)
            logger.info("State of AVI Content library: {}".format(res))
        find_command = ["govc", "library.ls", "/" + VC_Content_Library_name + "/"]
        output = rcmd.runShellCommandAndReturnOutputAsList(find_command)
        if output[1] != 0:
            return None, "Failed to find items in content library"
        if str(output[0]).__contains__(VC_AVI_OVA_NAME):
            logger.info(VC_AVI_OVA_NAME + " avi controller is already present in content library")
        else:
            logger.error(VC_AVI_OVA_NAME + " need to be present in content library for internet"
                                           "restricted env, please push avi "
                                           "controller to content library.")
            return None, VC_AVI_OVA_NAME + " not present in the content library " + VC_Content_Library_name
        return "SUCCESS", 200
    except Exception as e:
        return None, str(e)

def isAviHaEnabled(hafield):
    try:
        enable_avi_ha = hafield
        if str(enable_avi_ha).lower() == "true":
            return True
        else:
            return False
    except:
        return False

def ra_avi_download(jsonspec):

    vcenter = jsonspec['envSpec']['vcenterDetails']["vcenterAddress"]
    vcenter_user = jsonspec['envSpec']['vcenterDetails']["vcenterSsoUser"]
    vcpass_base64 = jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']
    vcpass = CmdHelper.decode_base64(vcpass_base64)
    refresh_token = jsonspec['envSpec']['marketplaceSpec']['refreshToken']
    os.putenv("GOVC_URL", "https://" + vcenter + "/sdk")
    os.putenv("GOVC_USERNAME", vcenter_user)
    os.putenv("GOVC_PASSWORD", vcpass)
    os.putenv("GOVC_INSECURE", "true")
    if not refresh_token:
        logger.info("refreshToken not provided")
        rcmd = cmd_runner.RunCmd()
        logger.info('Check if library is already present')
        VC_Content_Library_name = jsonspec['envSpec']['vcenterDetails']["contentLibraryName"]
        VC_AVI_OVA_NAME = jsonspec['envSpec']['vcenterDetails']["aviOvaName"]
        logger.debug("VC OVA targetted: {}".format(VC_AVI_OVA_NAME))
        find_command = ["govc", "library.ls", "/" + VC_Content_Library_name + "/"]
        output = rcmd.runShellCommandAndReturnOutputAsList(find_command)
        if str(output[0]).__contains__(VC_Content_Library_name):
            logger.info(VC_Content_Library_name + " is already present")
            return True
        else:
            logger.info(VC_Content_Library_name + " is not present in the content library")
            return False
    else:
        logger.info("Fetching ALB..")
        down = downloadAviControllerAndPushToContentLibrary(vcenter, vcenter_user, vcpass, jsonspec)
        if down[0] is None:
            logger.error('Error encountered in fetching avi')
            return False
        return True

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
        logger.info("Waited for  " + str(count * 10) + "s, retrying.")
        time.sleep(10)
    if response_login is not None:
        if response_login.status_code != 200:
            return None
        else:
            logger.info("Controller is up and running in   " + str(count * 10) + "s.")
            return "UP"
    else:
        logger.error("Controller is not reachable even after " + str(count * 10) + "s wait")
        return None

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

def obtain_second_csrf(ip, avienc_pass):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    str_enc_avi = str(avienc_pass)
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
    # current_app.config['csrftoken'] = cookiesString['csrftoken']
    return cookiesString['csrftoken'], cookies_string

def set_avi_admin_password(ip, first_csrf, avi_version, aviencpass):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": first_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": first_csrf[0]
    }
    str_enc_avi = str(aviencpass)
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

def get_system_configuration_and_set_values(ip, second_csrf, avi_version, jsonspec):
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
    logger.info('aviversion: {}'.format(avi_version))
    logger.info('response: {}'.format(response_csrf.text))
    logger.info('response code: {}'.format(response_csrf.status_code))
    if response_csrf.status_code != 200:
        return None
    os.system("rm -rf ./systemConfig1.json")
    json_object = json.dumps(response_csrf.json(), indent=4)
    ntp = jsonspec['envSpec']['infraComponents']['ntpServers']
    dns = jsonspec['envSpec']['infraComponents']['dnsServersIp']
    search_domain = jsonspec['envSpec']['infraComponents']['searchDomains']
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
    if TkgUtil.isEnvTkgs_ns(jsonspec):
        replaceValueSysConfig("./systemConfig1.json", "portal_configuration", "allow_basic_authentication",
                              "true")
    return "SUCCESS"

def disable_welcome_screen(ip, second_csrf, avi_version):
    url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": second_csrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": second_csrf[0]
    }
    body = {
            "replace": {
                "welcome_workflow_complete": "true",
                "global_tenant_config": {
                    "tenant_vrf": False,
                    "se_in_provider_context": False,
                    "tenant_access_to_provider_se": True,
                },
            }
        }
    response_csrf = requests.request("PATCH", url, headers=headers, data=json.dumps(body), verify=False)
    if response_csrf.status_code != 200:
        return None
    else:
        return "SUCCESS"

def obtain_avi_version(ip, jsonspec):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    if TkgUtil.isEnvTkgs_wcp(jsonspec):
        str_enc_avi = str(jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
    else:
        str_enc_avi = str(jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
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

def setBackupPhrase(ip, seconcsrf, url_backup, aviVersion, avi_backup_phrase):
    url = url_backup
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": seconcsrf[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": seconcsrf[0]
    }
    str_enc_avi_backup = str(avi_backup_phrase)
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

def form_avi_ha_cluster(ip, jsonspec, aviVersion):
    if TkgUtil.isEnvTkgs_wcp(jsonspec):
        avienc_pass = str(jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64'])
    else:
        avienc_pass = str(jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64'])
    csrf2 = obtain_second_csrf(ip, avienc_pass)
    if csrf2 is None:
        logger.error('Failed to get csrf2 info')
        return None
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }

    try:
        data_center = jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        logger.debug("Targetted Datacenter: {}".format(data_center))
        info, status = get_avi_cluster_info(ip, csrf2, aviVersion)
        if info is None:
            logger.error("Failed to get status of cluster: {}".format(str(status)))
            return None
        if TkgUtil.isEnvTkgs_wcp(jsonspec):
            avi_ip = jsonspec['tkgsComponentSpec']['aviComponents']['aviController01Ip']
            avi_ip2 = jsonspec['tkgsComponentSpec']['aviComponents']['aviController02Ip']
            avi_ip3 = jsonspec['tkgsComponentSpec']['aviComponents']['aviController03Ip']
            clusterIp = jsonspec['tkgsComponentSpec']['aviComponents']['aviClusterIp']
        else:
            avi_ip = jsonspec['tkgComponentSpec']['aviComponents']['aviController01Ip']
            avi_ip2 = jsonspec['tkgComponentSpec']['aviComponents']['aviController02Ip']
            avi_ip3 = jsonspec['tkgComponentSpec']['aviComponents']['aviController03Ip']
            clusterIp = jsonspec['tkgComponentSpec']['aviComponents']['aviClusterIp']
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
            logger.info("Avi HA cluster is already configured")
            return True
        logger.info("Forming Ha cluster")
        payload = AlbPayload.AVI_HA_CLUSTER.format(cluster_uuid=info["uuid"], cluster_name="Alb-Cluster",
                                                   cluster_ip1=avi_ip, vm_uuid_get=_cluster["vm_uuid"],
                                                   vm_mor_get=_cluster["vm_mor"],
                                                   vm_hostname_get=_cluster["vm_hostname"], cluster_ip2=avi_ip2,
                                                   cluster_ip3=avi_ip3, tennat_uuid_get=info["tenant_uuid"],
                                                   virtual_ip_get=clusterIp)
        url = AlbEndpoint.AVI_HA.format(ip=ip)
        response_csrf = requests.request("PUT", url, headers=headers, data=payload, verify=False)
        if response_csrf.status_code != 200:
            logger.error('Error on HA formation: {}'.format(str(response_csrf.text)))
            return None
        count = 0
        list_of_nodes = []
        while count < 180:
            response_csrf = requests.request("GET", url, headers=headers, verify=False)
            try:
                if len(response_csrf.json()["nodes"]) == 3:
                    for node in response_csrf.json()["nodes"]:
                        list_of_nodes.append(node["ip"]["addr"])
                    break
            except:
                pass
            time.sleep(10)
            logger.info("Waited " + str(count * 10) + "s for getting cluster ips, retrying")
            count = count + 1

        if avi_ip not in list_of_nodes or avi_ip2 not in list_of_nodes or not avi_ip3 in list_of_nodes:
            logger.error("Failed to form the cluster ips not found in nodes list")
            return None
        logger.info("Getting cluster runtime status")
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
                    logger.info("Checking node " + str(node_statuses[0]["mgmt_ip"]) + " state: " + str(
                        node_statuses[0]["state"]))
                    logger.info("Checking node " + str(node_statuses[1]["mgmt_ip"]) + " state: " + str(
                        node_statuses[1]["state"]))
                    logger.info("Checking node " + str(node_statuses[2]["mgmt_ip"]) + " state: " + str(
                        node_statuses[2]["state"]))
                    logger.info(
                        "***********************************************************************************")
                    if node_statuses[0]["state"] == "CLUSTER_ACTIVE" and \
                            node_statuses[1]["state"] == "CLUSTER_ACTIVE"\
                            and node_statuses[2]["state"] == "CLUSTER_ACTIVE":
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

def import_ssl_certificate(ip, csrf2, certificate, certificate_key, avi_version):
    body = AlbPayload.IMPORT_CERT.format(cert=certificate, cert_key=certificate_key)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": avi_version,
        "x-csrftoken": csrf2[0]
    }
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

def create_imported_ssl_certificate(ip, csrf2, dic, cer, key, avi_version):
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

def generate_ssl_certificate_vsphere(ip, csrf2, avi_fqdn, avi_version, jsonspec):
    common_name = avi_fqdn
    ips = [str(ip), common_name]
    hafield = jsonspec['tkgComponentSpec']['aviComponents']['enableAviHa']
    if isAviHaEnabled(hafield):
        if TkgUtil.isEnvTkgs_wcp(jsonspec):
            avi_fqdn2 = jsonspec['tkgsComponentSpec']['aviComponents']['aviController02Fqdn']
            avi_ip2 = jsonspec['tkgsComponentSpec']['aviComponents']['aviController02Ip']
            avi_fqdn3 = jsonspec['tkgsComponentSpec']['aviComponents']['aviController03Fqdn']
            avi_ip3 = jsonspec['tkgsComponentSpec']['aviComponents']['aviController03Ip']
            clusterIp = jsonspec['tkgsComponentSpec']['aviComponents']['aviClusterIp']
            cluster_fqdn = jsonspec['tkgsComponentSpec']['aviComponents']["aviClusterFqdn"]
        else:
            avi_fqdn2 = jsonspec['tkgComponentSpec']['aviComponents']['aviController02Fqdn']
            avi_ip2 = jsonspec['tkgComponentSpec']['aviComponents']['aviController02Ip']
            avi_fqdn3 = jsonspec['tkgComponentSpec']['aviComponents']['aviController03Fqdn']
            avi_ip3 = jsonspec['tkgComponentSpec']['aviComponents']['aviController03Ip']
            clusterIp = jsonspec['tkgComponentSpec']['aviComponents']['aviClusterIp']
            cluster_fqdn = jsonspec['tkgComponentSpec']['aviComponents']['aviClusterFqdn']
        ips.append(avi_ip2)
        ips.append(avi_fqdn2)
        ips.append(avi_ip3)
        ips.append(avi_fqdn3)
        ips.append(clusterIp)
        ips.append(cluster_fqdn)
        common_name = cluster_fqdn
    san = json.dumps(ips)
    body = AlbPayload.SELF_SIGNED_CERT.format(name=CertName.VSPHERE_CERT_NAME,
                                              common_name=common_name, san_list=san)
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


def manage_avi_certificates(ip, avi_version, jsonspec, avi_fqdn, cert_name):
    rcmd = cmd_runner.RunCmd()
    avienc_pass = jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64']
    csrf2 = obtain_second_csrf(ip, avienc_pass)
    if csrf2 is None:
        logger.error("Failed to get csrf from new set password")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get csrf from new set password",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500, False
    try:
        if TkgUtil.isEnvTkgs_wcp(jsonspec):
            avi_cert = jsonspec['tkgsComponentSpec']['aviComponents']['aviCertPath']
            avi_key = jsonspec['tkgsComponentSpec']['aviComponents']['aviCertKeyPath']
            license_key = ""
        else:
            avi_cert = jsonspec['tkgComponentSpec']['aviComponents']['aviCertPath']
            avi_key = jsonspec['tkgComponentSpec']['aviComponents']['aviCertKeyPath']
            license_key = jsonspec['tkgComponentSpec']['aviComponents']['aviLicenseKey']
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
            msg1 = "Certificate does not exist, please copy certificate file to location" + avi_cert
        if not Path(avi_key).exists():
            exist = False
            msg2 = "Certificate key does not exist, please copy key file to location " + avi_key
        if not exist:
            logger.error(msg1 + " " + msg2)
            d = {
                "responseType": "ERROR",
                "msg": msg1 + " " + msg2,
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500, False
        key_name = Path(avi_key).name
        cert_file_name = Path(avi_key).name
        os.system("rm -rf " + key_name)
        os.system("rm -rf " + cert_file_name)
        shell_cmd = """awk 'NF \{sub(/\\r/, ""); printf "%s\\n",$0;}' $1 >> $2"""
        converter_file_path = "/tmp/pem_to_one_line_converter.sh"
        with open(converter_file_path, 'w') as rsh:
            rsh.write(shell_cmd)
        logger.info("Changing permission for cert replacer")
        file_permission_cmd = "chmod +x {}".format(converter_file_path)
        rcmd.run_cmd_only(file_permission_cmd)
        run_cert_cmd = ".{conv_script} {avi_cert} {cert_fn}".format(conv_script=converter_file_path,
                                                                    avi_cert=avi_cert,
                                                                    cert_fn=cert_file_name)
        logger.debug("State of cert converter: {}".format(run_cert_cmd))
        cer = Path(cert_file_name).read_text().strip("\n")
        avi_controller_cert = cer
        key_cmd = ".{conv_script} {avi_key} {key_nm}".format(conv_script=converter_file_path,
                                                               avi_key=avi_key,
                                                               key_nm=key_name)
        rcmd.run_cmd_only(key_cmd)
        key = Path(key_name).read_text().strip("\n")
        avi_controller_cert_key = key
        if not avi_controller_cert or not avi_controller_cert_key:
            logger.error("Certificate or key provided is empty")
            d = {
                "responseType": "ERROR",
                "msg": "Certificate or key provided is empty",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500, False
        import_cert, error = import_ssl_certificate(ip, csrf2, avi_controller_cert,
                                                    avi_controller_cert_key, avi_version)
        if import_cert is None:
            logger.error("Avi cert import failed " + str(error))
            d = {
                "responseType": "ERROR",
                "msg": "Avi cert import failed " + str(error),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500, False
        cert_name = import_cert['cert_name']
    get_cert = get_ssl_certificate_status(ip, csrf2, cert_name, avi_version)
    if get_cert[0] is None:
        logger.error("Failed to get certificate status " + str(get_cert[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Avi cert import failed " + str(error),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500, False
    if get_cert[0] == "NOT_FOUND":
        logger.info("Generating cert")
        if avi_cert and avi_key:
            res = create_imported_ssl_certificate(ip, csrf2, import_cert, cer, key, avi_version)
        else:
            res = generate_ssl_certificate_vsphere(ip, csrf2, avi_fqdn, avi_version, jsonspec)
        url = res[0]
        if res[0] is None:
            logger.error("Failed to generate the ssl certificate")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to generate the ssl certificate " + res[1],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500, False
    else:
        url = get_cert[0]
    get_cert = get_current_cert_config(ip, csrf2, url, avi_version)
    if get_cert[0] is None:
        logger.error("Failed to get current certificate: {}".format(get_cert[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get current certificate " + get_cert[1],
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500, False

    logger.info("Replacing cert")
    replace_cert = replaceWithNewCert(ip, csrf2, avi_version)
    if replace_cert[0] is None:
        logger.error("Failed replace the certificate" + replace_cert[1])
        d = {
            "responseType": "ERROR",
            "msg": "Failed replace the certificate " + replace_cert[1],
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500, False

    if license_key:
        res, status = configure_alb_licence(ip, csrf2, license_key, avi_version)
        if res is None:
            logger.error("Failed to apply licesnce " + str(status))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to apply licesnce " + str(status),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500, False
        logger.info(status)
    d = {
        "responseType": "SUCCESS",
        "msg": "Certificate managed successfully",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200, True


def deployAndConfigureAvi(govc_client: GovcClient, vm_name, controller_ova_location,
                          deploy_options, performOtherTask, avi_version, jsonspec):
    try:
        data_center = jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter']
        if not govc_client.get_vm_ip(vm_name, datacenter_name=data_center):
            logger.info("Deploying avi controller..")
            govc_client.deploy_library_ova(location=controller_ova_location, name=vm_name,
                                           options=deploy_options)
            if TkgUtil.isEnvTkgs_wcp(jsonspec):
                avi_size = jsonspec['tkgsComponentSpec']['aviComponents']['aviSize']
            else:
                avi_size = jsonspec['tkgComponentSpec']['aviComponents']['aviSize']
            size = str(avi_size).lower()
            if size not in ["essentials", "small", "medium", "large"]:
                logger.error("Wrong avi size provided supported  essentials/small/medium/large " +
                             avi_size)
                return False
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
            change_VM_config = ["govc", "vm.change", "-dc=" + data_center, "-vm=" + vm_name, "-c=" + cpu,
                                "-m=" + memory]
            power_on = ["govc", "vm.power", "-dc=" + data_center, "-on=true", vm_name]
            runProcess(change_VM_config)
            runProcess(power_on)
            ip = govc_client.get_vm_ip(vm_name, datacenter_name=data_center, wait_time='30m')
            if ip is None:
                logger.error("Failed to get ip of avi controller on waiting 30m")
                return False

    except Exception as e:
        logger.error("Failed to deploy  the vm from library due to " + str(e))
        return False

    ip = govc_client.get_vm_ip(vm_name, datacenter_name=data_center)[0]
    logger.info("Checking controller is up")
    if check_controller_is_up(ip) is None:
        logger.error("Controller service is not up")
        return False
    deployed_avi_version = obtain_avi_version(ip, jsonspec)
    if deployed_avi_version[0] is None:
        logger.error("Failed to login and obtain avi version")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
            "ERROR_CODE": 500
        }
        logger.debug("Error: {}".format(json.dumps(d['msg'])))
        return False
    avi_version = deployed_avi_version[0]
    if TkgUtil.isEnvTkgs_wcp(jsonspec) and verifyVcenterVersion(Versions.VCENTER_UPDATE_THREE, jsonspec):
        avi_required = Avi_Version.AVI_VERSION_UPDATE_THREE
    elif TkgUtil.isEnvTkgs_wcp(jsonspec) and not verifyVcenterVersion(Versions.VCENTER_UPDATE_THREE, jsonspec):
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
        logger.error(f"Required avi_version: {avi_required} is not matching as obtained avi_version: {avi_version} ")
        logger.debug("Error: {}".format(json.dumps(d['msg'])))
        return False
    if performOtherTask:
        csrf = obtain_first_csrf(ip)
        if csrf is None:
            logger.error("Failed to get First csrf value.")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get First csrf",
                "ERROR_CODE": 500
            }
            logger.debug("Fetched resp detail for csrf: {}".format(json.dumps(d['msg'])))
            return False
        if csrf == "SUCCESS":
            logger.info("Password of appliance already changed")
        else:
            if TkgUtil.isEnvTkgs_wcp(jsonspec):
                avienc_pass = jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64']
            else:
                avienc_pass = jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64']
            if set_avi_admin_password(ip, csrf, avi_version, avienc_pass) is None:
                logger.error("Failed to set the avi admin password")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to set the avi admin password",
                    "ERROR_CODE": 500
                }
                logger.debug("Error: {}".format(json.dumps(d['msg'])))
                return False
        if TkgUtil.isEnvTkgs_wcp(jsonspec):
            avienc_pass = jsonspec['tkgsComponentSpec']['aviComponents']['aviPasswordBase64']
        else:
            avienc_pass = jsonspec['tkgComponentSpec']['aviComponents']['aviPasswordBase64']
        csrf2 = obtain_second_csrf(ip, avienc_pass)
        if csrf2 is None:
            logger.error("Failed to get csrf from new set password")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get csrf from new set password",
                "ERROR_CODE": 500
            }
            logger.debug("Error: {}".format(json.dumps(d['msg'])))
            return False
        else:
            logger.info("Obtained csrf with new credential successfully")
        if get_system_configuration_and_set_values(ip, csrf2, avi_version, jsonspec) is None:
            logger.error("Failed to set the system configuration")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to set the system configuration",
                "ERROR_CODE": 500
            }
            logger.debug("Error: {}".format(json.dumps(d['msg'])))
            return False
        else:
            logger.info("Got system configuration successfully")
        if set_dns_ntp_smtp_settings(ip, csrf2, avi_version) is None:
            logger.error("Set Dns Ntp smtp failed.")
            d = {
                "responseType": "ERROR",
                "msg": "Set Dns Ntp smtp failed.",
                "ERROR_CODE": 500
            }
            logger.debug("Error: {}".format(json.dumps(d['msg'])))
            return False
        else:
            logger.info("Set DNs Ntp Smtp successfully")
        if disable_welcome_screen(ip, csrf2, avi_version) is None:
            logger.error("Failed to disable welcome screen")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to disable welcome screen",
                "ERROR_CODE": 500
            }
            logger.debug("Error: {}".format(json.dumps(d['msg'])))
            return False
        else:
            logger.info("Disable welcome screen successfully")
        # deployed_avi_version = obtain_avi_version(ip, jsonspec)
        # if deployed_avi_version[0] is None:
        #     logger.error("Failed to login and obtain avi version")
        #     d = {
        #         "responseType": "ERROR",
        #         "msg": "Failed to login and obtain avi version " + deployed_avi_version[1],
        #         "ERROR_CODE": 500
        #     }
        #     logger.debug("Error: {}".format(json.dumps(d['msg'])))
        #     return False
        # avi_version = deployed_avi_version[0]
        backup_url = get_backup_configuration(ip, csrf2, avi_version)
        if backup_url[0] is None:
            logger.error("Failed to get backup configuration")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get backup configuration " + backup_url[1],
                "ERROR_CODE": 500
            }
            logger.debug("Error: {}".format(json.dumps(d['msg'])))
            return False
        else:
            logger.info("Got backup configuration successfully")
        logger.info("Set backup pass phrase")
        if TkgUtil.isEnvTkgs_wcp(jsonspec):
            avi_backup_phrase = jsonspec['tkgsComponentSpec']['aviComponents']['aviBackupPassphraseBase64']
        else:
            avi_backup_phrase = jsonspec['tkgComponentSpec']['aviComponents']['aviBackupPassphraseBase64']
        setBackup = setBackupPhrase(ip, csrf2, backup_url[0], avi_version, avi_backup_phrase)
        if setBackup[0] is None:
            logger.error("Failed to set backup pass phrase")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to set backup pass phrase " + str(setBackup[1]),
                "ERROR_CODE": 500
            }
            logger.debug("Error: {}".format(json.dumps(d['msg'])))
            return False
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured avi",
        "ERROR_CODE": 200
    }
    logger.debug("State: {}".format(json.dumps(d['msg'])))
    return True
