import json
import base64
import logging
import requests
import os

from pyVim import connect
from flask import Flask, request, jsonify
from flask import current_app, Blueprint
from pathlib import Path

from common.operation.constants import Env, VcdCSE, MarketPlaceUrl, CertName
from common.constants.alb_api_constants import AlbEndpoint
from common.operation.ShellHelper import runShellCommandWithPolling
from common.operation.vcenter_operations import get_dc, get_ds, getSi
from common.common_utilities import getAviIpFqdnDnsMapping, ping_test, obtain_second_csrf, get_cluster, getNetwork, \
    is_ipv4, getIpFromHost, get_ip_address, getHostFromIP, isAviHaEnabled, checkNtpServerValidity, getProductSlugId, \
    getOvaMarketPlace
from common.model.vcdSpec import VcdMasterSpec
from common.constants.vcd_api_constants import VcdApiEndpoint, VcdHeaders
from common.constants.alb_api_constants import AlbEndpoint

logger = logging.getLogger(__name__)
vcd_precheck = Blueprint("vcd_precheck", __name__, static_folder="vcd_prechecks")


def is_Greenfield(deploy_avi):
    try:
        deploy_avi = str(deploy_avi)
        if deploy_avi.lower() == "true":
            return True
        else:
            return False
    except Exception as e:
        current_app.logger.error(str(e))
        return False


@vcd_precheck.route("/api/tanzu/vcdprecheck", methods=['POST'])
def prechecks_vcd():
    """
    :param spec_file: full path of input spec file
    :param env: env "vcd"
    :return:
    """
    try:
        json_dict = request.get_json(force=True)
        vcdSpec = VcdMasterSpec.parse_obj(json_dict)
        cmd_doc_start = ["systemctl", "start", "docker"]
        try:
            runShellCommandWithPolling(cmd_doc_start)
        except:
            pass
        cmd_doc = ["systemctl", "enable", "docker"]
        runShellCommandWithPolling(cmd_doc)

        common_result = common_prechecks(vcdSpec)
        if not common_result[0]:
            current_app.logger.error(common_result[1])
            d = {
                "responseType": "ERROR",
                "msg": "Pre-check failed " + str(common_result[1]),
                "STATUS_CODE": 500
            }
            return jsonify(d), 500

        deploy_avi = vcdSpec.envSpec.aviCtrlDeploySpec.deployAvi
        if str(deploy_avi).lower() == "false":
            result = avi_spec_prechecks(vcdSpec)
            if not result[0]:
                current_app.logger.error(result[1])
                d = {
                    "responseType": "ERROR",
                    "msg": "Pre-check failed " + str(result[1]),
                    "STATUS_CODE": 500
                }
                return jsonify(d), 500
            current_app.logger.info(result[1])

        cse_result = cse_spec_validation(vcdSpec)
        if not cse_result[0]:
            current_app.logger.error(cse_result[1])
            d = {
                "responseType": "ERROR",
                "msg": "Pre-check failed " + str(cse_result[1]),
                "STATUS_CODE": 500
            }
            return jsonify(d), 500
        current_app.logger.info(cse_result[1])

        d = {
            "responseType": "SUCCESS",
            "msg": "Pre-check performed Successfully for given VCD Environment",
            "STATUS_CODE": 200
        }
        return jsonify(d), 200
    except Exception as e:
        current_app.logger.error(str(e))
        d = {
            "responseType": "ERROR",
            "msg": "Pre-checks Failed",
            "STATUS_CODE": 500
        }
        return jsonify(d), 500


def common_prechecks(vcdSpec):
    """
    check if version if 10.3.1 or greater
    Add check for "NSX-T and vCenter 2 must always be added to VCD under Infra Resources
    Check if a network pool exists and is mapped to Transport zone provided by user
    Check if network pool is mapped to provided NSX Manager
    :param vcdSpec:
    :return: True, if above precheks pass else, Talse
    """
    # check if version if 10.3.1 or greater
    vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
    vcenter = vcdSpec.envSpec.aviNsxCloudSpec.vcenterDetails.vcenterAddress
    nsx = vcdSpec.envSpec.aviNsxCloudSpec.nsxDetails.nsxtAddress
    result = verify_vcd_version(vcd_address)
    if not result[0]:
        return False, result[1]
    current_app.logger.info(result[1])

    vc_response = find_component_in_vcd(vcdSpec, vcenter, True)
    if not vc_response[0]:
        return False, vc_response[1]
    current_app.logger.info(vc_response[1])

    nsx_response = find_component_in_vcd(vcdSpec, nsx, False)
    if not nsx_response[0]:
        return False, nsx_response[1]
    current_app.logger.info(nsx_response[1])

    # check if ntp is valid
    current_app.logger.info("Checking if NTP server is valid")
    ntp_server = vcdSpec.envSpec.infraComponents.ntpServers
    if ntp_server:
        ntp_server = ntp_server.split(',')
        valid_ntp_server = checkNtpServerValidity(ntp_server)
        if valid_ntp_server[1] != 200:
            return False, valid_ntp_server[0]
        else:
            current_app.logger.info("Successfully validated NTP Server.")
    else:
        return False, "Please provide Valid NTP Server"

    # validate vc components under aviNsxCloudSpec
    current_app.logger.info("Validating vCenter components...")
    vc_check = vc_validations(vcdSpec)
    if not vc_check[0]:
        return False, str(vc_check[1])
    current_app.logger.info(vc_check[1])

    # validate network pool provided by user
    network_pool = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcResourceSpec.networkPoolName
    network_pool_response = validate_network_pool(vcd_address, network_pool, vcdSpec)
    if not network_pool_response[0]:
        return False, network_pool_response[1]
    current_app.logger.info(network_pool_response[1])

    return True, "SUCCESS"


def vc_validations(vcdSpec):
    try:
        deploy_avi = vcdSpec.envSpec.aviCtrlDeploySpec.deployAvi
        if str(deploy_avi).lower() == "true":
            vcenter = vcdSpec.envSpec.aviCtrlDeploySpec.vcenterDetails.vcenterAddress
            username = vcdSpec.envSpec.aviCtrlDeploySpec.vcenterDetails.vcenterSsoUser
            password = vcdSpec.envSpec.aviCtrlDeploySpec.vcenterDetails.vcenterSsoPasswordBase64
            datacenter = vcdSpec.envSpec.aviCtrlDeploySpec.vcenterDetails.vcenterDatacenter
            cluster = vcdSpec.envSpec.aviCtrlDeploySpec.vcenterDetails.vcenterCluster
            datastore = vcdSpec.envSpec.aviCtrlDeploySpec.vcenterDetails.vcenterDatastore
            avi_mgmt_nw = vcdSpec.envSpec.aviCtrlDeploySpec.aviMgmtNetwork.aviMgmtNetworkName

            kwargs = {'datacenter': datacenter, 'cluster': cluster, 'datastore': datastore, 'avi_mgmt_nw': avi_mgmt_nw}
            vc_check = validate_vc_components(vcenter, username, password, **kwargs)
            if not vc_check[0]:
                return False, str(vc_check[1])
            current_app.logger.info(vc_check[1])

        vcenter_2 = vcdSpec.envSpec.aviNsxCloudSpec.vcenterDetails.vcenterAddress
        username = vcdSpec.envSpec.aviNsxCloudSpec.vcenterDetails.vcenterSsoUser
        password = vcdSpec.envSpec.aviNsxCloudSpec.vcenterDetails.vcenterSsoPasswordBase64
        create_se = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.serviceEngineGroup.createSeGroup
        kwarg = {}
        if str(create_se).lower() == "true":
            try:
                datacenter = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.serviceEngineGroup.vcenterPlacementDetails.vcenterDatacenter
                cluster = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.serviceEngineGroup.vcenterPlacementDetails.vcenterCluster
                datastore = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.serviceEngineGroup.vcenterPlacementDetails.vcenterDatastore
                kwarg = {'datacenter': datacenter, 'cluster': cluster, 'datastore': datastore}
            except Exception as e:
                current_app.logger.error(str(e))
                return False, "vCenter details missing for creating SE group, please add " \
                              "it in input file and re-run deployment"

        vc2_check = validate_vc_components(vcenter_2, username, password, **kwarg)
        if not vc2_check[0]:
            return False, str(vc2_check[1])
        current_app.logger.info(vc2_check[1])

        return True, "vCenter components validated succesfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while validating vCenter details"


