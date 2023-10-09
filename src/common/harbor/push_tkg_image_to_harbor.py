# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause.

import base64
import os
import time
from http import HTTPStatus
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from common.operation.ShellHelper import grabPipeOutput, runProcess, runShellCommandAndReturnOutputAsList
from common.util.harbor_utils import HarborConstants, HarborUtils
from common.util.request_api_util import RequestApiUtil

harbor = Blueprint("harbor", __name__, static_folder="harbor")


@harbor.route("/api/tanzu/harbor", methods=["POST"])
def harbor_push():
    try:
        harbor_utils = HarborUtils()
        repo_name = request.get_json(force=True)["repo_name"]
        tkg_binaries_path = request.get_json(force=True)["tkg_binaries"]
        if harbor_utils.is_harbor_selected:
            fqdn = harbor_utils.harbor_fqdn
            base = harbor_utils.harbor_address
            repository = f"{base}/{repo_name}"
            repo_username = harbor_utils.harbor_repo_username
            repo_password = harbor_utils.harbor_repo_password
            status, message = harbor_utils.create_harbor_project()
            if status is None:
                current_app.logger.error(str(message))
                response = RequestApiUtil.create_json_object(str(message), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            current_app.logger.info("Logging in to docker")
            list_command = ["docker", "login", repository, "-u", repo_username, "-p", repo_password]
            sta = runShellCommandAndReturnOutputAsList(list_command)
            if sta[1] != 0:
                current_app.logger.error("Docker login failed " + str(sta[0]))
                response = RequestApiUtil.create_json_object(
                    "Docker login failed " + str(sta[0]), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            current_app.logger.info("Docker login success")
            status1, message = harbor_utils.check_repository_count()
            if status1 == "NOT_FOUND":
                current_app.logger.error(str(message))
                response = RequestApiUtil.create_json_object(str(message), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            elif status1 == "Partial":
                current_app.logger.error(str(message))
                response = RequestApiUtil.create_json_object(str(message), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            elif status1 == "Success":
                current_app.logger.info(str(message))
                response = RequestApiUtil.create_json_object(str(message), "SUCCESS", HTTPStatus.OK)
                return response, HTTPStatus.OK
            if os.path.exists(tkg_binaries_path):
                current_app.logger.info(f"All binaries are present at the location {tkg_binaries_path}")
            else:
                msg = f"Tanzu image package is not present at location {tkg_binaries_path}"
                response = RequestApiUtil.create_json_object(msg, "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR)
                return response, 500
            tanzu_extract = harbor_utils.tanzu_extract_folder
            tools_location = "/opt/vmware/arcas/tools"
            rm_cmd = ["rm", "-rf ", tanzu_extract]
            runShellCommandAndReturnOutputAsList(rm_cmd)
            tar_command = ["tar", "-xvf", tkg_binaries_path, "--directory", tools_location]
            if not os.path.exists(tanzu_extract):
                runShellCommandAndReturnOutputAsList(tar_command)
            tanzu_extract = harbor_utils.tanzu_extract_folder
            down_path = HarborConstants.FROM_TAR_YAML_FILE
            gen_path = HarborConstants.CER_GEN_PATH
            if os.path.exists(down_path):
                os.system("rm -rf " + tanzu_extract + "publish-images-fromtar.yaml")
                os.system("cp " + down_path + " " + tanzu_extract)
            if os.path.exists(gen_path):
                os.system("cp " + gen_path + " " + tanzu_extract)
            os.system(f"chmod +x {tanzu_extract}gen.sh")
            current_app.logger.info("Adding certificate for harbor")
            file_path = "/harbor_storage/cert/" + fqdn + ".crt"
            count = 0
            found = False
            while count < 60:
                if os.path.exists(file_path):
                    found = True
                    break
                else:
                    current_app.logger.info(
                        "Cert  file not found wating " + file_path + "  file to be available, "
                        " waited for " + str(count * 30) + "s, retrying"
                    )
                time.sleep(30)
                count = count + 1
            if found:
                current_app.logger.info("Found file after " + str(count * 30) + "s")
            else:
                response = RequestApiUtil.create_json_object(
                    "Certificate file not found in current directory", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            repo_cert = Path(file_path).read_text()
            base64_bytes = base64.b64encode(repo_cert.encode("utf-8"))
            root_ca_data_base64 = str(base64_bytes, "utf-8")
            push = ["sh", f"{tanzu_extract}gen.sh", root_ca_data_base64]
            push_harbor = runShellCommandAndReturnOutputAsList(push)
            if push_harbor[1] != 0:
                response = RequestApiUtil.create_json_object(
                    "Failed to generate harbor certificate " + str(push_harbor[0]),
                    "ERROR",
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            os.system("cp /tmp/cacrtbase64d.crt .")
            if not os.path.exists("cacrtbase64d.crt"):
                response = RequestApiUtil.create_json_object(
                    "Certificate file not found in current directory", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR
            current_app.logger.info("Pushing images to harbor")
            os.environ["HOME"] = "/root"
            os.putenv("TANZU_CLI_CEIP_OPT_IN_PROMPT_ANSWER", "No")
            push = [
                "tanzu",
                "isolated-cluster",
                "upload-bundle",
                "--source-directory",
                tanzu_extract,
                "--destination-repo",
                repository,
                "--ca-certificate",
                "cacrtbase64d.crt",
            ]
            install_plugin = [
                "tanzu",
                "plugin",
                "upload-bundle",
                "--tar",
                tools_location + "/plugin_bundle1.tar.gz",
                "--to-repo",
                base + "/" + HarborConstants.HARBOR_PROJECT_NAME + "/tanzu-cli/plugin",
            ]
            cert_add = ["tanzu", "config", "cert", "add", "--host", base, "--skip-cert-verify", "true"]
            update_plugin_path = [
                "tanzu",
                "plugin",
                "source",
                "update",
                "default",
                "--uri",
                base + "/tanzu/tanzu-cli/plugin/plugin-inventory:latest",
            ]
            try:
                runProcess(push)
                runProcess(cert_add)
                runProcess(install_plugin)
                runProcess(update_plugin_path)
            except Exception as e:
                current_app.logger.error("Harbor image push failed " + str(e))
                response = RequestApiUtil.create_json_object(
                    "Harbor image push failed " + str(e), "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
                )
                return response, HTTPStatus.INTERNAL_SERVER_ERROR

            current_app.logger.info("Successfully Pushed images to harbor")
            msg = "Harbor image pushed successfully"
        else:
            current_app.logger.info("Installation of harbor is not opted, skipping pushing image to habor")
            msg = "Installation of harbor is not opted, skipping pushing image to habor"
    except Exception as ex:
        response = RequestApiUtil.create_json_object(
            str(ex) + " Failed Harbor image push", "ERROR", HTTPStatus.INTERNAL_SERVER_ERROR
        )
        return response, HTTPStatus.INTERNAL_SERVER_ERROR
    response = RequestApiUtil.create_json_object(msg, "SUCCESS", HTTPStatus.OK)
    return response, HTTPStatus.OK


@harbor.route("/api/tanzu/harbor_pre_load_status", methods=["GET"])
def harbor_preload_status():
    harbor_util = HarborUtils()
    tanzu_extract = harbor_util.tanzu_extract_folder
    expected_tar_count = 139
    expected_repo_count = 132
    main_command = ["ls", tanzu_extract]
    sub_command = ["wc", "-l"]
    cert_state = grabPipeOutput(main_command, sub_command)
    repo_count = harbor_util.get_repo_count()
    current_tar_count = int(cert_state[0])
    current_repo_count = int(repo_count[0])
    total = expected_repo_count + expected_tar_count
    percentage = ((current_tar_count + current_repo_count) / total) * 100
    response_body = {"responseType": "SUCCESS", "msg": "", "percentage": percentage, "STATUS_CODE": HTTPStatus.OK}
    return jsonify(response_body), HTTPStatus.OK
