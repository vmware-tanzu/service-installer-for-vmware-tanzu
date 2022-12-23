import json
import requests
import base64
import uuid
import os

from flask import current_app
from pathlib import Path

from common.constants.vcd_api_constants import VcdApiEndpoint, VcdHeaders
from vcd.vcd_prechecks.vcdPrechecks import run_vcd_api, get_vcd_session, get_avi_version, get_csrf, get_org_vcd_list, \
    get_file_MarketPlace, download_kubernetes_ova
from common.operation.constants import CertName, VcdCSE, CseMarketPlace, KubernetesOva
from common.constants.alb_api_constants import AlbEndpoint
from common.model.vcdSpec import VcdMasterSpec
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList, runShellCommandAndReturnOutput


def upload_avi_cert(specFile):
    """
    :param specFile: Full path of input json file
    :return: True if upload successful. Else, False
    """
    vcd_address = specFile.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
    deploy_avi = specFile.envSpec.aviCtrlDeploySpec.deployAvi
    if str(deploy_avi).lower() == "true":
        avi_fqdn = specFile.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviController01Fqdn
    else:
        return False, "If NSX ALB is already deployed, please import the certificate to VCD, prior " \
                      "to initiating deployment"

    url = VcdApiEndpoint.GET_AVI_CERTIFICATES.format(vcd=vcd_address)
    response = run_vcd_api(specFile, url, "json")
    if not response[0]:
        return False, response[1]

    response = response[1]

    for cert in response.json()["values"]:
        if cert["alias"] == CertName.VCD_AVI_CERT_NAME.format(avi_fqdn=avi_fqdn):
            return True, "NSX ALB certificate is already imported to VCD"

    current_app.logger.info("NSX ALB certificate is not imported to VCD, importing now...")

    try:
        cert_file = specFile.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviCertPath
    except:
        cert_file = ""

    if cert_file.__len__() == 0:
        current_app.logger.info("Certificate not provided, fetching self signed certificate from AVI")
        cert_response = get_cert_from_avi(specFile,avi_fqdn)
        if cert_response[0] is None:
            return False, cert_response[1]
        cert = cert_response[0].strip("\n")
    else:
        cert = Path(cert_file).read_text().strip("\n")

    vcd_session_key = get_vcd_session(specFile)
    vcd_session_key = vcd_session_key[0]
    header = VcdHeaders.COMMON_HEADER.format(response_format="json", vcd_auth_key=vcd_session_key)
    header = json.loads(header)

    payload = {
        "alias": CertName.VCD_AVI_CERT_NAME.format(avi_fqdn=avi_fqdn),
        "certificate": cert
    }
    modified_payload = json.dumps(payload, indent=4)
    response = requests.request("POST", url, headers=header, data=modified_payload, verify=False)
    if response.status_code != 201:
        if response.text.__contains__("already exists"):
            return True, "Same AVI certificate with different cert name is already imported to VCD"
        current_app.logger.error(response.text)
        return False, "Failed to import NSX ALB certificate to VCD"

    return True, "Certificate imported to VCD successfully"


