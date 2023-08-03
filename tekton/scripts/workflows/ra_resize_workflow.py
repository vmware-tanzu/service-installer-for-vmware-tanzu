#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import random
import string
import json
import time
from constants.constants import Paths, RegexPattern, KubectlCommands
from workflows.cluster_common_workflow import ClusterCommonWorkflow
from lib.tkg_cli_client import TkgCliClient
from lib.kubectl_client import KubectlClient
from model.run_config import RunConfig
from util.logger_helper import LoggerHelper
import traceback
from util.common_utils import checkenv, envCheck, getManagementCluster
from util.cmd_runner import RunCmd
from util.ShellHelper import runShellCommandAndReturnOutputAsList, verifyPodsAreRunning,\
    grabKubectlCommand, grabPipeOutput
import ruamel.yaml
from ruamel.yaml.comments import CommentedMap

logger = LoggerHelper.get_logger(name='resize_workflow')

class RaResizeWorkflow:

    def __init__(self, run_config: RunConfig):

        self.target_clusters_list = []
        self.cluster_resize_state_dict = {}
        self.run_config = run_config
        logger.info("Current deployment config: %s", self.run_config.state)
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        self.tanzu_client = TkgCliClient()
        self.rcmd = RunCmd()

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

        self.tanzu_client = TkgCliClient()
        self.kube_client = KubectlClient()
        self.cluster_common_util = ClusterCommonWorkflow()
        self.cpu_change = ''
        self.memory_change = ''
        tanzu_plugin_cmd = "tanzu plugin sync"
        command_status = self.rcmd.run_cmd_output(tanzu_plugin_cmd)
        logger.debug("Tanzu plugin output: {}".format(command_status))
        logger.debug("Run tanzu command to filter out downloading mesages...")
        self.tanzu_client.get_clusters()

    def resize_workflow(self):

        """
            1. Get the list of clusters in cluster_array
            2. Prepare dict of operation {'clustername': 'Resize_Success',
                                           'clustername': 'Resize Skipped',
                                           'clustername': 'Resize_Failed'}
            3. If mutiple clusters are targetted,
                a. Mark Succeeded if all clusters have Succeeded or Skipped state.
                b. State can be: Succeeded, Skipped, Failed
                c. Mark task has failed, if any one cluster has Failed State
        :return:
        """
        try:

            self.get_list_of_targetted_clusters()
            self.cluster_resize_state_dict = dict.fromkeys(self.target_clusters_list, 'Resize_State')
            self.execute_resize()

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
            provided_targetcluster = str(self.run_config.day2_ops_details.resize.target_cluster).lower()
            logger.info(f"Targetted clusters: {provided_targetcluster}")

            if not provided_targetcluster:
                raise Exception("No cluster provided to perform resize")

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
                strip_targ_cluster = self.run_config.day2_ops_details.resize.target_cluster.strip('*')
                cluster_list_match = [cls for cls in non_mgmt_cluster_list if strip_targ_cluster in cls]
                self.target_clusters_list = cluster_list_match

            else:
                """
                    Only one cluster is targetted. 
                """
                self.target_clusters_list.append(self.run_config.day2_ops_details.resize.target_cluster)

            logger.info(f"Targetted clusters for resize operation{self.target_clusters_list}")

        except Exception:
            logger.error("Error Encountered retrieving cluster list: {}".format(traceback.format_exc()))

    def execute_resize(self):
        try:
            for target_cluster in self.target_clusters_list:
                try:
                    # check if targetted cluster is mgmt or workload cluster
                    cluster = target_cluster
                    logger.info("Check if provided cluster is mgmt cluster. Resize operation is currently not"
                                "supported for mgmt cluster.")

                    mgmt_name = getManagementCluster()
                    if not mgmt_name:
                        logger.error(f"Unable to fetch mgmt cluster name...")
                    else:
                        if mgmt_name == target_cluster:
                            logger.info("Cluster is mgmt cluster. Disabling resize operation for mgmt cluster...")
                            self.cluster_resize_state_dict[cluster] = "Resize_Skipped"
                            continue

                    logger.info(f"Checking if cluster {target_cluster} is present and healthy state...")
                    current_cluster_name = self.tanzu_client.check_cluster_exists(target_cluster)
                    if not current_cluster_name:
                        logger.error(f"Cluster {target_cluster} is not present or in unhealthy state...")
                        self.cluster_resize_state_dict[cluster] = "Resize_Skipped"
                        continue
                    # Perform to resize cluster
                    
                    self.resize_non_mgmt_clusters(cluster)
                    logger.info("Waiting for resize operation completion")
                    time.sleep(10)
                except Exception:
                    logger.error("Error Encountered: {}".format(traceback.format_exc()))
        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))

    def replace_values_cpu_mem(self, filedump):
        """
        1. Replace worker name for either cpu/mem or both replacement
        2. if cpu/memory, replace as required
        3. output formatted to yaml
        :param filedump:
        :param workername:
        :return: True, yamlfile on Success
                 None on Failure
        """
        try:
            skip_cpu = False
            skip_mem = False

            resize_cpu = self.run_config.day2_ops_details.resize.resize_cpu
            resize_mem = self.run_config.day2_ops_details.resize.resize_memory_mb

            if not resize_cpu or "none" in str(resize_cpu).lower() and resize_mem:
                skip_cpu = True
            elif not resize_mem or "none" in str(resize_cpu).lower() and resize_cpu:
                skip_mem = True
            elif resize_cpu and resize_mem:
                skip_cpu = False
                skip_mem = False
            else:
                raise Exception(f"Unable to parse resize options: cpu: {resize_cpu} mem: {resize_mem}")

            for ele in filedump['spec']['topology']['variables']:

                if ele['name'] == 'worker':
                    print(f'ele:{ele}')
                    if skip_cpu:
                        ele['value']['machine']['memoryMiB'] = int(resize_mem)
                        print(ele)
                    elif skip_mem:
                        ele['value']['machine']['numCPUs'] = int(resize_cpu)
                    else:
                        ele['value']['machine']['memoryMiB'] = int(resize_mem)
                        ele['value']['machine']['numCPUs'] = int(resize_cpu)

            replaced_values = json.dumps(filedump)

            def block_style(base):
                """set all mapping and sequneces to block-style"""
                if isinstance(base, CommentedMap):
                    for k in base:
                        block_style(base[k])
                    base.fa.set_block_style()
                if isinstance(base, list):
                    for item in base:
                        block_style(item)
                    base.fa.set_block_style()
                return base

            data = ruamel.yaml.round_trip_load(replaced_values)
            block_style(data)
            yaml_converted = ruamel.yaml.round_trip_dump(data)
            target_file = '/tmp/modified.yaml'
            with open(target_file, 'w') as fw:
                fw.write(yaml_converted)
            return True, target_file

        except Exception:
            print("Error Encountered:{}".format(traceback.format_exc()))
            return None

    def resize_non_mgmt_clusters(self, cluster):
        
        """
        1. switch to mgmt context
        2. get k get cluster <clustername> -o mod.yaml
        3. Browse to topology of worker spec
        4. Change cpu/mem
        5. k apply -f mod.yaml

        :param cluster: cluster name

        :return: True on success
                None on failure
        """

        try:
            # switch to mgmt context
            mgmt_cluster_name = self.cluster_common_util.get_mgmt_cluster_name()
            commands = ["tanzu", "management-cluster", "kubeconfig", "get", mgmt_cluster_name,
                        "--admin"]
            kube_context_cmd = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
            if kube_context_cmd is None:
                logger.error("Failed to get switch to management cluster context command")                
                return None
            list_switch_cmd = str(kube_context_cmd).split(" ")
            status = runShellCommandAndReturnOutputAsList(list_switch_cmd)
            if status[1] != 0:
                logger.error(
                    "Failed to get switch to management cluster context " + str(status[0]))
                return None

            # get the template of the cluster to separate yml file
            # kubectl get cluster cluster-worker -o yaml
            k_template_cmd_out = self.kube_client.get_cluster_template_json(cluster)
            if k_template_cmd_out is None:
                logger.error("Unable to get template of workernode. Bail out")
                return None
            target_file = '/tmp/modfile.json'
            with open(target_file, 'w') as fw:
                fw.write(k_template_cmd_out)

            with open(target_file, 'r') as f:
                filedump = json.load(f)

            status, config_file = self.replace_values_cpu_mem(filedump)
            if status is None:
                logger.error("Error Encountered in replacing values...")
                return None

            # apply the modified file
            apply_out = self.rcmd.run_cmd_output(KubectlCommands.APPLY.format(config_file=
                                                                              config_file))
            logger.info("Applied Out: {}".format(apply_out))
            # check for all running state from Provisioning state
            status_md = self.tanzu_client.retriable_check_cluster_exists(cluster)
            if status_md is None:
                logger.error("Machine deployments are not running on waiting")
                raise Exception("Machine deployments are not running on waiting")
            else:
                logger.info("Completed resize operation...")
                return True

        except Exception:
            logger.error(traceback.format_exc())
            return None
        pass



