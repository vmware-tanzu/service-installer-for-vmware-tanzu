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
from constants.constants import Tkg_version, Tkg_Extention_names
from util.extensions_helper import checkTanzuExtensionEnabled, check_fluent_bit_splunk_endpoint_endpoint_enabled, \
    check_fluent_bit_kafka_endpoint_endpoint_enabled, check_fluent_bit_syslog_endpoint_enabled, \
    check_fluent_bit_elastic_search_endpoint_enabled, check_fluent_bit_http_endpoint_enabled, checkPromethusEnabled
    
from constants.constants import Tkg_Extention_names, Paths 
from util.common_utils import checkenv
from util.tkg_util import TkgUtil

logger = LoggerHelper.get_logger(name='ra_deploy_ext_workflow.py')


class RaDeployExtWorkflow:

    def __init__(self, run_config: RunConfig) -> None:
        self.run_config = run_config
        self.version = None
        self.jsonpath = None
        self.tkg_type = self.run_config.desired_state.version.keys()
        if "tkgs" in self.tkg_type:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_WCP_MASTER_SPEC_PATH)
            #self.ns_jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_NS_MASTER_SPEC_PATH)
        elif "tkgm" in self.tkg_type:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        else:
            raise Exception(f"Could not find supported TKG version: {self.tkg_type}")

        with open(self.jsonpath) as f:
            self.jsonspec = json.load(f)

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)
        self.isEnvTkgs_wcp = TkgUtil.isEnvTkgs_wcp(self.jsonspec)
        self.isEnvTkgs_ns = TkgUtil.isEnvTkgs_ns(self.jsonspec)

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
            env = "vsphere"
            if self.isEnvTkgs_ns:
                result = deploy_tkgs_extensions()
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
                logginglistOfExtention = []
                if checkTanzuExtensionEnabled(self.jsonspec):
                    if check_fluent_bit_splunk_endpoint_endpoint_enabled():
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_SPLUNK)
                    if check_fluent_bit_http_endpoint_enabled():
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_HTTP)
                    if check_fluent_bit_syslog_endpoint_enabled():
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_SYSLOG)
                    if check_fluent_bit_elastic_search_endpoint_enabled():
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_ELASTIC)
                    if check_fluent_bit_kafka_endpoint_endpoint_enabled():
                        logginglistOfExtention.append(Tkg_Extention_names.FLUENT_BIT_KAFKA)
                        
                else:
                    logger.info("Tanzu logging extensions deploy is disabled, no extensions will be deployed")
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Tanzu extensions  deploy is disabled, no extensions will be deployed",
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
                        status = deploy_tkg_extensions.deploy(extn, self.jsonspec)
                        if status[1] != 200:
                            logger.info("Failed to deploy extension "+str(status[0].json['msg']))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to deploy extension "+str(status[0].json['msg']),
                                "ERROR_CODE": 500
                            }
                            return json.dumps(d), 500

                    logger.info("Successfully deployed "+str(logginglistOfExtention))
                    
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
                        status = deploy_tkg_extensions.deploy(extn, self.jsonspec)
                        if status[1] != 200:
                            logger.info("Failed to deploy extension "+str(status[0].json['msg']))
                            d = {
                                "responseType": "ERROR",
                                "msg": "Failed to deploy extension "+str(status[0].json['msg']),
                                "ERROR_CODE": 500
                            }
                            return json.dumps(d), 500
                    logger.info("Successfully deployed "+str(monitoringListOfExtention))
                    d = {
                        "responseType": "SUCCESS",
                        "msg": "Successfully deployed logging extension "+str(monitoringListOfExtention),
                        "ERROR_CODE": 200
                    }
                    return json.dumps(d), 200
                    
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
