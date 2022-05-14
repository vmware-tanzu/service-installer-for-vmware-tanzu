import logging

from common.constants.constants import KubectlCommands
from common.util.base_cmd_helper import BaseCmdHelper

# TODO: Replace with existing logger implementation
logger = logging.getLogger()


class KubectlClient:
    def __init__(self, cmd_runner: BaseCmdHelper):
        self.cmd_runner = cmd_runner

    def set_cluster_context(self, cluster_name):
        logger.info(f"Setting kubectl context to {cluster_name} cluster")
        set_kubectl_context = KubectlCommands.SET_KUBECTL_CONTEXT.format(cluster=cluster_name)
        return self.cmd_runner.run_cmd(set_kubectl_context)

    def get_all_pods(self):
        logger.info("Listing all pods...")
        exit_code, output = self.cmd_runner.run_cmd_output(KubectlCommands.GET_ALL_PODS)
        return output

    def get_all_namespaces(self, options=""):
        logger.info("Listing all namespaces...")
        exit_code, output = self.cmd_runner.run_cmd_output(KubectlCommands.LIST_NAMESPACES.format(options=options))
        return output

    def list_secrets(self, namespace: str, options=""):
        logger.info("Listing all secrets...")
        exit_code, output = self.cmd_runner.run_cmd_output(
            KubectlCommands.LIST_SECRETS.format(namespace=namespace, options=options)
        )
        return output

    def install_cert_manager(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)

        deploy_cert_mgr = f"""
                cd {work_dir};
                {KubectlCommands.APPLY.format(config_file=config_file_path)}
            """
        return self.cmd_runner.run_cmd(deploy_cert_mgr)

    def install_tmc_extensions_mgr(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)

        install_extensions_mgr = f"""
                    cd {work_dir};
                    {KubectlCommands.APPLY.format(config_file=config_file_path)}
                """
        return self.cmd_runner.run_cmd(install_extensions_mgr)

    def create_namespace(self, work_dir, config_file_path):
        create_namespace = f"""
                    cd {work_dir};
                    {KubectlCommands.APPLY.format(config_file=config_file_path)}
                """
        return self.cmd_runner.run_cmd(create_namespace)

    def create_secret(self, secret_name, work_dir, config_file_path, namespace):
        cmd = f"""
                cd {work_dir};
                {KubectlCommands.CREATE_SECRET.format(name=secret_name, config_file=config_file_path, namespace=namespace)}
                """
        return self.cmd_runner.run_cmd(cmd)

    def check_namespace_exists(self, namespace):
        logger.info("Checking if namespace exists")
        namespaces = self.get_all_namespaces(KubectlCommands.FILTER_NAME)
        return f"namespace/{namespace}" in namespaces.split("\r\n")

    def check_secret_exists(self, secret_name, namespace):
        logger.info("Checking if secret exists")
        secrets = self.list_secrets(namespace, KubectlCommands.FILTER_NAME)
        return f"secret/{secret_name}" in secrets.split("\r\n")

    def check_app_exists(self, app_name, namespace):
        logger.info("Checking if app exists")
        apps = self.list_apps(namespace, KubectlCommands.FILTER_NAME)
        return f"app.kappctrl.k14s.io/{app_name}" in apps.split("\r\n")

    def list_apps(self, namespace, options=""):
        logger.info(f"Listing all apps in namespace: {namespace}...")
        exit_code, output = self.cmd_runner.run_cmd_output(
            KubectlCommands.LIST_APPS.format(namespace=namespace, options=options)
        )
        return output

    def get_app_details(self, app_name, namespace, options):
        contour_status = KubectlCommands.GET_APP_DETAILS.format(app_name=app_name, namespace=namespace, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(contour_status)
        return output

    def deploy_extension(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)
        deploy_extension = f"""
                            cd {work_dir};
                            {KubectlCommands.APPLY.format(config_file=config_file_path)}
                        """
        return self.cmd_runner.run_cmd(deploy_extension)

    def add_services_label(self, cluster_name, mgmt_cluster_name):
        self.set_cluster_context(mgmt_cluster_name)

        logger.info(f"Adding shared services label to cluster: {cluster_name}")
        self.cmd_runner.run_cmd(KubectlCommands.ADD_SERVICES_LABEL.format(cluster=cluster_name))

    def list_service_accounts(self, namespace, options=""):
        logger.info(f"Listing all service accounts in namespace: {namespace}...")
        exit_code, output = self.cmd_runner.run_cmd_output(
            KubectlCommands.LIST_SERVICE_ACCOUNTS.format(namespace=namespace, options=options)
        )
        return output

    def check_sa_exists(self, sa_name, namespace):
        logger.info("Checking if service account exists")
        apps = self.list_service_accounts(namespace, KubectlCommands.FILTER_NAME)
        return f"serviceaccount/{sa_name}" in apps.split("\r\n")

    def get_harbor_cert(self, namespace, options=""):
        exit_code, output = self.cmd_runner.run_cmd_output(
            KubectlCommands.GET_HARBOR_CERT.format(namespace=namespace, options=options)
        )
        return output

    def delete_extension(self, cluster_name, extension_name, namespace):
        self.set_cluster_context(cluster_name=cluster_name)
        logger.info(f"Deleting extension {extension_name} in namespace {namespace}")
        return self.cmd_runner.run_cmd(KubectlCommands.DELETE_EXTENSION.format(app_name=extension_name, namespace=namespace))

    def delete_tmc_extensions_mgr(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)

        cmd = f"""
                    cd {work_dir};
                    {KubectlCommands.DELETE.format(config_file=config_file_path)}
                """
        return self.cmd_runner.run_cmd(cmd)

    def install_kapp_controller(self, cluster_name, work_dir, config_file_path):
        self.set_cluster_context(cluster_name)

        cmd = f"""
                    cd {work_dir};
                    {KubectlCommands.APPLY.format(config_file=config_file_path)}
            """
        return self.cmd_runner.run_cmd(cmd)

    def get_secret_details(self, secret_name, namespace, work_dir, options=""):
        cmd = f"""
                cd {work_dir};
                {KubectlCommands.GET_SECRET_DETAILS.format(name=secret_name, namespace=namespace, options=options)}
            """
        output = self.cmd_runner.run_cmd(cmd)
        return output

    def update_secret(self, secret_name, work_dir, config_file_path, namespace):
        cmd = f"""
                cd {work_dir};
                {KubectlCommands.UPDATE_SECRET.format(name=secret_name, config_file=config_file_path, namespace=namespace)}
                """
        return self.cmd_runner.run_cmd(cmd)

    def delete_cluster_context(self, cluster_name):
        logger.info(f"Deleting kubectl context for {cluster_name} cluster")
        delete_kubectl_context = KubectlCommands.DELETE_KUBECTL_CONTEXT.format(cluster=cluster_name)
        return self.cmd_runner.run_cmd(delete_kubectl_context)

    def delete_cluster_context_tkgs(self, cluster_name):
        logger.info(f"Deleting kubectl context for {cluster_name} cluster")
        delete_kubectl_context = KubectlCommands.DELETE_KUBECTL_CONTEXT_TKGS.format(cluster=cluster_name)
        return self.cmd_runner.run_cmd(delete_kubectl_context)

    def delete_cluster(self, cluster_name):
        logger.info(f"Deleting kubectl cluster for {cluster_name} cluster")
        delete_kubectl_cluster = KubectlCommands.DELETE_KUBECTL_CLUSTER.format(cluster=cluster_name)
        return self.cmd_runner.run_cmd(delete_kubectl_cluster)
