#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import json
from constants.constants import Paths, UpgradeVersions, UpgradeBinaries, TKGCommands
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from util.logger_helper import LoggerHelper
from workflows.cluster_common_workflow import ClusterCommonWorkflow
import traceback
from util.common_utils import downloadAndPushKubernetesOvaMarketPlace, download_upgrade_binaries, \
    checkenv, untar_binary, locate_binary_tmp
from util.cmd_runner import RunCmd
import pathlib

logger = LoggerHelper.get_logger(name='ra_mgmt_upgrade_workflow')

class RaMgmtUpgradeWorkflow:
    def __init__(self, run_config: RunConfig):
        self.run_config = run_config
        logger.info ("Current deployment state: %s", self.run_config.state)
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        self.tanzu_client = TkgCliClient()
        self.rcmd = RunCmd()

        with open(jsonpath) as f:
            self.jsonspec = json.load(f)

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)

    def get_desired_state_tkg_version(self):
        """
        Method to get desired state TKG version
        """
        desired_state_tkg_type = ''.join([attr for attr in dir(self.run_config.desired_state.version) if "tkg" in attr])
        self.desired_state_tkg_version = None
        if desired_state_tkg_type == "tkgm":
            self.desired_state_tkg_version = self.run_config.desired_state.version.tkgm
        elif desired_state_tkg_type == "tkgs":
            self.desired_state_tkg_version = self.run_config.desired_state.version.tkgs
        else:
            raise f"Invalid TKG type in desired state YAML file: {desired_state_tkg_type}"

    def upgrade_workflow(self):
        try:

            logger.info("Checking if required template is already present")
            kubernetes_ova_os = \
                self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"][
                    "tkgMgmtBaseOs"]
            kubernetes_ova_version = UpgradeVersions.KUBERNETES_OVA_LATEST_VERSION
            down_status = downloadAndPushKubernetesOvaMarketPlace(self.jsonspec,
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
            else:
                # execute upgrade
                cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
                self.tanzu_client.login(cluster_name=cluster)
                if self.tanzu_client.management_cluster_upgrade(cluster_name=cluster) is None:
                    msg= "Failed to upgrade Management cluster"
                    logger.error("Error: {}".format(msg))
                    raise Exception(msg)

                if not self.tanzu_client.retriable_check_cluster_exists(cluster_name=cluster):
                    msg = f"Cluster: {cluster} not in running state"
                    logger.error(msg)
                    raise Exception(msg)

                logger.info("Checking for services status...")
                cluster_status = self.tanzu_client.get_all_clusters()
                mgmt_health = ClusterCommonWorkflow.check_cluster_health(cluster_status, cluster)
                if mgmt_health == "UP":
                    msg = f"Management Cluster {cluster} upgraded successfully"
                    logger.info(msg)
                else:
                    msg = f"Management Cluster {cluster} failed to upgrade"
                    logger.error(msg)
                    raise Exception(msg)

        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))




