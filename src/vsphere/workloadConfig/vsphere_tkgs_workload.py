from common.common_utilities import checkTmcEnabled, get_alias_name, getPolicyID, getLibraryId, \
    convertStringToCommaSeperated, supervisorTMC, configureKubectl, \
    getClusterID, checkTmcEnabled, getPolicyID, getLibraryId, \
    convertStringToCommaSeperated, supervisorTMC, configureKubectl, getBodyResourceSpec, cidr_to_netmask, \
    seperateNetmaskAndIp, getCountOfIpAdress, createClusterFolder
from flask import current_app, jsonify, request
import time
import yaml
import json
import requests
from pathlib import Path
from ruamel import yaml as ryaml
from common.certificate_base64 import getBase64CertWriteToFile
import base64
from common.operation.constants import RegexPattern, ControllerLocation, Paths
from common.operation.ShellHelper import runShellCommandAndReturnOutput, grabKubectlCommand, grabIpAddress, \
    verifyPodsAreRunning, grabPipeOutput, runShellCommandAndReturnOutputAsList, \
    runShellCommandAndReturnOutputAsListWithChangedDir, grabPipeOutputChagedDir, runShellCommandWithPolling, runProcess
from common.prechecks.precheck import checkClusterVersionCompatibility
from common.operation.vcenter_operations import getDvPortGroupId