def avi_spec_prechecks(vcdSpec):
    # Check if AVI is already deployed in brown field
    avi_ip = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterIp
    avi_fqdn = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterFqdn
    is_cloud_configured = vcdSpec.envSpec.aviNsxCloudSpec.configureAviNsxtCloud
    nsxt_cloud_name = vcdSpec.envSpec.aviNsxCloudSpec.aviNsxCloudName
    nsxt_cvd_name = vcdSpec.envSpec.aviNsxCloudSpec.nsxtCloudVcdDisplayName
    vcd = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress

    current_app.logger.info("Checking if NSX ALB is deployed...")
    avi_deployed = nsx_alb_deployed(avi_ip, avi_fqdn, vcdSpec)
    if avi_deployed[0]:
        current_app.logger.info("Provided NSX ALB is verified and found version " + str(avi_deployed[1]))
    else:
        return False, "Unable to connect to NSX ALB Controller - " + avi_ip

    ###################### Add AVI license check for brown field
    license_check = validate_avi_license(avi_ip, vcdSpec)
    if license_check[0] is None:
        return False, license_check[1]
    current_app.logger.info(license_check[1])

    certificate_check = validate_avi_cert(vcdSpec)
    if not certificate_check[0]:
        current_app.logger.error(certificate_check[1])
        return False, certificate_check[1]
    current_app.logger.info(certificate_check[1])

    # AVI Display Name Prechecks for VCD
    avi_vcd_check = avi_vcd_display_name_check(vcdSpec)
    if not avi_vcd_check[0]:
        return False, avi_vcd_check[1]
    current_app.logger.info(avi_vcd_check[1])

    # If configureAviNsxtCloud is false, check if cloud is present and in healthy status

    # if is_cloud_configured.lower() == "false":
    current_app.logger.info("Proceeding to check NSX-T cloud configuration status on NSX ALB Controller")
    cloud_list = get_cloud_list(avi_ip, vcdSpec)
    if cloud_list[0] is None:
        return False, cloud_list[1]
    # current_app.logger.info(cloud_list[1])

    cloud_list = cloud_list[0]
    if nsxt_cloud_name not in cloud_list:
        if is_cloud_configured.lower() == "true":
            current_app.logger.info("NSX-T Cloud with name - " + nsxt_cloud_name + " not found on NSX ALB")
            current_app.logger.info("\"configureAviNsxtCloud\" is set to true, SIVT will configure this NSX-T cloud")
        else:
            return False, "NSX-T Cloud with name - " + nsxt_cloud_name + \
                   " not found. Set \"configureAviNsxtCloud\" keyword to true if " \
                   "this needs to be set by SIVT or provide right NSX-T cloud name"
    else:
        current_app.logger.info("NSX-T cloud - " + nsxt_cloud_name + " - is configured on NSX ALB controller")

    if avi_vcd_check[0] and avi_vcd_check[2] is not None:
        nsxt_vcd_reponse = nsxtCloud_vcd_check(vcd, nsxt_cvd_name, vcdSpec)
        if not nsxt_vcd_reponse[0]:
            return False, nsxt_vcd_reponse[1]
        current_app.logger.info(nsxt_vcd_reponse[1])
    else:
        current_app.logger.info("NSX Cloud is not imported to VCD."
                                " Hence, skipping NSX-T Cloud VCD pre-checks")

    return True, "NSX ALB Controller and NSX-T Cloud Pre-checks Passed"


def validate_vc_components(vcenter, vcenter_username, password, **kwargs):
    """
    validate both vc components for aviCtrlDeploySpec, aviNsxCloudSpec and serviceEngineGroup specs
    :param spec:
    :param greenField:
    :return:
    """
    try:
        current_app.logger.info("Performing pre-checks for vCenter - " + vcenter)
        base64_bytes = password.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        vcenter_password = enc_bytes.decode('ascii').rstrip("\n")
        errors = []
        try:
            si = connect.SmartConnectNoSSL(host=vcenter, user=vcenter_username, pwd=vcenter_password)
        except Exception as e:
            current_app.logger.error(str(e))
            return False, "Failed to connect to vCenter - " + vcenter
        if kwargs.__len__() != 0:
            try:
                datacenter_obj = get_dc(si, kwargs["datacenter"])
            except Exception as e:
                current_app.logger.error(str(e))
                return False, "Failed to find Datacenter: " + kwargs["datacenter"]

            try:
                get_ds(si, datacenter_obj, kwargs["datastore"])
            except Exception as e:
                errors.append("Failed to find datastore: " + kwargs["datastore"])

            try:
                cluster_list = get_cluster(si, datacenter_obj, None)
                if not cluster_list or kwargs["cluster"] not in cluster_list:
                    errors.append("Failed to find cluster: " + kwargs["cluster"])
            except Exception as e:
                errors.append(str(e))

            if "avi_mgmt_nw" in kwargs:
                try:
                    getNetwork(datacenter_obj, kwargs["avi_mgmt_nw"])
                except:
                    errors.append("Failed to find network: " + kwargs["avi_mgmt_nw"])

            if errors:
                current_app.logger.error("Pre-check failed with following errors")
                for error in errors:
                    current_app.logger.error(error)
                return False, "Pre-checks Failed for vCenter " + vcenter

        return True, "Pre-checks Passed for vCenter " + vcenter
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while performing prechecks on AVI vCenter"


