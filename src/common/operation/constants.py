# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import os


class Constants:
    REFRESH_TOKEN = None
    ORG_ID = None
    SDDC_ID = None
    VC_IP = None


class Status:
    PASS = "PASS"
    FAIL = "FAIL"


class Type:
    WORKLOAD = "workload"
    MANAGEMENT = "management"
    SHARED = "shared"
    AVI = "avi"


class SegmentsName:
    DISPLAY_NAME_AVI_MANAGEMENT = "tkgvmc-avi-mgmt-segment"
    DISPLAY_NAME_CLUSTER_VIP = "tkgvmc-clustervip-segment01"
    DISPLAY_NAME_TKG_WORKLOAD = "tkgvmc-workload-segment01"
    DISPLAY_NAME_TKG_WORKLOAD_DATA_SEGMENT = "tkgvmc-workload-data-segment01"
    DISPLAY_NAME_TKG_SharedService_Segment = "tkgvmc-shared-service-segment"
    DISPLAY_NAME_AVI_DATA_SEGMENT = "tkgvmc-mgmtdata-segment"

    DISPLAY_NAME_VCF_TKG_SharedService_Segment = "tkg-vsphere-nsxt-shared-service-segment"


class VCF:
    DHCP_SERVER_NAME = "tkg-vsphere-nsxt-dhcp-server"
    ARCAS_GROUP = "arcas"
    ARCAS_BACKEND_GROUP = "arcas_backend"
    NSXT_GROUP = "nsxt"
    ESXI_GROUP = "tkg-vsphere-nsxt-esxi"
    ESXI_FW = "tkg-vsphere-nsxt-tkg-esxi"


class EnvType:
    TKGS_NS = "tkgs-ns"
    TKGS_WCP = "tkgs-wcp"
    TKGM = "tkgm"
    TKGS_TKC_KIND = "TanzuKubernetesCluster"
    TKGS_CLUSTER_CLASS_KIND = "ClusterClass"


class GroupNameCgw:
    DISPLAY_NAME_AVI_Management_Network_Group_CGW = "tkgvmc-avimgmt"
    DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_CGW = "tkgvmc-tkgclustervip"
    DISPLAY_NAME_TKG_Management_Network_Group_CGW = "tkgvmc-tkgmgmt"
    DISPLAY_NAME_TKG_Workload_Networks_Group_CGW = "tkgvmc-tkg-workload"
    DISPLAY_NAME_TKG_SharedService_Group_CGW = "tkgvmc-shared-service"
    DISPLAY_NAME_DNS_IPs_Group = "tkgvmc-infra-dns-ips"
    DISPLAY_NAME_NTP_IPs_Group = "tkgvmc-infra-ntp-ips"
    DISPLAY_NAME_vCenter_IP_Group = "tkgvmc-infra-vcenter-ip"

    DISPLAY_NAME_VCF_AVI_Management_Network_Group_CGW = "tkg-vsphere-nsxt-avimgmt"
    DISPLAY_NAME_VCF_TKG_Management_Network_Group_CGW = "tkg-vsphere-nsxt-tkgmgmt"
    DISPLAY_NAME_VCF_CLUSTER_VIP_NETWORK_Group_CGW = "tkg-vsphere-nsxt-tkgclustervip"
    DISPLAY_NAME_VCF_TKG_SharedService_Group_CGW = "tkg-vsphere-nsxt-shared-service"
    DISPLAY_NAME_VCF_DNS_IPs_Group = "tkg-vsphere-nsxt-infra-dns-ips"
    DISPLAY_NAME_VCF_NTP_IPs_Group = "tkg-vsphere-nsxt-infra-ntp-ips"
    DISPLAY_NAME_VCF_vCenter_IP_Group = "tkg-vsphere-nsxt-infra-vcenter-ip"
    DISPLAY_NAME_VCF_TKG_Workload_Networks_Group_CGW = "tkg-vsphere-nsxt-tkg-workload"


