#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import re
from pathlib import Path

from constants.constants import Constants, KubectlCommands, Paths, TKGCommands
from lib.kubectl_client import KubectlClient
from lib.tkg_cli_client import TkgCliClient
from lib.tmc_cli_client import TmcCliClient
from model.spec import MasterSpec
from model.status import HealthEnum, State
from retry import retry
from util.file_helper import FileHelper
from util.git_helper import Git
from util.logger_helper import LoggerHelper, log, log_debug
from util.cmd_runner import RunCmd
from util.tanzu_utils import TanzuUtils

logger = LoggerHelper.get_logger(Path(__file__).stem)

DELAY = int(Constants.RECONCILE_WAIT_INTERVAL)
TIMEOUT = int(Constants.RECONCILE_WAIT_TIMEOUT)
RETRY_COUNT = TIMEOUT // DELAY


class ClusterCommonWorkflow:
    def __init__(self):
        self.runcmd = RunCmd()
        self.tkg_cli_client = TkgCliClient()
        self.kubectl_client = KubectlClient()
        self.tmc_cli_client = TmcCliClient()

    @log("Commit kubeconfig")
    def commit_kubeconfig(self, root_dir, cluster_type):
        TanzuUtils(root_dir).pull_config()
        Git.add_all_and_commit(
            Paths.KUBECONFIG_REPO_PATH.format(root_dir=root_dir), f"Successful {cluster_type} cluster deployment"
        )

    @log("Deploying Tanzu kubernetes cluster")
    def deploy_tanzu_k8s_cluster(self, cluster_to_deploy: str, file_path: str):
        if self.tkg_cli_client.check_cluster_exists(cluster_name=cluster_to_deploy):
            logger.info(f'Cluster {cluster_to_deploy} already exists')
        else:
            logger.info(f'Deploying cluster: {cluster_to_deploy}')
            self.tkg_cli_client.deploy_cluster(config_file_path=file_path)

            if self.tkg_cli_client.retriable_check_cluster_exists(cluster_name=cluster_to_deploy):
                logger.info(f'Cluster {cluster_to_deploy} created successfully')
            else:
                logger.error(f"Cluster {cluster_to_deploy} not created or not in running state")
                raise Exception(f"Cluster {cluster_to_deploy} not created or not in running state")

        self.tkg_cli_client.get_admin_context(cluster_to_deploy)
        self.kubectl_client.set_cluster_context(cluster_name=cluster_to_deploy)

    @log("Installing TMC extensions Manager")
    def install_tmc_extensions_mgr(self, cluster_to_deploy, work_dir):
        if not self.kubectl_client.check_namespace_exists(namespace=Constants.VMWARE_SYSTEM_TMC):
            logger.info(f"Install TMC extensions Manager on cluster: {cluster_to_deploy}")
            self.kubectl_client.install_tmc_extensions_mgr(cluster_to_deploy, work_dir,
                                                           Paths.TMC_EXTENSION_MGR_CONFIG)
            logger.info('TMC extensions Manager installation complete!')
        else:
            logger.info(
                f"Namespace {Constants.VMWARE_SYSTEM_TMC} exists. Skipping TMC extensions manager installation.")

    @log("Installing certificate manager")
    def install_cert_manager(self, cluster_to_deploy, work_dir):
        self.kubectl_client.install_cert_manager(cluster_name=cluster_to_deploy, work_dir=work_dir,
                                                 config_file_path=Paths.CERT_MANAGER_CONFIG)

        logger.debug(self.kubectl_client.get_all_pods())
        logger.info('Cert manager installation complete!')

    @log("Check if app has reconciled successfully")
    @retry(ValueError, delay=DELAY, tries=RETRY_COUNT, logger=logger)
    def check_app_reconciled(self, app_name, namespace, ignore_failed=False):
        filter_template = KubectlCommands.FILTER_JSONPATH.format(
            template="\"{@['metadata.name', 'status.friendlyDescription']}\"")

        app_status = self.kubectl_client.get_app_details(app_name=app_name,
                                                         namespace=namespace,
                                                         options=filter_template)

        if f'{app_name} {Constants.RECONCILE_SUCCESS}' == app_status:
            return True
        elif f'{app_name} {Constants.RECONCILE_FAILED}' in app_status:
            if ignore_failed:
                return False
            raise Exception(f"Failed to reconcile extension: {app_name}")
        else:
            raise ValueError(f"Waiting for {app_name} to reconcile. Current state: {app_status}")

    @log("Check if package has reconciled successfully")
    @retry(ValueError, delay=DELAY, tries=RETRY_COUNT, logger=logger)
    def check_package_reconciled(self, name, namespace, ignore_failed=False):
        package_status = self.tkg_cli_client.get_installed_package_details(name=name, namespace=namespace)[0]['status']

        if Constants.RECONCILE_SUCCESS == package_status:
            logger.info("Package {name} reconciled successfully.")
            return True
        elif Constants.RECONCILE_FAILED in package_status:
            if ignore_failed:
                return False
            raise Exception(f"Failed to reconcile package: {name}")
        else:
            raise ValueError(f"Waiting for {name} to reconcile. Current state: {package_status}")

    @log_debug
    def create_namespace_for_extension(self, namespace, sa_name, config_file, extension_name, work_dir):
        if not self.kubectl_client.check_namespace_exists(namespace=namespace):
            logger.info(f'Creating namespace for {extension_name} Service: {namespace}')
            self.kubectl_client.create_namespace(work_dir=work_dir, config_file_path=config_file)

            logger.info('Check if namespace created')
            if not self.kubectl_client.check_namespace_exists(namespace=namespace):
                err_msg = f'{namespace} namespace not found'
                logger.error(err_msg)
                raise Exception(err_msg)
            else:
                logger.info(f'Namespace {namespace} created.')
        elif not self.kubectl_client.check_sa_exists(sa_name=sa_name, namespace=namespace):
            logger.info(f'Adding service accounts and rbac roles for {extension_name} Service: {sa_name}')
            self.kubectl_client.create_namespace(work_dir=work_dir, config_file_path=config_file)

            logger.info('Check if service account created')
            if not self.kubectl_client.check_sa_exists(sa_name=sa_name, namespace=namespace):
                err_msg = f'{sa_name} service account not found'
                logger.error(err_msg)
                raise Exception(err_msg)
            else:
                logger.info(f'Service account {sa_name} created.')
        else:
            logger.info(f'Namespace {namespace} and service account {sa_name} already exists. Skip creation.')

    @log_debug
    def create_secret_for_extension(self, secret_name, namespace, config_file, work_dir):
        if not self.kubectl_client.check_secret_exists(secret_name=secret_name, namespace=namespace):
            logger.info(f'Creating secret {secret_name}')
            self.kubectl_client.create_secret(work_dir=work_dir, secret_name=secret_name,
                                              config_file_path=config_file,
                                              namespace=namespace)

            logger.info('Check if secret created')
            if not self.kubectl_client.check_secret_exists(secret_name=secret_name,
                                                           namespace=namespace):
                err_msg = f'{secret_name} secret not found'
                logger.error(err_msg)
                raise Exception(err_msg)
            else:
                logger.info(f'Secret {secret_name} created.')
        else:
            logger.info(f'Secret {secret_name} already exists. Skip creation.')

    @log_debug
    def reconcile_extension(self, cluster_to_deploy, app_name, namespace, work_dir, config_file):
        try:
            if not (self.kubectl_client.check_app_exists(app_name=app_name, namespace=namespace) and
                    self.check_app_reconciled(app_name=app_name, namespace=namespace, ignore_failed=True)):
                logger.info(f'Deploying {app_name} extension')
                self.kubectl_client.deploy_extension(cluster_name=cluster_to_deploy,
                                                     work_dir=work_dir,
                                                     config_file_path=config_file)

                logger.info(f'Check status of {app_name} service')

                self.check_app_reconciled(app_name=app_name, namespace=namespace)
                logger.info(f"App {app_name} reconciled successfully!")
            else:
                logger.info(f"App {app_name} already exists! Skip creation.")
        except ValueError:
            err_msg = f'Timed out waiting for {app_name} to be in "{Constants.RECONCILE_SUCCESS}" state ' \
                      f'after {TIMEOUT} seconds.'
            logger.error(err_msg)
            extension_status = self.kubectl_client.get_app_details(app_name=app_name,
                                                                   namespace=namespace,
                                                                   options=KubectlCommands.OUTPUT_YAML)
            logger.debug(extension_status)
            raise Exception(err_msg)

    def copy_config_file(self, work_dir, source, destination):
        copy_config = f'''
                                cd {work_dir};
                                cp {source} {destination}
                            '''
        # self.ssh.run_cmd(copy_config)
        self.runcmd.run_cmd_only(copy_config)

    @log("Deleting TMC extensions Manager")
    def delete_tmc_extensions_mgr(self, cluster_name, work_dir):
        if self.kubectl_client.check_namespace_exists(namespace=Constants.VMWARE_SYSTEM_TMC):
            logger.info(f"Delete TMC extensions Manager on cluster: {cluster_name}")
            self.kubectl_client.delete_tmc_extensions_mgr(cluster_name, work_dir,
                                                          Paths.TMC_EXTENSION_MGR_CONFIG)
            logger.info('TMC extensions Manager deletion complete!')
        else:
            logger.info(
                f"Namespace {Constants.VMWARE_SYSTEM_TMC} does not exist. "
                f"TMC extensions Manager already deleted isn't installed.")

    @log("Installing kapp controller")
    def install_kapp_controller(self, cluster_name, work_dir):
        self.kubectl_client.install_kapp_controller(cluster_name=cluster_name, work_dir=work_dir,
                                                    config_file_path=Paths.KAPP_CONTROLLER_CONFIG)

        logger.debug(self.kubectl_client.get_all_pods())
        logger.info('kapp controller installation complete!')

    @log_debug
    def update_secret_for_extension(self, secret_name, namespace, config_file, work_dir):
        logger.info(f'Updating secret {secret_name}')
        self.kubectl_client.update_secret(work_dir=work_dir, secret_name=secret_name,
                                          config_file_path=config_file,
                                          namespace=namespace)

        logger.info('Check if secret updated')
        if not self.kubectl_client.check_secret_exists(secret_name=secret_name,
                                                       namespace=namespace):
            err_msg = f'{secret_name} secret not found'
            logger.error(err_msg)
            raise Exception(err_msg)
        else:
            logger.info(f'Secret {secret_name} updated.')

    @log("Deleting extension")
    def delete_extension(self, cluster_name, extension_name, namespace):
        self.kubectl_client.delete_extension(cluster_name=cluster_name, extension_name=extension_name,
                                             namespace=namespace)

        # TODO: Check if extension deleted

    def install_package(self, cluster_name, package, namespace, name, version, values=None):
        self.kubectl_client.set_cluster_context(cluster_name=cluster_name)
        options = "" if self.kubectl_client.check_namespace_exists(namespace=namespace) else "--create-namespace "
        options += "" if not values else f"--values-file {values}"
        try:
            if not (self.tkg_cli_client.check_package_installed(name=name, namespace=namespace, version=version) and
                    self.check_package_reconciled(name=name, namespace=namespace, ignore_failed=False)):
                logger.info(f"Installing {name} package")
                self.tkg_cli_client.install_package(name=name, namespace=namespace, version=version, package=package,
                                                    options=options)

                logger.info(f"Check if package {name} reconciled")
                self.check_package_reconciled(name=name, namespace=namespace)

                logger.info(f'Check status of {name} service')
                self.check_app_reconciled(app_name=name, namespace=namespace)
                logger.info(f"App {name} reconciled successfully!")
            else:
                logger.info(f"Package {name} already installed. Skip installation.")
        except ValueError:
            err_msg = f'Timed out waiting for {name} to be in "{Constants.RECONCILE_SUCCESS}" state ' \
                      f'after {TIMEOUT} seconds.'
            logger.error(err_msg)
            app_status = self.kubectl_client.get_app_details(app_name=name,
                                                             namespace=namespace,
                                                             options=KubectlCommands.OUTPUT_YAML)
            logger.debug(app_status)
            raise Exception(err_msg)

    def attach_cluster_to_tmc(self, cluster_name, cluster_group, api_token):
        self.kubectl_client.set_cluster_context(cluster_name=cluster_name)
        logger.info("Logging in to Tmc...")
        self.tmc_cli_client.tmc_login(api_token=api_token)
        logger.info("Attaching cluster to Tmc.")
        file = "kubeconfig_cluster.yaml"
        self.tmc_cli_client.get_kubeconfig(cluster_name=cluster_name, file=file)
        self.tmc_cli_client.attach_cluster(cluster_name=cluster_name, cluster_group=cluster_group)

    def get_available_package_version(self, cluster_name, package, name):
        self.kubectl_client.set_cluster_context(cluster_name=cluster_name)
        if not self.tkg_cli_client.check_package_available(name=package,
                                                           display_name=name):
            msg = f"Package {Constants.CERT_MGR_PACKAGE} not available in specified cluster {cluster_name}"
            logger.error(msg)
            raise Exception(msg)
        logger.info(f"Getting available version for package {package}")
        return self.tkg_cli_client.get_available_package_details(package=package)[0]['version']

    def generate_spec_template(self, name, package, version, template_path, on_docker):
        filter_template = "-o jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}'"
        cmd = f"""
            image_url=$(kubectl -n tanzu-package-repo-global get packages {package}.{version} {filter_template})
            imgpkg pull -b $image_url -o /tmp/{name}-package-{version}
            cp /tmp/{name}-package-{version}/config/values.yaml {template_path}
            """
        if package == Constants.HARBOR_PACKAGE:
            cmd += f"""
            bash /tmp/{name}-package-{version}/config/scripts/generate-passwords.sh {template_path}
            """
        # Replace $ sign with escaped $ sign for running on container.
        if on_docker:
            cmd = re.sub(r'\$', r'\$', cmd)
        # return self.ssh.run_cmd(cmd)
        return self.runcmd.run_cmd_only(cmd)

    @log("check health of cluster and update state")
    def check_health(self, root_dir, spec: MasterSpec):
        state_file_path = os.path.join(root_dir, Paths.STATE_PATH)
        if not os.path.exists(state_file_path):
            logger.error("state file missing")
            return
        state: State = FileHelper.load_state(state_file_path)

        if not (
            state.mgmt.deployed
            and state.shared_services.deployed
            and len(state.workload_clusters) == len(spec.tkg.workloadClusters)
        ):
            logger.info("clusters are not deployed, skipping health checks")
            return

        cluster_status = self.tkg_cli_client.get_all_clusters()
        state.mgmt.health = self.check_cluster_health(cluster_status, spec.tkg.management.cluster.name)
        state.shared_services.health = self.check_cluster_health(cluster_status, spec.tkg.sharedService.cluster.name)
        if len(state.workload_clusters) == len(spec.tkg.workloadClusters):
            for i, wl in enumerate(spec.tkg.workloadClusters):
                state.workload_clusters[i].health = self.check_cluster_health(cluster_status, wl.cluster.name)
        # todo: if wl cluster is missing or new one is added
        # add more health checks for version
        logger.info("%s", FileHelper.yaml_from_model(state))
        self._update_state(root_dir, state)

    @staticmethod
    def check_cluster_health(cluster_status, cluster_name):
        return (
            HealthEnum.UP
            if next(x["status"] for x in cluster_status if x["name"] == cluster_name) == "running"
            else HealthEnum.DOWN
        )

    @log("Updating state file")
    def _update_state(self, root_dir, state):
        state_file_path = os.path.join(root_dir, Paths.STATE_PATH)
        FileHelper.dump_state(state, state_file_path)
        Git.add_all_and_commit(os.path.dirname(state_file_path), "Updated cluster health")

    @log("Upgrading tanzu kubernetes cluster")
    def upgrade_k8s_cluster_1_4_x(self, cluster_name, mgmt_cluster_name):
        self.tkg_cli_client.login(cluster_name=mgmt_cluster_name)
        self.tkg_cli_client.tanzu_cluster_upgrade(cluster_name=cluster_name)
        if not self.tkg_cli_client.retriable_check_cluster_exists(cluster_name=cluster_name):
            msg = f"Cluster: {cluster_name} not in running state"
            logger.error(msg)
            raise Exception(msg)

    @log("Upgrading tanzu kubernetes cluster")
    def upgrade_k8s_cluster_1_3_x(self, cluster_name, mgmt_cluster_name, timeout="60m0s", verbose=True):
        logger.info(f"Login with cluster context and cleanup for {cluster_name}")
        self.runcmd.run_cmd_only(
            TKGCommands.CLUSTER_UPGRADE_CLEANUP.format(
                cluster_name=cluster_name,
                mgmt_cluster_name=mgmt_cluster_name
            ),
            # it may fail but expected
            ignore_errors=True,
            msg="Cleanup Successful",
        )
        # todo: check releases and validate that release is available # GET_K8_RELEASES
        logger.info(f"Upgrade cluster: {cluster_name}")
        cmd_option = TKGCommands.TIMEOUT_OPTION.format(timeout=timeout) if timeout else ""
        cmd_option += " -v 9" if verbose else ""
        # self.ssh.run_cmd(TKGCommands.CLUSTER_UPGRADE.format(cluster_name=cluster_name, options=cmd_option))
        self.runcmd.run_cmd_only(TKGCommands.CLUSTER_UPGRADE.format(cluster_name=cluster_name,
                                                                    options=cmd_option))
        # self.ssh.run_cmd(TKGCommands.LIST_ALL_CLUSTERS)
        self.runcmd.run_cmd_only(TKGCommands.LIST_ALL_CLUSTERS)
