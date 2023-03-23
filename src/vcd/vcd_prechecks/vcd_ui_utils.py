import logging

from flask import Flask, request, jsonify
from flask import current_app, Blueprint

from common.model.vcdSpec import VcdMasterSpec
from common.constants.vcd_api_constants import VcdApiEndpoint, VcdHeaders
from vcd.vcd_prechecks.vcdPrechecks import get_vcd_session, getNsxManagerName, is_Greenfield, run_vcd_api, \
    get_provider_vcd_list, \
    get_seg_vcd_list, \
    get_np_list, get_catalog_list, validate_org, get_tier0_vcd_list, get_storage_policies_vcd_list, \
    get_tier0_nsx_list, get_org_vcd_list, get_seg_list_nsxCloud, get_cloud_list, get_org_vdc_list, \
    get_ip_pool_for_selected_T0, validate_t1_gateway, getNetworksList
from vcd.vcd_prechecks.vcd_utils import upload_avi_cert, upload_cse_ova_to_catalog, upload_kubernetes_ova_to_catalog, \
    configure_cse_plugin, create_server_config_cse, get_access_token_vapp

logger = logging.getLogger(__name__)
vcd_ui_util = Blueprint("vcd_ui_utils", __name__, static_folder="vcd_ui_util")


@vcd_ui_util.route("/api/tanzu/getVCDConnection", methods=['POST'])
def connect_to_vcd():
    """
    This function is for UI to establish connection with VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        result = get_vcd_session(vcdSpec)
        if result[0] is None:
            current_app.logger.error(result[1])
            d = {
                "responseType": "ERROR",
                "msg": result[2],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "VCD Connection established successfully",
            "STATUS_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Exception occurred while trying to establish connection to VCD")
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listNSXTCloud", methods=['POST'])
def list_nsxt_cloud():
    """
    This function is only for UI

    Provide a list of NSX-T clouds from AVI, this will be provided as drop down in UI.
    Users will select this info needed for creating Service Engine groups.
    :return: list of NSX-T cloud names
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        green = is_Greenfield(vcdSpec.envSpec.aviCtrlDeploySpec.deployAvi)

        if green:
            ip = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviController01Ip
        else:
            ip = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterIp

        cloud_list = get_cloud_list(ip, vcdSpec)
        if cloud_list[0] is None:
            if cloud_list[1].__contains__("List is empty"):
                current_app.logger.info(cloud_list[1])
            else:
                current_app.logger.error(cloud_list[1])
                d = {
                    "responseType": "ERROR",
                    "msg": cloud_list[1],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
        else:
            current_app.logger.info(cloud_list[0])
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully obtained NSX-T cloud names list from NSX ALB",
            "STATUS_CODE": 200,
            "NSXT_CLOUDS": cloud_list[0]
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error("Exception occurred while fetching the list of configured NSX-T "
                                 "clouds from NSX ALB Controller")
        d = {
            "responseType": "ERROR",
            "msg": str(e),
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listAviVcd", methods=['POST'])
def get_avi_vcd_list():
    """
    List all NSX ALB display names for NSX ALB's imported to VCD
    :return:
    """
    try:
        avi_list = []
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        url = VcdApiEndpoint.AVI_VCD_LIST.format(vcd=vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress)
        response = run_vcd_api(vcdSpec, url, "*")
        if not response[0]:
            current_app.logger.error("Failed to get names of NSX ALB Controllers imported in VCD")
            d = {
                "responseType": "ERROR",
                "msg": response[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        response = response[1]

        for avi in response.json()["values"]:
            avi_list.append(avi["name"])

        if not avi_list:
            current_app.logger.warn("NSX ALB Controllers are not imported to VCD")
        else:
            current_app.logger.info(avi_list)
        d = {
            "responseType": "SUCCESS",
            "msg": "NSX ALB Controller names obtained successfully",
            "STATUS_CODE": 200,
            "AVI_VCD_LIST": avi_list
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching NSX ALB controllers from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listCloudVcd", methods=['POST'])
def get_nsxt_cloud_vcd_list():
    """
    Get list of NSX-T Clouds configured on NSX ALB
    :return:
    """
    try:
        cloud_list = []
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress

        url = VcdApiEndpoint.NSXT_CLOUD_DISPLAY_NAME.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "*")
        if not response[0]:
            current_app.logger.error("Failed to get list of attached NSX-T clouds imported in VCD")
            d = {
                "responseType": "ERROR",
                "msg": response[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        response = response[1]

        for avi in response.json()["values"]:
            cloud_list.append(avi["name"])

        if not cloud_list:
            current_app.logger.warn("NSXT clouds are not added to VCD")
        else:
            current_app.logger.info(cloud_list)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of NSXT Clouds added to VCD",
            "STATUS_CODE": 200,
            "NSXT_CLOUD_VCD_LIST": cloud_list
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching NSX-T Cloud names from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listProviderVDC", methods=['POST'])
def get_provider_vdc():
    """
    List all provider VDCs from VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        result = get_provider_vcd_list(vcd_address, vcdSpec)

        if result[0] is None:
            current_app.logger.error("Failed to get list of Provider VDC from VCD")
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        pvdc_list = result[0]
        if not pvdc_list:
            current_app.logger.warn("Provider VDCs not found in VCD")
        else:
            current_app.logger.info(pvdc_list)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Provider VDCs from VCD",
            "STATUS_CODE": 200,
            "PVDC_LIST": pvdc_list
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Provider VDC's from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listSegVcd", methods=['POST'])
def get_seg_vcd():
    """
    List all service engine groups already imported to VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        result = get_seg_vcd_list(vcd_address, vcdSpec)

        if result[0] is None:
            current_app.logger.error("Failed to get list of Service Engine Groups from VCD")
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        seg_list = result[0]
        if not seg_list:
            current_app.logger.warn("Service Engine Groups not imported to VCD")
        else:
            current_app.logger.info(seg_list)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Service Engine Groups added to VCD",
            "STATUS_CODE": 200,
            "SEG_VDC_LIST": seg_list
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Service Engine Groups from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listNetworkPoolsVcd", methods=['POST'])
def get_network_pool_vcd():
    """
    Get network pool list from VCD
    :return: Fail if list if empty, lese, list all network pools
    """
    try:
        np_list = []
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        result = get_np_list(vcdSpec, vcd_address)

        if result[0] is None:
            current_app.logger.error("Failed to get Network Pool information from VCD")
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        result = result[0]

        if not result:
            d = {
                "responseType": "ERROR",
                "msg": "No Network pool found on VCD",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        for np in result:
            np_list.append(np["name"])

        current_app.logger.info(np_list)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of network pools from VCD",
            "STATUS_CODE": 200,
            "NP_LIST": np_list
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Network Pools from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listStoragePolicyVcd", methods=['POST'])
def get_storage_policies_vcd():
    """
    Get list of Storage Policies from VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        result = get_storage_policies_vcd_list(vcd_address, vcdSpec)

        if result[0] is None:
            current_app.logger.error("Failed to list Storage policies  from VCD")
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        result = result[0]

        if not result:
            d = {
                "responseType": "ERROR",
                "msg": "No Storage Policy found on VCD",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info(result)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Stoage policies from VCD",
            "STATUS_CODE": 200,
            "STORAGE_POLICY_LIST": result
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Storage Policies from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listTier0Vcd", methods=['POST'])
def get_tier0_vcd():
    """
    List all Tier-0 gateways which are already imported to VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        result = get_tier0_vcd_list(vcd_address, vcdSpec)

        if result[0] is None:
            current_app.logger.error("Failed to list Tier-0 Gateways from VCD")
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        result = result[0]

        if not result:
            d = {
                "responseType": "ERROR",
                "msg": "No Tier-0 gateway found on VCD",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info(result)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Tier-0 Gateways from VCD",
            "STATUS_CODE": 200,
            "Tier0_GATEWAY_VCD": result
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Tier-0 Gateways from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/getIpRangesForT0Gateway", methods=['POST'])
def get_ip_ranges_tier0():
    """
    Fetch start and end IP ranges for T0 gateway already configured on VCD env
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress

        t0_gateway_name = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcGatewaySpec.tier0GatewaySpec.tier0GatewayName
        result = get_ip_pool_for_selected_T0(vcd_address, vcdSpec, t0_gateway_name)

        if result[0] is None or result[1] is None:
            current_app.logger.error("Failed to fetch start and end IP ranges for TO gateway: "+t0_gateway_name)
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        start_add = result[0]
        end_add = result[1]
        cidr = result[2]

        if not result:
            d = {
                "responseType": "ERROR",
                "msg": "No Tier-0 gateway found on VCD",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info(result)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the start and end IP ranges for T0 gateway successfully",
            "STATUS_CODE": 200,
            "T0_GATEWAY_START_IP": start_add,
            "T0_GATEWAY_END_IP": end_add,
            "T0_GATEWAY_NW_CIDR": cidr

        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching start and end IP ranges for T0 Gateway",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/getNsxManager", methods=['POST'])
def get_Nsx_Manager():
    """
    Get Nsx Manager Name
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        current_app.logger.info(vcdSpec)
        result = getNsxManagerName(vcdSpec)

        if result[0] is None:
            current_app.logger.error("Failed to get nsx manager from VCD")
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Nsx manager from VCD",
            "STATUS_CODE": 200,
            "NSX_MANAGER": result
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Nsx manager from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/upload_cse_catalog", methods=['POST'])
def upload_cse_catalog_():
    """
    Get Nsx upload cse catalog
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        result, msg = upload_cse_ova_to_catalog(vcdSpec)
        if not result:
            current_app.logger.error("Failed to upload catalog " + msg)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to upload catalog " + msg,
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "uploaded catalog to vcd",
            "STATUS_CODE": 200,
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while uploading cse catalog",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/upload_k_catalog", methods=['POST'])
def upload_kubernetes_ova_to_catalog_():
    """
    Get Nsx upload k8s ova
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        result, msg = upload_kubernetes_ova_to_catalog(vcdSpec)
        if not result:
            current_app.logger.error("Failed to upload k8s catalog " + msg)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to upload  k8s catalog " + msg,
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "uploaded k8s catalog to vcd",
            "STATUS_CODE": 200,
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while uploading k8s  catalog",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/get_access_token_vapp", methods=['POST'])
def get_access_token_vapp_():
    """
    Get Nsx upload k8s ova
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        result, msg = get_access_token_vapp(vcdSpec)
        if not result:
            current_app.logger.error("Failed to get vapp access token " + msg)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to vapp access token " + msg,
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Fetched vapp access token Successfully",
            "token": result,
            "STATUS_CODE": 200,
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while getting vapp access token",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/configure_cse_plugin", methods=['POST'])
def configure_cse_plugin_():
    """
    Get cse plugin
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        result, msg = configure_cse_plugin(vcdSpec)
        if not result:
            current_app.logger.error("Failed to configure cse plugin " + msg)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to configure cse plugin " + msg,
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Configured cse plugin successfully",
            "STATUS_CODE": 200,
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while Configured cse plugin",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/create_server_config_cse", methods=['POST'])
def create_server_config_cse_():
    """
    Get cse plugin
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        result, msg = create_server_config_cse(vcdSpec)
        if not result:
            current_app.logger.error("Failed to create server config " + msg)
            d = {
                "responseType": "ERROR",
                "msg": "Failed to to create server config " + msg,
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        d = {
            "responseType": "SUCCESS",
            "msg": "Configured to create server config successfully",
            "STATUS_CODE": 200,
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while creating server config",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/upload_avi_cert", methods=['POST'])
def upload_avi_cert_():
    """
    Get Nsx Manager Name
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        result = upload_avi_cert(vcdSpec)

        if result[0] is None:
            current_app.logger.error("Failed to upload avi cert to VCD")
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "uploaded avi cert  to VCD",
            "STATUS_CODE": 200,
            "Tier0_GATEWAY_VCD": result
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while uploading avi cert to  VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listTier0Nsx", methods=['POST'])
def get_tier0_nsx():
    """
    List all Tier-0 gateways from NSX Manager
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        result = get_tier0_nsx_list(vcdSpec)

        if result[0] is None:
            current_app.logger.error(result[1])
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        result = result[0]

        if not result:
            d = {
                "responseType": "ERROR",
                "msg": "No Tier-0 gateway found on NSX, list is empty",
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        else:
            current_app.logger.info(result)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Tier-0 Gateways from NSX",
            "STATUS_CODE": 200,
            "Tier0_GATEWAY_NSX": result
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Tier-0 Gateways from NSX",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listOrgVcd", methods=['POST'])
def get_org_vcd():
    """
    Get organization list from VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress

        result = get_org_vcd_list(vcdSpec, vcd_address)

        if result[0] is None:
            current_app.logger.error(result[1])
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        org_list = result[0]
        org_list_fullname = result[3]

        if not result:
            current_app.logger.info("Org list is empty")
        else:
            current_app.logger.info(org_list)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Organizations from VCD",
            "STATUS_CODE": 200,
            "ORG_LIST_VCD": org_list,
            "ORG_LIST_VCD_FULLNAME": org_list_fullname
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching organization list from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listOrgVdc", methods=['POST'])
def get_org_vdc():
    """
    Get organization VDC list from VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress

        result = get_org_vdc_list(vcdSpec, vcd_address)

        if result[0] is None:
            current_app.logger.error(result[1])
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        org_list = result[0]

        if not result:
            current_app.logger.info("Org VDC list is empty")
        else:
            current_app.logger.info(org_list)

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Organizations VDC from VCD",
            "STATUS_CODE": 200,
            "ORG_LIST_VCD": org_list
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching organization VDC list from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/getSegAvi", methods=['POST'])
def get_seg_nsxcloud():
    """
    List all the service engine groups from NSX ALB for associated with user provided NSX-T Cloud
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        seg_list = get_seg_list_nsxCloud(vcdSpec)
        if seg_list[0] is None:
            if seg_list[1].__contains__("List is empty"):
                current_app.logger.info(seg_list[1])
            else:
                d = {
                    "responseType": "ERROR",
                    "msg": seg_list[1],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
        else:
            current_app.logger.info(seg_list[0])
        d = {
            "responseType": "SUCCESS",
            "msg": "Successfully obtained the list of service engines groups from NSX ALB for given NSX-T cloud",
            "STATUS_CODE": 200,
            "SEG_LIST_AVI": seg_list[0]
        }
        return jsonify(d), 200

    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching service engine groups from NSX ALB",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/validateOrgVcd", methods=['POST'])
def validate_existing_org():
    """
    To Validate whether an existing org has catalog sharing property enabled or not
    :return: success is canPublishCatalogs is "true" else, false
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        response = validate_org(vcdSpec)

        if not response[0]:
            d = {
                "responseType": "ERROR",
                "msg": response[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": response[1],
            "STATUS_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while validating the organization",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listCatalogVcd", methods=['POST'])
def list_catalog_vcd():
    """
    Obtain the list of catalogs associated with given org
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        catalog_list = []

        result = get_catalog_list(vcdSpec)

        if result[0] is None:
            if not result[1].__contains__("List is empty"):
                d = {
                    "responseType": "ERROR",
                    "msg": result[1],
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            else:
                current_app.logger.info(result[1])
        else:
            current_app.logger.info(result[0])

        catalog_list = result[0]

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained Catalog list successfully",
            "STATUS_CODE": 200,
            "CATALOG_LIST": catalog_list
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching catalogs list from ",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listTier1Vcd", methods=['POST'])
def get_tier1_vcd():
    """
    List all Tier-1 gateways which are already imported to VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        result = validate_t1_gateway(vcdSpec, vcd_address)

        if not result[0]:
            current_app.logger.error(result[1])
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": "Obtained the list of Tier-0 Gateways from VCD",
            "STATUS_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetching Tier-0 Gateways from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


@vcd_ui_util.route("/api/tanzu/listNetworksOrg", methods=['POST'])
def get_networks_vcdOrg():
    """
    List all Networks for the given org from VCD
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)

        result = getNetworksList(vcdSpec)

        if result[0] is None:
            current_app.logger.error(result[1])
            d = {
                "responseType": "ERROR",
                "msg": result[1],
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        d = {
            "responseType": "SUCCESS",
            "msg": result[1],
            "STATUS_CODE": 200,
            "NETWORKS_LIST": result[0]
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Exception occurred while fetchingNetworks from VCD",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500
