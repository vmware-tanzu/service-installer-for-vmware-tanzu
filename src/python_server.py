# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import datetime
import json
import logging
import os
import sys
import uuid
from http import HTTPStatus
from logging.config import fileConfig
from logging.handlers import RotatingFileHandler
from os.path import basename
from pathlib import Path
from zipfile import ZipFile

import jwt
import requests
from flask import Flask, jsonify, send_file, session
from flask_cors import CORS
from flask_injector import FlaskInjector, inject, singleton
from flask_restful import Api, request
from flask_swagger_ui import get_swaggerui_blueprint
from werkzeug.security import check_password_hash, generate_password_hash

from common.cleanup.cleanup import cleanup_env
from common.deployApp.deployApp import deploy_app
from common.harbor.push_tkg_image_to_harbor import harbor
from common.login_auth.authentication import token_required
from common.login_auth.users import Users, db
from common.operation.constants import Paths, SivtStatus
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
from common.prechecks.list_reources import vcenter_resources
from common.prechecks.precheck import vcenter_precheck
from common.session.session_acquire import session_acquire
from common.tkg.extension.deploy_ext import tkg_extensions
from common.util.common_utils import CommonUtils
from common.util.deployment_status_util import deploy_status
from common.util.log_streaming_util import log_stream
from common.util.request_api_util import RequestApiUtil
from common.util.tiny_db_util import TinyDbUtil
from common.wcp_shutdown.wcp_shutdown import shutdown_env
from vcd.vcd_prechecks.vcd_ui_utils import vcd_ui_util
from vcd.vcd_prechecks.vcdPrechecks import vcd_precheck
from vmc.aviConfig.avi_config import avi_config, configure_alb
from vmc.managementConfig.management_config import configManagementCluster, management_config
from vmc.sharedConfig.shared_config import configSharedCluster, shared_config
from vmc.vmcConfig.vmc_config import config_vmc_env, vmc_config
from vmc.workloadConfig.workload_config import workload_config, workloadConfig
from vsphere.aviConfig.vsphere_avi_config import vcenter_avi_config
from vsphere.managementConfig.vsphere_management_config import vsphere_management_config
from vsphere.managementConfig.vsphere_tkgs_supervisor_config import vsphere_supervisor_cluster
from vsphere.sharedConfig.vsphere_shared_config import vsphere_shared_config
from vsphere.vcfConfig.vcf_config import vcf_config
from vsphere.workloadConfig.vsphere_tkgs_workload import vsphere_tkgs_workload_cluster
from vsphere.workloadConfig.vsphere_workload_config import vsphere_workload_config

fileConfig(Path("logging.conf"))
logger = logging.getLogger(__name__)
logging.config.fileConfig("logging.conf")

Path("/var/log/server/").mkdir(parents=True, exist_ok=True)

logger.setLevel(logging.DEBUG)
LOG_FILENAME = "/var/log/server/arcas.log"
formatter = logging.Formatter("%(asctime)-16s %(levelname)-8s %(filename)-s:%(lineno)-3s %(message)s")

handler = RotatingFileHandler(LOG_FILENAME, maxBytes=5242880, backupCount=10)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
stdout_handler.setLevel(logging.INFO)

app = Flask(__name__)
api = Api(app)
CORS(app, supports_credentials=True)
app.config["SECRET_KEY"] = "004f2af45d3a4e161a7dd2d17fdae47f"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://///opt/vmware/arcas/src/sivt.db"
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(minutes=235)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
db.init_app(app)


@app.before_first_request
def create_tables():
    db.create_all()


# swagger specific ###
SWAGGER_URL = "/swagger"
SWAGGER_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    api_url=None,
    config={
        "app_name": "arcas",
        "layout": "StandaloneLayout",
        "plugins": ["TopBar"],
        "urls": [
            {"url": "/static/vsphere.json", "name": "vsphere", "primaryName": "vsphere"},
            {"url": "/static/vmc.json", "name": "vmc", "primaryName": "vmc"},
            {"url": "/static/vcf.json", "name": "vcf", "primaryName": "vcf"},
        ],
    },
    blueprint_name="arcas",
)

app.register_blueprint(SWAGGER_BLUEPRINT, url_prefix=SWAGGER_URL)
# end swagger specific ###

app.logger.addHandler(handler)
app.logger.addHandler(stdout_handler)
app.register_blueprint(shared_config, url_prefix="")
app.register_blueprint(vmc_config, url_prefix="")
app.register_blueprint(vcf_config, url_prefix="")
app.register_blueprint(avi_config, url_prefix="")
app.register_blueprint(workload_config, url_prefix="")
app.register_blueprint(deploy_app, url_prefix="")
app.register_blueprint(management_config, url_prefix="")
app.register_blueprint(session_acquire, url_prefix="")
app.register_blueprint(vcenter_avi_config, url_prefix="")

