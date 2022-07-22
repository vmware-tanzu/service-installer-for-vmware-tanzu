from .oneDot3_extentions import deploy_Dot3_ext
from .oneDot4_extentions import deploy_Dot4_ext
from .tkgs_extensions import deploy_tkgs_extensions
from common.operation.constants import Tkg_version, Tkg_Extention_names
from common.common_utilities import checkTanzuExtentionEnabled, check_fluent_bit_splunk_endpoint_endpoint_enabled, \
    check_fluent_bit_kafka_endpoint_endpoint_enabled, check_fluent_bit_syslog_endpoint_enabled, \
    check_fluent_bit_elastic_search_endpoint_enabled, check_fluent_bit_http_endpoint_enabled, checkPromethusEnabled, \
    isEnvTkgs_ns, envCheck
from flask import Blueprint, current_app, jsonify

tkg_extentions = Blueprint("tkg_extentions", __name__, static_folder="extension")


@tkg_extentions.route("/api/tanzu/extentions", methods=['POST'])
def deploy_tkg_extentions():
    try:
        env = envCheck()
        if env[1] != 200:
            current_app.logger.error("Wrong env provided " + env[0])
            d = {
                "responseType": "ERROR",
                "msg": "Wrong env provided " + env[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        env = env[0]
        if isEnvTkgs_ns(env):
            result = deploy_tkgs_extensions()
            if result[1] != 200:
                d = {
                    "responseType": "ERROR",
                    "msg": "Failed to deploy extensions - ",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            else:
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Extensions deployment is successful - ",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200
        else:
            listOfExtention = []
            if checkTanzuExtentionEnabled():
                if check_fluent_bit_splunk_endpoint_endpoint_enabled():
                    listOfExtention.append(Tkg_Extention_names.FLUENT_BIT_SPLUNK)
                if check_fluent_bit_http_endpoint_enabled():
                    listOfExtention.append(Tkg_Extention_names.FLUENT_BIT_HTTP)
                if check_fluent_bit_syslog_endpoint_enabled():
                    listOfExtention.append(Tkg_Extention_names.FLUENT_BIT_SYSLOG)
                if check_fluent_bit_elastic_search_endpoint_enabled():
                    listOfExtention.append(Tkg_Extention_names.FLUENT_BIT_ELASTIC)
                if check_fluent_bit_kafka_endpoint_endpoint_enabled():
                    listOfExtention.append(Tkg_Extention_names.FLUENT_BIT_KAFKA)

            else:
                current_app.logger.info("Tanzu extensions  deploy is disabled, no extensions will be deployed")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Tanzu extensions  deploy is disabled, no extensions will be deployed",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200
            if Tkg_version.TKG_VERSION == "1.3":
                extention = deploy_Dot3_ext()
            elif Tkg_version.TKG_VERSION == "1.5":
                extention = deploy_Dot4_ext()
            else:
                current_app.logger.info("Unsupported TKG version")
                d = {
                    "responseType": "ERROR",
                    "msg": "Unsupported TKG version",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if len(listOfExtention) > 1:
                current_app.logger.info("User can only enable one logging extension at a once, please select only one.")
                d = {
                    "responseType": "ERROR",
                    "msg": "User can only enable one logging extension at a once, please select only one.",
                    "ERROR_CODE": 500
                }
                return jsonify(d), 500
            if checkPromethusEnabled():
                listOfExtention.append(Tkg_Extention_names.PROMETHEUS)
                listOfExtention.append(Tkg_Extention_names.GRAFANA)
            if len(listOfExtention) == 0:
                current_app.logger.info("No extension to deploy")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "No extension to deploy ",
                    "ERROR_CODE": 200
                }
                return jsonify(d), 200
            for extention_name in listOfExtention:
                status = extention.deploy(extention_name)
                if status[1] != 200:
                    current_app.logger.info("Failed to deploy extension "+str(status[0].json['msg']))
                    d = {
                        "responseType": "ERROR",
                        "msg": "Failed to deploy extension "+str(status[0].json['msg']),
                        "ERROR_CODE": 500
                    }
                    return jsonify(d), 500
            current_app.logger.info("Successfully deployed "+str(listOfExtention))
            d = {
                "responseType": "SUCCESS",
                "msg": "Successfully deployed extension "+str(listOfExtention),
                "ERROR_CODE": 200
            }
            return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Failed to deploy the extensions " + str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy the extensions " + str(e),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