class GroupNameMgw:
    DISPLAY_NAME_TKG_Management_Network_Group_Mgw = "tkgvmc-tkgmgmt"
    DISPLAY_NAME_CLUSTER_VIP_NETWORK_Group_MGW = "tkgvmc-tkgclustervip"
    DISPLAY_NAME_TKG_Workload_Networks_Group_Mgw = "tkgvmc-tkg-workload"
    DISPLAY_NAME_AVI_Management_Network_Group_Mgw = "tkgvmc-avimgmt"
    DISPLAY_NAME_Tkg_Shared_Network_Group_Mgw = "tkgvmc-shared-service"


class ServiceName:
    KUBE_VIP_SERVICE = "tkgvmc-kube-api"
    KUBE_VIP_VCF_SERVICE = "tkg-vsphere-nsxt-kube-api"
    ARCAS_SVC = "arcas-svc"
    ARCAS_BACKEND_SVC = "arcas-backend-svc"
    SIVT_SERVICE_VIP = "sivt-virtual-service-vip"
    SIVT_SERVICE = "sivt-virtual-service"


class Ports:
    BACKEND = "5000"
    UI = "8888"
    KUBE_VIP = "6443"


class VrfType:
    GLOBAL = "global"
    MANAGEMENT = "management"


class Policy_Name:
    POLICY_NAME = "tkg-vsphere-nsxt-policy"


class FirewallRuleCgw:
    DISPLAY_NAME_WORKLOAD_TKG_and_AVI_DNS = "tkgvmc-tkgworkload01-tkginfra"
    DISPLAY_NAME_TKG_WORKLOAD_to_vCenter = "tkgvmc-tkg-workload-to-vcenter"
    DISPLAY_NAME_WORKLOAD_TKG_and_AVI_to_Internet = "tkgvmc-workload-tkg-external"

    DISPLAY_NAME_VCF_TKG_and_AVI_DNS = "tkg-vsphere-nsxt-tkg-avi-to-dns"
    DISPLAY_NAME_VCF_TKG_CLUSTER_VIP_CGW = "tkg-vsphere-nsxt-tkgcluster-vip"
    DISPLAY_NAME_VCF_TKG_and_AVI_NTP = "tkg-vsphere-nsxt-tkginfra-to-ntp"
    DISPLAY_NAME_VCF_TKG_and_AVI_to_vCenter = "tkg-vsphere-nsxt-tkg-avi-to-vcenter"
    DISPLAY_NAME_VCF_TKG_and_AVI_to_Internet = "tkg-vsphere-nsxt-tkg-external"
    DISPLAY_NAME_VCF_TKG_and_TKGtoAVIMgmt = "tkg-vsphere-nsxt-tkg-to-avimgmt"
    DISPLAY_NAME_VCF_TKG_and_AVIMgmt = "tkg-vsphere-nsxt-avimgmt"
    DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_DNS = "tkg-vsphere-nsxt-tkgworkload01-tkginfra"
    DISPLAY_NAME_VCF_TKG_WORKLOAD_to_vCenter = "tkg-vsphere-nsxt-tkgworkload01-vcenter"
    DISPLAY_NAME_VCF_WORKLOAD_TKG_and_AVI_to_Internet = "tkg-vsphere-nsxt-workload-tkg-external"
    DISPLAY_NAME_VCF_ARCAS_UI = "arcas-ui"
    DISPLAY_NAME_VCF_ARCAS_BACKEND = "arcas-backend"


class FirewallRuleMgw:
    DISPLAY_NAME_WORKLOAD_TKG_and_AVItovCenter = "tkgvmc-tkgworkload01-to-vcenter"