def cse_spec_validation(vcdSpec):
    try:
        # check if org exists, if yes, check if publish catalog and publish externally are set as true
        vcd = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        org_name = vcdSpec.envSpec.cseSpec.svcOrgSpec.svcOrgName

        org_found = False
        current_app.logger.info("Validating organization name...")
        org_list = get_org_vcd_list(vcdSpec, vcd)
        if org_list[0] is None:
            return False, org_list[1]
        elif org_name not in org_list[0]:
            current_app.logger.info("Provided organization is not yet created in VCD")
        else:
            for record in org_list[2].json()["values"]:
                if record["name"].strip() == org_name:
                    org_found = True
                    break

        if org_found:
            current_app.logger.info("Organization name found in VCD, "
                                    "checking if catalog sharing property enabled")
            validation = validate_org(vcdSpec)
            if not validation[0]:
                if validation[1].__contains__("Catalog sharing property is not enabled"):
                    current_app.logger.warn(validation[1])
                else:
                    return False, validation[1]
            current_app.logger.info(validation[1])
        else:
            current_app.logger.info("Organization not created in VCD yet")

        # Check if provided Storage policies exists in VCD
        current_app.logger.info("Validating Storage Policies...")
        input_policies = []
        input_policy_list = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcResourceSpec.storagePolicySpec.storagePolicies
        default_policy = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcResourceSpec.storagePolicySpec.defaultStoragePolicy
        policies_list = get_storage_policies_vcd_list(vcd, vcdSpec)
        if policies_list[0] is None:
            return False, policies_list[1]
        current_app.logger.info(policies_list[1])

        for input in input_policy_list:
            input_policies.append(input.storagePolicy)

        current_app.logger.info("User provide storage policies - " + str(input_policies))
        vcd_policies = policies_list[0]
        for policy in input_policies:
            if policy not in vcd_policies:
                return False, "Provided Storage Policy not found in VCD - " + policy

        if default_policy not in input_policies:
            return False, "Provided default policy is not added under \"storagePolicies\" section"

        current_app.logger.info("Storage Policies validated successfully")

        """
        Perform validation for serviceEngineGroup section
        createSEG -> false, check if service engine group exists in ALB, fail precheck if not present
        createSEG -> true, check if already imported, if not just give message, this will be created by TF
        """
        current_app.logger.info("Validating Service Engine Group details...")
        seg_found = False
        create_seg = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.serviceEngineGroup.createSeGroup
        seg_name = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.serviceEngineGroup.serviceEngineGroupName
        if str(create_seg).lower() == "false":
            current_app.logger.info("Validating if service engine group is created in NSX ALB")
            result = get_seg_list_nsxCloud(vcdSpec)
            if result[0] is None:
                return False, result[1]
            seg_avi_list = result[0]
            for seg in seg_avi_list:
                if seg == seg_name:
                    seg_found = True
                    current_app.logger.info("Service engine group found in NSX ALB")
                    break
            if not seg_found:
                current_app.logger.error("Provided Service engine group not found in NSX ALB. Set \"createSeGroup\" to "
                                         "true if you wish SIVT to create this service engine group")
                return False, "Service engine group not found in NSX ALB"
        else:
            seg_vcd_display_name = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.\
                serviceEngineGroup.serviceEngineGroupVcdDisplayName
            current_app.logger.info("Validating if provided service engine group is already imported to VCD")
            seg_vcd_list = get_seg_vcd_list(vcd, vcdSpec)
            if seg_vcd_list[0] is None:
                return False, seg_vcd_list[1]
            elif not seg_vcd_list[0]:
                current_app.logger.info("Service Engine Group is not yet imported to VCD")
            else:
                for seg in seg_vcd_list[0]:
                    if seg == seg_vcd_display_name:
                        seg_found = True
                        current_app.logger.info("Service engine group is already imported "
                                                "to VCD with provided VCD object name")
            if not seg_found:
                current_app.logger.info("Service Engine Group is not imported to VCD object - " + seg_vcd_display_name)

        """
        Validate provided Tier-0 gateway
        If importTier0 -> True, Make sure, provided tier0 i.e. tier0Router exists in NSX-T, else fail
        If importTier0 -> False, make sure tier0GatewayName exists in VCD, otherwise fail
        """
        current_app.logger.info("Validating Tier-0 details...")
        tier0_found = False
        import_tier0 = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcGatewaySpec.tier0GatewaySpec.importTier0
        if str(import_tier0.lower()) == "true":
            current_app.logger.info("Validating if Tier-0 exists in NSX-T")
            tier0_router = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcGatewaySpec.tier0GatewaySpec.tier0Router
            tier0_list = get_tier0_nsx_list(vcdSpec)
            if tier0_list[0] is None:
                return False, tier0_list[1]
            elif not tier0_list[0]:
                return False, "No Tier-0 Gateways found on NSX-T Manager, list is empty"
            else:
                for gateway in tier0_list[0]:
                    if gateway == tier0_router:
                        tier0_found = True
                        break

            if tier0_found:
                current_app.logger.info("Tier-0 gateway found on NSX-T - " + tier0_router)
                current_app.logger.info("Tier-0 Gateway validation completed successfully. ")
            else:
                return False, "Provided tier-0 gateway not found on NSX-T - " + tier0_router
        else:
            current_app.logger.info("Validating if Tier-0 is imported to VCD already...")
            gateway_vcd_name = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcGatewaySpec.tier0GatewaySpec.tier0GatewayName
            result = get_tier0_vcd_list(vcd, vcdSpec)
            if result[0] is None:
                return False, result[1]
            elif not result[0]:
                current_app.logger.info("Tier-0 gateways not yet imported to VCD, list is empty")
            else:
                for gateway in result[0]:
                    if gateway == gateway_vcd_name:
                        tier0_found = True
                        break

            if tier0_found:
                current_app.logger.info("Provided Tier0 gateway VCD object exists in VCD - " + gateway_vcd_name)
            else:
                current_app.logger.info("Provided Tier-0 gateway VCD object not found. Set \"importTier0\" to true if "
                                        "this needs to be imported using SIVT")
                return False, "Provided Tier-0 gateway VCD object not found"

        """
        If tier1GatewayName -> exists, make sure enabled=true, connected=true and whether or not the IP range is configured on the Tier-1
        If tier1GatewayName -> doesn't exist, pass the pre-check, SIVT will create tier-1
        """
        current_app.logger.info("Validating Tier-1 gateway...")
        tier1_details = None
        tier1_gateway = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcGatewaySpec.tier1GatewaySpec.tier1GatewayName
        url = VcdApiEndpoint.T1_LIST_VCD.format(vcd=vcd)
        response = run_vcd_api(vcdSpec, url, "json")
        if not response[0]:
            return False, response[1]

        response = response[1]
        for entry in response.json()["values"]:
            if entry["name"] == tier1_gateway:
                current_app.logger.info("Tier-1 gateway is already created in VCD, checking if all properties are set")
                tier1_details = entry
                break

        if tier1_details is None:
            current_app.logger.info("Tier-1 gateway is not yet created in VCD - " + tier1_gateway)
        else:
            isConnected = False
            ip_configured = False
            enabled = False
            # tier1_details = json.loads(tier1_details)
            uplinks = tier1_details["edgeGatewayUplinks"]
            for uplink in uplinks:
                if str(uplink["connected"]).lower() == "true":
                    isConnected = True
                for ip_config in uplink["subnets"]["values"]:
                    if str(ip_config["enabled"]).lower() == "true":
                        enabled = True
                    if ip_config["ipRanges"]["values"]:
                        ip_configured = True
            if isConnected and ip_configured and enabled:
                current_app.logger.info("Tier1 gateway status in VCD:\n"
                                        "\tisConnected - " + str(isConnected) +
                                        "\n\tenabled - " + str(enabled) +
                                        "\n\tip_configured - " + str(ip_configured))
                current_app.logger.info("Tier-1 validations completed successfully")
            else:
                current_app.logger.error("Tier-1 gateway validations failed. Following the status")
                current_app.logger.error("\tisConnected - " + str(isConnected) +
                                         "\n\tenabled - " + str(enabled) +
                                         "\n\tip_configured - " + str(ip_configured))
                return False, "Tier-1 gateway validations Failed"

        """
        validate catalog, skip this precheck if org is not created
        If given catalog doesn't exist, pass precheck as it will be created by TF
        If given catalog exists, it must be associated with user provided org, else fail
        """
        if not org_found:
            current_app.logger.info(
                "Skipping catalog validations as organization - " + org_name + " is not yet created")
        else:
            current_app.logger.info("Validating catalogs...")

            cse_catalog = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgCatalogSpec.cseOvaCatalogName
            k8s_template_catalog = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgCatalogSpec.k8sTemplatCatalogName

            url = VcdApiEndpoint.GET_CATALOG_LIST.format(vcd=vcd)
            catalogs = run_vcd_api(vcdSpec, url, "vnd.vmware.vcloud.query.records+json")
            if not catalogs[0]:
                return False, catalogs[1]
            catalogs = catalogs[1]
            if not catalogs.json()["record"]:
                current_app.logger.info("No Catalogs found in VCD. List is empty")
            else:
                try:
                    for entry in catalogs.json()["record"]:
                        catalog = str(entry["name"]).strip()
                        if catalog == cse_catalog or catalog == k8s_template_catalog:
                            if entry["_type"] == "QueryResultCatalogRecordType" and entry["orgName"] == org_name:
                                current_app.logger.info("Catalog - " + catalog + " is created under org - " + org_name)
                            else:
                                return False, "Catalog - " + catalog + " exists but it's " \
                                                                       "not created under org - " + org_name
                except:
                    pass

            current_app.logger.info("Catalog validations completed")

        return True, "Pre-flight validations for CSE Completed successfully"

    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while performing prechecks for CSE"