def createTkgWorkloadCluster(env, vc_ip, vc_user, vc_password):
    try:
        url_ = "https://" + vc_ip + "/"
        sess = requests.post(url_ + "rest/com/vmware/cis/session", auth=(vc_user, vc_password), verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vc_ip,
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
        if str(cluster_name).__contains__("/"):
            cluster_name = cluster_name[cluster_name.rindex("/")+1:]
        id = getClusterID(vc_ip, vc_user, vc_password, cluster_name)
        if id[1] != 200:
            return None, id[0]
        clusterip_resp = requests.get(url_ + "api/vcenter/namespace-management/clusters/" + str(id[0]), verify=False,
                                      headers=header)
        if clusterip_resp.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch API server cluster endpoint - " + vc_ip,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500

        cluster_endpoint = clusterip_resp.json()["api_server_cluster_endpoint"]

        configure_kubectl = configureKubectl(cluster_endpoint)
        if configure_kubectl[1] != 200:
            return configure_kubectl[0], 500
        supervisorTMC(vc_user, vc_password, cluster_endpoint)
        current_app.logger.info("Switch context to name space")
        name_space = \
            request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']

        workload_name = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
        if not createClusterFolder(workload_name):
            d = {
                "responseType": "ERROR",
                "msg": "Failed to create directory: " + Paths.CLUSTER_PATH + workload_name,
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info(
            "The config files for shared services cluster will be located at: " + Paths.CLUSTER_PATH + workload_name)
        current_app.logger.info("Before deploying cluster, checking if namespace is in running status..." + name_space)
        wcp_status = checkClusterStatus(vc_ip, header, name_space, id[0])
        if wcp_status[0] is None:
            return None, wcp_status[1]

        switch = ["kubectl", "config", "use-context", name_space]
        switch_context = runShellCommandAndReturnOutputAsList(switch)
        if switch_context[1] != 0:
            return None, "Failed to switch  to context " + str(switch_context[0]), 500
        command = ["kubectl", "get", "tanzukubernetescluster"]
        cluster_list = runShellCommandAndReturnOutputAsList(command)
        if cluster_list[1] != 0:
            return None, "Failed to get list of cluster " + str(cluster_list[0]), 500
        if str(cluster_list[0]).__contains__(workload_name):
            current_app.logger.info("Cluster with same name already exist - " + workload_name)
            return "Cluster with same name already exist ", 200
        if checkTmcEnabled(env):
            supervisor_cluster = request.get_json(force=True)['envSpec']["saasEndpoints"]['tmcDetails'][
                'tmcSupervisorClusterName']
            current_app.logger.info("Creating workload cluster...")
            name_space = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec'][
                'tkgsVsphereNamespaceName']
            version = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterVersion']

            # if user using json and v not appended to version
            if not version.startswith('v'):
                version = 'v' + version
            is_compatible = checkClusterVersionCompatibility(vc_ip, vc_user, vc_password, cluster_name, version)
            if is_compatible[0]:
                current_app.logger.info("Provided cluster version is valid !")
            else:
                return None, is_compatible[1]
            pod_cidr = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec'][
                'podCidrBlocks']
            service_cidr = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['serviceCidrBlocks']
            node_storage_class_input = \
                request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['nodeStorageClass']
            policy_id = getPolicyID(node_storage_class_input, vc_ip, vc_user, vc_password)
            if policy_id[0] is None:
                return None, "Failed to get policy id"
            allowed_ = get_alias_name(policy_id[0])
            if allowed_[0] is None:
                current_app.logger.error(allowed_[1])
                return None, "Failed to get Alias name"
            node_storage_class = allowed_[0]
            allowed_storage = \
                request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['allowedStorageClasses']
            allowed = ""
            classes = allowed_storage
            for c in classes:
                policy_id = getPolicyID(c, vc_ip, vc_user, vc_password)
                if policy_id[0] is None:
                    return None, "Failed to get policy id"
                allowed_ = get_alias_name(policy_id[0])
                if allowed_[0] is None:
                    current_app.logger.error(allowed_[1])
                    return None, "Failed to alias name"
                allowed += str(allowed_[0]) + ","
            if not allowed:
                current_app.logger.error("Failed to get allowed classes")
                return None, "Failed to get allowed classes"
            allowed = allowed.strip(",")
            default_storage_class = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['defaultStorageClass']
            policy_id = getPolicyID(default_storage_class, vc_ip, vc_user, vc_password)
            if policy_id[0] is None:
                return None, "Failed to get policy id"
            default = get_alias_name(policy_id[0])
            if default[0] is None:
                current_app.logger.error(default[1])
                return None, "Failed to get Alias name"
            default_class = default[0]
            worker_node_count = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['workerNodeCount']
            enable_ha = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['enableControlPlaneHa']
            clusterGroup = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']["tkgsWorkloadClusterGroupName"]
            worker_vm_class = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['workerVmClass']
            if not clusterGroup:
                clusterGroup = "default"

            if str(enable_ha).lower() == "true":
                workload_cluster_create_command = ["tmc", "cluster", "create", "--template", "tkgs", "-m",
                                                   supervisor_cluster, "-p", name_space, "--cluster-group",
                                                   clusterGroup,
                                                   "--name", workload_name, "--version",
                                                   version, "--pods-cidr-blocks", pod_cidr, "--service-cidr-blocks",
                                                   service_cidr, "--storage-class", node_storage_class,
                                                   "--allowed-storage-classes", allowed,
                                                   "--default-storage-class", default_class,
                                                   "--worker-instance-type", worker_vm_class, "--instance-type",
                                                   worker_vm_class, "--worker-node-count", worker_node_count,
                                                   "--high-availability"]
            else:
                workload_cluster_create_command = ["tmc", "cluster", "create", "--template", "tkgs", "-m",
                                                   supervisor_cluster, "-p", name_space, "--cluster-group",
                                                   clusterGroup,
                                                   "--name", workload_name, "--version",
                                                   version, "--pods-cidr-blocks", pod_cidr, "--service-cidr-blocks",
                                                   service_cidr, "--storage-class", node_storage_class,
                                                   "--allowed-storage-classes", allowed,
                                                   "--default-storage-class", default_class,
                                                   "--worker-instance-type", worker_vm_class, "--instance-type",
                                                   worker_vm_class, "--worker-node-count", worker_node_count]
            try:
                control_plane_volumes = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['controlPlaneVolumes']
                control_plane_volumes_list = []
                for control_plane_volume in control_plane_volumes:
                    if control_plane_volume['storageClass']:
                        storageClass = control_plane_volume['storageClass']
                    else:
                        storageClass = default_class
                    control_plane_volumes_list.append(
                        dict(name=control_plane_volume['name'], mountPath=control_plane_volume['mountPath'],
                             capacity=dict(storage=control_plane_volume['storage']), storageClass=storageClass))
                control_plane_vol = True
            except Exception as e:
                control_plane_vol = False
            try:
                worker_volumes = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                    'tkgsVsphereWorkloadClusterSpec']['workerVolumes']
                worker_vol = True
                worker_volumes_list = []
                for worker_volume in worker_volumes:
                    if worker_volume['storageClass']:
                        storageClass = worker_volume['storageClass']
                    else:
                        storageClass = default_class
                    worker_volumes_list.append(dict(name=worker_volume['name'], mountPath=worker_volume['mountPath'],
                                                    capacity=dict(storage=worker_volume['storage']),
                                                    storageClass=storageClass))
            except Exception as e:
                worker_vol = False
            if control_plane_vol and worker_vol:
                workload_cluster_create_command.append("--control-plane-volumes")
                control_plane_command = ""
                for control_plane_volumes in control_plane_volumes_list:
                    control_plane_command += control_plane_volumes["name"] + ":[" + control_plane_volumes[
                        "mountPath"] + " " + str(control_plane_volumes['capacity']["storage"]).lower().strip(
                        "gi") + " " + control_plane_volumes['storageClass'] + "],"
                workload_cluster_create_command.append("\"" + control_plane_command.strip(",") + "\"")
                workload_cluster_create_command.append("--nodepool-volumes")
                worker_command = ""
                for worker_volumes in worker_volumes_list:
                    worker_command += worker_volumes["name"] + ":[" + worker_volumes["mountPath"] + " " + \
                                      str(worker_volumes['capacity']["storage"]).lower().strip("gi") + " " + \
                                      worker_volumes['storageClass'] + "]"
                workload_cluster_create_command.append("\"" + worker_command.strip(",") + "\"")
            elif control_plane_vol:
                workload_cluster_create_command.append("--control-plane-volumes")
                control_plane_command = ""
                for control_plane_volumes in control_plane_volumes_list:
                    control_plane_command += control_plane_volumes["name"] + ":[" + control_plane_volumes[
                        "mountPath"] + " " + str(control_plane_volumes['capacity']["storage"]).lower().strip(
                        "gi") + " " + control_plane_volumes['storageClass'] + "],"
                workload_cluster_create_command.append("\"" + control_plane_command.strip(",") + "\"")
            elif worker_vol:
                workload_cluster_create_command.append("--nodepool-volumes")
                worker_command = ""
                for worker_volumes in worker_volumes_list:
                    worker_command += worker_volumes["name"] + ":[" + worker_volumes["mountPath"] + " " + \
                                      str(worker_volumes['capacity']["storage"]).lower().strip("gi") + " " + \
                                      worker_volumes['storageClass'] + "]"
                workload_cluster_create_command.append("\"" + worker_command.strip(",") + "\"")
            current_app.logger.info(workload_cluster_create_command)
            worload = runShellCommandAndReturnOutputAsList(workload_cluster_create_command)
            if worload[1] != 0:
                return None, "Failed to create  workload cluster " + str(worload[0])
            current_app.logger.info("Waiting for 2 min for checking status == ready")
            time.sleep(120)
            command_monitor = ["tmc", "cluster", "get", workload_name, "-m", supervisor_cluster, "-p", name_space]
            count = 0
            found = False
            while count < 135:
                o = runShellCommandAndReturnOutput(command_monitor)
                if o[1] == 0:
                    l = yaml.safe_load(o[0])
                    try:
                        phase = str(l["status"]["phase"])
                        wcm = str(l["status"]["conditions"]["WCM-Ready"]["status"])
                        health = str(l["status"]["health"])
                        if phase == "READY" and wcm == "TRUE" and health == "HEALTHY":
                            found = True
                            current_app.logger.info(
                                "Phase status " + phase + " wcm status " + wcm + " Health status " + health)
                            break
                        current_app.logger.info(
                            "Phase status " + phase + " wcm status " + wcm + " Health status " + health)
                    except:
                        pass
                time.sleep(20)
                current_app.logger.info("Waited for " + str(count * 20) + "s, retrying")
                count = count + 1
            if not found:
                return None, "Cluster not in ready state"
            return "SUCCESS", 200
        else:
            try:
                gen = generateYamlFile(vc_ip, vc_user, vc_password, workload_name)
                if gen is None:
                    return None, "Failed"
            except Exception as e:
                return None, "Failed to generate yaml file " + str(e)

            command = ["kubectl", "apply", "-f", gen]
            worload = runShellCommandAndReturnOutputAsList(command)
            if worload[1] != 0:
                return None, "Failed to create workload " + str(worload[0])
            current_app.logger.info(worload[0])
            name_space = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
            workload_name = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
            current_app.logger.info("Waiting for cluster creation to be initiated...")
            time.sleep(60)
            command = ["kubectl", "get", "tkc", "-n", name_space]
            count = 0
            found = False
            while count < 90:
                worload = runShellCommandAndReturnOutputAsList(command)
                if worload[1] != 0:
                    return None, "Failed to monitor workload " + str(worload[0])

                index = None
                for item in range(len(worload[0])):
                    if worload[0][item].split()[0] == workload_name:
                        index = item
                        break

                if index is None:
                    return None, "Unable to find cluster..."

                output = worload[0][index].split()
                if not ((output[5] == "True" or output[5] == "running") and output[6] == "True"):
                    current_app.logger.info("Waited for " + str(count * 30) + "s, retrying")
                    count = count + 1
                    time.sleep(30)
                else:
                    found = True
                    break
            if not found:
                current_app.logger.error("Cluster is not up and running on waiting " + str(count * 30) + "s")
                return None, "Failed"
            return "SUCCESS", "DEPLOYED"
    except Exception as e:
        return None, "Failed to create tkg workload cluster  " + str(e)


