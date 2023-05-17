/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import {Injectable} from '@angular/core';
import {ApiHandlerService} from './api-handler.service';
import {AppApiUrls} from 'src/app/shared/enums/app-api-urls.enum';
import {ApiEndPoint} from 'src/app/configs/api-endpoint.config';

@Injectable({
    providedIn: 'root',
})
export class APIClient {

    // KUBERNETES BASE IMAGE SUPPORTED VERSIONS
    public baseImage = ['photon', 'ubuntu'];
    public baseImageVersion154 = ['v1.22.9', 'v1.21.11', 'v1.20.15'];
    public baseImageVersion160 = ['v1.23.8', 'v1.22.11', 'v1.21.14'];
    public baseImageVersion210 = ['v1.24.9', 'v1.23.15', 'v1.22.17'];
    public baseImageVersion211 = ['v1.24.10', 'v1.23.16', 'v1.22.17'];
    public baseImageVersion = ['v1.25.7', 'v1.24.11', 'v1.23.17'];
    public AllSupportedCNI = ['antrea', 'calico'];
    public TkgsCertTypes = ['Path', 'Endpoint'];
    public sharedBaseImageVersion = [];
    public wrkBaseImageVersion = [];

    private apiEndPointConfig: ApiEndPoint;
    private apiEndPoint: string;
    networks = [];
    allClusters = [];
    // networks = ['nw-segment-1', 'nw-segment-2', 'nw-segment-3', 'nw-segment-4', 'nw-segment-5'];
    private mgmtSegmentName: string;
    private mgmtGatewayCidr: string;

    public redirectedToHome = false;

    public TkgMgmtDataNwValidated = false;
    public TkgMgmtNwValidated = false;
    public TkgSharedNwValidated = false;
    public SharedNwValidated = false;
    public TkgWrkDataNwValidated = false;
    public TkgWrkNwValidated = false;
    // AVI Component Errors
    public AviIpValidated = false; // Blanket with all below validations
    public aviSegmentError = false;
    public aviClusterSegmentError = false;
    public aviController01Error = false;
    public aviController02Error = false;
    public aviController03Error = false;
    public clusterIpError = false;
    public isEnterpriseLicense = false;

    public tkgMgmtDataSegmentError = false;
    public mgmtSegmentError = false;
    public tkgWrkDataSegmentError = false;
    public wrkSegmentError = false;
    public tkgClusterError = false;
    public tmcEnabled = false;
    public toEnabled = false;
    public arcasProxyEnabled = false;

    public vspherePayload;
    public vsphereNsxtPayload;
    public vmcPayload;
    public vpshereTkgsPayload;
    public vcdPayload;

    public storagePolicies = [];
    public masterPolicyError: boolean = false;
    public ephemeralPolicyError: boolean  = false;
    public imagePolicyError: boolean = false;
    public contentLibs = [];
    public wrkNetworks = [];
//     public storageSpec = [];
    public namespaceVmClass = [];
    public namespaceSegmentError = false;
    public storageSpec;
    public allowedStoragePolicy = [];
    public selectedVmClass = [];
    public storagePolicy: Map<string, string> = new Map<string, string>();
    // CONFIGURE ADDITIONAL VOLUMES FOR TKGS
    public tkgsControlPlaneVolumes: Map<string, string> = new Map<string, string>();
    public tkgsWorkerVolumes: Map<string, string> = new Map<string, string>();
    public tkgsAdditionalCerts: Map<string, string> = new Map<string, string>();

    public proxyConfiguredVsphere = false;
    public proxyConfiguredVCF = false;

    public tkgsStage: string;
    public createNewSegment: boolean = false;
    public showOld: boolean = false;
    public existingNamespace: boolean = true;
    public clusterVersions = [];
    public tkgsWorkloadNetwork = ["CREATE NEW"];
    public allNamespaces = ["CREATE NEW"];
    public wcpClusterName = [];
    public tmcMgmtCluster = [];

    // VELERO fields
    public clusterGroups = [];
    public wrkDataProtectionEnabled = false;
    public sharedDataProtectonEnabled = false;
    public dataProtectionCredentials = [];
    public dataProtectionTargetLocations = [];

    // VCENTER DETAILS
    public vcAddress;
    public vcUser;
    public vcPass;
    public fetchNamespaceStorageSpec = false;
    // CHECK CLUSTER VERSION MISMATCH
    public clusterVersionMismatch = false;
    // IDENTITY MANAGEMENT FIELDS
    public enableIdentityManagement = false;
    public rbacUsersAccess: Map<string, string> = new Map<string, string>();
    public rbacAccessLevel = ['cluster-admin', 'admin', 'edit', 'view'];

    //CHECKING IF SHARED AND WORKLOAD CLUSTER FIELDS ARE TO BE MADE MANDATORY
    sharedServicesClusterSettings = false;
    workloadClusterSettings = false;
    workloadDataSettings = false;

    // Compliance changes
    compliantDeployment = false;
    isAirgapped = false;

    constructor(private apiHandlerService: ApiHandlerService){
        this.apiEndPointConfig = new ApiEndPoint();
        this.apiEndPoint = this.apiEndPointConfig.getGeneratedApiEndpoint();
    }

