# cleanup constant file


class Cleanup:
    ALL = "all"
    VCF = "vcf_pre_configuration"
    VMC = "vmc_pre_configuration"
    AVI = "avi_configuration"
    MGMT_CLUSTER = "tkgm_mgmt_cluster"
    SHARED_CLUSTER = "tkgm_shared_cluster"
    WORKLOAD_CLUSTER = "tkgm_workload_cluster"
    EXTENSION = "extensions"
    SUPERVISOR_NAMESPACE = "tkgs_supervisor_namespace"
    TKG_WORKLOAD_CLUSTER = "tkgs_workload_cluster"
    DISABLE_WCP = "disable_wcp"


class VCenter:
    vCenter = "vCenter"
    user = "user"
    PASSWORD = "PASSWORD"
    datacenter = "datacenter"
    cluster = "cluster"
    parent_rp = "parent_rp"
    management_cluster = "management_cluster"
    shared_cluster = "shared_cluster"
    workload_cluster = "workload_cluster"


class SePrefixNames:
    Management = "Mgmt"
    Workload = "Workload"
