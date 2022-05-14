from flask import Flask, jsonify, send_file
from flask_restful import Api, request
from flask_cors import CORS
from zipfile import ZipFile
from vsphere.sharedConfig.vsphere_shared_config import vsphere_shared_config
from vmc.sharedConfig.shared_config import shared_config, configSharedCluster
from vmc.vmcConfig.vmc_config import vmc_config, config_vmc_env
from vmc.aviConfig.avi_config import avi_config, configure_alb
from vsphere.aviConfig.vsphere_avi_config import vcenter_avi_config
from common.prechecks.precheck import vcenter_precheck
from common.cleanup.cleanup import cleanup_env
from common.prechecks.list_reources import vcenter_resources
from common.common_utilities import envCheck
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
from common.deployApp.deployApp import deploy_app
from common.tkg.extension.deploy_ext import tkg_extentions
from vmc.managementConfig.management_config import management_config, configManagementCluster
from vsphere.managementConfig.vsphere_management_config import vsphere_management_config
from vmc.workloadConfig.workload_config import workload_config, workloadConfig
from vsphere.workloadConfig.vsphere_workload_config import vsphere_workload_config
from common.session.session_acquire import session_acquire
import logging
import json
import os
import sys
from os.path import basename
from pathlib import Path
from logging.config import fileConfig
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

fileConfig(Path('logging.conf'))
logger = logging.getLogger(__name__)
logging.config.fileConfig('logging.conf')

Path("/var/log/server/").mkdir(parents=True, exist_ok=True)

logger.setLevel(logging.DEBUG)
LOG_FILENAME = "/var/log/server/arcas.log"
formatter = logging.Formatter('%(asctime)-16s %(levelname)-8s %(filename)-s:%(lineno)-3s %(message)s')

handler = RotatingFileHandler(LOG_FILENAME, maxBytes=5242880, backupCount=10)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
stdout_handler.setLevel(logging.INFO)

app = Flask(__name__)
api = Api(app)
CORS(app)

app.logger.addHandler(handler)
app.logger.addHandler(stdout_handler)
app.register_blueprint(shared_config, url_prefix="")
app.register_blueprint(vmc_config, url_prefix="")
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
app.register_blueprint(tkg_extentions, url_prefix="")
app.register_blueprint(cleanup_env, url_prefix="")


@app.route('/api/tanzu/vmc/tkgm', methods=['POST'])
def configTkgm():
    vmc = config_vmc_env()
    if vmc[1] != 200:
        app.logger.error(vmc[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": vmc[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    avi = configure_alb()
    if vmc[1] != 200:
        app.logger.error(str(avi[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": str(avi[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    mgmt = configManagementCluster()
    if mgmt[1] != 200:
        app.logger.error(str(mgmt[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": str(mgmt[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    shared = configSharedCluster()
    if shared[1] != 200:
        app.logger.error(str(shared[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": str(shared[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    workLoad = workloadConfig()
    if workLoad[1] != 200:
        app.logger.error(str(workLoad[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": str(workLoad[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Tkgm configured Successfully ",
        "ERROR_CODE": 200
    }
    app.logger.info("Tkgm configured Successfully ")
    return jsonify(d), 200


@app.route('/api/tanzu/createinputfile', methods=['POST'])
def createInputFile():
    try:
        env = request.headers['filename']
    except Exception:
        app.logger.error("No filename passed")
        return "No filename passed", 400
    if env is None:
        return "No filename passed", 400
    try:
        jsonInput = request.get_json(force=True)
        json_object_m = json.dumps(jsonInput, indent=4)
        with open("./" + env, "w") as outfile:
            outfile.write(json_object_m)
    except Exception as e:
        app.logger.error("Failed to generate the json file " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to generate the json file " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    app.logger.info("Successfully generated input file")
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully generated input file",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@app.route('/api/tanzu/logbundle', methods=['GET'])
def download_log_bundle():
    path = "/var/log/server"
    app.logger.info(f"*************Downloading log files {path}************")
    if not os.path.isdir("/tmp/logbundle"):
        command = ["mkdir", "/tmp/logbundle"]
        runShellCommandAndReturnOutputAsList(command)
    zip_path = "/tmp/logbundle/service_installer_log_bundle.zip"
    with ZipFile(zip_path, "w") as newzip:
        for folderName, subfolders, filenames in os.walk(path):
            for filename in filenames:
                #create complete filepath of file in directory
                filePath = os.path.join(folderName, filename)
                # Add file to zip
                newzip.write(filePath, basename(filePath))
    return send_file(zip_path, as_attachment=True)


if __name__ == '__main__':
    from waitress import serve

    serve(app, port=5000)