def checkClusterStatus(vc_ip, header, name_space, cluster_id):
    try:
        url = "https://" + str(vc_ip) + "/api/vcenter/namespaces/instances"
        namespace_status = checkNameSpaceRunningStatus(url, header, name_space, cluster_id)
        running = False
        if namespace_status[0] != "SUCCESS":
            current_app.logger.info("Namespace is not in running status... retrying")
        else:
            running = True

        count = 0
        while count < 60 and not running:
            namespace_status = checkNameSpaceRunningStatus(url, header, name_space, cluster_id)
            if namespace_status[0] == "SUCCESS":
                running = True
                break
            count = count + 1
            time.sleep(5)
            current_app.logger.info("Waited for " + str(count * 1) + "s ...retrying")

        if not running:
            return None, "Namespace is not in running status - " + name_space + ". Waited for " + str(
                count * 5) + "seconds"

        current_app.logger.info("Checking Cluster WCP status...")
        url1 = "https://" + vc_ip + "/api/vcenter/namespace-management/clusters/" + str(cluster_id)
        count = 0
        found = False
        while count < 60 and not found:
            response_csrf = requests.request("GET", url1, headers=header, verify=False)
            try:
                if response_csrf.json()["config_status"] == "RUNNING":
                    found = True
                    break
                else:
                    if response_csrf.json()["config_status"] == "ERROR":
                        return None, "WCP status in ERROR"
                current_app.logger.info("Cluster config status " + response_csrf.json()["config_status"])
            except:
                pass
            time.sleep(20)
            count = count + 1
            current_app.logger.info("Waited " + str(count * 20) + "s, retrying")
        if not found:
            current_app.logger.error("Cluster is not running on waiting " + str(count * 20))
            return None, "Failed"
        else:
            current_app.logger.info("WCP config status " + response_csrf.json()["config_status"])

        return "SUCCESS", "WCP and Namespace configuration check pass"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while checking cluster config status"


