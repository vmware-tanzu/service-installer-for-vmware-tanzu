import logging
import sys
from flask import Blueprint, jsonify, request
from jinja2 import Template

logger = logging.getLogger(__name__)
avi_config = Blueprint("avi_config", __name__, static_folder="aviConfig")
from flask import current_app

sys.path.append(".../")
from common.operation.constants import Paths
from common.lib.govc_client import GovcClient
from common.operation.constants import ResourcePoolAndFolderName, Vcenter, CertName
from common.common_utilities import preChecks, createResourceFolderAndWait, deployAndConfigureAvi, get_avi_version, \
    envCheck, manage_avi_certificates, validateNetworkAvailable
from common.common_utilities import form_avi_ha_cluster, isAviHaEnabled, preChecks, createResourceFolderAndWait, \
    deployAndConfigureAvi, \
    envCheck, validateNetworkAvailable, downloadAviController
import os
from common.replace_value import replaceValue

from common.operation.constants import SegmentsName
from common.operation.constants import ControllerLocation
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.file_helper import FileHelper


@avi_config.route("/api/tanzu/vmc/alb", methods=['POST'])
def configure_alb():
    avi_dep = deploy_alb()
    if avi_dep[1] != 200:
        current_app.logger.error(str(avi_dep[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy avi " + str(avi_dep[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    avi_cert = manage_alb_certs()
    if avi_cert[1] != 200:
        current_app.logger.error(str(avi_cert[0].json['msg']))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to manage avi cert " + str(avi_cert[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Avi configured Successfully",
        "ERROR_CODE": 200
    }
    current_app.logger.info("Avi configured Successfully ")
    return jsonify(d), 200


@avi_config.route("/api/tanzu/vmc/alb/config", methods=['POST'])
def deploy_alb():
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": pre[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    password = current_app.config['VC_PASSWORD']
    vcenter_username = current_app.config['VC_USER']
    vcenter_ip = current_app.config['VC_IP']
    cluster_name = current_app.config['VC_CLUSTER']
    data_center = current_app.config['VC_DATACENTER']
    data_store = current_app.config['VC_DATASTORE']
    parent_resourcepool = current_app.config['RESOURCE_POOL']
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
    refreshToken = request.get_json(force=True)['marketplaceSpec']['refreshToken']
    if refreshToken:
        download_status = downloadAviController(env)
        if download_status[1] != 200:
            current_app.logger.error(download_status[0])
            d = {
                "responseType": "ERROR",
                "msg": download_status[0],
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    else:
        current_app.logger.info(
            "MarketPlace refresh token is not provided, skipping the download of AVI Controller OVA")
    create = createResourceFolderAndWait(vcenter_ip, vcenter_username, password,
                                         cluster_name, data_center, ResourcePoolAndFolderName.AVI_RP,
                                         ResourcePoolAndFolderName.AVI_Components_FOLDER, parent_resourcepool)
    data_center = data_center.replace(' ', "#remove_me#")
    data_store = data_store.replace(' ', "#remove_me#")
    if parent_resourcepool:
        rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + parent_resourcepool + "/" + ResourcePoolAndFolderName.AVI_RP
    else:
        rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.AVI_RP
    if create[1] != 200:
        current_app.logger.error("Failed to create resource pool and folder " + create[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(create[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    rp_pool = rp_pool.replace(' ', "#remove_me#")
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    if not govc_client.check_network_exists(network_name=SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT):
        current_app.logger.error("Failed to find the network " + SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT)
        d = {
            "responseType": "ERROR",
            "msg": "Failed to find the network " + SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT,
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    control_plan = request.get_json(force=True)['componentSpec']['tkgMgmtSpec']['tkgMgmtDeploymentType']
    if str(control_plan) == "prod":
        control_plan = "dev"
    if str(control_plan).lower() == "dev":
        deploy_options = template_alb_deployment_spec()
        controller_location = "/" + current_app.config['VC_CONTENT_LIBRARY_NAME'] + "/" + current_app.config[
            'VC_AVI_OVA_NAME']
        controller_location = controller_location.replace(' ', "#remove_me#")
        options = f"-options {deploy_options} -dc={data_center} -ds={data_store} -folder={ResourcePoolAndFolderName.AVI_Components_FOLDER} -pool=/{rp_pool}"
    else:
        current_app.logger.error("Currently only dev plan is supported for NSX ALB controller")
        d = {
            "responseType": "ERROR",
            "msg": "Currently only dev plan is supported for NSX ALB controller",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
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
    avi_version = get_avi_version(env)
    dep = deployAndConfigureAvi(govc_client=govc_client, vm_name=ControllerLocation.CONTROLLER_NAME,
                                controller_ova_location=controller_location, deploy_options=options,
                                performOtherTask=True, env=env,
                                avi_version=avi_version)
    if dep[1] != 200:
        current_app.logger.error("Failed to deploy and configure avi ")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy and configure avi  " + str(dep[0].json['msg']),
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    if isAviHaEnabled(env):
        dep = deployAndConfigureAvi(govc_client=govc_client, vm_name=ControllerLocation.CONTROLLER_NAME2,
                                    controller_ova_location=controller_location, deploy_options=options,
                                    performOtherTask=False, env=env,
                                    avi_version=avi_version)
        if dep[1] != 200:
            current_app.logger.error("Failed to deploy and configure 2nd avi " + str(dep[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy and configure avi  " + str(dep[0].json['msg']),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        dep = deployAndConfigureAvi(govc_client=govc_client, vm_name=ControllerLocation.CONTROLLER_NAME3,
                                    controller_ova_location=controller_location, deploy_options=options,
                                    performOtherTask=False, env=env,
                                    avi_version=avi_version)
        if dep[1] != 200:
            current_app.logger.error("Failed to deploy and configure avi " + str(dep[0].json['msg']))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy and configure 3rd avi  " + str(dep[0].json['msg']),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        ip = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME, datacenter_name=data_center)[0]
        if ip is None:
            current_app.logger.error("Failed to get ip of avi controller")
            d = {
                "responseType": "ERROR",
                "msg": "Failed to get ip of avi controller",
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
        res, status = form_avi_ha_cluster(ip, env, govc_client, avi_version)
        if res is None:
            current_app.logger.error("Failed to form avi ha cluster " + str(status))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to form avi ha cluster " + str(status),
                "ERROR_CODE": 500
            }
            return jsonify(d), 500
    d = {
        "responseType": "SUCCESS",
        "msg": "Successfully deployed and configured avi",
        "ERROR_CODE": 200
    }
    return jsonify(d), 200


@avi_config.route("/api/tanzu/vmc/alb/certcreation", methods=['POST'])
def manage_alb_certs():
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": pre[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    data_center = current_app.config['VC_DATACENTER']
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    ip = govc_client.get_vm_ip(ControllerLocation.CONTROLLER_NAME, datacenter_name=data_center)
    if ip is None:
        current_app.logger.error("Failed to get ip of avi controller")
        d = {
            "responseType": "ERROR",
            "msg": "Failed to get ip of avi controller",
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
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
    avi_version = get_avi_version(env)
    cert = manage_avi_certificates(ip[0], avi_version, env, None, CertName.NAME)
    if cert[1] != 200:
        current_app.logger.error("Failed to manage-certificate " + cert[0].json['msg'])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to manage-certificate " + cert[0].json['msg'],
            "ERROR_CODE": 500
        }
        return jsonify(d), 500
    is_gen = cert[2]
    if is_gen:
        current_app.logger.info("Generated and replaced the certificate successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Generated and replaced the certificate successfully",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200
    else:
        current_app.logger.info("Certificate is already generated")
        d = {
            "responseType": "SUCCESS",
            "msg": "Certificate is already generated",
            "ERROR_CODE": 200
        }
        return jsonify(d), 200


def template_alb_deployment_spec():
    deploy_options = Template(FileHelper.read_resource(Paths.VMC_ALB_DEPLOY_J2))
    FileHelper.write_to_file(
        deploy_options.render(network=SegmentsName.DISPLAY_NAME_AVI_MANAGEMENT,
                              vm_name=ControllerLocation.CONTROLLER_NAME),
        Paths.VMC_ALB_DEPLOY_JSON)
    return Paths.VMC_ALB_DEPLOY_JSON
