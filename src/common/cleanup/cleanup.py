import logging
import requests
import time
import base64
import os
import json
from pyVmomi import vim
from flask import current_app, request, jsonify, Blueprint
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.common_utilities import envCheck, isEnvTkgs_ns, isEnvTkgs_wcp, getClusterID, isWcpEnabled, \
    getClusterStatusOnTanzu, isAviHaEnabled, checkTmcEnabled, obtain_second_csrf, obtain_avi_version, grabNsxtHeaders, \
    getPolicy, getList, checkObjectIsPresentAndReturnPath
from common.operation.constants import Env, ResourcePoolAndFolderName, ControllerLocation, RegexPattern, KubernetesOva, \
    GroupNameCgw, VCF, ServiceName, FirewallRuleMgw, FirewallRuleCgw, ServiceName, GroupNameMgw, SegmentsName, \
    Policy_Name
from common.lib.govc_client import GovcClient
from common.lib.kubectl_client import KubectlClient
from common.lib.nsxt_client import NsxtClient
from common.util.local_cmd_helper import LocalCmdHelper
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList, runShellCommandAndReturnOutput, \
    grabPipeOutput, verifyPodsAreRunning, runProcess
from common.operation.vcenter_operations import checkVmPresent, destroy_vm, getSi, wait_for_task, get_obj, get_dc
from common.session.session_acquire import login, fetch_vmc_env
from common.prechecks.list_reources import getAllNamespaces
from common.constants.constants import FirewallRulePrefix

cleanup_env = Blueprint("cleanup_env", __name__, static_folder="cleanup")
logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
__author__ = 'Tasmiya'