def generateYamlFile(vc_ip, vc_user, vc_password, workload_name):
    workload_name = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterName']
    file = Paths.CLUSTER_PATH + workload_name + "/tkgs_workload.yaml"
    command = ["rm", "-rf", file]
    runShellCommandAndReturnOutputAsList(command)
    name_space = \
        request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereNamespaceName']
    enable_ha = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['enableControlPlaneHa']
    if str(enable_ha).lower() == "true":
        count = "3"
    else:
        count = "1"
    control_plane_vm_class = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['controlPlaneVmClass']
    node_storage_class = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['nodeStorageClass']
    policy_id = getPolicyID(node_storage_class, vc_ip, vc_user, vc_password)
    if policy_id[0] is None:
        current_app.logger.error("Failed to get policy id")
        return None
    allowed_ = get_alias_name(policy_id[0])
    if allowed_[0] is None:
        current_app.logger.error(allowed_[1])
        return None
    node_storage_class = str(allowed_[0])
    worker_node_count = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['workerNodeCount']
    worker_vm_class = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['workerVmClass']
    cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
    if str(cluster_name).__contains__("/"):
        cluster_name = cluster_name[cluster_name.rindex("/")+1:]
    kube_version = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['tkgsVsphereWorkloadClusterVersion']
    if not kube_version.startswith('v'):
        kube_version = 'v' + kube_version
    is_compatible = checkClusterVersionCompatibility(vc_ip, vc_user, vc_password, cluster_name, kube_version)
    if is_compatible[0]:
        current_app.logger.info("Provided cluster version is valid !")
    else:
        return None
    service_cidr = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['serviceCidrBlocks']
    pod_cidr = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['podCidrBlocks']
    allowed_clases = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['allowedStorageClasses']
    allowed = ""
    classes = allowed_clases
    for c in classes:
        policy_id = getPolicyID(c, vc_ip, vc_user, vc_password)
        if policy_id[0] is None:
            current_app.logger.error("Failed to get policy id")
            return None
        allowed_ = get_alias_name(policy_id[0])
        if allowed_[0] is None:
            current_app.logger.error(allowed_[1])
            return None
        allowed += str(allowed_[0]) + ","
    if allowed is None:
        current_app.logger.error("Failed to get allowed classes")
        return None
    allowed = allowed.strip(",")
    li = convertStringToCommaSeperated(allowed)
    default_clases = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
        'tkgsVsphereWorkloadClusterSpec']['defaultStorageClass']
    policy_id = getPolicyID(default_clases, vc_ip, vc_user, vc_password)
    if policy_id[0] is None:
        current_app.logger.error("Failed to get policy id")
        return None
    allowed_ = get_alias_name(policy_id[0])
    if allowed_[0] is None:
        current_app.logger.error(allowed_[1])
        return None
    default_clases = str(allowed_[0])
    try:
        control_plane_volumes = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['controlPlaneVolumes']
        control_plane_volumes_list = []
        for control_plane_volume in control_plane_volumes:
            control_plane_volumes_list.append(
                dict(name=control_plane_volume['name'], mountPath=control_plane_volume['mountPath'],
                     capacity=dict(storage=control_plane_volume['storage'])))
        control_plane_vol = True
    except Exception as e:
        control_plane_vol = False
    try:
        worker_volumes = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereWorkloadClusterSpec']['workerVolumes']
        worker_vol = True
        worker_volumes_list = []
        for worker_volume in worker_volumes:
            worker_volumes_list.append(dict(name=worker_volume['name'], mountPath=worker_volume['mountPath'],
                                            capacity=dict(storage=worker_volume['storage'])))
    except Exception as e:
        worker_vol = False

    if worker_vol and control_plane_vol:
        topology_dict = {
            "controlPlane": {
                "count": int(count),
                "class": control_plane_vm_class,
                "storageClass": node_storage_class,
                "volumes": control_plane_volumes_list
            },
            "workers": {
                "count": int(worker_node_count),
                "class": worker_vm_class,
                "storageClass": node_storage_class,
                "volumes": worker_volumes_list
            }
        }
    elif control_plane_vol:
        topology_dict = {
            "controlPlane": {
                "count": int(count),
                "class": control_plane_vm_class,
                "storageClass": node_storage_class,
                "volumes": control_plane_volumes_list
            },
            "workers": {
                "count": int(worker_node_count),
                "class": worker_vm_class,
                "storageClass": node_storage_class
            }
        }
    elif worker_vol:
        topology_dict = {
            "controlPlane": {
                "count": int(count),
                "class": control_plane_vm_class,
                "storageClass": node_storage_class
            },
            "workers": {
                "count": int(worker_node_count),
                "class": worker_vm_class,
                "storageClass": node_storage_class,
                "volumes": worker_volumes_list
            }
        }
    else:
        topology_dict = {
            "controlPlane": {
                "count": int(count),
                "class": control_plane_vm_class,
                "storageClass": node_storage_class
            },
            "workers": {
                "count": int(worker_node_count),
                "class": worker_vm_class,
                "storageClass": node_storage_class
            }
        }
    meta_dict = {
        "name": workload_name,
        "namespace": name_space
    }
    try:
        cni = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['defaultCNI']
        if cni:
            defaultCNI = cni
            isCni = True
        else:
            defaultCNI = "antrea"
            isCni = False
    except:
        defaultCNI = "antrea"
        isCni = False
    spec_dict = {
        "topology": topology_dict,
        "distribution": {
            "version": kube_version
        },
        "settings": {
            "network": {
                "services": {
                    "cidrBlocks": [service_cidr]
                },
                "pods": {
                    "cidrBlocks": [pod_cidr]
                }
            },
            "storage": {
                "classes": li,
                "defaultClass": default_clases
            }
        }
    }
    if isCni:
        default = dict(cni=dict(name=defaultCNI))
        spec_dict["settings"]["network"].update(default)
    try:
        isProxyEnabled = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['enableProxy']
        if str(isProxyEnabled).lower() == "true":
            proxyEnabled = True
        else:
            proxyEnabled = False
    except:
        proxyEnabled = False
    if proxyEnabled:
        try:
            httpProxy = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['httpProxy']
            httpsProxy = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['httpsProxy']
            noProxy = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['noProxy']
            list_ = convertStringToCommaSeperated(noProxy)
        except Exception as e:
            return None, str(e)
        proxy = dict(proxy=dict(httpProxy=httpProxy, httpsProxy=httpsProxy, noProxy=list_))
        spec_dict["settings"]["network"].update(proxy)
        cert_list = []
        isProxy = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['proxySpec']['proxyCert']
        if isProxy:
            cert = Path(isProxy).read_text()
            string_bytes = cert.encode("ascii")
            base64_bytes = base64.b64encode(string_bytes)
            cert_base64 = base64_bytes.decode("ascii")
            cert_list.append(dict(name="certProxy", data=cert_base64))
        proxyPath = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs']['paths']
        proxyEndpoints = request.get_json(force=True)['tkgsComponentSpec']['tkgServiceConfig']['additionalTrustedCAs']['endpointUrls']
        if proxyPath:
            proxyCert = proxyPath
            isProxyCert = True
            isCaPath = True
        elif proxyEndpoints:
            proxyCert = proxyEndpoints
            isProxyCert = True
            isCaPath = False
        else:
            isProxyCert = False
            isCaPath = False
        if isProxyCert:
            count = 0
            for certs in proxyCert:
                count = count + 1
                if isCaPath:
                    cert = Path(certs).read_text()
                    string_bytes = cert.encode("ascii")
                    base64_bytes = base64.b64encode(string_bytes)
                    cert_base64 = base64_bytes.decode("ascii")
                else:
                    getBase64CertWriteToFile(certs, "443")
                    with open('cert.txt', 'r') as file2:
                        cert_base64 = file2.readline()
                cert_list.append(dict(name="cert" + str(count), data=cert_base64))
        trust = dict(trust=dict(additionalTrustedCAs=cert_list))
        spec_dict["settings"]["network"].update(trust)
    ytr = dict(apiVersion='run.tanzu.vmware.com/v1alpha1', kind='TanzuKubernetesCluster', metadata=meta_dict,
               spec=spec_dict)
    with open(file, 'w') as outfile:
        # formatted = ytr % (
        # workload_name, name_space, count, control_plane_vm_class, node_storage_class, worker_node_count,
        # worker_vm_class, node_storage_class, kube_version, service_cidr, pod_cidr, li, default_clases)
        # data1 = ryaml.load(formatted, Loader=ryaml.RoundTripLoader)
        ryaml.dump(ytr, outfile, Dumper=ryaml.RoundTripDumper, indent=2)
    return file