class ResourcePoolAndFolderName:
    AVI_Components_FOLDER = "tkg-vmc-alb-components"
    AVI_Components_FOLDER_VSPHERE = "tkg-vsphere-alb-components"
    Template_Automation_Folder = "tkg-vmc-templates"
    TKG_Mgmt_Components_Folder = "tkg-vmc-tkg-mgmt"
    TKG_Mgmt_Components_Folder_VSPHERE = "tkg-vsphere-tkg-mgmt"
    AVI_RP = "tkg-vmc-alb-components"
    AVI_RP_VSPHERE = "tkg-vsphere-alb-components"
    TKG_Mgmt_RP = "tkg-vmc-tkg-mgmt"
    TKG_Mgmt_RP_VSPHERE = "tkg-vsphere-tkg-mgmt"
    SHARED_FOLDER_NAME = "tkg-vmc-shared-services"
    SHARED_FOLDER_NAME_VSPHERE = "tkg-vsphere-shared-services"
    SHARED_RESOURCE_POOL_NAME = "tkg-vmc-shared-services"
    SHARED_RESOURCE_POOL_NAME_VCENTER = "tkg-vsphere-shared-services"
    WORKLOAD_FOLDER = "tkg-vmc-workload"
    WORKLOAD_FOLDER_VSPHERE = "tkg-vsphere-workload"
    WORKLOAD_RESOURCE_POOL = "tkg-vmc-workload"
    WORKLOAD_RESOURCE_POOL_VSPHERE = "tkg-vsphere-workload"


class Avi_Version:
    VSPHERE_AVI_VERSION = "22.1.4"
    VMC_AVI_VERSION = "22.1.4"
    AVI_VERSION_UPDATE_THREE = "22.1.4"
    AVI_VERSION_UPDATE_TWO = "22.1.4"


class ControllerLocation:
    CONTROLLER_CONTENT_LIBRARY = "TanzuAutomation-Lib"
    CONTENT_LIBRARY_OVA_NAME = "avi-controller"
    CONTROLLER_NAME = "avi-controller"
    CONTROLLER_NAME2 = "avi-controller2"
    CONTROLLER_NAME3 = "avi-controller3"
    CONTROLLER_NAME_VSPHERE = "tkg-vsphere-avi-ctrl-01"
    CONTROLLER_NAME_VSPHERE2 = "tkg-vsphere-avi-ctrl-02"
    CONTROLLER_NAME_VSPHERE3 = "tkg-vsphere-avi-ctrl-03"
    CONTROLLER_SE_NAME = "tkgvmc-tkgmgmt-se01"
    CONTROLLER_SE_NAME2 = "tkgvmc-tkgmgmt-se02"
    CONTROLLER_SE_WORKLOAD_NAME = "tkgvmc-workload-se01"
    CONTROLLER_SE_WORKLOAD_NAME2 = "tkgvmc-workload-se02"
    CONTROLLER_SE_WORKLOAD_NAME_VSPHERE = "tkgvsphere-workload-se01"
    CONTROLLER_SE_WORKLOAD_NAME2_VSPHERE = "tkgvsphere-workload-se02"
    SE_OVA_TEMPLATE_NAME = "tkgvmc-cloud01-avi-se"
    SUBSCRIBED_CONTENT_LIBRARY = "SubscribedAutomation-Lib"
    SUBSCRIBED_CONTENT_LIBRARY_URL = "https://wp-content.vmware.com/v2/latest/lib.json"
    MARKETPLACE_CONTROLLER_FILENAME = "controller-20-1641297052015.ova"
    MARKETPLACE_AVI_SOLUTION_NAME = "nsx-advanced-load-balancer-1"
    OVA_DOWNLOAD_PATH = "/tmp"
    SUBSCRIBED_CONTENT_LIBRARY_THUMBPRINT = "B2:52:9E:4D:57:9F:EA:53:4D:A0:0B:7F:D4:7E:55:91:56:C0:64:BB"
    SUBSCRIBED_CONTENT_LIBRARY_THUMBPRINT8 = "50:ff:be:b6:a4:89:60:82:65:63:00:5e:f8:6f:9c:e9:ca:6d:50:e6"


class MarketPlaceUrl:
    URL = "https://gtw.marketplace.cloud.vmware.com"
    API_URL = "https://api.marketplace.cloud.vmware.com"
    PRODUCT_SEARCH_URL = (
        API_URL + "/products?managed=false&filters={%22Publishers%22:[%22318e72f1-7215-41fa-9016-ef4528b82d0a%22]}"
    )
    TANZU_PRODUCT = "Tanzu Kubernetes Grid"
    AVI_PRODUCT = "NSX Advanced Load Balancer"
    VCD_RPODUCT = "Service Installer for VMware Tanzu"
    TKG_PRODUCT_VERSION_LATEST = "2.3.0"


