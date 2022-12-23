#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import json
from constants.constants import Paths, UpgradeVersions, TKGCommands, UpgradeBinaries, Tkg_version
from lib.tkg_cli_client import TkgCliClient
from model.run_config import RunConfig
from util.logger_helper import LoggerHelper
from workflows.cluster_common_workflow import ClusterCommonWorkflow
import traceback
from util.common_utils import downloadAndPushKubernetesOvaMarketPlace, checkenv, \
    download_upgrade_binaries, untar_binary, locate_binary_tmp, envCheck, checkAirGappedIsEnabled, \
        grabPortFromUrl, grabHostFromUrl
from util.cmd_runner import RunCmd
from util.ShellHelper import grabKubectlCommand, runShellCommandAndReturnOutputAsList, \
    grabPipeOutput, runProcess
from common.certificate_base64 import getBase64CertWriteToFile

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
        self.env = envCheck(self.run_config)
        if self.env[1] != 200:
            logger.error("Wrong env provided " + self.env[0])
            d = {
                "responseType": "ERROR",
                "msg": "Wrong env provided " + self.env[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        self.env = self.env[0]

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)

    def upgrade_workflow(self):
        try:
            ## Set airgapped custom repository envs
            if checkAirGappedIsEnabled(self.jsonspec):
                air_gapped_repo = self.jsonspec['envSpec']['customRepositorySpec']['tkgCustomImageRepository']
                air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
                bom_image_cmd = ["tanzu", "config", "set", "env.TKG_BOM_IMAGE_TAG", Tkg_version.TAG]
                custom_image_cmd = ["tanzu", "config", "set", "env.TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo]
                custom_image_skip_tls_cmd = ["tanzu", "config", "set", "env.TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False"]
                runProcess(bom_image_cmd)
                runProcess(custom_image_cmd)
                runProcess(custom_image_skip_tls_cmd)
                getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
                with open('cert.txt', 'r') as file2:
                    repo_cert = file2.readline()
                repo_certificate = repo_cert
                tkg_custom_image_repo = ["tanzu", "config", "set", "env.TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate]
                runProcess(tkg_custom_image_repo)
                
            tanzu_init_cmd = "tanzu plugin sync"
            command_status = self.rcmd.run_cmd_output(tanzu_init_cmd)
            logger.debug("Tanzu plugin output: {}".format(command_status))
            podRunninng = ["tanzu", "cluster", "list"]
            command_status = runShellCommandAndReturnOutputAsList(podRunninng)
            if command_status[1] != 0:
                logger.error("Failed to run command to check status of pods")
                msg = f"Failed to run command to check status of pods"
                logger.error(msg)
                raise Exception(msg)

            cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterName']
            cmdList = ["tanzu", "cluster", "available-upgrades", "get", cluster]
            cmdOP = runShellCommandAndReturnOutputAsList(cmdList)

            if cmdOP[1] != 0:
               logger.error("available-upgrades command failed for cluster "+cluster)
               msg = f"'tanzu cluster available-upgrades' command failed for cluster {cluster}"
               logger.error(msg)
               raise Exception(msg)

            if len(cmdOP[0]) > 1 and str(cmdOP[0][1]).__contains__("True"):
                print(cmdOP[0][1])

                logger.info("Checking if required template is already present")
                kubernetes_ova_os = \
                    self.jsonspec["tkgComponentSpec"]["tkgMgmtComponents"][
                        "tkgMgmtBaseOs"]
                kubernetes_ova_version = (cmdOP[0][1].split())[1].split('+', 1)[0]
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
                    
                mgmt_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgMgmtClusterName']
                self.tanzu_client.login(cluster_name=mgmt_cluster)
                if self.tanzu_client.tanzu_cluster_upgrade(cluster_name=cluster, k8s_version=kubernetes_ova_version) is None:
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
            elif str(cmdOP[0][0]).__contains__("no available upgrades"):
                msg = f"no available upgrades for cluster {cluster}"
                logger.info(msg)
            else:
                msg = f"Shared Cluster {cluster} failed to upgrade"
                logger.error(msg)
                raise Exception(msg)
        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))