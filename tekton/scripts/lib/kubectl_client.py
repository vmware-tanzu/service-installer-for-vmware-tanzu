#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import time
from pathlib import Path

import yaml
from constants.constants import KubectlCommands, Paths, RepaveTkgCommands
from util.cmd_helper import CmdHelper
from util.logger_helper import LoggerHelper, log, log_debug
from util.ssh_helper import SshHelper
from util.cmd_runner import RunCmd

logger = LoggerHelper.get_logger(Path(__file__).stem)


class KubectlClient:
    def __init__(self):
        self.rcmd = RunCmd()

    def set_cluster_context(self, cluster_name):
        logger.info(f"Setting kubectl context to {cluster_name} cluster")
        set_kubectl_context = KubectlCommands.SET_KUBECTL_CONTEXT.format(cluster=cluster_name)
        return self.rcmd.run_cmd_only(set_kubectl_context)

    def get_all_pods(self):
        logger.info("Listing all pods...")
        exit_code, output = self.rcmd.run_cmd_output(KubectlCommands.GET_ALL_PODS)
        return output

    def get_vsphere_template_json(self, worker_name):
        logger.info(f"Getting machine template for {worker_name}")
        # kubectl get VsphereMachineTemplate tekton-shared-cluster-worker -o json
        get_template = KubectlCommands.GET_VSPHERE_TEMPLATE.format(workername=worker_name)
        return self.rcmd.run_cmd_output(get_template)

    def get_machinedeployment_json(self, deployment_name):
        logger.info(f"Getting machine deployment for {deployment_name}")
        # k get machinedeployment  tekton-shared-cluster-md-0 -o json
        get_template = KubectlCommands.GET_MACHINE_DEPLOYMENT.format(deployment_name=
                                                                     deployment_name)
        return self.rcmd.run_cmd_output(get_template)

    def get_all_namespaces(self, options=""):
        logger.info("Listing all namespaces...")
        exit_code, output = self.rcmd.run_cmd_output(KubectlCommands.LIST_NAMESPACES.format(options=options))
        return output

    def list_secrets(self, namespace: str, options=""):
        logger.info("Listing all secrets...")
        exit_code, output = self.rcmd.run_cmd_output(
            KubectlCommands.LIST_SECRETS.format(namespace=namespace, options=options)
        )
        return output

    def install_cert_manager(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)

        deploy_cert_mgr = f"""
                cd {work_dir};
                {KubectlCommands.APPLY.format(config_file=config_file_path)}
            """
        return self.rcmd.run_cmd_only(deploy_cert_mgr)

    def install_tmc_extensions_mgr(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)

        install_extensions_mgr = f"""
                    cd {work_dir};
                    {KubectlCommands.APPLY.format(config_file=config_file_path)}
                """
        return self.ssh.run_cmd_only(install_extensions_mgr)

    def create_namespace(self, work_dir, config_file_path):
        create_namespace = f"""
                    cd {work_dir};
                    {KubectlCommands.APPLY.format(config_file=config_file_path)}
                """
        return self.rcmd.run_cmd_only(create_namespace)

    def create_secret(self, secret_name, work_dir, config_file_path, namespace):
        cmd = f"""
                cd {work_dir};
                {KubectlCommands.CREATE_SECRET.format(name=secret_name, config_file=config_file_path, namespace=namespace)}
                """
        return self.rcmd.run_cmd_only(cmd)

    @log("Checking if namespace exists")
    def check_namespace_exists(self, namespace):
        namespaces = self.get_all_namespaces(KubectlCommands.FILTER_NAME)
        return f"namespace/{namespace}" in namespaces.split("\r\n")

    @log("Checking if secret exists")
    def check_secret_exists(self, secret_name, namespace):
        secrets = self.list_secrets(namespace, KubectlCommands.FILTER_NAME)
        return f"secret/{secret_name}" in secrets.split("\r\n")

    @log("Checking if app exists")
    def check_app_exists(self, app_name, namespace):
        apps = self.list_apps(namespace, KubectlCommands.FILTER_NAME)
        return f"app.kappctrl.k14s.io/{app_name}" in apps.split("\r\n")

    def list_apps(self, namespace, options=""):
        logger.info(f"Listing all apps in namespace: {namespace}...")
        exit_code, output = self.rcmd.run_cmd_output(
            KubectlCommands.LIST_APPS.format(namespace=namespace, options=options)
        )
        return output

    def get_app_details(self, app_name, namespace, options):
        contour_status = KubectlCommands.GET_APP_DETAILS.format(app_name=app_name, namespace=namespace, options=options)
        exit_code, output = self.rcmd.run_cmd_output(contour_status)
        return output

    def deploy_extension(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)
        deploy_extension = f"""
                            cd {work_dir};
                            {KubectlCommands.APPLY.format(config_file=config_file_path)}
                        """
        return self.ssh.run_cmd_only(deploy_extension)

    def add_services_label(self, cluster_name, mgmt_cluster_name):
        self.set_cluster_context(mgmt_cluster_name)

        logger.info(f"Adding shared services label to cluster: {cluster_name}")
        self.rcmd.run_cmd_only(KubectlCommands.ADD_SERVICES_LABEL.format(cluster=cluster_name))

    def list_service_accounts(self, namespace, options=""):
        logger.info(f"Listing all service accounts in namespace: {namespace}...")
        exit_code, output = self.rcmd.run_cmd_output(
            KubectlCommands.LIST_SERVICE_ACCOUNTS.format(namespace=namespace, options=options)
        )
        return output

    @log("Checking if service account exists")
    def check_sa_exists(self, sa_name, namespace):
        apps = self.list_service_accounts(namespace, KubectlCommands.FILTER_NAME)
        return f"serviceaccount/{sa_name}" in apps.split("\r\n")

    def get_harbor_cert(self, namespace, options=""):
        exit_code, output = self.rcmd.run_cmd_output(
            KubectlCommands.GET_HARBOR_CERT.format(namespace=namespace, options=options)
        )
        return output

    def delete_extension(self, cluster_name, extension_name, namespace):
        self.set_cluster_context(cluster_name=cluster_name)
        logger.info(f"Deleting extension {extension_name} in namespace {namespace}")
        return self.rcmd.run_cmd_only(KubectlCommands.DELETE_EXTENSION.format(app_name=extension_name, namespace=namespace))

    def delete_tmc_extensions_mgr(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)

        cmd = f"""
                    cd {work_dir};
                    {KubectlCommands.DELETE.format(config_file=config_file_path)}
                """
        return self.rcmd.run_cmd_only(cmd)

    def install_kapp_controller(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)

        cmd = f"""
                    cd {work_dir};
                    {KubectlCommands.APPLY.format(config_file=config_file_path)}
            """
        return self.rcmd.run_cmd_only(cmd)

    def get_secret_details(self, secret_name, namespace, work_dir, options=""):
        cmd = f"""
                cd {work_dir};
                {KubectlCommands.GET_SECRET_DETAILS.format(name=secret_name, namespace=namespace, options=options)}
            """
        output = self.rcmd.run_cmd_only(cmd)
        return output

    def update_secret(self, secret_name, work_dir, config_file_path, namespace):
        cmd = f"""
                cd {work_dir};
                {KubectlCommands.UPDATE_SECRET.format(name=secret_name, config_file=config_file_path, namespace=namespace)}
                """
        return self.ssh.run_cmd_only(cmd)

    def get_oldest_node(self):
        logger.info("Worker Nodes: ")
        self.rcmd.run_cmd_only(RepaveTkgCommands.GET_NODES_WITH_TIMESTAMP)
        return self.rcmd.run_cmd_output(RepaveTkgCommands.GET_OLDEST_WORKER_NODE)[1].strip()

    def add_node(self, cluster_name, control_plane_node_count, worker_node_count):
        self.rcmd.run_cmd_only(
            RepaveTkgCommands.ADD_NODES.format(
                cluster_name=cluster_name,
                control_plane_node_count=control_plane_node_count,
                worker_node_count=worker_node_count,
            )
        )

    def drain_pods_from_node(self, node_name):
        logger.info(f"Drain pods from node: {node_name}")
        self.rcmd.run_cmd_only(RepaveTkgCommands.DRAIN_PODS.format(node_name=node_name))

    def delete_node(self, node_name):
        logger.info(f"Delete node: {node_name}")
        self.rcmd.run_cmd_only(RepaveTkgCommands.DELETE_NODE.format(node_name=node_name))

    def get_node_count(self) -> int:
        output = CmdHelper.escape_ansi(self.rcmd.run_cmd_output(RepaveTkgCommands.NODE_COUNT)[1].strip())
        return int(output)

    def wait_for_ready_nodes(self, initial_count: int, retry: int):
        r = retry
        while initial_count != self.get_ready_node_count() and r > 0:
            logger.warn("Waiting for node to be up...")
            time.sleep(30)
            r -= 1
        if initial_count != self.get_ready_node_count():
            raise ValueError(f"Nodes are not in correct count after {retry} retries")

    def get_ready_node_count(self) -> int:
        node_status_str = self.rcmd.run_cmd_output(RepaveTkgCommands.NODE_STATUS)[1]
        logger.debug(f"Node Status: {node_status_str}")
        node_status = yaml.safe_load(node_status_str)
        return len([node for node in node_status if bool(node["status"])])
