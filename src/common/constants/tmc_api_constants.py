from enum import Enum


class TmcCommands(str, Enum):
    """
    SaaS commands corresponding to TSM, TMC and TO
    """

    TMC_LOGIN = "tmc login --no-configure -name {user}"
    REGISTER_TMC_PROXY_MGMT = (
        "tmc managementcluster register {management_cluster} -c {cluster_group} -p TKG "
        "--proxy-name {proxy_name} -k {kubeconfig_yaml}"
    )
    REGISTER_TMC_MGMT = (
        "tmc managementcluster register {management_cluster} -c {cluster_group} -p TKG -k {kubeconfig_yaml}"
    )
    REGISTER_TMC_PROXY = (
        "tmc cluster attach --name {cluster_name} --cluster-group default -k {file} --proxy-name {proxy_name}"
    )
    REGISTER_TMC = "tmc cluster attach --name {cluster_name} --cluster-group default -k {file} --force"
    LIST_TMC_CLUSTERS_MGMT = "tmc managementcluster list"
    LIST_TMC_CLUSTERS = "tmc cluster list"
    GET_CLUSTER_STATUS_MGMT = "tmc managementcluster get {mgmt_cluster}"
    GET_CLUSTER_STATUS = "tmc cluster get {cluster} -m {mgmt_cluster} -p {provisioner}"
    GET_KUBE_CONFIG = "tanzu cluster kubeconfig get {cluster_name} --admin --export-file {file}"
    CREATE_TMC_CREDENTIAL = "tmc account credential create -f {tmc_proxy_yaml}"
    INTEGRATE_SAAS = "tmc cluster integration create -f {file_name}"
    GET_SAAS_STATUS = (
        "tmc cluster integration get {saas_type} --cluster-name {cluster_name} -m " "{mgmt_cluster} -p {provisioner}"
    )
    REGISTER_SUPERVISOR_TMC = "tmc managementcluster register {supervisor_cluster} -c {cluster_group} -p TKGS"
    CREATE_TKGS_WORKLOAD_CLUSTER = (
        "tmc cluster create --template tkgs -m {supervisor_cluster} -p {namespace} "
        "--cluster-group {cluster_group} --name {cluster_name} --version {version} "
        "--pods-cidr-blocks {pod_cidr} --service-cidr-blocks {service_cidr} --storage-class "
        "{node_storage_class} --allowed-storage-classes {allowed_storage_class} "
        "--default-storage-class {default_storage_class} --worker-instance-type "
        "{worker_type} --instance-type {instance_type} --worker-node-count {node_count}"
    )


class TmcPayloads(str, Enum):
    """
    TMC API payloads for TO, TSM and proxy credentails creation
    """

    SUPERVISOR_CLUSTER_REGISTER = """
    {{
        "managementCluster": {{
            "fullName": {{"name": "{management_cluster}"}},
            "meta": {{}},
            "spec": {{
                "kubernetesProviderType": "VMWARE_TANZU_KUBERNETES_GRID_SERVICE",
                "defaultClusterGroup": "{cluster_group}",
                "proxyName": "{proxy_name}",
                "defaultWorkloadClusterProxyName": "{proxy_name}"
            }}
        }}
    }}
    """
    SUPERVISOR_REGISTER_YAML = """
    {{
    "apiVersion": "installers.tmc.cloud.vmware.com/v1alpha1",
    "kind": "AgentInstall",
    "metadata":
        {{
            "namespace": "{tmc_namespace}",
            "name": "tmc-agent-installer-config",
            "annotations": "{boots}"
        }},
    "spec": {{
    "operation": "INSTALL",
    "registrationLink": "{reg_link}"
        }}
    }}
    """
    TKGS_PROXY_CREDENTIAL = """
    {{
        "credential": {{
            "fullName": {{"name": "{proxy_name}"}},
            "meta": {{
                "annotations": {{
                    "httpProxy": "{http_url}",
                    "httpsProxy": "{https_url}",
                    "noProxyList": "{no_proxy}",
                    "proxyDescription": ""
                }}
            }},
            "spec": {{
                "capability": "PROXY_CONFIG",
                "data": {{
                    "keyValue": {{
                        "data": {{
                            "httpUserName": "{http_user}",
                            "httpPassword": "{http_password}",
                            "httpsUserName": "{https_user}",
                            "httpsPassword": "{https_password}",
                            "proxyCABundle": ""
                        }}
                    }}
                }}
            }}
        }}
    }}
    """
    TO_PAYLOAD = """
    {{
    "full_name": {{
        "provisionerName": "{provisioner_name}",
        "clusterName": "{cluster_name}",
        "managementClusterName": "{management_cluster}",
        "name": "tanzu-observability-saas" }},
    "spec": {{
        "configurations": {{
        "url": "{to_url}"
        }},
        "secrets": {{ "token": "{to_secrets}" }}
        }}
    }}
    """
    TSM_PAYLOAD = """
    {{
        "full_name": {{
            "provisionerName": "{provisioner_name}",
            "managementClusterName": "{management_cluster}",
            "clusterName": "{cluster_name}",
            "name": "tanzu-service-mesh"
        }},
        "spec": {{"configurations": ""}}
    }}
    """


class TmcConstants:
    TMC_LOGIN_API = (
        "https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize?refresh_token={refresh_token}"
    )
    FETCH_PROXY_CREDENTIAL = "{tmc_url}/v1alpha1/account/credentials/{credential_name}"
    CREATE_PROXY_CREDENTIAL = "{tmc_url}/v1alpha1/account/credentials"
    FETCH_TMC_MGMT_CLUSTER = "{tmc_url}/v1alpha1/managementclusters/{management_cluster}"
    REGISTER_TMC_MGMT_CLUSTER = "{tmc_url}/v1alpha1/managementclusters/"
    TMC_MGMT_MANIFEST = "{tmc_url}/v1alpha1/managementclusters:manifest/{management_cluster}"
    CREATE_TKGM_WORKLOAD_CLUSTER = (
        "{tmc_url}/v1alpha1/managementclusters/{management_cluster}/"
        "provisioners/{provisioner}/tanzukubernetesclusters"
    )
    TO = "tanzu-observability-saas"
    TSM = "tanzu-service-mesh"
    TSM_NAMESPACE = "vmware-system-tsm"
    TO_NAMESPACE = "tanzu-observability-saas"
    TSM_PODS = ["allspark", "installer-job", "k8s-cluster-manager", "tsm-agent-operator"]
    TO_PODS = ["wavefront"]
    TO_JSON = "/opt/vmware/arcas/src/to_json.json"
    TSM_JSON = "/opt/vmware/arcas/src/tsm_json.json"
    TMC_PROXY_NAME = "arcas-{cluster_name}-tmc-proxy"
    TKGS_REGISTRAION_FILE = "/opt/vmware/arcas/src/tkgs-tmc-registration.yaml"
    PROXY_YAML = "/opt/vmware/arcas/src/tmc_proxy.yaml"
    WORKLOAD_KUBE_CONFIG_FILE = "/opt/vmware/arcas/src/kubeconfig_cluster.yaml"
