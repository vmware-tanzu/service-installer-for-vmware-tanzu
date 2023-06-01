/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable()
export  class VCDDataService {

    // ====================================== VCD Specififc Values =================================== //
    public aviGreenfield = false;
    public configureAviNsxtCloud = false;
    public createSeGroup = false;

    public t0StartAddress = null;
    public t0EndAddress = null;
    public t0GatewayCidr = null;
    public tier0IpRangeErrorMessage = null;

    public aviVcdDisplayNames = [];
    public aviVcdDisplayNamesErrorMessage = null;

    public nsxtCloudsInALB = [];
    public nsxtCloudsInAlbErrorMessage = null;

    public vc2Datacenters = [];
    public vc2Clusters = [];
    public vc2Datastores = [];
    public vc2ContentLibs = [];

    public nsxtCloudVcdDisplayNames = [];
    public nsxtCloudVcdDisplayNameErrorMessage = null;

    public importTier0Nsxt = false;
    public t0GatewayFromNsxt = [];
    public t0GatewayFromNsxtErrorMessage = null;

    public t0GatewayFromVcd = [];
    public t0GatewayFromVcdErrorMessage = null;

    public svcOrgNames = [];
    public svcOrgNamesErrorMessage = null;
    public newOrgCreation = false;

    public providerVDCNames = [];
    public providerVDCErrorMessage = null;

    public networkPoolNames = [];
    public networkPoolNamesErrorMessage = null;

    //Policy list used as from API client (TKGS)
    public storagePolicyErrorMessage = null;

    public importServiceEngineGroup = false;

    public serviceEngineGroupnamesAlb = [];
    public serviceEngineGroupnameAlbErrorMessage = null;

    public serviceEngineGroupVcdDisplayNames = [];
    public serviceEngineGroupVcdDisplayNameErrorMessage = null;

    public catalogNames = [];
    public catalogNamesErrorMessage = null;

    // ==================================== Subscription variables ===================================== //
    private useInputFile = new BehaviorSubject<boolean>(false);
    currentInputFileStatus = this.useInputFile.asObservable();
    changeInputFileStatus(useInputFile:boolean) {
        this.useInputFile.next(useInputFile);
    }
    // ====================================================================================== //


    // ============================================= INFRASTRUCTURE DETAILS ======================================== //
    private dnsServer = new BehaviorSubject('');
    currentDnsValue = this.dnsServer.asObservable();
    changeDnsServer(dnsServer:string) {
        this.dnsServer.next(dnsServer);
    }
    private ntpServer = new BehaviorSubject('');
    currentNtpValue = this.ntpServer.asObservable();
    changeNtpServer(ntpServer:string) {
        this.ntpServer.next(ntpServer);
    }
    private searchDomain = new BehaviorSubject('');
    currentSearchDomainValue = this.searchDomain.asObservable();
    changeSearchDomain(searchDomian: string) {
        this.searchDomain.next(searchDomian);
    }
    // ====================================================================================== //


    // ======================================== VCD SPECIFICATIONS ================================================== //
    private vcdAddress = new BehaviorSubject('');
    currentVcdAddress = this.vcdAddress.asObservable();
    changeVcdAddress(vcAddress:string) {
        this.vcdAddress.next(vcAddress);
    }
    private vcdUsername = new BehaviorSubject('');
    currentVcdUsername = this.vcdUsername.asObservable();
    changeVcdUsername(vcUser:string) {
        this.vcdUsername.next(vcUser);
    }
    private vcdPassword = new BehaviorSubject('');
    currentVcdPassword = this.vcdPassword.asObservable();
    changeVcdPassword(vcPass:string) {
        this.vcdPassword.next(vcPass);
    }
    private isCeipEnabled = new BehaviorSubject<boolean>(false);
    currentCeipParticipation = this.isCeipEnabled.asObservable();
    changeCeipParticipation(ceip: boolean) {
        this.isCeipEnabled.next(ceip);
    }
    // ========================================================================================= //


