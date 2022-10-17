#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os, sys
import re
import traceback
import json
from util import cmd_runner
from pathlib import Path
import base64
import logging
import ipaddress
import time

from util.logger_helper import LoggerHelper
from util.ShellHelper import  runShellCommandAndReturnOutputAsList, verifyPodsAreRunning, grabPipeOutput
from constants.constants import Paths, ControllerLocation, KubernetesOva, MarketPlaceUrl, VrfType, \
    RegexPattern, AppName, Env
from util.common_utils import switchToManagementContext, switchToContext
from util.tkg_util import TkgUtil

from util.logger_helper import LoggerHelper, log

logger = LoggerHelper.get_logger(Path(__file__).stem)


def checkEnableIdentityManagement(env, jsonspec):
    try:
        if not TkgUtil.isEnvTkgs_ns(jsonspec) and not TkgUtil.isEnvTkgs_wcp(jsonspec):
            if env == Env.VMC:
                idm = jsonspec["componentSpec"]["identityManagementSpec"]["identityManagementType"]
            elif env == Env.VSPHERE or env == Env.VCF:
                idm = jsonspec["tkgComponentSpec"]["identityManagementSpec"][
                    "identityManagementType"]
            if (idm.lower() == "oidc") or (idm.lower() == "ldap"):
                return True
            else:
                return False
        else:
            return False
    except Exception:
        return False