class KubernetesOva:
    UBUNTU_KUBERNETES_FILE_NAME = "ubuntu-2004-kube-v1.24.10+vmware.1-tkg.1-765d418b72c247c2310384e640ee075e.ova"
    PHOTON_KUBERNETES_FILE_NAME = "photon-3-kube-v1.24.10+vmware.1-tkg.1-fbb49de6d1bf1f05a1c3711dea8b9330.ova"
    PHOTON_KUBERNETES_TEMPLATE_FILE_NAME = "photon-3-kube-v1.24.10+vmware.1"
    UBUNTU_KUBERNETES__TEMPLATE_FILE_NAME = "ubuntu-2004-kube-v1.24.10+vmware.1"
    MARKETPLACE_KUBERNETES_SOLUTION_NAME = "tanzu-kubernetes-grid-1-1"
    MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME = "arcas-ubuntu-kube"
    MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME = "arcas-photon-kube"
    MARKETPLACE_PHOTON_GROUPNAME = "Photon-OVA"
    MARKETPLACE_UBUTNU_GROUPNAME = "Ubuntu-OVA"
    KUBERNETES_OVA_LATEST_VERSION = "v1.26.5"


class RegexPattern:
    SWITCH_CONTEXT_KUBECTL = r"(kubectl\s*([^\n\r]*[^']))"
    running = "running"
    RUNNING = "Running"
    RECONCILE_SUCCEEDED = "Reconcile succeeded"
    RECONCILE_FAILED = "Reconcile failed"
    IP_ADDRESS = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    URL_REGEX_PORT = "(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*"
    deleting = "deleting"


class Cloud:
    CLOUD_NAME = "tkgvmc-cloud01"
    DEFAULT_CLOUD_NAME_VSPHERE = "Default-Cloud"
    CLOUD_NAME_VSPHERE = "tkgvsphere-cloud01"
    CLOUD_NAME_NSXT = "tkgnsxt-cloud01"
    SE_GROUP_NAME = "tkgvmc-tkgmgmt-group01"
    SE_GROUP_NAME_VSPHERE = "tkgvsphere-tkgmgmt-group01"
    SE_GROUP_NAME_NSXT = "tkgnsxt-tkgmgmt-group01"
    DEFAULT_SE_GROUP_NAME_VSPHERE = "Default-Group"
    SE_WORKLOAD_GROUP_NAME = "tkgvmc-tkgworkload-group01"
    SE_WORKLOAD_GROUP_NAME_VSPHERE = "tkgvsphere-tkgworkload-group01"
    SE_WORKLOAD_GROUP_NAME_NSXT = "tkgnsxt-tkgworkload-group01"
    WIP_NETWORK_NAME = "tkgvmc-tkgmgmt-data-network01"
    WIP_CLUSTER_NETWORK_NAME = "tkgvmc-cluster-data-network01"
    WIP_WORKLOAD_NETWORK_NAME = "tkgworkload-group01-data-network"
    IPAM_NAME = "tkgvmc-tkgmgmt-ipam01"
    IPAM_NAME_VSPHERE = "tkgvsphere-tkgmgmt-ipam01"
    mgmtVipNetwork = "tkgvmc-tkgmgmt-vip_network"


class Vcenter:
    CLUSTER = "Cluster-1"
    DATA_STORE = "WorkloadDatastore"
    DATA_CENTER = "SDDC-Datacenter"