def createNameSpace(vcenter_ip, vcenter_username, password):
    try:
        sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                             auth=(vcenter_username, password),
                             verify=False)
        if sess.status_code != 200:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to fetch session ID for vCenter - " + vcenter_ip,
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
        name_space = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereNamespaceName']
        url = "https://" + str(vcenter_ip) + "/api/vcenter/namespaces/instances"
        cluster_name = request.get_json(force=True)["envSpec"]["vcenterDetails"]["vcenterCluster"]
        if str(cluster_name).__contains__("/"):
            cluster_name = cluster_name[cluster_name.rindex("/")+1:]
        id = getClusterID(vcenter_ip, vcenter_username, password, cluster_name)
        if id[1] != 200:
            return None, id[0]
        status = checkNameSpaceRunningStatus(url, header, name_space, id[0])
        if status[0] is None:
            if status[1] == "NOT_FOUND":
                pass
            elif status[1] == "NOT_FOUND_INITIAL":
                pass
            elif status[1] == "NOT_RUNNING":
                return None, "Name is already created but not in running state"
        if status[0] == "SUCCESS":
            return "SUCCESS", name_space + " already created"
        try:
            cpu_limit = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereNamespaceResourceSpec']['cpuLimit']
        except Exception as e:
            cpu_limit = ""
            current_app.logger.info("CPU Limit is not provided, will continue without setting Custom CPU Limit")
        try:
            memory_limit = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereNamespaceResourceSpec']['memoryLimit']
        except Exception as e:
            memory_limit = ""
            current_app.logger.info("Memory Limit is not provided, will continue without setting Custom Memory Limit")
        try:
            storage_limit = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
                'tkgsVsphereNamespaceResourceSpec']['storageRequestLimit']
        except Exception as e:
            storage_limit = ""
            current_app.logger.info("Storage Request Limit is not provided, will continue without setting Custom "
                                    "Storage Request Limit")
        content_library = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereNamespaceContentLibrary']
        resource_spec = getBodyResourceSpec(cpu_limit, memory_limit, storage_limit)
        if not content_library:
            content_library = ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY
        lib = getLibraryId(vcenter_ip, vcenter_username, password, content_library)
        if lib is None:
            return None, "Failed to get content library id " + content_library
        name_space_vm_classes = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereNamespaceVmClasses']
        storage_specs = request.get_json(force=True)['tkgsComponentSpec']["tkgsVsphereNamespaceSpec"][
            'tkgsVsphereNamespaceStorageSpec']
        list_storage = []
        for storage_spec in storage_specs:
            policy = storage_spec["storagePolicy"]
            policy_id = getPolicyID(policy, vcenter_ip, vcenter_username, password)
            if policy_id[0] is None:
                current_app.logger.error("Failed to get policy id")
                return None, policy_id[1]
            if "storageLimit" in storage_spec:
                if not storage_spec["storageLimit"]:
                    list_storage.append(dict(policy=policy_id[0]))
                else:
                    list_storage.append(dict(limit=storage_spec["storageLimit"], policy=policy_id[0]))
            else:
                list_storage.append(dict(policy=policy_id[0]))
        workload_network = request.get_json(force=True)['tkgsComponentSpec']['tkgsWorkloadNetwork'][
            'tkgsWorkloadNetworkName']
        network_status = checkWorkloadNetwork(vcenter_ip, vcenter_username, password, id[0], workload_network)
        if network_status[1] and network_status[0] == "SUCCESS":
            current_app.logger.info("Workload network is already created - " + workload_network)
            current_app.logger.info("Using " + workload_network + " network for creating namespace " + name_space)
        elif network_status[0] == "NOT_CREATED":
            create_status = create_workload_network(vcenter_ip, vcenter_username, password, id[0], workload_network)
            if create_status[0] == "SUCCESS":
                current_app.logger.info("Workload network created successfully - " + workload_network)
            else:
                current_app.logger.error("Failed to created workload network - " + workload_network)
                return None, create_status[1]
        else:
            return None, network_status[0]

        body = {
            "cluster": id[0],
            "description": "name space",
            "namespace": name_space,
            "networks": [workload_network],
            "resource_spec": resource_spec,
            "storage_specs": list_storage,
            "vm_service_spec": {
                "content_libraries": [lib],
                "vm_classes": name_space_vm_classes
            }
        }
        json_object = json.dumps(body, indent=4)
        url = "https://" + str(vcenter_ip) + "/api/vcenter/namespaces/instances"
        response_csrf = requests.request("POST", url, headers=header, data=json_object, verify=False)
        if response_csrf.status_code != 204:
            return None, "Failed to create name-space " + response_csrf.text
        count = 0
        while count < 30:
            status = checkNameSpaceRunningStatus(url, header, name_space, id[0])
            if status[0] == "SUCCESS":
                break
            current_app.logger.info("Waited for " + str(count * 10) + "s, retrying")
            count = count + 1
            time.sleep(10)
        return "SUCCESS", "CREATED"
    except Exception as e:
        return None, str(e)