def checkPinnipedInstalled():
    main_command = ["tanzu", "package", "installed", "list", "-A"]
    sub_command = ["grep", AppName.PINNIPED]
    command_pinniped = grabPipeOutput(main_command, sub_command)
    if not verifyPodsAreRunning(AppName.PINNIPED, command_pinniped[0], RegexPattern.RECONCILE_SUCCEEDED):
        count_pinniped = 0
        found = False
        command_status_pinniped = grabPipeOutput(main_command, sub_command)
        while not verifyPodsAreRunning(AppName.PINNIPED, command_status_pinniped[0],
                                       RegexPattern.RECONCILE_SUCCEEDED) and count_pinniped < 20:
            command_status_pinniped = grabPipeOutput(main_command, sub_command)
            if verifyPodsAreRunning(AppName.PINNIPED, command_status_pinniped[0], RegexPattern.RECONCILE_SUCCEEDED):
                found = True
                break
            count_pinniped = count_pinniped + 1
            time.sleep(30)
            logger.info("Waited for  " + str(count_pinniped * 30) + "s, retrying.")
        if not found:
            logger.error(
                "Pinniped is not in RECONCILE SUCCEEDED state on waiting " + str(count_pinniped * 30))
            d = {
                "responseType": "ERROR",
                "msg": "Pinniped is not in RECONCILE SUCCEEDED state on waiting " + str(count_pinniped * 30),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    logger.info("Successfully validated Pinniped installation")
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully validated Pinniped installation",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200


def checkPinnipedServiceStatus():
    try:
        listOfCmd = ["kubectl", "get", "svc", "-n", "pinniped-supervisor"]
        output = runShellCommandAndReturnOutputAsList(listOfCmd)
        line1 = output[0][0].split()
        line2 = output[0][1].split()
        if str(line1[3]) == 'EXTERNAL-IP':
            try:
                ip = ipaddress.ip_address(str(line2[3]))
                logger.info("Successfully retrieved Load Balancers' External IP: " + str(line2[3]))
                logger.info(
                    "Update the callback URI with the Load Balancers' External IP: " + str(line2[3]))
                return "Load Balancers' External IP: " + str(line2[3]), 200
            except Exception as e:
                logger.error("Failed to retrieve Load Balancers' External IP")
                logger.error(str(e))
                return "Failed to retrieve Load Balancers' External IP", 500
        return "Failed to retrieve Load Balancers' External IP", 500
    except:
        return "Failed to retrieve Load Balancers' External IP", 500


def checkPinnipedDexServiceStatus():
    try:
        listOfCmd = ["kubectl", "get", "svc", "-n", "tanzu-system-auth"]
        output = runShellCommandAndReturnOutputAsList(listOfCmd)
        line1 = output[0][0].split()
        line2 = output[0][1].split()
        if str(line1[3]) == 'EXTERNAL-IP':
            try:
                ip = ipaddress.ip_address(str(line2[3]))
                logger.info("Successfully retrieved dexsvc Load Balancers' External IP: " + str(line2[3]))
                return "dexsvc Load Balancers' External IP: " + str(line2[3]), 200
            except Exception as e:
                logger.error(str(e))
                logger.error("Failed to retrieve dexsvc Load Balancers' External IP")
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to retrieve dexsvc Load Balancers' External IP",
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        return "Failed to retrieve dexsvc Load Balancers' External IP", 500
    except:
        return "Failed to retrieve dexsvc Load Balancers' External IP", 500


def createRbacUsers(clusterName, isMgmt, env, cluster_admin_users, admin_users, edit_users, view_users):
    try:
        if isMgmt:
            switch = switchToManagementContext(clusterName)
            if switch[1] != 200:
                logger.info(switch[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": switch[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        else:
            switch = switchToContext(clusterName, env=env)
            if switch[1] != 200:
                logger.info(switch[0].json['msg'])
                d = {
                    "responseType": "ERROR",
                    "msg": switch[0].json['msg'],
                    "ERROR_CODE": 500
                }
                return json.dumps(d), 500
        if isMgmt:
            exportCmd = ["tanzu", "management-cluster", "kubeconfig", "get",
                         clusterName, "--export-file",
                         Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig"]
        else:
            exportCmd = ["tanzu", "cluster", "kubeconfig", "get",
                         clusterName, "--export-file",
                         Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig"]

        output = runShellCommandAndReturnOutputAsList(exportCmd)
        if output[1] == 0:
            logger.info(
                "Exported kubeconfig at  " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig")
        else:
            logger.error(
                "Failed to export config file to " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig")
            logger.error(output[0])
            d = {
                "responseType": "ERROR",
                "msg": "Failed to export config file to " + Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig",
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        rbac_dict = dict()
        rbac_dict.update({"cluster-admin": cluster_admin_users})
        rbac_dict.update({"admin": admin_users})
        rbac_dict.update({"edit": edit_users})
        rbac_dict.update({"view": view_users})

        for key in rbac_dict:
            users = rbac_dict[key]
            if users:
                users_list = users.split(",")
                for username in users_list:
                    logger.info("Checking if Cluster Role binding exists for the user: " + username)
                    main_command = ["kubectl", "get", "clusterrolebindings"]
                    sub_command = ["grep", username + "-crb"]
                    output = grabPipeOutput(main_command, sub_command)
                    if output[1] == 0:
                        if output[0].__contains__(key):
                            logger.info(key + " role binding for user: " + username + " already exists!")
                            continue
                    logger.info("Creating Cluster Role binding for user: " + username)
                    listOfCmd = ["kubectl", "create", "clusterrolebinding", username + "-crb",
                                 "--clusterrole", key, "--user", username]
                    output = runShellCommandAndReturnOutputAsList(listOfCmd)
                    if output[1] == 0:
                        logger.info("Created RBAC for user: " + username + " SUCCESSFULLY")
                        logger.info("Kubeconfig file has been generated and stored at " +
                                                Paths.CLUSTER_PATH + clusterName + "/" + "crb-kubeconfig")
                    else:
                        logger.error("Failed to created Cluster Role Binding for user: " + username)
                        logger.error(output[0])
                        d = {
                            "responseType": "ERROR",
                            "msg": "Failed to created Cluster Role Binding for user: " + username,
                            "ERROR_CODE": 500
                        }
                        return json.dumps(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "Created RBAC successfully for all the provided users",
            "ERROR_CODE": 200
        }
        return json.dumps(d), 200

    except Exception as e:
        logger.info("Some error occurred while creating cluster role bindings")
        d = {
            "responseType": "ERROR",
            "msg": "Some error occurred while creating cluster role bindings",
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500