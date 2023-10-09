# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import logging
from http import HTTPStatus

import requests
from flask import Blueprint, current_app
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.login_auth.authentication import token_required
from common.operation.constants import Type
from common.util.request_api_util import RequestApiUtil
from common.workflows.vsphere_cluster_creation import ClusterCreateWorkflow

logger = logging.getLogger(__name__)
vsphere_workload_config = Blueprint("vsphere_workload_config", __name__, static_folder="workloadConfig")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

__author__ = "Pooja Deshmukh"


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/preconfig", methods=["POST"])
@token_required
def workloadConfig(current_user):
    network_config = networkConfig()
    if network_config[1] != 200:
        errorMessage = network_config[0].json["msg"]
        current_app.logger.error(errorMessage)
        return (
            RequestApiUtil.send_error("Failed to Config workload cluster " + str(errorMessage)),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    deploy_workload = deploy()
    if deploy_workload[1] != 200:
        errorMessage = str(deploy_workload[0].json["msg"])
        current_app.logger.error(errorMessage)
        return RequestApiUtil.send_error(str(errorMessage)), HTTPStatus.INTERNAL_SERVER_ERROR
    return RequestApiUtil.send_ok("Workload cluster configured Successfully"), HTTPStatus.OK


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/network-config", methods=["POST"])
@token_required
def networkConfig(current_user):
    try:
        ClusterCreateWorkflow(current_app.config, Type.WORKLOAD).workload_preconfig()
        return RequestApiUtil.send_ok("Successfully configured workload preconfig"), HTTPStatus.OK
    except Exception as ex:
        return RequestApiUtil.send_error(str(ex)), HTTPStatus.INTERNAL_SERVER_ERROR


@vsphere_workload_config.route("/api/tanzu/vsphere/workload/config", methods=["POST"])
@token_required
def deploy(current_user):
    try:
        ClusterCreateWorkflow(current_app.config, Type.WORKLOAD).create_cluster()
        return RequestApiUtil.send_ok("Successfully deployed workload cluster"), HTTPStatus.OK
    except Exception as ex:
        return RequestApiUtil.send_error(str(ex)), HTTPStatus.INTERNAL_SERVER_ERROR