    // ====================================== MARKETPLACE ================================================================ //
    private isMarketplace = new BehaviorSubject<boolean>(false);
    currentMarketplace = this.isMarketplace.asObservable();
    changeIsMarketplace(isMarketplace: boolean) {
        this.isMarketplace.next(isMarketplace);
    }
    private marketplaceRefreshToken = new BehaviorSubject('');
    currentMarketplaceRefreshToken = this.marketplaceRefreshToken.asObservable();
    changeMarketplaceRefreshToken(marketplaceRefreshToken: string) {
        this.marketplaceRefreshToken.next(marketplaceRefreshToken);
    }
    // ====================================================================================== //


    // ============================================== GREENFIELD OR BROWNFIELD ============================================= //
    private deployAvi = new BehaviorSubject<boolean>(false);
    currentDeployAvi = this.deployAvi.asObservable();
    changeDeployAvi(deploy: boolean) {
        this.deployAvi.next(deploy);
    }
    // ====================================================================================== //


    // ====================================== VSPHERE DETAILS ============================================================== //
    private vcAddress = new BehaviorSubject('');
    currentVcAddress = this.vcAddress.asObservable();
    changeVCAddress(vcAddress:string) {
        this.vcAddress.next(vcAddress);
    }
    private vcUser = new BehaviorSubject('');
    currentVcUser = this.vcUser.asObservable();
    changeVCUser(vcUser:string) {
        this.vcUser.next(vcUser);
    }
    private vcPass = new BehaviorSubject('');
    currentVcPass = this.vcPass.asObservable();
    changeVCPass(vcPass:string) {
        this.vcPass.next(vcPass);
    }
    private datastore = new BehaviorSubject('');
    currentDatastore = this.datastore.asObservable();
    changeDatastore(datastore:string) {
        this.datastore.next(datastore);
    }
    private cluster = new BehaviorSubject('');
    currentCluster = this.cluster.asObservable();
    changeCluster(cluster:string) {
        this.cluster.next(cluster);
    }
    private datacenter = new BehaviorSubject('');
    currentDatacenter = this.datacenter.asObservable();
    changeDatacenter(datacenter: string) {
        this.datacenter.next(datacenter);
    }
    private contentLib = new BehaviorSubject('');
    currentContentLib = this.contentLib.asObservable();
    changeContentLib(contentLib: string) {
        this.contentLib.next(contentLib);
    }
    private ovaImage = new BehaviorSubject('');
    currentOvaImage = this.ovaImage.asObservable();
    changeOvaImage(ovaImage: string) {
        this.ovaImage.next(ovaImage);
    }
    private resourcePool = new BehaviorSubject('');
    currentResourcePool = this.resourcePool.asObservable();
    changeResourcePool(resourcePool: string) {
        this.resourcePool.next(resourcePool);
    }
    // ====================================================================================== //


    // ========================================= AVI MANAGEMENT NETWORK ======================================================= //
    private aviMgmtNetworkName = new BehaviorSubject('');
    currentAviMgmtNetworkName = this.aviMgmtNetworkName.asObservable();
    changeAviMgmtNetworkName(networkName: string) {
        this.aviMgmtNetworkName.next(networkName);
    }
    private aviMgmtNetworkGatewayCidr = new BehaviorSubject('');
    currentAviMgmtNetworkGatewayCidr = this.aviMgmtNetworkGatewayCidr.asObservable();
    changeAviMgmtNetworkGatewayCidr(cidr: string) {
        this.aviMgmtNetworkGatewayCidr.next(cidr);
    }
    // ====================================================================================== //