class Extension:
    TKG_EXTENSION_LOCATION = "/root/tkg-extensions-v1.3.1+vmware.1/"
    CONTOUR_LOCATION = TKG_EXTENSION_LOCATION + "extensions/ingress/contour"
    HARBOR_LOCATION = TKG_EXTENSION_LOCATION + "extensions/registry/harbor"
    FLUENT_BIT_LOCATION = TKG_EXTENSION_LOCATION + "extensions/logging/fluent-bit"
    PROMETHUS_LOCATION = TKG_EXTENSION_LOCATION + "extensions/monitoring/prometheus"
    GRAFANA_LOCATION = TKG_EXTENSION_LOCATION + "extensions/monitoring/grafana"
    VELERO_PLUGIN_IMAGE_LOCATION = "velero/velero-plugin-for-aws:v1.5.5_vmware.1"
    VELERO_CONTAINER_IMAGE = "velero/velero:v1.9.7_vmware.1"
    CERT_MANAGER_LOCATION = TKG_EXTENSION_LOCATION + "cert-manager"
    CERT_MANAGER_CA_INJECTOR = "cert-manager-cainjector:v0.16.1_vmware.1"
    CERT_MANAGER_CONTROLLER = "cert-manager-controller:v0.16.1_vmware.1"
    CERT_MANAGER_WEB_HOOK = "cert-manager-webhook:v0.16.1_vmware.1"
    APP_EXTENSION = "tkg-extensions-templates:v1.3.1_vmware.1"
    BOM_LOCATION_14 = "/root/.config/tanzu/tkg/bom/tkg-bom-v2.4.0.yaml"
    FIPS_BOM_LOCATION_14 = "/root/.config/tanzu/tkg/bom/tkg-bom-v1.6.0-fips.1.yaml"


class Repo:
    PUBLIC_REPO = "projects-stg.registry.vmware.com/tkg"
    NAME = "tanzu-standard"


class SAS:
    TO = "TO"
    TSM = "tsm"


class Tkg_version:
    TKG_VERSION = "2.1"
    TAG = "v2.3.0"


class Tkg_Extension_names:
    FLUENT_BIT_SYSLOG = "FluentBitSysLog"
    FLUENT_BIT_HTTP = "FluentBitHttp"
    FLUENT_BIT_ELASTIC = "FluentBitElastic"
    FLUENT_BIT_KAFKA = "FluentBitKafka"
    FLUENT_BIT_SPLUNK = "FluentBitSplunk"
    GRAFANA = "Grafana"
    LOGGING = "Logging"
    PROMETHEUS = "Prometheus"
    FLUENT_BIT = "Fluent-bit"


class Tkgs_Extension_Details:
    ROLE_NAME = "arcas-automation-authenticated-user-privileged-binding"
    PACKAGE_REPO_URL = "projects.registry.vmware.com/tkg/packages/standard/repo:v2023.9.19"
    SUPPORTED_VERSIONS_U3 = [
        "v1.20.7+vmware.1-tkg.1.7fb9067",
        "v1.20.9+vmware.1-tkg.1.a4cee5b",
        "v1.20.12+vmware.1-tkg.1.b9a42f3",
        "v1.21.2+vmware.1-tkg.1.ee25d55",
        "v1.21.6+vmware.1-tkg.1.b3d708a",
        "v1.21.6+vmware.1-tkg.1",
    ]
    SUPPORTED_VERSIONS_U2 = ["v1.20.12+vmware.1-tkg.1.b9a42f3", "v1.19.7+vmware.1-tkg.1.fc82c41"]
    TKGS_PROXY_CREDENTIAL_NAME = "sivt-credential"


class TKG_Package_Details:
    REPO_NAME = "tanzu-standard"
    STANDARD_PACKAGE_URL = "projects.registry.vmware.com/tkg/packages/standard/repo"
    REPOSITORY_URL = "projects.registry.vmware.com/tkg/packages/standard/repo:v2023.9.19"
    NAMESPACE = "tkg-system"


class CIDR:
    CLUSTER_CIDR = "100.96.0.0/11"
    SERVICE_CIDR = "100.64.0.0/13"
    SHARED_CLUSTER_CIDR = "172.20.0.0/16"
    SHARED_SERVICE_CIDR = "10.96.0.0/16"


class PLAN:
    DEV_PLAN = "dev"
    PROD_PLAN = "prod"


class AkoType:
    KEY = "type"
    VALUE = "management"
    WORKLOAD_CLUSTER_SELECTOR = "workload-set01"
    SHARED_CLUSTER_SELECTOR = "shared-services-cluster"
    CLUSTER_NAME_LIMIT = 25