def verify_vcd_version(vcd):
    try:
        current_app.logger.info("Checking if VCD version is 10.3.1 or greater....")
        url = VcdApiEndpoint.VCD_API_VERSIONS.format(vcd=vcd)
        # header = {
        #     "Accept": "application/vnd.api+json"
        # }
        header = VcdHeaders.VCD_VERSION
        header = json.loads(header)
        response = requests.get(url, headers=header, verify=False)
        if response.status_code != 200:
            current_app.logger.error("Failed to fetch VCD version details")
            return False, response.text

        for version in response.json()["versionInfo"]:
            if version["version"] == "36.1":
                return True, "VCD version validation successful"

        return False, "VCD version validation check failed. VCD version is found lesser than 10.3.1. "
    except Exception as e:
        return False, str(e)


def validate_t1_gateway(vcdSpec, vcd):
    try:
        tier1_details = None
        tier1_gateway = vcdSpec.envSpec.cseSpec.svcOrgVdcSpec.svcOrgVdcGatewaySpec.tier1GatewaySpec.tier1GatewayName
        url = VcdApiEndpoint.T1_LIST_VCD.format(vcd=vcd)
        response = run_vcd_api(vcdSpec, url, "json")
        if not response[0]:
            return False, response[1]

        response = response[1]
        for entry in response.json()["values"]:
            if entry["name"] == tier1_gateway:
                current_app.logger.info("Tier-1 gateway is already created in VCD, checking if all properties are set")
                tier1_details = entry
                break

        if tier1_details is None:
            current_app.logger.info("Tier-1 gateway is not yet created in VCD - " + tier1_gateway)
            return False, "Tier-1 gateway not found in VCD"
        else:
            isConnected = False
            ip_configured = False
            enabled = False
            # tier1_details = json.loads(tier1_details)
            uplinks = tier1_details["edgeGatewayUplinks"]
            for uplink in uplinks:
                if str(uplink["connected"]).lower() == "true":
                    isConnected = True
                for ip_config in uplink["subnets"]["values"]:
                    if str(ip_config["enabled"]).lower() == "true":
                        enabled = True
                    if ip_config["ipRanges"]["values"]:
                        ip_configured = True
            if isConnected and ip_configured and enabled:
                current_app.logger.info("Tier1 gateway status in VCD:\n"
                                        "\tisConnected - " + str(isConnected) +
                                        "\n\tenabled - " + str(enabled) +
                                        "\n\tip_configured - " + str(ip_configured))
                current_app.logger.info("Tier-1 validations completed successfully")
            else:
                current_app.logger.error("Tier-1 gateway validations failed. Following the status")
                current_app.logger.error("\tisConnected - " + str(isConnected) +
                                         "\n\tenabled - " + str(enabled) +
                                         "\n\tip_configured - " + str(ip_configured))
                return False, "Tier-1 gateway validations Failed"
        return True, "T1 gateway validated successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while validating T1 gateway"


def find_component_in_vcd(spec, component, is_vc):
    """
    The function checks if given component is added in vCenter under 'Infra Resources' section
    :param spec: spec file dict
    :param component: vc to nsx manager ip/fqdn
    :param is_vc: True if component is vcenter, false if it is NSX manager
    :return: True if added else, False
    """
    ip_fqdn_list = []
    vcd = spec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
    ip_fqdn_list.append(component)

    if not is_ipv4(component):  # host -> ip
        ip = getIpFromHost(component)
        if ip is None:
            current_app.logger.warn("Failed to fetch IP address for - " + component)
        else:
            ip_fqdn_list.append(ip)
    else:
        hostname = getHostFromIP(component)
        if hostname is None:
            current_app.logger.warn("failed to fetch hostname - " + component)
        else:
            ip_fqdn_list.append(hostname)
    if is_vc:
        comp_type = "virtualCenter"
    else:
        comp_type = "nsxTManager"

    url = VcdApiEndpoint.VCD_INFRA_COMP.format(vcd=vcd, type=comp_type)
    response = run_vcd_api(spec, url, "vnd.vmware.vcloud.query.records+json")
    if not response[0]:
        return False, response[1]
    response = response[1]

    for record in response.json()["record"]:
        # if record["url"] in ip_fqdn_list:
        # current_app.logger.info(record["name"] + " found in VCD")
        # if given component is VC, check if status is READY
        comp_url = record["url"]
        for s in ip_fqdn_list:
            if comp_url.__contains__(s):
                if not is_vc:
                    return True, record["name"] + " is added to VCD"
                else:
                    if record["status"] == "READY":
                        return True, str(s) + " is added to VCD and the status is " + record["status"]
                    else:
                        return False, str(s) + " is added to VCD and the status is " + record["status"]

    return False, str(component) + " is not added to VCD "


def validate_avi_license(ip, vcdSpec):
    url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    csrf2 = get_csrf(ip, vcdSpec)
    if csrf2 is None:
        return None, "Failed to get csrf from for NSX ALB Controller"

    aviVersion = get_avi_version(ip, vcdSpec)
    if aviVersion[0]:
        aviVersion = aviVersion[1]
    else:
        return None, "Failed to get NSX ALB Controller version details. " + str(aviVersion[1])
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    payload = {}
    response_csrf = requests.request("GET", url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return None, response_csrf.text

    license = response_csrf.json()["default_license_tier"]

    if license == "ENTERPRISE" or license == "ENTERPRISE_WITH_CLOUD_SERVICES":
        return "SUCCESS", "Found " + license + " license for NSX ALB Controller"

    return None, "NSX ALB Controller license validation failed, found license: " + license


def validate_avi_cert(vcdspec):
    ip = vcdspec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterIp
    fqdn = vcdspec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterFqdn
    csrf2 = get_csrf(ip, vcdspec)
    if csrf2 is None:
        return False, "Failed to get csrf from for NSX ALB Controller"

    aviVersion = get_avi_version(ip, vcdspec)
    if aviVersion[0]:
        aviVersion = aviVersion[1]
    else:
        return False, "Failed to get NSX ALB Controller version details. " + str(aviVersion[1])
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }

    payload = {}
    cert_url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=ip)
    response_csrf = requests.request("GET", cert_url, headers=headers, data=payload, verify=False)
    if response_csrf.status_code != 200:
        return False, response_csrf.text

    certificates = response_csrf.json()["portal_configuration"]["sslkeyandcertificate_refs"]

    if not certificates:
        return False, "No certificate found for NSX ALB"

    url = AlbEndpoint.CRUD_SSL_CERT.format(ip=ip)
    response_csrf = requests.request("GET", url, headers=headers, verify=False)
    if response_csrf.status_code != 200:
        current_app.logger.error(response_csrf.text)
        return False, response_csrf.text

    # current_app.logger.error(response_csrf.json())
    for record in response_csrf.json()["results"]:
        if record["url"] in certificates:
            try:
                cert_entries = record["certificate"]["subject_alt_names"]
                # result = validate_san_list(cert_entries, vcdspec)
                if all(x in cert_entries for x in [ip, fqdn]):
                    return True, "NSX ALB Certificate validated successfully"
            except:
                pass

    return False, "Failed to validate NSX ALB Certificate, IPs and FQDN not found Certificate SAN list"


def validate_san_list(cert_list, spec):
    deploy_avi = spec.envSpec.aviCtrlDeploySpec.deployAvi
    ip_fqdn_list = []
    not_found = []
    ip_fqdn_list.append(spec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterIp)
    ip_fqdn_list.append(spec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterFqdn)

    for entry in ip_fqdn_list:
        if entry not in cert_list:
            not_found.append(entry)

    if not_found:
        current_app.logger.error("Following entries were not found in NSX ALB certificate")
        current_app.logger.error(not_found)
        return False, "Certificate validation failed for NSX ALB. "

    return True, "Certificate validated successfully"


