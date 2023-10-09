# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import logging
from http import HTTPStatus

import requests
from flask import Blueprint, current_app
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.login_auth.authentication import token_required
from common.util.request_api_util import RequestApiUtil
from common.workflows.nsx_alb_workflow import NsxAlbWorkflow

logger = logging.getLogger(__name__)
vcenter_avi_config = Blueprint("vcenter_avi_config", __name__, static_folder="aviConfig")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@vcenter_avi_config.route("/api/tanzu/vsphere/alb", methods=["POST"])
@token_required
def aviConfig_vsphere(current_user):
    try:
        NsxAlbWorkflow().nsx_alb_deploy_workflow()
    except Exception as ex:
        return RequestApiUtil.send_error(message=str(ex)), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Avi configured Successfully")
    return RequestApiUtil.send_ok(message="Avi configured Successfully"), HTTPStatus.OK
