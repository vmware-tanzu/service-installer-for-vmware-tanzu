from enum import Enum


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
                "defaultClusterGroup": "{cluster_group}"
            }}
        }}
    }}
    """
    SUPERVISOR_CLUSTER_REGISTER_PROXY = """
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
    TKGM_MGMT_CLUSTER_REGISTER_PROXY = """
    {{
        "managementCluster": {{
            "fullName": {{"name": "{management_cluster}"}},
            "meta": {{}},
            "spec": {{
                "kubernetesProviderType": "VMWARE_TANZU_KUBERNETES_GRID",
                "defaultClusterGroup": "{cluster_group}",
                "proxyName": "{proxy_name}",
                "defaultWorkloadClusterProxyName": "{proxy_name}"
            }}
        }}
    }}
    """
    TKGM_MGMT_CLUSTER_REGISTER = """
    {{
        "managementCluster": {{
            "fullName": {{"name": "{management_cluster}"}},
            "meta": {{}},
            "spec": {{
                "kubernetesProviderType": "VMWARE_TANZU_KUBERNETES_GRID",
                "defaultClusterGroup": "{cluster_group}"
            }}
        }}
    }}
    """
    SUPERVISOR_AGENT_INSTALLER_YAML = """
    {{
    "apiVersion": "installers.tmc.cloud.vmware.com/v1alpha1",
    "kind": "AgentInstall",
    "metadata":
        {{
            "namespace": "{tmc_namespace}",
            "name": "tmc-agent-installer-config"
        }},
    "spec": {{
    "operation": "INSTALL",
    "registrationLink": "{reg_link}"
        }}
    }}
    """
    SUPERVISOR_AGENT_INSTALLER_YAML_PROXY = """
    {{
    "apiVersion": "installers.tmc.cloud.vmware.com/v1alpha1",
    "kind": "AgentInstall",
    "metadata":
        {{
            "namespace": "{tmc_namespace}",
            "name": "tmc-agent-installer-config",
            "annotations": {{"tmc.cloud.vmware.com/bootstrap-token" : "{bots_trap_token}"}}
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
    "integration":{{
        "fullName":
            {{
                "provisionerName": "{provisioner_name}",
                "managementClusterName": "{management_cluster}",
                "name": "tanzu-observability-saas"
            }},
             "spec":
                {{
                "configurations": {{  "url": "{to_url}" }},
                "secrets": {{ "token": "{to_secrets}" }}
                }}
            }}
         }}
    }}
    """
    TSM_PAYLOAD = """
    {{
    "integration":{{
        "fullName": {{
            "provisionerName": "{provisioner_name}",
            "managementClusterName": "{management_cluster}",
            "name": "tanzu-service-mesh"
        }},
        "spec": {{"configurations": ""}}
    }}
    }}
    """
    ENABLE_DATA_PROTECTION = """
    {{
        "dataProtection": {{
            "fullName": {{
                "orgId": "{org_id}",
                "managementClusterName": "{mgmt_cluster}",
                "provisionerName": "{provisioner_name}",
                "clusterName": "{workload_cluster}"
            }},
            "spec": {{}}
        }}
    }}
    """


class TmcConstants:
    TMC_LOGIN_API = (
        "https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize?refresh_token={refresh_token}"
    )
    FETCH_PROXY_CREDENTIAL = "{tmc_url}/v1alpha1/account/credentials/{credential_name}"
    CREATE_PROXY_CREDENTIAL = "{tmc_url}/v1alpha1/account/credentials"
    FETCH_TMC_MGMT_CLUSTER = "{tmc_url}/v1alpha1/managementclusters/{management_cluster}"
    FETCH_TMC_WORKLOAD_CLUSTER = "{tmc_url}/v1alpha1/clusters/{cluster_name}"
    REGISTER_TMC_MGMT_CLUSTER = "{tmc_url}/v1alpha1/managementclusters"
    LIST_TMC_MGMT_CLUSTERS = "{tmc_url}/v1alpha1/managementclusters"
    LIST_TMC_CLUSTERS = "{tmc_url}/v1alpha1/clusters"
    TMC_MGMT_MANIFEST = "{tmc_url}/v1alpha1/managementclusters:manifest/{management_cluster}"
    CREATE_TKGM_WORKLOAD_CLUSTER = (
        "{tmc_url}/v1alpha1/managementclusters/{management_cluster}/"
        "provisioners/{provisioner}/tanzukubernetesclusters"
    )
    CREATE_TKGS_WORKLOAD_CLUSTER = "{tmc_url}/v1alpha1/clusters"
    DELETE_TKGM_WORKLOAD_CLUSTER = (
        "{tmc_url}/v1alpha1/managementclusters/{management_cluster}/"
        "provisioners/{provisioner}/tanzukubernetesclusters/{cluster}"
    )
    GET_WORKLOAD_CLUSTER_STATUS = "{tmc_url}/v1alpha1/clusters/{cluster_name}?full_name.managementClusterName={management_cluster}&full_name.provisionerName={provisioner}"
    GET_WORKLOAD_CLUSTER_KUBECONFIG = "{tmc_url}/v1alpha1/clusters/{cluster_name}/adminkubeconfig"
    INTEGRATE_SAAS = "{tmc_url}/v1alpha1/clusters/{cluster_name}/integrations"
    GET_SAAS_INTEGRATE_STATUS = "{tmc_url}/v1alpha1/clusters/{cluster_name}/integrations/{saas_type}?full_name.managementClusterName={management_cluster}&full_name.provisionerName={provisioner}"
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
    TKGM_REGISTRAION_FILE = "/opt/vmware/arcas/src/tkgm-tmc-registration.yaml"
    PROXY_YAML = "/opt/vmware/arcas/src/tmc_proxy.yaml"
    WORKLOAD_KUBE_CONFIG_FILE = "/opt/vmware/arcas/src/kubeconfig_cluster.yaml"
    VELERO_SECRET_FILE = "/opt/vmware/arcas/src/credentials-velero"
    MGMT_CLUSTERS = "managementClusters"
    CLUSTERS = "clusters"


class VeleroAPI:
    LIST_CLUSTER_GROUPS = "{tmc_url}/v1alpha1/clustergroups"
    LIST_CREDENTIALS = "{tmc_url}/v1alpha1/account/credentials?search_scope.capability=DATA_PROTECTION"
    LIST_BACKUP_LOCATIONS = "{tmc_url}/v1alpha1/dataprotection/providers/tmc/backuplocations"
    GET_LOCATION_INFO = "{tmc_url}/v1alpha1/dataprotection/providers/tmc/backuplocations/{location}"
    GET_CRED_INFO = "{tmc_url}/v1alpha1/account/credentials/{credential}"
    GET_CLUSTER_INFO = "{tmc_url}/v1alpha1/clusters/{cluster}"
    ENABLE_DP = "{tmc_url}/v1alpha1/clusters/{cluster}/dataprotection"