    // ========================================= AVI COMPONENT SPECIFICATIONS ================================================= //
    private aviUsername = new BehaviorSubject('');
    currentAviUsername = this.aviUsername.asObservable();
    changeAviUsername(username: string) {
        this.aviUsername.next(username);
    }
    private aviPasswordBase64 = new BehaviorSubject('');
    currentAviPasswordBase64 = this.aviPasswordBase64.asObservable();
    changeAviPasswordBase64(pass: string) {
        this.aviPasswordBase64.next(pass);
    }
    private aviBackupPassphraseBase64 = new BehaviorSubject('');
    currentAviBackupPassphraseBase64 = this.aviBackupPassphraseBase64.asObservable();
    changeAviBackupPasswordBase64(pass: string) {
        this.aviBackupPassphraseBase64.next(pass);
    }
    private enableAviHa = new BehaviorSubject<boolean>(false);
    currentEnableAviHa= this.enableAviHa.asObservable();
    changeEnableAviHa(enableHa: boolean) {
        this.enableAviHa.next(enableHa);
    }
    private aviController01Ip = new BehaviorSubject('');
    currentAviController01Ip = this.aviController01Ip.asObservable();
    changeAviController01Ip(aviIp: string) {
        this.aviController01Ip.next(aviIp);
    }
    private aviController01Fqdn = new BehaviorSubject('');
    currentAviController01Fqdn = this.aviController01Fqdn.asObservable();
    changeAviController01Fqdn(aviFqdn: string) {
        this.aviController01Fqdn.next(aviFqdn);
    }
    private aviController02Ip = new BehaviorSubject('');
    currentAviController02Ip = this.aviController02Ip.asObservable();
    changeAviController02Ip(aviIp: string) {
        this.aviController02Ip.next(aviIp);
    }
    private aviController02Fqdn = new BehaviorSubject('');
    currentAviController02Fqdn = this.aviController02Fqdn.asObservable();
    changeAviController02Fqdn(aviFqdn: string) {
        this.aviController02Fqdn.next(aviFqdn);
    }
    private aviController03Ip = new BehaviorSubject('');
    currentAviController03Ip = this.aviController03Ip.asObservable();
    changeAviController03Ip(aviIp: string) {
        this.aviController03Ip.next(aviIp);
    }
    private aviController03Fqdn = new BehaviorSubject('');
    currentAviController03Fqdn = this.aviController03Fqdn.asObservable();
    changeAviController03Fqdn(aviFqdn: string) {
        this.aviController03Fqdn.next(aviFqdn);
    }
    private aviClusterIp = new BehaviorSubject('');
    currentAviClusterIp = this.aviClusterIp.asObservable();
    changeAviClusterIp(clusterIp: string) {
        this.aviClusterIp.next(clusterIp);
    }
    private aviClusterFqdn = new BehaviorSubject('');
    currentAviClusterFqdn = this.aviClusterFqdn.asObservable();
    changeAviClusterFqdn(clusterFqdn: string) {
        this.aviClusterFqdn.next(clusterFqdn);
    }
    private aviSize = new BehaviorSubject('');
    currentAviSize = this.aviSize.asObservable();
    changeAviSize(size: string){
        this.aviSize.next(size);
    }
    private aviCertPath = new BehaviorSubject('');
    currentAviCertPath = this.aviCertPath.asObservable();
    changeAviCertPath(certPath: string) {
        this.aviCertPath.next(certPath);
    }
    private aviCertKeyPath = new BehaviorSubject('');
    currentAviCertKeyPath = this.aviCertKeyPath.asObservable();
    changeAviCertKeyPath(certKeyPath: string) {
        this.aviCertKeyPath.next(certKeyPath);
    }
    // ====================================================================================== //


    // ======================================== AVI VCD DISPLAY NAME ============================================================ //
    private aviVcdDisplayName = new BehaviorSubject('');
    currentAviVcdDisplayName = this.aviVcdDisplayName.asObservable();
    changeAviVcdDisplayName(name: string) {
        this.aviVcdDisplayName.next(name);
    }
    // ====================================================================================== //


    // ======================================== AVI NSXT CLOUD SPECIFICATIONS ==================================================== //
    private configureNsxtCloud = new BehaviorSubject<boolean>(false);
    currentConfigureNsxtCloud = this.configureNsxtCloud.asObservable();
    changeConfigureNsxtCloud(conf: boolean) {
        this.configureNsxtCloud.next(conf);
    }
    // ====================================================================================== //


    // ===================================================== NSXT DETAILS ======================================================== //
    private nsxtAddress = new BehaviorSubject('');
    currentNsxtAddress = this.nsxtAddress.asObservable();
    changeNsxtAddress(add: string) {
        this.nsxtAddress.next(add);
    }
    private nsxtUser = new BehaviorSubject('');
    currentNsxtUser = this.nsxtUser.asObservable();
    changeNsxtUser(user: string) {
        this.nsxtUser.next(user);
    }
    private nsxtUserPasswordBase64 = new BehaviorSubject('');
    currentNsxtUserPasswordBase64 = this.nsxtUserPasswordBase64.asObservable();
    changeNsxtUserPasswordBase64(pass: string) {
        this.nsxtUserPasswordBase64.next(pass);
    }
    // ====================================================================================== //


