# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import logging

import requests
from flask import Blueprint, current_app, jsonify, request
from jinja2 import Template
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from common.common_utilities import (
    createResourceFolderAndWait,
    deployAndConfigureAvi,
    downloadAviController,
    envCheck,
    form_avi_ha_cluster,
    get_avi_version,
    isAviHaEnabled,
    isEnvTkgs_wcp,
    manage_avi_certificates,
    obtain_avi_version,
    ping_check_gateways,
    preChecks,
    seperateNetmaskAndIp,
)
from common.lib.govc_client import GovcClient
from common.operation.constants import CertName, ControllerLocation, Paths, ResourcePoolAndFolderName
from common.operation.vcenter_operations import checkforIpAddress, getSi
from common.util.file_helper import FileHelper
from common.util.local_cmd_helper import LocalCmdHelper

logger = logging.getLogger(__name__)
vcenter_avi_config = Blueprint("vcenter_avi_config", __name__, static_folder="aviConfig")

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@vcenter_avi_config.route("/api/tanzu/vsphere/alb", methods=["POST"])
def aviConfig_vsphere():
    avi_dep = aviDeployment_vsphere()
    if avi_dep[1] != 200:
        current_app.logger.error(str(avi_dep[0].json["msg"]))
        d = {"responseType": "ERROR", "msg": "Failed to deploy avi " + str(avi_dep[0].json["msg"]), "STATUS_CODE": 500}
        return jsonify(d), 500
    avi_cert = aviCertManagement_vsphere()
    if avi_cert[1] != 200:
        current_app.logger.error(str(avi_cert[0].json["msg"]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to manage  avi cert " + str(avi_cert[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Avi configured Successfully", "STATUS_CODE": 200}
    current_app.logger.info("Avi configured Successfully ")
    return jsonify(d), 200


@vcenter_avi_config.route("/api/tanzu/vsphere/alb/config", methods=["POST"])
def aviDeployment_vsphere():
    pre = preChecks()
    if pre[1] != 200:
        current_app.logger.error(pre[0].json["msg"])
        d = {"responseType": "ERROR", "msg": pre[0].json["msg"], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    current_app.logger.info("Performing ping checks for default gateways...")
    if not ping_check_gateways(env):
        d = {"responseType": "ERROR", "msg": "Ping test failed for default gateways", "STATUS_CODE": 500}
        return jsonify(d), 500
    else:
        current_app.logger.info("Ping check passed for default gateways")
    refreshToken = request.get_json(force=True)["envSpec"]["marketplaceSpec"]["refreshToken"]
    if refreshToken:
        download_status = downloadAviController(env)
        if download_status[1] != 200:
            current_app.logger.error(download_status[0])
            d = {"responseType": "ERROR", "msg": download_status[0].json["msg"], "STATUS_CODE": 500}
            return jsonify(d), 500
    else:
        current_app.logger.info(
            "MarketPlace refresh token is not provided, skipping the download of AVI Controller OVA"
        )
    cluster_name = current_app.config["VC_CLUSTER"]
    data_center = current_app.config["VC_DATACENTER"]
    data_store = current_app.config["VC_DATASTORE"]
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    if isEnvTkgs_wcp(env):
        parent_resourcepool = ""
    else:
        parent_resourcepool = current_app.config["RESOURCE_POOL"]
    create = createResourceFolderAndWait(
        vcenter_ip,
        vcenter_username,
        password,
        cluster_name,
        data_center,
        ResourcePoolAndFolderName.AVI_RP_VSPHERE,
        ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE,
        parent_resourcepool,
    )
    if create[1] != 200:
        current_app.logger.error("Failed to create resource pool and folder " + create[0].json["msg"])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to create resource pool " + str(create[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    try:
        if isEnvTkgs_wcp(env):
            control_plan = "dev"
            avi_fqdn = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController01Fqdn"]
            avi_ip = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController01Ip"]
            if isAviHaEnabled(env):
                avi_fqdn2 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController02Fqdn"]
                avi_ip2 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController02Ip"]
                avi_fqdn3 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController03Fqdn"]
                avi_ip3 = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController03Ip"]
            mgmgt_name = request.get_json(force=True)["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkName"]
            mgmt_cidr = request.get_json(force=True)["tkgsComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"]
        else:
            control_plan = request.get_json(force=True)["tkgComponentSpec"]["tkgMgmtComponents"][
                "tkgMgmtDeploymentType"
            ]
            avi_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Fqdn"]
            avi_ip = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Ip"]
            if isAviHaEnabled(env):
                avi_fqdn2 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController02Fqdn"]
                avi_ip2 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController02Ip"]
                avi_fqdn3 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController03Fqdn"]
                avi_ip3 = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController03Ip"]
            mgmgt_name = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkName"]
            mgmt_cidr = request.get_json(force=True)["tkgComponentSpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"]
    except Exception as e:
        current_app.logger.error("Failed to get input " + str(e))
        d = {"responseType": "ERROR", "msg": "Failed to get input " + str(e), "STATUS_CODE": 500}
        return jsonify(d), 500
    if str(control_plan) == "prod":
        control_plan = "dev"
    if isAviHaEnabled(env):
        if not avi_fqdn or not avi_fqdn2 or not avi_fqdn3:
            current_app.logger.error("AVI fqdn not provided, for HA mode 3 fqdns are required")
            d = {
                "responseType": "ERROR",
                "msg": "Avi fqdn not provided, for ha mode 3 fqdns are required",
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
    if not avi_fqdn:
        current_app.logger.error("AVI fqdn not provided")
        d = {"responseType": "ERROR", "msg": "Avi fqdn not provided", "STATUS_CODE": 500}
        return jsonify(d), 500
    if str(control_plan).lower() == "dev":
        if not avi_ip:
            controller_name = ControllerLocation.CONTROLLER_NAME_VSPHERE
            if isAviHaEnabled(env):
                controller_name2 = ControllerLocation.CONTROLLER_NAME_VSPHERE2
                controller_name3 = ControllerLocation.CONTROLLER_NAME_VSPHERE3
            netmask = ""
            ip = ""
            gateway = ""
        else:
            if not mgmt_cidr:
                current_app.logger.error("Mgmt cidr not provided")
                d = {"responseType": "ERROR", "msg": "Mgmt cidr not provided", "STATUS_CODE": 500}
                return jsonify(d), 500
            gateway, netmask = seperateNetmaskAndIp(mgmt_cidr)
            ip = avi_ip
            controller_name = avi_fqdn
            if isAviHaEnabled(env):
                controller_name2 = avi_fqdn2
                controller_name3 = avi_fqdn3
                ip2 = avi_ip2
                ip3 = avi_ip3
        fqdn = avi_fqdn
        if isAviHaEnabled(env):
            fqdn2 = avi_fqdn2
            fqdn3 = avi_fqdn3
        deploy_options = Template(FileHelper.read_resource(Paths.VSPHERE_ALB_DEPLOY_J2))
        FileHelper.write_to_file(
            deploy_options.render(
                ip=ip, netmask=netmask, gateway=gateway, fqdn=fqdn, network=mgmgt_name, vm_name=controller_name
            ),
            Paths.VSPHERE_ALB_DEPLOY_JSON,
        )
        if isAviHaEnabled(env):
            FileHelper.write_to_file(
                deploy_options.render(
                    ip=ip2, netmask=netmask, gateway=gateway, fqdn=fqdn2, network=mgmgt_name, vm_name=controller_name2
                ),
                Paths.VSPHERE_ALB_DEPLOY_JSON2,
            )
            FileHelper.write_to_file(
                deploy_options.render(
                    ip=ip3, netmask=netmask, gateway=gateway, fqdn=fqdn3, network=mgmgt_name, vm_name=controller_name3
                ),
                Paths.VSPHERE_ALB_DEPLOY_JSON3,
            )
        controller_location = (
            "/" + current_app.config["VC_CONTENT_LIBRARY_NAME"] + "/" + current_app.config["VC_AVI_OVA_NAME"]
        )
        controller_location = controller_location.replace(" ", "#remove_me#")
        data_center = "/" + data_center.replace(" ", "#remove_me#")
        data_store = data_store.replace(" ", "#remove_me#")
        if parent_resourcepool is not None:
            rp_pool = (
                data_center
                + "/host/"
                + cluster_name
                + "/Resources/"
                + parent_resourcepool
                + "/"
                + ResourcePoolAndFolderName.AVI_RP_VSPHERE
            )
        else:
            rp_pool = data_center + "/host/" + cluster_name + "/Resources/" + ResourcePoolAndFolderName.AVI_RP_VSPHERE
        rp_pool = rp_pool.replace(" ", "#remove_me#")
        options = f"-options {Paths.VSPHERE_ALB_DEPLOY_JSON} -dc={data_center}\
             -ds={data_store} -folder={ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE} -pool=/{rp_pool}"
        if isAviHaEnabled(env):
            options2 = f"-options {Paths.VSPHERE_ALB_DEPLOY_JSON2} -dc={data_center}\
                 -ds={data_store} -folder={ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE} -pool=/{rp_pool}"
            options3 = f"-options {Paths.VSPHERE_ALB_DEPLOY_JSON3} -dc={data_center}\
                 -ds={data_store} -folder={ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE} -pool=/{rp_pool}"
    else:
        current_app.logger.error("Currently other then dev plan is not supported")
        d = {"responseType": "ERROR", "msg": "Currently other then dev plan is not supported", "STATUS_CODE": 500}
        return jsonify(d), 500
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    avi_version = get_avi_version(env)
    govc_client = GovcClient(current_app.config, LocalCmdHelper())
    dep = deployAndConfigureAvi(
        govc_client=govc_client,
        vm_name=controller_name,
        controller_ova_location=controller_location,
        deploy_options=options,
        performOtherTask=True,
        env=env,
        avi_version=avi_version,
    )
    if dep[1] != 200:
        current_app.logger.error("Failed to deploy and configure avi " + str(dep[0].json["msg"]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to deploy and configure avi  " + str(dep[0].json["msg"]),
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    if isAviHaEnabled(env):
        current_app.logger.info("Deploying 2nd avi controller")
        dep2 = deployAndConfigureAvi(
            govc_client=govc_client,
            vm_name=controller_name2,
            controller_ova_location=controller_location,
            deploy_options=options2,
            performOtherTask=False,
            env=env,
            avi_version=avi_version,
        )
        if dep2[1] != 200:
            current_app.logger.error("Failed to deploy and configure 2nd avi controller  " + str(dep2[0].json["msg"]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy and configure 2nd avi controller " + str(dep2[0].json["msg"]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        current_app.logger.info("Deploying 3rd avi controller")
        dep3 = deployAndConfigureAvi(
            govc_client=govc_client,
            vm_name=controller_name3,
            controller_ova_location=controller_location,
            deploy_options=options3,
            performOtherTask=False,
            env=env,
            avi_version=avi_version,
        )
        if dep3[1] != 200:
            current_app.logger.error("Failed to deploy and configure 3rd avi controller  " + str(dep3[0].json["msg"]))
            d = {
                "responseType": "ERROR",
                "msg": "Failed to deploy and configure 3rd avi controller " + str(dep3[0].json["msg"]),
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500
        res, status = form_avi_ha_cluster(ip, env, None, avi_version)
        if res is None:
            current_app.logger.error("Failed to form avi ha cluster " + str(status))
            d = {"responseType": "ERROR", "msg": "Failed to form avi ha cluster " + str(status), "STATUS_CODE": 500}
            return jsonify(d), 500
    d = {"responseType": "SUCCESS", "msg": "Successfully deployed and configured AVI", "STATUS_CODE": 200}
    return jsonify(d), 200


@vcenter_avi_config.route("/api/tanzu/vsphere/alb/certcreation", methods=["POST"])
def aviCertManagement_vsphere():
    try:
        if current_app.config["VC_PASSWORD"] is None:
            current_app.logger.info("Vc password")
        if current_app.config["VC_USER"] is None:
            current_app.logger.info("Vc user password")
        if current_app.config["VC_IP"] is None:
            current_app.logger.info("Vc ip")
    except Exception as e:
        d = {"responseType": "ERROR", "msg": "Un-Authorized " + str(e), "STATUS_CODE": 401}
        current_app.logger.error("Un-Authorized " + str(e))
        return jsonify(d), 401
    password = current_app.config["VC_PASSWORD"]
    vcenter_username = current_app.config["VC_USER"]
    vcenter_ip = current_app.config["VC_IP"]
    env = envCheck()
    if env[1] != 200:
        current_app.logger.error("Wrong env provided " + env[0])
        d = {"responseType": "ERROR", "msg": "Wrong env provided " + env[0], "STATUS_CODE": 500}
        return jsonify(d), 500
    env = env[0]
    if isEnvTkgs_wcp(env):
        avi_fqdn = request.get_json(force=True)["tkgsComponentSpec"]["aviComponents"]["aviController01Fqdn"]
    else:
        avi_fqdn = request.get_json(force=True)["tkgComponentSpec"]["aviComponents"]["aviController01Fqdn"]
    if not avi_fqdn:
        current_app.logger.error("AVI fqdn not provided")
        d = {"responseType": "ERROR", "msg": "Avi fqdn not provided", "STATUS_CODE": 500}
        return jsonify(d), 500
    ip = checkforIpAddress(getSi(vcenter_ip, vcenter_username, password), avi_fqdn)
    if ip is None:
        current_app.logger.error("Failed to get IP of AVI controller")
        d = {"responseType": "ERROR", "msg": "Failed to get IP of AVI controller", "STATUS_CODE": 500}
        return jsonify(d), 500
    deployed_avi_version = obtain_avi_version(ip, env)
    if deployed_avi_version[0] is None:
        current_app.logger.error("Failed to login and obtain AVI version" + str(deployed_avi_version[1]))
        d = {
            "responseType": "ERROR",
            "msg": "Failed to login and obtain AVI version " + deployed_avi_version[1],
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    aviVersion = deployed_avi_version[0]
    cert = manage_avi_certificates(ip, aviVersion, env, avi_fqdn, CertName.VSPHERE_CERT_NAME)
    if cert[1] != 200:
        current_app.logger.error("Failed to manage-certificate for AVI " + cert[0].json["msg"])
        d = {
            "responseType": "ERROR",
            "msg": "Failed to manage-certificate for AVI " + cert[0].json["msg"],
            "STATUS_CODE": 500,
        }
        return jsonify(d), 500
    isGen = cert[2]
    if isGen:
        current_app.logger.info("Generated and replaced the certificate successfully")
        d = {
            "responseType": "SUCCESS",
            "msg": "Generated and replaced the certificate successfully",
            "STATUS_CODE": 200,
        }
        return jsonify(d), 200
    else:
        current_app.logger.info("Certificate is already generated")
        d = {"responseType": "SUCCESS", "msg": "Certificate is already generated", "STATUS_CODE": 200}
        return jsonify(d), 200
