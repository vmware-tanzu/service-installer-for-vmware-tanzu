#!/usr/bin/env python
import json
import os
import os.path
import ssl
import sys
import tarfile
import time
import logging
import socket
import hashlib
import uuid
from flask import jsonify, request
from flask import Flask
import requests
from flask import current_app
from flask import Blueprint

vcenter_resources = Blueprint("vcenter_listResources", __name__, static_folder="listResources")

# from src.aviConfig.vsphere_avi_config import vcenter_avi_config

logger = logging.getLogger(__name__)

from pyVim import connect
from pyVim.connect import Disconnect
import atexit
import base64
# import env_variables
import requests
from pyVmomi import vim
from flask import Flask, request

# sys.path.append("../")
from common.operation.vcenter_operations import get_dc, get_ds, get_rp
from common.prechecks.precheck import get_cluster, getNetwork, checkClusterNamespace, \
    getClusterVersionsFullList
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from common.operation.ShellHelper import runShellCommandWithPolling
from common.operation.constants import Env, MarketPlaceUrl, TmcUser
from common.common_utilities import envCheck, getProductSlugId, enableProxy, \
    getListOfTransportZone, getStoragePolicies, isEnvTkgs_wcp, KubernetesOva, checkClusterStateOnTmc, isEnvTkgs_ns, \
    getClusterID, fetchNamespaceInfo, validate_backup_location, validate_cluster_credential, list_cluster_groups, \
    fetchTMCHeaders
from common.operation.constants import Env, VeleroAPI
from common.common_utilities import envCheck, enableProxy, getListOfTransportZone, getStoragePolicies, isWcpEnabled
from common.session.session_acquire import fetch_vmc_env
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList, runProcess

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
__author__ = 'Tasmiya'