def upload_kubernetes_ova_to_catalog(specFile):
    """
    Download kubernetes OVA from marketPlace and Upload it to Catalog
    Photon 1.23 ova will be uploaded to k8sTemplateCatalogName catalog
    :param specFile: Full path of input json file
    :return: True, if successfull, else, False
    """
    try:
        vcd_address = specFile.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        password =specFile.envSpec.vcdSpec.vcdComponentSpec.vcdSysAdminPasswordBase64
        vcd_username = specFile.envSpec.vcdSpec.vcdComponentSpec.vcdSysAdminUserName
        refresh_token = specFile.envSpec.marketplaceSpec.refreshToken

        ## add download ova from marketplace step here
        version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION
        file_name = KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + version
        file_obj = Path("/tmp/" + file_name + ".ova")
        if not file_obj.exists():
            current_app.logger.info("Downloading Kubernetes OVA from VMware MarketPlace...")
            response = download_kubernetes_ova(file_name, refresh_token, version, "ubuntu")
            if response[0] is None:
                return False, response[1]
            current_app.logger.info(response[1])
        else:
            current_app.logger.info("Kubernetes ova is already downloaded - " + file_name)

        login = vcd_login(vcd_address, vcd_username, password)
        if not login[0]:
            return False, login[1]
        current_app.logger.info(login[1])

        ova_available = False
        catalog_name = specFile.envSpec.cseSpec.svcOrgVdcSpec.svcOrgCatalogSpec.k8sTemplatCatalogName
        ova_filename = file_name
        catalog_response = find_file_in_catalog(catalog_name, ova_filename + ".ova")
        if not catalog_response[0]:
            if catalog_response[1].__contains__("file not found"):
                current_app.logger.info(catalog_response[1])
            else:
                return False, catalog_response[1]
        else:
            current_app.logger.info(catalog_response[1])
            ova_available = True

        if not ova_available:
            current_app.logger.info("Uploading Kubernetes OVA to catalog " + catalog_name +
                                    ". This will take approximately 5 minutes to complete...")

            upload_command = ["vcd", "--json", "catalog",  "upload",  catalog_name,
                              "/tmp/" + ova_filename + ".ova"]
            output = runShellCommandAndReturnOutputAsList(upload_command)
            if output[1] != 0:
                current_app.logger.error(output[0])
                return False, "Failed to upload kubernetes OVA to catalog " + str(output[0])

            catalog_response = find_file_in_catalog(catalog_name, ova_filename + ".ova")
            if not catalog_response[0]:
                return False, catalog_response[1]

        return True, "Kubernetes OVA uploaded to catalog successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while uploading CSE OVA to Catalog"


def upload_cse_ova_to_catalog(specFile):
    """
    Download CSE OVA from marketPlace and Upload it to Catalog
    :param specFile: Full path of input json file
    :return: True, if successfull, else, False
    """
    try:
        vcd_address = specFile.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        password =specFile.envSpec.vcdSpec.vcdComponentSpec.vcdSysAdminPasswordBase64
        vcd_username = specFile.envSpec.vcdSpec.vcdComponentSpec.vcdSysAdminUserName
        refresh_token = specFile.envSpec.marketplaceSpec.refreshToken

        if not refresh_token:
            return False, "MarketPlace refresh token field is empty"

        ## add download ova from marketplace step here
        file_obj = Path("/tmp/" + CseMarketPlace.CSE_OVA_NAME)
        if not file_obj.exists():
            current_app.logger.info("Downloading CSE OVA from VMware MarketPlace, "
                                    "download will take approximately 5 mins to complete...")
            response = get_file_MarketPlace(CseMarketPlace.CSE_OVA_NAME, refresh_token, CseMarketPlace.VERSION,
                                            CseMarketPlace.CSE_OVA_GROUPNAME)
            if response[0] is None:
                return False, response[1]
            current_app.logger.info(response[1])
        else:
            current_app.logger.info(CseMarketPlace.CSE_OVA_NAME + " is already downloaded")

        login = vcd_login(vcd_address, vcd_username, password)
        if not login[0]:
            return False, login[1]
        current_app.logger.info(login[1])

        ova_available = False
        catalog_name = specFile.envSpec.cseSpec.svcOrgVdcSpec.svcOrgCatalogSpec.cseOvaCatalogName
        ova_filename = CseMarketPlace.CSE_OVA_NAME
        catalog_response = find_file_in_catalog(catalog_name, ova_filename)
        if not catalog_response[0]:
            if catalog_response[1].__contains__("file not found"):
                current_app.logger.info(catalog_response[1])
            else:
                return False, catalog_response[1]
        else:
            current_app.logger.info(catalog_response[1])
            ova_available = True

        if not ova_available:
            current_app.logger.info("Uploading CSE OVA to catalog " + catalog_name + ". This will take approximately "
                                                                                     "5 minutes to complete...")

            upload_command = ["vcd", "--json", "catalog",  "upload",  catalog_name, "/tmp/" + ova_filename]
            output = runShellCommandAndReturnOutputAsList(upload_command)
            if output[1] != 0:
                current_app.logger.error(output[0])
                return False, "Failed to upload CSE OVA to catalog " + str(output[0])

            catalog_response = find_file_in_catalog(catalog_name, ova_filename)
            if not catalog_response[0]:
                return False, catalog_response[1]

        return True, "CSE OVA uploaded to catalog successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while uploading CSE OVA to Catalog"