app.register_blueprint(vsphere_management_config, url_prefix="")
app.register_blueprint(vsphere_shared_config, url_prefix="")
app.register_blueprint(vsphere_workload_config, url_prefix="")
app.register_blueprint(vcenter_precheck, url_prefix="")
app.register_blueprint(vcenter_resources, url_prefix="")
app.register_blueprint(tkg_extensions, url_prefix="")
app.register_blueprint(cleanup_env, url_prefix="")
app.register_blueprint(harbor, url_prefix="")
app.register_blueprint(shutdown_env, url_prefix="")
app.register_blueprint(vcd_precheck, url_prefix="")
app.register_blueprint(vcd_ui_util, url_prefix="")
app.register_blueprint(vsphere_tkgs_workload_cluster, url_prefix="")
app.register_blueprint(vsphere_supervisor_cluster, url_prefix="")
app.register_blueprint(deploy_status, url_prefix="")
app.register_blueprint(log_stream, url_prefix="")


def configure(binder):
    # incase of server restart all the in-progress(halted) jobs needs to be error.
    db_file = Paths.SIVT_DB_FILE
    db_object = TinyDbUtil(Paths.SIVT_DB_FILE)
    if CommonUtils.is_file_exist(db_file):
        db_object.update_in_progress_to_error()
    binder.bind(TinyDbUtil, to=db_object, scope=singleton)


@app.before_request
@inject
def before_request_func(tiny_db_util: TinyDbUtil):
    env = request.headers.get("Env")
    json_data = ""
    # fetch json data from endpoint body
    if len(request.data) > 0:
        json_data = request.get_json(force=True)
    # update db, in case new request and db json not exist
    tiny_db_util.check_db_file(env=env, json_file=json_data)
    # update db with in-progress status
    endpoint_path = request.path
    component = CommonUtils.match_endpoint(endpoint_path)
    if component:
        tiny_db_util.update_db_file(SivtStatus.IN_PROGRESS, component)


@app.after_request
@inject
def after_request_func(response, tiny_db_util: TinyDbUtil):
    # update db with deployment job status
    endpoint_path = request.path
    component = CommonUtils.match_endpoint(endpoint_path)
    if component:
        if response.status_code == HTTPStatus.OK:
            tiny_db_util.update_db_file(SivtStatus.SUCCESS, component)
        else:
            tiny_db_util.update_db_file(SivtStatus.FAILED, component)
    return response


@app.route("/api/tanzu/vmc/tkgm", methods=["POST"])
@token_required
def configTkgm(current_user):
    vmc = config_vmc_env()
    if vmc[1] != 200:
        app.logger.error(vmc[0].json["msg"])
        d = {"responseType": "ERROR", "msg": vmc[0].json["msg"], "STATUS_CODE": 500}
        return jsonify(d), 500
    avi = configure_alb()
    if vmc[1] != 200:
        app.logger.error(str(avi[0].json["msg"]))
        d = {"responseType": "ERROR", "msg": str(avi[0].json["msg"]), "STATUS_CODE": 500}
        return jsonify(d), 500
    mgmt = configManagementCluster()
    if mgmt[1] != 200:
        app.logger.error(str(mgmt[0].json["msg"]))
        d = {"responseType": "ERROR", "msg": str(mgmt[0].json["msg"]), "STATUS_CODE": 500}
        return jsonify(d), 500
    shared = configSharedCluster()
    if shared[1] != 200:
        app.logger.error(str(shared[0].json["msg"]))
        d = {"responseType": "ERROR", "msg": str(shared[0].json["msg"]), "STATUS_CODE": 500}
        return jsonify(d), 500
    workLoad = workloadConfig()
    if workLoad[1] != 200:
        app.logger.error(str(workLoad[0].json["msg"]))
        d = {"responseType": "ERROR", "msg": str(workLoad[0].json["msg"]), "STATUS_CODE": 500}
        return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Tkgm configured Successfully ", "STATUS_CODE": 200}
    app.logger.info("Tkgm configured Successfully ")
    return jsonify(d), 200


