from enum import Enum


class Component(str, Enum):
    ENV = "Environment"
    PRECHECK = "Prechecks (--precheck)"
    VCF_PRECONFIG = "VCF Pre-configurations (--vcf_pre_configuration)"
    VMC_PRECONFIG = "VMC Pre-configurations (--vmc_pre_configuration)"
    AVI = "NSX ALB Deployment (--avi_configuration)"
    MGMT = "Management Cluster (--tkg_mgmt_configuration)"
    WCP_CONFIG = "WCP Pre-configurations (--avi_wcp_configuration)"
    WCP = "Workload Control Plane Activation (--enable_wcp)"
    SS = "Shared Services Cluster (--shared_service_configuration)"
    NAMESPACE = "Supervisor Namespace (--create_supervisor_namespace)"
    WORKLOAD_PRECONFIG = "Workload Cluster Pre-configurations (--workload_preconfig)"
    WORKLOAD = "Workload Cluster (--workload_deploy)"
    EXTENSIONS = "User Managed Packages (--deploy_extensions)"
    CLEANUP = "Deployment Cleanup (--cleanup)"


class Status(str, Enum):
    SKIP = "SKIPPED"
    NOT_STARTED = "NOT STARTED"
    IN_PROGRESS = "IN PROGRESS"
    SUCCESS = "PASSED"
    FAILED = "FAILED"
    NA = "NOT APPLICABLE"


class DbDetails(str, Enum):
    FILE_NAME = "/opt/vmware/arcas/src/sivt_db.json"