class Versions:
    tkg = "v1.20.5+vmware.2-tkg.1"
    ako = "v1.3.2_vmware.1"
    vcenter = "7.0.2.00000"
    VCENTER_UPDATE_THREE = "7.0.3"
    VCENTER_UPDATE_TWO = "7.0.2"
    COMPLIANT_OVA_TEMPLATE = "v1.23.8+vmware.2-stig-fips-sivt-ova"


class Env:
    VMC = "vmc"
    VSPHERE = "vsphere"
    VCF = "vcf"
    VCD = "vcd"
    YTT_FILE_LOCATION = "/root/.tanzu/tkg/providers/infrastructure-vsphere/ytt"
    # for tanzu>1.4 use below
    UPDATED_YTT_FILE_LOCATION = "/root/.config/tanzu/tkg/providers/infrastructure-vsphere/ytt"
    BOM_FILE_LOCATION = "/root/.config/tanzu/tkg/bom"
    COMPATIBILITY_FILE_LOCATION = "/root/.config/tanzu/tkg/compatibility"
    CACHE_FILE_LOCATION = "/root/.cache"


class TmcUser:
    USER = "tkgvmc-automation"
    USER_VSPHERE = "tkgvsphere-automation"


class AppName:
    AKO = "ako"
    HARBOR = "harbor"
    FLUENT_BIT = "fluent-bit"
    PROMETHUS = "prometheus"
    GRAFANA = "grafana"
    CERT_MANAGER = "cert-manager"
    CONTOUR = "contour"
    PINNIPED = "pinniped"


class Sizing:
    small = {"CPU": "2", "MEMORY": "4096", "DISK": "20"}
    medium = {"CPU": "2", "MEMORY": "8192", "DISK": "40"}
    large = {"CPU": "4", "MEMORY": "16384", "DISK": "40"}
    extraLarge = {"CPU": "8", "MEMORY": "32768", "DISK": "80"}


class AviSize:
    ESSENTIALS = {"cpu": "4", "memory": "24576"}
    SMALL = {"cpu": "6", "memory": "24576"}
    MEDIUM = {"cpu": "10", "memory": "32768"}
    LARGE = {"cpu": "16", "memory": "49152"}


class CertName:
    NAME = "tkgvmc-avi-cert"
    VSPHERE_CERT_NAME = "tkgvsphere-avi-cert"
    COMMON_NAME = "avi.demo.com"
    VSPHERE_COMMON_NAME = "tkgvsphere-avi-cert_common_name"
    VCD_AVI_CERT_NAME = "{avi_fqdn}-certificate"


class Paths:
    SIVT_INSTALL_DIR = "/opt/vmware/arcas/src"
    INJECT_FILE = "./common/injectValue.sh"
    TEMPLATES_ROOT_DIR = "template"
    TKGS_WORKLOAD_V1BETA1_J2 = f"{TEMPLATES_ROOT_DIR}/deploy_tkgs_v1beta1_cluster.yaml.j2"
    TKG_MGMT_SPEC_J2 = f"{TEMPLATES_ROOT_DIR}/deploy_vsphere_mgmt.yaml.j2"
    TKG_CLUSTER_14_SPEC_J2 = f"{TEMPLATES_ROOT_DIR}/deploy_cluster_1.4.yaml.j2"
    TKG_VMC_CLUSTER_14_SPEC_J2 = f"{TEMPLATES_ROOT_DIR}/deploy_vmc_cluster_1.4.yaml.j2"
    TKG_MGMT_VMC_14_SPEC_J2 = f"{TEMPLATES_ROOT_DIR}/deploy_vmc_mgmt_cluster_1.4.yaml.j2"
    VMC_ALB_DEPLOY_J2 = f"{TEMPLATES_ROOT_DIR}/deploy_vmc_alb_controller_config.json.j2"
    VMC_ALB_DEPLOY_JSON = "./common/template/deploy_vmc_alb_controller_config.json"
    VSPHERE_ALB_DEPLOY_J2 = f"{TEMPLATES_ROOT_DIR}/deploy_vsphere_alb_controller_config.json.j2"
    VSPHERE_ALB_DEPLOY_JSON = "./common/template/deploy_vsphere_alb_controller_config.json"
    VSPHERE_ALB_DEPLOY_JSON2 = "./common/template/deploy_vsphere_alb_controller_config2.json"
    VSPHERE_ALB_DEPLOY_JSON3 = "./common/template/deploy_vsphere_alb_controller_config3.json"
    VSPHERE_FLUENT_BIT_YAML = "./common/template/fluent_bit_data_values.yaml"
    try:
        with open("current_user.txt", "r") as outfile:
            current_user = outfile.read()
    except Exception:
        current_user = ""
    CLUSTER_PATH = f"/home/{current_user}/tanzu-clusters/"
    USER_HOME_DIR = os.path.expanduser("~")
    SIVT_DB_FILE = os.path.join(SIVT_INSTALL_DIR, "sivt_db.json")
    SIVT_LOG_FILE = os.path.join(SIVT_INSTALL_DIR, "arcas_server.log")
    SKIP_PRECHECK = "/tmp/skipPrecheck.txt"
    KUBE_OVA_JSON = os.path.join(SIVT_INSTALL_DIR, "common/resource/kubeova.json")


