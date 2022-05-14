from enum import Enum


class Constants(str, Enum):
    RECONCILE_SUCCESS = "Reconcile succeeded"
    RECONCILE_FAILED = "Reconcile failed"


class ComponentPrefix(str, Enum):
    ALB_MGMT_NW = "tkgvmc-avi-mgmt"
    MGMT_CLU_NW = "tkgvmc-management"
    SHARED_CLU_NW = "tkgvmc-shared-service"
    MGMT_DATA_VIP_NW = "tkgvmc-mgmt-data"
    CLUSTER_VIP_NW = "tkgvmc-cluster-vip"
    WORKLOAD_CLU_NW = "tkgvmc-workload"
    WORKLOAD_DATA_VIP_NW = "tkgvmc-workload-data"
    DNS_IPS = "tkgvmc-infra-dns-ips"
    NTP_IPS = "tkgvmc-infra-ntp-ips"
    VC_IP = "tkgvmc-infra-vcenter-ip"
    KUBE_VIP_SERVICE = "tkgvmc-kube-api"
    KUBE_VIP_SERVICE_ENTRY = "tkgvmc-kube-api-service-entry"
    ESXI = "ESXI"
    VCENTER = "VCENTER"


class FirewallRulePrefix(str, Enum):
    INFRA_TO_NTP = "tkgvmc-alb-to-ntp"
    INFRA_TO_DNS = "tkgvmc-alb-to-dns"
    INFRA_TO_VC = "tkgvmc-alb-to-vcenter"
    INFRA_TO_ANY = "tkgvmc-to-external"
    INFRA_TO_ALB = "tkgvmc-to-alb"
    INFRA_TO_CLUSTER_VIP = "tkgvmc-to-cluster-vip"
    MGMT_TO_ESXI = "tkgvmc-mgmt-to-esxi"
    WORKLOAD_TO_VC = "tkgvmc-workload{index}-to-vc"


class VmcNsxtGateways(str, Enum):
    CGW = "cgw"
    MGW = "mgw"


class NsxtServicePaths(str, Enum):
    HTTPS = "/infra/services/HTTPS"
    ICMP = "/infra/services/ICMP-ALL"
    NTP = "/infra/services/NTP"
    DNS = "/infra/services/DNS"
    DNS_UDP = "/infra/services/DNS-UDP"
    ANY = "ANY"


class NsxtScopes(str, Enum):
    CGW_ALL = "/infra/labels/cgw-all"
    MGW = "/infra/labels/mgw"


class GovcCommands(str, Enum):
    DEPLOY_OVA = "govc vm.deploy"
    FIND_VMS_BY_NAME = "govc find . -type m -name {vm_name} {options}"
    FIND_DATACENTER_BY_NAME = "govc find . -type d -name {dc_name} {options}"
    FIND_CLUSTERS_BY_NAME = "govc find . -type c -name {clu_name} {options}"
    FIND_FOLDERS_BY_NAME = "govc find . -type f -name {folder_name} {options}"
    FIND_RESOURCE_POOLS_BY_NAME = "govc find . -type p -name {rp_name} {options}"
    FIND_NETWORKS_BY_NAME = "govc find . -type n -name {network_name} {options}"
    CREATE_RESOURCE_POOL = "govc pool.create {options} {pool}"
    CREATE_FOLDER = "govc folder.create {options} {folder}"
    DEPLOY_LIBRARY_OVA = "govc library.deploy {options} {location} {name}"
    GET_VM_IP = "govc vm.ip -dc={datacenter} {options} {name}"
    GET_VM_PATH = "govc vm.info -dc={datacenter} {name}"
    DELETE_VM = "govc vm.destroy {vm_path}"
    DELETE_RESOURCE_POOL = "govc pool.destroy {path} {options}"
    POWER_OFF_VM = "govc vm.power -off -force {vm_path}"
    GET_CONTENT_LIBRARIES = "govc library.ls {options}"


class VmPowerState(str, Enum):
    ON = "poweredOn"
    OFF = "poweredOff"