    verifyTmcRefreshToken(refreshToken) {
        let payload = {
            "envSpec" : {
                "saasEndpoints": {
                    "tmcDetails": {
                        "tmcAvailability": "true",
                        "tmcRefreshToken": refreshToken
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VERIFY_TMC_TOKEN;
        return this.apiHandlerService.post(url, payload);
    }

    enableArcasProxy(httpProxy, httpsProxy, noProxy, proxyCert, env) {
        let payload = {
            "envSpec": {
                "proxySpec": {
                    "arcasVm": {
                        "enableProxy": "true",
                        "httpProxy": httpProxy,
                        "httpsProxy": httpsProxy,
                        "noProxy": noProxy,
                        "proxyCert": proxyCert
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.ENABLE_PROXY_ON_ARCAS;
        if (env === 'vsphere') {
            return this.apiHandlerService.post(url, payload);
        } else if (env === 'vcf') {
            return this.apiHandlerService.postVcf(url, payload);
        }
    }

    disableArcasProxy(env) {
        let payload = {
            "envSpec": {
                "proxySpec": {
                    "arcasVm": {
                        "disableProxy": "true",
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.DISABLE_PROXY_ON_ARCAS;
        if (env === 'vsphere') {
            return this.apiHandlerService.post(url, payload);
        } else if (env === 'vcf') {
            return this.apiHandlerService.postVcf(url, payload);
        }
    }

    getOvaImagesUnderContentLib(vCenterData, contentLibName, env) {
        let payload;
        let payloadVsphereVCF = {
            "envSpec": {
                "vcenterDetails": {
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "contentLibraryName": contentLibName
                }
            }
        };
        let payloadVMC = {
            'envSpec': {
                'sddcRefreshToken': vCenterData.sddcToken,
                'sddcName': vCenterData.sddcName,
                'orgName': vCenterData.orgName,
                'contentLibraryName':  contentLibName
            }
        };
        if (env === 'vsphere') {
            payload  = payloadVsphereVCF;
        } else if (env === 'vcf') {
            payload  = payloadVsphereVCF;
        } else if (env === 'vmc') {
            payload  = payloadVMC;
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_CONTENTLIB_FILES;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    verifyTmcRefreshTokenVmc(refreshToken) {
        let payload = {
            "saasEndpoints": {
                "tmcDetails": {
                    "tmcAvailability": "true",
                    "tmcRefreshToken": refreshToken
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VERIFY_TMC_TOKEN;
        return this.apiHandlerService.postVmc(url, payload);
    }

    verifySDDCRefreshToken(refreshToken) {
        let payload = {
            "envSpec": {
                "sddcRefreshToken": refreshToken
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VERIFY_SDDC_TOKEN;
        return this.apiHandlerService.postVmc(url, payload);
    }

    getVMCSession(vmcData, env) {
        let payload = {};
        if (env === 'vmc') {
            payload = {
                "envSpec": {
                    "sddcRefreshToken": vmcData.sddcRefreshToken,
                    "orgName": vmcData.orgName,
                    "sddcName": vmcData.sddcName,
                    "sddcDatacenter": vmcData.sddcDatacenter,
                    "sddcCluster": vmcData.sddcCluster,
                    "sddcDatastore": vmcData.sddcDatastore,
                    "resourcePoolName": vmcData.resourcePoolName,
                    "contentLibraryName": vmcData.contentLibraryName,
                    "aviOvaName": vmcData.aviOvaName,
                },
                "marketplaceSpec": {
                    "refreshToken": vmcData.refreshToken,
                }
            }
        } else {
            payload = {
                "envSpec": {
                    "vcenterDetails": {
                        "vcenterAddress": vmcData.vcenterAddress,
                        "vcenterSsoUser": vmcData.username,
                        "vcenterSsoPasswordBase64": btoa(vmcData.password),
                        "vcenterDatacenter": vmcData.datacenter,
                        "vcenterCluster": vmcData.cluster,
                        "vcenterDatastore": vmcData.datastore,
                        "resourcePoolName": vmcData.resourcePoolName,
                        "contentLibraryName": vmcData.contentLibraryName,
                        "aviOvaName": vmcData.aviOvaName,
                    },
                    "marketplaceSpec": {
                        "refreshToken": vmcData.refreshToken,
                    }
                },
            }
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.ESTABLISH_VMC_SESSION;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    getVsphereData(vCenterData, env, infraType) {
        let payloadVsphere = {
            "envSpec": {
                "envType": infraType,
                "vcenterDetails": {
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword)
                }
            }
        };
        let payloadVcf = {
            "envSpec": {
                "vcenterDetails": {
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword)
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_RESOURCES;
        if (env === 'vsphere') {
            return this.apiHandlerService.postCall(url, payloadVsphere, env);
        } else if (env === 'vcf') {
            return this.apiHandlerService.postCall(url, payloadVcf, env);
        }
    }

    getClustersUnderDatacenter(vCenterData, env, infraType) {
        let payloadVsphere = {
            "envSpec": {
                "envType": infraType,
                "vcenterDetails": {
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            }
        };
        let payloadVcf = {
            "envSpec": {
                "vcenterDetails": {
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_CLUSTER_UNDER_DATACENTER;
        if (env === 'vsphere') {
            return this.apiHandlerService.post(url, payloadVsphere);
        } else if (env === 'vcf') {
            return this.apiHandlerService.postVcf(url, payloadVcf);
        }
    }

    getDatastoresUnderDatacenter(vCenterData, env, infraType) {
        let payloadVsphere = {
            "envSpec": {
                "envType": infraType,
                "vcenterDetails": {
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            }
        };
        let payloadVcf = {
            "envSpec": {
                "vcenterDetails": {
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_DATASTORE_UNDER_DATACENTER;
        if (env === 'vsphere') {
            return this.apiHandlerService.post(url, payloadVsphere);
        } else if (env === 'vcf') {
            return this.apiHandlerService.postVcf(url, payloadVcf);
        }
    }
    getStoragePolicy(vCenterData) {
        let payload = {
            "envSpec": {
                "envType": "tkgs",
                "vcenterDetails":{
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword)
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_STORAGE_POLICY;
        return this.apiHandlerService.post(url, payload);
    }

    getVmClasses(vCenterData) {
        let payload = {
            "envSpec": {
                "envType": "tkgs",
                "vcenterDetails":{
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword)
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_VM_CLASSES;
        return this.apiHandlerService.post(url, payload);
    }

    getWcpCluster(vCenterData) {
        let payload = {
            "envSpec": {
                "envType": "tkgs-ns",
                "vcenterDetails":{
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_WCP_CLUSTER;
        return this.apiHandlerService.post(url, payload);
    }

    //Ping test on Supervisor Start IP
    pingTestSupervisor(vCenterData) {
        let payload = {
            "envSpec": {
                "envType": "tkgs-wcp",
                "vcenterDetails":{
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterCluster": vCenterData.cluster,
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            },
            "tkgsComponentSpec": {
                "tkgsMgmtNetworkSpec": {
                    "tkgsMgmtNetworkStartingIp": vCenterData.startIp,
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.PING_TEST_SUPERVISOR_VM;
        return this.apiHandlerService.post(url, payload);
    }

    //Ping test on Supervisor Start IP
    aviNameResolution(aviData, env) {
        let payloadTkgs = {
            "envSpec": {
                "envType": "tkgs-wcp",
                "infraComponents": {
                    "dnsServersIp": aviData.dnsServersIp
                },
                "vcenterDetails": {
                    "vcenterAddress": aviData.vcenterAddress,
                    "vcenterSsoUser": aviData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(aviData.ssoPassword),
                }
            },
            "tkgsComponentSpec": {
                "aviComponents": {
                    "enableAviHa": aviData.enableAviHa,
                    "aviController01Fqdn": aviData.fqdn01,
                    "aviController01Ip": aviData.ip01,
                    "aviController02Fqdn": aviData.fqdn02,
                    "aviController02Ip": aviData.ip02,
                    "aviController03Fqdn": aviData.fqdn03,
                    "aviController03Ip": aviData.ip03,
                    "aviClusterFqdn": aviData.clusterFqdn,
                    "aviClusterIp": aviData.clusterIp
                }
            }
        };
        let payloadVsphereVcf = {
            "envSpec": {
                "infraComponents": {
                    "dnsServersIp": aviData.dnsServersIp
                },
                "vcenterDetails": {
                    "vcenterAddress": aviData.vcenterAddress,
                    "vcenterSsoUser": aviData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(aviData.ssoPassword),
                }
            },
            "tkgComponentSpec": {
                "aviComponents": {
                    "enableAviHa": aviData.enableAviHa,
                    "aviController01Fqdn": aviData.fqdn01,
                    "aviController01Ip": aviData.ip01,
                    "aviController02Fqdn": aviData.fqdn02,
                    "aviController02Ip": aviData.ip02,
                    "aviController03Fqdn": aviData.fqdn03,
                    "aviController03Ip": aviData.ip03,
                    "aviClusterFqdn": aviData.clusterFqdn,
                    "aviClusterIp": aviData.clusterIp
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.NAME_RESOLUTION;
        if(env == 'tkgs'){
            return this.apiHandlerService.postCall(url, payloadTkgs, 'vsphere');
        } else {
            return this.apiHandlerService.postCall(url, payloadVsphereVcf, env);
        }
    }

    // Get Namespace Under a Cluster
    getNamespaces(vCenterData) {
        let payload = {
            "envSpec": {
                "envType": "tkgs-ns",
                "vcenterDetails":{
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterCluster": vCenterData.cluster,
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_NAMESPACES;
        return this.apiHandlerService.post(url, payload);
    }
    // Get Cluster Versions
    getClusterVersion(vCenterData) {
        let payload = {
            "envSpec": {
                "envType": "tkgs-ns",
                "vcenterDetails":{
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterCluster": vCenterData.cluster,
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_CLUSTER_VERSION;
        return this.apiHandlerService.post(url, payload);
    }
    // Get Workload Networks
    getWorkloadNetwork(vCenterData) {
        let payload = {
            "envSpec": {
                "envType": "tkgs-ns",
                "vcenterDetails":{
                    "vcenterAddress": vCenterData.vcenterAddress,
                    "vcenterSsoUser": vCenterData.ssoUser,
                    "vcenterSsoPasswordBase64": btoa(vCenterData.ssoPassword),
                    "vcenterCluster": vCenterData.cluster,
                    "vcenterDatacenter": vCenterData.datacenter,
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_WORKLOAD_NETWORK;
        return this.apiHandlerService.post(url, payload);
    }

    getSupervisorClustersForTMC(refreshToken) {
        let payload = {
            "saasEndpoints": {
                "tmcDetails": {
                    "tmcRefreshToken": refreshToken,
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_SUPERVISOR_CLUSTER;
        return this.apiHandlerService.post(url, payload);
    }

    validateSupervisorCluster(clusterName) {
        let payload = {
            'envSpec': {
                'saasEndpoints': {
                    'tmcDetails': {
                        'tmcSupervisorClusterName': clusterName,
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VALIDATE_SUPERVISOR_CLUSTER;
        return this.apiHandlerService.post(url, payload);

    }
    getNsxtData(nsxtData, env='vcf') {
        let payload = {
            "envSpec":{
                "vcenterDetails":{
                    "nsxtAddress": nsxtData.nsxtAddress,
                    "nsxtUser": nsxtData.nsxtUsername,
                    "nsxtUserPasswordBase64": btoa(nsxtData.nsxtPassword)
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_TIER1_ROUTERS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    getVMCResources(sddcToken, sddcName, orgName) {
        let payload = {
            'envSpec': {
                'sddcRefreshToken': sddcToken,
                'sddcName': sddcName,
                'orgName': orgName,
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_RESOURCES;
        return this.apiHandlerService.postVmc(url, payload);
    }

    getClustersUnderDatacenterVMC(vmcData, env, infraType) {
        let payload = {
            'envSpec': {
                'sddcRefreshToken': vmcData.sddcToken,
                'sddcName': vmcData.sddcName,
                'orgName': vmcData.orgName,
                'sddcDatacenter': vmcData.datacenter,
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_CLUSTER_UNDER_DATACENTER;
        return this.apiHandlerService.postVmc(url, payload);
    }

    getDatastoresUnderDatacenterVMC(vmcData, env, infraType) {
        let payload = {
            'envSpec': {
                'sddcRefreshToken': vmcData.sddcToken,
                'sddcName': vmcData.sddcName,
                'orgName': vmcData.orgName,
                'sddcDatacenter': vmcData.datacenter,
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_DATASTORE_UNDER_DATACENTER;
        return this.apiHandlerService.postVmc(url, payload);
    }

    validateIpAndNetwork(ipData) {
        let payload = {
            'tkgComponentSpec': {
                'aviMgmtNetwork': {
                    'aviMgmtNetworkGatewayCidr': ipData['aviMgmtNetworkGatewayCidr'],
                    'aviMgmtServiceIpStartrange': ipData['aviMgmtServiceIpStartrange'],
                    'aviMgmtServiceIpEndrange': ipData['aviMgmtServiceIpEndrange']
                },
                'tkgMgmtComponents': {
                    'tkgMgmtGatewayCidr': ipData['tkgMgmtGatewayCidr'],
                    'tkMgmtControlplaneIp': ipData['tkgMgmtControlplaneIp'],
                    'tkgSharedserviceControlplaneIp': ipData['tkgSharedserviceControlplaneIp']
                }
            },
            'tkgMgmtDataNetwork': {
                'tkgMgmtDataNetworkGatewayCidr': ipData['tkgMgmtDataNetworkGatewayCidr'],
                'tkgMgmtAviServiceIpStartRange': ipData['tkgMgmtAviServiceIpStartRange'],
                'tkgMgmtAviServiceIpEndRange': ipData['tkgMgmtAviServiceIpEndRange']
            },
            'tkgWorkloadDataNetwork': {
                'tkgWorkloadDataNetworkGatewayCidr': ipData['tkgWorkloadDataNetworkGatewayCidr'],
                'tkgWorkloadAviServiceIpStartRange': ipData['tkgWorkloadAviServiceIpStartRange'],
                'tkgWorkloadAviServiceIpEndRange': ipData['tkgWorkloadAviServiceIpEndRange']
            },
            'tkgWorkloadComponents': {
                'tkgWorkloadGatewayCidr': ipData['tkgWorkloadGatewayCidr'],
                'tkgWorkloadControlplaneIp': ipData['tkgWorkloadControlplaneIp']
            },

        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VALIDATE_IP_SUBNET;
        return this.apiHandlerService.post(url, payload);
    }

    getVsphereThumbprint(data) {
        // let payload: {
        //     'host': data.vsphereHost,
        // };
        // const url = '/login/to/vc';
        // return this.apiHandlerService.post(url, payload);
        let dumy_data = 'SSL_Thumbprint_DUMY_DATA_REPLACE_WITH_API_RESPONSE' + data;
        return dumy_data;
    }

    getSSLThumbprint(env, data) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VC_SSL_THUMBPRINT;
        return this.apiHandlerService.postCall(url, data, env);
    }

    generateInputJSON(payload, filename, env) {

        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.GENERATE_JSON_INPUT;
        return this.apiHandlerService.postGenerateInput(url, payload, filename, env);
    }

    generateVmcInputJSON(payload) {

        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.GENERATE_JSON_INPUT;
        return this.apiHandlerService.postVmc(url, payload);
    }

    generateVcfInputJSON(payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.GENERATE_JSON_INPUT;
        return this.apiHandlerService.postVcf(url, payload);
    }

    setMgmtSegmentName(segmentName:string) {
        this.mgmtSegmentName = segmentName;
    }
    setMgmtGatewayCidr(gatewayCidr:string) {
        this.mgmtGatewayCidr = gatewayCidr;
    }
    getMgmtSegmentName() {
        return this.mgmtSegmentName;
    }
    getMgmtGatewayCidr() {
        return this.mgmtGatewayCidr;
    }

    triggerVmcPreConfiguration(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vmc') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VMC_PRE_CONFIGURATION;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerPrecheck(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VCF_VSPHERE_VMC_TRIGGER_PRECHECKS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    triggerAvi(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vsphere') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VCF_VSPHERE_TRIGGER_AVI;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerVmcAvi(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vmc') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VMC_TRIGGER_AVI;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerMgmt(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vsphere') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VCF_VSPHERE_TRIGGER_MGMT;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerVmcMgmt(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vmc') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VMC_TRIGGER_MGMT;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerShared(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vsphere' || env === 'vcf') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VCF_VSPHERE_TRIGGER_SHARED;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerVmcShared(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vmc') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VMC_TRIGGER_SHARED;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerWrkPreConfig(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vsphere' || env === 'vcf') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VCF_VSPHERE_TRIGGER_WRK_PRECONFIG;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerVmcWrkPreConfig(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vmc') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VMC_TRIGGER_WRK_PRECONFIG;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerWrk(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vsphere' || env === 'vcf') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VCF_VSPHERE_TRIGGER_WRK_DEPLOY;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerVmcWrk(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vmc') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VMC_TRIGGER_WRK_DEPLOY;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    triggerExtensions(env, payload) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        if (env === 'vsphere' || env === 'vcf' || env === 'vmc') {
            const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VCF_VSPHERE_VMC_TRIGGER_EXTENSIONS;
            return this.apiHandlerService.postCall(url, payload, env);
        }
    }

    streamLogs() {
        const baseUrl = this.apiEndPoint  + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = baseUrl + AppApiUrls.URL_SEPARATER + AppApiUrls.ARCAS_LOGS;
        return this.apiHandlerService.get(url);
    }

    downloadSupportBundle(env: string) {
        const baseUrl = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = baseUrl + AppApiUrls.URL_SEPARATER + AppApiUrls.SUPPORT_BUNDLE;
        return this.apiHandlerService.download(url, env);
    }

    verifyMarketplaceToken(refreshToken: string, env: string) {
        const baseUrl = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = baseUrl + AppApiUrls.URL_SEPARATER + AppApiUrls.VERIFY_MARKETPLACE_TOKEN;
        let payload = {};
        if (env === 'vsphere' || env === 'vcf') {
            payload = {
                'envSpec': {
                    'marketplaceSpec': {
                        'refreshToken': refreshToken
                    }
                }
            };
        } else if (env === 'vmc') {
            payload = {
                'marketplaceSpec': {
                    'refreshToken': refreshToken
                }
            };
        } else if (env === 'vcd') {
            payload = {
                'envSpec': {
                    'marketplaceSpec': {
                        'refreshToken': refreshToken,
                    }
                }
            };
        }
        return this.apiHandlerService.postCall(url, payload, env);
    }

    downloadLogBundle(env){
        const baseUrl = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = baseUrl + AppApiUrls.URL_SEPARATER + AppApiUrls.ARCAS_LOG_BUNDLE;
        return this.apiHandlerService.download(url, env);
    }

    getKubeVersions(env) {
        const baseUrl = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = baseUrl + AppApiUrls.URL_SEPARATER + AppApiUrls.GET_KUBE_VERSIONS;
        let payload = {};
        return this.apiHandlerService.postCall(url, payload, env);
    }

    getNamespaceDetails(vcenterData, env){
        let payload = {
            "envSpec": {
                "vcenterDetails": {
                    "vcenterAddress": vcenterData.address,
                    "vcenterSsoUser": vcenterData.user,
                    "vcenterSsoPasswordBase64": btoa(vcenterData.password),
                }
            },
            "tkgsComponentSpec": {
                "tkgsVsphereNamespaceSpec": {
                    "tkgsVsphereNamespaceName": vcenterData.namespace,
                }
            }
        };
        const baseUrl = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = baseUrl + AppApiUrls.URL_SEPARATER + AppApiUrls.NAMESPACE_DETAILS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    fetchClusterGroups(refreshToken, instanceUrl, env) {
        let payload;
        if (env === 'vmc') {
            payload = {
                'saasEndpoints': {
                    'tmcDetails': {
                        'tmcRefreshToken': refreshToken,
                        'tmcInstanceURL': instanceUrl
                    }
                }
            };
        } else {
            payload = {
                'envSpec': {
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': refreshToken,
                            'tmcInstanceURL': instanceUrl
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.FETCH_CLUSTER_GROUPS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    fetchCredentials(tmcData, env) {
        let payload;
        if (env === 'vmc') {
            payload = {
                'saasEndpoints': {
                    'tmcDetails': {
                        'tmcRefreshToken': tmcData.refreshToken,
                        'tmcInstanceURL': tmcData.instanceUrl
                    }
                }
            };
        } else {
            if (env === 'tkgs') env = 'vsphere';
            payload = {
                'envSpec': {
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': tmcData.refreshToken,
                            'tmcInstanceURL': tmcData.instanceUrl
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.FETCH_CREDENTIALS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    fetchTargetLocations(tmcData, env) {
        let payload;
        if (env === 'vmc') {
            payload = {
                'saasEndpoints': {
                    'tmcDetails': {
                        'tmcRefreshToken': tmcData.refreshToken,
                        'tmcInstanceURL': tmcData.instanceUrl
                    }
                }
            };
        } else {
            if (env === 'tkgs') env = 'vsphere';
            payload = {
                'envSpec': {
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': tmcData.refreshToken,
                            'tmcInstanceURL': tmcData.instanceUrl
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.FETCH_TARGET_LOCATIONS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    validateCredentials(tmcData, env, clusterType) {
        let payload;
        if (env === 'vmc') {
            if (clusterType === 'shared') {
                payload = {
                    'clusterType': clusterType,
                    'componentSpec': {
                        'tkgSharedServiceSpec': {
                            'tkgSharedClusterCredential': tmcData.credential,
                            'tkgSharedClusterBackupLocation': tmcData.targetLocation,
                            'tkgSharedserviceClusterGroupName': tmcData.clusterGroupName
                        }
                    },
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': tmcData.refreshToken,
                            'tmcInstanceURL': tmcData.instanceUrl
                        }
                    }
                };
            } else if (clusterType === 'workload') {
                payload = {
                    'clusterType': clusterType,
                    'componentSpec': {
                        'tkgWorkloadSpec': {
                            'tkgWorkloadClusterCredential': tmcData.credential,
                            'tkgWorkloadClusterBackupLocation': tmcData.targetLocation,
                            'tkgWorkloadClusterGroupName': tmcData.clusterGroupName
                        }
                    },
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': tmcData.refreshToken,
                            'tmcInstanceURL': tmcData.instanceUrl
                        }
                    }
                };
            }
        } else if (env === 'vsphere'){
            if (clusterType === 'shared') {
                payload = {
                    'clusterType': clusterType,
                    'tkgComponentSpec': {
                        'tkgMgmtComponents': {
                            'tkgSharedClusterCredential': tmcData.credential,
                            'tkgSharedClusterBackupLocation': tmcData.targetLocation,
                            'tkgSharedserviceClusterGroupName': tmcData.clusterGroupName
                        }
                    },
                    'envSpec': {
                        'saasEndpoints': {
                            'tmcDetails': {
                                'tmcRefreshToken': tmcData.refreshToken,
                                'tmcInstanceURL': tmcData.instanceUrl
                            }
                        }
                    }
                };
            } else if (clusterType === 'workload') {
                payload = {
                    'clusterType': clusterType,
                    'tkgWorkloadComponents': {
                        'tkgWorkloadClusterCredential': tmcData.credential,
                        'tkgWorkloadClusterBackupLocation': tmcData.targetLocation,
                        'tkgWorkloadClusterGroupName': tmcData.clusterGroupName
                    },
                    'envSpec': {
                        'saasEndpoints': {
                            'tmcDetails': {
                                'tmcRefreshToken': tmcData.refreshToken,
                                'tmcInstanceURL': tmcData.instanceUrl
                            }
                        }
                    }
                };
            }
        } else if (env === 'vcf') {
            if (clusterType === 'shared') {
                payload = {
                    'clusterType': clusterType,
                    'tkgComponentSpec': {
                        'tkgSharedserviceSpec': {
                            'tkgSharedClusterCredential': tmcData.credential,
                            'tkgSharedClusterBackupLocation': tmcData.targetLocation,
                            'tkgSharedserviceClusterGroupName': tmcData.clusterGroupName
                        }
                    },
                    'envSpec': {
                        'saasEndpoints': {
                            'tmcDetails': {
                                'tmcRefreshToken': tmcData.refreshToken,
                                'tmcInstanceURL': tmcData.instanceUrl
                            }
                        }
                    }
                };
            } else if (clusterType === 'workload') {
                payload = {
                    'clusterType': clusterType,
                    'tkgWorkloadComponents': {
                        'tkgWorkloadClusterCredential': tmcData.credential,
                        'tkgWorkloadClusterBackupLocation': tmcData.targetLocation,
                        'tkgWorkloadClusterGroupName': tmcData.clusterGroupName
                    },
                    'envSpec': {
                        'saasEndpoints': {
                            'tmcDetails': {
                                'tmcRefreshToken': tmcData.refreshToken,
                                'tmcInstanceURL': tmcData.instanceUrl
                            }
                        }
                    }
                };
            }
        } else if (env === 'tkgs') {
            env = 'vsphere';
            payload = {
                'clusterType': 'workload',
                'envSpec': {
                    'envType': 'tkgs-ns',
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': tmcData.refreshToken,
                            'tmcInstanceURL': tmcData.instanceUrl
                        }
                    }
                },
                'tkgsComponentSpec': {
                    'tkgsVsphereNamespaceSpec': {
                        'tkgsVsphereWorkloadClusterSpec': {
                            'tkgWorkloadClusterCredential': tmcData.credential,
                            'tkgWorkloadClusterBackupLocation': tmcData.targetLocation,
                            'tkgsWorkloadClusterGroupName': tmcData.clusterGroupName
                        }
                    }
                }

            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VALIDATE_CREDENTIALS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    validateTargetLocations(tmcData, env, clusterType) {
        let payload;
        if (env === 'vmc') {
            if (clusterType === 'shared') {
                payload = {
                    'clusterType': clusterType,
                    'componentSpec': {
                        'tkgSharedServiceSpec': {
                            'tkgSharedClusterBackupLocation': tmcData.backupLocation,
                            'tkgSharedClusterCredential': tmcData.credential,
                            'tkgSharedserviceClusterGroupName': tmcData.clusterGroupName
                        }
                    },
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': tmcData.refreshToken,
                            'tmcInstanceURL': tmcData.instanceUrl
                        }
                    }
                };
            } else if (clusterType === 'workload') {
                payload = {
                    'clusterType': clusterType,
                    'componentSpec': {
                        'tkgWorkloadSpec': {
                            'tkgWorkloadClusterBackupLocation': tmcData.backupLocation,
                            'tkgWorkloadClusterCredential': tmcData.credential,
                            'tkgWorkloadClusterGroupName': tmcData.clusterGroupName
                        }
                    },
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': tmcData.refreshToken,
                            'tmcInstanceURL': tmcData.instanceUrl
                        }
                    }
                };
            }

        } else if (env === 'vsphere'){
            if (clusterType === 'shared') {
                payload = {
                    'clusterType': clusterType,
                    'tkgComponentSpec': {
                        'tkgMgmtComponents': {
                            'tkgSharedClusterBackupLocation': tmcData.backupLocation,
                            'tkgSharedClusterCredential': tmcData.credential,
                            'tkgSharedserviceClusterGroupName': tmcData.clusterGroupName
                        }
                    },
                    'envSpec': {
                        'saasEndpoints': {
                            'tmcDetails': {
                                'tmcRefreshToken': tmcData.refreshToken,
                                'tmcInstanceURL': tmcData.instanceUrl
                            }
                        }
                    }
                };
            } else if (clusterType === 'workload') {
                payload = {
                    'clusterType': clusterType,
                    'tkgWorkloadComponents': {
                        'tkgWorkloadClusterBackupLocation': tmcData.backupLocation,
                        'tkgWorkloadClusterCredential': tmcData.credential,
                        'tkgWorkloadClusterGroupName': tmcData.clusterGroupName
                    },
                    'envSpec': {
                        'saasEndpoints': {
                            'tmcDetails': {
                                'tmcRefreshToken': tmcData.refreshToken,
                                'tmcInstanceURL': tmcData.instanceUrl
                            }
                        }
                    }
                };
            }
        } else if (env === 'vcf') {
            if (clusterType === 'shared') {
                payload = {
                    'clusterType': clusterType,
                    'tkgComponentSpec': {
                        'tkgSharedserviceSpec': {
                            'tkgSharedClusterBackupLocation': tmcData.backupLocation,
                            'tkgSharedClusterCredential': tmcData.credential,
                            'tkgSharedserviceClusterGroupName': tmcData.clusterGroupName
                        }
                    },
                    'envSpec': {
                        'saasEndpoints': {
                            'tmcDetails': {
                                'tmcRefreshToken': tmcData.refreshToken,
                                'tmcInstanceURL': tmcData.instanceUrl
                            }
                        }
                    }
                };
            } else if (clusterType === 'workload') {
                payload = {
                    'clusterType': clusterType,
                    'tkgWorkloadComponents': {
                        'tkgWorkloadClusterBackupLocation': tmcData.backupLocation,
                        'tkgWorkloadClusterCredential': tmcData.credential,
                        'tkgWorkloadClusterGroupName': tmcData.clusterGroupName
                    },
                    'envSpec': {
                        'saasEndpoints': {
                            'tmcDetails': {
                                'tmcRefreshToken': tmcData.refreshToken,
                                'tmcInstanceURL': tmcData.instanceUrl
                            }
                        }
                    }
                };
            }
        } else if (env === 'tkgs') {
            env = 'vsphere';
            payload = {
                'clusterType': 'workload',
                'envSpec': {
                    'envType': 'tkgs-ns',
                    'saasEndpoints': {
                        'tmcDetails': {
                            'tmcRefreshToken': tmcData.refreshToken,
                            'tmcInstanceURL': tmcData.instanceUrl
                        }
                    }
                },
                'tkgsComponentSpec': {
                    'tkgsVsphereNamespaceSpec': {
                        'tkgsVsphereWorkloadClusterSpec': {
                            'tkgWorkloadClusterBackupLocation': tmcData.backupLocation,
                            'tkgWorkloadClusterCredential': tmcData.credential,
                            'tkgsWorkloadClusterGroupName': tmcData.clusterGroupName
                        }
                    }
                }

            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VALIDATE_TARGET_LOCATIONS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    verifyLdapConnect(ldapData, env) {
        let payload;
        if (env === 'vmc') {
            payload = {
                'componentSpec': {
                    'identityManagementSpec': {
                        'ldapSpec': {
                            'ldapEndpointIp': ldapData.ldapEndpointIp,
                            'ldapEndpointPort': ldapData.ldapEndpointPort,
                            'ldapRootCAData': ldapData.ldapRootCAData,
                        }
                    }
                }
            };
        } else if (env === 'vsphere' || env === 'vsphere-nsxt'){
            if (env === 'vsphere-nsxt') env = 'vcf';
            payload = {
                'tkgComponentSpec': {
                    'identityManagementSpec': {
                        'ldapSpec': {
                            'ldapEndpointIp': ldapData.ldapEndpointIp,
                            'ldapEndpointPort': ldapData.ldapEndpointPort,
                            'ldapRootCAData': ldapData.ldapRootCAData,
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LDAP_CONNECT;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    verifyLdapBind(ldapData, env) {
        let payload;
        if (env === 'vmc') {
            payload = {
                'componentSpec': {
                    'identityManagementSpec': {
                        'ldapSpec': {
                            'ldapEndpointIp': ldapData.ldapEndpointIp,
                            'ldapEndpointPort': ldapData.ldapEndpointPort,
                            'ldapRootCAData': ldapData.ldapRootCAData,
                            'ldapBindDN': ldapData.ldapBindDN,
                            'ldapBindPW': ldapData.ldapBindPW,
                        }
                    }
                }
            };
        } else if (env === 'vsphere' || env === 'vsphere-nsxt'){
            if (env === 'vsphere-nsxt') env = 'vcf';
            payload = {
                'tkgComponentSpec': {
                    'identityManagementSpec': {
                        'ldapSpec': {
                            'ldapEndpointIp': ldapData.ldapEndpointIp,
                            'ldapEndpointPort': ldapData.ldapEndpointPort,
                            'ldapRootCAData': ldapData.ldapRootCAData,
                            'ldapBindDN': ldapData.ldapBindDN,
                            'ldapBindPW': ldapData.ldapBindPW,
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LDAP_BIND;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    verifyLdapUserSearch(ldapData, env) {
        let payload;
        if (env === 'vmc') {
            payload = {
                'componentSpec': {
                    'identityManagementSpec': {
                        'ldapSpec': {
                            'ldapEndpointIp': ldapData.ldapEndpointIp,
                            'ldapEndpointPort': ldapData.ldapEndpointPort,
                            'ldapRootCAData': ldapData.ldapRootCAData,
                            'ldapBindDN': ldapData.ldapBindDN,
                            'ldapBindPW': ldapData.ldapBindPW,
                            'ldapUserSearchBaseDN': ldapData.ldapUserSearchBaseDN,
                            'ldapUserSearchFilter': ldapData.ldapUserSearchFilter,
                            'ldapUserSearchUsername': ldapData.ldapUserSearchUsername,
                            'ldapTestUserName': ldapData.ldapTestUserName,
                        }
                    }
                }
            };
        } else if (env === 'vsphere' || env === 'vsphere-nsxt'){
            if (env === 'vsphere-nsxt') env = 'vcf';
            payload = {
                'tkgComponentSpec': {
                    'identityManagementSpec': {
                        'ldapSpec': {
                            'ldapEndpointIp': ldapData.ldapEndpointIp,
                            'ldapEndpointPort': ldapData.ldapEndpointPort,
                            'ldapRootCAData': ldapData.ldapRootCAData,
                            'ldapBindDN': ldapData.ldapBindDN,
                            'ldapBindPW': ldapData.ldapBindPW,
                            'ldapUserSearchBaseDN': ldapData.ldapUserSearchBaseDN,
                            'ldapUserSearchFilter': ldapData.ldapUserSearchFilter,
                            'ldapUserSearchUsername': ldapData.ldapUserSearchUsername,
                            'ldapTestUserName': ldapData.ldapTestUserName,
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LDAP_USER_SEARCH;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    verifyLdapGroupSearch(ldapData, env) {
        let payload;
        if (env === 'vmc') {
            payload = {
                'componentSpec': {
                    'identityManagementSpec': {
                        'ldapSpec': {
                            'ldapEndpointIp': ldapData.ldapEndpointIp,
                            'ldapEndpointPort': ldapData.ldapEndpointPort,
                            'ldapRootCAData': ldapData.ldapRootCAData,
                            'ldapBindDN': ldapData.ldapBindDN,
                            'ldapBindPW': ldapData.ldapBindPW,
                            'ldapGroupSearchBaseDN': ldapData.ldapGroupSearchBaseDN,
                            'ldapGroupSearchFilter': ldapData.ldapGroupSearchFilter,
                            'ldapGroupSearchUserAttr': ldapData.ldapGroupSearchUserAttr,
                            'ldapGroupSearchGroupAttr': ldapData.ldapGroupSearchGroupAttr,
                            'ldapGroupSearchNameAttr': ldapData.ldapGroupSearchNameAttr,
                            'ldapTestGroupName': ldapData.ldapTestGroupName,
                        }
                    }
                }
            };
        } else if (env === 'vsphere' || env === 'vsphere-nsxt'){
            if (env === 'vsphere-nsxt') env = 'vcf';
            payload = {
                'tkgComponentSpec': {
                    'identityManagementSpec': {
                        'ldapSpec': {
                            'ldapEndpointIp': ldapData.ldapEndpointIp,
                            'ldapEndpointPort': ldapData.ldapEndpointPort,
                            'ldapRootCAData': ldapData.ldapRootCAData,
                            'ldapBindDN': ldapData.ldapBindDN,
                            'ldapBindPW': ldapData.ldapBindPW,
                            'ldapGroupSearchBaseDN': ldapData.ldapGroupSearchBaseDN,
                            'ldapGroupSearchFilter': ldapData.ldapGroupSearchFilter,
                            'ldapGroupSearchUserAttr': ldapData.ldapGroupSearchUserAttr,
                            'ldapGroupSearchGroupAttr': ldapData.ldapGroupSearchGroupAttr,
                            'ldapGroupSearchNameAttr': ldapData.ldapGroupSearchNameAttr,
                            'ldapTestGroupName': ldapData.ldapTestGroupName,
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LDAP_GROUP_SEARCH;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    verifyLdapCloseConnection(ldapData, env) {
        let payload = {};
        if (env === 'vsphere-nsxt') env = 'vcf';
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LDAP_DISCONNECT;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    // =============================== VCD APIS ============================================

    /**
     * @method connectToVCD
     * @desc method to validate VCD credentials
     * @param data - contains vcdAddress, vcdSysAdminUserName, vcdSysAdminPasswordBase64
     * @param env - will be 'vcd'
     */
    connectToVCD(env, data) {
        let payload;
        if(env === 'vcd') {
            payload = {
                'envSpec': {
                    'vcdSpec': {
                        'vcdComponentSpec': {
                            'vcdAddress': data['vcdAddress'],
                            'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                            'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.CONNECT_TO_VCD;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    /**
     * @method getVsphere1Data
     * @desc method to list all the resources under vcenter 1
     * @param data - contains vcenterAddress, vcenterSsoUser, vcenterSsoPasswordBase64
     * @param env - will be 'vcd'
     */
    getVsphere1Data(env, data){
        let payload = {
            'envSpec': {
                'aviCtrlDeploySpec': {
                    'vcenterDetails': {
                        'vcenterAddress': data.vcenterAddress,
                        'vcenterSsoUser': data.vcenterSsoUser,
                        'vcenterSsoPasswordBase64': btoa(data.vcenterSsoPasswordBase64),
                    }
                }
            }
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_RESOURCES;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    /**
     * @method getDatastoresUnderDatacenterVsphere1
     * @desc method to list all the clusters under datacenter in vsphere 1
     * @param data - contains vcenterAddress, vcenterSsoUser, vcenterSsoPasswordBase64, vcenterDatacenter
     * @param env - will be 'vcd'
     */
    getClustersUnderDatacenterVsphere1(env, data) {
        let payload = {
            'envSpec': {
                'aviCtrlDeploySpec': {
                    'vcenterDetails': {
                        'vcenterAddress': data['vcenterAddress'],
                        'vcenterSsoUser': data['vcenterSsoUser'],
                        'vcenterSsoPasswordBase64': btoa(data['vcenterSsoPasswordBase64']),
                        'vcenterDatacenter': data['vcenterDatacenter'],
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_CLUSTER_UNDER_DATACENTER;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    /**
     * @method getDatastoresUnderDatacenterVsphere1
     * @desc method to list all the datastores under datacenter in vsphere 1
     * @param data - contains vcenterAddress, vcenterSsoUser, vcenterSsoPasswordBase64, vcenterDatacenter
     * @param env - will be 'vcd'
     */
    getDatastoresUnderDatacenterVsphere1(env, data) {
        let payload = {
            'envSpec': {
                'aviCtrlDeploySpec': {
                    'vcenterDetails': {
                        'vcenterAddress': data['vcenterAddress'],
                        'vcenterSsoUser': data['vcenterSsoUser'],
                        'vcenterSsoPasswordBase64': btoa(data['vcenterSsoPasswordBase64']),
                        'vcenterDatacenter': data['vcenterDatacenter'],
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_DATASTORE_UNDER_DATACENTER;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    /**
     * @method getOvaImagesUnderContentLibraryVsphere1
     * @desc method to list all the content library items from content-lib 1 in vsphere 1
     * @param data - contains vcenterAddress, vcenterSsoUser, vcenterSsoPasswordBase64, contentLibraryName
     * @param env - will be 'vcd'
     */
    getOvaImagesUnderContentLibraryVsphere1(env, data) {
        let payload = {
            'envSpec': {
                'aviCtrlDeploySpec': {
                    'vcenterDetails': {
                        'vcenterAddress': data['vcenterAddress'],
                        'vcenterSsoUser': data['vcenterSsoUser'],
                        'vcenterSsoPasswordBase64': btoa(data['vcenterSsoPasswordBase64']),
                        'contentLibraryName': data['contentLibraryName']
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_CONTENTLIB_FILES;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    /**
     * @method aviNameResolutionForVCD
     * @desc method to verify if DNS mapping exists for provided AVI controller ip and fqdn
     * @param data - contains dnsServersIp, vcenterAddress, vcenterSsoUser, vcenterSsoPasswordBase64, enableAviHa
     * @param data - contains aviController01Ip, aviController01Fqdn, aviController02Ip, aviController02Fqdn
     * @param data - contains aviController03Ip, aviController03Fqdn, aviClusterIp, aviClusterFqdn
     * @param env - will be 'vcd'
     */
    aviNameResolutionForVCD(env, data) {
        let payload;
        if (data['deployAvi']) {
            payload = {
                "envSpec": {
                    "infraComponents": {
                        "dnsServersIp": data['dnsServersIp'],
                    },
                    "aviCtrlDeploySpec": {
                        'deployAvi': 'true',
                        'vcenterDetails': {
                            'vcenterAddress': data['vcenterAddress'],
                            'vcenterSsoUser': data['vcenterSsoUser'],
                            'vcenterSsoPasswordBase64': btoa(data['vcenterSsoPasswordBase64']),
                        },
                        'aviComponentsSpec': {
                            'enableAviHa': data['enableAviHa'],
                            'aviController01Ip': data['aviController01Ip'],
                            'aviController01Fqdn': data['aviController01Fqdn'],
                            'aviController02Ip': data['aviController02Ip'],
                            'aviController02Fqdn': data['aviController02Fqdn'],
                            'aviController03Ip': data['aviController03Ip'],
                            'aviController03Fqdn': data['aviController03Fqdn'],
                            'aviClusterIp': data['aviClusterIp'],
                            'aviClusterFqdn': data['aviClusterFqdn'],
                        }
                    }
                }
            };
        } else {
            payload = {
                "envSpec": {
                    "infraComponents": {
                        "dnsServersIp": data['dnsServersIp'],
                    },
                    "aviCtrlDeploySpec": {
                        'deployAvi': 'false',
                        'vcenterDetails': {
                            'vcenterAddress': data['vcenterAddress'],
                            'vcenterSsoUser': data['vcenterSsoUser'],
                            'vcenterSsoPasswordBase64': btoa(data['vcenterSsoPasswordBase64']),
                        },
                        'aviComponentsSpec': {
                            'aviClusterIp': data['aviClusterIp'],
                            'aviClusterFqdn': data['aviClusterFqdn'],
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.NAME_RESOLUTION;
        return this.apiHandlerService.postCall(url, payload, 'vcd');
    }


    /**
     * @method listAVIVCDDisplayNames
     * @desc method to list all the AVI VCD display names from VCD environment
     * @param data - contains vcdAddress, vcdSysAdminUserName, vcdSysAdminPasswordBase64
     * @param env - will be 'vcd'
     */
    listAVIVCDDisplayNames(env, data) {
        let payload;
        if(env === 'vcd') {
            payload = {
                'envSpec': {
                    'vcdSpec': {
                        'vcdComponentSpec': {
                            'vcdAddress': data['vcdAddress'],
                            'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                            'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                        }
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_AVI_VCD_DISPLAY_NAMES;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    /**
     * @method listNSXTCloudsConfiguredInAVI
     * @desc method to list all the NSXT Clouds configured in AVI
     * @param data - contains deployAvi, aviController01Ip(if deployAvi=true), aviClusterIp(id deployAvi=false), aviUsername, aviPasswordBase64
     * @param env - will be 'vcd'
     */
    listNSXTCloudsConfiguredInAVI(env, data) {
        let payload;
        if(env === 'vcd') {
            if(data['deployAvi'] === 'true') {
                payload = {
                    'envSpec': {
                        'aviCtrlDeploySpec': {
                            'deployAvi': 'true',
                            'aviComponentsSpec': {
                                'aviController01Ip': data['aviController01Ip'],
                                'aviUsername': data['aviUsername'],
                                'aviPasswordBase64': btoa(data['aviPasswordBase64']),
                            }
                        }
                    }
                };
            } else {
                payload = {
                    'envSpec': {
                        'aviCtrlDeploySpec': {
                            'deployAvi': 'false',
                            'aviComponentsSpec': {
                                'aviClusterIp': data['aviClusterIp'],
                                'aviUsername': data['aviUsername'],
                                'aviPasswordBase64': btoa(data['aviPasswordBase64']),
                            }
                        }
                    }
                };
            }
        } else {

        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_AVI_NSX_CLOUD_NAMES;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    /**
     * @method listNsxtCloudVcdDisplayNames
     * @desc method to list all the NSXT Cloud VCD display names
     * @param data - contains vcdAddress, vcdSysAdminUserName, vcdSysAdminPasswordBase64
     * @param env - will be 'vcd'
     */
    listNsxtCloudVcdDisplayNames(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_NSXT_CLOUD_VCD_DISPLAY_NAMES;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    fetchT0FromNsxt(env, data) {
        let payload = {
            'envSpec': {
                'aviNsxCloudSpec': {
                    'nsxDetails': {
                        'nsxtAddress': data['nsxtAddress'],
                        'nsxtUser': data['nsxtUser'],
                        'nsxtUserPasswordBase64': btoa(data['nsxtUserPasswordBase64']),
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_T0_ROUTERS_FROM_NSXT;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    fetchT0FromVcd(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_T0_ROUTERS_FROM_VCD;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    fetchIpRangesForSelectedTier0(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                },
                'cseSpec': {
                    'svcOrgVdcSpec': {
                        'svcOrgVdcGatewaySpec': {
                            'tier0GatewaySpec': {
                                'tier0GatewayName': data['tier0GatewayName']
                            }
                        }
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.FETCH_IP_RANGES_FOR_T0;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    fetchSvcOrgNames(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_SVC_ORG_NAMES;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    fetchProviderVdcNames(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_PROVIDER_VDC_NAMES;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    fetchNetworkPoolNames(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_NETWORK_POOL_NAMES;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    fetchStoragePoliciesFromVdc(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_STORAGE_POLICIES;
        return this.apiHandlerService.postCall(url, payload, env);
    }


    fetchServiceEngineGroupNamesFromALB(env, data) {
        let payload;
        if(data['deployAvi'] === 'true') {
            payload = {
                'envSpec': {
                    'aviCtrlDeploySpec': {
                        'deployAvi': data['deployAvi'],
                        'aviComponentsSpec': {
                            'aviUsername': data['aviUsername'],
                            'aviPasswordBase64': btoa(data['aviPasswordBase64']),
                            'aviController01Ip': data['aviController01Ip'],
                        }
                    },
                    'aviNsxCloudSpec': {
                        'aviNsxCloudName': data['aviNsxCloudName']
                    }
                }
            };
        } else {
            payload = {
                'envSpec': {
                    'aviCtrlDeploySpec': {
                        'deployAvi': 'false',
                        'aviComponentsSpec': {
                            'aviUsername': data['aviUsername'],
                            'aviPasswordBase64': btoa(data['aviPasswordBase64']),
                            'aviClusterIp': data['aviClusterIp'],
                        }
                    },
                    'aviNsxCloudSpec': {
                        'aviNsxCloudName': data['aviNsxCloudName']
                    }
                }
            };
        }
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_SEG_NAMES_FROM_ALB;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    fetchServiceEngineGroupNamesFromVCD(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_SEG_NAMES_FROM_VCD;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    fetchCatalogsFromVCD(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                },
                'cseSpec': {
                    'svcOrgSpec': {
                        'svcOrgName': data['svcOrgName']
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_CATALOGS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    validateOrgPublishStatus(env, data) {
        let payload = {
            'envSpec': {
                'vcdSpec': {
                    'vcdComponentSpec': {
                        'vcdAddress': data['vcdAddress'],
                        'vcdSysAdminUserName': data['vcdSysAdminUserName'],
                        'vcdSysAdminPasswordBase64': btoa(data['vcdSysAdminPasswordBase64']),
                    }
                },
                'cseSpec': {
                    'svcOrgSpec': {
                        'svcOrgName': data['svcOrgName']
                    }
                }
            }
        };
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VALIDATE_ORG_PUBLISH_STATUS;
        return this.apiHandlerService.postCall(url, payload, env);
    }

    // fetchK8sTemplatCatalogNames(env, data) {
    //     let payload = {};
    //     const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
    //     const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.LIST_K8S_OVA_CATALOGS;
    //     return this.apiHandlerService.postCall(url, payload, env);
    // }
}