def configure_cse_plugin(vcdspec):
    """
    Register CSE plugin metadata, upload plugin, create interface, entities and access controls
    :param vcdspec: full path of user input json file
    :return:
    """
    try:
        vcd = vcdspec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        refresh_token = vcdspec.envSpec.marketplaceSpec.refreshToken

        ## add download ova from marketplace step here
        file_obj = Path("/tmp/" + CseMarketPlace.CSE_PLUGIN_NAME_VCD)
        if not file_obj.exists():
            current_app.logger.info("Downloading CSE Plugin from VMware MarketPlace...")
            response = get_file_MarketPlace(CseMarketPlace.CSE_PLUGIN_NAME_VCD, refresh_token, CseMarketPlace.VERSION,
                                            CseMarketPlace.CSE_PLUGIN_GROUPNAME)
            if response[0] is None:
                return False, response[1]
            current_app.logger.info(response[1])
        else:
            current_app.logger.info(CseMarketPlace.CSE_PLUGIN_NAME_VCD + " is already downloaded")

        response = register_plugin_metadata(vcd, vcdspec)
        if not response[0]:
            current_app.logger.error(response[1])
            return False, response[1]

        current_app.logger.info(response[1])
        plugin_id = response[2]

        upload_plugin = upload_cse_plugin(vcd, plugin_id, vcdspec)
        if not upload_plugin[0]:
            current_app.logger.error(upload_plugin[1])
            return False, upload_plugin[1]
        current_app.logger.info(upload_plugin[1])

        response = create_interfaces_entities(vcd, vcdspec)
        if not response[0]:
            return False, response[1]
        current_app.logger.info(response[1])

        return True, "Completed CSE plugin configuration"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while performing CSE configurations"


def create_server_config_cse(vcdspec):
    """
    Creating and Registering Server Config For CSE
    :param vcdspec: Full path of input json file
    :return: True, if successful. Else, False
    """
    try:
        vcd = vcdspec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress

        response = cse_server_config(vcd, vcdspec)
        if not response[0]:
            current_app.logger.info(response[1])
        else:
            current_app.logger.info(response[1])
            return True, response[1]

        vcd_session_key = get_vcd_session(vcdspec)
        if vcd_session_key[0] is None:
            return False, vcd_session_key[1]
        vcd_session_key = vcd_session_key[0]

        header = VcdHeaders.COMMON_HEADER.format(response_format="json",
                                                 vcd_auth_key=vcd_session_key)
        header = json.loads(header)

        payload = {
            "entityType": "urn:vcloud:type:vmware:VCDKEConfig:1.0.0",
            "name": "vcdKeConfig",
            "externalId": "null",
            "entity": {
                "profiles": [{
                    "name": "production",
                    "active": "true",
                    "vcdKeInstances": [{
                        "name": "vcd-container-service-extension"
                    }],
                    "K8Config": {
                        "cni": {
                            "name": "antrea",
                            "version": ""
                        },
                        "cpi": {
                            "name": "cpi for cloud director",
                            "version": "1.2.0"
                        },
                        "csi": [{
                            "name": "csi for cloud director",
                            "version": "1.3.0"
                        }]
                    },
                    "serverConfig": {
                        "rdePollIntervalInMin": 1
                    },
                    "githubConfig": {
                        "githubPersonalAccessToken": ""
                    },
                    "bootstrapClusterConfig": {
                        "clusterctl": {
                            "version": "v1.1.3",
                            "clusterctlyaml": ""
                        },
                        "kindVersion": "v0.14.0",
                        "proxyConfig": {
                            "noProxy": "localhost,127.0.0.1,k8s.test,.svc",
                            "httpProxy": "",
                            "httpsProxy": ""
                        },
                        "sizingPolicy": "TKG small",
                        "capiEcosystem": {
                            "infraProvider": {
                                "name": "capvcd",
                                "version": "1.0.0",
                                "capvcdRde": {
                                    "nss": "capvcdCluster",
                                    "vendor": "vmware",
                                    "version": "1.1.0"
                                }
                            },
                            "coreCapiVersion": "v1.1.3",
                            "bootstrapProvider": {
                                "name": "CAPBK",
                                "version": "v1.1.3"
                            },
                            "controlPlaneProvider": {
                                "name": "KCP",
                                "version": "v1.1.3"
                            }
                        },
                        "dockerVersion": "",
                        "kubectlVersion": ""
                    }
                }]
            }
        }

        modified_payload = json.dumps(payload, indent=4)
        url = VcdApiEndpoint.CREATE_CSE_SERVER_CONFIG.format(vcd=vcd, config_type=VcdCSE.VCDKE_CONFIG)
        response = requests.request("POST", url, headers=header, data=modified_payload, verify=False)
        if response.status_code != 201:
            current_app.logger.error(response.text)
            return False, "Failed to created vcdKeConfig server config"

        get_response = cse_server_config(vcd, vcdspec)
        if not get_response[0]:
            current_app.logger.error(get_response[1])
            return False, get_response[1]

        current_app.logger.info("vcdKeConfig server config created successfully")

        register = register_entity(vcdspec, vcd, get_response[2])
        if not register[0]:
            current_app.logger.error(register[1])
            return False, register[1]

        current_app.logger.info(register[1])

        return True, "CSE Server Configuration and Registration successful"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while creating CSE service configs"


