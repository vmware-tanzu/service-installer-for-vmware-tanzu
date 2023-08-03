#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import time
import json
from constants.constants import Paths
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from workflows.cluster_common_workflow import ClusterCommonWorkflow
from util.logger_helper import LoggerHelper
import traceback
from util.common_utils import checkenv
from util.cmd_runner import RunCmd
logger = LoggerHelper.get_logger(name='scale_workflow')

class RaScaleWorkflow:

    def __init__(self, run_config: RunConfig):

        self.run_config = run_config
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        self.tanzu_client = TkgCliClient()
        self.rcmd = RunCmd()
        self.cluster_common_util = ClusterCommonWorkflow()
        self.fetched_cluster_dict = {}
        self.cluster_scale_state_dict = {}
        self.target_clusters_list = []
        self.is_a_mgmt_cluster = False

        with open(jsonpath) as f:
            self.jsonspec = json.load(f)
        try:
            check_env_output = checkenv(self.jsonspec)
            print("check_env_output: {}".format(check_env_output))
            if check_env_output is None:
                msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                      "incorrect spec provided."
                logger.error(msg)
                sys.exit(-1)
        except Exception:
            logger.error(traceback.format_exc())

    def construct_cmd(self, cluster_name, ctrl_count, worker_count):
        """
        Constructs tanzu cluster scale cmd based on provided controller and worker count
        :param cluster_name:
        :param ctrl_count:
        :param worker_count:
        :return: constructed tanzu scale command
        """
        tanzu_scale_cmd = 'tanzu cluster scale {} '.format(cluster_name)
        add_cnode_options = ''
        add_wnode_options = ''
        if not worker_count:
            logger.debug(f"HERE AT NOT_WORKER_COUNT")
            add_cnode_options = f'--controlplane-machine-count {ctrl_count}'
        if not ctrl_count:
            logger.debug(f"HERE AT NOT_CONTROLLER_COUNT")
            add_wnode_options = f'--worker-machine-count {worker_count}'
        else:
            add_cnode_options = f'--controlplane-machine-count {ctrl_count}'
            add_wnode_options = f'--worker-machine-count {worker_count}'

        exec_scale_cmd = f'{tanzu_scale_cmd} {add_cnode_options} {add_wnode_options}'
        return exec_scale_cmd

    def execute_and_validate(self, cluster_name, exec_cmd):
        """
        executes cluster scale cmd
        validate cluster health after executing
        :param cluster_name:
        :param exec_cmd:
        :return: True on completion.
                 Bail on Exception if failed
        """
        scale_output = self.rcmd.run_cmd_output(exec_cmd)
        logger.debug(scale_output)
        if scale_output is None:
            logger.error("Failure during scaling operation..")
            raise Exception(traceback.format_exc())
        else:
            scale_completed = self.tanzu_client.retriable_long_duration_check_cluster_exists(
                cluster_name=cluster_name)
            if scale_completed:
                logger.info("Completed Scaling Operation Successfully: {}".format(scale_output))
                return True
            else:
                error_msg = "Unable to get cluster health after scaling"
                raise Exception(error_msg)

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
            provided_targetcluster = str(self.run_config.day2_ops_details.scale.target_cluster).lower()
            logger.info(f"Targetted clusters: {provided_targetcluster}")

            if not provided_targetcluster:
                raise Exception("No cluster provided to perform scale...")

            elif "all" in provided_targetcluster:

                """
                    Get mgmt cluster name first and add to target_clusters_list as first member
                    Get remaining clusters name and append to the list. 
                """

                logger.info("Getting mgmt cluster name")
                mgmt_cluster_name = self.cluster_common_util.get_mgmt_cluster_name()
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
                self.target_clusters_list.append(self.run_config.day2_ops_details.scale.target_cluster)

            logger.info(f"Targetted clusters for scale operation{self.target_clusters_list}")

        except Exception:
            logger.error("Error Encountered retrieving cluster list: {}".format(traceback.format_exc()))

    def execute_scale(self, target_cluster):

        try:
            logger.info(f"Starting scaling of cluster: {target_cluster}")

            ctrl_count = self.run_config.day2_ops_details.scale.control_plane_node_count
            worker_count = self.run_config.day2_ops_details.scale.worker_node_count

            construct_tanzu_scale_cmd = self.construct_cmd(target_cluster, ctrl_count, worker_count)            
            # append namespace for mgmt cluster
            exec_scale_cmd = f'{construct_tanzu_scale_cmd} '
            if self.is_a_mgmt_cluster:
                exec_scale_cmd += " --namespace tkg-system"
            if self.execute_and_validate(target_cluster, exec_scale_cmd):
                logger.info(f"Executing scaling for cluster: {target_cluster}.")
                time.sleep(30)
        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))

        logger.info("All Scale operations have been completed..")

        d = {
            "responseType": "SUCCESS",
            "msg": "Scale operation completed",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    def scale_workflow(self):

        """
            1. Get the list of clusters in cluster_array
            2. Prepare dict of operation {'clustername': 'Scale_Success',
                                         'clustername': 'Scale Skipped',
                                         'clustername': 'Scale_Failed'}
            3. If mutiple clusters are targetted,
                        a. Mark Succeeded if all clusters have Succeeded or Skipped state.
                        b. State can be: Succeeded, Skipped, Failed
                        c. Mark task has failed, if any one cluster has Failed State
        :return:
        """
        try:

            self.get_list_of_targetted_clusters()
            self.cluster_scale_state_dict = dict.fromkeys(self.target_clusters_list, 'Scale_State')

        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))

        try:
            for target_cluster in self.target_clusters_list:
                self.is_a_mgmt_cluster = False
                try:
                    tanzu_plugin_cmd = "tanzu plugin sync"
                    command_status = self.rcmd.run_cmd_output(tanzu_plugin_cmd)
                    logger.debug("Tanzu plugin output: {}".format(command_status))
                    logger.debug("Run tanzu command to filter out downloading mesages...")
                    self.tanzu_client.get_clusters()
                    current_cluster_name = self.tanzu_client.check_cluster_exists(target_cluster)
                    if not current_cluster_name:
                        logger.error(f"Cluster {target_cluster} is not present or in unhealthy state...")
                        self.cluster_scale_state_dict[target_cluster] = "Scale_Skipped"
                        continue

                    # check if targetted cluster is mgmt or workload cluster
                    # If mgmt cluster, do tanzu login before issuing tanzu cluster scale cmd
                    if self.cluster_common_util.is_mgmt_cluster:
                        self.is_a_mgmt_cluster = True
                        self.tanzu_client.login(target_cluster)
                    # Perform to scale cluster
                    logger.info("Waiting for scale operation to be completed...")
                    self.execute_scale(target_cluster)
                    time.sleep(10)
                except Exception:
                    logger.error("Error Encountered: {}".format(traceback.format_exc()))
        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))