class TKGCommands(str, Enum):
    VERSION = "tanzu version"
    MGMT_DEPLOY = "tanzu management-cluster create --file {file_path} -v 9"
    CLUSTER_DEPLOY = "tanzu cluster create --file {file_path} {verbose}"
    LIST_CLUSTERS_JSON = "tanzu cluster list --output json"
    LIST_ALL_CLUSTERS_JSON = "tanzu cluster list --include-management-cluster --output json"
    GET_ADMIN_CONTEXT = "tanzu cluster kubeconfig get {cluster} --admin"
    MGMT_UPGRADE_CLEANUP = """
    rm -rf ~/.tanzu/tkg/bom
    export TKG_BOM_CUSTOM_IMAGE_TAG="v1.3.1-patch1"
    tanzu management-cluster create
    tanzu login --server {cluster_name}
    kubectl delete deployment kapp-controller -n kapp-controller
    kubectl delete clusterrole kapp-controller-cluster-role
    kubectl delete clusterrolebinding kapp-controller-cluster-role-binding
    kubectl delete serviceaccount kapp-controller-sa -n kapp-controller
    """
    MGMT_UPGRADE = "tanzu management-cluster upgrade --yes {options}"
    CLUSTER_UPGRADE_CLEANUP = """
    tanzu login --server {mgmt_cluster_name}
    tanzu cluster list --include-management-cluster
    tanzu cluster kubeconfig get {cluster_name} --admin
    kubectl config use-context {cluster_name}-admin@{cluster_name}
    kubectl delete deployment kapp-controller -n kapp-controller
    kubectl delete clusterrole kapp-controller-cluster-role
    kubectl delete clusterrolebinding kapp-controller-cluster-role-binding
    kubectl delete serviceaccount kapp-controller-sa -n kapp-controller
    """
    CLUSTER_UPGRADE = "tanzu cluster upgrade {cluster_name} --yes {options}"
    GET_K8_RELEASES = """
    tanzu kubernetes-release get
    tanzu kubernetes-release available-upgrades get {tkr}
    """
    UPDATE_TKG_BOM = """
    rm -rf ~/.tanzu/tkg/bom
    export TKG_BOM_CUSTOM_IMAGE_TAG="{bom_image_tag}"
    tanzu management-cluster create
    """
    TANZU_LOGIN = "tanzu login --server {server}"
    MGMT_CLUSTER_UPGRADE = "tanzu management-cluster upgrade --yes {options}"
    TIMEOUT_OPTION = " --timeout {timeout} "

    LIST_ALL_CLUSTERS = "tanzu cluster list --include-management-cluster"
    LIST_AVAILABLE_PACKAGES = "tanzu package available list -A {options}"
    GET_AVAILABLE_PACKAGE_DETAILS = "tanzu package available list {pkgName} -A {options}"
    INSTALL_PACKAGE = "tanzu package install {name} --package-name {pkgName} --namespace {namespace} --version {version} {options}"
    LIST_INSTALLED_PACKAGES = "tanzu package installed list -A {options}"
    GET_PACKAGE_DETAILS = "tanzu package installed get {name} --namespace {namespace} {options}"
    REGISTER_TMC = "tanzu management-cluster register --'tmc'-registration-url \"{url}\""


class KubectlCommands(str, Enum):
    VERSION = "kubectl version --client --short"
    SET_KUBECTL_CONTEXT = "kubectl config use-context {cluster}-admin@{cluster}"
    DELETE_KUBECTL_CONTEXT = "kubectl config delete-context {cluster}-admin@{cluster}"
    DELETE_KUBECTL_CONTEXT_TKGS = "kubectl config delete-context {cluster}"
    DELETE_KUBECTL_CLUSTER = "kubectl config delete-cluster {cluster}"
    ADD_SERVICES_LABEL = 'kubectl label cluster.cluster.x-k8s.io/{cluster} cluster-role.tkg.tanzu.vmware.com/tanzu-services="" --overwrite=true'
    GET_ALL_PODS = "kubectl get pods -A"
    APPLY = "kubectl apply -f {config_file}"
    LIST_NAMESPACES = "kubectl get namespaces {options}"
    LIST_APPS = "kubectl get apps -n {namespace} {options}"
    GET_APP_DETAILS = "kubectl get app {app_name} -n {namespace} {options}"
    LIST_SECRETS = "kubectl get secret -n {namespace} {options}"
    FILTER_NAME = "-o=name"
    FILTER_JSONPATH = "-o=jsonpath={template}"
    OUTPUT_YAML = "-o yaml"
    OUTPUT_JSON = "-o json"
    CREATE_SECRET = "kubectl create secret generic {name} --from-file={config_file} -n {namespace}"
    LIST_SERVICE_ACCOUNTS = "kubectl get serviceaccounts -n {namespace} {options}"
    GET_HARBOR_CERT = "kubectl -n {namespace} get secret harbor-tls {options}"
    DELETE = "kubectl delete -f {config_file}"
    DELETE_EXTENSION = "kubectl delete extension {app_name} -n {namespace}"
    GET_SECRET_DETAILS = "kubectl get secret {name} -n {namespace} {options}"
    UPDATE_SECRET = "kubectl create secret generic {name} --from-file={config_file} -n {namespace} -o yaml --dry-run | kubectl replace -f-"
