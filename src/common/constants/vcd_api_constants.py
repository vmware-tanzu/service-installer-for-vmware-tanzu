class VcdApiEndpoint:
    VCD_SESSION_KEY = "https://{vcd}/api/sessions"
    VCD_API_VERSIONS = "https://{vcd}/api/versions"
    VCD_INFRA_COMP = "https://{vcd}/api/query?type={type}&;format=references"
    AVI_DISPLAY_NAME = "https://{vcd}/cloudapi/1.0.0/loadBalancer/controllers"
    NSXT_CLOUD_DISPLAY_NAME = "https://{vcd}/cloudapi/1.0.0/loadBalancer/clouds"
    NSXT_CLOUD_IMPORTED_VCD = "https://{vcd}/cloudapi/1.0.0/nsxAlbResources/importableClouds?filter=(_context=={avi_id})"
    LIST_NETWORK_POOLS = "https://{vcd}/cloudapi/1.0.0/networkPools/networkPoolSummaries"
    NP_DETAILS = "https://{vcd}/cloudapi/1.0.0/networkPools/urn:vcloud:networkpool:{id}"
    VALIDATE_TZ_NSX = "https://{vcd}/api/query?type=nsxTManager&filter=(id=={uuid})"
    AVI_VCD_LIST = "https://{vcd}/cloudapi/1.0.0/loadBalancer/controllers"
    LIST_PROVIDER_VDC = "https://{vcd}/cloudapi/1.0.0/providerVdcs"
    LIST_SEG_VCD = "https://{vcd}/cloudapi/1.0.0/loadBalancer/serviceEngineGroups"
    LIST_STORAGE_POLICY_VCD = "https://{vcd}/cloudapi/1.0.0/pvdcStoragePolicies"
    T0_GATEWAY_LIST_VCD = "https://{vcd}/cloudapi/1.0.0/externalNetworks"
    LIST_ORG_VCD = "https://{vcd}/cloudapi/1.0.0/orgs/"
    VALIDATE_ORG_VCD = "https://{vcd}/api/admin/org/{org_id}/settings/general"
    GET_CATALOG_LIST = "https://{vcd}/api/query?type=catalog"
    T1_LIST_VCD = "https://{vcd}/cloudapi/1.0.0/edgeGateways"
    GET_AVI_CERTIFICATES = "https://{vcd}/cloudapi/1.0.0/ssl/trustedCertificates"
    LIST_ORG_VDC = "https://{vcd}/api/query?type=adminOrgVdc"
    GET_PLUGIN_INFO = "https://{vcd}/cloudapi/extensions/ui"
    UPLOAD_CSE_PLUGIN = "https://{vcd}/cloudapi/extensions/ui/{plugin_id}/plugin"
    NSX_MANAGER = "https://{vcd}/api/query?type=nsxTManager&page=1&pageSize=25&format=records"
    CREATE_INTERFACE = "https://{vcd}/cloudapi/1.0.0/interfaces"
    CREATE_ENTITIES = "https://{vcd}/cloudapi/1.0.0/entityTypes/"
    ENTITY_ACCESS_CONTROL = "https://{vcd}/cloudapi/1.0.0/entityTypes/urn:vcloud:type:vmware:" \
                           "{config_type}:1.0.0/accessControls"
    GET_CSE_SERVER_CONFIG = "https://{vcd}/cloudapi/1.0.0/entities/types/vmware/{config_type}/1.0.0?filter=name==vcdKeConfig"
    CREATE_CSE_SERVER_CONFIG = "https://{vcd}/cloudapi/1.0.0/entityTypes/urn:vcloud:type:vmware:{config_type}:1.0.0"
    REGISTER_ENTITY ="https://{vcd}/cloudapi/1.0.0/entities/{config_id}/resolve"
    REGISTER_SIVT_TOKEN = "https://{vcd}/oauth/provider/{operation}"
    GET_NETWORKS_LIST = "https://{vcd}/cloudapi/1.0.0/orgVdcNetworks"


class VcdHeaders:
    VCD_VERSION = """
    {
        "Accept": "application/vnd.api+json"
    }
    """

    VCD_SESSION = """
    {
        "Accept": "application/*;version=36.1"
    }"""

    COMMON_HEADER = """
    {{
        "Accept": "application/{response_format};version=36.1",
        "x-vcloud-authorization": "{vcd_auth_key}"
    }}"""
