# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause


import requests
from flask import Blueprint, current_app, jsonify, request
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.model.vmcSpec import VmcMasterSpec
from common.workflows.nsxt_workflow import NsxtWorkflow

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

vmc_config = Blueprint("vmc_config", __name__, static_folder="vmcConfig")


@vmc_config.route("/api/tanzu/vmc/envconfig", methods=["POST"])
def config_vmc_env():
    try:
        spec_json = request.get_json(force=True)
        spec: VmcMasterSpec = VmcMasterSpec.parse_obj(spec_json)
        NsxtWorkflow(spec, current_app.config, current_app.logger).execute_workflow()
    except ValueError as ex:
        response_body = {"responseType": "ERROR", "msg": str(ex), "STATUS_CODE": 500}
        return jsonify(response_body), 500
    d = {"responseType": "SUCCESS", "msg": "VMC configured Successfully", "STATUS_CODE": 200}
    current_app.logger.info("VMC configured Successfully")
    return jsonify(d), 200
