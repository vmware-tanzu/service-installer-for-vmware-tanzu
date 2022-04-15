#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import json
from constants.constants import Paths, UpgradeVersions, TKGCommands, UpgradeBinaries
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from util.logger_helper import LoggerHelper
from workflows.cluster_common_workflow import ClusterCommonWorkflow
import traceback
from util.common_utils import downloadAndPushKubernetesOvaMarketPlace, checkenv, \
    download_upgrade_binaries, untar_binary, locate_binary_tmp
from util.cmd_runner import RunCmd

logger = LoggerHelper.get_logger(name='ra_shared_upgrade_workflow')

class RaSharedUpgradeWorkflow:
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

    def upgrade_workflow(self):
        try:

            # Precheck if binary is already downloaded.
            version_raw = self.rcmd.run_cmd_output(TKGCommands.VERSION)
            version = [line for line in version_raw.split("\n") if "version" in line][0]
            if not UpgradeVersions.TARGET_VERSION in version:
                logger.info("Binary Version needs to be upgraded to targetted version")
                refToken = self.jsonspec['envSpec']['marketplaceSpec']['refreshToken']

                for binary in UpgradeBinaries.binary_list:
                    # kubectl and yq are same version for 1.4.0 to 1.4.1
                    # proceed to download to tanzu cli only.
                    if 'tanzu-cli' in binary:
                        logger.info("Downloading and replacing binary: {}".format(binary))
                        download_status = download_upgrade_binaries(binary, refToken)
                        logger.info("Download status: {}".format(download_status))
                        # Proceed to install the binary
                        try:
                            logger.info("Removing old bom file")
                            remove_old_bom_cmd = 'rm -rf {}'.format(
                                UpgradeVersions.OLD_TKG_COMP_FILE)
                            self.rcmd.run_cmd_only(remove_old_bom_cmd)
                            # extract to /tmp
                            logger.info("Untar binary...")
                            tar_binary_tmp = '/tmp/{}'.format(binary)
                            untar_binary(tar_binary_tmp)
                            # locate the right binary path
                            logger.info("Locating full path of binary...")
                            full_path_bin = locate_binary_tmp(search_dir='/tmp/cli/core',
                                                              filestring='tanzu')
                            if full_path_bin:
                                installer_cmd = 'install {} /usr/local/bin/tanzu'.format(
                                    full_path_bin)
                            else:
                                logger.error("Unable to install tanzu binary")
                                raise Exception()
                            self.rcmd.run_cmd_only(installer_cmd)

                        except Exception:
                            logger.error("Error: {}".format(traceback.format_exc()))

            logger.info("Binary Version is already upgraded to targetted version")
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

                mgmt_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
                cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterName']
                self.tanzu_client.login(cluster_name=mgmt_cluster)
                if self.tanzu_client.tanzu_cluster_upgrade(cluster_name=cluster) is None:
                    msg = "Failed to upgrade {} cluster".format(cluster)
                    logger.error("Error: {}".format(msg))
                    raise Exception(msg)

                if not self.tanzu_client.retriable_check_cluster_exists(cluster_name=cluster):
                    msg = f"Cluster: {cluster} not in running state"
                    logger.error(msg)
                    raise Exception(msg)

                logger.info("Checking for services status...")
                cluster_status = self.tanzu_client.get_all_clusters()
                shared_health = ClusterCommonWorkflow.check_cluster_health(cluster_status, cluster)
                if shared_health == "UP":
                    msg = f"Shared Cluster {cluster} upgraded successfully"
                    logger.info(msg)
                else:
                    msg = f"Shared Cluster {cluster} failed to upgrade"
                    logger.error(msg)
                    raise Exception(msg)

        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))