def nsx_alb_deployed(ip, fqdn, vcdSpec):
    try:
        dns_server = vcdSpec.envSpec.infraComponents.dnsServersIp
        current_app.logger.info("Ping check NSX ALP IP: " + ip)
        if ping_test("ping -c 1 " + ip) != 0:
            return False, "NSX ALB IP is not responding to ping"

        current_app.logger.info("NSX ALB is responding to ping, checking DNS mapping...")
        avi_controller_fqdn_ip_dict = dict()
        avi_controller_fqdn_ip_dict[fqdn] = ip
        avi_ip_fqdn_dns_entry = getAviIpFqdnDnsMapping(avi_controller_fqdn_ip_dict, dns_server.split(','))
        if avi_ip_fqdn_dns_entry[1] != 200:
            return False, "NSX ALB FQDN and Ip validation failed on DNS Server"
        # current_app.logger.info("DNS mapping for NSX ALB IP and FQDN found")

        current_app.logger.info("Fetching NSX ALB version details...")
        avi_version = get_avi_version(ip, vcdSpec)
        if avi_version[0]:
            return avi_version[0], avi_version[1]

        return False, avi_version[1]

    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while validating existing NSX ALB"


def get_avi_version(ip, vcdSpec):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    avi_username = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviUsername
    str_enc_avi = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviPasswordBase64
    base64_bytes_avi = str_enc_avi.encode('ascii')
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode('ascii').rstrip("\n")

    payload = {
        "username": avi_username,
        "password": password_avi
    }
    modified_payload = json.dumps(payload, indent=4)
    response_avi = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
    if response_avi.status_code != 200:
        current_app.logger.error("Failed to obtain NSX ALB version details")
        return False, response_avi.text

    return True, response_avi.json()["version"]["Version"]


def get_vcd_session(vcdSpec, *args):
    vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
    if len(args) > 0:
        username = args[0]
        str_enc = args[1]
    else:
        username = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdSysAdminUserName
        str_enc = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdSysAdminPasswordBase64
    base64_bytes = str_enc.encode('ascii')
    enc_bytes = base64.b64decode(base64_bytes)
    password = enc_bytes.decode('ascii').rstrip("\n")

    if not username.__contains__("@system"):
        username = username.strip() + "@system"

    url = VcdApiEndpoint.VCD_SESSION_KEY.format(vcd=vcd_address)
    header = VcdHeaders.VCD_SESSION
    header = json.loads(header)
    session = requests.post(url, auth=(username, password), headers=header, verify=False)
    if session.status_code != 200:
        return None, "Failed to retrieve VCD authorization key", session.text

    session_key = session.headers['x-vcloud-authorization']
    access_key = session.headers['X-VMWARE-VCLOUD-ACCESS-TOKEN']

    return session_key, "Successfully obtained VCD authorization key", access_key


def avi_vcd_display_name_check(vcdSpec):
    avi_urls = []
    green = is_Greenfield(vcdSpec.envSpec.aviCtrlDeploySpec.deployAvi)
    vcd_address = vcdSpec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
    avi_vcd_display_name = vcdSpec.envSpec.aviCtrlDeploySpec.aviVcdDisplayName
    if green:
        avi_ha = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.enableAviHa
        if avi_ha.lower() == "false":
            avi_urls.append("https://" + vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviController01Ip)
            avi_urls.append("https://" + vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviController01Fqdn)
        else:
            avi_urls.append("https://" + vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterIp)
            avi_urls.append("https://" + vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterFqdn)
    else:
        avi_urls.append("https://" + vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterIp)
        avi_urls.append("https://" + vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterFqdn)

    url = VcdApiEndpoint.AVI_DISPLAY_NAME.format(vcd=vcd_address)
    response = run_vcd_api(vcdSpec, url, "*")
    if not response[0]:
        current_app.logger.error("Failed to get list of attached NSX ALB Controllers in VCD")
        return False, response[1]
    response = response[1]

    for alb in response.json()["values"]:
        if alb["name"] == avi_vcd_display_name:
            if alb["url"] in avi_urls:
                return True, "NSX ALB VCD object is mapped " \
                             "to given NSX ALB controller " + str(alb["url"]), alb["id"]
            else:
                current_app.logger.error("Please provide correct aviVcdDisplayName to continue")
                return False, "Provided NSX ALB VCD object " + avi_vcd_display_name + " is already mapped " \
                              "to different NSX ALB Controller" + str(alb["url"])
        else:
            if alb["url"] in avi_urls:
                return False, "Provided NSX ALB is already imported to " \
                              " a different object in VCD - " + str(alb["name"])

    return True, "NSX ALB is not imported to VCD with given display name", None


def get_cloud_list(ip, vcdSpec):
    cloud_names = []
    csrf2 = get_csrf(ip, vcdSpec)
    if csrf2 is None:
        return None, "Failed to get csrf from for NSX ALB Controller"

    aviVersion = get_avi_version(ip, vcdSpec)
    if aviVersion[0]:
        aviVersion = aviVersion[1]
    else:
        return None, "Failed to get NSX ALB Controller version details. " + str(aviVersion[1])

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Cookie": csrf2[1],
        "referer": "https://" + ip + "/login",
        "x-avi-version": aviVersion,
        "x-csrftoken": csrf2[0]
    }
    body = {}
    url = "https://" + ip + "/api/cloud"
    response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
    if response_csrf.status_code != 200:
        return None, "Failed to obtain NSX-T cloud names list. " + str(response_csrf.text)
    else:
        for re in response_csrf.json()["results"]:
            cloud_names.append(re['name'])

    if not cloud_names:
        return None, "No NSX-T Cloud configured on NSX ALB Controller - " + ip + " .List is empty"

    return cloud_names, "NSX-T cloud list obtained", response_csrf


