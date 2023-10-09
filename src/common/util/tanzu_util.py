# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
import os
import time
from datetime import datetime
from http import HTTPStatus

from flask import current_app

from common.operation.constants import AppName, Env, Paths, RegexPattern, Repo, TKG_Package_Details
from common.operation.ShellHelper import (
    grabKubectlCommand,
    grabPipeOutput,
    runProcess,
    runShellCommandAndReturnOutput,
    runShellCommandAndReturnOutputAsJson,
    runShellCommandAndReturnOutputAsList,
    verifyPodsAreRunning,
)
from common.util.request_api_util import RequestApiUtil
from common.util.singleton_class_util import Singleton


class TanzuCommands:
    INSTALLED_LIST_PACKAGE = "tanzu package installed list -A"
    INSTALLED_LIST_PACKAGE_JSON = "tanzu package installed list -A -o json"
    DELETE_PACKAGE = "tanzu package installed delete {package_name} -n {name_space} -y"
    CONFIG_SET = "tanzu config set {key} {value}"
    REPOSITORY_LIST = "tanzu package repository list -A"
    PACKAGE_REPO_ADD = "tanzu package repository add {repo_name} --url {url} -n {namespace}"
    REPOSITORY_LIST_NAMESPACE = "tanzu package repository list -n {namespace}"
    LIST_CONFIG = "tanzu config server list"
    DELETE_CONFIG_SERVER = "tanzu config server delete {cluster_endpoint} -y"
    CLUSTER_LIST_WITH_MANAGEMENT = "tanzu cluster list --include-management-cluster -A"
    CLUSTER_LIST = "tanzu cluster list"
    MANAGEMENT_CLUSTER_GET = "tanzu management-cluster get"
    MANAGEMENT_CLUSTER_DELETE = "tanzu management-cluster delete --force -y"
    CLUSTER_GET = "tanzu cluster get"
    GET_AVAILABLE_PACKAGE = "tanzu package available list {package_name} -A"
    GET_CLUSTER_CONTEXT = "tanzu cluster kubeconfig get {cluster_name} --admin"
    GET_MANAGEMENT_CLUSTER_CONTEXT = "tanzu management-cluster kubeconfig get {cluster_name} --admin"
    GET_CLUSTER_CONTEXT_NAMESPACE = "tanzu cluster kubeconfig get {cluster_name} --admin -n {name_space}"
    CLUSTER_CREATE = "tanzu cluster create -f {file_path} --tkr {kube_version} -v 6"
    CLUSTER_DELETE = "tanzu cluster delete {cluster_name} -y"
    CREATE_MGMT_CLUSTER = "tanzu management-cluster create -y --file {file_path} -v 6"
    PLUGIN_SYNC = "tanzu plugin sync"
    CONFIG_INIT = "tanzu config init"
    ACCEPT_EULA = "tanzu config eula accept"
    INSTALL_PLUGIN = "tanzu plugin install --group vmware-tkg/default:v2.4.0"
    CONFIG_ACCEPT = "tanzu config list_of_cmd accept"


