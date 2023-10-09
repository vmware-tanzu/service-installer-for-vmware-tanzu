# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
from http import HTTPStatus

from flask import Blueprint, jsonify
from flask_injector import inject

from common.login_auth.authentication import token_required
from common.util.common_utils import CommonUtils
from common.util.request_api_util import RequestApiUtil
from common.util.tiny_db_util import TinyDbUtil

deploy_status = Blueprint("deploy_status", __name__, static_folder="deploy_status")


@deploy_status.route("/api/tanzu/deployStatusOverview", methods=["GET"])
@inject
@token_required
def overview_status(current_user, tiny_db_util: TinyDbUtil):
    """
    this function will fetch status deployment job status from db, if any job started return True else False
    """
    status = tiny_db_util.fetch_in_progress_job_status()
    if len(status) > 0:
        response = RequestApiUtil.create_json_object("Found", "SUCCESS", HTTPStatus.OK)
        return response, HTTPStatus.OK
    else:
        response = RequestApiUtil.create_json_object("Not Found", "SUCCESS", HTTPStatus.NOT_FOUND)
        return response, HTTPStatus.NOT_FOUND


@deploy_status.route("/api/tanzu/deployStatusDetails", methods=["GET"])
@inject
@token_required
def detailed_status(current_user, tiny_db_util: TinyDbUtil):
    """
    this function will fetch deployment job status in details from db, if any job started return True else False
    """
    status = tiny_db_util.get_all_db_entries()
    if len(status) > 0:
        json_data = CommonUtils.prepare_status_json_output(status)
        json_data.update({"responseType": "SUCCESS", "STATUS_CODE": HTTPStatus.OK})
        return jsonify(json_data), HTTPStatus.OK
    else:
        response = RequestApiUtil.create_json_object("Not Found", "SUCCESS", HTTPStatus.NOT_FOUND)
        return response, HTTPStatus.NOT_FOUND
