#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from constants.constants import ControllerLocation, Repo, AppName, RegexPattern, Constants, Paths
from pathlib import Path
import base64
from util.common_utils import installCertManagerAndContour, getVersionOfPackage, waitForGrepProcessWithoutChangeDir
import json
from util.logger_helper import LoggerHelper
import logging
from util.ShellHelper import grabPipeOutput, verifyPodsAreRunning, \
    runShellCommandAndReturnOutputAsList, runShellCommandAndReturnOutput
import time
import os
from workflows.cluster_common_workflow import ClusterCommonWorkflow
from util.cmd_runner import RunCmd
from util.file_helper import FileHelper
from util.cmd_helper import CmdHelper

logger = LoggerHelper.get_logger('common_utils')
logging.getLogger("paramiko").setLevel(logging.WARNING)


def certChanging(harborCertPath, harborCertKeyPath, harborPassword, host):
    os.system("chmod +x common/inject.sh")
    location = "harbor-data-values.yaml"

    if harborCertPath and harborCertKeyPath:
        harbor_cert = Path(harborCertPath).read_text()
        harbor_cert_key = Path(harborCertKeyPath).read_text()
        certContent = harbor_cert
        certKeyContent = harbor_cert_key
        command_harbor_change_host_password_cert = ["sh", "./common/inject.sh",
                                                    location,
                                                    harborPassword, host, certContent, certKeyContent]
        state_harbor_change_host_password_cert = runShellCommandAndReturnOutput(
            command_harbor_change_host_password_cert)
        if state_harbor_change_host_password_cert[1] == 500:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to change host, password and cert " + str(state_harbor_change_host_password_cert[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    else:
        command_harbor_change_host_password_cert = ["sh", "./common/inject.sh",
                                                    location,
                                                    harborPassword, host, "", ""]
        state_harbor_change_host_password_cert = runShellCommandAndReturnOutput(
            command_harbor_change_host_password_cert)
        if state_harbor_change_host_password_cert[1] == 500:
            d = {
                "responseType": "ERROR",
                "msg": "Failed to change host, password and cert " + str(state_harbor_change_host_password_cert[0]),
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Updated harbor data-values yaml",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200

def _update_harbor_data_values(remote_file, jsonspec, runconfig):
    rcmd = RunCmd()
    local_file = Paths.LOCAL_HARBOR_DATA_VALUES.format(root_dir=runconfig.root_dir)
    logger.info(f"Fetching and saving data values yml to {local_file}")
    rcmd.local_file_copy(remote_file, local_file)
    harbor_host = jsonspec['harborSpec']['harborFqdn']
    harbor_pass_enc = jsonspec['harborSpec']['harborPasswordBase64']
    sp_pass = CmdHelper.decode_base64(harbor_pass_enc)
    harbor_pass = ''.join(sp_pass)

    logger.info(f"Updating admin password in local copy of harbor-data-values.yaml")
    # Replacing string with pattern matching instead of loading yaml because comments
    # in yaml file will be lost during boxing/unboxing of yaml data
    replacement_list = [(Constants.HARBOR_ADMIN_PASSWORD_TOKEN,
                         Constants.HARBOR_ADMIN_PASSWORD_SUB.format(password=harbor_pass)),
                        (Constants.HARBOR_HOSTNAME_TOKEN,
                         Constants.HARBOR_HOSTNAME_SUB.format(hostname=harbor_host))]
    logger.debug(f"Replacement spec: {replacement_list}")
    FileHelper.replace_pattern(src=local_file, target=local_file, pattern_replacement_list=replacement_list)
    logger.info(f"Updating harbor-data-values.yaml on bootstrap VM")
    rcmd.local_file_copy(local_file, remote_file)

def _install_harbor_package(jsonspec, cluster_name, runconfig):
    common_workflow = ClusterCommonWorkflow()
    version = common_workflow.get_available_package_version(cluster_name=cluster_name,
                                                            package=Constants.HARBOR_PACKAGE,
                                                            name=Constants.HARBOR_DISPLAY_NAME)
    logger.info("Generating Harbor configuration template")
    common_workflow.generate_spec_template(name=Constants.HARBOR_APP, package=Constants.HARBOR_PACKAGE,
                                                        version=version, template_path=Paths.REMOTE_HARBOR_DATA_VALUES,
                                                        on_docker=False)
    logger.info("Updating data values based on inputs")
    _update_harbor_data_values(Paths.REMOTE_HARBOR_DATA_VALUES, jsonspec, runconfig)
    logger.info("Removing comments from harbor-data-values.yaml")
    rcmd = RunCmd()
    rcmd.run_cmd_only(f"yq -i eval '... comments=\"\"' {Paths.REMOTE_HARBOR_DATA_VALUES}")
    common_workflow.install_package(cluster_name=cluster_name, package=Constants.HARBOR_PACKAGE,
                                    namespace="Tekton",
                                    name=Constants.HARBOR_APP, version=version,
                                    values=Paths.REMOTE_HARBOR_DATA_VALUES)
    podRunninng = ["tanzu", "cluster", "list"]
    command_status = rcmd.runShellCommandAndReturnOutputAsList(podRunninng)
    if command_status[1] != 0:
        logger.error(
            "Failed to check pods are running " + str(command_status[0]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to check pods are running " + str(command_status[0]),
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500
    logger.info('Harbor installation complete')
    return "SUCCESS", 200

def deployExtentions(jsonspec, runconfig):

    aviVersion = ControllerLocation.VSPHERE_AVI_VERSION
    shared_cluster_name = jsonspec['tkgComponentSpec']['tkgMgmtComponents']['tkgSharedserviceClusterName']
    str_enc = str(jsonspec['harborSpec']['harborPasswordBase64'])
    base64_bytes = str_enc.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password = enc_bytes.decode('ascii').rstrip("\n")
    harborPassword = password
    host = jsonspec['harborSpec']['harborFqdn']
    harborCertPath = jsonspec['harborSpec']['harborCertPath']
    harborCertKeyPath = jsonspec['harborSpec']['harborCertKeyPath']
    checkHarborEnabled = jsonspec['harborSpec']['enableHarborExtension']
    if str(checkHarborEnabled).lower() == "true":
        isHarborEnabled = True
    else:
        isHarborEnabled = False
    repo_address = Repo.PUBLIC_REPO
    if not repo_address.endswith("/"):
        repo_address = repo_address + "/"
    repo_address = repo_address.replace("https://", "").replace("http://", "")
    logger.info('Setting up Cert and Contour...')
    cert_ext_status = installCertManagerAndContour(jsonspec, shared_cluster_name, repo_address)
    if cert_ext_status[1] != 200:
        logger.error(cert_ext_status[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": cert_ext_status[0].json['msg'],
            "ERROR_CODE": 500
        }
        return json.dumps(d), 500

    service = "all"
    if isHarborEnabled:
        logger.info('Setting up Harbor...')
        harbor_status = _install_harbor_package(jsonspec, shared_cluster_name, runconfig)
        if harbor_status[1] != 200:
            logger.error("Error setting up Harbor registry...")
            d = {
                "responseType": "ERROR",
                "msg": cert_ext_status[0].json['msg'],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
    logger.info("Configured all extentions successfully")
    d = {
        "responseType": "SUCCESS",
        "msg": "Configured all extentions successfully",
        "ERROR_CODE": 200
    }
    return json.dumps(d), 200
