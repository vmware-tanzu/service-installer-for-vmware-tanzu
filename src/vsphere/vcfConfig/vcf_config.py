# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import requests
from flask import Blueprint, current_app, jsonify, request
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.model.vcfSpec import VcfMasterSpec
from common.workflows.nsxt_workflow import NsxtWorkflow

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

vcf_config = Blueprint("vcf_config", __name__, static_folder="vcfConfig")


@vcf_config.route("/api/tanzu/vsphere/alb/vcf_pre_config", methods=["POST"])
def config_vcf_env():
    try:
        spec_json = request.get_json(force=True)
        spec: VcfMasterSpec = VcfMasterSpec.parse_obj(spec_json)
        NsxtWorkflow(spec, current_app.config, current_app.logger).execute_workflow_vcf()
    except ValueError as ex:
        response_body = {"responseType": "ERROR", "msg": str(ex), "STATUS_CODE": 500}
        return jsonify(response_body), 500
    d = {"responseType": "SUCCESS", "msg": "VCF configured Successfully", "STATUS_CODE": 200}
    current_app.logger.info("VCF configured Successfully")
    return jsonify(d), 200