def create_workload_network(vCenter, vc_user, password, cluster_id, network_name):
    worker_cidr = request.get_json(force=True)['tkgsComponentSpec']['tkgsWorkloadNetwork'][
        'tkgsWorkloadNetworkGatewayCidr']
    start = request.get_json(force=True)['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadNetworkStartRange']
    end = request.get_json(force=True)['tkgsComponentSpec']['tkgsWorkloadNetwork']['tkgsWorkloadNetworkEndRange']
    port_group_name = request.get_json(force=True)['tkgsComponentSpec']['tkgsWorkloadNetwork'][
        'tkgsWorkloadPortgroupName']
    datacenter = request.get_json(force=True)['envSpec']['vcenterDetails']['vcenterDatacenter']
    if str(datacenter).__contains__("/"):
        datacenter = datacenter[datacenter.rindex("/")+1:]
    if not (worker_cidr or start or end or port_group_name):
        return None, "Details to create workload network are not provided - " + network_name
    ip_cidr = seperateNetmaskAndIp(worker_cidr)
    count_of_ip = getCountOfIpAdress(worker_cidr, start, end)
    worker_network_id = getDvPortGroupId(vCenter, vc_user, password, port_group_name, datacenter)

    sess = requests.post("https://" + str(vCenter) + "/rest/com/vmware/cis/session",
                         auth=(vc_user, password), verify=False)
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

    body = {
        "network": network_name,
        "network_provider": "VSPHERE_NETWORK",
        "vsphere_network": {
            "address_ranges": [{
                "address": start,
                "count": count_of_ip
            }],
            "gateway": ip_cidr[0],
            "ip_assignment_mode": "STATICRANGE",
            "portgroup": worker_network_id,
            "subnet_mask": cidr_to_netmask(worker_cidr)
        }
    }

    json_object = json.dumps(body, indent=4)
    url1 = "https://" + vCenter + "/api/vcenter/namespace-management/clusters/" + cluster_id + "/networks"
    create_response = requests.request("POST", url1, headers=header, data=json_object, verify=False)
    if create_response.status_code == 204:
        return "SUCCESS", "Workload network created successfully"
    else:
        return None, create_response.txt


