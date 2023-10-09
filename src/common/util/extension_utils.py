# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import os
import time
from pathlib import Path

from flask import current_app, jsonify, request

from common.common_utilities import (
    checkAirGappedIsEnabled,
    createOverlayYaml,
    envCheck,
    grabPipeOutput,
    installCertManagerAndContour,
    preChecks,
    runProcess,
    runShellCommandAndReturnOutput,
    runShellCommandAndReturnOutputAsList,
    verifyPodsAreRunning,
    waitForGrepProcessWithoutChangeDir,
)
from common.operation.constants import AppName, Env, Paths, RegexPattern, Repo
from common.util.common_utils import CommonUtils
from common.util.tanzu_util import TanzuUtil

__author__ = "Pooja Deshmukh"


class ExtensionUtils:
    def __init__(self, config):
        self.run_config = config

    def deploy_shared_extensions(self):
        pre = preChecks()
        if pre[1] != 200:
            current_app.logger.error(pre[0].json["msg"])
            d = {"responseType": "ERROR", "msg": pre[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
        env = envCheck()
        if env[1] != 200:
            current_app.logger.error("Wrong env provided " + env[0])
            d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
            return jsonify(d), 500
        env = env[0]
        spec_json = request.get_json(force=True)
        spec_obj = CommonUtils.get_spec_obj(env)
        spec: spec_obj = spec_obj.parse_obj(spec_json)
        TanzuUtil(env=env, spec=spec)
        service = request.args.get("service", default="all", type=str)
        if env == Env.VMC:
            shared_cluster_name = spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterName
            str_enc = str(spec.componentSpec.harborSpec.harborPasswordBase64)
            base64_bytes = str_enc.encode("ascii")
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode("ascii").rstrip("\n")
            harborPassword = password
            host = spec.componentSpec.harborSpec.harborFqdn
            harborCertPath = spec.componentSpec.harborSpec.harborCertPath
            harborCertKeyPath = spec.componentSpec.harborSpec.harborCertKeyPath
            isHarborEnabled = True
        else:
            if env == Env.VCF:
                shared_cluster_name = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceClusterName
            else:
                shared_cluster_name = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceClusterName
            str_enc = str(spec.harborSpec.harborPasswordBase64)
            base64_bytes = str_enc.encode("ascii")
            enc_bytes = base64.b64decode(base64_bytes)
            password = enc_bytes.decode("ascii").rstrip("\n")
            harborPassword = password
            host = spec.harborSpec.harborFqdn
            harborCertPath = spec.harborSpec.harborCertPath
            harborCertKeyPath = spec.harborSpec.harborCertKeyPath
            checkHarborEnabled = spec.harborSpec.enableHarborExtension
            if str(checkHarborEnabled).lower() == "true":
                isHarborEnabled = True
            else:
                isHarborEnabled = False
        if checkAirGappedIsEnabled(env):
            repo_address = str(spec.envSpec.customRepositorySpec.tkgCustomImageRepository)
        else:
            repo_address = Repo.PUBLIC_REPO
        if not repo_address.endswith("/"):
            repo_address = repo_address + "/"
        repo_address = repo_address.replace("https://", "").replace("http://", "")
        cert_ext_status = installCertManagerAndContour(env, shared_cluster_name, repo_address, service)
        if cert_ext_status[1] != 200:
            current_app.logger.error(cert_ext_status[0].json["msg"])
            d = {"responseType": "ERROR", "msg": cert_ext_status[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500

        if not isHarborEnabled:
            service = "disable"
        if service == "registry" or service == "all":
            if not host or not harborPassword:
                current_app.logger.error(
                    "Harbor FQDN and password are mandatory for harbor deployment." " Please provide both the details"
                )
                d = {
                    "responseType": "ERROR",
                    "msg": "Harbor FQDN and password are mandatory for harbor deployment. Please provide both the details",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Validating if harbor is running")
            state = self.install_harbor(
                repo_address, harborCertPath, harborCertKeyPath, harborPassword, host, shared_cluster_name
            )
            if state[1] != 200:
                current_app.logger.error(state[0].json["msg"])
                d = {"responseType": "ERROR", "msg": state[0].json["msg"], "STATUS_CODE": 500}
                return jsonify(d), 500
        current_app.logger.info("Configured all extensions successfully")
        d = {"responseType": "SUCCESS", "msg": "Configured all extensions successfully", "STATUS_CODE": 200}
        return jsonify(d), 200

    def install_harbor(self, repo_address, harborCertPath, harborCertKeyPath, harborPassword, host, clusterName):
        clusterName_path = os.path.join(Paths.CLUSTER_PATH, clusterName)
        main_command = ["tanzu", "package", "installed", "list", "-A"]
        sub_command = ["grep", AppName.HARBOR]
        out = grabPipeOutput(main_command, sub_command)
        if not verifyPodsAreRunning(AppName.HARBOR, out[0], RegexPattern.RECONCILE_SUCCEEDED):
            timer = 0
            current_app.logger.info("Validating if contour and cert-manager is running")
            command = ["tanzu", "package", "installed", "list", "-A"]
            status = runShellCommandAndReturnOutputAsList(command)
            verify_contour = False
            verify_cert_manager = False
            while timer < 600:
                if verify_contour or verifyPodsAreRunning(AppName.CONTOUR, status[0], RegexPattern.RECONCILE_SUCCEEDED):
                    current_app.logger.info("Contour is running")
                    verify_contour = True
                if verify_cert_manager or verifyPodsAreRunning(
                    AppName.CERT_MANAGER, status[0], RegexPattern.RECONCILE_SUCCEEDED
                ):
                    verify_cert_manager = True
                    current_app.logger.info("Cert Manager is running")

                if verify_contour and verify_cert_manager:
                    break
                else:
                    timer = timer + 30
                    time.sleep(30)
                    status = runShellCommandAndReturnOutputAsList(command)
                    current_app.logger.info(
                        "Waited for " + str(timer) + "s, retrying for contour and cert manager to be running"
                    )
            if not verify_contour:
                current_app.logger.error("Contour is not running")
                d = {"responseType": "ERROR", "msg": "Contour is not running ", "STATUS_CODE": 500}
                return jsonify(d), 500
            if not verify_cert_manager:
                current_app.logger.error("Cert manager is not running")
                d = {"responseType": "ERROR", "msg": "Cert manager is not running ", "STATUS_CODE": 500}
                return jsonify(d), 500
            state = TanzuUtil.get_version_of_package("harbor.tanzu.vmware.com")
            if state is None:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get Version of package harbor.tanzu.vmware.com",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Deploying harbor")
            current_app.logger.info("Harbor version " + state)
            get_url_command = [
                "kubectl",
                "-n",
                "tkg-system",
                "get",
                "packages",
                "harbor.tanzu.vmware.com." + state,
                "-o",
                "jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}'",
            ]
            current_app.logger.info("Getting harbor url")
            status = runShellCommandAndReturnOutputAsList(get_url_command)
            if status[1] != 0:
                current_app.logger.error("Failed to get harbor image url " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get harbor image url " + str(status[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            current_app.logger.info("Got harbor url " + str(status[0][0]).replace("'", ""))
            my_file = Path("./cacrtbase64d.crt")
            if my_file.exists():
                pull = [
                    "imgpkg",
                    "pull",
                    "-b",
                    str(status[0][0]).replace("'", ""),
                    "-o",
                    "/tmp/harbor-package",
                    "--registry-ca-cert-path",
                    "./cacrtbase64d.crt",
                ]
            else:
                pull = ["imgpkg", "pull", "-b", str(status[0][0]).replace("'", ""), "-o", "/tmp/harbor-package"]
            status = runShellCommandAndReturnOutputAsList(pull)
            if status[1] != 0:
                current_app.logger.error("Failed to pull harbor packages " + str(status[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to get harbor image url " + str(status[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            rm_cmd = ["rm", "-rf ", clusterName_path, "/harbor-data-values.yaml"]
            runShellCommandAndReturnOutputAsList(rm_cmd)
            cp_cmd = ["cp", "/tmp/harbor-package/config/values.yaml", clusterName_path + "/harbor-data-values.yaml"]
            runShellCommandAndReturnOutputAsList(cp_cmd)
            command_harbor_genrate_psswd = [
                "sh",
                "/tmp/harbor-package/config/scripts/generate-passwords.sh",
                clusterName_path + "/harbor-data-values.yaml",
            ]
            state_harbor_genrate_psswd = runShellCommandAndReturnOutputAsList(command_harbor_genrate_psswd)
            if state_harbor_genrate_psswd[1] == 500:
                current_app.logger.error("Failed to generate password " + str(state_harbor_genrate_psswd[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to generate password " + str(state_harbor_genrate_psswd[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            cer = self.harbor_cert_change(harborCertPath, harborCertKeyPath, harborPassword, host, clusterName)
            if cer[1] != 200:
                current_app.logger.error(cer[0].json["msg"])
                d = {"responseType": "ERROR", "msg": cer[0].json["msg"], "STATUS_CODE": 500}
                return jsonify(d), 500

            chmod_cmd = ["chmod", "+x", "common/injectValue.sh"]
            runShellCommandAndReturnOutputAsList(chmod_cmd)
            command = ["sh", "./common/injectValue.sh", clusterName_path + "/harbor-data-values.yaml", "remove"]
            runShellCommandAndReturnOutputAsList(command)
            # Changed for glasgow
            harbor_ns = "tanzu-system-registry"
            extra_ns = "tanzu-harbor-registry"
            verify_ns = ["kubectl", "get", "ns"]
            out = runShellCommandAndReturnOutputAsList(verify_ns)
            for item in out[0]:
                if harbor_ns in item:
                    break
            else:
                create_ns_cmd = ["kubectl", "create", "ns", harbor_ns]
                runProcess(create_ns_cmd)

            out = runShellCommandAndReturnOutputAsList(verify_ns)
            for item in out[0]:
                if extra_ns in item:
                    break
            else:
                create_ns_cmd = ["kubectl", "create", "ns", extra_ns]
                runProcess(create_ns_cmd)

            command = [
                "tanzu",
                "package",
                "install",
                "harbor",
                "--package",
                "harbor.tanzu.vmware.com",
                "--version",
                state,
                "--values-file",
                clusterName_path + "/harbor-data-values.yaml",
                "--namespace",
                extra_ns,
            ]
            runShellCommandAndReturnOutputAsList(command)
            createOverlayYaml(repo_address, clusterName)
            cp_cmd = ["cp", "./common/harbor-overlay.yaml", Paths.CLUSTER_PATH]
            runShellCommandAndReturnOutputAsList(cp_cmd)
            state = waitForGrepProcessWithoutChangeDir(
                main_command, sub_command, AppName.HARBOR, RegexPattern.RECONCILE_SUCCEEDED
            )
            if state[1] != 200:
                current_app.logger.error(state[0].json["msg"])
                d = {"responseType": "ERROR", "msg": state[0].json["msg"], "STATUS_CODE": 500}
                return jsonify(d), 500
            current_app.logger.info("Deployed harbor successfully")
            d = {"responseType": "SUCCESS", "msg": "Deployed harbor successfully", "STATUS_CODE": 200}
            return jsonify(d), 200
        else:
            current_app.logger.info("Harbor is already deployed and running")
            d = {"responseType": "SUCCESS", "msg": "Harbor is already deployed and running", "STATUS_CODE": 200}
            return jsonify(d), 200

    def harbor_cert_change(self, harborCertPath, harborCertKeyPath, harborPassword, host, clusterName):
        os.system("chmod +x common/inject.sh")
        location = Paths.CLUSTER_PATH + clusterName + "/harbor-data-values.yaml"
        if harborCertPath and harborCertKeyPath:
            harbor_cert = Path(harborCertPath).read_text()
            harbor_cert_key = Path(harborCertKeyPath).read_text()
            certContent = harbor_cert
            certKeyContent = harbor_cert_key
            command_harbor_change_host_password_cert = [
                "sh",
                "./common/inject.sh",
                location,
                harborPassword,
                host,
                certContent,
                certKeyContent,
            ]
            state_harbor_change_host_password_cert = runShellCommandAndReturnOutput(
                command_harbor_change_host_password_cert
            )
            if state_harbor_change_host_password_cert[1] == 500:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to change host, password and cert " + str(state_harbor_change_host_password_cert[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        else:
            command_harbor_change_host_password_cert = [
                "sh",
                "./common/inject.sh",
                location,
                harborPassword,
                host,
                "",
                "",
            ]
            state_harbor_change_host_password_cert = runShellCommandAndReturnOutput(
                command_harbor_change_host_password_cert
            )
            if state_harbor_change_host_password_cert[1] == 500:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to change host, password and cert " + str(state_harbor_change_host_password_cert[0]),
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
        d = {"responseType": "SUCCESS", "msg": "Updated harbor data-values yaml", "STATUS_CODE": 200}
        return jsonify(d), 200