def check_nsxtCloud_health(ip, nsxt_cloud_name, vcdSpec):
    try:
        csrf2 = get_csrf(ip, vcdSpec)
        if csrf2 is None:
            return None, "Failed to get csrf from for NSX ALB Controller"

        aviVersion = get_avi_version(ip, vcdSpec)
        if aviVersion[0]:
            aviVersion = aviVersion[1]
        else:
            return None, "Failed to get NSX ALB Controller version details. " + str(aviVersion[1])

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {}
        uuid = None
        url = "https://" + ip + "/api/cloud"
        response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, "Failed to obtain NSX-T cloud names list. " + str(response_csrf.text)

        for re in response_csrf.json()["results"]:
            if re['name'] == nsxt_cloud_name:
                uuid = re["uuid"]
                break

        if uuid is None:
            return None, "Failed to find NSX-T Cloud " + nsxt_cloud_name

        status_url = "https://" + ip + "/api/cloud/" + uuid + "/status"
        response_csrf = requests.request("GET", status_url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, "Failed to get health status for NSX-T Cloud " + nsxt_cloud_name
        if response_csrf.json()["state"] == "CLOUD_STATE_PLACEMENT_READY":
            return "SUCCESS", "NSX-T cloud found in status - " + response_csrf.json()["state"]
        else:
            return None, "NSX-T Cloud status is " + response_csrf.json()["state"]
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while checking health status of provided NSX-T cloud"


def get_csrf(ip, vcdSpec):
    url = "https://" + str(ip) + "/login"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    username = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviUsername
    str_enc_avi = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviPasswordBase64
    base64_bytes_avi = str_enc_avi.encode('ascii')
    enc_bytes_avi = base64.b64decode(base64_bytes_avi)
    password_avi = enc_bytes_avi.decode('ascii').rstrip("\n")
    payload = {
        "username": username,
        "password": password_avi
    }
    modified_payload = json.dumps(payload, indent=4)
    response_csrf = requests.request("POST", url, headers=headers, data=modified_payload, verify=False)
    if response_csrf.status_code != 200:
        return None
    cookies_string = ""
    cookiesString = requests.utils.dict_from_cookiejar(response_csrf.cookies)
    for key, value in cookiesString.items():
        cookies_string += key + "=" + value + "; "
    current_app.config['csrftoken'] = cookiesString['csrftoken']
    return cookiesString['csrftoken'], cookies_string


def nsxtCloud_vcd_check(vcd_address, nsxtCloud_vcd_displayName, vcdSpec):
    try:
        nsxt_imported = False
        url = VcdApiEndpoint.NSXT_CLOUD_DISPLAY_NAME.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "*")
        if not response[0]:
            current_app.logger.error("Failed to get list of NSX-T clouds imported in VCD")
            return False, response[1]
        response = response[1]

        for cloud in response.json()["values"]:
            if cloud["name"] == nsxtCloud_vcd_displayName:
                avi_controller_id = cloud["loadBalancerCloudBacking"]["loadBalancerControllerRef"]["id"]
                nsxt_imported = True
                break

        if nsxt_imported:
            current_app.logger.info("Validating if NSX-T imported in VCD...")
            nsxt_cloud_name = vcdSpec.envSpec.aviNsxCloudSpec.aviNsxCloudName
            if avi_controller_id is None:
                return False, "Failed to find AVI controller ID for provided NSX-T controller imported to VCD"
            url = VcdApiEndpoint.NSXT_CLOUD_IMPORTED_VCD.format(vcd=vcd_address, avi_id=avi_controller_id)
            api_response = run_vcd_api(vcdSpec, url, "*")
            if not api_response[0]:
                current_app.logger.error("Failed to obtain imported NSX-T cloud details")
                return False, api_response[1]
            api_response = api_response[1]
            for record in api_response.json()["values"]:
                if str(record["alreadyImported"]).lower() == "true" and record["displayName"] == nsxt_cloud_name:
                    current_app.logger.info("NSX-T Cloud VCD object - " + nsxtCloud_vcd_displayName +
                                            " - is mapped to correct NSX-T Cloud - " + nsxt_cloud_name)
                else:
                    return False, "NSX-T Cloud VCD object is mapped to different NSX-T Cloud - " + record["displayName"]
        else:
            current_app.logger.info("NSX-T Cloud VCD object - " + nsxtCloud_vcd_displayName + " - not found")
            ######### Add check to see if NSX_cloud is mapped to any other VCD boject
            for cloud in response.json()["values"]:
                # if cloud["name"] == nsxtCloud_vcd_displayName:
                avi_controller_id = cloud["loadBalancerCloudBacking"]["loadBalancerControllerRef"]["id"]
                check = validate_nsxt_cloud_vcd_name(avi_controller_id, vcd_address, vcdSpec)
                if check:
                    return False, "Provided NSX-T Cloud is mapped to different object in VCD - " + cloud["name"]

        return True, "NSX-T cloud validations on VCD passed"
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while looking for NSX-T Cloud VCD display name"


def validate_nsxt_cloud_vcd_name(avi_controller_id, vcd_address, vcdSpec):
    nsxt_cloud_name = vcdSpec.envSpec.aviNsxCloudSpec.aviNsxCloudName
    if avi_controller_id is None:
        return False
    url = VcdApiEndpoint.NSXT_CLOUD_IMPORTED_VCD.format(vcd=vcd_address, avi_id=avi_controller_id)
    api_response = run_vcd_api(vcdSpec, url, "*")
    if not api_response[0]:
        current_app.logger.error("Failed to obtain imported NSX-T cloud details")
        return False, api_response[1]
    api_response = api_response[1]
    for record in api_response.json()["values"]:
        if record["displayName"] == nsxt_cloud_name:
            return True
    return False


def validate_network_pool(vcd, pool_name, vcdspec):
    # np_ip_id = dict()
    pool_id = None
    current_app.logger.info("Checking if network pool exists in VCD...")

    np_list = get_np_list(vcdspec, vcd)

    if np_list[0] is None:
        return False, np_list[1]

    np_list = np_list[0]

    for np in np_list:
        if np["name"] == pool_name:
            current_app.logger.info("Network Pool found in VCD: " + pool_name)
            pool_id = np["id"]
            # np_ip_id[name] = np["id"]

    if pool_id is None:
        return False, "Network pool " + pool_name + " not available in VCD, " \
                                                    "it must be pre-created before starting the deployment"

    transport_zone = vcdspec.envSpec.aviNsxCloudSpec.aviSeTier1Details.nsxtOverlay
    tp_response = validate_transport_zone(vcd, pool_name, pool_id, transport_zone, vcdspec)
    if not tp_response[0]:
        return False, tp_response[1]

    # nw_pool = tp_response[2]
    current_app.logger.info(
        "Network pool - " + pool_name + " - is associated with given transport zone - " + transport_zone)
    response = validate_tp_nsx(vcd, tp_response[1], vcdspec)
    if not response[0]:
        return False, response[1]
    current_app.logger.info(response[1])

    return True, "Network Pool validations completed successfully - " + pool_name


def get_np_list(vcdspec, vcd):
    url = VcdApiEndpoint.LIST_NETWORK_POOLS.format(vcd=vcd)
    response = run_vcd_api(vcdspec, url, "*")
    if not response[0]:
        current_app.logger.error("Failed to list network pools from VCD")
        return None, response[1]
    response = response[1]

    if not response.json()["values"]:
        return None, "Network Pool list is empty"

    return response.json()["values"], "Fetched Network Pool list successfully"


def validate_transport_zone(vcd_address, np_name, np_id, transport_zone, vcdspec):
    current_app.logger.info("Validating network pool association with transport zone...")
    # for name, np_id in np_ip_id_dict.items():
    url = VcdApiEndpoint.NP_DETAILS.format(vcd=vcd_address, id=np_id)
    response = run_vcd_api(vcdspec, url, "*")
    if not response[0]:
        current_app.logger.error("Failed to obtain details for network pool - " + np_name)
        return False, response[1]
    response = response[1]
    tz = response.json()["backing"]["transportZoneRef"]["name"]
    if tz == transport_zone:
        nsxmanager_id = response.json()["backing"]["providerRef"]["id"]
        return True, nsxmanager_id.split(":")[-1]

    return False, "Network pool is not associated with given transport zone - " + transport_zone


def validate_tp_nsx(vcd, nsx_uuid, vcdspec):
    # current_app.logger.info("Validating of transport zone is associated with provided NSX Manager")
    nsx_mgr = vcdspec.envSpec.aviNsxCloudSpec.nsxDetails.nsxtAddress
    nsx_ip = getIpFromHost(nsx_mgr)
    if nsx_ip is None:
        current_app.logger.warn("Failed to fetch IP address for - " + nsx_mgr)

    url = VcdApiEndpoint.VALIDATE_TZ_NSX.format(vcd=vcd, uuid=nsx_uuid)
    response = run_vcd_api(vcdspec, url, "vnd.vmware.vcloud.query.records+json")
    if not response[0]:
        current_app.logger.error("Failed to get NSX manager details")
        return False, response[1]
    response = response[1]

    for record in response.json()["record"]:
        if record["url"].__contains__(nsx_mgr):
            return True, "Transport zone is associated with given NSXT Manager - " + nsx_mgr
        elif nsx_ip is not None and record["url"].__contains__(nsx_ip):
            return True, "Transport zone is associated with given NSXT Manager IP Address- " + nsx_ip

    return False, "Transport zone is not found on given NSXT Manager"


def get_provider_vcd_list(vcd_address, vcdSpec):
    try:
        pvdc_list = []
        url = VcdApiEndpoint.LIST_PROVIDER_VDC.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "json")

        if not response[0]:
            return None, response[1]

        response = response[1]
        for record in response.json()["values"]:
            pvdc_list.append(record["name"])

        return pvdc_list, "Found List successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching PVDC list from VCD"


def get_seg_vcd_list(vcd_address, vcdSpec):
    try:
        seg_list = []
        url = VcdApiEndpoint.LIST_SEG_VCD.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "json")

        if not response[0]:
            return None, response[1]

        response = response[1]
        for record in response.json()["values"]:
            seg_list.append(record["name"])

        return seg_list, "Found SEG List from VCD successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching Service Engine Groups list from VCD"


