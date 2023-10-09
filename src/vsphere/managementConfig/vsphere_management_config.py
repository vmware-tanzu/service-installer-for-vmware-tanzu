# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import logging
from http import HTTPStatus

import requests
from flask import Blueprint, current_app
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.login_auth.authentication import token_required
from common.util.request_api_util import RequestApiUtil
from common.workflows.management_cluster_workflow import MgmtWorkflow

logger = logging.getLogger(__name__)
vsphere_management_config = Blueprint("vsphere_management_config", __name__, static_folder="managementConfig")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@vsphere_management_config.route("/api/tanzu/vsphere/tkgmgmt", methods=["POST"])
@token_required
def configManagementCluster(current_user):
    try:
        MgmtWorkflow().management_cluster_deploy_worklflow()
    except Exception as ex:
        return RequestApiUtil.send_error(message=str(ex)), HTTPStatus.INTERNAL_SERVER_ERROR
    current_app.logger.info("Management Cluster configured Successfully")
    return RequestApiUtil.send_ok(message="Management Cluster configured Successfully"), HTTPStatus.OK