@vcenter_resources.route("/api/tanzu/tier1_details", methods=['POST'])
def getTer1Details():
    try:
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
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["nsxtUserPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")

        ecod_bytes = (request.get_json(force=True)['envSpec']['vcenterDetails']["nsxtUser"] + ":" + password).encode(
            "ascii")
        ecod_bytes = base64.b64encode(ecod_bytes)
        address = str(request.get_json(force=True)['envSpec']['vcenterDetails']["nsxtAddress"])
        ecod_string = ecod_bytes.decode("ascii")
        uri = "https://" + address + "/policy/api/v1/infra/tier-1s"
        headers = {'Authorization': (
                'Basic ' + ecod_string)}
        response = requests.request(
            "GET", uri, headers=headers, verify=False)
        if response.status_code != 200:
            current_app.logger.error("Failed to get tier1 details, failed to fetch from api " + response.text)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get tier1 details, failed to fetch from api " + response.text,
                "ERROR_CODE": 500
            }
            return jsonify(d), response.status_code
        list_of_display_name = []
        for result in response.json()["results"]:
            list_of_display_name.append(result["display_name"])
        if len(list_of_display_name) < 1:
            current_app.logger.error("Failed to get tier1 details, list is empty ")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get tier1 details, list is empty ",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        list_zones = getListOfTransportZone(address, headers)
        if list_zones[0] is None:
            current_app.logger.error("Failed to get list of transport zones " + str(list_zones[1]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get list of transport zones " + str(list_zones[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully got tier1 details ",
            "ERROR_CODE": 200,
            "TIER1_DETAILS": list_of_display_name,
            "OVERLAY_LIST": list_zones[0]
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Failed to get details of nsxt tier 1 " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get details of nsxt tier 1 " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/listResources", methods=['POST'])
def listResources():
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
    si = None
    errors = []
    current_app.config['DEPLOYMENT_PLATFORM'] = env
    current_app.logger.info("Fetching the list of resources on environment")
    if env == Env.VSPHERE or env == Env.VCF:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")

    elif env == Env.VMC:
        status = fetch_vmc_env(request.get_json(force=True))
        if status[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to capture VMC setup details ",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        vCenter = current_app.config['VC_IP']
        vCenter_user = current_app.config['VC_USER']
        VC_PASSWORD = current_app.config['VC_PASSWORD']

        if not (vCenter or vCenter_user or VC_PASSWORD):
            current_app.logger.error('Failed to fetch VC details')
            d = {
                "responseType": "ERROR",
                "msg": "Failed to find VC details",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

    try:
        si = connect.SmartConnectNoSSL(host=vCenter, user=vCenter_user, pwd=VC_PASSWORD)
        content = si.RetrieveContent()
        # if datacenter itself is not found, fail
        try:
            datacenterss = get_dc(si, None)
        except Exception as e:
            current_app.logger.error(e)
            d = {
                "responseType": "ERROR",
                "msg": "No datacenters found " + str(e),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        datacenter_names = []
        clusters = []
        datastores = []
        networks = []
        resource_pools = []
        library_files = []
        library_names = []
        for dc in datacenterss:
            try:
                clusters.extend(get_cluster(dc, None))
            except Exception as e:
                errors.append(e)

            try:
                datastores.extend(get_ds(dc, None))
            except Exception as e:
                errors.append(e)

            try:
                networks.extend(getNetwork(dc, None))
            except Exception as e:
                errors.append(e)

            try:
                rp = get_rp(si, dc, None)
                if rp:
                    resource_pools.extend(rp)
            except Exception as e:
                errors.append(e)

            try:
                datacenter_names.append(dc.name)
            except Exception as e:
                errors.append(e)

        try:
            files, names = getLibraryFile(vCenter, vCenter_user, VC_PASSWORD)
            library_files.extend(files)
            library_names.extend(names)
        except Exception as e:
            errors.append(e)

        if errors:
            current_app.logger.error("Failed with following errors")
            for error in errors:
                current_app.logger.error(error)
            d = {
                "responseType": "ERROR",
                "msg": "Failed " + str(errors),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("Printing all resources found on vCenter: " + vCenter)
        current_app.logger.info("Datacenters: ")
        current_app.logger.info(datacenter_names)
        current_app.logger.info("Clusters: ")
        current_app.logger.info(clusters)
        current_app.logger.info("Datastores: ")
        current_app.logger.info(datastores)
        current_app.logger.info("Network PortGroups: ")
        current_app.logger.info(networks)
        current_app.logger.info("Resource Pools: ")
        current_app.logger.info(resource_pools)
        current_app.logger.info('Content Library names:')
        current_app.logger.info(library_names)
        current_app.logger.info('Content Library Image Files:')
        current_app.logger.info(library_files)

    except IOError as e:
        atexit.register(Disconnect, si)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to connect to vcenter. " + str(e),
            "ERROR_CODE": 500
        }
        current_app.logger.error("Failed to connect to vcenter. " + str(e))
        return jsonify(d), 500

    d = {
        "responseType": "SUCCESS",
        "msg": "Obtained the list of resources Successfully",
        "ERROR_CODE": 200,
        "DATACENTERS": datacenter_names,
        "DATASTORES": datastores,
        "CLUSTERS": clusters,
        "NETWORKS": networks,
        "RESOURCEPOOLS": resource_pools,
        "CONTENTLIBRARY_FILES": library_files,
        "CONTENTLIBRARY_NAMES": library_names
    }
    current_app.logger.info("Obtained the list of resources Successfully")
    return jsonify(d), 200


def getVCthumbprint():
    current_app.logger.info("Fetching VC thumbprint")
    try:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterAddress"]
    except:
        current_app.logger.error('Failed to fetch VC details')
        return 500
    if not vCenter:
        current_app.logger.error('Failed to fetch VC details')
        return 500

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    wrappedSocket = ssl.wrap_socket(sock)
    try:
        wrappedSocket.connect((vCenter, 443))
    except:
        current_app.logger.error('vCenter connection failed')
        return 500

    der_cert_bin = wrappedSocket.getpeercert(True)
    pem_cert = ssl.DER_cert_to_PEM_cert(wrappedSocket.getpeercert(True))

    # Thumbprint
    thumb_md5 = hashlib.md5(der_cert_bin).hexdigest()
    thumb_sha1 = hashlib.sha1(der_cert_bin).hexdigest()
    thumb_sha256 = hashlib.sha256(der_cert_bin).hexdigest()
    wrappedSocket.close()
    if thumb_sha1:
        thumb_sha1 = thumb_sha1.upper()
        thumb_sha1 = ':'.join(thumb_sha1[i:i + 2] for i in range(0, len(thumb_sha1), 2))
        current_app.logger.info("SHA1 : " + thumb_sha1)
        return thumb_sha1
    else:
        current_app.logger.error('Failed to obtain VC SHA1')
        return 500


@vcenter_resources.route("/api/tanzu/getThumbprint", methods=['POST'])
def getthumbprint():
    thumb_sha1 = getVCthumbprint()
    if thumb_sha1 != 500:
        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained VC thumbprint Successfully",
            "ERROR_CODE": 200,
            "SHA1": thumb_sha1
        }
        current_app.logger.info("Obtained VC thumbprint Successfully")
        return jsonify(d), 200
    else:
        d = {
            "responseType": "ERROR",
            "msg": "Failed to obtain VC thumbprint",
            "ERROR_CODE": 500
        }
        current_app.logger.info("Failed to obtain VC thumbprint")
        return jsonify(d), 500


def getLibraryFile(vcIp, vcUser, vcPassword):
    url = "https://" + vcIp + "/"
    vCenter_user = vcUser
    VC_PASSWORD = vcPassword
    file_list = []
    item_list = []
    library_Names = []

    if not (vCenter_user or VC_PASSWORD):
        raise Exception('VCenter credentials are empty')

    try:
        sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            raise Exception('Failed to obtain session id for vCenter in content library module')
        else:
            session_id = sess.json()['value']

        resp = requests.get(url + "rest/com/vmware/content/library", verify=False, headers={
            "vmware-api-session-id": session_id
        })
        if resp.status_code != 200:
            raise Exception('API to obtain Content Library ids for vCenter failed')

        library_ids = []
        library_ids.extend(resp.json()['value'])

        for library in library_ids:
            library_item = requests.get(url + "rest/com/vmware/content/library/item?library_id=" + library,
                                        verify=False, headers={
                    "vmware-api-session-id": session_id
                })

            if library_item.status_code != 200:
                raise Exception('API to obtain item ids for content Library Failed')
            else:
                item_list.extend(library_item.json()['value'])

            lib_name = requests.get(url + "rest/com/vmware/content/library/id:" + library, verify=False, headers={
                "vmware-api-session-id": session_id
            })

            if lib_name.status_code != 200:
                raise Exception('API to obtain content Library name Failed')
            else:
                library_Names.append(lib_name.json()['value']['name'])

        for item in item_list:
            resp_new_item = requests.get(url + "rest/com/vmware/content/library/item/id:" + item, verify=False,
                                         headers={
                                             "vmware-api-session-id": session_id})

            if resp_new_item.status_code != 200:
                raise Exception('API to Obtain item details failed')

            file_list.append(resp_new_item.json()['value']['name'])
        return file_list, library_Names

    except Exception as e:
        current_app.logger.error(e)
        raise Exception('Failed to execute vCenter REST APIs to fetch content library details')


@vcenter_resources.route("/api/tanzu/getContentLibraryFiles", methods=['POST'])
def getFilesInContentLibrary():
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
    current_app.logger.info("Fetching the list of resources on environment")
    if env == Env.VSPHERE or env == Env.VCF:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
        library_name = request.get_json(force=True)['envSpec']['vcenterDetails']['contentLibraryName']
    elif env == Env.VMC:
        status = fetch_vmc_env(request.get_json(force=True))
        if status[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to capture VMC setup details ",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        vCenter = current_app.config['VC_IP']
        vCenter_user = current_app.config['VC_USER']
        VC_PASSWORD = current_app.config['VC_PASSWORD']
        library_name = request.get_json(force=True)['envSpec']['contentLibraryName']

    if not (vCenter_user or VC_PASSWORD):
        d = {
            "responseType": "ERROR",
            "msg": "vCenter details are missing",
            "ERROR_CODE": 500,
            "CONTENT_LIBRARY_FILES": None
        }
        current_app.logger.error("vCenter details are missing")
        return jsonify(d), 500

    if not library_name:
        d = {
            "responseType": "ERROR",
            "msg": "Library name field is empty, please provide a content library name",
            "ERROR_CODE": 500,
            "CONTENT_LIBRARY_FILES": None
        }
        current_app.logger.error("Library name field is empty, please provide a content library name")
        return jsonify(d), 500

    url = "https://" + vCenter + "/"
    file_list = []
    item_list = []

    try:
        '''sess = requests.post(url + "rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD), verify=False)
        if sess.status_code != 200:
            raise Exception('Failed to obtain session id for vCenter in content library module')
        else:
            session_id = sess.json()['value']

        resp = requests.get(url + "rest/com/vmware/content/library", verify=False, headers={
            "vmware-api-session-id": session_id
        })
        current_app.logger.info("========================First API")
        current_app.logger.info(resp.json())
        if resp.status_code != 200:
            raise Exception('API to obtain Content Library ids for vCenter failed')

        library_ids = []
        library_ids.extend(resp.json()['value'])

        for library in library_ids:
            getLibrary_id = requests.get(url + "api/content/library/" + library, verify=False, headers={
                "vmware-api-session-id": session_id})
            if getLibrary_id.status_code != 200:
                raise Exception('API to obtain Content Library Names for vCenter failed')

            if library_name.strip() == getLibrary_id.json()["name"].strip():
                library_item = requests.get(url + "rest/com/vmware/content/library/item?library_id=" + library,
                                            verify=False, headers={"vmware-api-session-id": session_id})

                current_app.logger.info("========================second API")
                current_app.logger.info(library_item.json())
                if library_item.status_code != 200:
                    raise Exception('API to obtain item ids for content Library Failed')
                else:
                    item_list.extend(library_item.json()['value'])

        for item in item_list:
            resp_new_item = requests.get(url + "rest/com/vmware/content/library/item/id:" + item, verify=False,
                                         headers={
                                             "vmware-api-session-id": session_id})

            current_app.logger.info("========================Third API")
            current_app.logger.info(resp_new_item.json())

            if resp_new_item.status_code != 200:
                raise Exception('API to Obtain item details failed')

            file_list.append(resp_new_item.json()['value']['name'])
            current_app.logger.info("Files in library - " + library_name)
            current_app.logger.info(file_list)
        if not file_list:
            d = {
                "responseType": "ERROR",
                "msg": "No files available in given content library",
                "ERROR_CODE": 500,
                "CONTENT_LIBRARY_FILES": None
            }
            current_app.logger.error("No files available in given content library")
            return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained list of files for given Content Library",
            "ERROR_CODE": 200,
            "CONTENT_LIBRARY_FILES": file_list
        }
        current_app.logger.info("Obtained list of files for given Content Library")
        return jsonify(d), 200'''

        response = getfiles_content(vCenter, vCenter_user, VC_PASSWORD, library_name)
        current_app.logger.info(response[0])
        if response[0] is None:
            current_app.logger.error(response[1])
            d = {
                "responseType": "ERROR",
                "msg": response[0].json["msg"],
                "ERROR_CODE": 500,
                "CONTENT_LIBRARY_FILES": None
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Found below items in Content Library - " + library_name)
            file_list=[]
            for item in response[0]:
                file_list.append(item[0])
            current_app.logger.info(file_list)
            d = {
                "responseType": "SUCCESS",
                "msg": "Obtained list of files for given Content Library",
                "ERROR_CODE": 200,
                "CONTENT_LIBRARY_FILES": file_list
            }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to obtain files for given content library: "+library_name,
            "ERROR_CODE": 500,
            "CONTENT_LIBRARY_FILES": None
        }
        current_app.logger.error("Failed to obtain files for given content library: "+library_name)
        return jsonify(d), 500


def getfiles_content(vCenter, vCenter_user, VC_PASSWORD, library_name):
    os.putenv("GOVC_URL", "https://" + vCenter + "/sdk")
    os.putenv("GOVC_USERNAME", vCenter_user)
    os.putenv("GOVC_PASSWORD", VC_PASSWORD)
    os.putenv("GOVC_INSECURE", "true")
    get_library_command = ["govc", "library.ls"]
    file_list = []

    get_status = runShellCommandAndReturnOutputAsList(get_library_command)
    if get_status[1] != 0:
        current_app.logger.error(get_status[0])
        return None, "Failed to fetch content libraries"

    if "/"+library_name in get_status[0]:
        fetch_files_command = ["govc", "library.ls", "/" + library_name + "/"]
        files_status = runShellCommandAndReturnOutputAsList(fetch_files_command)
        if files_status[1] != 0:
            current_app.logger.error("Failed to fetch files from given content library -" + library_name)
            return None, "Failed to fetch files from given content library -" + library_name
        elif not files_status[0]:
            return None, "Content Library is empty - ", library_name
        else:
            for item in files_status[0]:
                file_list.append(item.split("/")[-1:])
            return file_list, "Successfully obtained files in given content library"
    else:
        current_app.logger.error("Provided content library not found")
        return None, "Provided content library not found"


@vcenter_resources.route("/api/tanzu/storagePolicies", methods=['POST'])
def storagePolicies():
    try:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
        policies = getStoragePolicies(vCenter, vCenter_user, VC_PASSWORD)
        policies_list = []
        for policy in policies[0]:
            policies_list.append(policy["name"])
        current_app.logger.info(policies_list)
        if policies_list:
            d = {
                "responseType": "SUCCESS",
                "msg": "Obtained VC Storage Policies Successfully",
                "ERROR_CODE": 200,
                "STORAGE_POLICIES": policies_list
            }
            current_app.logger.info("Obtained VC Storage Policies Successfully")
            return jsonify(d), 200
        else:
            d = {
                "responseType": "ERROR",
                "msg": "No Storage Policies found",
                "ERROR_CODE": 500,
                "STORAGE_POLICIES": policies_list
            }
            current_app.logger.error("No Storage Policies found")
            return jsonify(d), 500
    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Storage Policies",
            "ERROR_CODE": 500,
            "STORAGE_POLICIES": None
        }
        current_app.logger.error("Exception occurred while fetching Storage Policies")
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/listvmclasses", methods=['POST'])
def listvmclasses():
    try:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
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
        vm_classes_response = requests.request("GET", url + "api/vcenter/namespace-management/virtual-machine-classes",
                                               headers=header, verify=False)
        if vm_classes_response.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch VM classes",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        vm_classes = []
        for vmclass in vm_classes_response.json():
            vm_classes.append(vmclass["id"])
        current_app.logger.info(vm_classes)
        if vm_classes:
            d = {
                "responseType": "SUCCESS",
                "msg": "Obtained list of VM Classes Successfully",
                "ERROR_CODE": 200,
                "VM_CLASSES": vm_classes
            }
            current_app.logger.info("Obtained list of VM Classes Successfully")
            return jsonify(d), 200
        else:
            d = {
                "responseType": "ERROR",
                "msg": "No VM Class found",
                "ERROR_CODE": 500,
                "VM_CLASSES": vm_classes
            }
            current_app.logger.error("No VM Class found")
            return jsonify(d), 500
    except Exception as e:
        current_app.logger.error(e)
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching VM Class list",
            "ERROR_CODE": 500,
            "VM_CLASSES": None
        }
        current_app.logger.error("Exception occurred while fetching VM Class list")
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/getkubeversions", methods=['POST'])
def getKubernetesOvaVersions():
    solutionName = KubernetesOva.MARKETPLACE_KUBERNETES_SOLUTION_NAME
    kubeVersionList = []
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
    if env == Env.VMC:
        refToken = request.get_json(force=True)['marketplaceSpec']['refreshToken']
    elif env == Env.VSPHERE or env == Env.VCF:
        refToken = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
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
    if str(MarketPlaceUrl.API_URL).__contains__("stg"):
        slug = "false"
    else:
        slug = "true"
    _solutionName = getProductSlugId(MarketPlaceUrl.AVI_PRODUCT, headers)
    if _solutionName[0] is None:
        return None, "Failed to find product on Marketplace "+str(_solutionName[1])
    solutionName = _solutionName[0]

    product = requests.get(
        MarketPlaceUrl.API_URL + "/products/" + solutionName + "?isSlug=" + slug + "&ownorg=false", headers=headers,
        verify=False)

    if product.status_code != 200:
        current_app.logger.error("Failed to Obtain product details from MarketPlace for solution " + solutionName)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to Obtain product details from MarketPlace for solution " + solutionName,
            "ERROR_CODE": 500,
            "KUBE_VERSION_LIST": None
        }
        return jsonify(d), 500
    else:
        for metalist in product.json()['response']['data']['metafilesList']:
            if metalist["groupname"] == (KubernetesOva.MARKETPLACE_PHOTON_GROUPNAME or
                                         KubernetesOva.MARKETPLACE_UBUTNU_GROUPNAME):
                version = "v" + metalist["version"]
                if version not in kubeVersionList:
                    kubeVersionList.append(version)

    if not kubeVersionList:
        current_app.logger.error("Version list for Kubernetes OVA in MarketPlace is found empty")
        d = {
            "responseType": "ERROR",
            "msg": "Version list for Kubernetes OVA in MarketPlace is found empty",
            "ERROR_CODE": 500,
            "KUBE_VERSION_LIST": None
        }
        return jsonify(d), 500
    else:
        current_app.logger.info("Kubernetes OVA version list obtained successfully from MarketPlace")
        d = {
            "responseType": "SUCCESS",
            "msg": "Kubernetes OVA version list obtained successfully from MarketPlace",
            "ERROR_CODE": 200,
            "KUBE_VERSION_LIST": kubeVersionList
        }
        return jsonify(d), 200


@vcenter_resources.route("/api/tanzu/getWCPEnabledClusters", methods=['POST'])
def getWCPEnabledClusters():
    try:
        wcp_cluster = []
        vcenter_ip = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
        datacenter_name = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']

        if not (vcenter_ip or vCenter_user or VC_PASSWORD):
            current_app.logger.error('Failed to fetch VC details')
            d = {
                "responseType": "ERROR",
                "msg": "Failed to find VC details",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        si = connect.SmartConnectNoSSL(host=vcenter_ip, user=vCenter_user, pwd=VC_PASSWORD)

        datacenter = get_dc(si, datacenter_name)
        cluster_list = get_cluster(datacenter, None)
        if not cluster_list:
            current_app.logger.error("No clusters found under selected datacenter - " + datacenter_name)
            d = {
                "responseType": "ERROR",
                "msg": "No clusters found under selected datacenter - " + datacenter_name,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        for cluster in cluster_list:
            isWCP = isWcpEnabled(getClusterID(vcenter_ip, vCenter_user, VC_PASSWORD, cluster)[0])
            if isWCP[0]:
                wcp_cluster.append(cluster)
            else:
                current_app.logger.info("WCP is not enabled on cluster: " + cluster + ". Hence not added to list")

        if not wcp_cluster:
            current_app.logger.error("WCP enabled cluster list is empty")
            d = {
                "responseType": "ERROR",
                "msg": "WCP enabled clusters not found",
                "ERROR_CODE": 500,
                "WCP_CLUSTER_LIST": wcp_cluster
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Below is the List of WCP enabled clusters : ")
            current_app.logger.info(wcp_cluster)
            d = {
                "responseType": "SUCCESS",
                "msg": "WCP enabled clusters found successfully",
                "ERROR_CODE": 200,
                "WCP_CLUSTER_LIST": wcp_cluster
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching WCP enabled clusters " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def get_VCSession():
    try:
        env = envCheck()
        env = env[0]
        if env == Env.VSPHERE or env == Env.VCF:
            vcenter_ip = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
            vcenter_username = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode('ascii').rstrip("\n")
        elif env == Env.VMC:
            status = fetch_vmc_env(request.get_json(force=True))
            if status[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to capture VMC setup details ",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            vcenter_ip = current_app.config['VC_IP']
            vcenter_username = current_app.config['VC_USER']
            password = current_app.config['VC_PASSWORD']

        if not (vcenter_ip or vcenter_username or password):
            return None, "Failed to fetch VC details"

        sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                             auth=(vcenter_username, password), verify=False)
        if sess.status_code != 200:
            current_app.logger.error("Connection to vCenter failed")
            return None, "Connection to vCenter failed"
        else:
            return sess.json()['value'], "Obtained vCenter session successfully"
    except Exception as e:
        return None, str(e)


@vcenter_resources.route("/api/tanzu/getWorkloadNetworks", methods=['POST'])
def getWorkloadNetworks():
    try:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
        vcenter_username = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")
        workload_networks = []
        cluster_id = getClusterID(vCenter, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[0])
            d = {
                "responseType": "ERROR",
                "msg": cluster_id[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        cluster_id = cluster_id[0]
        vc_session = get_VCSession()
        if vc_session[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": vc_session[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        vc_session = vc_session[0]

        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": vc_session
            }

        url = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/"+cluster_id+"/networks"
        response_networks = requests.request("GET", url, headers=header, verify=False)
        if response_networks.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch workload networks for cluster - " + cluster,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        for network in response_networks.json():
            workload_networks.append(network["network"])

        if not workload_networks:
            current_app.logger.error("No workload network found on cluster - " + cluster)
            d = {
                "responseType": "ERROR",
                "msg": "No workload network found on cluster - " + cluster,
                "ERROR_CODE": 500,
                "WORKLOAD_NETWORKS": workload_networks
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Below are the list of workload networks found on cluster - " + cluster)
            current_app.logger.info(workload_networks)
            d = {
                "responseType": "SUCCESS",
                "msg": "workload networks found successfully on cluster - " + cluster,
                "ERROR_CODE": 200,
                "WORKLOAD_NETWORKS": workload_networks
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Exception occurred while fetching workload networks for given cluster - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching workload networks for given cluster - " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/getClusterVersions", methods=['POST'])
def getClusterVersions():
    try:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
        vcenter_username = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")
        cluster_versions = []

        versions_output = getClusterVersionsFullList(vCenter, vcenter_username, password, cluster)
        if versions_output[1] != 200:
            current_app.logger.error(versions_output[0].json["msg"])
            d = {
                "responseType": "ERROR",
                "msg": versions_output[0].json["msg"],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        for version in versions_output[0]:
            value_list = version.split()
            if (value_list[2] and value_list[3]) == "True":
                cluster_versions.append('v'+value_list[1])

        if not cluster_versions:
            current_app.logger.error("Cluster versions list is empty")
            d = {
                "responseType": "ERROR",
                "msg": "Cluster versions list is empty",
                "ERROR_CODE": 500,
                "CLUSTER_VERSIONS": cluster_versions
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Below is the list of cluster versions found - ")
            current_app.logger.info(cluster_versions)
            d = {
                "responseType": "SUCCESS",
                "msg": "Cluster versions obtained successfully",
                "ERROR_CODE": 200,
                "CLUSTER_VERSIONS": cluster_versions
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Exception occurred while fetching cluster versions - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching cluster versions - " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/getAllNamespaces", methods=['POST'])
def getAllNamespaces():
    try:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
        vcenter_username = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")
        namespaces_list = []
        vc_session = get_VCSession()
        if vc_session[0] is None:
            return False, vc_session[1]
        vc_session = vc_session[0]

        cluster_id = getClusterID(vCenter, vcenter_username, password, cluster)
        if cluster_id[1] != 200:
            current_app.logger.error(cluster_id[0])
            d = {
                "responseType": "ERROR",
                "msg": cluster_id[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        cluster_id = cluster_id[0]

        header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vmware-api-session-id": vc_session
        }

        url = "https://" + vCenter + "/api/vcenter/namespaces/instances"
        response_namespaces = requests.request("GET", url, headers=header, verify=False)
        if response_namespaces.status_code != 200:
            current_app.logger.error("Failed to get all namespaces for cluster - " + cluster)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get all namespaces for cluster - " + cluster,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        for cls_id in response_namespaces.json():
            if cls_id["cluster"] == cluster_id and cls_id["config_status"] == "RUNNING":
                namespaces_list.append(cls_id["namespace"])

        if namespaces_list:
            current_app.logger.info("Below is the list of all namespaces found in cluster - " + cluster)
            current_app.logger.info(namespaces_list)
            d = {
                "responseType": "SUCCESS",
                "msg": "Obtained namespaces for given cluster successfully",
                "ERROR_CODE": 200,
                "NAMESPACES_LIST": namespaces_list
            }
            return jsonify(d), 200
        else:
            current_app.logger.error("No namespaces found under cluster - " + cluster)
            d = {
                "responseType": "SUCCESS",
                "msg": "No namespaces found under cluster - " + cluster,
                "ERROR_CODE": 200,
                "NAMESPACES_LIST": namespaces_list
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Exception occurred while fetching namespaces list for given cluster - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching namespaces list for given cluster - " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/getSupervisorClusters", methods=['POST'])
def getSupervisorClusters():
    try:
        os.putenv("TMC_API_TOKEN",
                  request.get_json(force=True)["saasEndpoints"]['tmcDetails']['tmcRefreshToken'])
        user = TmcUser.USER
        listOfCmdTmcLogin = ["tmc", "login", "--no-configure", "-name", user]
        runProcess(listOfCmdTmcLogin)
        cls_list = []
        command = ["tmc", "managementcluster", "list"]
        output = runShellCommandAndReturnOutputAsList(command)
        if output[1] != 0:
            current_app.logger.error("Failed to fetch list of supervisor cluster " + str(output[0]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch list of supervisor cluster " + str(output[0]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        cls_list = [s.strip() for s in output[0]]
        for elem in cls_list:
            if elem.__contains__("NAME"):
                cls_list.remove(elem)
            elif elem.__contains__("type:management"):
                cls_list.remove(elem)
                elem = elem.replace("type:management", "")
                cls_list.append(elem.strip())
        if cls_list:
            current_app.logger.info("Below is the list of supervisor clusters")
            current_app.logger.info(cls_list)
            d = {
                "responseType": "SUCCESS",
                "msg": "Obtained list of supervisor clusters successfully",
                "ERROR_CODE": 200,
                "NAMESPACES_LIST": cls_list
            }
            return jsonify(d), 200
        else:
            current_app.logger.error("No supervisor clusters found!")
            d = {
                "responseType": "ERROR",
                "msg": "No supervisor clusters found!",
                "ERROR_CODE": 500,
                "NAMESPACES_LIST": cls_list
            }
            return jsonify(d), 500
    except Exception as e:
        current_app.logger.error("Exception occurred while fetching supervisor clusters list - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching supervisor clusters list - " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/getSupervisorClusterHealth", methods=['POST'])
def getSupervisorClusterHealth():
    try:
        super_cluster = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails']['tmcSupervisorClusterName']
        state = checkClusterStateOnTmc(super_cluster, True)
        if state[0] == "SUCCESS":
            current_app.logger.info("Selected supervisor cluster is registered to TMC")
            d = {
                "responseType": "SUCCESS",
                "msg": "Selected supervisor cluster is registered to TMC",
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
        else:
            current_app.logger.error("Selected supervisor cluster is not registered to TMC!")
            d = {
                "responseType": "ERROR",
                "msg": "Selected supervisor cluster is not registered to TMC",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    except Exception as e:
        current_app.logger.error("Exception occurred while fetching supervisor clusters state on TMC - " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching supervisor clusters state on TMC - " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/getClusters", methods=['POST'])
def getClusters():
    try:
        clusters = []
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
        if env == Env.VSPHERE or env == Env.VCF:
            vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
            vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
            datacenter_name = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']

        elif env == Env.VMC:
            status = fetch_vmc_env(request.get_json(force=True))
            if status[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to capture VMC setup details ",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            vCenter = current_app.config['VC_IP']
            vCenter_user = current_app.config['VC_USER']
            VC_PASSWORD = current_app.config['VC_PASSWORD']
            datacenter_name = request.get_json(force=True)['envSpec']['sddcDatacenter']

            if not (vCenter or vCenter_user or VC_PASSWORD):
                current_app.logger.error('Failed to fetch VC details')
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to find VC details",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500

        si = connect.SmartConnectNoSSL(host=vCenter, user=vCenter_user, pwd=VC_PASSWORD)

        datacenter = get_dc(si, datacenter_name)
        clusters = get_cluster(datacenter, None)
        if not clusters:
            current_app.logger.error("No clusters found under selected datacenter - " + datacenter_name)
            d = {
                "responseType": "ERROR",
                "msg": "No clusters found under selected datacenter - " + datacenter_name,
                "ERROR_CODE": 500,
                "CLUSTERS": clusters
            }
            return jsonify(d), 500

        if isEnvTkgs_wcp(env):
            for cls in clusters:
                namespace_status = checkClusterNamespace(vCenter, vCenter_user, VC_PASSWORD, cls)
                if namespace_status[1] != 200:
                    clusters.remove(cls)
            if not clusters:
                current_app.logger.error("No vSphere Namespace compatible cluster found")
                d = {
                    "responseType": "ERROR",
                    "msg": "No vSphere Namespace compatible cluster found",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500

        if isEnvTkgs_ns(env):
            wcp_clusters = getWCPEnabledClusters()
            if wcp_clusters[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": wcp_clusters[0].json["msg"],
                    "ERROR_CODE": 500
                }
                current_app.logger.error(wcp_clusters[0].json["msg"])
                return jsonify(d), 500
            else:
                clusters = wcp_clusters[0].json["WCP_CLUSTER_LIST"]

        current_app.logger.info("Found below clusters on selected datacenter ")
        current_app.logger.info(clusters)
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully obtained clusters on given datacenter",
            "ERROR_CODE": 200,
            "CLUSTERS": clusters
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.info(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching list of clusters ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/getDatastores", methods=['POST'])
def getDatastores():
    try:
        datastores = []
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
        if env == Env.VSPHERE or env == Env.VCF:
            vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
            vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
            str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            base64_bytes = str_enc.encode('ascii')
            enc_bytes = base64.b64decode(base64_bytes)
            VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
            datacenter_name = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']

        elif env == Env.VMC:
            status = fetch_vmc_env(request.get_json(force=True))
            if status[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to capture VMC setup details ",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            vCenter = current_app.config['VC_IP']
            vCenter_user = current_app.config['VC_USER']
            VC_PASSWORD = current_app.config['VC_PASSWORD']
            datacenter_name = request.get_json(force=True)['envSpec']['sddcDatacenter']

            if not (vCenter or vCenter_user or VC_PASSWORD):
                current_app.logger.error('Failed to fetch VC details')
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to find VC details",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500

        si = connect.SmartConnectNoSSL(host=vCenter, user=vCenter_user, pwd=VC_PASSWORD)

        datacenter = get_dc(si, datacenter_name)
        datastores = get_ds(datacenter, None)
        if not datastores:
            current_app.logger.error("No datastores found under selected datacenter - " + datacenter_name)
            d = {
                "responseType": "ERROR",
                "msg": "No datastores found under selected datacenter - " + datacenter_name,
                "ERROR_CODE": 500,
                "DATASTORES": datastores
            }
            return jsonify(d), 500
        else:
            current_app.logger.info("Found below datastores on selected datacenter - ")
            current_app.logger.info(datastores)
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully obtained datastores on given datacenter",
                "ERROR_CODE": 200,
                "DATASTORES": datastores
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.info(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching list of datastores ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/getNamespaceDetails", methods=['POST'])
def getNamespaceDetails():
    try:
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

        namespace_info = fetchNamespaceInfo(env)
        if namespace_info[1] != 200:
            current_app.logger.error(namespace_info[0].json["msg"])
            d = {
                "responseType": "ERROR",
                "msg": namespace_info[0].json["msg"],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("Found namespace details successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": namespace_info[0].json["msg"],
            "ERROR_CODE": 200,
            "VM_CLASSES": namespace_info[0].json["VM_CLASSES"],
            "STORAGE_POLICIES": namespace_info[0].json["STORAGE_POLICIES"]
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching details for namespace - ",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/fetchClusterGroups", methods=['POST'])
def fetchClusterGroups():
    try:
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

        response = list_cluster_groups(env)
        if not response[0]:
            current_app.logger.error(response[1])
            d = {
                "responseType": "ERROR",
                "msg": response[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        cluster_groups = response[1]

        if not cluster_groups:
            current_app.logger.info("Cluster groups list for data protection is empty")
            d = {
                "responseType": "ERROR",
                "msg": "Cluster groups list for data protection is empty",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("Found below cluster groups")
        current_app.logger.info(cluster_groups)
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully obtained cluster groups",
            "ERROR_CODE": 200,
            "CLUSTER_GROUPS": cluster_groups
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.info(str(e))
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/fetchCredentials", methods=['POST'])
def fetchCredentials():
    try:
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

        tmc_header = fetchTMCHeaders(env)
        if tmc_header[0] is None:
            current_app.logger.error(tmc_header[1])
            d = {
                "responseType": "ERROR",
                "msg": tmc_header[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        credentials = []

        #url = tmc_url + "v1alpha1/account/credentials?search_scope.capability=DATA_PROTECTION"
        url = VeleroAPI.LIST_CREDENTIALS.format(tmc_url=tmc_header[1])

        response = requests.request("GET", url, headers=tmc_header[0], verify=False)
        if response.status_code != 200:
            current_app.logger.error("Failed to fetch data protection credentials")
            current_app.logger.error(response.json())
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch data protection credentials",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        for credential in response.json()["credentials"]:
            credentials.append(credential["fullName"]["name"])

        if not credentials:
            current_app.logger.error("Data Protection credentials list is empty")
            d = {
                "responseType": "ERROR",
                "msg": "Data Protection credentials list is empty",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("Below is the list of data protection credentials found")
        current_app.logger.info(credentials)
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully obtained data protection credentials",
            "ERROR_CODE": 200,
            "CREDENTIALS": credentials
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.info(str(e))
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/fetchTargetLocations", methods=['POST'])
def fetchTargetLocations():
    try:
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

        tmc_header = fetchTMCHeaders(env)
        if tmc_header[0] is None:
            current_app.logger.error(tmc_header[1])
            d = {
                "responseType": "ERROR",
                "msg": tmc_header[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        target_locations = []

        #url = tmc_url + "v1alpha1/dataprotection/providers/tmc/backuplocations"
        url = VeleroAPI.LIST_BACKUP_LOCATIONS.format(tmc_url=tmc_header[1])

        response = requests.request("GET", url, headers=tmc_header[0], verify=False)
        if response.status_code != 200:
            current_app.logger.error("Failed to fetch target locations for data protection")
            current_app.logger.error(response.json())
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch target locations for data protection",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        for location in response.json()["backupLocations"]:
            target_locations.append(location["fullName"]["name"])

        if not target_locations:
            current_app.logger.error("Target locations list for Data Protection is empty")
            d = {
                "responseType": "ERROR",
                "msg": "Target locations list for Data Protection is empty",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info("Below is the list of target locations found")
        current_app.logger.info(target_locations)
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully obtained target locations",
            "ERROR_CODE": 200,
            "TARGET_LOCATIONS": target_locations
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.info(str(e))
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/validateCredentials", methods=['POST'])
def validateCredentials():
    try:
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

        cluster_type = request.get_json(force=True)["clusterType"]

        response = validate_cluster_credential(env, cluster_type)
        if not response[0]:
            d = {
                "responseType": "ERROR",
                "msg": response[1],
                "ERROR_CODE": 500
            }
            current_app.logger.error(response[1])
            return jsonify(d), 500
        else:
            current_app.logger.info(response[1])
            d = {
                "responseType": "SUCCESS",
                "msg": response[1],
                "ERROR_CODE": 200
            }
            return jsonify(d), 200

    except Exception as e:
        current_app.logger.info(str(e))
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


@vcenter_resources.route("/api/tanzu/validateTargetLocations", methods=['POST'])
def validateTargetLocations():
    try:
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

        cluster_type = request.get_json(force=True)["clusterType"]

        response = validate_backup_location(env, cluster_type)
        if not response[0]:
            d = {
                "responseType": "ERROR",
                "msg": response[1],
                "ERROR_CODE": 500
            }
            current_app.logger.error(response[1])
            return jsonify(d), 500
        else:
            current_app.logger.info(response[1])
            d = {
                "responseType": "SUCCESS",
                "msg": response[1],
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.info(str(e))
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500