def get_storage_policies_vcd_list(vcd_address, vcdSpec):
    try:
        policy_list = []
        url = VcdApiEndpoint.LIST_STORAGE_POLICY_VCD.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "json")

        if not response[0]:
            return None, response[1]

        response = response[1]
        for record in response.json()["values"]:
            policy_list.append(record["name"])

        return policy_list, "Obtained Storage Policies List from VCD successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching Service Engine Groups list from VCD"


def get_tier0_vcd_list(vcd_address, vcdSpec):
    try:
        gateway_list = []
        url = VcdApiEndpoint.T0_GATEWAY_LIST_VCD.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "json")

        if not response[0]:
            return None, response[1]

        response = response[1]
        for record in response.json()["values"]:
            gateway_list.append(record["name"])

        return gateway_list, "Obtained T- Gateways from VCD successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching T0 gateways list from VCD"


def get_ip_pool_for_selected_T0(vcd_address, vcdSpec, gateway_name):
    try:
        url = VcdApiEndpoint.T0_GATEWAY_LIST_VCD.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "json")
        start_add = None
        end_add = None
        nw_cidr = None
        if not response[0]:
            return None, response[1]

        response = response[1]
        for record in response.json()["values"]:
            if gateway_name == record["name"]:
                nw_cidr = str(record["subnets"]["values"][0]["gateway"]) + "/" + str(record["subnets"]["values"][0]["prefixLength"])
                start_add = str(record["subnets"]["values"][0]["ipRanges"]["values"][0]["startAddress"])
                end_add = str(record["subnets"]["values"][0]["ipRanges"]["values"][0]["endAddress"])
        if start_add and end_add and nw_cidr:
            return start_add, end_add, nw_cidr, "Obtained start and end IP ranges for the TO gateway: " + gateway_name
        else:
            return None, None, None, "Failed to get start and end IP ranges for the T0 gateway: " + gateway_name
    except Exception as e:
        current_app.logger.error(str(e))
        return None, None, None, "Exception occurred while fetching start and end IP Ranges for T0 gateway: " + gateway_name


def get_tier0_nsx_list(vcdSpec):
    try:
        nsx = vcdSpec.envSpec.aviNsxCloudSpec.nsxDetails.nsxtAddress
        username = vcdSpec.envSpec.aviNsxCloudSpec.nsxDetails.nsxtUser
        str_enc = vcdSpec.envSpec.aviNsxCloudSpec.nsxDetails.nsxtUserPasswordBase64
        base64_bytes = str_enc.encode('ascii')
        enc_bytes = base64.b64decode(base64_bytes)
        password = enc_bytes.decode('ascii').rstrip("\n")
        url = "https://" + nsx + "/policy/api/v1/infra/tier-0s"
        header = {
            'Accept': 'application/json'
        }
        response = requests.get(url, auth=(username, password), headers=header, verify=False)
        if response.status_code != 200:
            current_app.logger.error(response.json())
            return None, "Failed to get tier0 details from NSX, failed to fetch from api "

        list_of_display_name = []
        for result in response.json()["results"]:
            list_of_display_name.append(result["display_name"])
        if len(list_of_display_name) < 1:
            return None, "Failed to get tier0 details, list is empty "

        return list_of_display_name, "Successfully obtained tier0 details from NSX-T"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while Tier-0 list from NSX"


def get_org_vcd_list(vcdSpec, vcd_address):
    try:
        org_list = []
        org_list_full_name = []
        url = VcdApiEndpoint.LIST_ORG_VCD.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "json")

        if not response[0]:
            return None, response[1]

        response_list = response[1]
        for record in response_list.json()["values"]:
            org_list.append(record["name"].strip())
            org_list_full_name.append(record["displayName"].strip())

        return org_list, "Obtained Organizations list from VCD successfully", response_list, org_list_full_name
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching Organizations list from VCD"


def get_org_vdc_list(vcdSpec, vcd_address):
    try:
        org_vdc_list = []
        url = VcdApiEndpoint.LIST_ORG_VDC.format(vcd=vcd_address)
        response = run_vcd_api(vcdSpec, url, "vnd.vmware.vcloud.query.records+json")

        if not response[0]:
            return None, response[1]

        response_list = response[1]
        for record in response_list.json()["record"]:
            org_vdc_list.append(record["name"].strip())

        return org_vdc_list, "Obtained Organizations VDC list from VCD successfully", response_list
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching Organizations VDC list from VCD"


def validate_org(input_spec):
    try:

        org_id = None
        vcd_address = input_spec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        org_name = input_spec.envSpec.cseSpec.svcOrgSpec.svcOrgName
        org_list = get_org_vcd_list(input_spec, vcd_address)
        if org_list[0] is None:
            return False, org_list[1]

        org_list = org_list[2]

        for record in org_list.json()["values"]:
            if record["name"].strip() == org_name:
                org_id = record["id"].strip()
                break

        if org_id is None:
            return False, "Organization not found in VCD - " + org_name

        org_id = org_id.split(":")[-1]
        url = VcdApiEndpoint.VALIDATE_ORG_VCD.format(vcd=vcd_address, org_id=org_id)
        response = run_vcd_api(input_spec, url, "*+json")

        if not response[0]:
            return False, response[1]

        response = response[1]
        validity = response.json()["canPublishCatalogs"]
        if str(validity).lower() == "true":
            return True, "Catalog sharing property is enabled for given organization"

        return False, "Catalog sharing property is not enabled for given organization - " + org_name
    except Exception as e:
        current_app.logger.error(str(e))
        return False, "Exception occurred while validating given org"


def get_catalog_list(vcdspec):
    try:
        catalog_list = []
        org_found = False
        vcd_address = vcdspec.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        org_name = vcdspec.envSpec.cseSpec.svcOrgSpec.svcOrgName

        response = get_org_vcd_list(vcdspec, vcd_address)

        if response[0] is None:
            return None, response[1]

        response = response[2]

        for record in response.json()["values"]:
            if record["name"].strip() == org_name:
                org_found = True
                if record["catalogCount"] <= 0:
                    return None, "No Catalogs found for given organization. List is empty"
                else:
                    current_app.logger.info("Found " + str(record["catalogCount"]) + " catalogs under given org")

        if not org_found:
            return None, "Organization not found in VCD - " + org_name

        current_app.logger.info("Fetching catalog list from Organization - " + org_name)

        url = VcdApiEndpoint.GET_CATALOG_LIST.format(vcd=vcd_address)

        catalogs = run_vcd_api(vcdspec, url, "vnd.vmware.vcloud.query.records+json")

        if not catalogs[0]:
            return None, catalogs[1]

        catalogs = catalogs[1]

        if not catalogs.json()["record"]:
            return None, "No Catalogs found in VCD. List is empty"

        try:
            for entry in catalogs.json()["record"]:
                if entry["_type"] == "QueryResultCatalogRecordType" and entry["orgName"] == org_name:
                    catalog_list.append(entry["name"])
        except Exception as e:
            current_app.logger.error(str(e))
            return None, "No Catalogs found for given organization. List is empty"

        return catalog_list, "successfully obtained catalog list for org - " + org_name

    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching catalog list from given organization"


def get_seg_list_nsxCloud(vcdSpec):
    try:
        green = is_Greenfield(vcdSpec.envSpec.aviCtrlDeploySpec.deployAvi)

        if green:
            ip = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviController01Ip
        else:
            ip = vcdSpec.envSpec.aviCtrlDeploySpec.aviComponentsSpec.aviClusterIp

        nsxt_cloud_name = vcdSpec.envSpec.aviNsxCloudSpec.aviNsxCloudName
        cloud_list = get_cloud_list(ip, vcdSpec)

        if cloud_list[0] is None:
            return None, cloud_list[1]

        cloud_id = None
        response = cloud_list[2]
        for record in response.json()["results"]:
            if record["name"] == nsxt_cloud_name:
                cloud_id = record["uuid"]
                break

        if cloud_id is None:
            return None, "Failed to obtain id of NSX-T Cloud"

        service_engines = get_service_engines(cloud_id, ip, vcdSpec)
        if service_engines[0] is None:
            current_app.logger.error(service_engines[1])
            return None, service_engines[1]
        elif not service_engines[0]:
            return None, "No service engines configured on " + ip + " .List is empty"
        else:
            return service_engines[0], "Obtained service engines from NSX ALB successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching service engine groups from fiven NSX-T"


