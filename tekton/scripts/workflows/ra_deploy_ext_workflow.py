#!/usr/local/bin/python3

#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path
import time
import json
from util.logger_helper import LoggerHelper, log
from model.run_config import RunConfig
from extensions.tkg_extensions import deploy_tkg_extensions
from extensions.tkgs_extensions import deploy_tkgs_extensions
from common.certificate_base64 import getBase64CertWriteToFile
from constants.constants import Tkg_version, Tkg_Extention_names
from util.extensions_helper import checkTanzuExtensionEnabled, check_fluent_bit_splunk_endpoint_endpoint_enabled, \
    check_fluent_bit_kafka_endpoint_endpoint_enabled, check_fluent_bit_syslog_endpoint_enabled, \
    check_fluent_bit_elastic_search_endpoint_enabled, check_fluent_bit_http_endpoint_enabled, checkPromethusEnabled
    
from constants.constants import Tkg_Extention_names, Paths 
from util.common_utils import checkenv,  checkAirGappedIsEnabled, \
        grabPortFromUrl, grabHostFromUrl
from util.tkg_util import TkgUtil
from util.cmd_runner import RunCmd
from util.ShellHelper import runProcess

logger = LoggerHelper.get_logger(name='ra_deploy_ext_workflow.py')


class RaDeployExtWorkflow:

    def __init__(self, run_config: RunConfig) -> None:
        self.run_config = run_config
        self.version = None
        self.jsonpath = None
        self.tkg_util_obj = TkgUtil(run_config=self.run_config)
        self.tkg_version_dict = self.tkg_util_obj.get_desired_state_tkg_version()
        self.desired_state_tkg_version = None
        if "tkgs" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_NS_MASTER_SPEC_PATH)
            self.desired_state_tkg_version = self.tkg_version_dict["tkgs"]
        elif "tkgm" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
            self.desired_state_tkg_version = self.tkg_version_dict["tkgm"]
        else:
            raise Exception(f"Could not find supported TKG version: {self.tkg_version_dict}")
        with open(self.jsonpath) as f:
            self.jsonspec = json.load(f)

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)
        self.isEnvTkgs_wcp = TkgUtil.isEnvTkgs_wcp(self.jsonspec)
        self.isEnvTkgs_ns = TkgUtil.isEnvTkgs_ns(self.jsonspec)
        self.extension_obj = deploy_tkg_extensions(self.jsonspec)
        self.rcmd = RunCmd()

    def deploy_tkg_extensions(self):
        try:
            """
            Env check commented and hardcoded the env variable with value vpshere

            env = envCheck()
            if env[1] != 200:
                logger.error("Wrong env provided " + env[0])
                d = {
                    "responseType": "ERROR",
                    "msg": "Wrong env provided " + env[0],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
            """
            if self.isEnvTkgs_ns:
                result = deploy_tkgs_extensions(self.jsonspec)
                if result[1] != 200:
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to deploy extensions - ",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                else:
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Extensions deployment is successful - ",
                        "ERROR_CODE": 200
                    }
                    return json.dumps(d), 200
            else:
                # Init tanzu cli plugins
                if checkAirGappedIsEnabled(self.jsonspec) :
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
                logginglistOfExtention = []
                if checkTanzuExtensionEnabled(self.jsonspec):
                    if check_fluent_bit_splunk_endpoint_endpoint_enabled(self.jsonspec):
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_SPLUNK)
                    if check_fluent_bit_http_endpoint_enabled(self.jsonspec):
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_HTTP)
                    if check_fluent_bit_syslog_endpoint_enabled(self.jsonspec):
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_SYSLOG)
                    if check_fluent_bit_elastic_search_endpoint_enabled(self.jsonspec):
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_ELASTIC)
                    if check_fluent_bit_kafka_endpoint_endpoint_enabled(self.jsonspec):
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_KAFKA)
                        
                else:
                    logger.info("Tanzu logging extensions deploy is deactivated, no extensions will be deployed")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Tanzu extensions  deploy is deactivated, no extensions will be deployed",
                        "ERROR_CODE": 200
                    }
                    return json.dumps(d), 200

                if len(logginglistOfExtention) > 1:
                    logger.info("User can only enable one logging extension at a once, please select only one.")
                    d = {
                        "responseType": "ERROR",
                        "msg": "User can only enable one logging extension at a once, please select only one.",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500

                if Tkg_version.TKG_VERSION == "1.5":
                    for extn in logginglistOfExtention:
                        status = self.extension_obj.deploy(extn)
                        if status[1] == 200:
                            logger.info("Successfully deployed " + str(logginglistOfExtention))
                        elif status[1] == 299:
                            logger.info(extn + " is not deployed, but is enabled in deployment json file...hence skipping upgrade")
                        else:
                            logger.info("Failed to deploy extension " + str(status[0]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to deploy extension " + str(status[0]),
                                "ERROR_CODE": 500
                            }
                            return json.dumps(d), 500
                    
                else:
                    logger.info("Unsupported TKG version")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Unsupported TKG version",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
               
                monitoringListOfExtention = []
                if checkPromethusEnabled(self.jsonspec):
                    monitoringListOfExtention.append(Tkg_Extention_names.PROMETHEUS)
                    monitoringListOfExtention.append(Tkg_Extention_names.GRAFANA)
                if len(monitoringListOfExtention) == 0:
                    logger.info("No monitoring extension to deploy")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "No extension to deploy ",
                        "ERROR_CODE": 200
                    }
                    return json.dumps(d), 200
                if Tkg_version.TKG_VERSION == "1.5":
                    for extn in monitoringListOfExtention:
                        status = self.extension_obj.deploy(extn)

                        if status[1] == 200:
                            logger.info("Successfully deployed " + str(monitoringListOfExtention))
                        elif status[1] == 299:
                            logger.info(extn + " is not deployed, but is enabled in deployment json file...hence skipping upgrade")
                        else:
                            logger.info("Failed to deploy extension "+str(status[0]))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to deploy extension "+str(status[0]),
                                "ERROR_CODE": 500
                            }
                            return json.dumps(d), 500
                    
                else:
                    logger.info("Unsupported TKG version")
                    d = {
                        "responseType": "ERROR",
                        "msg": "Unsupported TKG version",
                        "ERROR_CODE": 500
                    }
                    return json.dumps(d), 500
                    
                
        except Exception as e:
            logger.error("Failed to deploy the extensions " + str(e))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy the extensions " + str(e),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
