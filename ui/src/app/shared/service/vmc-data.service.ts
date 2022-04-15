/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable()
export  class VMCDataService {
    private useInputFile = new BehaviorSubject<boolean>(false);
    // Dumy Component Form Control
    private dnsServer = new BehaviorSubject('');
    private ntpServer = new BehaviorSubject('');
    private searchDomain = new BehaviorSubject('');
    // Iaas Provider
    private sddcToken = new BehaviorSubject('');
    private tmcToken = new BehaviorSubject('');
    private orgName = new BehaviorSubject('');
    private sddcName = new BehaviorSubject('');
    private datastore = new BehaviorSubject('');
    private cluster = new BehaviorSubject('');
    private datacenter = new BehaviorSubject('');
    private resourcePool = new BehaviorSubject('');
    private contentLib = new BehaviorSubject('');
    private ovaImage = new BehaviorSubject('');
    private customerConnect = new BehaviorSubject<boolean>(false);
    private custUsername = new BehaviorSubject('');
    private custPassword = new BehaviorSubject('');
    private jwtToken = new BehaviorSubject('');
    private kubernetesOva = new BehaviorSubject('');
    private isMarketplace = new BehaviorSubject<boolean>(false);
    private marketplaceRefreshToken = new BehaviorSubject('');
    // TMC
    private enableTMC = new BehaviorSubject<boolean>(false);
    private apiToken = new BehaviorSubject('');
    private enableTO = new BehaviorSubject<boolean>(false);
    private toURL = new BehaviorSubject('');
    private toApiToken = new BehaviorSubject('');
    // AVI Components
    private aviPassword = new BehaviorSubject('');
    private aviBackupPassword = new BehaviorSubject('');
    private aviSize = new BehaviorSubject('');
    // AVI HA Fields
    private enableHAAvi = new BehaviorSubject<boolean>(false);
    private clusterIp = new BehaviorSubject('');
    private clusterFqdn = new BehaviorSubject('');
    // Optional License and Cert
    private aviLicenseKey = new BehaviorSubject('');
    private aviCertPath = new BehaviorSubject('');
    private aviCertKeyPath = new BehaviorSubject('');
    // AVI Management Segment
    private aviGateway = new BehaviorSubject('');
    private aviDhcpStart = new BehaviorSubject('');
    private aviDhcpEnd = new BehaviorSubject('');
    // AVI Cluster VIP Network Details
    private aviClusterVipGatewayIp = new BehaviorSubject('');
    private aviClusterVipNetworkName = new BehaviorSubject('');
    private aviClusterVipStartIp = new BehaviorSubject('');
    private aviClusterVipEndIp = new BehaviorSubject('');
    private aviClusterVipSeStartIp = new BehaviorSubject('');
    private aviClusterVipSeEndIp = new BehaviorSubject('');
    // TKG Mgmt Data
    private tkgMgmtDataGateway = new BehaviorSubject('');
    private tkgMgmtDataDhcpStart = new BehaviorSubject('');
    private tkgMgmtDataDhcpEnd = new BehaviorSubject('');
    private tkgMgmtDataServiceStart = new BehaviorSubject('');
    private tkgMgmtDataServiceEnd = new BehaviorSubject('');
    // Mgmt Cluster
    private mgmtDeploymentType = new BehaviorSubject('');
    private mgmtDeploymentSize = new BehaviorSubject('');
    private mgmtSegment = new BehaviorSubject('');
    private mgmtGateway = new BehaviorSubject('');
    private mgmtClusterName = new BehaviorSubject('');
    private mgmtClusterCidr = new BehaviorSubject('100.96.0.0/11');
    private mgmtServiceCidr = new BehaviorSubject('100.64.0.0/13');
    private mgmtBaseImage = new BehaviorSubject('');
    private mgmtCpu = new BehaviorSubject('');
    private mgmtMemory = new BehaviorSubject('');
    private mgmtStorage = new BehaviorSubject('');
    // Shared Cluster
    private sharedDeploymentType = new BehaviorSubject('');
    private sharedDeploymentSize = new BehaviorSubject('');
    private sharedWorkerNodeCount = new BehaviorSubject('');
    private sharedClusterName = new BehaviorSubject('');
    private sharedGateway = new BehaviorSubject('');
    private sharedDhcpStart = new BehaviorSubject('');
    private sharedDhcpEnd = new BehaviorSubject('');
    private sharedClusterCidr = new BehaviorSubject('100.96.0.0/11');
    private sharedServiceCidr = new BehaviorSubject('100.64.0.0/13');
    private sharedBaseImage = new BehaviorSubject('');
    private sharedBaseImageVersion = new BehaviorSubject('');
    private sharedCpu = new BehaviorSubject('');
    private sharedMemory = new BehaviorSubject('');
    private sharedStorage = new BehaviorSubject('');
    private enableHarbor = new BehaviorSubject<boolean>(false);
    private harborFqdn = new BehaviorSubject('');
    private harborPassword = new BehaviorSubject('');
    private harborCertPath = new BehaviorSubject('');
    private harborCertKey = new BehaviorSubject('');
    // TKG Workload Data
    private tkgWrkDataGateway = new BehaviorSubject('');
    private tkgWrkDataDhcpStart = new BehaviorSubject('');
    private tkgWrkDataDhcpEnd = new BehaviorSubject('');
    private tkgWrkDataServiceStart = new BehaviorSubject('');
    private tkgWrkDataServiceEnd = new BehaviorSubject('');
    // Workload Cluster
    private wrkDeploymentType = new BehaviorSubject('');
    private wrkDeploymentSize = new BehaviorSubject('');
    private wrkClusterName = new BehaviorSubject('');
    private wrkWorkerNodeCount = new BehaviorSubject('');
    private wrkGateway = new BehaviorSubject('');
    private wrkDhcpStart = new BehaviorSubject('');
    private wrkDhcpEnd = new BehaviorSubject('');
    private wrkClusterCidr = new BehaviorSubject('100.96.0.0/11');
    private wrkServiceCidr = new BehaviorSubject('100.64.0.0/13');
    private wrkBaseImage = new BehaviorSubject('');
    private wrkBaseImageVersion = new BehaviorSubject('');
    private enableTSM = new BehaviorSubject<boolean>(false);
    private exactNamespaceExclusion = new BehaviorSubject('');
    private startsWithNamespaceExclusion = new BehaviorSubject('');
    private wrkCpu = new BehaviorSubject('');
    private wrkMemory = new BehaviorSubject('');
    private wrkStorage = new BehaviorSubject('');
    // Extension
    private enableTanzuExtension = new BehaviorSubject<boolean>(false);
    private tkgClusters = new BehaviorSubject('');
    private enableLoggingExtension = new BehaviorSubject<boolean>(false);
    private enableMonitoringExtension = new BehaviorSubject<boolean>(false);
    private loggingEndpoint = new BehaviorSubject('');
    private syslogAddress = new BehaviorSubject('');
    private syslogPort = new BehaviorSubject('');
    private syslogMode = new BehaviorSubject('');
    private syslogFormat = new BehaviorSubject('');
    private httpAddress = new BehaviorSubject('');
    private httpPort = new BehaviorSubject('');
    private httpUri = new BehaviorSubject('');
    private httpHeaderKey = new BehaviorSubject('');
    private elasticSearchAddress = new BehaviorSubject('');
    private elasticSearchPort = new BehaviorSubject('');
    private kafkaServiceName = new BehaviorSubject('');
    private kafkaTopicName = new BehaviorSubject('');
    private splunkAddress = new BehaviorSubject('');
    private splunkPort = new BehaviorSubject('');
    private splunkToken = new BehaviorSubject('');
    private prometheusFqdn = new BehaviorSubject('');
    private prometheusCertPath = new BehaviorSubject('');
    private prometheusCertKeyPath = new BehaviorSubject('');
    private grafanaFqdn = new BehaviorSubject('');
    private grafanaPassword = new BehaviorSubject('');
    private grafanaCertPath = new BehaviorSubject('');
    private grafanaCertKeyPath = new BehaviorSubject('');