def get_service_engines(nsxt_cloud_id, avi_ip, inputSpec):
    try:
        service_engines_list = []
        csrf2 = get_csrf(avi_ip, inputSpec)
        if csrf2 is None:
            return None, "Failed to get csrf from for NSX ALB Controller"

        aviVersion = get_avi_version(avi_ip, inputSpec)
        if aviVersion[0]:
            aviVersion = aviVersion[1]
        else:
            return None, "Failed to get NSX ALB Controller version details. " + str(aviVersion[1])

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": csrf2[1],
            "referer": "https://" + avi_ip + "/login",
            "x-avi-version": aviVersion,
            "x-csrftoken": csrf2[0]
        }
        body = {}
        url = "https://" + avi_ip + "/api/serviceenginegroup-inventory/?cloud_ref.uuid=" + nsxt_cloud_id
        response_csrf = requests.request("GET", url, headers=headers, data=body, verify=False)
        if response_csrf.status_code != 200:
            return None, "Failed to obtain service engine groups from given NSX-T Cloud, API failed. " + str(
                response_csrf.text)

        for entry in response_csrf.json()["results"]:
            service_engines_list.append(entry["config"]["name"])

        return service_engines_list, "Obtained Service Engines list from NSX ALB successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Found exception while fetching service engine groups from NSX ALB"


def get_file_MarketPlace(filename, refreshToken, version, group_name):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "refreshToken": refreshToken
    }
    json_object = json.dumps(payload, indent=4)
    sess = requests.request("POST", MarketPlaceUrl.URL + "/api/v1/user/login", headers=headers,
                            data=json_object, verify=False)
    if sess.status_code != 200:
        return None, "Failed to login and obtain csp-auth-token"
    else:
        token = sess.json()["access_token"]

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "csp-auth-token": token
    }

    objectid = None
    slug = "true"

    _solutionName = getProductSlugId(MarketPlaceUrl.VCD_RPODUCT, headers)
    if _solutionName[0] is None:
        return None, "Failed to find product on Marketplace " + str(_solutionName[1])
    solutionName = _solutionName[0]
    product = requests.get(
        MarketPlaceUrl.API_URL + "/products/" + solutionName + "?isSlug=" + slug + "&ownorg=false", headers=headers,
        verify=False)

    if product.status_code != 200:
        return None, "Failed to Obtain Product ID"
    else:
        product_id = product.json()['response']['data']['productid']
        for metalist in product.json()['response']['data']['metafilesList']:
            if metalist["version"] == version and str(metalist["groupname"]).strip("\t") == group_name:
                objectid = metalist["metafileobjectsList"][0]['fileid']
                ovaName = metalist["metafileobjectsList"][0]['filename']
                app_version = metalist['appversion']
                metafileid = metalist['metafileid']

    if (objectid or ovaName or app_version or metafileid) is None:
        return None, "Failed to find the file details in Marketplace"

    current_app.logger.info("Downloading " + ovaName)

    payload = {
        "eulaAccepted": "true",
        "appVersion": app_version,
        "metafileid": metafileid,
        "metafileobjectid": objectid
    }

    json_object = json.dumps(payload, indent=4).replace('\"true\"', 'true')
    presigned_url = requests.request("POST",
                                     MarketPlaceUrl.URL + "/api/v1/products/" + product_id + "/download",
                                     headers=headers, data=json_object, verify=False)
    if presigned_url.status_code != 200:
        return None, "Failed to obtain pre-signed URL"
    else:
        download_url = presigned_url.json()["response"]["presignedurl"]

    response_csfr = requests.request("GET", download_url, headers=headers, verify=False, timeout=600)
    if response_csfr.status_code != 200:
        return None, response_csfr.text
    else:
        os.system("rm -rf " + "/tmp/" + filename)
        with open(r'/tmp/' + filename, 'wb') as f:
            f.write(response_csfr.content)

    return filename, filename + " download from MarketPlace successfully"


def download_kubernetes_ova(file_name, refresh_token, version, baseOs):
    try:
        download_status = getOvaMarketPlace(file_name, refresh_token, version, baseOs)
        if download_status[0] is None:
            return None, download_status[1]
        return file_name, "Downloaded Kubernetes ova successfully - " + file_name
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while downloading kubernetes ova"


def run_vcd_api(vcdspec, url, response_format):
    try:
        vcd_session_key = get_vcd_session(vcdspec)
        if vcd_session_key[0] is None:
            return False, vcd_session_key[1]
        vcd_session_key = vcd_session_key[0]

        header = VcdHeaders.COMMON_HEADER.format(response_format=response_format, vcd_auth_key=vcd_session_key)
        header = json.loads(header)
        response = requests.get(url, headers=header, verify=False)
        if response.status_code != 200:
            current_app.logger.error(response.json())
            return False, response
        return True, response
    except Exception as e:
        current_app.logger.error(str(e))
        return False, str(e)


def run_vcd_api_nsx(vcdspec, url, response_format):
    try:
        vcd_session_key = get_vcd_session(vcdspec)
        if vcd_session_key[0] is None:
            return False, vcd_session_key[1]
        vcd_session_key = vcd_session_key[0]
        header = {
            "Accept": "application/vnd.vmware.vcloud.query.records+json;version=36.1",
            "x-vcloud-authorization": vcd_session_key
        }
        # header = VcdHeaders.COMMON_HEADER.format(response_format=response_format, vcd_auth_key=vcd_session_key)
        #header = json.loads(header)
        response = requests.get(url, headers=header, verify=False)
        if response.status_code != 200:
            current_app.logger.error(response.json())
            return False, response
        return True, response
    except Exception as e:
        current_app.logger.error(str(e))
        return False, str(e)


def getNsxManagerName(specFile):
    try:
        manager_list = []
        url = VcdApiEndpoint.NSX_MANAGER.format(vcd=specFile.envSpec.vcdSpec.vcdComponentSpec.vcdAddress)
        response = run_vcd_api_nsx(specFile, url, "json")

        if not response[0]:
            return None, response[1]

        response = response[1]
        nsx_address = specFile.envSpec.aviNsxCloudSpec.nsxDetails.nsxtAddress
        name = ""
        for record in response.json()["record"]:
            if record['url'] == "https://" + nsx_address:
                manager_list.append(record["name"])
                name = record["name"]
                break
        if len(manager_list) == 0:
            return None, "No nsx manager found"
        out = {
            "nsxManager": name,

        }
        with open("/opt/vmware/arcas/src/vcd/var_nsx.json", "w") as file_out:
            file_out.write(json.dumps(out, indent=4))
        return manager_list, "Obtained Nsx manager List from VCD successfully"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching Nsx manager List from VCD"


def getNetworksList(specFile):
    try:
        network_list = []
        vcd = specFile.envSpec.vcdSpec.vcdComponentSpec.vcdAddress
        org_name = specFile.envSpec.cseSpec.svcOrgSpec.svcOrgName
        url = VcdApiEndpoint.GET_NETWORKS_LIST.format(vcd=vcd)
        response = run_vcd_api(specFile, url, "*")
        if not response[0]:
            return None, response[1]

        response = response[1]

        for entry in response.json()["values"]:
            if str(entry["orgRef"]["name"]).strip() == org_name:
                network_list.append(str(entry["name"]).strip())

        return network_list, "Obtained networks list for given organization"
    except Exception as e:
        current_app.logger.error(str(e))
        return None, "Exception occurred while fetching networks list from VCD for given org"

