/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
export enum AppApiUrls {
    ////////////////// Base URL //////////////////////////////////////////
    URL_SEPARATER = '/',
    BASE_URL = 'api/tanzu',
    ////////////////// Provider Page List Resources Endpoint /////////////
    ESTABLISH_VMC_SESSION = 'vmc/env/session',
    ENABLE_PROXY_ON_ARCAS = 'enableproxy',
    DISABLE_PROXY_ON_ARCAS = 'disableproxy',
    LIST_RESOURCES = 'listResources',
    LIST_CLUSTER_UNDER_DATACENTER = 'getClusters',
    LIST_DATASTORE_UNDER_DATACENTER = 'getDatastores',
    LIST_CONTENTLIB_FILES = 'getContentLibraryFiles',
    LIST_TIER1_ROUTERS = 'tier1_details',
    VC_SSL_THUMBPRINT = 'getThumbprint',
    GET_KUBE_VERSIONS = 'getkubeversions',
    ////////////////// Validation Endpoints //////////////////////////////
    VALIDATE_IP_SUBNET = 'validateIP',
    VERIFY_TMC_TOKEN = 'validateTMCRefreshToken',
    VERIFY_SDDC_TOKEN = 'validateSDDCRefreshToken',
    VERIFY_MARKETPLACE_TOKEN = 'validateMarketplaceRefreshToken',
    ////////////////// Input file generation to arcas ////////////////////
    GENERATE_JSON_INPUT = 'createinputfile',
    ////////////////// vSphere VCF Deployment Endpoint //////////////////////////////
    VCF_VSPHERE_VMC_TRIGGER_PRECHECKS = 'precheck',
    VCF_VSPHERE_TRIGGER_AVI = 'vsphere/alb',
    VCF_VSPHERE_TRIGGER_MGMT = 'vsphere/tkgmgmt',
    VCF_VSPHERE_TRIGGER_SHARED = 'vsphere/tkgsharedsvc',
    VCF_VSPHERE_TRIGGER_WRK_PRECONFIG = 'vsphere/workload/network-config',
    VCF_VSPHERE_TRIGGER_WRK_DEPLOY = 'vsphere/workload/config',
    VCF_VSPHERE_VMC_TRIGGER_EXTENSIONS = 'extentions',
    /////////////////////////// VMC Deployment Endpoint //////////////////////////////
    VMC_PRE_CONFIGURATION = 'vmc/envconfig',
    VMC_TRIGGER_AVI = 'vmc/alb',
    VMC_TRIGGER_MGMT = 'vmc/tkgmgmt',
    VMC_TRIGGER_SHARED = 'vmc/tkgsharedsvc',
    VMC_TRIGGER_WRK_PRECONFIG = 'vmc/workload/network-config',
    VMC_TRIGGER_WRK_DEPLOY = 'vmc/workload/config',
    /////////////////////////// TKGS SPECIFIC ENDPOINTS //////////////////////////////
    NAMESPACE_DETAILS = 'getNamespaceDetails',
    LIST_SUPERVISOR_CLUSTER = 'getSupervisorClusters',
    LIST_WCP_CLUSTER = 'getWCPEnabledClusters',
    LIST_NAMESPACES = 'getAllNamespaces',
    LIST_VM_CLASSES = 'listvmclasses',
    LIST_STORAGE_POLICY = 'storagePolicies',
    VALIDATE_SUPERVISOR_CLUSTER = 'getSupervisorClusterHealth',
    LIST_CLUSTER_VERSION = 'getClusterVersions',
    LIST_WORKLOAD_NETWORK = 'getWorkloadNetworks',
    /////////////////// Logs /////////////////////////////////////////////
    ARCAS_LOG_BUNDLE = 'logbundle',
    ARCAS_LOGS = 'streamLogs',
    SUPPORT_BUNDLE = 'downloadSupportBundle',
}