    currentInputFileStatus = this.useInputFile.asObservable();
    // Dumy Component Form Control Current Values
    currentDnsValue = this.dnsServer.asObservable();
    currentNtpValue = this.ntpServer.asObservable();
    currentSearchDomainValue = this.searchDomain.asObservable();
    // Iaas Provider
    currentSddcToken = this.sddcToken.asObservable();
    currentTmcToken = this.tmcToken.asObservable();
    currentOrgName = this.orgName.asObservable();
    currentSddcName = this.sddcName.asObservable();
    currentDatastore = this.datastore.asObservable();
    currentCluster = this.cluster.asObservable();
    currentDatacenter = this.datacenter.asObservable();
    currentResourcePool = this.resourcePool.asObservable();
    currentContentLib = this.contentLib.asObservable();
    currentOvaImage = this.ovaImage.asObservable();
    currentCustomerConnect = this.customerConnect.asObservable();
    currentCustUsername = this.custUsername.asObservable();
    currentCustPassword = this.custPassword.asObservable();
    currentJwtToken = this.jwtToken.asObservable();
    currentKubernetesOva = this.kubernetesOva.asObservable();
    currentMarketplace = this.isMarketplace.asObservable();
    currentMarketplaceRefreshToken = this.marketplaceRefreshToken.asObservable();
    // TMC
    currentEnableTMC = this.enableTMC.asObservable();
    currentApiToken = this.apiToken.asObservable();
    currentEnableTO = this.enableTO.asObservable();
    currentTOUrl = this.toURL.asObservable();
    currentTOApiToken = this.toApiToken.asObservable();
    // AVI Components
    currentAviHA = this.enableHAAvi.asObservable();
    currentAviPassword = this.aviPassword.asObservable();
    currentAviBackupPassword = this.aviBackupPassword.asObservable();
    currentAviClusterIp = this.clusterIp.asObservable();
    currentAviClusterFqdn = this.clusterFqdn.asObservable();
    currentAviSize = this.aviSize.asObservable();
    // AVI License and Cert
    currentAviLicense = this.aviLicenseKey.asObservable();
    currentAviCertPath = this.aviCertPath.asObservable();
    currentAviCertKeyPath = this.aviCertKeyPath.asObservable();
    // AVI Management Network
    currentAviGateway = this.aviGateway.asObservable();
    currentAviDhcpStart = this.aviDhcpStart.asObservable();
    currentAviDhcpEnd = this.aviDhcpEnd.asObservable();
    currentAviClusterVipGatewayIp = this.aviClusterVipGatewayIp.asObservable();
    currentAviClusterVipNetworkName = this.aviClusterVipNetworkName.asObservable();
    currentAviClusterVipStartIp = this.aviClusterVipStartIp.asObservable();
    currentAviClusterVipEndIp = this.aviClusterVipEndIp.asObservable();
    currentAviClusterVipSeStartIp = this.aviClusterVipSeStartIp.asObservable();
    currentAviClusterVipSeEndIp = this.aviClusterVipSeEndIp.asObservable();
    // TKG Mgmt Data
    currentTkgMgmtDataGateway = this.tkgMgmtDataGateway.asObservable();
    currentTkgMgmtDataDhcpStart = this.tkgMgmtDataDhcpStart.asObservable();
    currentTkgMgmtDataDhcpEnd = this.tkgMgmtDataDhcpEnd.asObservable();
    currentTkgMgmtDataServiceStart = this.tkgMgmtDataServiceStart.asObservable();
    currentTkgMgmtDataServiceEnd = this.tkgMgmtDataServiceEnd.asObservable();
    // Mgmt Cluster
    currentMgmtDeploymentType = this.mgmtDeploymentType.asObservable();
    currentMgmtDeploymentSize = this.mgmtDeploymentSize.asObservable();
    currentMgmtSegment = this.mgmtSegment.asObservable();
    currentMgmtClusterName = this.mgmtClusterName.asObservable();
    currentMgmtGateway = this.mgmtGateway.asObservable();
    currentMgmtClusterCidr = this.mgmtClusterCidr.asObservable();
    currentMgmtServiceCidr = this.mgmtServiceCidr.asObservable();
    currentMgmtBaseImage = this.mgmtBaseImage.asObservable();
    currentMgmtCpu = this.mgmtCpu.asObservable();
    currentMgmtMemory = this.mgmtMemory.asObservable();
    currentMgmtStorage = this.mgmtStorage.asObservable();
    // Shared Cluster
    currentSharedDeploymentType = this.sharedDeploymentType.asObservable();
    currentSharedDeploymentSize = this.sharedDeploymentSize.asObservable();
    currentSharedClusterName = this.sharedClusterName.asObservable();
    currentSharedWorkerNodeCount = this.sharedWorkerNodeCount.asObservable();
    currentSharedGateway = this.sharedGateway.asObservable();
    currentSharedDhcpStart = this.sharedDhcpStart.asObservable();
    currentSharedDhcpEnd = this.sharedDhcpEnd.asObservable();
    currentSharedClusterCidr = this.sharedClusterCidr.asObservable();
    currentSharedServiceCidr = this.sharedServiceCidr.asObservable();
    currentSharedBaseImage = this.sharedBaseImage.asObservable();
    currentSharedBaseImageVersion = this.sharedBaseImageVersion.asObservable();
    currentSharedCpu = this.sharedCpu.asObservable();
    currentSharedMemory = this.sharedMemory.asObservable();
    currentSharedStorage = this.sharedStorage.asObservable();
    currentEnableHarbor = this.enableHarbor.asObservable();
    currentHarborFqdn = this.harborFqdn.asObservable();
    currentHarborPassword = this.harborPassword.asObservable();
    currentHarborCertPath = this.harborCertPath.asObservable();
    currentHarborCertKey = this.harborCertKey.asObservable();
    // TKG Workload Data
    currentTkgWrkDataGateway = this.tkgWrkDataGateway.asObservable();
    currentTkgWrkDataDhcpStart = this.tkgWrkDataDhcpStart.asObservable();
    currentTkgWrkDataDhcpEnd = this.tkgWrkDataDhcpEnd.asObservable();
    currentTkgWrkDataServiceStart = this.tkgWrkDataServiceStart.asObservable();
    currentTkgWrkDataServiceEnd = this.tkgWrkDataServiceEnd.asObservable();
    // Workload Cluster
    currentWrkDeploymentType = this.wrkDeploymentType.asObservable();
    currentWrkDeploymentSize = this.wrkDeploymentSize.asObservable();
    currentWrkClusterName = this.wrkClusterName.asObservable();
    currentWrkWorkerNodeCount = this.wrkWorkerNodeCount.asObservable();
    currentWrkGateway = this.wrkGateway.asObservable();
    currentWrkDhcpStart = this.wrkDhcpStart.asObservable();
    currentWrkDhcpEnd = this.wrkDhcpEnd.asObservable();
    currentWrkClusterCidr = this.wrkClusterCidr.asObservable();
    currentWrkServiceCidr = this.wrkServiceCidr.asObservable();
    currentWrkBaseImage = this.wrkBaseImage.asObservable();
    currentWrkBaseImageVersion = this.wrkBaseImageVersion.asObservable();
    currentWrkCpu = this.wrkCpu.asObservable();
    currentWrkMemory = this.wrkMemory.asObservable();
    currentWrkStorage = this.wrkStorage.asObservable();
    currentEnableTSM = this.enableTSM.asObservable();
    currentExactNamespaceExclusion = this.exactNamespaceExclusion.asObservable();
    currentStartsWithNamespaceExclusion = this.startsWithNamespaceExclusion.asObservable();
    // Extension
    currentEnableTanzuExtension = this.enableTanzuExtension.asObservable();
    currentTkgClusters = this.tkgClusters.asObservable();
    currentEnableLoggingExtension = this.enableLoggingExtension.asObservable();
    currentEnableMonitoringExtension = this.enableMonitoringExtension.asObservable();
    currentLoggingEndpoint = this.loggingEndpoint.asObservable();
    currentSyslogAddress = this.syslogAddress.asObservable();
    currentSyslogPort = this.syslogPort.asObservable();
    currentSyslogMode = this.syslogMode.asObservable();
    currentSyslogFormat = this.syslogFormat.asObservable();
    currentHttpAddress = this.httpAddress.asObservable();
    currentHttpPort = this.httpPort.asObservable();
    currentHttpUri = this.httpUri.asObservable();
    currentHttpHeaderKey = this.httpHeaderKey.asObservable();
    currentElasticSearchAddress = this.elasticSearchAddress.asObservable();
    currentElasticSearchPort = this.elasticSearchPort.asObservable();
    currentKafkaServiceName = this.kafkaServiceName.asObservable();
    currentKafkaTopicName = this.kafkaTopicName.asObservable();
    currentSplunkAddress = this.splunkAddress.asObservable();
    currentSplunkPort = this.splunkPort.asObservable();
    currentSplunkToken = this.splunkToken.asObservable();
    currentPrometheusFqdn = this.prometheusFqdn.asObservable();
    currentPrometheusCertPath = this.prometheusCertPath.asObservable();
    currentPrometheusCertkeyPath = this.prometheusCertKeyPath.asObservable();
    currentGrafanaFqdn = this.grafanaFqdn.asObservable();
    currentGrafanaPassword = this.grafanaPassword.asObservable();
    currentGrafanaCertPath = this.grafanaCertPath.asObservable();
    currentGrafanaCertKeyPath = this.grafanaCertKeyPath.asObservable();