class TanzuUtil(metaclass=Singleton):
    def __init__(self, spec=None, env=None):
        from common.util.cluster_yaml_dump_util import ClusterYaml
        from common.util.tkgs_util import TkgsUtil

        self._spec = spec
        self._env = env
        if self.env != Env.VMC:
            self.tkgs_util = TkgsUtil(spec)
        self.cluster_yaml_util = ClusterYaml(env, spec)

    @property
    def spec(self):
        return self._spec

    # a setter function
    @spec.setter
    def spec(self, spec):
        self._spec = spec

    @property
    def env(self):
        return self._env

    # a setter function
    @env.setter
    def env(self, env):
        self._env = env

    @staticmethod
    def check_pinniped_installed():
        """
        static method to check pinniped is installed or not with the help of tanzu commands
        """
        sub_command = ["grep", AppName.PINNIPED]
        cmd = TanzuCommands.INSTALLED_LIST_PACKAGE.split(" ")
        command_pinniped = grabPipeOutput(cmd, sub_command)
        if not verifyPodsAreRunning(AppName.PINNIPED, command_pinniped[0], RegexPattern.RECONCILE_SUCCEEDED):
            count_pinniped = 0
            found = False
            command_status_pinniped = grabPipeOutput(cmd, sub_command)
            while (
                not verifyPodsAreRunning(AppName.PINNIPED, command_status_pinniped[0], RegexPattern.RECONCILE_SUCCEEDED)
                and count_pinniped < 20
            ):
                command_status_pinniped = grabPipeOutput(cmd, sub_command)
                if verifyPodsAreRunning(AppName.PINNIPED, command_status_pinniped[0], RegexPattern.RECONCILE_SUCCEEDED):
                    found = True
                    break
                count_pinniped = count_pinniped + 1
                time.sleep(30)
                current_app.logger.info("Waited for  " + str(count_pinniped * 30) + "s, retrying.")
            if not found:
                msg = f"Pinniped is not in RECONCILE SUCCEEDED state on waiting {str(count_pinniped * 30)}"
                current_app.logger.error(msg)
                return msg, HTTPStatus.INTERNAL_SERVER_ERROR
        msg = "Successfully validated Pinniped installation"
        current_app.logger.info(msg)
        return msg, HTTPStatus.OK

    def check_repository_added(self):
        set_cmd = TanzuCommands.CONFIG_SET.format(key="features.package.kctrl-command-tree", value="true")
        runProcess(set_cmd)
        from common.common_utilities import checkAirGappedIsEnabled

        if checkAirGappedIsEnabled(self.env):
            try:
                time.sleep(60)
                status = runShellCommandAndReturnOutputAsList(TanzuCommands.REPOSITORY_LIST)
                if status[1] != 0:
                    msg = f"Failed to run validate repository added command {str(status[0])}"
                    current_app.logger.error(msg)
                    return msg, HTTPStatus.INTERNAL_SERVER_ERROR

                repo_url = self.spec.envSpec.customRepositorySpec.tkgCustomImageRepository
                repo_url = str(repo_url).replace("https://", "").replace("http://", "")
                if repo_url not in str(status[0]):
                    ospath1 = repo_url
                    ospath2 = f"{os.sep}".join(TKG_Package_Details.REPOSITORY_URL.split(os.sep)[2:])
                    url = os.path.join(ospath1, ospath2)
                    repo_add = TanzuCommands.PACKAGE_REPO_ADD.format(
                        repo_name=Repo.NAME, url=url, namespace="tkg-system"
                    )
                    status = runShellCommandAndReturnOutputAsList(repo_add)
                    if status[1] != 0:
                        msg = f"Failed to run command to add repository {str(status[0])}"
                        current_app.logger.error(msg)
                        return msg, HTTPStatus.INTERNAL_SERVER_ERROR
                    time.sleep(60)
                    status = runShellCommandAndReturnOutputAsList(TanzuCommands.REPOSITORY_LIST)
                    if status[1] != 0:
                        msg = f"Failed to run validate repository added command {str(status[0])}"
                        current_app.logger.error(msg)
                        return msg, HTTPStatus.INTERNAL_SERVER_ERROR
                else:
                    current_app.logger.info(repo_url + " is already added")
                msg = f"Successfully  added repository {repo_url}"
                current_app.logger.info(msg)
                return msg, HTTPStatus.OK
            except Exception as e:
                msg = f"Failed to add repository {str(e)}"
                current_app.logger.error(msg)
                return msg, HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            try:
                list_command = TanzuCommands.REPOSITORY_LIST_NAMESPACE.format(namespace=TKG_Package_Details.NAMESPACE)
                status = runShellCommandAndReturnOutputAsList(list_command)
                msg_to_verify = "the server is currently unable to handle the request"
                wait_time = 0
                while status[1] != 0 and msg_to_verify in str(status[0]) and wait_time < 300:
                    current_app.logger.error("Error in validate repository added command " + str(status[0]))
                    current_app.logger.info("Waiting for 30 secs")
                    time.sleep(30)
                    wait_time += 30
                    status = runShellCommandAndReturnOutputAsList(list_command)
                if status[1] != 0:
                    msg = f"Failed to run validate repository added command {str(status[0])}"
                    current_app.logger.error(msg)
                    return RequestApiUtil.send_error(msg), HTTPStatus.INTERNAL_SERVER_ERROR
                if TKG_Package_Details.STANDARD_PACKAGE_URL not in str(status[0]):
                    add_repo = TanzuCommands.PACKAGE_REPO_ADD.format(
                        repo_name=TKG_Package_Details.REPO_NAME,
                        url=TKG_Package_Details.REPOSITORY_URL,
                        namespace=TKG_Package_Details.NAMESPACE,
                    )
                    status = runShellCommandAndReturnOutputAsList(add_repo)
                    if status[1] != 0:
                        msg = f"Failed to run command to add repository {str(status[0])}"
                        current_app.logger.error(msg)
                        return RequestApiUtil.send_error(msg), HTTPStatus.INTERNAL_SERVER_ERROR
                    status = runShellCommandAndReturnOutputAsList(list_command)
                    if status[1] != 0:
                        msg = f"Failed to run validate repository added command {str(status[0])}"
                        current_app.logger.error(msg)
                        return RequestApiUtil.send_error(msg), HTTPStatus.INTERNAL_SERVER_ERROR
                else:
                    current_app.logger.info(TKG_Package_Details.REPOSITORY_URL + " is already added")
                msg = f"Successfully  added repository {TKG_Package_Details.REPOSITORY_URL}"
                current_app.logger.info(msg)
                return RequestApiUtil.send_ok(message=msg), HTTPStatus.OK
            except Exception as e:
                msg = f"Failed to validate tanzu standard repository status {str(e)}"
                current_app.logger.error(msg)
                return RequestApiUtil.send_error(msg), HTTPStatus.INTERNAL_SERVER_ERROR

    @staticmethod
    def delete_config_server(cluster_endpoint):
        """
        list and delete cluster config server
        """
        list_output = runShellCommandAndReturnOutputAsList(TanzuCommands.LIST_CONFIG)
        if list_output[1] != 0:
            return " Failed to use context " + str(list_output[0]), HTTPStatus.INTERNAL_SERVER_ERROR

        if cluster_endpoint in str(list_output[0]):
            delete_config = TanzuCommands.DELETE_CONFIG_SERVER.format(cluster_endpoint=cluster_endpoint)
            delete_output = runShellCommandAndReturnOutputAsList(delete_config)
            if delete_output[1] != 0:
                return " Failed to use  context " + str(delete_output[0]), HTTPStatus.INTERNAL_SERVER_ERROR
            return "Cluster config deleted successfully", HTTPStatus.OK
        else:
            return "Cluster config not added", HTTPStatus.OK

    def deploy_multi_cloud_cluster(
        self,
        cluster_name,
        cluster_plan,
        data_center,
        data_store_path,
        folder_path,
        mgmt_network,
        vsphere_password,
        shared_cluster_resource_pool,
        vsphere_server,
        ssh_key,
        vsphere_user_name,
        machine_count,
        size,
        cluster_type,
    ):
        """
        class generate yaml for dumping yaml and create cluster for TKGm deployment, by using tanzu cluster create
        command
        """

        try:
            if not TanzuUtil.get_cluster_status_on_tanzu(cluster_name, "cluster"):
                kube_version = self.cluster_yaml_util.generate_cluster_yaml(
                    cluster_name,
                    cluster_plan,
                    data_center,
                    data_store_path,
                    folder_path,
                    mgmt_network,
                    vsphere_password,
                    shared_cluster_resource_pool,
                    vsphere_server,
                    ssh_key,
                    vsphere_user_name,
                    machine_count,
                    size,
                    cluster_type,
                )
                if kube_version is None:
                    return None, "kubeVersion Not found"
                current_app.logger.info("Deploying " + cluster_name + " cluster")
                os.putenv("DEPLOY_TKG_ON_VSPHERE7", "true")
                feature = "features.cluster.auto-apply-generated-clusterclass-based-configuration"
                config_set_command = TanzuCommands.CONFIG_SET.format(key=feature, value="true")
                runProcess(config_set_command)
                yaml_path = os.path.join(Paths.CLUSTER_PATH, cluster_name, cluster_name + ".yaml")
                cluster_created_command = TanzuCommands.CLUSTER_CREATE.format(
                    file_path=yaml_path, kube_version=kube_version
                )
                runProcess(cluster_created_command)
                return "SUCCESS", 200
            else:
                return "SUCCESS", 200
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_cluster_status_on_tanzu(management_cluster, type_of_cluster):
        """
        check whether cluster(workload/management) is in running state and returns True if found in running state.
        """
        try:
            if type_of_cluster == "management":
                get_command = TanzuCommands.MANAGEMENT_CLUSTER_GET
            else:
                get_command = TanzuCommands.CLUSTER_GET
            o = runShellCommandAndReturnOutput(get_command)
            if o[1] == 0:
                try:
                    if management_cluster in o[0] and "running" in o[0]:
                        return True
                    else:
                        return False
                except Exception:
                    return False
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def get_management_cluster():
        """
        fetch management cluster name with running status, return None if not found
        """
        try:
            command = TanzuCommands.CLUSTER_LIST_WITH_MANAGEMENT
            status = runShellCommandAndReturnOutput(command)
            mcs = status[0].split("\n")
            for mc in mcs:
                if "management" in str(mc) and "running" in str(mc):
                    return str(mc).split(" ")[2].strip()
            return None
        except Exception:
            return None

    @staticmethod
    def get_version_of_package(package_name):
        """
        get latest version of the package with given package name, latest version with latest release date
        """
        list_h = []
        get_package = TanzuCommands.GET_AVAILABLE_PACKAGE.format(package_name=package_name)
        ss = runShellCommandAndReturnOutputAsList(get_package)
        release_dates = []
        for s in ss[0]:
            if "Retrieving package versions for " + package_name + "..." not in s:
                if "Waited for" not in s:
                    for nn in s.split("\n"):
                        if nn:
                            if "RELEASED-AT" not in nn.split()[3]:
                                release_date = datetime.fromisoformat(" ".join(nn.split()[3:5])).date()
                                release_dates.append(release_date)
                                list_h.append(nn)
        if len(list_h) == 0:
            current_app.logger.error("Failed to run get version list")
            return None

        version = None
        max_release_date = str(max(release_dates))
        version_list = []
        for li in list_h:
            if max_release_date in li:
                version = li.split()[2]
                version_list.append(version)
                version = str(max(version_list))
        if version is None or not version:
            current_app.logger.error("Failed to get version string")
            return None
        return version

    def switch_to_context(self, cluster_name):
        """
        switch to cluster context with given name, in case of TKGs use namespace
        """

        from common.util.tkgs_util import TkgsUtil

        if self.env == Env.VSPHERE and TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
            name_space = (
                self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereWorkloadClusterSpec
            )
            commands_shared = TanzuCommands.GET_CLUSTER_CONTEXT.format(cluster_name=cluster_name, name_space=name_space)
        else:
            commands_shared = TanzuCommands.GET_CLUSTER_CONTEXT.format(cluster_name=cluster_name)
        command = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if command is None:
            msg = f"Failed get admin cluster context of cluster {cluster_name}"
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        list_command = str(command)
        status = runShellCommandAndReturnOutputAsList(list_command)
        if status[1] != 0:
            msg = f"Failed to switch to {cluster_name} cluster context {str(status[0])}"
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        msg = f"Switched to {cluster_name} context"
        current_app.logger.info(msg)
        return RequestApiUtil.send_ok(message=msg), HTTPStatus.OK

    @staticmethod
    def switch_to_management_context(cluster_name):
        """
        static method for switching context to management cluster context
        """
        commands_shared = TanzuCommands.GET_MANAGEMENT_CLUSTER_CONTEXT.format(cluster_name=cluster_name)
        kube_context = grabKubectlCommand(commands_shared, RegexPattern.SWITCH_CONTEXT_KUBECTL)
        if kube_context is None:
            msg = f"Failed get admin cluster context of cluster {cluster_name}"
            current_app.logger.error(msg)
            return msg, HTTPStatus.INTERNAL_SERVER_ERROR
        list_of_switch_context = str(kube_context)
        status = runShellCommandAndReturnOutputAsList(list_of_switch_context)
        if status[1] != 0:
            msg = f"Failed to switch to {cluster_name} cluster context {str(status[0])}"
            current_app.logger.error(msg)
            return msg, HTTPStatus.INTERNAL_SERVER_ERROR
        msg = f"Switched to {cluster_name} context"
        current_app.logger.info(msg)
        return msg, HTTPStatus.OK

    @staticmethod
    def verify_cluster(cluster_name):
        """
        verify the cluster from list of tanzu clusters list
        """
        list_command = TanzuCommands.CLUSTER_LIST_WITH_MANAGEMENT
        command_status = runShellCommandAndReturnOutputAsList(list_command)
        if not verifyPodsAreRunning(cluster_name, command_status[0], RegexPattern.running):
            return False
        else:
            return True

    @staticmethod
    def get_cluster_list():
        """
        get list of cluster
        """
        o = runShellCommandAndReturnOutput(TanzuCommands.CLUSTER_LIST)
        return o

    @staticmethod
    def delete_cluster(cluster_name):
        """
        delete cluster with the specified cluster name
        """
        cmd = TanzuCommands.CLUSTER_DELETE.format(cluster_name=cluster_name)
        o = runShellCommandAndReturnOutput(cmd)
        return o

    @staticmethod
    def get_management_cluster_output():
        """
        get management cluster
        """
        o = runShellCommandAndReturnOutput(TanzuCommands.MANAGEMENT_CLUSTER_GET)
        return o

    @staticmethod
    def delete_management_cluster():
        """
        delete management cluster
        """
        o = runShellCommandAndReturnOutput(TanzuCommands.MANAGEMENT_CLUSTER_DELETE)
        return o

    @staticmethod
    def get_installed_package_json():
        """
        get list of installed package and package output as json
        """
        o = runShellCommandAndReturnOutputAsJson(TanzuCommands.INSTALLED_LIST_PACKAGE_JSON)
        return o

    @staticmethod
    def delete_installed_package(package_name, name_space):
        """
        delete package by providing package name and namespace
        """
        cmd = TanzuCommands.DELETE_PACKAGE.format(package_name=package_name, name_space=name_space)
        o = runShellCommandAndReturnOutputAsList(cmd)
        return o