@app.route("/api/tanzu/login", methods=["POST"])
def login_user():
    auth = request.authorization
    try:
        server = request.headers["Server"]
    except Exception:
        app.logger.error("vCenter Server is not passed as header")
        response = RequestApiUtil.create_json_object(
            "vCenter Server is not passed as header", response_type="ERROR", status_code=HTTPStatus.UNAUTHORIZED
        )
        return response, HTTPStatus.UNAUTHORIZED

    if not auth or not auth.username or not auth.password:
        app.logger.error("Username and Password not passed.")
        response = RequestApiUtil.create_json_object(
            "Username and Password not passed", response_type="ERROR", status_code=HTTPStatus.UNAUTHORIZED
        )
        return response
    sess = requests.post(
        "https://" + str(server) + "/rest/com/vmware/cis/session", auth=(auth.username, auth.password), verify=False
    )
    if sess.status_code != 200:
        app.logger.error("Connection to vCenter failed, incorrect user name or password")
        response = RequestApiUtil.create_json_object(
            "Connection to vCenter failed, incorrect user name or password",
            response_type="ERROR",
            status_code=HTTPStatus.UNAUTHORIZED,
        )
        return response, HTTPStatus.UNAUTHORIZED
    execute = False
    try:
        user = Users.query.filter_by(name=auth.username).first()
        if user is None:
            execute = True
    except Exception:
        execute = True
    if execute:
        hashed_password = generate_password_hash(auth.password, method="sha256")
        new_user = Users(public_id=str(uuid.uuid4()), name=auth.username, password=hashed_password, admin=False)
        db.session.add(new_user)
        db.session.commit()
    user = Users.query.filter_by(name=auth.username).first()
    if check_password_hash(user.password, auth.password):
        app.logger.info("Generated token successfully")
        token = jwt.encode(
            {"public_id": user.public_id, "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=240)},
            app.config["SECRET_KEY"],
            "HS256",
        )
        session["username"] = auth.username
        app.logger.info("Login successful")
        response = RequestApiUtil.create_json_object(
            "Successfully fetched session token",
            response_type="SUCCESS",
            status_code=HTTPStatus.UNAUTHORIZED,
            add_data={"token": token},
        )
        return response, HTTPStatus.OK

    app.logger.error("Could not verify, login required")
    response = RequestApiUtil.create_json_object(
        "Could not verify, login required", response_type="ERROR", status_code=HTTPStatus.UNAUTHORIZED
    )
    return response, HTTPStatus.UNAUTHORIZED


@app.route("/api/tanzu/active_session", methods=["GET"])
def check_active_session():
    user = session.get("username")
    if user is None:
        is_active = False
    else:
        is_active = True
    app.logger.info("******")
    app.logger.info(user)
    if is_active:
        app.logger.info("You are already logged in as: " + user)
        response = RequestApiUtil.create_json_object(
            "You are already logged in as: " + user,
            status_code=HTTPStatus.OK,
            add_data={"SESSION": "ACTIVE", "USER": user},
        )
        return response, HTTPStatus.OK
    else:
        app.logger.info("Session not active")
        response = RequestApiUtil.create_json_object(
            "Session not active",
            response_type="ERROR",
            status_code=HTTPStatus.UNAUTHORIZED,
        )
        return response, HTTPStatus.UNAUTHORIZED


@app.route("/api/tanzu/logout", methods=["GET"])
def logout():
    user = session.get("username")
    if user is None:
        is_active = False
    else:
        is_active = True
    if is_active:
        session.pop("username", None)
        app.logger.info("User successfully logged out")
        response = RequestApiUtil.create_json_object("User successfully logged out", status_code=HTTPStatus.OK)
        return response, HTTPStatus.OK
    else:
        app.logger.info("No active session found")
        response = RequestApiUtil.create_json_object("No active session found", status_code=HTTPStatus.OK)
        return response, HTTPStatus.OK


@app.route("/api/tanzu/createinputfile", methods=["POST"])
@token_required
def createInputFile(current_user):
    user = current_user.name
    home_dir = os.path.join("/home", user)
    try:
        filename = home_dir + "/" + request.headers["filename"]
        if not os.path.exists(home_dir):
            os.makedirs(home_dir)
    except Exception:
        app.logger.error("No filename passed")
        return "No filename passed", 400
    if filename is None:
        return "No filename passed", 400
    try:
        jsonInput = request.get_json(force=True)
        json_object_m = json.dumps(jsonInput, indent=4)
        name, file_ext = os.path.splitext(filename)
        # MAPBU-1694, whenever there is an existing deployment file, it needs to be saved, with _counter, so that user
        # can re-use them and new file saved with same name
        if os.path.isfile(filename):
            i = 1
            while os.path.isfile(f"{name}_{i}{file_ext}"):
                i += 1
            new_filename = f"{name}_{i}{file_ext}"
            os.system(f"cp {filename} {new_filename}")
        with open(filename, "w") as outfile:
            outfile.write(json_object_m)
    except Exception as e:
        app.logger.error("Failed to generate the json file " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to generate the json file " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
    app.logger.info("Successfully generated input file")
    d = {"responseType": "SUCCESS", "msg": "Successfully generated input file", "STATUS_CODE": 200}
    return jsonify(d), 200


@app.route("/api/tanzu/logbundle", methods=["GET"])
@token_required
def download_log_bundle(current_user):
    path = "/var/log/server"
    app.logger.info(f"*************Downloading log files {path}************")
    if not os.path.isdir("/tmp/logbundle"):
        command = ["mkdir", "/tmp/logbundle"]
        runShellCommandAndReturnOutputAsList(command)
    zip_path = "/tmp/logbundle/service_installer_log_bundle.zip"
    with ZipFile(zip_path, "w") as newzip:
        for folderName, subfolders, filenames in os.walk(path):
            for filename in filenames:
                # create complete filepath of file in directory
                filePath = os.path.join(folderName, filename)
                # Add file to zip
                newzip.write(filePath, basename(filePath))
    return send_file(zip_path, as_attachment=True)


if __name__ == "__main__":
    FlaskInjector(app=app, modules=[configure])
    from waitress import serve

    serve(app, port=5000)