    // ================================================= AVI NSX CLOUD NAME ======================================================= //
    private aviNsxCloudName = new BehaviorSubject('');
    currentAviNsxCloudName = this.aviNsxCloudName.asObservable();
    changeAviNsxCloudName(name: string) {
        this.aviNsxCloudName.next(name);
    }
    // ====================================================================================== //


    // ============================================= VCENTER DETAILS ============================================================= //
    private vcenterAddressCloud = new BehaviorSubject('');
    currentVcenterAddressCloud = this.vcenterAddressCloud.asObservable();
    changeVcenterAddressCloud(add: string) {
        this.vcenterAddressCloud.next(add);
    }
    private vcenterSsoUserCloud = new BehaviorSubject('');
    currentVcenterSsoUserCloud = this.vcenterSsoUserCloud.asObservable();
    changeVcenterSsoUserCloud(user: string) {
        this.vcenterSsoUserCloud.next(user);
    }
    private vcenterSsoPasswordBase64Cloud = new BehaviorSubject('');
    currentVcenterSsoPasswordBase64Cloud = this.vcenterSsoPasswordBase64Cloud.asObservable();
    changeVcenterSsoPasswordBase64Cloud(pass: string) {
        this.vcenterSsoPasswordBase64Cloud.next(pass);
    }
    private vcenterDatacenterCloud = new BehaviorSubject('');
    currentVcenterDatacenterCloud = this.vcenterDatacenterCloud.asObservable();
    changeVcenterDatacenterCloud(datacenter: string) {
        this.vcenterDatacenterCloud.next(datacenter);
    }
    private vcenterContentSeLibrary = new BehaviorSubject('');
    currentVcenterContentSeLibrary = this.vcenterContentSeLibrary.asObservable();
    changeVcenterContentSeLibrary(lib: string) {
        this.vcenterContentSeLibrary.next(lib);
    }
    private vcenterDatastoreCloud = new BehaviorSubject('');
    currentVcenterDatastoreCloud = this.vcenterDatastoreCloud.asObservable();
    changeVcenterDatastoreCloud(datastore: string) {
        this.vcenterDatastoreCloud.next(datastore);
    }
    private vcenterClusterCloud = new BehaviorSubject('');
    currentVcenterClusterCloud = this.vcenterClusterCloud.asObservable();
    changeVcenterClusterCloud(datastore: string) {
        this.vcenterClusterCloud.next(datastore);
    }
    // ====================================================================================== //


    // ============================================= AVI SE TEIR 1 DETAILS ========================================================== //
    private nsxtTier1SeMgmtNetworkName = new BehaviorSubject('');
    currentNsxtTier1SeMgmtNetworkName = this.nsxtTier1SeMgmtNetworkName.asObservable();
    changeNsxtTier1SeMgmtNetworkName(name: string) {
        this.nsxtTier1SeMgmtNetworkName.next(name);
    }
    private nsxtOverlay = new BehaviorSubject('');
    currentNsxtOverlay = this.nsxtOverlay.asObservable();
    changeNsxtOverlay(overlay: string) {
        this.nsxtOverlay.next(overlay);
    }
    // ====================================================================================== //


    // ======================================== AVI SE MANAGEMENT NETWORK ============================================================ //
    private aviSeMgmtNetworkName = new BehaviorSubject('');
    currentAviSeMgmtNetworkName = this.aviSeMgmtNetworkName.asObservable();
    changeAviSeMgmtNetworkName(name: string) {
        this.aviSeMgmtNetworkName.next(name);
    }
    private aviSeMgmtNetworkGatewayCidr = new BehaviorSubject('');
    currentAviSeMgmtNetworkGatewayCidr = this.aviSeMgmtNetworkGatewayCidr.asObservable();
    changeAviSeMgmtNetworkGatewayCidr(cidr: string) {
        this.aviSeMgmtNetworkGatewayCidr.next(cidr);
    }
    private aviSeMgmtNetworkDhcpStartRange = new BehaviorSubject('');
    currentAviSeMgmtNetworkDhcpStartRange = this.aviSeMgmtNetworkDhcpStartRange.asObservable();
    changeAviSeMgmtNetworkDhcpStartRange(start: string) {
        this.aviSeMgmtNetworkDhcpStartRange.next(start);
    }
    private aviSeMgmtNetworkDhcpEndRange = new BehaviorSubject('');
    currentAviSeMgmtNetworkDhcpEndRange = this.aviSeMgmtNetworkDhcpEndRange.asObservable();
    changeAviSeMgmtNetworkDhcpEndRange(end: string) {
        this.aviSeMgmtNetworkDhcpEndRange.next(end);
    }
    // ====================================================================================== //


