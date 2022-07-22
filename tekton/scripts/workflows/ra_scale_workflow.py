#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os, sys
import json
from constants.constants import Paths
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig, ScaleConfig
from util.logger_helper import LoggerHelper
import traceback
from util.common_utils import checkenv
from util.cmd_runner import RunCmd
logger = LoggerHelper.get_logger(name='scale_workflow')

class ScaleWorkflow:
    def __init__(self, run_config: RunConfig, scale_config: ScaleConfig):
        self.scale_config = scale_config
        self.run_config = run_config
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        self.tanzu_client = TkgCliClient()
        self.rcmd = RunCmd()
        self.fetched_cluster_dict = {}

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

        logger.debug("Get tanzu login for entire flow")
        management_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtClusterName']
        self.tanzu_client.login(cluster_name=management_cluster)
        self.scaledetails = self.scale_config.scaledetails.scaleinfo

    def get_cluster_dict(self):

        """
        Execute tanzu login
        tanzu cluster list --include-management-cluster --output json
        format to dict
        :return: cluster dict if succeeded
                 None if failed
        """
        logger.info("Fetching cluster details")
        try:
            cluster_dict = self.tanzu_client.get_all_clusters()
            logger.debug("Cluster dict")
            return cluster_dict
        except Exception:
            logger.error("Error Encountered")
            logger.error(traceback.format_exc())
            return None

    def validate_node_options(self, cluster_details_dict, ctrl_count, worker_count):
        """
                CHECK IF GIVEN CPNODE AND WORKER NODE ARE HIGHER THAN EXISITNG

        :param cluster_details_dict:
        :param ctrl_count:
        :param worker_count:
        :return:
        """
        skip_cnode = False
        skip_wnode = False
        existing_cnode = str(cluster_details_dict['controlplane']).split('/')[1]
        existing_wnode = str(cluster_details_dict['workers']).split('/')[1]
        logger.debug(f"Existing cnode: {existing_cnode}")
        logger.debug(f"Provided node: {ctrl_count}")
        logger.debug(f"Existing wnode: {existing_wnode}")
        logger.debug(f"Provided wnode: {worker_count}")

        if existing_cnode >= str(ctrl_count):
            logger.info("Either No controller nodes are opted for scaling or "
                        "Existing controller nodes are either higher or equal to provided. "
                        "Skipping controller scaling operation..")
            skip_cnode = True
        elif existing_wnode >= str(worker_count):
            logger.info("Either No worker nodes are opted for scaling or "
                        "Existing worker nodes are either higher or equal to provided. "
                        "Skipping worker scaling operation..")
            skip_wnode = True
        return skip_cnode, skip_wnode

    def construct_cmd(self, cluster_name, skip_cnode, skip_wnode, ctrl_count, worker_count):
        """
        Constructs tanzu cluster scale cmd based on provided controller and worker count
        :param cluster_name:
        :param skip_cnode:
        :param skip_wnode:
        :param ctrl_count:
        :param worker_count:
        :return:
        """
        tanzu_scale_cmd = 'tanzu cluster scale {} '.format(cluster_name)
        add_cnode_options = ''
        add_wnode_options = ''
        if not skip_cnode:
            add_cnode_options = '--controlplane-machine-count {}'. \
                format(ctrl_count)
        if not skip_wnode:
            add_wnode_options = '--worker-machine-count {}'. \
                format(worker_count)
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

    def execute_scale(self):
        try:
            # precheck for right entries in scale.yml to identify the cluster
            # to be scaled and the controlnode and worker node to be scaled
            logger.info("====Perform precheck======")
            if not self.scaledetails.execute:
                logger.info("Scale operation is not enabled.")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Scale operation is not enabled",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200

            # There is atleast one scale operation to be present
            # Best possible to avoid repetation is to dump cluster list to dict
            # And then to check cluster exists and also scale operation of controlplane
            # and workers specified in scale-repave yaml file are higher than the existing
            # clusters. Same dictionary can be reused for mgmt, shared and workload clusters

            self.fetched_cluster_dict = self.get_cluster_dict()
            logger.debug(f'Cluster details: {self.fetched_cluster_dict} ')

            if self.fetched_cluster_dict is None:
                error_msg = "Error Fetching cluster details. Possible reasons could be:" \
                            " unable to login to cluster or command output has failed"
                logger.error("Error: {}".format(error_msg))
                raise Exception(error_msg)

            # Check if mgmt needs scaling
            if not self.scaledetails.mgmt.execute_scale:
                logger.info("Scale operation is not enabled for management.")
            else:

                logger.info("Starting scaling of management cluster")
                cluster_name = self.scaledetails.mgmt.clustername
                if not self.tanzu_client.check_cluster_exists(cluster_name=cluster_name):
                    error_msg = f'Cluster {cluster_name} does not exit. Cannot execute Scale ' \
                                f'Operation on given cluster. Check the cluster name and retry ' \
                                f'the operation'
                    logger.error('Error: {}'.format(error_msg))
                    raise Exception(error_msg)
                # strip out mgmt cluster details from the list obtained from cluster_list_json
                mgmt_details_list = [cluster for cluster in self.fetched_cluster_dict
                                     if cluster['name'] == cluster_name]
                mgmt_details_dict = {k: v for d in mgmt_details_list for k, v in d.items()}
                logger.debug(mgmt_details_dict)
                # CHECK IF GIVEN CPNODE AND WORKER NODE ARE HIGHER THAN EXISITNG..
                ctrl_count = self.scaledetails.mgmt.scalecontrolnodecount
                worker_count = self.scaledetails.mgmt.scalworkernodecount
                skip_cnode, skip_wnode = self.validate_node_options(mgmt_details_dict, ctrl_count,
                                                                    worker_count)
                if skip_cnode:
                    if skip_wnode:
                        error_msg = "Invalid counts provided for controller and worker."
                        raise Exception(error_msg)

                construct_tanzu_scale_cmd = self.construct_cmd(cluster_name, skip_cnode, skip_wnode,
                                                               ctrl_count, worker_count)
                # append namespace for mgmt cluster
                exec_scale_mgmt_cmd = f'{construct_tanzu_scale_cmd} --namespace tkg-system'
                logger.debug("TANZU MGMT SCALE CMD: {}".format(exec_scale_mgmt_cmd))
                if self.execute_and_validate(cluster_name, exec_scale_mgmt_cmd):
                    logger.info("Completed scaling for mgmt cluster. Proceeding to next cluster.")

            # Proceed for next cluster
            # Check if shared_services needs scaling
            if not self.scaledetails.shared_services.execute_scale:
                logger.info("Scale operation is not enabled for shared cluster.")
            else:
                logger.info("Starting scaling of Shared Service cluster")
                cluster_name = self.scaledetails.shared_services.clustername
                if not self.tanzu_client.check_cluster_exists(cluster_name=cluster_name):
                    error_msg = f'Cluster {cluster_name} does not exit. Cannot execute Scale ' \
                                f'Operation on given cluster. Check the cluster name and retry ' \
                                f'the operation'
                    logger.error('Error: {}'.format(error_msg))
                    raise Exception(error_msg)
                # strip out shared cluster details from the list obtained from cluster_list_json
                shared_details_list = [cluster for cluster in self.fetched_cluster_dict if
                                       cluster['name'] == cluster_name]
                shared_details_dict = {k: v for d in shared_details_list for k, v in d.items()}
                logger.debug(shared_details_dict)
                # CHECK IF GIVEN CPNODE AND WORKER NODE ARE HIGHER THAN EXISITNG..
                ctrl_count = self.scaledetails.shared_services.scalecontrolnodecount
                worker_count = self.scaledetails.shared_services.scalworkernodecount
                skip_cnode, skip_wnode = self.validate_node_options(shared_details_dict,
                                                                    ctrl_count,
                                                                    worker_count)
                logger.debug(f"skipcnode: {skip_cnode} \t skipwnode: {skip_wnode}")
                if skip_cnode:
                    if skip_wnode:
                        error_msg = "Invalid counts provided for controller and worker."
                        raise Exception(error_msg)
                construct_tanzu_scale_cmd = self.construct_cmd(cluster_name, skip_cnode,
                                                               skip_wnode,
                                                               ctrl_count, worker_count)
                logger.debug("TANZU SHARED SCALE CMD: {}".format(construct_tanzu_scale_cmd))
                if self.execute_and_validate(cluster_name, construct_tanzu_scale_cmd):
                    logger.info("Completed scaling for shared cluster. Proceeding to next cluster.")
            # Proceed for next cluster
            # Check if workload_clusters needs scaling
            if not self.scaledetails.workload_clusters.execute_scale:
                logger.info("Scale operation is not enabled for shared cluster.")
            else:
                logger.info("Starting scaling of workload cluster")
                cluster_name = self.scaledetails.workload_clusters.clustername
                if not self.tanzu_client.check_cluster_exists(cluster_name=cluster_name):
                    error_msg = f'Cluster {cluster_name} does not exit. Cannot execute Scale ' \
                                f'Operation on given cluster. Check the cluster name and retry ' \
                                f'the operation'
                    logger.error('Error: {}'.format(error_msg))
                    raise Exception(error_msg)
                # strip out workload_clusters details from the list obtained from cluster_list_json
                wld_details_list = [cluster for cluster in self.fetched_cluster_dict if
                                       cluster['name'] == cluster_name]
                wld_details_dict = {k: v for d in wld_details_list for k, v in d.items()}
                logger.debug(wld_details_dict)
                # CHECK IF GIVEN CPNODE AND WORKER NODE ARE HIGHER THAN EXISITNG..
                ctrl_count = self.scaledetails.workload_clusters.scalecontrolnodecount
                worker_count = self.scaledetails.workload_clusters.scalworkernodecount
                skip_cnode, skip_wnode = self.validate_node_options(wld_details_dict,
                                                                    ctrl_count,
                                                                    worker_count)
                if skip_cnode:
                    if skip_wnode:
                        error_msg = "Invalid counts provided for controller and worker."
                        raise Exception(error_msg)
                construct_tanzu_scale_cmd = self.construct_cmd(cluster_name, skip_cnode, skip_wnode,
                                                               ctrl_count, worker_count)
                logger.debug("TANZU SHARED SCALE CMD: {}".format(construct_tanzu_scale_cmd))
                if self.execute_and_validate(cluster_name, construct_tanzu_scale_cmd):
                    logger.info("Completed scaling for workload_cluster.")
            logger.info("All Scale operations have been completed..")
            d = {
                "responseType": "SUCCESS",
                "msg": "Scale operation completed",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))

