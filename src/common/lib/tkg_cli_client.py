import json
import logging

from common.constants.constants import TKGCommands, KubectlCommands, Constants
from common.util.base_cmd_helper import BaseCmdHelper
from retry import retry

# TODO: Replace with existing logger implementation
logger = logging.getLogger()


class TkgCliClient:
    def __init__(self, cmd_runner: BaseCmdHelper):
        self.cmd_runner = cmd_runner

    def get_clusters(self):
        logger.info("Getting list of Tanzu clusters")
        exit_code, output = self.cmd_runner.run_cmd_output(TKGCommands.LIST_CLUSTERS_JSON)
        return json.loads(output)

    def get_all_clusters(self):
        logger.info("Getting list of Tanzu clusters(including management cluster)")
        exit_code, output = self.cmd_runner.run_cmd_output(TKGCommands.LIST_ALL_CLUSTERS_JSON)
        return json.loads(output)

    def get_cluster_details(self, cluster_name):
        logger.info(f'Getting details of cluster: {cluster_name}')
        return [cluster for cluster in self.get_all_clusters() if cluster['name'] == cluster_name]

    def check_cluster_exists(self, cluster_name, expected_status='running'):
        logger.info(f'Checking if cluster: {cluster_name} exists in {expected_status} state')
        cluster_list = [cluster for cluster in self.get_all_clusters() if cluster['name'] == cluster_name and
                        cluster['status'] == expected_status]
        return any(cluster_list)

    @retry(ValueError, tries=5, delay=20, logger=logger)
    def retriable_check_cluster_exists(self, cluster_name):
        if not self.check_cluster_exists(cluster_name):
            raise ValueError(f"Waiting for Cluster {cluster_name} to be in running state.")
        return True

    def deploy_cluster(self, config_file_path, verbosity='-v 9'):
        logger.info("Deploying Tanzu kubernetes cluster")
        cluster_deploy = TKGCommands.CLUSTER_DEPLOY.format(file_path=config_file_path, verbose=verbosity)
        return self.cmd_runner.run_cmd(cluster_deploy)

    def get_admin_context(self, cluster_name):
        logger.info(f'Getting admin context for cluster: {cluster_name}')
        get_cluster_context = TKGCommands.GET_ADMIN_CONTEXT.format(cluster=cluster_name)
        return self.cmd_runner.run_cmd(get_cluster_context)

    def list_available_packages(self, json_format=True):
        logger.info("Getting all available packages")
        if json_format:
            cmd = TKGCommands.LIST_AVAILABLE_PACKAGES.format(options=KubectlCommands.OUTPUT_JSON)
            exit_code, output = self.cmd_runner.run_cmd_output(cmd)
            return json.loads(output)
        else:
            cmd = TKGCommands.LIST_AVAILABLE_PACKAGES.format(options="")
            return self.cmd_runner.run_cmd(cmd)

    def list_installed_packages(self, json_format=True):
        logger.info("Getting all installed packages")
        if json_format:
            cmd = TKGCommands.LIST_INSTALLED_PACKAGES.format(options=KubectlCommands.OUTPUT_JSON)
            exit_code, output = self.cmd_runner.run_cmd_output(cmd)
            return json.loads(output)
        else:
            cmd = TKGCommands.LIST_INSTALLED_PACKAGES.format(options="")
            return self.cmd_runner.run_cmd(cmd)

    def install_package(self, name, package, namespace, version, options=""):
        logger.info(f"Installing package {package} (ver: {version}) in namespace {namespace}")
        cmd = TKGCommands.INSTALL_PACKAGE.format(name=name, pkgName=package, namespace=namespace, version=version,
                                                 options=options)
        return self.cmd_runner.run_cmd(cmd)

    def get_installed_package_details(self, name, namespace, json_format=True):
        logger.info("Get installed package details")
        if json_format:
            cmd = TKGCommands.GET_PACKAGE_DETAILS.format(name=name, namespace=namespace,
                                                         options=KubectlCommands.OUTPUT_JSON)
            exit_code, output = self.cmd_runner.run_cmd_output(cmd)
            return json.loads(output)
        else:
            cmd = TKGCommands.GET_PACKAGE_DETAILS.format(name=name, namespace=namespace, options="")
            return self.cmd_runner.run_cmd(cmd)

    def check_package_installed(self, name, namespace, version):
        logger.info("Check if package is installed in given namespace and is in specified version")
        packages = self.list_installed_packages()
        for package in packages:
            if package['name'] == name and package['namespace'] == namespace and package['package-version'] == version:
                if package['status'] == Constants.RECONCILE_SUCCESS:
                    logger.info(f"Found installed package: {package}")
                    return True
        return False

    def check_package_available(self, name, display_name):
        logger.info(f"Checking if package {name} available.")
        packages = self.list_available_packages()
        for package in packages:
            if package['name'] == name and package['display-name'] == display_name:
                logger.info(f"Found available package: {package}")
                return True
        return False

    def get_available_package_details(self, package, json_format=True):
        logger.info("Get available package details")
        if json_format:
            cmd = TKGCommands.GET_AVAILABLE_PACKAGE_DETAILS.format(pkgName=package, options=KubectlCommands.OUTPUT_JSON)
            exit_code, output = self.cmd_runner.run_cmd_output(cmd)
            return json.loads(output)
        else:
            cmd = TKGCommands.GET_AVAILABLE_PACKAGE_DETAILS.format(pkgName=package, options="")
            return self.cmd_runner.run_cmd(cmd)

    def login(self, cluster_name):
        logger.info("Logging into management cluster")
        return self.cmd_runner.run_cmd(TKGCommands.TANZU_LOGIN.format(server=cluster_name))

    def management_cluster_upgrade(self, cluster_name, timeout="60m0s", verbose=True):
        logger.info(f"Upgrading management cluster: {cluster_name}")
        cmd_option = TKGCommands.TIMEOUT_OPTION.format(timeout=timeout) if timeout else ""
        cmd_option += " -v 9" if verbose else ""
        return self.cmd_runner.run_cmd(TKGCommands.MGMT_CLUSTER_UPGRADE.format(options=cmd_option))

    def tanzu_cluster_upgrade(self, cluster_name, timeout="60m0s", verbose=True):
        logger.info(f"Upgrading tanzu kubernetes cluster: {cluster_name}")
        cmd_option = TKGCommands.TIMEOUT_OPTION.format(timeout=timeout) if timeout else ""
        cmd_option += " -v 9" if verbose else ""
        return self.cmd_runner.run_cmd(
            TKGCommands.CLUSTER_UPGRADE.format(cluster_name=cluster_name, options=cmd_option))
