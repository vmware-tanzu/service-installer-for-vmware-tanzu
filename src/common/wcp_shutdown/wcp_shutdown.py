import logging
import requests
import json
import os

import subprocess
import ssl
import atexit
import time
import base64

from kubernetes import client
from kubernetes import config
from flask import current_app, request, jsonify, Blueprint
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim, vmodl

from common.operation.constants import Env
from common.session.session_acquire import login
from common.common_utilities import envCheck, isEnvTkgs_ns, isEnvTkgs_wcp

shutdown_env = Blueprint("shutdown_env", __name__, static_folder="wcp_shutdown")
logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
__author__ = 'Rashi'

@shutdown_env.route("/api/tanzu/wcp-bringup", methods=['POST'])
def wcp_bringup():
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
    login()
    if env == Env.VSPHERE:
        if isEnvTkgs_ns(env):
            current_app.logger.error(
                "Wrong spec file provided for cleanup, please use the spec file which was used "
                "for enabling WCP")
            d = {
                "responseType": "ERROR",
                "msg": "Wrong environment provided for cleanup",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
        vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']

        try:
            current_app.logger.info("\n")
            current_app.logger.info("STEP 0 - Logging into vCenter API with supplied credentials ")
            vc_service_instance = get_si(vCenter, vCenter_user, VC_PASSWORD)
            if not vc_service_instance[1]:
                current_app.logger.error("ERROR: Failed to retrieve Service Instance from the provided vCenter details")
                current_app.logger.debug(vc_service_instance[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "ERROR: Failed to retrieve Service Instance from the provided vCenter details",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            vc_service_instance = vc_service_instance[0]
            atexit.register(Disconnect, vc_service_instance)
            content = vc_service_instance.RetrieveContent()

        except vmodl.MethodFault as error:
            current_app.logger.error("ERROR: Caught vmodl fault : " + error.msg)
            current_app.logger.debug(error.msg)
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Caught vmodl fault",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        # Set REST VC Variables
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        headers = {'content-type': 'application/json'}
        s = "Global"
        s = requests.Session()
        s.verify = False

        # Connect to VCenter and start a REST session
        vcsession = s.post('https://' + vCenter + '/rest/com/vmware/cis/session', auth=(vCenter_user, VC_PASSWORD))
        if not vcsession.ok:
            current_app.logger.error("ERROR: Session creation is failed, please check vcenter connection")
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Session creation is failed, please check vcenter connection",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        token = json.loads(vcsession.text)["value"]

        restart_status = restart_vc_svcname(s, vCenter, "wcp")
        if not restart_status[1]:
            current_app.logger.error("ERROR: Unable to restart WCP Service")
            current_app.logger.debug(restart_status[0])
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Unable to restart WCP Service",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Successfully Restarted WCP services")

        ## Find Cluster object from Cluster Name specified in script parameter
        if vCenter_cluster:
            for cl in get_obj(content, vim.ComputeResource):
                if cl.name == vCenter_cluster:
                    cluster_id = str(cl).split(":")[1].rstrip('\'')
                    current_app.logger.info('Found the vSphere Cluster named: ' + vCenter_cluster + ' with ID ' + cluster_id)
                    break
                else:
                    current_app.logger.error('ERROR: Could NOT find cluster with name: ', vCenter_cluster)
                    current_app.logger.debug('DEBUG: Double check the Cluster Name. Exiting the program')
                    d = {
                        "responseType": "ERROR",
                        "msg": "ERROR: Could NOT find cluster with name: " + vCenter_cluster,
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
        timer = 0
        wcp_status = False
        while timer < 300:
            wcp_endpoint = check_wcp_cluster_status(s, vCenter, cluster_id)
            if wcp_endpoint[1]:
                wcp_status = True
                break
            elif timer < 600:
                wcp_status = False
                current_app.logger.info("WCP services are not up, waiting for 30 seconds...")
                time.sleep(30)
                timer = timer + 30

        if not wcp_status:
            current_app.logger.error("ERROR: Waited for 5 minutes to fetch WCP endpoint")
            current_app.logger.error("ERROR: Failed to fetch WCP endpoint for Supervisor Cluster after restart")
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Failed to fetch WCP endpoint for Supervisor Cluster after restart",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            wcp_endpoint = wcp_endpoint[0]
            current_app.logger.info("WCP Endpoint for SC is: " + wcp_endpoint)
            current_app.logger.info("Successfully restarted WCP services")
        session_delete = s.delete('https://' + vCenter + '/rest/com/vmware/cis/session',
                                  auth=(vCenter_user, VC_PASSWORD))
        current_app.logger.info("\n")
        current_app.logger.info("POST - Successfully Completed Script - Cleaning up REST Session to VC.")
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully restarted WCP services, WCP endpoint: " + wcp_endpoint + " is reachable",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        current_app.logger.error("ERROR: This action can only be performed on a vsphere environment")
        d = {
            "responseType": "ERROR",
            "msg": "ERORR: This action can only be performed on a vsphere environment",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500



@shutdown_env.route("/api/tanzu/wcp-shutdown", methods=['POST'])
def wcp_shutdown():
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
    login()
    if env == Env.VSPHERE:
        if isEnvTkgs_ns(env):
            current_app.logger.error(
                "Wrong spec file provided for cleanup, please use the spec file which was used "
                "for enabling WCP")
            d = {
                "responseType": "ERROR",
                "msg": "Wrong environment provided for cleanup",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        esxi_user = request.headers['User']
        esxi_password = request.headers['Password']
        current_app.logger.info("ESXI User: " + esxi_user)
        current_app.logger.info("ESXI Password: " + esxi_password)

        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
        vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
        try:
            current_app.logger.info("\n")
            current_app.logger.info("STEP 0 - Logging into vCenter API with supplied credentials ")
            vc_service_instance = get_si(vCenter, vCenter_user, VC_PASSWORD)
            if not vc_service_instance[1]:
                current_app.logger.error("Failed to retrieve Service Instance from the provided vCenter details")
                current_app.logger.debug(vc_service_instance[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to retrieve Service Instance from the provided vCenter details",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            vc_service_instance = vc_service_instance[0]
            atexit.register(Disconnect, vc_service_instance)
            content = vc_service_instance.RetrieveContent()
            search_index = vc_service_instance.content.searchIndex

            # Search for all VM Objects in vSphere API
            objview = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
            vmList = objview.view
            objview.Destroy()
            current_app.logger.info("Found a total of %s VMS on VC. " % str(len(vmList)))
        except vmodl.MethodFault as error:
            current_app.logger.error("ERROR: Caught vmodl fault : " + error.msg)
            current_app.logger.debug(error.msg)
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Caught vmodl fault",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        # Set REST VC Variables
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        headers = {'content-type': 'application/json'}
        s = "Global"
        s = requests.Session()
        s.verify = False

        # Connect to VCenter and start a REST session
        vcsession = s.post('https://' + vCenter + '/rest/com/vmware/cis/session', auth=(vCenter_user, VC_PASSWORD))
        if not vcsession.ok:
            current_app.logger.error("ERROR: Session creation is failed, please check vcenter connection")
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Session creation is failed, please check vcenter connection",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        token = json.loads(vcsession.text)["value"]
        token_header = {'vmware-api-session-id': token}

        ## Find Cluster object from Cluster Name specified in script parameter
        if vCenter_cluster:
            for cl in get_obj(content, vim.ComputeResource):
                if cl.name == vCenter_cluster:
                    cluster_id = str(cl).split(":")[1].rstrip('\'')
                    current_app.logger.info('Found the vSphere Cluster named: ' + vCenter_cluster + ' with ID ' + cluster_id)
                    break
                else:
                    current_app.logger.error('ERROR: Could NOT find cluster with name: ', vCenter_cluster)
                    current_app.logger.debug('DEBUG: Double check the Cluster Name. Exiting the program')
                    d = {
                        "responseType": "ERROR",
                        "msg": "ERROR: Could NOT find cluster with name: " + vCenter_cluster,
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500

        current_app.logger.info("\n")
        current_app.logger.info("STEP 1: - Getting all Workload Cluster VMs from K8s API Server on Supervisor Cluster")
        ## GET the Supervisor Cluster apiserver Endpoint
        wcp_endpoint = check_wcp_cluster_status(s, vCenter, cluster_id)
        if not wcp_endpoint[1]:
            current_app.logger.error("ERROR: Failed while fetching WCP endpoint")
            current_app.logger.debug(wcp_endpoint[0])
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Failed while fetching WCP endpoint",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        wcp_endpoint = wcp_endpoint[0]
        current_app.logger.info("WCP Endpoint for SC is: " + wcp_endpoint)

        ## Log into the Supervisor Cluster to create kubeconfig contexts
        try:
            os.putenv("KUBECTL_VSPHERE_PASSWORD", VC_PASSWORD)
            subprocess.check_call(
                ['kubectl', 'vsphere', 'login', '--insecure-skip-tls-verify', '--server', wcp_endpoint, '-u',
                 vCenter_user])
        except Exception as e:
            current_app.logger.debug("DEBUG: Could not login to WCP SC Endpoint.  Is WCP Service running ?")
            current_app.logger.error(str(e))
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Could not login to WCP SC Endpoint",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        # Create k8s client for CustomObjects
        client2 = client.CustomObjectsApi(api_client=config.new_client_from_config(context=wcp_endpoint))

        # Return Cluster API "Machine" objects
        # This builds a list of every Guest Cluster VM (Not including SC VMs)
        try:
            machine_list_dict = client2.list_namespaced_custom_object("cluster.x-k8s.io", "v1alpha3", "", "machines",
                                                                      pretty="True")
            current_app.logger.info("\n -Found", str(len(machine_list_dict)), 'kubernetes Workload Cluster VMs')
        except Exception as e:
            current_app.logger.error("Exception when calling CustomObjectsApi --> list_namespaced_custom_object: %s\n" % e)
            current_app.logger.error(str(e))
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Could not login to WCP SC Endpoint",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        wkld_cluster_vms = []
        for machine in machine_list_dict["items"]:
            current_app.logger.info('-Found CAPI Machine Object in SC. VM Name = {0}'.format(machine['metadata']['name']))
            # print(' -Machine Namespace - {0}'.format(machine['metadata']['namespace']))
            # print(' -Machine Cluster - {0}'.format(machine['metadata']['labels']['cluster.x-k8s.io/cluster-name']))
            # Search pyVmomi all VMs by DNSName
            vm = search_index.FindByDnsName(None, machine['metadata']['name'], True)

            if vm is None:
                current_app.logger.error("ERROR: Could not find a matching VM with VC API ")
            else:
                current_app.logger.info("-Found VM matching CAPI Machine Name in VC API. VM=%s. " % vm.summary.config.name)
                wkld_cluster_vms.append(vm)

        # Shutdown WCP Service on vCenter
        current_app.logger.info("\n")
        current_app.logger.info("STEP 2 - Stopping WCP Service on vCenter")
        stop_vc_svc = stop_vc_svcname(s, vCenter, "wcp")
        if not stop_vc_svc[1]:
            current_app.logger.error("ERROR: Unable to stop WCP Service")
            current_app.logger.debug(stop_vc_svc[0])
            d = {
                "responseType": "ERROR",
                "msg": "ERROR: Unable to stop WCP Service",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        ## Find 3 SC CP VMs and shutdown from the ESXi hosts they are running on.
        current_app.logger.info("\n")
        current_app.logger.info("STEP 3 - Shutting Down all Supervisor Control Plane VMs ")
        for vmobject in vmList:
            if "SupervisorControlPlaneVM" in vmobject.summary.config.name:
                current_app.logger.info("Found Supervisor Control Plane VM %s. " % vmobject.summary.config.name)
                current_app.logger.info("-VM", vmobject.summary.config.name, " is running on ESX host", vmobject.runtime.host.name)
                vnicManager = vmobject.runtime.host.configManager.virtualNicManager
                netConfig = vnicManager.QueryNetConfig("management")
                for vNic in netConfig.candidateVnic:
                    if (netConfig.selectedVnic.index(vNic.key) != -1):
                        # Below will return the Management IP (SC Address) for the ESxi host where SC VP VM is running.
                        current_app.logger.info("ESX host", vmobject.runtime.host.name, " has Management IP", vNic.spec.ip.ipAddress)
                        # Due to permissions limitations we need to log into each ESXi host where the SC CP VM is running
                        # To perform the shutdown operation.
                        shutdown_status = shutdown_sc_vm(25, vmobject.summary.config.name, vmobject.summary.config.uuid,
                                                            vNic.spec.ip.ipAddress, esxi_user, esxi_password)
                        if not shutdown_status[1]:
                            current_app.logger.error("ERROR: Failed to shutdown the SC VMs")
                            current_app.logger.error(shutdown_status[0])
                            d = {
                                "responseType": "ERROR",
                                "msg": "ERROR: Failed to shutdown the SC VMs",
                                "ERROR_CODE": 500
                            }
                            return jsonify(d), 500
                        break
                    else:
                        current_app.logger.info("\tvNic[ " + vNic.key + " ] is not selected; skipping it")

        # Shutdown Guest Cluster Machines Virtual Machines
        current_app.logger.info("Waiting for 3 mins for SC VMs to shutdown")
        time.sleep(180)

        current_app.logger.info("\n")
        current_app.logger.info("STEP 4 - Shutting down all Guest Cluster VMs")
        current_app.logger.info("The following Workload Cluster VMs will be shutdown")
        for wvm in wkld_cluster_vms:
            current_app.logger.info("--" + wvm.summary.config.name)

        for vmobject in wkld_cluster_vms:
            current_app.logger.info("Found Workload Cluster VM: %s. " % vmobject.summary.config.name)
            current_app.logger.info("--VM", vmobject.summary.config.name, " is running on ESX host", vmobject.runtime.host.name)
            vnicManager = vmobject.runtime.host.configManager.virtualNicManager
            netConfig = vnicManager.QueryNetConfig("management")
            for vNic in netConfig.candidateVnic:
                if (netConfig.selectedVnic.index(vNic.key) != -1):
                    # Below will return the Management IP (SC Address) for the ESxi host where SC VP VM is running.
                    current_app.logger.info("ESX host", vmobject.runtime.host.name, " has Management IP", vNic.spec.ip.ipAddress)
                    # Due to permissions limitations we need to log into each ESXi host where the SC CP VM is running
                    # To perform the shutdown operation.
                    shutdown_status = shutdown_sc_vm(25, vmobject.summary.config.name, vmobject.summary.config.uuid,
                                                        vNic.spec.ip.ipAddress, esxi_user, esxi_password)
                    if not shutdown_status[1]:
                        current_app.logger.error("ERROR: Failed to shutdown the SC VMs")
                        current_app.logger.error(shutdown_status[0])
                        d = {
                            "responseType": "ERROR",
                            "msg": "ERROR: Failed to shutdown the SC VMs",
                            "ERROR_CODE": 500
                        }
                        return jsonify(d), 500
                    break
                else:
                    current_app.logger.info("\tvNic[ " + vNic.key + " ] is not selected; skipping it")
        # shutdown_status_wkld = shutdown_Vm(20, wkld_cluster_vms)
        # if not shutdown_status_wkld[1]:
        #     current_app.logger.error("ERROR: Caught error trying to shutdown VM")
        #     current_app.logger.debug(shutdown_status_wkld[0])
        #     d = {
        #         "responseType": "ERROR",
        #         "msg": "ERROR: Caught error trying to shutdown VM",
        #         "ERROR_CODE": 500
        #     }
        #     return jsonify(d), 500

        # Clean up and exit...
        session_delete = s.delete('https://' + vCenter + '/rest/com/vmware/cis/session',
                                  auth=(vCenter_user, VC_PASSWORD))
        current_app.logger.info("\n")
        current_app.logger.info("POST - Successfully Completed Script - Cleaning up REST Session to VC.")
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully shutdown WCP",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        current_app.logger.error("ERROR: This action can only be performed on a vsphere environment")
        d = {
            "responseType": "ERROR",
            "msg": "ERORR: This action can only be performed on a vsphere environment",
            "ERROR_CODE": 500
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
            current_app.logger.error("ERROR: Could not connect to the specified vCenter host using specified username and password")
            return None, False
        else:
            return service_instance, True
    except Exception as e:
        current_app.logger.error("ERROR: Got an exception while connecting to specified vCenter host")
        current_app.logger.debug(str(e))
        return str(e), False

def get_obj(content, vimtype, name = None):
    return [item for item in content.viewManager.CreateContainerView(
        content.rootFolder, [vimtype], recursive=True).view]

def check_wcp_cluster_status(s, vcip, cluster):
    try:
        json_response = s.get('https://' + vcip + '/api/vcenter/namespace-management/clusters/' + cluster)
        if json_response.ok:
            result = json.loads(json_response.text)
            if result["config_status"] == "RUNNING":
                if result["kubernetes_status"] == "READY":
                    return result["api_server_cluster_endpoint"], True
            else:
                return None, False
        else:
            return None, False
    except Exception as e:
        current_app.logger.error("ERROR: Got an exception while fetching WCP endpoint")
        current_app.logger.debug(str(e))
        return str(e), False


def stop_vc_svcname(s, vcip, svc_name):
    json_config = {"startup_type": "MANUAL"}
    startup_json_response = s.patch('https://' + vcip + '/api/vcenter/services/' + svc_name, json=json_config)
    if startup_json_response.status_code == 204:
        current_app.logger.info("Successfully set WCP Service Startup to MANUAL. Response Code %s " % startup_json_response.status_code)
    else:
        current_app.logger.error("ERROR: Unable to setup Startup for WCP Service to Manual")
        return None, False

    stop_json_response = s.post('https://' + vcip + '/api/vcenter/services/' + svc_name + '?action=stop')
    if stop_json_response.status_code == 204:
        current_app.logger.info("Successfully stopped WCP Service. Response Code %s " % stop_json_response.status_code)
        return "SUCCESS", True
    else:
        current_app.logger.error("ERROR: Unable to stop WCP Service")
        return None, False

def restart_vc_svcname(s, vcip, svc_name):
    stop_json_response = s.post('https://' + vcip + '/api/vcenter/services/' + svc_name + '?action=restart')
    if stop_json_response.status_code == 204:
        current_app.logger.info("Successfully restarted WCP Service. Response Code %s " % stop_json_response.status_code)
        return "SUCCESS", True
    else:
        current_app.logger.error("ERROR: Unable to restart WCP Service")
        return None, False


def shutdown_sc_vm(delay, vm_name, vm_uuid, vm_host_ip, esx_user, esx_password):
    try:
        current_app.logger.info("Shutting down VM " + vm_name + " on host " + vm_host_ip)
        esx_service_instance = get_si(vm_host_ip, esx_user, esx_password)
        if not esx_service_instance[1]:
            current_app.logger.error("Failed to retrieve ESX Service Instance")
            return None, False
        esx_service_instance = esx_service_instance[0]
        # content = esx_service_instance.RetrieveContent()
        atexit.register(Disconnect, esx_service_instance)
        search_index = esx_service_instance.content.searchIndex
        scvm = search_index.FindByUuid(None, vm_uuid, True)

        if scvm is None:
            current_app.logger.info("Could not find virtual machine")
            return "SUCCESS", True

        current_app.logger.info("Found Virtual Machine on ESX")
        details = {'--name': scvm.summary.config.name,
                   '--instance UUID': scvm.summary.config.instanceUuid,
                   '--bios UUID': scvm.summary.config.uuid,
                   '--path to VM': scvm.summary.config.vmPathName,
                   '--host name': scvm.runtime.host.name,
                   '--last booted timestamp': scvm.runtime.bootTime,
                   }

        for name, value in details.items():
            current_app.logger.info("{0:{width}{base}}: {1}".format(name, value, width=25, base='s'))

        current_app.logger.info("Shutting down VM %s" % scvm.summary.config.name)
        scvm.ShutdownGuest()
        current_app.logger.info("Pausing for %s seconds..." % delay)
        time.sleep(delay)
        return "SUCCESS", True
    except vmodl.MethodFault as error:
        current_app.logger.error("ERROR: Caught error trying to shutdown VM  ")
        current_app.logger.error("ERROR: Caught vmodl fault : " + error.msg)
        return str(error), False


def shutdown_Vm(delay, list_of_vms):
    for vm in list_of_vms:
        try:
            current_app.logger.info("Shutting down VM %s." % vm.summary.config.name)
            vm.ShutdownGuest()
            current_app.logger.info("Pausing for %s seconds..." % delay)
            time.sleep(delay)
            return "SUCCESS", True
        except vmodl.MethodFault as error:
            current_app.logger.error("ERROR: Caught error trying to shutdown VM  ")
            current_app.logger.error("ERROR: Caught vmodl fault : " + error.msg)
            return str(error), False