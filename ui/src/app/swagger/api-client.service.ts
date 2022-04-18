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

    // Kubernetes Base OS Image
    public baseImage = ['photon', 'ubuntu'];
    public baseImageVersion = ['v1.22.5', 'v1.21.8', 'v1.20.14'];
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

    public vcAddress;
    public vcUser;
    public vcPass;
    public fetchNamespaceStorageSpec = false;

    public clusterVersionMismatch = false;
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

    enableArcasProxy(httpProxy, httpsProxy, noProxy, env) {
        let payload = {
            "envSpec": {
                "proxySpec": {
                    "arcasVm": {
                        "enableProxy": "true",
                        "httpProxy": httpProxy,
                        "httpsProxy": httpsProxy,
                        "noProxy": noProxy
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

    getVMCSession(vmcData) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url = base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.ESTABLISH_VMC_SESSION;
        return this.apiHandlerService.postVmc(url, vmcData);
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
            return this.apiHandlerService.post(url, payloadVsphere);
        } else if (env === 'vcf') {
            return this.apiHandlerService.postVcf(url, payloadVcf);
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
    getNsxtData(nsxtData) {
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
        return this.apiHandlerService.postVcf(url, payload);
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

    getSSLThumbprint(data) {
        const base_url = this.apiEndPoint + AppApiUrls.URL_SEPARATER + AppApiUrls.BASE_URL;
        const url =  base_url + AppApiUrls.URL_SEPARATER + AppApiUrls.VC_SSL_THUMBPRINT;
        return this.apiHandlerService.post(url, data);
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

}
