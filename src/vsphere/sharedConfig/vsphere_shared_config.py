# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import logging
from http import HTTPStatus

import requests
from flask import Blueprint, current_app
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.login_auth.authentication import token_required
from common.operation.constants import Type
from common.util.extension_utils import ExtensionUtils
from common.util.request_api_util import RequestApiUtil
from common.workflows.vsphere_cluster_creation import ClusterCreateWorkflow

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logger = logging.getLogger(__name__)

vsphere_shared_config = Blueprint("vsphere_shared_config", __name__, static_folder="sharedConfig")

__author__ = "Pooja Deshmukh"


@vsphere_shared_config.route("/api/tanzu/vsphere/tkgsharedsvc", methods=["POST"])
@token_required
def configSharedCluster(current_user):
    try:
        deploy_shared = deploy()
        if deploy_shared[1] != 200:
            errorMessage = str(deploy_shared[0].json["msg"])
            current_app.logger.error(errorMessage)
            return (
                RequestApiUtil.send_error("Failed to Config shared cluster " + errorMessage),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        deploy_shared_extension = ExtensionUtils(current_app.config).deploy_shared_extensions()
        if deploy_shared_extension[1] != 200:
            errorMessage = str(deploy_shared_extension[0].json["msg"])
            current_app.logger.error(errorMessage)
            return RequestApiUtil.send_error(errorMessage), HTTPStatus.INTERNAL_SERVER_ERROR
        current_app.logger.info("Shared cluster configured Successfully")
        return RequestApiUtil.send_ok("Shared cluster configured Successfully"), HTTPStatus.OK
    except Exception as ex:
        return RequestApiUtil.send_error(str(ex)), HTTPStatus.INTERNAL_SERVER_ERROR


@vsphere_shared_config.route("/api/tanzu/vsphere/tkgsharedsvc/config", methods=["POST"])
@token_required
def deploy(current_user):
    try:
        ClusterCreateWorkflow(current_app.config, Type.SHARED).create_cluster()
        return RequestApiUtil.send_ok("Successfully deployed shared cluster"), HTTPStatus.OK
    except Exception as ex:
        current_app.logger.info(str(ex))
        return RequestApiUtil.send_error(str(ex)), HTTPStatus.INTERNAL_SERVER_ERROR