    constructor() {
    }
    // Infra Settings
    changeDnsServer(dnsServer:string) {
        this.dnsServer.next(dnsServer);
    }
    changeNtpServer(ntpServer:string) {
        this.ntpServer.next(ntpServer);
    }
    changeSearchDomain(searchDomain: string) {
        this.searchDomain.next(searchDomain);
    }
    // Upload Status
    changeInputFileStatus(useInputFile:boolean) {
        this.useInputFile.next(useInputFile);
    }
    // IaaS Provider
    changeSddcToken(vcAddress:string) {
        this.sddcToken.next(vcAddress);
    }
    changeTmcToken(vcUser:string) {
        this.tmcToken.next(vcUser);
    }
    changeOrgName(orgName: string) {
        this.orgName.next(orgName);
    }
    changeSddcName(sddcName: string) {
        this.sddcName.next(sddcName);
    }
    changeDatastore(datastore:string) {
        this.datastore.next(datastore);
    }
    changeCluster(cluster:string) {
        this.cluster.next(cluster);
    }
    changeDatacenter(datacenter: string) {
        this.datacenter.next(datacenter);
    }
    changeResourcePool(resourcePool: string) {
        this.resourcePool.next(resourcePool);
    }
    changeContentLib(contentLib: string) {
        this.contentLib.next(contentLib);
    }
    changeOvaImage(ovaImage: string) {
        this.ovaImage.next(ovaImage);
    }
    changeIsCustomerConnect(customerConnect: boolean) {
        this.customerConnect.next(customerConnect);
    }
    changeCustUsername(custUsername: string) {
        this.custUsername.next(custUsername);
    }
    changeCustPassword(custPassword: string) {
        this.custPassword.next(custPassword);
    }
    changeJwtToken(jwtToken: string) {
        this.jwtToken.next(jwtToken);
    }
    changeKubernetesOva(kubernetesOva: string) {
        this.kubernetesOva.next(kubernetesOva);
    }
    changeIsMarketplace(isMarketplace: boolean) {
        this.isMarketplace.next(isMarketplace);
    }
    changeMarketplaceRefreshToken(marketplaceRefreshToken: string) {
        this.marketplaceRefreshToken.next(marketplaceRefreshToken);
    }
    // TMC Parameter
    changeEnableTMC(enableTMC: boolean) {
        this.enableTMC.next(enableTMC);
    }
    changeApiToken(apiToken: string) {
        this.apiToken.next(apiToken);
    }
    changeEnableTO(enableTO: boolean) {
        this.enableTO.next(enableTO);
    }
    changeTOUrl(toURL: string) {
        this.toURL.next(toURL);
    }
    changeTOApiToken(toApiToken: string) {
        this.toApiToken.next(toApiToken);
    }
    // AVI Component
    changeAviPassword(aviPassword: string) {
        this.aviPassword .next(aviPassword);
    }
    changeAviBackupPassword(aviBackupPassword: string) {
        this.aviBackupPassword.next(aviBackupPassword);
    }
    changeAviClusterIp(clusterIp: string) {
        this.clusterIp.next(clusterIp);
    }
    changeAviClusterFqdn(clusterFqdn: string) {
        this.clusterFqdn.next(clusterFqdn);
    }
    changeEnableAviHA(enableHa: boolean) {
        this.enableHAAvi.next(enableHa);
    }
    changeAviSize(size: string){
        this.aviSize.next(size);
    }
    changeAviCertPath(certPath: string) {
        this.aviCertPath.next(certPath);
    }
    changeAviCertKeyPath(certKeyPath: string) {
        this.aviCertKeyPath.next(certKeyPath);
    }
    changeAviLicenseKey(license: string) {
        this.aviLicenseKey.next(license);
    }
    changeAviGateway(aviGateway: string) {
        this.aviGateway.next(aviGateway);
    }
    changeAviDhcpStart(aviDhcpStart: string) {
        this.aviDhcpStart.next(aviDhcpStart);
    }
    changeAviDhcpEnd(aviDhcpEnd: string) {
        this.aviDhcpEnd.next(aviDhcpEnd);
    }
    changeAviClusterVipGatewayIp(aviClusterVipGatewayIp: string) {
        this.aviClusterVipGatewayIp.next(aviClusterVipGatewayIp);
    }
    changeAviClusterVipNetworkName(aviClusterVipNetworkName: string) {
        this.aviClusterVipNetworkName.next(aviClusterVipNetworkName);
    }
    changeAviClusterVipStartIp(aviClusterVipStartIp: string) {
        this.aviClusterVipStartIp.next(aviClusterVipStartIp);
    }
    changeAviClusterVipEndIp(aviClusterVipEndIp: string) {
        this.aviClusterVipEndIp.next(aviClusterVipEndIp);
     }
    changeAviClusterVipSeStartIp(aviClusterVipSeStartIp: string) {
        this.aviClusterVipSeStartIp.next(aviClusterVipSeStartIp);
    }
    changeAviClusterVipSeEndIp(aviClusterVipSeEndIp: string) {
        this.aviClusterVipSeEndIp.next(aviClusterVipSeEndIp);
    }
    // TKG Mgmt Data
    changeTkgMgmtDataGateway(tkgMgmtDataGateway: string) {
        this.tkgMgmtDataGateway.next(tkgMgmtDataGateway);
    }
    changeTkgMgmtDataDhcpStart(tkgMgmtDataDhcpStart: string) {
        this.tkgMgmtDataDhcpStart.next(tkgMgmtDataDhcpStart);
    }
    changeTkgMgmtDataDhcpEnd(tkgMgmtDataDhcpEnd: string) {
        this.tkgMgmtDataDhcpEnd.next(tkgMgmtDataDhcpEnd);
    }
    changeTkgMgmtDataServiceStart(tkgMgmtDataServiceStart: string) {
        this.tkgMgmtDataServiceStart.next(tkgMgmtDataServiceStart);
    }
    changeTkgMgmtDataServiceEnd(tkgMgmtDataServiceEnd: string) {
        this.tkgMgmtDataServiceEnd.next(tkgMgmtDataServiceEnd);
    }
    // Mgmt Cluster
    changeMgmtDeploymentType(mgmtDeploymentType: string) {
        this.mgmtDeploymentType.next(mgmtDeploymentType);
    }
    changeMgmtDeploymentSize(mgmtDeploymentSize: string) {
        this.mgmtDeploymentSize.next(mgmtDeploymentSize);
    }
    changeMgmtSegment(mgmtSegment: string) {
        this.mgmtSegment.next(mgmtSegment);
    }
    changeMgmtGateway(mgmtGateway: string) {
        this.mgmtGateway.next(mgmtGateway);
    }
    changeMgmtClusterName(mgmtClusterName: string) {
        this.mgmtClusterName.next(mgmtClusterName);
    }
    changeMgmtClusterCidr(mgmtClusterCidr: string) {
        this.mgmtClusterCidr.next(mgmtClusterCidr);
    }
    changeMgmtServiceCidr(mgmtServiceCidr: string) {
        this.mgmtServiceCidr.next(mgmtServiceCidr);
    }
    changeMgmtBaseImage(mgmtBaseImage: string) {
        this.mgmtBaseImage.next(mgmtBaseImage);
    }
    changeMgmtCpu(mgmtCpu: string){
        this.mgmtCpu.next(mgmtCpu);
    }
    changeMgmtMemory(mgmtMemory: string){
        this.mgmtMemory.next(mgmtMemory);
    }
    changeMgmtStorage(mgmtStorage: string){
        this.mgmtStorage.next(mgmtStorage);
    }
    // Shared Cluster
    changeSharedDeploymentType(sharedDeploymentType: string) {
        this.sharedDeploymentType.next(sharedDeploymentType);
    }
    changeSharedDeploymentSize(sharedDeploymentSize: string) {
        this.sharedDeploymentSize.next(sharedDeploymentSize);
    }
    changeSharedClusterName(sharedClusterName: string) {
        this.sharedClusterName.next(sharedClusterName);
    }
    changeSharedWorkerNodeCount(sharedWorkerNodeCount: string) {
        this.sharedWorkerNodeCount.next(sharedWorkerNodeCount);
    }
    changeSharedGateway(sharedGateway: string) {
        this.sharedGateway.next(sharedGateway);
    }
    changeSharedDhcpStart(sharedDhcpStart: string) {
        this.sharedDhcpStart.next(sharedDhcpStart);
    }
    changeSharedDhcpEnd(sharedDhcpEnd: string) {
        this.sharedDhcpEnd.next(sharedDhcpEnd);
    }
    changeSharedClusterCidr(sharedClusterCidr: string) {
        this.sharedClusterCidr.next(sharedClusterCidr);
    }
    changeSharedServiceCidr(sharedServiceCidr: string) {
        this.sharedServiceCidr.next(sharedServiceCidr);
    }
    changeSharedBaseImage(sharedBaseImage: string) {
        this.sharedBaseImage.next(sharedBaseImage);
    }
    changeSharedBaseImageVersion(sharedBaseImageVersion: string) {
        this.sharedBaseImageVersion.next(sharedBaseImageVersion);
    }
    changeSharedCpu(sharedCpu: string){
        this.sharedCpu.next(sharedCpu);
    }
    changeSharedMemory(sharedMemory: string){
        this.sharedMemory.next(sharedMemory);
    }
    changeSharedStorage(sharedStorage: string){
        this.sharedStorage.next(sharedStorage);
    }
    changeEnableHarbor(enableHarbor: boolean ) {
        this.enableHarbor.next(enableHarbor);
    }
    changeHarborFqdn(harborFqdn: string) {
        this.harborFqdn.next(harborFqdn);
    }
    changeHarborPassword(harborPassword: string) {
        this.harborPassword.next(harborPassword);
    }
    changeHarborCertPath(harborCertPath: string) {
        this.harborCertPath.next(harborCertPath);
    }
    changeHarborCertKey(harborCertKey: string) {
        this.harborCertKey.next(harborCertKey);
    }
    // TKG Workload Data
    changeTkgWrkDataGateway(tkgWrkDataGateway: string) {
        this.tkgWrkDataGateway.next(tkgWrkDataGateway);
    }
    changeTkgWrkDataDhcpStart(tkgWrkDataDhcpStart: string) {
        this.tkgWrkDataDhcpStart.next(tkgWrkDataDhcpStart);
    }
    changeTkgWrkDataDhcpEnd(tkgWrkDataDhcpEnd: string) {
        this.tkgWrkDataDhcpEnd.next(tkgWrkDataDhcpEnd);
    }
    changeTkgWrkDataServiceStart(tkgWrkDataServiceStart: string) {
        this.tkgWrkDataServiceStart.next(tkgWrkDataServiceStart);
    }
    changeTkgWrkDataServiceEnd(tkgWrkDataServiceEnd: string) {
        this.tkgWrkDataServiceEnd.next(tkgWrkDataServiceEnd);
    }
    // Workload Cluster
    changeWrkDeploymentType(wrkDeploymentType: string) {
        this.wrkDeploymentType.next(wrkDeploymentType);
    }
    changeWrkDeploymentSize(wrkDeploymentSize: string) {
        this.wrkDeploymentSize.next(wrkDeploymentSize);
    }
    changeWrkWorkerNodeCount(wrkWorkerNodeCount: string) {
        this.wrkWorkerNodeCount.next(wrkWorkerNodeCount);
    }
    changeWrkClusterName(wrkClusterName: string) {
        this.wrkClusterName.next(wrkClusterName);
    }
    changeWrkGateway(wrkGateway: string) {
        this.wrkGateway.next(wrkGateway);
    }
    changeWrkDhcpStart(wrkDhcpStart: string) {
        this.wrkDhcpStart.next(wrkDhcpStart);
    }
    changeWrkDhcpEnd(wrkDhcpEnd: string) {
        this.wrkDhcpEnd.next(wrkDhcpEnd);
    }
    changeWrkClusterCidr(wrkClusterCidr: string) {
        this.wrkClusterCidr.next(wrkClusterCidr);
    }
    changeWrkServiceCidr(wrkServiceCidr: string) {
        this.wrkServiceCidr.next(wrkServiceCidr);
    }
    changeWrkBaseImage(wrkBaseImage: string) {
        this.wrkBaseImage.next(wrkBaseImage);
    }
    changeWrkBaseImageVersion(wrkBaseImageVersion: string) {
        this.wrkBaseImageVersion.next(wrkBaseImageVersion);
    }
    changeWrkCpu(wrkCpu: string){
        this.wrkCpu.next(wrkCpu);
    }
    changeWrkMemory(wrkMemory: string){
        this.wrkMemory.next(wrkMemory);
    }
    changeWrkStorage(wrkStorage: string){
        this.wrkStorage.next(wrkStorage);
    }
    changeEnableTSM(enableTSM: boolean) {
        this.enableTSM.next(enableTSM);
    }
    changeTsmExactNamespaceExclusion(exactNamespaceExclusion: string) {
        this.exactNamespaceExclusion.next(exactNamespaceExclusion);
    }
    changeTsmStartsWithNamespaceExclusion(startsWithNamespaceExclusion: string) {
        this.startsWithNamespaceExclusion.next(startsWithNamespaceExclusion);
    }
    // Extension
    changeEnableTanzuExtension(enableTanzuExtension: boolean) {
        this.enableTanzuExtension.next(enableTanzuExtension);
    }
    changeTkgClusters(tkgClusters: string) {
        this.tkgClusters.next(tkgClusters);
    }
    changeEnableLoggingExtension(enableLoggingExtension: boolean) {
        this.enableLoggingExtension.next(enableLoggingExtension);
    }
    changeEnableMonitoringExtension(enableMonitoringExtension: boolean) {
        this.enableMonitoringExtension.next(enableMonitoringExtension);
    }
    changeLoggingEndpoint(loggingEndpoint: string) {
        this.loggingEndpoint.next(loggingEndpoint);
    }
    changeSyslogAddress(syslogAddress: string) {
        this.syslogAddress.next(syslogAddress);
    }
    changeSyslogPort(syslogPort: string) {
        this.syslogPort.next(syslogPort);
    }
    changeSyslogMode(syslogMode: string) {
        this.syslogMode.next(syslogMode);
    }
    changeSyslogFormat(syslogFormat: string) {
        this.syslogFormat.next(syslogFormat);
    }
    changeHttpAddress(httpAddress: string) {
        this.httpAddress.next(httpAddress);
    }
    changeHttpPort(httpPort: string) {
        this.httpPort.next(httpPort);
    }
    changeHttpUri(httpUri: string) {
        this.httpUri.next(httpUri);
    }
    changeHttpHeaderKey(httpHeaderKey: string) {
        this.httpHeaderKey.next(httpHeaderKey);
    }
    changeElasticSearchAddress(elasticSearchAddress: string) {
        this.elasticSearchAddress.next(elasticSearchAddress);
    }
    changeElasticSearchPort(elasticSearchPort: string) {
        this.elasticSearchPort.next(elasticSearchPort);
    }
    changeKafkaServiceName(kafkaServiceName: string) {
        this.kafkaServiceName.next(kafkaServiceName);
    }
    changeKafkaTopicName(kafkaTopicName: string) {
        this.kafkaTopicName.next(kafkaTopicName);
    }
    changeSplunkAddress(splunkAddress: string) {
        this.splunkAddress.next(splunkAddress);
    }
    changeSplunkPort(splunkPort: string) {
        this.splunkPort.next(splunkPort);
    }
    changeSplunkToken(splunkToken: string) {
        this.splunkToken.next(splunkToken);
    }
    changePrometheusFqdn(prometheusFqdn: string) {
        this.prometheusFqdn.next(prometheusFqdn);
    }
    changePrometheusCertPath(prometheusCertPath: string) {
        this.prometheusCertPath.next(prometheusCertPath);
    }
    changePrometheusCertkeyPath(prometheusCertKeyPath: string) {
        this.prometheusCertKeyPath.next(prometheusCertKeyPath);
    }
    changeGrafanaFqdn(grafanaFqdn: string) {
        this.grafanaFqdn.next(grafanaFqdn);
    }
    changeGrafanaPassword(grafanaPassword: string) {
        this.grafanaPassword.next(grafanaPassword);
    }
    changeGrafanaCertPath(grafanaCertPath: string) {
        this.grafanaCertPath.next(grafanaCertPath);
    }
    changeGrafanaCertKeyPath(grafanaCertKeyPath: string) {
        this.grafanaCertKeyPath.next(grafanaCertKeyPath);
    }
}