def get_access_token_vapp(vcdspec):
    """
    Creating and Registering Server Config For CSE
    :param vcdspec: Full path of input json file
    :return: True, if successful. Else, False
    """
    try:
        vcd = vcdspec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        cse_username = vcdspec.envSpec.cseSpec.cseServerDeploySpec.customCseProperties.cseSvcAccountName
        cse_password = vcdspec.envSpec.cseSpec.cseServerDeploySpec.customCseProperties.cseSvcAccountPasswordBase64

        unique_id = uuid.uuid1()

        token_file = Path(VcdCSE.ACCESS_TOKEN)
        if token_file.exists():
            current_app.logger.info("Token file exists, fetching token")
            if token_file.stat().st_size == 0:
                current_app.logger.info("Token file is empty, generating new token")
            else:
                with open(token_file, "r") as file_read:
                    access_token = file_read.read()
                    return access_token, "Access token was created in previous run, returning same."

        token_name = "sivt-access-token-" + str(unique_id).split("-")[0]
        current_app.logger.info("Registering token to VCD - " + token_name)
        payload = {
            "client_name": token_name
        }
        modified_payload = json.dumps(payload, indent=4)
        vcd_session_key = get_vcd_session(vcdspec, cse_username, cse_password)
        if vcd_session_key[0] is None:
            return False, vcd_session_key[1]
        vcd_session_key = vcd_session_key[2]

        header = {
            "Accept": "application/*;version=36.1",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + vcd_session_key
        }

        url = VcdApiEndpoint.REGISTER_SIVT_TOKEN.format(vcd=vcd, operation="register")
        response = requests.request("POST", url, headers=header, data=modified_payload, verify=False)
        if response.status_code != 200:
            current_app.logger.error(response.text)
            return False, "Failed to register access token"

        current_app.logger.info("Token registered successfully")

        grant_type = None
        client_id = response.json()["client_id"]
        for grandTypes in response.json()["grant_types"]:
            if str(grandTypes).startswith("urn"):
                grant_type = str(grandTypes)

        data = dict(grant_type=grant_type, client_id=client_id, assertion=vcd_session_key)

        header = {
            "Accept": "application/*;version=36.1",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        url = VcdApiEndpoint.REGISTER_SIVT_TOKEN.format(vcd=vcd, operation="token")
        token_response = requests.request("POST", url, headers=header, data=data, verify=False)
        if token_response.status_code != 200:
            current_app.logger.error(token_response.text)
            return False, "Failed to register access token"

        access_token = token_response.json()["refresh_token"]
        os.system("mkdir -p /opt/vmware/arcas/src/access_token/")
        with open(token_file, 'w') as fileout:
            fileout.write(access_token)

        return access_token, "Access token for CSE vApp obtained successfully"

    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while fetching access token for CSE vApp"


def get_cert_from_avi(spec, alb):
    csrf2 = get_csrf(alb, spec)
    if csrf2 is None:
        return None, "Failed to get csrf from for NSX ALB Controller"

    aviVersion = get_avi_version(alb, spec)
    if aviVersion[0]:
        aviVersion = aviVersion[1]
    else:
        return None, "Failed to get NSX ALB Controller version details. " + str(aviVersion[1])
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + alb + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }

    url = AlbEndpoint.CRUD_SSL_CERT.format(ip=alb)
    response_csrf = requests.request("GET", url, headers=headers, verify=False)
    if response_csrf.status_code != 200:
        current_app.logger.error(response_csrf.text)
        return None, response_csrf.text

    for record in response_csrf.json()["results"]:
        if record["name"] == CertName.VSPHERE_CERT_NAME:
            return record["certificate"]["certificate"], "successfully obtained certificate from NSX ALB"

    return None, "Failed to obtain certificate from NSX ALB"


