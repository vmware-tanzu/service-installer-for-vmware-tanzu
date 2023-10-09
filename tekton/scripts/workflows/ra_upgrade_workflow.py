#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import json
from constants.constants import Paths, UpgradeVersions, Tkg_version
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from util.logger_helper import LoggerHelper
from workflows.cluster_common_workflow import ClusterCommonWorkflow
import traceback
from util.common_utils import downloadAndPushKubernetesOvaMarketPlace, checkenv, envCheck, checkAirGappedIsEnabled, \
    grabPortFromUrl, grabHostFromUrl
from util.cmd_runner import RunCmd
from common.certificate_base64 import getBase64CertWriteToFile
from util.ShellHelper import runShellCommandAndReturnOutputAsList, runProcess

logger = LoggerHelper.get_logger(name='ra_mgmt_upgrade_workflow')

class RaUpgradeWorkflow:

    """
    Though the first layer of day2 operations selected are done by day2_precheck tasks, perform
    check that only one day2 operation is selected.

    For upgrade:
        - Call upgrade workflow
            - Get the clustername.
            - If only one clustername. Set clustername to target_cluster for upgrade operation
            - If all mentioned in clustername. Start with mgmt cluster and proceed to all clusters
              under tanzu cluster list
            - If * mentioned in clustername. Call iterator to perform upgrade one by one matching
              clustername.
              Parallel upgrading of multiple clusters is YET TO BE TESTED and hence NOT IMPLEMENTED.
              Perform cluster upgrade one by one.
            - Download ova only once before starting the update operation

    """
    def __init__(self, run_config: RunConfig):

        self.target_clusters_list = []
        self.cluster_update_state_dict = {}
        self.run_config = run_config
        logger.info("Current deployment config: %s", self.run_config.state)
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        self.tanzu_client = TkgCliClient()
        self.rcmd = RunCmd()
        self.cluster_common_util = ClusterCommonWorkflow()

        with open(jsonpath) as f:
            self.jsonspec = json.load(f)
        self.env = envCheck(self.run_config)
        if self.env[1] != 200:
            logger.error("Wrong env provided " + self.env[0])
            d = {
                "responseType": "ERROR",
                "msg": "Wrong env provided " + self.env[0],
                "ERROR_CODE": 500
            }
            logger.error(f"Error: {d}")
        self.env = self.env[0]

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)

    def update_workflow(self):

        """
            1. Get the list of clusters in cluster_array
            2. Prepare dict of operation {'clustername': 'Update_Success',
                                           'clustername': 'Update Skipped',
                                           'clustername': 'Update_Failed'}
            3. If mutiple clusters are targetted,
                a. Mark Succeeded if all clusters have Succeeded or Skipped state.
                b. State can be: Succeeded, Skipped, Failed
                c. Mark task has failed, if any one cluster has Failed State
        :return:
        """
        try:

            self.get_list_of_targetted_clusters()
            self.cluster_update_state_dict = dict.fromkeys(self.target_clusters_list, 'Update_State')
            self.execute_update()

        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))

    def get_list_of_targetted_clusters(self):

        """
            - If single cluster name is provided,
                - add clustername in target_clusters_list and
                - proceed default cluster upgrade process
            - If * present in clustername, grep for cluster list matching regex before *.
                - append the matching clusters in target_clusters_list
            - If all is provided in clustername, append all clusternames to target_clusters_list
        :return:
        """
        try:
            logger.info("Retreiving targetted clusters")
            provided_targetcluster = str(self.run_config.day2_ops_details.update.target_cluster).lower()
            logger.info(f"Targetted clusters: {provided_targetcluster}")

            if not provided_targetcluster:
                raise Exception("No cluster provided to perform update")

            elif "all" in provided_targetcluster:

                """
                    Get mgmt cluster name first and add to target_clusters_list as first member
                    Get remaining clusters name and append to the list. 
                """

                logger.info("Getting mgmt cluster name")
                mgmt_cluster_name = self.cluster_common_util.get_mgmt_cluster_name()
                if mgmt_cluster_name is None:
                    raise Exception("Unable to obtain mgmt cluster details")

                self.target_clusters_list.append(mgmt_cluster_name)

                non_mgmt_cluster_list = self.cluster_common_util.get_all_non_mgmt_clusters_name()
                self.target_clusters_list += non_mgmt_cluster_list

            elif "*" in provided_targetcluster:

                """
                    * inclusion covers a list of clusters which are targeted 
                    This mode suports only on shared/workload clusters NOT ON MGMT clusters. 
                """
                non_mgmt_cluster_list = self.cluster_common_util.get_all_non_mgmt_clusters_name()
                strip_targ_cluster = self.run_config.day2_ops_details.update.target_cluster.strip('*')
                cluster_list_match = [cls for cls in non_mgmt_cluster_list if strip_targ_cluster in cls]
                self.target_clusters_list = cluster_list_match

            else:
                """
                    Only one cluster is targetted. 
                """
                self.target_clusters_list.append(self.run_config.day2_ops_details.update.target_cluster)

            logger.info(f"Targetted clusters for update operation{self.target_clusters_list}")

        except Exception:
            logger.error("Error Encountered retrieving cluster list: {}".format(traceback.format_exc()))

    def set_airgap_env(self):

        """
        Set airgap requisites in case of airgap environment.

        :return:
        """
        air_gapped_repo = self.jsonspec['envSpec']['customRepositorySpec'][
            'tkgCustomImageRepository']
        air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        bom_image_cmd = ["tanzu", "config", "set", "env.TKG_BOM_IMAGE_TAG", Tkg_version.TAG]
        custom_image_cmd = ["tanzu", "config", "set", "env.TKG_CUSTOM_IMAGE_REPOSITORY",
                            air_gapped_repo]
        custom_image_skip_tls_cmd = ["tanzu", "config", "set",
                                     "env.TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY",
                                     "False"]
        runProcess(bom_image_cmd)
        runProcess(custom_image_cmd)
        runProcess(custom_image_skip_tls_cmd)
        getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo),
                                 grabPortFromUrl(air_gapped_repo))
        with open('cert.txt', 'r') as file2:
            repo_cert = file2.readline()
        repo_certificate = repo_cert
        tkg_custom_image_repo = ["tanzu", "config", "set",
                                 "env.TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE",
                                 repo_certificate]
        runProcess(tkg_custom_image_repo)

    def update_mgmt_cluster(self, cluster):

        kubernetes_ova_os = self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"][
            "tkgMgmtBaseOs"]
        target_update_version = self.run_config.day2_ops_details.update.tkgm
        kubernetes_ova_version = UpgradeVersions.upgrade_mapping_dict[target_update_version]
        # Set airgapped custom repository envs
        if checkAirGappedIsEnabled(self.jsonspec):
            self.set_airgap_env()
        else:
            logger.info("Checking if required template is already present")
            upgrade_version = self.run_config.day2_ops_details.update.tkgm
            down_status = downloadAndPushKubernetesOvaMarketPlace(self.env, self.jsonspec,
                                                                  kubernetes_ova_version,
                                                                  kubernetes_ova_os,
                                                                  upgrade=True,
                                                                  upgrade_version=upgrade_version)
            if down_status[0] is None:
                logger.error(down_status[1])
                d = {
                    "responseType": "ERROR",
                    "msg": down_status[1],
                    "ERROR_CODE": 500
                }
                logger.error("Error: {}".format(json.dumps(d)))
                msg = "Failed to download template..."
                raise Exception(msg)

        self.tanzu_client.login(cluster_name=cluster)
        if self.tanzu_client.management_cluster_upgrade(cluster_name=cluster) is None:
            msg = "Failed to upgrade Management cluster"
            logger.error("Error: {}".format(msg))
            raise Exception(msg)

        if not self.tanzu_client.retriable_check_cluster_exists(cluster_name=cluster):
            msg = f"Cluster: {cluster} not in running state"
            logger.error(msg)
            raise Exception(msg)

        logger.info("Checking for services status...")
        cluster_status = self.tanzu_client.get_all_clusters()
        mgmt_health = self.cluster_common_util.check_cluster_health(cluster_status, cluster)
        if mgmt_health == "UP":
            msg = f"Management Cluster {cluster} upgraded successfully"
            logger.info(msg)
            logger.info("Updating cluster dictionary")
            self.cluster_update_state_dict[cluster] = "Update_Success"
        else:
            msg = f"Management Cluster {cluster} failed to upgrade"
            logger.error(msg)
            logger.info("Updating cluster dictionary")
            self.cluster_update_state_dict[cluster] = "Update_Failed"
            raise Exception(msg)

    def update_non_mgmt_clusters(self, clustername):

        tanzu_init_cmd = "tanzu plugin sync"
        command_status = self.rcmd.run_cmd_output(tanzu_init_cmd)
        logger.debug("Tanzu plugin output: {}".format(command_status))
        pod_runninng = ["tanzu", "cluster", "list"]
        command_status = runShellCommandAndReturnOutputAsList(pod_runninng)
        if command_status[1] != 0:
            logger.error("Failed to run command to check status of pods")
            msg = f"Failed to run command to check status of pods"
            logger.error(msg)
            raise Exception(msg)

        cluster = clustername
        cmd_list = ["tanzu", "cluster", "available-upgrades", "get", cluster]
        cmd_op = runShellCommandAndReturnOutputAsList(cmd_list)

        if cmd_op[1] != 0:
            logger.error("available-upgrades command failed for cluster " + cluster)
            msg = f"'tanzu cluster available-upgrades' command failed for cluster {cluster}"
            logger.error(msg)
            raise Exception(msg)

        if len(cmd_op[0]) > 1 and str(cmd_op[0][1]).__contains__("True"):
            print(cmd_op[0][1])

            logger.info("Checking if required template is already present")
            kubernetes_ova_os = \
                self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"][
                    "tkgMgmtBaseOs"]
            kubernetes_ova_version = (cmd_op[0][1].split())[1].split('+', 1)[0]
            if not checkAirGappedIsEnabled(self.jsonspec):
                down_status = downloadAndPushKubernetesOvaMarketPlace(self.env, self.jsonspec,
                                                                      kubernetes_ova_version,
                                                                      kubernetes_ova_os,
                                                                      upgrade=True)
                if down_status[0] is None:
                    logger.error(down_status[1])
                    d = {
                        "responseType": "ERROR",
                        "msg": down_status[1],
                        "ERROR_CODE": 500
                    }
                    logger.error("Error: {}".format(json.dumps(d)))
                    msg = "Failed to download template..."
                    raise Exception(msg)

            mgmt_cluster = self.cluster_common_util.get_mgmt_cluster_name()
            self.tanzu_client.login(cluster_name=mgmt_cluster)
            if self.tanzu_client.tanzu_cluster_upgrade(cluster_name=cluster,
                                                       k8s_version=kubernetes_ova_version) is None:
                msg = "Failed to upgrade {} cluster".format(cluster)
                logger.error("Error: {}".format(msg))
                raise Exception(msg)

            if not self.tanzu_client.retriable_check_cluster_exists(cluster_name=cluster):
                msg = f"Cluster: {cluster} not in running state"
                logger.error(msg)
                raise Exception(msg)

            logger.info("Checking for services status...")
            cluster_status = self.tanzu_client.get_all_clusters()
            shared_health = self.cluster_common_util.check_cluster_health(cluster_status, cluster)
            if shared_health == "UP":
                msg = f"Shared Cluster {cluster} upgraded successfully"
                logger.info(msg)
                logger.info("Updating cluster dictionary")
                self.cluster_update_state_dict[cluster] = "Update_Success"
            else:
                msg = f"Shared Cluster {cluster} failed to upgrade"
                logger.error(msg)
                logger.info("Updating cluster dictionary")
                self.cluster_update_state_dict[cluster] = "Update_Failed"
                raise Exception(msg)
        elif str(cmd_op[0][0]).__contains__("no available upgrades"):
            msg = f"no available upgrades for cluster {cluster}"
            logger.info(msg)
            self.cluster_update_state_dict[cluster] = "Update_Skipped"
        else:
            msg = f"Shared Cluster {cluster} failed to upgrade"
            logger.error(msg)
            logger.info("Updating cluster dictionary")
            self.cluster_update_state_dict[cluster] = "Update_Failed"
            raise Exception(msg)

    def execute_update(self):

        try:
            # loop through target cluster list
            for target_cluster in self.target_clusters_list:
                try:
                    # check if targetted cluster is mgmt or workload cluster
                    cluster = target_cluster
                    logger.info(f"Checking if cluster {target_cluster} is present and healthy state...")
                    current_cluster_list = self.tanzu_client.check_cluster_exists(target_cluster)
                    if not current_cluster_list:
                        logger.error(f"Cluster {target_cluster} is not present or in unhealthy state...")
                        self.cluster_update_state_dict[cluster] = "Update_Skipped"
                        continue

                    if self.cluster_common_util.is_mgmt_cluster:
                        logger.info("Cluster is mgmt cluster")
                        # self.update_mgmt_cluster(cluster)
                    else:
                        # self.update_non_mgmt_clusters(cluster)
                        logger.info("Cluster is wkld cluster")
                except Exception:
                    logger.error("Error Encountered: {}".format(traceback.format_exc()))
            logger.info(f"Cluster update status: {self.cluster_update_state_dict}")
        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))




