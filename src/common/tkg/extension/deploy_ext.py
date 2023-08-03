# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause.

from flask import Blueprint, current_app, jsonify, request

from common.common_utilities import (
    check_fluent_bit_elastic_search_endpoint_enabled,
    check_fluent_bit_http_endpoint_enabled,
    check_fluent_bit_kafka_endpoint_endpoint_enabled,
    check_fluent_bit_splunk_endpoint_endpoint_enabled,
    check_fluent_bit_syslog_endpoint_enabled,
    checkPromethusEnabled,
    checkTanzuExtensionEnabled,
    envCheck,
    isEnvTkgs_ns,
)
from common.model.vsphereTkgsSpecNameSpace import VsphereTkgsNameSpaceMasterSpec
from common.operation.constants import Tkg_Extension_names
from common.util.common_utils import CommonUtils
from common.util.tanzu_util import TanzuUtil

from .oneDot4_extensions import deploy_Dot4_ext
from .tkgs_extensions import deploy_tkgs_extensions

tkg_extensions = Blueprint("tkg_extensions", __name__, static_folder="extension")


@tkg_extensions.route("/api/tanzu/extensions", methods=["POST"])
def deploy_tkg_extensions():
    try:
        env = envCheck()
        if env[1] != 200:
            current_app.logger.error("Wrong env provided " + env[0])
            d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
            return jsonify(d), 500
        env = env[0]
        spec_json = request.get_json(force=True)
        if isEnvTkgs_ns(env):
            spec: VsphereTkgsNameSpaceMasterSpec = VsphereTkgsNameSpaceMasterSpec.parse_obj(spec_json)
            TanzuUtil(env=env, spec=spec)
            result = deploy_tkgs_extensions()
            if result[1] != 200:
                d = {"responseType": "ERROR", "msg": "Failed to deploy extensions - ", "STATUS_CODE": 500}
                return jsonify(d), 500
            else:
                d = {"responseType": "SUCCESS", "msg": "Extensions deployment is successful - ", "STATUS_CODE": 200}
                return jsonify(d), 200
        else:
            spec_obj = CommonUtils.get_spec_obj(env)
            spec: spec_obj = spec_obj.parse_obj(spec_json)
            TanzuUtil(env=env, spec=spec)
            list_of_extension = []
            if checkTanzuExtensionEnabled():
                if check_fluent_bit_splunk_endpoint_endpoint_enabled():
                    list_of_extension.append(Tkg_Extension_names.FLUENT_BIT_SPLUNK)
                if check_fluent_bit_http_endpoint_enabled():
                    list_of_extension.append(Tkg_Extension_names.FLUENT_BIT_HTTP)
                if check_fluent_bit_syslog_endpoint_enabled():
                    list_of_extension.append(Tkg_Extension_names.FLUENT_BIT_SYSLOG)
                if check_fluent_bit_elastic_search_endpoint_enabled():
                    list_of_extension.append(Tkg_Extension_names.FLUENT_BIT_ELASTIC)
                if check_fluent_bit_kafka_endpoint_endpoint_enabled():
                    list_of_extension.append(Tkg_Extension_names.FLUENT_BIT_KAFKA)

            else:
                current_app.logger.info("Tanzu extensions deploy is deactivated, no extensions will be deployed")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Tanzu extensions deploy is deactivated, no extensions will be deployed",
                    "STATUS_CODE": 200,
                }
                return jsonify(d), 200
            extension = deploy_Dot4_ext()
            if len(list_of_extension) > 1:
                current_app.logger.info("User can only enable one logging extension at a once, please select only one.")
                d = {
                    "responseType": "ERROR",
                    "msg": "User can only enable one logging extension at a once, please select only one.",
                    "STATUS_CODE": 500,
                }
                return jsonify(d), 500
            if checkPromethusEnabled():
                # before running fluent-bit we need to run prometheus and grafana, to make extensions
                # deployment in sync with TKGs
                list_of_extension.insert(0, Tkg_Extension_names.PROMETHEUS)
                list_of_extension.insert(1, Tkg_Extension_names.GRAFANA)
            if len(list_of_extension) == 0:
                current_app.logger.info("No extension to deploy")
                d = {"responseType": "SUCCESS", "msg": "No extension to deploy ", "STATUS_CODE": 200}
                return jsonify(d), 200
            for extension_name in list_of_extension:
                status = extension.deploy(extension_name)
                if status[1] != 200:
                    current_app.logger.info("Failed to deploy extension " + str(status[0].json["msg"]))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to deploy extension " + str(status[0].json["msg"]),
                        "STATUS_CODE": 500,
                    }
                    return jsonify(d), 500
            current_app.logger.info("Successfully deployed extensions " + str(list_of_extension))
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully deployed extensions " + str(list_of_extension),
                "STATUS_CODE": 200,
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Failed to deploy extensions " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to deploy extensions " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
