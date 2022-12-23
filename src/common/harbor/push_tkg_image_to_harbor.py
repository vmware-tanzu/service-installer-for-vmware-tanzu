# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause.

import sys
import os
import base64
import requests
import json

from flask import Blueprint, current_app, jsonify, request
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList, grabPipeOutput
from pathlib import Path

sys.path.append(".../")

harbor = Blueprint("harbor", __name__, static_folder="harbor")


@harbor.route('/api/tanzu/harbor', methods=['POST'])
def harbor_push():
    try:
        repo_name = request.get_json(force=True)['repo_name']
        tkg_binaries_path = request.get_json(force=True)['tkg_binaries']
        with open(r'/opt/vmware/arcas/tools/isharbor.txt', 'r') as file:
            isharbor_requested = file.read()
        if isharbor_requested.strip("\n").strip("\r").strip() == "true":
            with open(r'/opt/vmware/arcas/tools/harbor_fqdn.txt', 'r') as file:
                data = file.read()
            data = data.strip("\n").strip("\r").strip()
            fqdn = data
            base = data + ":9443"
            repository = f"{base}/{repo_name}"
            repo_username = "admin"
            file = "/etc/.secrets/root_password"
            repo_password = Path(file).read_text().strip("\n")
            status, message = create_harbor_project(base, repo_username, repo_password, repo_name)
            if status is None:
                current_app.logger.error(str(message))
                d = {
                    "responseType": "ERROR",
                    "msg": str(message),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Logging in to docker")
            list_command = ["docker", "login", repository, "-u", repo_username, "-p", repo_password]
            sta = runShellCommandAndReturnOutputAsList(list_command)
            if sta[1] != 0:
                current_app.logger.error("Docker login failed " + str(sta[0]))
                d = {
                    "responseType": "ERROR",
                    "msg": "Docker login failed " + str(sta[0]),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info("Docker login success")
            status1, message = check_repository_count(base, repo_username, repo_password, repo_name)
            if status1 == "NOT_FOUND":
                current_app.logger.error(str(message))
                d = {
                    "responseType": "ERROR",
                    "msg": str(message),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            elif status1 == "Partial":
                current_app.logger.error(str(message))
                d = {
                    "responseType": "ERROR",
                    "msg": str(message),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            elif status1 == "Success":
                current_app.logger.info(str(message))
                d = {
                    "responseType": "SUCCESS",
                    "msg": str(message),
                    "STATUS_CODE": 200
                }
                return jsonify(d), 200
            if os.path.exists(tkg_binaries_path):
                current_app.logger.info(f"All binaries are present at the location {tkg_binaries_path}")
            else:
                response_body = {
                    "responseType": "ERROR",
                    "msg": f"Tanzu image package is not present at location {tkg_binaries_path}",
                    "STATUS_CODE": 500
                }
                return jsonify(response_body), 500
            tanzu_extract = "/opt/vmware/arcas/tools/tanzu/"
            tools_location = "/opt/vmware/arcas/tools"
            os.system("rm -rf "+tanzu_extract)
            if not os.path.exists(tanzu_extract):
                os.system("tar -xvf " + tkg_binaries_path + " --directory " + tools_location)
            down_path = "/opt/vmware/arcas/tools/download.sh"
            list_path = "/opt/vmware/arcas/tools/tanzu/image-list-fromtar"
            search_text = "repo_harbor_with_port"
            repo_text = "repo_name"
            replace_text = base
            tanzu_extract = "/opt/vmware/arcas/tools/tanzu/"
            with open(list_path, 'r') as file:
                data = file.read()
                data = data.replace(search_text, replace_text)
                data = data.replace(repo_text, repo_name)
            with open(list_path, 'w') as file:
                file.write(data)
            gen_path = "/opt/vmware/arcas/tools/gen.sh"
            if os.path.exists(down_path):
                os.system("cp " + down_path + " " + tanzu_extract)
            if os.path.exists(gen_path):
                os.system("cp " + gen_path + " " + tanzu_extract)
            os.system(f"chmod +x {tanzu_extract}download.sh")
            os.system(f"chmod +x {tanzu_extract}gen.sh")
            os.system("cp /tmp/cacrtbase64d.crt .")
            current_app.logger.info("Adding certificate for harbor")
            file_path = "/harbor_storage/cert/" + fqdn + ".crt"
            repo_cert = Path(file_path).read_text()
            base64_bytes = base64.b64encode(repo_cert.encode("utf-8"))
            root_ca_data_base64 = str(base64_bytes, "utf-8")
            push = ["sh", f"{tanzu_extract}gen.sh", root_ca_data_base64]
            push_harbor = runShellCommandAndReturnOutputAsList(push)
            if push_harbor[1] != 0:
                response_body = {
                    "responseType": "ERROR",
                    "msg": "Failed to generate harbor certificate " + str(push_harbor[0]),
                    "STATUS_CODE": 500
                }
                return jsonify(response_body), 500
            os.system(f"cp {list_path} {tanzu_extract}")
            current_app.logger.info("Pushing images to harbor")
            push = os.system(f"cd {tanzu_extract} && ./download.sh {tanzu_extract}/image-list-fromtar")
            if push != 0:
                response_body = {
                    "responseType": "ERROR",
                    "msg": "Harbor image push failed ",
                    "STATUS_CODE": 500
                }
                return jsonify(response_body), 500
            current_app.logger.info("Pushing images to harbor success")
            msg = "Harbor image pushed successfully"
        else:
            current_app.logger.info("Installation of harbor is not opted, skipping pushing image to habor")
            msg = "Installation of harbor is not opted, skipping pushing image to habor"
    except Exception as ex:
        response_body = {
            "responseType": "ERROR",
            "msg": str(ex) + " Failed Harbor image push",
            "STATUS_CODE": 500
        }
        return jsonify(response_body), 500
    response_body = {
        "responseType": "SUCCESS",
        "msg": msg,
        "STATUS_CODE": 200
    }
    return jsonify(response_body), 200


def create_harbor_project(address, user, password, project_name):
    ecod_bytes = (user + ":" + password).encode(
        "ascii")
    ecod_bytes = base64.b64encode(ecod_bytes)
    ecod_string = ecod_bytes.decode("ascii")
    uri = "https://" + address + "/api/v2.0/projects"
    headers = {'Authorization': (
            'Basic ' + ecod_string),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.request(
        "GET", uri, headers=headers, verify=False)
    if response.status_code != 200:
        return None, response.text
    for project in response.json():
        if project["name"] == project_name:
            return "Success", project_name + " is already created"
    body = {
        "project_name": project_name,
        "registry_id": None,
        "public": True,
        "storage_limit": 53687091200
    }
    json_object = json.dumps(body, indent=4)
    response = requests.request(
        "POST", uri, headers=headers, data=json_object, verify=False)
    if response.status_code != 201:
        return None, "Failed to create harbor project " + project_name + " " + response.text
    return "Success", project_name + " created"


def check_repository_count(address, user, password, project_name):
    ecod_bytes = (user + ":" + password).encode(
        "ascii")
    ecod_bytes = base64.b64encode(ecod_bytes)
    ecod_string = ecod_bytes.decode("ascii")
    uri = "https://" + address + "/api/v2.0/projects"
    headers = {'Authorization': (
            'Basic ' + ecod_string),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.request(
        "GET", uri, headers=headers, verify=False)
    if response.status_code != 200:
        return None, response.text
    for project in response.json():
        if project["name"] == project_name:
            if project["repo_count"] == 157:
                return "Success", "All tanzu images are present"
            elif project["repo_count"] == 0:
                return None, "No repository present, pushing"
            else:
                return "Partial", "Repo count is less then expected , clear all repostory under  " + project_name + " and retrigger command --load_tanzu_image_to_harbor"
    return "NOT_FOUND", project_name + " project not found"


def get_repo_count(repo_name):
    with open(r'/opt/vmware/arcas/tools/isharbor.txt', 'r') as file:
        isharbor_requested = file.read()
    if isharbor_requested.strip("\n").strip("\r").strip() == "true":
        with open(r'/opt/vmware/arcas/tools/harbor_fqdn.txt', 'r') as file:
            data = file.read()
        data = data.strip("\n").strip("\r").strip()
        fqdn = data
        address = data + ":9443"
        user = "admin"
        file = "/etc/.secrets/root_password"
        password = Path(file).read_text().strip("\n")
        ecod_bytes = (user + ":" + password).encode(
            "ascii")
        project_name = repo_name
        ecod_bytes = base64.b64encode(ecod_bytes)
        ecod_string = ecod_bytes.decode("ascii")
        uri = "https://" + address + "/api/v2.0/projects"
        headers = {'Authorization': (
                'Basic ' + ecod_string),
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        response = requests.request(
            "GET", uri, headers=headers, verify=False)
        if response.status_code != 200:
            return None, response.text
        for project in response.json():
            if project["name"] == project_name:
                return project["repo_count"], "SUCCESS"
    return "NOT_FOUND", project_name + " project not found"


@harbor.route('/api/tanzu/harbor_pre_load_status', methods=['GET'])
def harbor_preload_status():
    repo_name = request.args.get('repo_name')
    tanzu_extract = "/opt/vmware/arcas/tools/tanzu/"
    expected_tar_count = 212
    expected_repo_count = 156
    main_command = ["ls", tanzu_extract]
    sub_command = ["wc", "-l"]
    cert_state = grabPipeOutput(main_command, sub_command)
    repo_count = get_repo_count(repo_name)
    if repo_count[0] == "NOT_FOUND":
        repo_count[0] = "0"
    current_tar_count = int(cert_state[0])
    current_repo_count = int(repo_count[0])
    total = expected_repo_count + expected_tar_count
    percentage = ((current_tar_count + current_repo_count) / total) * 100
    response_body = {
        "responseType": "SUCCESS",
        "msg": "",
        "percentage": percentage,
        "STATUS_CODE": 200
    }
    return jsonify(response_body), 200