def cse_server_config(vcd, vcdspec):
    try:
        url = VcdApiEndpoint.GET_CSE_SERVER_CONFIG.format(vcd=vcd, config_type=VcdCSE.VCDKE_CONFIG)
        response = run_vcd_api(vcdspec, url, "*")
        if not response[0]:
            current_app.logger.error(response[1].text)
            return False, response[1]

        response = response[1]

        for entry in response.json()["values"]:
            if entry["name"].strip() == "vcdKeConfig":
                return True, "vcdKeConfig server config is already created", entry["id"]

        return False, "vcdKeConfig server config not found"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while fetching vcdKeConfig details"


def register_entity(vcdspec, vcd, vcdke_id):
    try:
        vcd_session_key = get_vcd_session(vcdspec)
        if vcd_session_key[0] is None:
            return False, vcd_session_key[1]
        vcd_session_key = vcd_session_key[0]

        header = VcdHeaders.COMMON_HEADER.format(response_format="*",
                                                 vcd_auth_key=vcd_session_key)
        header = json.loads(header)

        payload = {}
        url = VcdApiEndpoint.REGISTER_ENTITY.format(vcd=vcd, config_id=vcdke_id)
        response = requests.request("POST", url, headers=header, data=payload, verify=False)
        if response.status_code != 200:
            current_app.logger.error(response.text)
            return False, "Failed to created vcdKeConfig server config"

        state = response.json()["state"]
        if state.strip() == "RESOLVED":
            return True, "Entity registered and it's state found - " + state

        return False, "Entity registered but state is - " + state
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while registering entity"


def find_file_in_catalog(catalog, file_name):
    try:
        command = ["vcd", "--json", "catalog", "list", catalog]
        output = runShellCommandAndReturnOutput(command)
        if output[1] != 0:
            current_app.logger.error(output[0])
            return False, "Failed to list files from catalog - " + catalog

        json_response = output[0].strip(VcdCSE.CLI_WARNING_MSG)

        json_response = json.loads(json_response)

        try:
            if json_response["message"] == "not found":
                return False, "Catalog is empty, file not found"
        except:
            pass

        for entry in json_response:
            if file_name == str(entry["name"]).strip():
                return True, "CSE OVA available in given catalog"

        return False, "CSE OVA file not found in catalog - " + catalog
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while fetching files from CSE Catalog"


def vcd_login(vcd, username, password):
    try:
        current_app.logger.info("Login to VCD....")
        if username.__contains__("@"):
            username = str(username).split("@")[0]

        base64_bytes = password.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        vcd_password = enc_bytes.decode('ascii').rstrip("\n")

        login_command = ["vcd", "login", vcd, "system", username, "-p", vcd_password, "-i"]
        output = runShellCommandAndReturnOutputAsList(login_command)
        if output[1] != 0:
            current_app.logger.error(output[0])
            return False, "Failed to login to VCD, " + str(output[0])
        return True, "Login to VCD successful"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Failed to login to VCD, exception occurred - " + str(e)


def register_plugin_metadata(vcd, vcdspec):
    try:
        plugin = None
        result = is_plugin_registered(vcdspec, vcd)
        if not result[0]:
            return False, result[1]

        plugin = result[2]
        if plugin is None:
            vcd_session_key = get_vcd_session(vcdspec)
            if vcd_session_key[0] is None:
                return False, vcd_session_key[1]
            vcd_session_key = vcd_session_key[0]
            current_app.logger.info("Plugin metadata not registered yet, registering now")
            header = VcdHeaders.COMMON_HEADER.format(response_format="*", vcd_auth_key=vcd_session_key)
            header = json.loads(header)
            payload = {
                "pluginName": VcdCSE.PLUGIN_NAME,
                "vendor": "VMware",
                "description": "Kubernetes Container Clusters UI Plugin for CSE",
                "version": "4.0.0",
                "license": "Copyright (C) VMware 2022.  All rights reserved.",
                "link": "http://www.vmware.com/support",
                "tenant_scoped": "true",
                "enabled": "true"
            }
            modified_payload = json.dumps(payload, indent=4)
            url = VcdApiEndpoint.GET_PLUGIN_INFO.format(vcd=vcd)
            register_response = requests.request("POST", url, headers=header, data=modified_payload, verify=False)
            if register_response.status_code != 201:
                current_app.logger.error(register_response.text)
                return False, "Failed to register plugin metadata to VCD"
            current_app.logger.info("Plugin metadata registered successfully.")
            result = is_plugin_registered(vcdspec, vcd)
            if not result[0]:
                return False, result[1]

            return result[0], result[1], result[2]
        else:
            return True, "Plugin metadata is already registered", plugin

        return False, "Plugin metadata registration failed"

    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while fetching plugin metadata details - " + str(e)