def checkWorkloadNetwork(vcenter_ip, vc_user, password, cluster_id, workload_network):
    sess = requests.post("https://" + str(vcenter_ip) + "/rest/com/vmware/cis/session",
                         auth=(vc_user, password), verify=False)
    if sess.status_code != 200:
        current_app.logger.error("Connection to vCenter failed")
        return "Connection to vCenter failed", False
    else:
        vc_session = sess.json()['value']
    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "vmware-api-session-id": vc_session
    }

    url = "https://" + vcenter_ip + "/api/vcenter/namespace-management/clusters/" + cluster_id + "/networks"
    response_networks = requests.request("GET", url, headers=header, verify=False)
    if response_networks.status_code != 200:
        return "Failed to fetch workload networks for given cluster", False

    for network in response_networks.json():
        if network["network"] == workload_network:
            return "SUCCESS", True
    else:
        return "NOT_CREATED", False


def checkNameSpaceRunningStatus(url, header, name_space, cluster_id):
    response_csrf = requests.request("GET", url, headers=header, verify=False)
    if response_csrf.status_code != 200:
        return None, "Failed to get namespace list " + str(response_csrf.text)
    found = False
    if len(response_csrf.json()) < 1:
        current_app.logger.info("No name space is created")
        return None, "NOT_FOUND_INITIAL"
    else:
        for name in response_csrf.json():
            if name['cluster'] == cluster_id:
                if name['namespace'] == name_space:
                    found = True
                    break
    if found:
        running = False
        current_app.logger.info(name_space + " name space  is already created")
        current_app.logger.info("Checking Running status")
        for name in response_csrf.json():
            if name['cluster'] == cluster_id:
                if name['namespace'] == name_space:
                    if name['config_status'] == "RUNNING":
                        running = True
                        break
        if running:
            current_app.logger.info(name_space + " name space  is running")
            return "SUCCESS", "RUNNING"
        else:
            current_app.logger.info(name_space + " name space  is not running")
            return None, "NOT_RUNNING"
    else:
        return None, "NOT_FOUND"