    // ====================================== NSXT CLOUD VCD DISPLAY NAME ================================================================= //
    private nsxtCloudVcdDisplayName = new BehaviorSubject('');
    currentNsxtCloudVcdDisplayName = this.nsxtCloudVcdDisplayName.asObservable();
    changeNsxtCloudVcdDisplayName(name: string) {
        this.nsxtCloudVcdDisplayName.next(name);
    }
    // ====================================================================================== //


    // ======================================================= TIER 0 ROUTER ============================================================== //
    private importTier0 = new BehaviorSubject<boolean>(false);
    currentImportTier0 = this.importTier0.asObservable();
    changeImportTier0(importT0: boolean) {
        this.importTier0.next(importT0);
    }

    private tier0Router = new BehaviorSubject('');
    currentTier0Router = this.tier0Router.asObservable();
    changeTier0Router(router: string) {
        this.tier0Router.next(router);
    }

    private tier0GatewayName = new BehaviorSubject('');
    currentTier0GatewayName = this.tier0GatewayName.asObservable();
    changeTier0GatewayName(gatewayName: string) {
        this.tier0GatewayName.next(gatewayName);
    }

    private extNetgatewayCIDR = new BehaviorSubject('');
    currentExtNetgatewayCIDR = this.extNetgatewayCIDR.asObservable();
    changeExtNetgatewayCIDR(cidr: string) {
        this.extNetgatewayCIDR.next(cidr);
    }

    private extNetStartIP = new BehaviorSubject('');
    currentExtNetStartIP = this.extNetStartIP.asObservable();
    changeExtNetStartIP(startIp: string) {
        this.extNetStartIP.next(startIp);
    }
    private extNetEndIP = new BehaviorSubject('');
    currentExtNetEndIP = this.extNetEndIP.asObservable();
    changeExtNetEndIP(endIp: string) {
        this.extNetEndIP.next(endIp);
    }
    // =========================================================================================================================================== //


    // ======================================== SERVICE ORG SPEC ======================================== //
    private svcOrgName = new BehaviorSubject('');
    currentSvcOrgName = this.svcOrgName.asObservable();
    changeSvcOrgName(name: string) {
        this.svcOrgName.next(name);
    }
    private svcOrgFullName = new BehaviorSubject('');
    currentSvcOrgFullName = this.svcOrgFullName.asObservable();
    changeSvcOrgFullName(name: string) {
        this.svcOrgFullName.next(name);
    }
    // =========================================================================================================================================== //


    // ======================================== SERVICE ORG VDC SPEC ======================================== //
    private svcOrgVdcName = new BehaviorSubject('');
    currentSvcOrgVdcName = this.svcOrgVdcName.asObservable();
    changeSvcOrgVdcName(name: string) {
        this.svcOrgVdcName.next(name);
    }
    // =========================================================================================================================================== //