def is_plugin_registered(vcdspec, vcd):
    try:
        plugin_id = None
        url = VcdApiEndpoint.GET_PLUGIN_INFO.format(vcd=vcd)
        response = run_vcd_api(vcdspec, url, "*")
        if not response[0]:
            current_app.logger.error(response[1].text)
            return False, response[1]

        for plugin in response[1].json():
            if plugin["pluginName"] == VcdCSE.PLUGIN_NAME:
                plugin_id = plugin["id"]

        return True, "Plugin is registered", plugin_id
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred - " + str(e)


def upload_cse_plugin(vcd_address, plugin_id, vcdspec):
    try:
        vcd_session_key = get_vcd_session(vcdspec)
        if vcd_session_key[0] is None:
            return False, vcd_session_key[1]
        vcd_session_key = vcd_session_key[0]

        vcd_filename = "/tmp/" + CseMarketPlace.CSE_PLUGIN_NAME_VCD
        zip_size = Path(vcd_filename).stat().st_size
        url = VcdApiEndpoint.UPLOAD_CSE_PLUGIN.format(vcd=vcd_address, plugin_id=plugin_id)
        header = VcdHeaders.COMMON_HEADER.format(response_format="vnd.vmware.vcloud.query.records+json",
                                                 vcd_auth_key=vcd_session_key)
        header = json.loads(header)
        payload = {
            "fileName": CseMarketPlace.CSE_PLUGIN_NAME_VCD,
            "size": zip_size
        }
        modified_payload = json.dumps(payload, indent=4)
        response = requests.request("POST", url, headers=header, data=modified_payload, verify=False)
        if response.status_code == 400:
            if response.text.__contains__("Plugin binary already exists"):
                #current_app.logger.info("Plugin binary already exists")
                return True, "Plugin binary already exists"
        elif response.status_code != 204:
            current_app.logger.error(response.text)
            return False, "Failed to upload CSE plugin to VCD"

        transfer_link = response.headers['Link']

        transfer_link = transfer_link.split(".zip")[0]
        if str(transfer_link).startswith("<"):
            transfer_link = transfer_link[1:]

        url = transfer_link + ".zip"
        current_app.logger.info("Obtained transfer link - " + str(url))

        header = {
            "x-vcloud-authorization": vcd_session_key,
            "Accept": "application/json;version=36.1",
            "Content-Type": "application/binary"
        }
        #header = json.loads(header)
        data = open("/tmp/" + CseMarketPlace.CSE_PLUGIN_NAME_VCD, 'rb').read()
        response = requests.request("PUT", url, headers=header, data=data, verify=False)
        if response.status_code != 200:
            current_app.logger.error(response.status_code)
            current_app.logger.error(response.text)
            return False, "Failed transfer CSE plugin"

        # Read transfer link from response and pass it
        return True, "Plugin uploaded to VCD successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while uploading CSE plugin to VCD "


