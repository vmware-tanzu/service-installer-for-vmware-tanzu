import sys

from flask import Blueprint, current_app, jsonify, request

sys.path.append(".../")
from common.lib.csp_client import CspClient
from common.lib.vmc_client import VmcClient
from common.util.ssl_helper import get_colon_formatted_thumbprint, get_thumbprint

from common.operation.constants import Env, ControllerLocation
from common.common_utilities import checkAirGappedIsEnabled, isEnvTkgs_wcp, isEnvTkgs_ns
from common.util.ssl_helper import decode_from_b64
session_acquire = Blueprint("session_acquire", __name__, static_folder="session")


def fetch_vmc_env(spec):
    try:
        current_app.config['access_token'] = CspClient(current_app.config, spec['envSpec']['sddcRefreshToken']).get_access_token()
        vmc_client = VmcClient(config=current_app.config)
        org = vmc_client.find_org_by_name(spec['envSpec']['orgName'])
        current_app.config['ORG_ID'] = vmc_client.get_org_id(org)
        sddc = vmc_client.find_sddc_by_name(current_app.config['ORG_ID'], spec['envSpec']['sddcName'])
        current_app.config['SDDC_ID'] = vmc_client.get_sddc_id(sddc)
        current_app.config['NSX_REVERSE_PROXY_URL'] = vmc_client.get_nsx_reverse_proxy_url(sddc)
        current_app.config['VC_IP'] = vmc_client.get_vcenter_ip(sddc)
        current_app.config['VC_USER'] = vmc_client.get_vcenter_cloud_user(sddc)
        current_app.config['VC_PASSWORD'] = vmc_client.get_vcenter_cloud_password(sddc)
        #current_app.config['VC_TLS_THUMBPRINT'] = get_colon_formatted_thumbprint(
            #get_thumbprint(current_app.config['VC_IP']))
    except Exception as ex:
        response_body = {
            "responseType": "ERROR",
            "msg": f"Failed to capture VMC setup details; {ex}",
            "ERROR_CODE": 500
        }
        current_app.logger.error(response_body['msg'])
        return jsonify(response_body), 500
    response_body = {
        "responseType": "SUCCESS",
        "msg": "Captured VMC setup details successfully",
        "ERROR_CODE": 200
    }
    current_app.logger.info(response_body['msg'])
    return jsonify(response_body), 200


@session_acquire.route('/api/tanzu/vmc/env/session', methods=['POST'])
def login():
    try:
        env = request.headers['Env']
        if not env:
            raise Exception("No env headers passed")
    except Exception:
        response_body = {
            "responseType": "ERROR",
            "msg": "No env headers passed",
            "ERROR_CODE": "400"
        }
        current_app.logger.error(response_body['msg'])
        return jsonify(response_body), 400

    spec = request.get_json(force=True)
    current_app.config['DEPLOYMENT_PLATFORM'] = env
    try:
        if env == Env.VMC:
            status, code = fetch_vmc_env(spec)
            if code != 200:
                raise Exception(status["msg"])
            current_app.config['VC_DATACENTER'] = spec['envSpec']['sddcDatacenter']
            current_app.config['VC_CLUSTER'] = spec['envSpec']['sddcCluster']
            current_app.config['VC_DATASTORE'] = spec['envSpec']['sddcDatastore']
            current_app.config['RESOURCE_POOL'] = spec['envSpec']['resourcePoolName']
            # TODO: Don't need to populate content lib and ova; We can manage this from spec defaults once it is implemented using pydantic model
            jwt = spec['marketplaceSpec']['refreshToken']
            current_app.config['VC_CONTENT_LIBRARY_NAME'] = ControllerLocation.CONTROLLER_CONTENT_LIBRARY if jwt else \
                spec['envSpec']["contentLibraryName"]
            current_app.config['VC_AVI_OVA_NAME'] = ControllerLocation.CONTROLLER_NAME if jwt else spec['envSpec'][
                "aviOvaName"]
        elif env == Env.VSPHERE or env == Env.VCF:
            current_app.config['VC_IP'] = spec['envSpec']['vcenterDetails']["vcenterAddress"]
            current_app.config['VC_USER'] = spec['envSpec']['vcenterDetails']["vcenterSsoUser"]
            current_app.config['VC_PASSWORD'] = decode_from_b64(
                spec['envSpec']['vcenterDetails']["vcenterSsoPasswordBase64"])
            current_app.config['VC_DATACENTER'] = spec['envSpec']['vcenterDetails']["vcenterDatacenter"]
            current_app.config['VC_CLUSTER'] = spec['envSpec']['vcenterDetails']["vcenterCluster"]
            if not isEnvTkgs_ns(env):
                current_app.config['VC_DATASTORE'] = spec['envSpec']['vcenterDetails']["vcenterDatastore"]
            # TODO: Don't need to populate content lib and ova; We can manage this from spec defaults once it is implemented using pydantic model
            if checkAirGappedIsEnabled(env):
                VC_Content_Library_name = spec['envSpec']['vcenterDetails'][
                    "contentLibraryName"]
                VC_AVI_OVA_NAME = spec['envSpec']['vcenterDetails']["aviOvaName"]
            else:
                jwt = request.get_json(force=True)['envSpec']['marketplaceSpec']['refreshToken']
                if not jwt:
                    VC_Content_Library_name = request.get_json(force=True)['envSpec']['vcenterDetails'][
                        "contentLibraryName"]
                    VC_AVI_OVA_NAME = request.get_json(force=True)['envSpec']['vcenterDetails']["aviOvaName"]
                else:
                    VC_Content_Library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
                    VC_AVI_OVA_NAME = ControllerLocation.CONTROLLER_NAME
            if not VC_Content_Library_name:
                d = {
                    "responseType": "ERROR",
                    "msg": "VC Content Library Name is not provided",
                    "ERROR_CODE": 500
                }
                current_app.logger.error("VC content library name not provided")
                return jsonify(d), 500
            current_app.config['VC_CONTENT_LIBRARY_NAME'] = VC_Content_Library_name
            if not VC_AVI_OVA_NAME:
                d = {
                    "responseType": "ERROR",
                    "msg": "VC AVI Ova Name is not provided",
                    "ERROR_CODE": 500
                }
                current_app.logger.error("VC avi ova name not provided")
                return jsonify(d), 500
            current_app.config['VC_AVI_OVA_NAME'] = VC_AVI_OVA_NAME
            if not (isEnvTkgs_wcp(env) or isEnvTkgs_ns(env)):
                current_app.config['RESOURCE_POOL'] = spec['envSpec']['vcenterDetails']["resourcePoolName"]
        else:
            response_body = {
                "responseType": "ERROR",
                "msg": "Un-recognised env",
                "ERROR_CODE": 500
            }
            current_app.logger.error("Un recognised env")
            return jsonify(response_body), 500
    except Exception as ex:
        response_body = {
            "responseType": "ERROR",
            "msg": str(ex) + " check the input file",
            "ERROR_CODE": 400
        }
        current_app.logger.error("Failed to get environment details please check the input file " + str(ex))
        return jsonify(response_body), 500
    response_body = {
        "responseType": "SUCCESS",
        "msg": "Environment details captured successfully",
        "ERROR_CODE": 200
    }
    current_app.logger.info(response_body['msg'])
    return jsonify(response_body), 200