    // ======================================== SERVICE ORG VDC RESOURCE SPEC ======================================== //
    private providerVDC = new BehaviorSubject('');
    currentProviderVDC = this.providerVDC.asObservable();
    changeProviderVDC(pvdc: string) {
        this.providerVDC.next(pvdc);
    }
    private cpuAllocation = new BehaviorSubject('');
    currentCpuAllocation = this.cpuAllocation.asObservable();
    changeCpuAllocation(cpu: string) {
        this.cpuAllocation.next(cpu);
    }
    private cpuGuaranteed = new BehaviorSubject('20');
    currentCpuGuaranteed = this.cpuGuaranteed.asObservable();
    changeCpuGuaranteed (cpu: string) {
        this.cpuGuaranteed.next(cpu);
    }
    private memoryAllocation = new BehaviorSubject('');
    currentMemoryAllocation = this.memoryAllocation.asObservable();
    changeMemoryAllocation(mem: string) {
        this.memoryAllocation.next(mem);
    }
    private memoryGuaranteed = new BehaviorSubject('20');
    currentMemoryGuaranteed = this.memoryGuaranteed.asObservable();
    changeMemoryGuaranteed(mem: string) {
        this.memoryGuaranteed.next(mem);
    }
    private vcpuSpeed = new BehaviorSubject('1');
    currentVcpuSpeed = this.vcpuSpeed.asObservable();
    changeVcpuSpeed(speed: string){
        this.vcpuSpeed.next(speed);
    }
    private isElastic = new BehaviorSubject<boolean>(false);
    currentIsElastic = this.isElastic.asObservable();
    changeIsElastic(elastic: boolean) {
        this.isElastic.next(elastic);
    }
    private includeMemoryOverhead = new BehaviorSubject<boolean>(false);
    currentIncludeMemoryOverhead = this.includeMemoryOverhead.asObservable();
    changeIncludeMemoryOverhead(includeMemOver: boolean) {
        this.includeMemoryOverhead.next(includeMemOver);
    }
    private vmQuota = new BehaviorSubject('100');
    currentVmQuota = this.vmQuota.asObservable();
    changeVmQuota(vm: string) {
        this.vmQuota.next(vm);
    }
    private storageSpec = new BehaviorSubject(new Map<string, string>());
    currentStorageSpec = this.storageSpec.asObservable();
    changeStorageSpec(spec) {
        this.storageSpec.next(spec);
    }
    private defaultStoragePolicy = new BehaviorSubject('');
    currentDefaultStoragePolicy = this.defaultStoragePolicy.asObservable();
    changeDefaultStoragePolicy(defaultPolicy: string) {
        this.defaultStoragePolicy.next(defaultPolicy);
    }
    private thinProvisioning = new BehaviorSubject<boolean>(false);
    currentThinProvisioning = this.thinProvisioning.asObservable();
    changeThinProvisioning(thin: boolean) {
        this.thinProvisioning.next(thin);
    }
    private fastProvisioning = new BehaviorSubject<boolean>(false);
    currentFastProvisioning = this.fastProvisioning.asObservable();
    changeFastProvisioning(fast: boolean) {
        this.fastProvisioning.next(fast);
    }
    private networkPoolName = new BehaviorSubject('');
    currentNetworkPoolName = this.networkPoolName.asObservable();
    changeNetworkPoolName(name: string){
        this.networkPoolName.next(name);
    }
    private networkQuota = new BehaviorSubject('100');
    currentNetworkQuota = this.networkQuota.asObservable();
    changeNetworkQuota(quota: string){
        this.networkQuota.next(quota);
    }
    // =========================================================================================================================================== //


    // ======================================== SERVICE ORG VDC SERVICE ENGINE GROUP ======================================== //
    private importSEG = new BehaviorSubject<boolean>(false);
    currentImportSEG = this.importSEG.asObservable();
    changeImportSEG(importSeg: boolean) {
        this.importSEG.next(importSeg);
    }
    private serviceEngineGroupname = new BehaviorSubject('');
    currentServiceEngineGroupname = this.serviceEngineGroupname.asObservable();
    changeServiceEngineGroupname(name: string) {
        this.serviceEngineGroupname.next(name);
    }
    private serviceEngineGroupVcdDisplayName = new BehaviorSubject('');
    currentServiceEngineGroupVcdDisplayName = this.serviceEngineGroupVcdDisplayName.asObservable();
    changeServiceEngineGroupVcdDisplayName(name: string) {
        this.serviceEngineGroupVcdDisplayName.next(name);
    }
    private reservationType = new BehaviorSubject('');
    currentReservationType = this.reservationType.asObservable();
    changeReservationType(reserType: string) {
        this.reservationType.next(reserType);
    }
    // =========================================================================================================================================== //