class NSXtCloud:
    VCENTER_CREDENTIALS = "vcenter-creds"
    NSXT_CREDENTIALS = "nsxt-creds"


class VcdCSE:
    PLUGIN_NAME = "Kubernetes Container Clusters"
    CLI_WARNING_MSG = (
        "InsecureRequestWarning: Unverified HTTPS request is being made. "
        "Adding certificate verification is strongly advised"
    )
    CKE_INTERFACE_TEMPLATE = "/opt/vmware/arcas/src/vcd/vcd_prechecks/templates/vcdKeInterface.json"
    CAP_INTERFACE_TEMPLATE = "/opt/vmware/arcas/src/vcd/vcd_prechecks/templates/vcdCap.json"
    VCDKE_CONFIG = "VCDKEConfig"
    CAPVCD_CONFIG = "capvcdCluster"
    ACCESS_TOKEN = "/opt/vmware/arcas/src/access_token/vapp_access_token.txt"


class CseMarketPlace:
    CSE_OVA_GROUPNAME = "Container-Service-Extension"
    CSE_PLUGIN_GROUPNAME = "Container-Ui-Plugin"
    VERSION = "4.0"
    CSE_PLUGIN_NAME_VCD = "arcas-container-ui-plugin-" + VERSION + ".zip"
    CSE_OVA_NAME = "arcas-VMware_Cloud_Director_Container_Service_Extension-" + VERSION + ".ova"


class SivtStatus:
    SKIP = "SKIPPED"
    NOT_STARTED = "NOT STARTED"
    IN_PROGRESS = "IN PROGRESS"
    SUCCESS = "PASSED"
    FAILED = "FAILED"
    NA = "NOT APPLICABLE"


class Component:
    ENV = "Environment"
    PRECHECK = "Prechecks (--precheck)"
    VCF_PRECONFIG = "VCF Pre-configurations (--vcf_pre_configuration)"
    VMC_PRECONFIG = "VMC Pre-configurations (--vmc_pre_configuration)"
    AVI = "NSX ALB Deployment (--avi_configuration)"
    MGMT = "Management Cluster (--tkg_mgmt_configuration)"
    WCP_CONFIG = "WCP Pre-configurations (--avi_wcp_configuration)"
    WCP = "Workload Control Plane Activation (--enable_wcp)"
    SHARED_SERVICE = "Shared Services Cluster (--shared_service_configuration)"
    NAMESPACE = "Supervisor Namespace (--create_supervisor_namespace)"
    WORKLOAD_PRECONFIG = "Workload Cluster Pre-configurations (--workload_preconfig)"
    WORKLOAD = "Workload Cluster (--workload_deploy)"
    EXTENSIONS = "User Managed Packages (--deploy_extensions)"
    CLEANUP = "Deployment Cleanup (--cleanup)"