def create_interfaces_entities(vcd, vcdspec):
    try:
        vcdke_access = True
        capvc_access = True
        vcd_session_key = get_vcd_session(vcdspec)
        if vcd_session_key[0] is None:
            return False, vcd_session_key[1]
        vcd_session_key = vcd_session_key[0]

        #name = "VCDKEConfig"
        header = VcdHeaders.COMMON_HEADER.format(response_format="json",
                                                 vcd_auth_key=vcd_session_key)
        header = json.loads(header)
        payload = {
            "name": VcdCSE.VCDKE_CONFIG,
            "version": "1.0.0",
            "vendor": "vmware",
            "nss": "VCDKEConfig"
        }
        modified_payload = json.dumps(payload, indent=4)
        url = VcdApiEndpoint.CREATE_INTERFACE.format(vcd=vcd)
        current_app.logger.info("Creating Interface " + VcdCSE.VCDKE_CONFIG + "...")
        response = requests.request("POST", url, headers=header, data=modified_payload, verify=False)
        if response.status_code == 400:
            if response.text.__contains__("RDE_INTERFACE_ALREADY_EXISTS"):
                current_app.logger.info("Interface " + VcdCSE.VCDKE_CONFIG + " already created")
            else:
                return False, "Failed to create interface"
        elif response.status_code == 201:
            current_app.logger.info("Interface " + VcdCSE.VCDKE_CONFIG + " created successfully")
        else:
            current_app.logger.error(response.text)
            return False, "Interface creation failed"

        current_app.logger.info("Creating VCDKEConfig entity...")
        url = VcdApiEndpoint.CREATE_ENTITIES.format(vcd=vcd)
        with open(VcdCSE.CKE_INTERFACE_TEMPLATE) as f:
            data = json.load(f)
        modified_payload = json.dumps(data, indent=4)
        response_entity = requests.request("POST", url, headers=header, data=modified_payload, verify=False)
        if response_entity.status_code == 400:
            vcdke_access = False
            if response.text.__contains__("RDE_TYPE_ALREADY_EXISTS"):
                current_app.logger.info("VCDKEConfig entity is already created")
        elif response_entity.status_code == 201:
            current_app.logger.info("VCDKEConfig entity created successfully")
        else:
            current_app.logger.error(response_entity.text)
            return False, "VCDKEConfig entity creation failed"

        current_app.logger.info("Creating capvcdCluster entity...")
        with open(VcdCSE.CAP_INTERFACE_TEMPLATE) as f:
            data = json.load(f)

        modified_payload = json.dumps(data, indent=4)
        response_entity = requests.request("POST", url, headers=header, data=modified_payload, verify=False)
        if response_entity.status_code == 201:
            current_app.logger.info("capvcdCluster entity created successfully")
        elif response_entity.status_code == 400:
            capvc_access = False
            if response.text.__contains__("RDE_TYPE_ALREADY_EXISTS"):
                current_app.logger.info("capvcdCluster entity is already created")
        else:
            current_app.logger.error(response_entity.text)
            return False, "VCDKEConfig entity creation failed"

        current_app.logger.info("Creating access control for both the entities")

        org_name = vcdspec.envSpec.cseSpec.svcOrgSpec.svcOrgName
        org_id = None
        org_list = get_org_vcd_list(vcdspec, vcd)
        if org_list[0] is None:
            return False, org_list[1]

        else:
            org_list = org_list[2]
            for record in org_list.json()["values"]:
                if record["name"].strip() == org_name:
                    org_id = record["id"].strip()
                    break

        if org_id is None:
            return False, "Failed to find organization details"

        access_payload = {
            "tenant": {
                "name": "System",
                "id": org_id
            },
            "grantType": "MembershipAccessControlGrant",
            "accessLevelId": "urn:vcloud:accessLevel:FullControl",
            "memberId": org_id
        }
        access_payload_json = json.dumps(access_payload, indent=4)
        if vcdke_access:
            url = VcdApiEndpoint.ENTITY_ACCESS_CONTROL.format(vcd=vcd, config_type=VcdCSE.VCDKE_CONFIG)
            access_response = requests.request("POST", url, headers=header, data=access_payload_json, verify=False)
            if access_response.status_code != 201:
                current_app.logger.error(access_response.text)
                return False, "Access control creation for VCDKEConfig failed"
            current_app.logger.info("access control creation passed for VCDKEConfig")
        else:
            current_app.logger.info("Access control for VCDKEConfig is already created")

        if capvc_access:
            url = VcdApiEndpoint.ENTITY_ACCESS_CONTROL.format(vcd=vcd, config_type=VcdCSE.CAPVCD_CONFIG)
            access_response = requests.request("POST", url, headers=header, data=access_payload_json, verify=False)
            if access_response.status_code != 201:
                return False, "Access control creation for capvcdCluster failed"
            current_app.logger.info("access control creation passed for capvcdCluster")
        else:
            current_app.logger.info("Access control for capvcdCluster is already created")

        return True, "Interface and Entities created successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while creating Interfaces and Entities"