    // ======================================== SERVICE ORG VDC TIER 1 GATEWAY SPEC ======================================== //
    private tier1Gatewayname = new BehaviorSubject('');
    currentTier1Gatewayname = this.tier1Gatewayname.asObservable();
    changeTier1Gatewayname(name: string) {
        this.tier1Gatewayname.next(name);
    }
    private isDedicated = new BehaviorSubject<boolean>(false);
    currentIsDedicated = this.isDedicated.asObservable();
    changeIsDedicated(dedicated: boolean) {
        this.isDedicated.next(dedicated);
    }
    private primaryIp = new BehaviorSubject('');
    currentPrimaryIp = this.primaryIp.asObservable();
    changePrimaryIp(ip: string) {
        this.primaryIp.next(ip);
    }
    private IpAllocationStartIP = new BehaviorSubject('');
    currentIpAllocationStartIP = this.IpAllocationStartIP.asObservable();
    changeIpAllocationStartIP(startIp: string) {
        this.IpAllocationStartIP.next(startIp);
    }
    private IpAllocationEndIP = new BehaviorSubject('');
    currentIpAllocationEndIP = this.IpAllocationEndIP.asObservable();
    changeIpAllocationEndIP(endIp: string) {
        this.IpAllocationEndIP.next(endIp);
    }
    // =========================================================================================================================================== //


    // ======================================== SERVICE ORG VDC NETWORK SPEC ======================================== //
    private networkName = new BehaviorSubject('');
    currentNetworkName = this.networkName.asObservable();
    changeNetworkName (name: string) {
        this.networkName.next(name);
    }
    private gatewayCIDR = new BehaviorSubject('');
    currentGatewayCIDR = this.gatewayCIDR.asObservable();
    changeGatewayCIDR (cidr: string) {
        this.gatewayCIDR.next(cidr);
    }
    private staticIpPoolstartAddress = new BehaviorSubject('');
    currentStaticIpPoolstartAddress = this.staticIpPoolstartAddress.asObservable();
    changeStaticIpPoolstartAddress(startIp: string) {
        this.staticIpPoolstartAddress.next(startIp);
    }
    private staticIpPoolendAddress = new BehaviorSubject('');
    currentStaticIpPoolendAddress = this.staticIpPoolendAddress.asObservable();
    changeStaticIpPoolendAddress(endIp: string) {
        this.staticIpPoolendAddress.next(endIp);
    }
    private primaryDNS = new BehaviorSubject('');
    currentPrimaryDNS = this.primaryDNS.asObservable();
    changePrimaryDNS(primary: string) {
        this.primaryDNS.next(primary);
    }
    private secondaryDNS = new BehaviorSubject('');
    currentSecondaryDNS = this.secondaryDNS.asObservable();
    changeSecondaryDNS(secondary: string) {
        this.secondaryDNS.next(secondary);
    }
    private dnsSuffix = new BehaviorSubject('');
    currentDnsSuffix = this.dnsSuffix.asObservable();
    changeDnsSuffix(suffix: string){
        this.dnsSuffix.next(suffix);
    }
    // =========================================================================================================================================== //


    // ======================================== CATALOG SPEC ======================================== //
    private cseOvaCatalogName = new BehaviorSubject('');
    currentCseOvaCatalogName = this.cseOvaCatalogName.asObservable();
    changeCseOvaCatalogName(cse: string) {
        this.cseOvaCatalogName.next(cse);
    }
    private k8sTemplatCatalogName = new BehaviorSubject('');
    currentK8sTemplatCatalogName = this.k8sTemplatCatalogName.asObservable();
    changeK8sTemplatCatalogName(k8s: string) {
        this.k8sTemplatCatalogName.next(k8s);
    }
    // =========================================================================================================================================== //

    private vAppName = new BehaviorSubject('');
    currentVappName = this.vAppName.asObservable();
    changeVappName(vapp: string) {
        this.vAppName.next(vapp);
    }

    private cseSvcAccountName = new BehaviorSubject('');
    currentCseSvcAccountName = this.cseSvcAccountName.asObservable();
    changeCseSvcAccountName(acc: string) {
        this.cseSvcAccountName.next(acc);
    }

    private cseSvcAccountPasswordBase64 = new BehaviorSubject('');
    currentCseSvcAccountPasswordBase64 = this.cseSvcAccountPasswordBase64.asObservable();
    changeCseSvcAccountPasswordBase64(password: string) {
        this.cseSvcAccountPasswordBase64.next(password);
    }
    constructor() {
    }
}