class ApiUrl:
    BASE_PORT = 5000
    BASE_URL = f"http://localhost:{BASE_PORT}/api/tanzu"
    VCF_PRE_CONFIG = f"{BASE_URL}/vsphere/alb/vcf_pre_config"
    VMC_PRE_CONFIG = f"{BASE_URL}/vmc/envconfig"
    ACTIVE_SEESION = f"{BASE_URL}/active_session"
    LOGIN = f"{BASE_URL}/login"
    PRE_CHECK = f"{BASE_URL}/precheck"
    AVI_CONFIG_URL = {
        Env.VCF: f"{BASE_URL}/vsphere/alb",
        Env.VCD: f"{BASE_URL}/vsphere/alb",
        Env.VSPHERE: f"{BASE_URL}/vsphere/alb",
        Env.VMC: f"{BASE_URL}/vmc/alb",
    }
    SHARED_SERVICE_CONFIG_URL = {
        Env.VCF: f"{BASE_URL}/vsphere/tkgsharedsvc",
        Env.VSPHERE: f"{BASE_URL}/vsphere/tkgsharedsvc",
        Env.VMC: f"{BASE_URL}/vmc/tkgsharedsvc",
    }
    WORKLOAD_NTWRK_CONFIG_URL = {
        Env.VCF: f"{BASE_URL}/vsphere/workload/network-config",
        Env.VSPHERE: f"{BASE_URL}/vsphere/workload/network-config",
        Env.VMC: f"{BASE_URL}/vmc/workload/network-config",
    }
    WORKLOAD_CONFIG_URL = {
        Env.VCF: f"{BASE_URL}/vsphere/workload/config",
        Env.VSPHERE: f"{BASE_URL}/vsphere/workload/config",
        Env.VMC: f"{BASE_URL}/vmc/workload/config",
    }
    MGMT_CONFIG_URL = {
        Env.VCF: f"{BASE_URL}/vsphere/tkgmgmt",
        Env.VSPHERE: f"{BASE_URL}/vsphere/tkgmgmt",
        Env.VMC: f"{BASE_URL}/vmc/tkgmgmt",
    }
    DEPLOY_APP_URL = {
        Env.VCF: "http://localhost:5000/vsphere/deployApp",
        Env.VSPHERE: "http://localhost:5000/vsphere/deployApp",
        Env.VMC: "http://localhost:5000/deployApp",
    }
    EXTENSIONS_URL = f"{BASE_URL}/extensions"
    AVI_WCP_CONFIG_URL = f"{BASE_URL}/vsphere/tkgmgmt/alb/config/wcp"
    ENABLE_WCP_URL = f"{BASE_URL}/vsphere/enablewcp"
    SUPRVSR_NAMESPACE_URL = f"{BASE_URL}/vsphere/workload/createnamespace"
    WORKLOAD_URL = f"{BASE_URL}/vsphere/workload/createworkload"
    WCP_SHUTDOWN_URL = f"{BASE_URL}/wcp-shutdown"
    WCP_BRINGUP_URL = f"{BASE_URL}/wcp-bringup"
    CLEANUP_PROMPT_URL = f"{BASE_URL}/cleanup-prompt"
    CLEANUP_ENV_URL = f"{BASE_URL}/cleanup-env"
    VCD_URL = {
        "cloud": f"{BASE_URL}/listCloudVcd",
        "avi": f"{BASE_URL}/listAviVcd",
        "seg": f"{BASE_URL}/listSegVcd",
        "org": f"{BASE_URL}/listOrgVcd",
        "org_vdc": f"{BASE_URL}/listOrgVdc",
        "networks": f"{BASE_URL}/listNetworksOrg",
    }
    HARBOR_URL = f"{BASE_URL}/harbor"
    HARBOR_PRELOAD_STATUS_URL = f"{BASE_URL}/harbor_pre_load_status"


class Csp:
    BASE_URL = "https://console.cloud.vmware.com"
    GATEWAY_API = f"{BASE_URL}/csp/gateway/am/api"
    API_TOKEN = f"{GATEWAY_API}/auth/api-tokens"
    AUTH_URL = f"{API_TOKEN}/authorize"
    AUTH_URL_REFRESH_TOKEN_URL = f"{AUTH_URL}?refresh_token={{ref_token}}"
    DETAILS_URL = f"{API_TOKEN}/details"
    LOGGED_IN_USER_URL = f"{GATEWAY_API}/loggedin/user/orgs/{{org_id}}/info"