@cleanup_env.route("/api/tanzu/cleanup-env", methods=['POST'])
def cleanup_environment():
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
    if env == Env.VSPHERE or env == Env.VCF:
        if isEnvTkgs_ns(env):
            current_app.logger.error("Wrong spec file provided for cleanup, please use the spec file which was used "
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
        vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
        vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']
        if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env):
            parent_rp = None
        else:
            parent_rp = request.get_json(force=True)['envSpec']['vcenterDetails']["resourcePoolName"]
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
        vCenter_datacenter = request.get_json(force=True)['envSpec']['sddcDatacenter']
        vCenter_cluster = request.get_json(force=True)['envSpec']['sddcCluster']
        parent_rp = request.get_json(force=True)['envSpec']['resourcePoolName']

    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    GovcClient.set_env_vars(govc_client)

    if isEnvTkgs_wcp(env):
        tkgs_response = tkgs_cleanup(vCenter=vCenter, vCenter_user=vCenter_user, VC_PASSWORD=VC_PASSWORD,
                                     vc_cluster=vCenter_cluster)
        if tkgs_response[1] != 200:
            current_app.logger.error("Cleanup failed - " + tkgs_response[0].json["msg"])
            d = {
                "responseType": "ERROR",
                "msg": "Cleanup failed - " + tkgs_response[0].json["msg"],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    elif env == Env.VSPHERE or env == Env.VMC or env == Env.VCF:
        tkg_response = tkgm_cleanup(env=env)
        if tkg_response[1] != 200:
            current_app.logger.error("Cleanup failed - " + tkg_response[0].json["msg"])
            d = {
                "responseType": "ERROR",
                "msg": "Cleanup failed - " + tkg_response[0].json["msg"],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

    current_app.logger.info("Clusters are deleted successfully. Performing other components cleanup")

    response = delete_common_comp(govc_client=govc_client, env=env, vCenter=vCenter, vCenter_user=vCenter_user,
                                  VC_PASSWORD=VC_PASSWORD, datacenter=vCenter_datacenter, cluster=vCenter_cluster,
                                  parent_resourcepool=parent_rp)
    if response[1] != 200:
        current_app.logger.error("Cleanup failed - " + response[0].json["msg"])
        d = {
            "responseType": "ERROR",
            "msg": "Cleanup failed - " + response[0].json["msg"],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info("Cleanup for " + env + " is successful")
    d = {
        "responseType": "SUCCESS",
        "msg": "Cleanup completed ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def tkgs_cleanup(vCenter, vCenter_user, VC_PASSWORD, vc_cluster):
    try:
        sess = requests.post("https://" + vCenter + "/rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD),
                             verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        else:
            vc_session = sess.json()['value']

        id = getClusterID(vCenter, vCenter_user, VC_PASSWORD, vc_cluster)
        if id[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": id[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        cluster_id = id[0]

        namespaces = []
        workload_clusters = []
        delete = True
        if delete:
            enabled = getWCPStatus(cluster_id)
            if enabled[0]:
                current_app.logger.info("WCP is enabled and it's status is " + enabled[1])
                current_app.logger.info("Proceeding to disable WCP on cluster - " + vc_cluster)
                if enabled[1] == "RUNNING":
                    current_app.logger.info("Fetching list of namespaces and clusters deployed")
                    response = getAllNamespaces()
                    if response[1] == 200:
                        namespaces = response[0].json["NAMESPACES_LIST"]
                    clusters_response = getAllClusters_tkgs(vCenter, vCenter_user, VC_PASSWORD, namespaces, vc_cluster)
                    if not (clusters_response[0] is None):
                        workload_clusters = clusters_response[0]
                    current_app.logger.info("List of deployed workload clusters")
                    current_app.logger.info(workload_clusters)
                else:
                    current_app.logger.error("Unable to fetch list of namespaces and workload clusters as "
                                             "WCP status is " + enabled[1])

                disable = disableWCP(vCenter, cluster_id, vc_session)
                if disable[0] is None:
                    current_app.logger.error(disable[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": disable[1],
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                current_app.logger.info("WCP is already disabled on cluster - " + vc_cluster)

        kubectl_configs_status = kubectl_configs_cleanup(Env.VSPHERE, workload_clusters + namespaces)
        #kubectl_configs_status = kubectl_configs_cleanup(env, ['cluster-03', 'tbano-ns03'])
        if not kubectl_configs_status[0]:
            current_app.logger.error(kubectl_configs_status[1])
            d = {
                "responseType": "ERROR",
                "msg": kubectl_configs_status[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        current_app.logger.info(kubectl_configs_status[1])

        if checkTmcEnabled(Env.VSPHERE):
            current_app.logger.info("Performing TMC Cleanup")
            os.putenv("TMC_API_TOKEN", request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                'tmcRefreshToken'])
            if isEnvTkgs_wcp(Env.VSPHERE):
                if not delete_tmc_cluster(workload_clusters, False):
                    current_app.logger.warn("Failed to delete workload clusters from TMC")
                    current_app.logger.warn("Try deleting it using :'tmc cluster delete <clusterName>' command")
                if not delete_tmc_cluster([request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails']
                                           ['tmcSupervisorClusterName']], True):
                    current_app.logger.warn("Failed to delete Management clusters from TMC")
                current_app.logger.warn("Try deleting it using :'tmc managmentcluster delete <clusterName>' command")
        current_app.logger.info("TKGs components deleted successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "TKGs components deleted successfully",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occured while performing cleanup",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500


def getWCPStatus(cluster_id):
    """
    :param cluster_id:
    :return:
     False: If WCP is not enabled
    True: if WCP is enabled and any state, not necessarily running status
    """
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
    else:
        return True, response_csrf.json()["config_status"]


def tkgm_cleanup(env):
    if env == Env.VMC:
        management_cluster = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']
        shared_cluster = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterName']
        workload_cluster = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterName']
    elif env == Env.VSPHERE:
        management_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
        shared_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterName']
        workload_cluster = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']
    elif env == Env.VCF:
        management_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
        shared_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceClusterName']
        workload_cluster = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']

    worload_clusters = [shared_cluster, workload_cluster]
    if management_exists(management_cluster):
        for cluster in worload_clusters:
            current_app.logger.info("Deleting " + cluster + " cluster")
            if getCluster(cluster):
                if delete_cluster(cluster):
                    current_app.logger.info("Cluster " + cluster + " deleted successfully")
                else:
                    current_app.logger.error("Failed to delete cluster - " + cluster)
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to delete cluster - " + cluster,
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            else:
                current_app.logger.info("Workload cluster " + cluster + " is not available in environment")

        current_app.logger.info("Deleting management cluster...")
        if delete_mgmt_cluster(management_cluster):
            current_app.logger.info("Management cluster " + management_cluster + " - deleted successfully")
        else:
            current_app.logger.error("Failed to delete management cluster - " + management_cluster)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to delete management cluster - " + management_cluster,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    else:
        current_app.logger.info("Management cluster " + management_cluster + " is not present in environment")

    kubectl_configs_status = kubectl_configs_cleanup(env, [management_cluster, workload_cluster, shared_cluster])
    if not kubectl_configs_status[0]:
        current_app.logger.error(kubectl_configs_status[1])
        d = {
            "responseType": "ERROR",
            "msg": kubectl_configs_status[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info(kubectl_configs_status[1])

    if checkTmcEnabled(env):
        current_app.logger.info("Performing TMC cleanup")
        if env == Env.VMC:
            os.putenv("TMC_API_TOKEN", request.get_json(force=True)["saasEndpoints"]['tmcDetails']['tmcRefreshToken'])
        else:
            os.putenv("TMC_API_TOKEN", request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                'tmcRefreshToken'])
        if not delete_tmc_cluster([workload_cluster, shared_cluster], False):
            current_app.logger.warn("Failed to delete workload clusters from TMC")
            current_app.logger.warn("Try deleting it using :'tmc cluster delete <clusterName>' command")
        if not delete_tmc_cluster([management_cluster], True):
            current_app.logger.warn("Failed to delete management cluster " + management_cluster + " from TMC")
            current_app.logger.warn("Try deleting it using :'tmc managementcluster delete <clusterName>' command")

    current_app.logger.info("TKG Clusters and Nodes deleted successfully ")
    d = {
        "responseType": "SUCCESS",
        "msg": "TKG Clusters and Nodes deleted successfully ",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def delete_tmc_cluster(clusters, is_mgmt):
    try:
        for cls in clusters:
            if not is_mgmt:
                current_app.logger.info("Performing TMC cleanup for workload clusters")
                command = ["tmc", "cluster", "list"]
                command_status = runShellCommandAndReturnOutputAsList(command)
                if command_status[1] != 0:
                    current_app.logger.error("Failed to run command to check status of workload cluster - " + cls)
                    return False
                for line in command_status[0]:
                    if line.split()[0] == cls:
                        current_app.logger.info("Un-register cluster " + cls + " from TMC")
                        delete_command = ["tmc", "cluster", "delete", cls, "-m", line.split()[1],
                                          "-p", line.split()[2], "--force"]
                        current_app.logger.debug(delete_command)
                        delete_status = runShellCommandAndReturnOutputAsList(delete_command)
                        if delete_status[1] != 0:
                            current_app.logger.error(delete_status[0])
                            current_app.logger.error("Failed to un-register cluster - " + cls + " from TMC")
                            return False
                        else:
                            current_app.logger.info(cls + " un-registered from TMC successfully")
            else:
                current_app.logger.info("Performing TMC cleanup for management clusters")
                mgmt_command = ["tmc", "managementcluster", "list"]
                mgmt_command_status = runShellCommandAndReturnOutputAsList(mgmt_command)
                if mgmt_command_status[1] != 0:
                    current_app.logger.error("Failed to run command to check status of workload cluster - " + cls)
                    return False
                for mgmt in mgmt_command_status[0]:
                    if mgmt.strip() == cls:
                        current_app.logger.info("Un-register cluster " + cls + " from TMC")
                        delete_mgmt = ["tmc", "managementcluster", "delete", cls, "--force"]
                        delete_mgmt_status = runShellCommandAndReturnOutputAsList(delete_mgmt)
                        if delete_mgmt_status[1] != 0:
                            current_app.logger.error(delete_mgmt_status[0])
                            current_app.logger.error("Failed to un-register cluster - " + cls + " from TMC")
                            return False
                        else:
                            current_app.logger.info(cls + " un-registered from TMC successfully")
        return True
    except Exception as e:
        current_app.logger.error(str(e))
        return False


def delete_cluster(cluster):
    try:
        current_app.logger.info("Initiating deletion of cluster - " + cluster)
        delete = ["tanzu", "cluster", "delete", cluster, "-y"]
        delete_status = runShellCommandAndReturnOutputAsList(delete)
        if delete_status[1] != 0:
            current_app.logger.error("Command to delete - " + cluster + " Failed")
            current_app.logger.debug(delete_status[0])
            d = {
                "responseType": "ERROR",
                "msg": "Failed delete cluster - " + cluster,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        cluster_running = ["tanzu", "cluster", "list"]
        command_status = runShellCommandAndReturnOutputAsList(cluster_running)
        if command_status[1] != 0:
            current_app.logger.error("Failed to run command to check status of workload cluster - " + cluster)
            return False
        deleting = True
        count = 0
        while count < 360 and deleting:
            if verifyPodsAreRunning(cluster, command_status[0], RegexPattern.deleting) or \
                    verifyPodsAreRunning(cluster, command_status[0], RegexPattern.running):
                current_app.logger.info("Waiting for " + cluster + " deletion to complete...")
                current_app.logger.info("Retrying in 10s...")
                time.sleep(10)
                count = count + 1
                command_status = runShellCommandAndReturnOutputAsList(cluster_running)
            else:
                deleting = False
        if not deleting:
            return True

        current_app.logger.error("waited for " + str(count*5) + "s")
        return False
    except Exception as e:
        current_app.logger.error("Exception occurred while deleting cluster " + str(e))
        return False


def delete_mgmt_cluster(mgmt_cluster):
    try:
        current_app.logger.info("Delete Management cluster - " + mgmt_cluster)
        delete_command = ["tanzu", "management-cluster", "delete", "--force", "-y"]
        runProcess(delete_command)

        deleted = False
        count = 0
        while count < 360 and not deleted:
            if management_exists(mgmt_cluster):
                current_app.logger.debug("Management cluster is still not deleted... retrying in 10s")
                time.sleep(10)
                count = count + 1
            else:
                deleted = True
                break

        if not deleted:
            current_app.logger.error("Management cluster " + mgmt_cluster + " is not deleted even after " + str(count*5)
                                     + "s")
            return False
        else:
            return True

        return False

    except Exception as e:
        current_app.logger.error(str(e))
        return False


def management_exists(mgmt_cluster):
    try:
        listn = ["tanzu", "management-cluster", "get"]
        o = runShellCommandAndReturnOutput(listn)
        if o[1] == 0:
            try:
                if o[0].__contains__(mgmt_cluster):
                    return True
                else:
                    return False
            except:
                return False
        else:
            return False
    except:
        return False


def kubectl_configs_cleanup(env, clusters):
    try:
        kubectl_client = KubectlClient(LocalCmdHelper())
        current_app.logger.info("Deleting contexts of clusters")
        for cluster in clusters:
            if isEnvTkgs_wcp(env):
                try:
                    delete = kubectl_client.delete_cluster_context_tkgs(cluster)
                    if delete == 0:
                        current_app.logger.info(cluster + " context deleted successfully")
                    else:
                        current_app.logger.error("Failed to delete kubectl context for cluster - " + cluster)
                except Exception as e:
                    current_app.logger.info("Cluster context does not exist for " + cluster)
            else:
                try:
                    delete = kubectl_client.delete_cluster_context(cluster)
                    if delete == 0:
                        current_app.logger.info(cluster + " context deleted successfully")
                    else:
                        current_app.logger.error("Failed to delete kubectl context for cluster - " + cluster)

                    delete_cluster = kubectl_client.delete_cluster(cluster)
                    if delete_cluster == 0:
                        current_app.logger.info(cluster + " context deleted successfully")
                    else:
                        current_app.logger.error("Failed to delete kubectl context for cluster - " + cluster)
                except Exception as e:
                    current_app.logger.info("Cluster context does not exist for " + cluster)
        return True, "kubectl contexts deleted successfully"
    except Exception as e:
        current_app.logger.error("Exception occurred while cleaning cluster contexts - " + str(e))
        return False


def get_context_name(env, cluster):
    try:
        command = ["kubectl", "config", "get-contexts"]
        command_status = runShellCommandAndReturnOutputAsList(command)
        if command_status[1] != 0:
            current_app.logger.error(command_status[0])
            return None

        for context in command_status[0]:
            if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
                if context.split()[0] == cluster:
                    return context.split()[0]
                elif context.split()[1] == cluster:
                    return context.split()[1]
            else:
                if context.split()[2] == cluster:
                    return context.split()[1]
                elif context.split()[1] == cluster:
                    return context.split()[0]

        return None
    except Exception as e:
        current_app.logger.error(str(e))
        return None


def delete_common_comp(govc_client: GovcClient, env, vCenter, vCenter_user, VC_PASSWORD, datacenter, cluster, parent_resourcepool):

    uuid = get_avi_uuid(vCenter, vCenter_user, VC_PASSWORD)

    avi_cleanup_status = cleanup_avi_vms(govc_client, env, datacenter)
    if not avi_cleanup_status[0]:
        current_app.logger.error(avi_cleanup_status[1])
        d = {
            "responseType": "ERROR",
            "msg": avi_cleanup_status[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    current_app.logger.info(avi_cleanup_status[1])

    response = cleanup_resource_pools(govc_client, env, datacenter, cluster, parent_resourcepool)
    if not response[0]:
        d = {
            "responseType": "ERROR",
            "msg": response[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info(response[1])

    library_response = cleanup_content_libraries(env)
    if not library_response[0]:
        d = {
            "responseType": "ERROR",
            "msg": library_response[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info(library_response[1])

    cleanup_sivt = cleanup_downloaded_ovas(env)
    if not cleanup_sivt[0]:
        current_app.logger.info(cleanup_sivt[1])
        d = {
            "responseType": "ERROR",
            "msg": cleanup_sivt[1],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    current_app.logger.info(cleanup_sivt[1])

    if not delete_folders(env, vCenter, vCenter_user, VC_PASSWORD):
        current_app.logger.error("Failed to delete folders which were created by SIVT")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to delete folders which were created by SIVT",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500

    if env == Env.VMC or env == Env.VCF or env == Env.VSPHERE:
        if not delete_kubernetes_templates(govc_client, vCenter, vCenter_user, VC_PASSWORD, datacenter, uuid):
            current_app.logger.error("Failed to delete Kubernetes templates")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to delete Kubernetes templates",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        if not delete_config_yaml():
            current_app.logger.error("Failed to delete config.yaml files /root/.config/tanzu/config.yaml "
                                     "and /root/.config/tanzu/tkg/config.yaml")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to delete config.yaml files",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

    current_app.logger.info("Performing NSX-T components cleanup")
    if env == Env.VCF:
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            d = {
                "responseType": "ERROR",
                "msg": str(headers_[1]),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        headers_[1].update({"Content-Type": "application/json", "Accept": "application/json"})

        current_app.logger.info("Deleting NSX-T gateway policies...")
        url = "https://" + headers_[2] + "/policy/api/v1/infra/domains/default/gateway-policies/"
        delete_policy = delete_nsxt_components(url, headers_[1], [Policy_Name.POLICY_NAME])
        if not delete_policy[0]:
            current_app.logger.error(delete_policy[1])
            d = {
                "responseType": "ERROR",
                "msg": delete_policy[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Gateway policies deleted successfully")

        current_app.logger.info("Deleting Inventory groups and firewall rules...")
        url = "https://" + headers_[2] + "/policy/api/v1/infra/domains/default/groups/"
        delete_groups = delete_nsxt_components(url, headers_[1], nsxt_list_groups())
        if not delete_groups[0]:
            current_app.logger.error(delete_groups[1])
            d = {
                "responseType": "ERROR",
                "msg": delete_groups[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Inventory groups and firewall rules deleted successfully")

        current_app.logger.info("Deleting Services...")
        url = "https://" + headers_[2] + "/policy/api/v1/infra/services/"
        delete_services = delete_nsxt_components(url, headers_[1], nsxt_list_services())
        if not delete_services[0]:
            current_app.logger.error(delete_services[1])
            d = {
                "responseType": "ERROR",
                "msg": delete_services[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Services deleted successfully")

        current_app.logger.info("Deleting network Segments...")
        time.sleep(30)
        url = "https://" + headers_[2] + "/policy/api/v1/infra/segments/"
        delete_segments = delete_nsxt_components(url, headers_[1], list_network_segments(env))
        if not delete_segments[0]:
            current_app.logger.error(delete_segments[1])
            d = {
                "responseType": "ERROR",
                "msg": delete_segments[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Segments deleted successfully")

    elif env == Env.VMC:
        headers = {
            "Content-Type": "application/json",
            "csp-auth-token": current_app.config['access_token']
        }

        url = current_app.config['NSX_REVERSE_PROXY_URL'] + "orgs/" + current_app.config['ORG_ID'] + "/sddcs/" \
              + current_app.config['SDDC_ID']

        current_app.logger.info("Deleting firewall rules for compute Gateway...")
        del_cgw_rules = delete_nsxt_components(url + "/policy/api/v1/infra/domains/cgw/gateway-policies/default/rules/",
                                               headers, vmc_list_cgw_firewall_rules())
        if not del_cgw_rules[0]:
            current_app.logger.error(del_cgw_rules[1])
            d = {
                "responseType": "ERROR",
                "msg": del_cgw_rules[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Firewall rules for Compute Gateway deleted successfully...")

        current_app.logger.info("Deleting firewall rules for Management Gateway...")
        del_mgw_rules = delete_nsxt_components(url + "/policy/api/v1/infra/domains/mgw/gateway-policies/default/rules/",
                                               headers, vmc_list_mgw_firewall_rules())
        if not del_cgw_rules[0]:
            current_app.logger.error(del_mgw_rules[1])
            d = {
                "responseType": "ERROR",
                "msg": del_mgw_rules[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Firewall rules for Management Gateway deleted successfully...")

        current_app.logger.info("Deleting services... ")
        del_services = delete_nsxt_components(url + "/policy/api/v1/infra/services/", headers,
                                              [ServiceName.KUBE_VIP_SERVICE])
        if not del_services[0]:
            current_app.logger.error(del_services[1])
            d = {
                "responseType": "ERROR",
                "msg": del_services[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Services deleted successfully... ")

        current_app.logger.info("Deleting inventory groups for Management Gateway...")
        del_mgw_inventory_grps = delete_nsxt_components(url + "/policy/api/v1/infra/domains/mgw/groups/", headers,
                                                        vmc_list_mgw_inventory_groups())
        if not del_mgw_inventory_grps[0]:
            current_app.logger.error(del_mgw_inventory_grps[1])
            d = {
                "responseType": "ERROR",
                "msg": del_mgw_inventory_grps[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Inventory groups for Management Gateway deleted successfully")

        current_app.logger.info("Deleting inventory groups for Compute Gateway...")
        del_cgw_inventory_grps = delete_nsxt_components(url + "/policy/api/v1/infra/domains/cgw/groups/", headers,
                                                        vmc_list_cgw_inventory_groups())
        if not del_cgw_inventory_grps[0]:
            current_app.logger.error(del_cgw_inventory_grps[1])
            d = {
                "responseType": "ERROR",
                "msg": del_cgw_inventory_grps[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Inventory groups for Compute Gateway deleted successfully")

        current_app.logger.info("Deleting network segments...")
        time.sleep(30)
        del_segments = delete_nsxt_components(url + "/policy/api/v1/infra/tier-1s/cgw/segments/", headers,
                                              list_network_segments(env))
        if not del_segments[0]:
            current_app.logger.error(del_segments[1])
            d = {
                "responseType": "ERROR",
                "msg": del_segments[1],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info("Network segments deleted successfully")

    d = {
        "responseType": "SUCCESS",
        "msg": "Common Components delete successful",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


def disableWCP(vCenter, cluster_id, session_id):
    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "vmware-api-session-id": session_id
    }

    url1 = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/"+cluster_id+"?action=disable"
    response_csrf = requests.request("POST", url1, headers=header, verify=False)
    if response_csrf.status_code != 204:
        return None, response_csrf.text

    current_app.logger.info("Checking WCP Status")
    count = 0
    disabled = False
    while count < 90 and not disabled:
        url = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/"+cluster_id
        response_csrf = requests.request("GET", url, headers=header, verify=False)
        if response_csrf.status_code != 200:
            if response_csrf.json()["messages"][0]["default_message"].__contains__("does not have Workloads enabled"):
                disabled = True
                break
        else:
            try:
                if response_csrf.json()["config_status"] == "REMOVING" or response_csrf.json()["config_status"] == "ERROR":
                    current_app.logger.info("Cluster config status " + response_csrf.json()["config_status"])
            except:
                pass
        time.sleep(20)
        count = count + 1
        current_app.logger.info("Waited " + str(count * 20) + "s, retrying")
    if not disabled:
        current_app.logger.error("Cluster is still running " + str(count * 20))
        return None, "WCP DISABLE Failed"
    return "SUCCESS", "WCP is DISABLED successfully"


def cleanup_avi_vms(govc_client, env, datacenter):
    try:
        datacenter = datacenter.replace(' ', "#remove_me#")
        avi_list = fetch_avi_vms(govc_client, env, datacenter)
        for avi_fqdn in avi_list[1]:
            vm_path = govc_client.get_vm_path(avi_fqdn, datacenter)
            govc_client.delete_vm(avi_fqdn, vm_path.replace(' ', "#remove_me#"))
        return True, "NXS load balancer cleanup successful"
    except Exception as e:
        return False, str(e)


def fetch_avi_vms(govc_client, env, data_center):
    data_center = data_center.replace(' ', "#remove_me#")
    vm_list = []
    vmc_se_vms_list = [ControllerLocation.CONTROLLER_SE_NAME,
                       ControllerLocation.CONTROLLER_SE_NAME2,
                       ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME,
                       ControllerLocation.CONTROLLER_SE_WORKLOAD_NAME2]

    if isEnvTkgs_wcp(env):
        avi_fqdn = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']
    elif env == Env.VSPHERE or env == Env.VCF:
        avi_fqdn = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController01Fqdn']
    else:
        avi_fqdn = ControllerLocation.CONTROLLER_NAME

    if env == Env.VMC:
        for se_vm in vmc_se_vms_list:
            if govc_client.find_vms_by_name(vm_name=se_vm, options="-dc "+data_center):
                vm_list.append(se_vm)
        if isAviHaEnabled(env):
            if govc_client.find_vms_by_name(vm_name=ControllerLocation.CONTROLLER_NAME2, options="-dc "+data_center):
                vm_list.append(ControllerLocation.CONTROLLER_NAME2)
            if govc_client.find_vms_by_name(vm_name=ControllerLocation.CONTROLLER_NAME3, options="-dc "+data_center):
                vm_list.append(ControllerLocation.CONTROLLER_NAME3)

    elif isAviHaEnabled(env):
        if isEnvTkgs_wcp(env):
            avi_fqdn2 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController02Fqdn']
            avi_fqdn3 = request.get_json(force=True)['tkgsComponentSpec']['aviComponents']['aviController03Fqdn']
        else:
            avi_fqdn2 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController02Fqdn']
            avi_fqdn3 = request.get_json(force=True)['tkgComponentSpec']['aviComponents']['aviController03Fqdn']

        if govc_client.find_vms_by_name(vm_name=avi_fqdn2, options="-dc "+data_center):
            vm_list.append(avi_fqdn2)
        if govc_client.find_vms_by_name(vm_name=avi_fqdn3, options="-dc "+data_center):
            vm_list.append(avi_fqdn3)

    if govc_client.find_vms_by_name(vm_name=avi_fqdn):
        vm_list.append(avi_fqdn)
        ip = govc_client.get_vm_ip(avi_fqdn, datacenter_name=data_center)[0]
        if ip is None:
            current_app.logger.warn("Unable to fetch IP address for NSX ALB LoadBalancer")
            return True, vm_list
        deployed_avi_version = obtain_avi_version(ip, env)
        if deployed_avi_version[0] is None:
            current_app.logger.warn("Failed to obtain deployed AVI version")
            return True, vm_list
        csrf2 = obtain_second_csrf(ip, env)
        if csrf2 is None:
            current_app.logger.warn("Failed to get csrf for AVI")
            return True, vm_list

        url = "https://" + str(ip) + "/api/serviceengine-inventory"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": deployed_avi_version[0],
            "x-csrftoken": csrf2[0]
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
        payload = {}
        try:
            response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
            if response_csrf.status_code != 200:
                current_app.logger.error(response_csrf.json())
                current_app.logger.error("Failed to fetch AVI Service Engine VM details")
            else:
                for config in response_csrf.json()["results"]:
                    if govc_client.find_vms_by_name(config["config"]["name"], options="-dc "+data_center):
                        current_app.logger.info(config["config"]["name"] + " is present in datacenter " + data_center)
                        vm_list.append(config["config"]["name"])
        except Exception as e:
            current_app.logger.warn("Failed to login to NSX Load Balancer")
            return True, vm_list
    else:
        current_app.logger.warn("NSX ALB Controller VM not found")
    return True, vm_list


def cleanup_resource_pools(govc_client, env, vc_datcenter, vc_cluster, parent_rp):
    if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env) or not parent_rp:
        resource_pool_path = "/" + vc_datcenter + "/host/" + vc_cluster + "/Resources/"
    else:
        resource_pool_path = "/" + vc_datcenter + "/host/" + vc_cluster + "/Resources/" + parent_rp + "/"
    resource_pools = fetch_resource_pools(env, vc_datcenter, vc_cluster, parent_rp)
    for rp in resource_pools[1]:
        current_app.logger.info(rp + " resource pool exists, deleting it")
        if child_elements(vc_datcenter, rp):
            current_app.logger.info(rp + " skipped deletion due to the presence of virtual machines")
        elif clusterNodes(vc_datcenter, rp):
            current_app.logger.info(rp + " skipped deletion due to the presence cluster nodes")
        else:
            govc_client.delete_resource_pool(resource_pool_path.replace(' ', "#remove_me#") + rp)
            current_app.logger.info(rp + " deleted successfully")
    return True, "Resource pools deleted successfully"


def child_elements(vc_datcenter, resource_pool):
    password = current_app.config['VC_PASSWORD']
    username = current_app.config['VC_USER']
    vcenter_host = current_app.config['VC_IP']
    rp_vms = []
    datacenter_obj = get_dc(getSi(vcenter_host, username, password), vc_datcenter)
    vms = datacenter_obj.vmFolder.childEntity
    for vm in vms:
        if isinstance(vm, vim.VirtualMachine):
            rp_obj = vm.resourcePool
            if rp_obj:
                if rp_obj.name == resource_pool:
                    rp_vms.append(vm.name)

    if rp_vms:
        current_app.logger.info(resource_pool + " resource pool contains virtual machines - " + str(rp_vms))
        return True
    return False


def clusterNodes(vc_datcenter, resource_pool):
    data_center = vc_datcenter.replace(' ', "#remove_me#")

    command = ["govc", "ls", "/" + data_center.replace("#remove_me#", " ") + "/vm/" + resource_pool.lower()]
    node_list = runShellCommandAndReturnOutputAsList(command)
    if node_list[1] != 0:
        return False
    for ele in node_list[0]:
        if resource_pool in ele:
            current_app.logger.info(resource_pool + " resource pool still contains cluster nodes - " + str(node_list[0]))
            return True
    return False


def fetch_resource_pools(env, vc_datcenter, vc_cluster, parent_rp):
    delete_pool = []
    to_be_deleted = []
    if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env) or not parent_rp:
        resource_pool_path = "/" + vc_datcenter + "/host/" + vc_cluster + "/Resources/"
    else:
        resource_pool_path = "/" + vc_datcenter + "/host/" + vc_cluster + "/Resources/" + parent_rp + "/"

    if env == Env.VSPHERE or env == Env.VCF:
        delete_pool.append(ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE)
        if not isEnvTkgs_ns(env) or not isEnvTkgs_wcp(env):
            delete_pool.append(ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE)
            delete_pool.append(ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER)
            delete_pool.append(ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE)
    elif env == Env.VMC:
        delete_pool.append(ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL)
        delete_pool.append(ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME)
        delete_pool.append(ResourcePoolAndFolderName.TKG_Mgmt_RP)
        delete_pool.append(ResourcePoolAndFolderName.AVI_Components_FOLDER)
    else:
        return False, "Wrong environment provided for Resource Pool deletion"

    password = current_app.config['VC_PASSWORD']
    username = current_app.config['VC_USER']
    vcenter_host = current_app.config['VC_IP']

    si = getSi(vcenter_host, username, password)
    content = si.RetrieveContent()

    for resource_pool in delete_pool:
        resource_pool_obj = get_obj(content, [vim.ResourcePool], resource_pool)
        obj = content.searchIndex.FindByInventoryPath(resource_pool_path + resource_pool)
        if obj is None:
            current_app.logger.info(resource_pool + " resource pool does not exist.")
        elif hasattr(resource_pool_obj, 'childEntity'):
            current_app.logger.info(resource_pool + " has child elements. Hence, its deletion is skipped")
        else:
            to_be_deleted.append(resource_pool)

    return True, to_be_deleted


def cleanup_content_libraries(env):
    delete_lib = []
    if isEnvTkgs_wcp(env) or isEnvTkgs_ns(env):
        delete_lib.append(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY)

    delete_lib.append(ControllerLocation.CONTROLLER_CONTENT_LIBRARY)

    list_libraries = ["govc", "library.ls"]
    list_output = runShellCommandAndReturnOutputAsList(list_libraries)
    if list_output[1] != 0:
        current_app.logger.error(list_output[0])
        return False, "Command to list content libraries failed"

    for library in delete_lib:
        if "/"+library in list_output[0]:
            current_app.logger.info(library + " - Content Library exists, deleting it")
            delete_command = ["govc", "library.rm", "/" + library]
            delete_output = runShellCommandAndReturnOutputAsList(delete_command)
            if delete_output[1] != 0:
                current_app.logger.error(delete_output[0])
                return False, "Failed to delete content library - " + library
            elif delete_output[0]:
                if delete_output[0][0].__contains__("403 Forbidden"):
                    current_app.logger.info(delete_output[0])
                    current_app.logger.info(library + " - could not be deleted due to permission issue")
            else:
                current_app.logger.info(library + " - Content Library deleted successfully")
        else:
            current_app.logger.info(library + " - Content Library does not exist")

    return True, "Content Libraries cleanup is successful"


def cleanup_downloaded_ovas(env):
    path = "/tmp/"
    delete_files = [ControllerLocation.CONTENT_LIBRARY_OVA_NAME + ".ova", "arcas-photon-kube-v*.ova",
                    "arcas-ubuntu-kube-v*.ova"]

    for file in delete_files:
        delete_ova = "rm " + path + file
        os.system(delete_ova)
    return True, "All OVAs downloaded during SIVT deployment are deleted."


def get_ova_filename(os, version):
    if version is None:
        version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION

    if os == "photon":
        return KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + version
    elif os == "ubuntu":
        return KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + version
    else:
        return None


def delete_kubernetes_templates(govc_client, vcenter_host, username, password, datacenter, avi_uuid):
    try:
        deployed_templates = get_deployed_templates(vcenter_host, username, password, avi_uuid)
        if deployed_templates[0]:
            deployed_templates = deployed_templates[1]
        else:
            return False
        for template in deployed_templates:
            current_app.logger.info("deleting template - " + template)
            datacenter = datacenter.replace(' ', "#remove_me#")
            vm_path = govc_client.get_vm_path(template, datacenter)
            if vm_path:
                govc_client.delete_vm(template, vm_path)
            current_app.logger.info(f"{template} deleted.")
        return True
    except Exception as e:
        current_app.logger.error("Exception occurred while deleting Kubernetes templates ")
        current_app.logger.error(str(e))
        return False


def get_avi_uuid(center_host, username, password):
    avi_uuid = None
    vm_state = checkVmPresent(center_host, username, password, ControllerLocation.CONTROLLER_NAME)
    if not (vm_state is None):
        avi_uuid = vm_state.config.uuid
    return avi_uuid


def get_deployed_templates(vcenter_host, username, password, avi_uuid):
    try:
        delete_templates = []
        si = getSi(vcenter_host, username, password)
        content = si.RetrieveContent()
        all_vms = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], recursive=True).view

        for vm in all_vms:
            if vm.config.template:
                if vm.name.startswith(KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-") or \
                        vm.name.startswith(KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-"):
                    delete_templates.append(vm.name)
                elif vm.name.startswith(ControllerLocation.SE_OVA_TEMPLATE_NAME) and not (avi_uuid is None):
                    if vm.name == ControllerLocation.SE_OVA_TEMPLATE_NAME + "_" + avi_uuid:
                        delete_templates.append(ControllerLocation.SE_OVA_TEMPLATE_NAME + "_" + avi_uuid)
        return True, delete_templates
    except Exception as e:
        current_app.logger.error(str(e))
        return False, None


def delete_config_yaml():
    command = ["rm", "-r", "/root/.config/tanzu/config.yaml", "/root/.config/tanzu/tkg/config.yaml"]
    delete_output = runShellCommandAndReturnOutputAsList(command)
    if delete_output[1] != 0:
        current_app.logger.error(delete_output[0])
        return False
    return True


def delete_folders(env, vcenter_host, username, password):
    try:
        folders = []
        si = getSi(vcenter_host, username, password)
        content = si.RetrieveContent()
        if env == Env.VSPHERE or env == Env.VCF:
            folders.append(ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE)
            if not isEnvTkgs_ns(env) or not isEnvTkgs_wcp(env):
                folders.append(ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE)
                folders.append(ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE)
                folders.append(ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE)
        elif env == Env.VMC:
            folders.append(ResourcePoolAndFolderName.WORKLOAD_FOLDER)
            folders.append(ResourcePoolAndFolderName.SHARED_FOLDER_NAME)
            folders.append(ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder)
            folders.append(ResourcePoolAndFolderName.AVI_Components_FOLDER)

        for folder in folders:
            folder_obj = get_obj(content, [vim.Folder], folder)
            if folder_obj:
                if folder_obj.childEntity:
                    current_app.logger.info(folder + " folder contains child elements hence, skipping it's deletion")
                else:
                    current_app.logger.info("deleting folder - " + folder)
                    folder_obj.Destroy_Task()
                    #wait_for_task(TASK, si)
                    current_app.logger.info(f"{folder} deleted.")
                    time.sleep(1)
            else:
                current_app.logger.debug("Folder " + folder + " does not exist")
        return True
    except Exception as e:
        current_app.logger.error("Exception occurred while deleting folders")
        current_app.logger.error(str(e))
        return False


def getCluster(cluster):
    podRunninng = ["tanzu", "cluster", "list"]
    command_status = runShellCommandAndReturnOutputAsList(podRunninng)
    if command_status[1] != 0:
        return False

    #fetch the cluster even if it is in error state
    for line in command_status[0]:
        if line.split()[0] == cluster:
            return True
    return False


def getAllClusters_tkgs(vc_ip, vc_user, password, namspaces, vc_cluster):
    cluster_list = []
    current_app.logger.info("Connecting to workload cluster...")
    cluster_id = getClusterID(vc_ip, vc_user, password, vc_cluster)
    if cluster_id[1] != 200:
        current_app.logger.error(cluster_id[0])
        return None, cluster_id[0].json['msg']

    cluster_id = cluster_id[0]
    wcp_status = isWcpEnabled(cluster_id)
    if wcp_status[0]:
        endpoint_ip = wcp_status[1]['api_server_cluster_endpoint']
    else:
        return None, "Failed to obtain cluster endpoint IP on given cluster - " + vc_cluster
    current_app.logger.info("logging into cluster - " + endpoint_ip)
    os.putenv("KUBECTL_VSPHERE_PASSWORD", password)
    for ns in namspaces:
        connect_command = ["kubectl", "vsphere", "login", "--vsphere-username", vc_ip, "--server",
                           endpoint_ip, "--tanzu-kubernetes-cluster-namespace",
                           ns, "--insecure-skip-tls-verify"]
        output = runShellCommandAndReturnOutputAsList(connect_command)
        if output[1] != 0:
            current_app.logger.error(output[0])
            return None, "Failed to login to cluster endpoint - " + endpoint_ip
        switch_context = ["kubectl", "config", "use-context", ns]
        context_output = runShellCommandAndReturnOutputAsList(switch_context)
        if output[1] != 0:
            current_app.logger.error(context_output[0])
            return None, "Failed to login to cluster context - " + ns

        command = ["kubectl", "get", "tkc"]
        cluster_output = runShellCommandAndReturnOutputAsList(command)
        if cluster_output[1] != 0:
            current_app.logger.error(cluster_output[0])
        else:
            for line in cluster_output[0]:
                if not line.__contains__("NAME"):
                    if line.__contains__("No resources found"):
                        current_app.logger.info("No workload clusters found on namespace " + ns)
                    else:
                        cluster_list.append(line.split()[0])

    return cluster_list, "Obtained workload clusters successfully"


def delete_nsxt_components(url, header, list_components):
    for element in list_components:
        response = requests.request("DELETE", url + element, headers=header, verify=False)
        if response.status_code != 200:
            return False, str(response.text)
        else:
            current_app.logger.info(element + " deleted")

    return True, "SUCCESS"


def nsxt_list_groups():
    return [
        VCF.ESXI_GROUP,
        VCF.ARCAS_GROUP,
        GroupNameCgw.DISPLAY_NAME_VCF_vCenter_IP_Group,
        GroupNameCgw.DISPLAY_NAME_VCF_NTP_IPs_Group,
        GroupNameCgw.DISPLAY_NAME_VCF_DNS_IPs_Group,
        GroupNameCgw.DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW]


def nsxt_list_services():
    return [
        ServiceName.ARCAS_BACKEND_SVC,
        ServiceName.ARCAS_SVC,
        ServiceName.KUBE_VIP_VCF_SERVICE]


def vmc_list_mgw_firewall_rules():
    return [
        FirewallRulePrefix.INFRA_TO_VC,
        FirewallRulePrefix.MGMT_TO_ESXI,
        FirewallRuleMgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVItovCenter]


def vmc_list_cgw_firewall_rules():
    return [
        FirewallRulePrefix.INFRA_TO_NTP,
        FirewallRulePrefix.INFRA_TO_DNS,
        FirewallRulePrefix.INFRA_TO_VC,
        FirewallRulePrefix.INFRA_TO_ANY,
        FirewallRulePrefix.INFRA_TO_ALB,
        FirewallRulePrefix.INFRA_TO_CLUSTER_VIP,
        FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS,
        FirewallRuleCgw.DISPLAY_NAME_TKG_WORKLOAD_to_vCenter,
        FirewallRuleCgw.DISPLAY_NAME_WORKLOAD_TKG_and_AVI_to_Internet]


def vmc_list_cgw_inventory_groups():
    return [
        GroupNameCgw.DISPLAY_NAME_AVI_Management_Network_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_TKG_Management_Network_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_TKG_Workload_Networks_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_TKG_SharedService_Group_CGW,
        GroupNameCgw.DISPLAY_NAME_DNS_IPs_Group,
        GroupNameCgw.DISPLAY_NAME_NTP_IPs_Group,
        GroupNameCgw.DISPLAY_NAME_vCenter_IP_Group]


def vmc_list_mgw_inventory_groups():
    return [
        GroupNameMgw.DISPLAY_NAME_TKG_Management_Network_Group_Mgw,
        GroupNameMgw.DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_MGW,
        GroupNameMgw.DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw,
        GroupNameMgw.DISPLAY_NAME_AVI_Management_Network_Group_Mgw,
        GroupNameMgw.DISPLAY_NAME_Tkg_Shared_Network_Group_Mgw]


def list_network_segments(env):
    if env == Env.VMC:
        list_of_segments = [SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT,SegmentsName.DISPLAY_NAME_CLUSTER_VIP,
                            SegmentsName.DISPLAY_NAME_TKG_WORKLOAD,
                            SegmentsName.DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT,
                            SegmentsName.DISPLAY_NAME_TKG_SharedService_Segment,
                            SegmentsName.DISPLAY_NAME_AVI_DATA_SEGMENT]

        listOfSegment = NsxtClient(current_app.config).list_segments(gateway_id='cgw')
        for segment in list_of_segments:
            if not NsxtClient.find_object(listOfSegment, segment):
                current_app.logger.info(segment + " network segment not found in environment.")
                list_of_segments.remove(segment)

    elif env == Env.VCF:
        list_of_segments = [request.get_json(force=True)['tkgComponentSpec']['aviMgmtNetwork']['aviMgmtNetworkName'],
                            request.get_json(force=True)['tkgMgmtDataNetwork']['tkgMgmtDataNetworkName'],
                            request.get_json(force=True)['tkgWorkloadDataNetwork']['tkgWorkloadDataNetworkName'],
                            request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadNetworkName'],
                            request.get_json(force=True)['tkgComponentSpec']['tkgClusterVipNetwork']['tkgClusterVipNetworkName'],
                            request.get_json(force=True)['tkgComponentSpec']['tkgSharedserviceSpec']['tkgSharedserviceNetworkName']]
        headers_ = grabNsxtHeaders()
        if headers_[0] is None:
            current_app.logger.error("Failed to nsxt info " + str(headers_[1]))
            return list_of_segments
        uri = "https://" + headers_[2] + "/policy/api/v1/infra/segments"
        output = getList(headers_[1], uri)
        if output[1] != 200:
            current_app.logger.error("Failed to get list of segments " + str(output[0]))
            return list_of_segments

        for segmentName in list_of_segments:
            if not checkObjectIsPresentAndReturnPath(output[0], segmentName)[0]:
                current_app.logger.info(segmentName + " network segment not found in environment.")
                list_of_segments.remove(segmentName)

    else:
        list_of_segments = []

    return list_of_segments


@cleanup_env.route("/api/tanzu/cleanup-prompt", methods=['POST'])
def cleanup_resources_list():
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
    os.putenv("HOME", "/root")
    if env == Env.VSPHERE or env == Env.VCF:
        vCenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterAddress']
        vCenter_user = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterSsoUser']
        str_enc = str(request.get_json(force=True)['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode('ascii').rstrip("\n")
        vCenter_datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
        vCenter_cluster = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterCluster']

        if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env):
            parent_rp = None
        else:
            parent_rp = request.get_json(force=True)['envSpec']['vcenterDetails']["resourcePoolName"]
            management_cluster = request.get_json(force=True)['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
            if env == Env.VCF:
                shared_cluster = request.get_json(force=True)['tkgComponentSpec']["tkgSharedserviceSpec"]['tkgSharedserviceClusterName']
            else:
                shared_cluster = request.get_json(force=True)['tkgComponentSpec']["tkgMgmtComponents"]['tkgSharedserviceClusterName']
            workload_cluster = request.get_json(force=True)['tkgWorkloadComponents']['tkgWorkloadClusterName']

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
        vCenter_datacenter = request.get_json(force=True)['envSpec']['sddcDatacenter']
        vCenter_cluster = request.get_json(force=True)['envSpec']['sddcCluster']
        parent_rp = request.get_json(force=True)['envSpec']['resourcePoolName']
        management_cluster = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtClusterName']
        shared_cluster = request.get_json(force=True)['componentSpec']['tkgSharedServiceSpec']['tkgSharedClusterName']
        workload_cluster = request.get_json(force=True)['componentSpec']['tkgWorkloadSpec']['tkgWorkloadClusterName']

    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    GovcClient.set_env_vars(govc_client)
    management_cluster_list = []
    work_clusters_list = []
    content_libraries = []
    kubernetes_templates = []
    avi_vms = []
    resource_pools = []
    namespaces = []
    network_segments = []
    supervisor_cluster = ""
    if not isEnvTkgs_wcp(env) and not isEnvTkgs_ns(env):
        if env == Env.VCF or env == Env.VMC:
            network_segments = list_network_segments(env)

        if management_exists(management_cluster):
            management_cluster_list.append(management_cluster)

        if getCluster(workload_cluster):
            work_clusters_list.append(workload_cluster)
        if getCluster(shared_cluster):
            work_clusters_list.append(shared_cluster)

        kubernetes_templates = get_deployed_templates(vCenter, vCenter_user, VC_PASSWORD,
                                                      get_avi_uuid(vCenter, vCenter_user, VC_PASSWORD))[1]

    else:
        sess = requests.post("https://" + vCenter + "/rest/com/vmware/cis/session", auth=(vCenter_user, VC_PASSWORD),
                             verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vCenter,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        id = getClusterID(vCenter, vCenter_user, VC_PASSWORD, vCenter_cluster)
        if id[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": id[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        cluster_id = id[0]

        if getWCPStatus(cluster_id)[0]:
            supervisor_cluster = "Workload Control Plane (WCP) will be disabled on cluster: [ " + vCenter_cluster + " ]"
        else:
            supervisor_cluster = "Workload Control Plane (WCP) is not enabled on cluster: [ " + vCenter_cluster + " ]"

        response = getAllNamespaces()
        if response[1] == 200:
            namespaces = response[0].json["NAMESPACES_LIST"]
        output = getAllClusters_tkgs(vCenter, vCenter_user, VC_PASSWORD, namespaces, vCenter_cluster)
        if not (output[0] is None):
            work_clusters_list = output[0]

    for c_lib in govc_client.get_content_libraries():
        if str(c_lib) == "/"+ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY:
            content_libraries.append(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY)
        elif str(c_lib) == "/"+ControllerLocation.CONTROLLER_CONTENT_LIBRARY:
            content_libraries.append(ControllerLocation.CONTROLLER_CONTENT_LIBRARY)

    vm_list = fetch_avi_vms(govc_client, env, vCenter_datacenter)
    if vm_list[0]:
        avi_vms = vm_list[1]

    response = fetch_resource_pools(env, vCenter_datacenter, vCenter_cluster, parent_rp)
    if response[0]:
        resource_pools = response[1]
    else:
        current_app.logger.warn("Failed to fetch resource pools")

    d = {
        "responseType": "SUCCESS",
        "msg": "got the details",
        "MANAGEMENT_CLUSTERS": management_cluster_list,
        "WORKLOAD_CLUSTERS": work_clusters_list,
        "CONTENT_LIBRARY": content_libraries,
        "KUBERNETES_TEMPLATES": kubernetes_templates,
        "AVI_VMS": avi_vms,
        "RESOURCE_POOLS": resource_pools,
        "NETWORK_SEGMENTS": network_segments,
        "NAMESPACES": namespaces,
        "PORT_GROUPS": network_segments,
        "SUPERVISOR_CLUSTER": supervisor_cluster,
        "ERROR_CODE": 200
    }
    return jsonify(d), 200
