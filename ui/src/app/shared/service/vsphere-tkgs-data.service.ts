import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable()
export  class VsphereTkgsService {
    private useInputFile = new BehaviorSubject<boolean>(false);
    // Dns Ntp Component Form Control
    private dnsServer = new BehaviorSubject('');
    private ntpServer = new BehaviorSubject('');
    private searchDomain = new BehaviorSubject('');
    // Arcas Bootstrap VM Proxy
//     private arcasEnableProxy = new BehaviorSubject<boolean>(false);
//     private arcasHttpProxyUrl = new BehaviorSubject('');
//     private arcasHttpProxyUsername = new BehaviorSubject('');
//     private arcasHttpProxyPassword = new BehaviorSubject('');
//     private arcasIsSameAsHttp = new BehaviorSubject<boolean>(false);
//     private arcasHttpsProxyUrl = new BehaviorSubject('');
//     private arcasHttpsProxyUsername = new BehaviorSubject('');
//     private arcasHttpsProxyPassword  = new BehaviorSubject('');
//     private arcasNoProxy = new BehaviorSubject('');
    // Iaas Provider
    private vcAddress = new BehaviorSubject('');
    private vcUser = new BehaviorSubject('');
    private vcPass = new BehaviorSubject('');
    private datastore = new BehaviorSubject('');
    private cluster = new BehaviorSubject('');
    private datacenter = new BehaviorSubject('');
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
    private instanceUrl = new BehaviorSubject('');
    private supervisorClusterName = new BehaviorSubject('');
    private supervisorClusterGroupName = new BehaviorSubject('');
    private enableTO = new BehaviorSubject<boolean>(false);
    private toURL = new BehaviorSubject('');
    private toApiToken = new BehaviorSubject('');
    // Custom Repo
//     private enableRepo = new BehaviorSubject<boolean>(false);
//     private repoImage = new BehaviorSubject('');
//     private caCert = new BehaviorSubject<boolean>(true);
//     private repoUsername = new BehaviorSubject('');
//     private repoPassword = new BehaviorSubject('');
    // AVI Components
    private aviPassword = new BehaviorSubject('');
    private aviBackupPassword = new BehaviorSubject('');
    // AVI HA fields
    private enableHAAvi = new BehaviorSubject<boolean>(false);
    private aviFqdn = new BehaviorSubject('');
    private aviIp = new BehaviorSubject('');
    private aviFqdn02 = new BehaviorSubject('');
    private aviIp02 = new BehaviorSubject('');
    private aviFqdn03 = new BehaviorSubject('');
    private aviIp03 = new BehaviorSubject('');
    private clusterIp = new BehaviorSubject('');
    private clusterFqdn = new BehaviorSubject('');
    private aviSize = new BehaviorSubject('');
    // Optional License and Cert
    private aviLicenseKey = new BehaviorSubject('');
    private aviCertPath = new BehaviorSubject('');
    private aviCertKeyPath = new BehaviorSubject('');
    // AVI Management Segment
    private aviSegment = new BehaviorSubject('');
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
    // Control Plane
    private controlPlaneSize = new BehaviorSubject('');
    // Content Library
    private subscribedContentLib = new BehaviorSubject('');
    // Storage Policy
    private masterStoragePolicy = new BehaviorSubject('');
    private ephemeralStoragePolicy = new BehaviorSubject('');
    private imageStoragePolicy = new BehaviorSubject('');
    // Mgmt NW
    private mgmtGateway = new BehaviorSubject('');
    private mgmtSegment = new BehaviorSubject('');
    private mgmtStartIp = new BehaviorSubject('');
    private mgmtDns = new BehaviorSubject('');
    private mgmtNtp = new BehaviorSubject('');
    private mgmtSearchDomain = new BehaviorSubject('');
    // Workload NW
    private wrkServiceCidr = new BehaviorSubject('10.96.0.0/22');
    private wrkGateway = new BehaviorSubject('');
    private wrkSegment = new BehaviorSubject('');
    private workloadSegmentName = new BehaviorSubject('');
    private wrkDns = new BehaviorSubject('');
    private wrkNtp = new BehaviorSubject('');
    private wrkStartIp = new BehaviorSubject('');
    private wrkEndIp = new BehaviorSubject('');
    // Namespace Settings
    private namespaceName = new BehaviorSubject('');
    private namespaceDescription = new BehaviorSubject('');
    private namespaceSegment = new BehaviorSubject('');
    private namespaceContentLib = new BehaviorSubject('');
    private namespaceVmClass = new BehaviorSubject([]);
    private cpuLimit = new BehaviorSubject('');
    private memLimit = new BehaviorSubject('');
    private storageLimit = new BehaviorSubject('');
    private storageSpec = new BehaviorSubject(new Map<string, string>());
    private clusterVersion = new BehaviorSubject('');
    // Workload Cluster
    private wrkNamespaceName = new BehaviorSubject('');
    private wrkClusterName = new BehaviorSubject('');
    private allowedStorageClass = new BehaviorSubject([]);
    private defaultStorageClass = new BehaviorSubject('');
    private nodeStorageClass = new BehaviorSubject('');
    private serviceCidr = new BehaviorSubject('');
    private podCidr = new BehaviorSubject('');
    private controlPlaneVmClass = new BehaviorSubject('');
    private workerVmClass = new BehaviorSubject('');
    private enableHA = new BehaviorSubject<boolean>(false);
    private wrkWorkerNodeCount = new BehaviorSubject('');
    private enableTSM = new BehaviorSubject<boolean>(false);
    private exactNamespaceExclusion = new BehaviorSubject('');
    private startsWithNamespaceExclusion = new BehaviorSubject('');
    //Additional volumes
    private tkgsControlVolumes = new BehaviorSubject(new Map<string, string>());
    private tkgsWorkerVolumes = new BehaviorSubject(new Map<string, string>());
    // VELERO fields
    private wrkEnableDataProtection = new BehaviorSubject<boolean>(false);
    private wrkClusterGroupName = new BehaviorSubject('');
    private wrkDataProtectionCreds = new BehaviorSubject('');
    private wrkDataProtectionTargetLocation = new BehaviorSubject('');
    //Harbor
    private enableHarbor = new BehaviorSubject<boolean>(false);
    private harborFqdn = new BehaviorSubject('');
    private harborPassword = new BehaviorSubject('');
    private harborCertPath = new BehaviorSubject('');
    private harborCertKey = new BehaviorSubject('');
    // Global Settings
    private defaultCNI = new BehaviorSubject('');

    private tkgsEnableProxy = new BehaviorSubject<boolean>(false);
    private tkgsHttpProxyUrl = new BehaviorSubject('');
    private tkgsHttpProxyUsername = new BehaviorSubject('');
    private tkgsHttpProxyPassword = new BehaviorSubject('');
    private tkgsIsSameAsHttp = new BehaviorSubject<boolean>(false);
    private tkgsHttpsProxyUrl = new BehaviorSubject('');
    private tkgsHttpsProxyUsername = new BehaviorSubject('');
    private tkgsHttpsProxyPassword  = new BehaviorSubject('');
    private tkgsNoProxy = new BehaviorSubject('');
    private tkgsProxyCert = new BehaviorSubject('');

    private tkgsAdditionalCAPaths = new BehaviorSubject([]);
    private tkgsAdditionalCaEndpointUrls = new BehaviorSubject([]);
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
    // private enableTSM = new BehaviorSubject<boolean>(false);
    // private exactNamespaceExclusion = new BehaviorSubject('');
    // private startsWithNamespaceExclusion = new BehaviorSubject('');

    currentInputFileStatus = this.useInputFile.asObservable();
    // Dumy Component Form Control Current Values
    currentDnsValue = this.dnsServer.asObservable();
    currentNtpValue = this.ntpServer.asObservable();
    currentSearchDomainValue = this.searchDomain.asObservable();
    // Iaas Provider
    currentVcAddress = this.vcAddress.asObservable();
    currentVcUser = this.vcUser.asObservable();
    currentVcPass = this.vcPass.asObservable();
    currentDatastore = this.datastore.asObservable();
    currentCluster = this.cluster.asObservable();
    currentDatacenter = this.datacenter.asObservable();
    currentContentLib = this.contentLib.asObservable();
    currentOvaImage = this.ovaImage.asObservable();
    // Marketplace Fields
    currentMarketplace = this.isMarketplace.asObservable();
    currentMarketplaceRefreshToken = this.marketplaceRefreshToken.asObservable();
    // Customer Connect Fields
    currentCustomerConnect = this.customerConnect.asObservable();
    currentCustUsername = this.custUsername.asObservable();
    currentCustPassword = this.custPassword.asObservable();
    currentJwtToken = this.jwtToken.asObservable();
    currentKubernetesOva = this.kubernetesOva.asObservable();
    // TMC
    currentEnableTMC = this.enableTMC.asObservable();
    currentApiToken = this.apiToken.asObservable();
    currentInstanceUrl = this.instanceUrl.asObservable();
    currentSupervisorClusterName = this.supervisorClusterName.asObservable();
    currentSupervisorClusterGroupName = this.supervisorClusterGroupName.asObservable();
    currentEnableTO = this.enableTO.asObservable();
    currentTOUrl = this.toURL.asObservable();
    currentTOApiToken = this.toApiToken.asObservable();
    // AVI Components
    currentAviHA = this.enableHAAvi.asObservable();
    currentAviPassword = this.aviPassword.asObservable();
    currentAviBackupPassword = this.aviBackupPassword.asObservable();
    currentAviFqdn = this.aviFqdn.asObservable();
    currentAviIp = this.aviIp.asObservable();
    currentAviFqdn02 = this.aviFqdn02.asObservable();
    currentAviIp02 = this.aviIp02.asObservable();
    currentAviFqdn03 = this.aviFqdn03.asObservable();
    currentAviIp03 = this.aviIp03.asObservable();
    currentAviClusterIp = this.clusterIp.asObservable();
    currentAviClusterFqdn = this.clusterFqdn.asObservable();
    currentAviSize = this.aviSize.asObservable();
    // AVI License and Cert
    currentAviLicense = this.aviLicenseKey.asObservable();
    currentAviCertPath = this.aviCertPath.asObservable();
    currentAviCertKeyPath = this.aviCertKeyPath.asObservable();
    // AVI Management Network
    currentAviSegment = this.aviSegment.asObservable();
    currentAviGateway = this.aviGateway.asObservable();
    currentAviDhcpStart = this.aviDhcpStart.asObservable();
    currentAviDhcpEnd = this.aviDhcpEnd.asObservable();
    // AVI Cluster VIP Network
    currentAviClusterVipGatewayIp = this.aviClusterVipGatewayIp.asObservable();
    currentAviClusterVipNetworkName = this.aviClusterVipNetworkName.asObservable();
    currentAviClusterVipStartIp = this.aviClusterVipStartIp.asObservable();
    currentAviClusterVipEndIp = this.aviClusterVipEndIp.asObservable();
    currentAviClusterVipSeStartIp = this.aviClusterVipSeStartIp.asObservable();
    currentAviClusterVipSeEndIp = this.aviClusterVipSeEndIp.asObservable();
    // Control Plane
    currentControlPlaneSize = this.controlPlaneSize.asObservable();
    // Content Library
    currentSubsContentLib = this.subscribedContentLib.asObservable();
    // Storage Policy
    currentMasterStoragePolicy = this.masterStoragePolicy.asObservable();
    currentEphemeralStoragePolicy = this.ephemeralStoragePolicy.asObservable();
    currentImageStoragePolicy = this.imageStoragePolicy.asObservable();
    // Mgmt NW
    currentMgmtSegment = this.mgmtSegment.asObservable();
    currentMgmtGateway = this.mgmtGateway.asObservable();
    currentMgmtStartAddress = this.mgmtStartIp.asObservable();
    currentMgmtDnsValue = this.mgmtDns.asObservable();
    currentMgmtNtpValue = this.mgmtNtp.asObservable();
    currentMgmtSearchDomainValue = this.mgmtSearchDomain.asObservable();
    // Workload NW
    currentWrkSegment = this.wrkSegment.asObservable();
    currentWorkloadSegmentName = this.workloadSegmentName.asObservable();
    currentWrkGateway = this.wrkGateway.asObservable();
    currentWrkStartAddress = this.wrkStartIp.asObservable();
    currentWrkEndAddress = this.wrkEndIp.asObservable();
    currentWrkDnsValue = this.wrkDns.asObservable();
    currentWrkNtpValue = this.wrkNtp.asObservable();
    currentWrkServiceCidr = this.wrkServiceCidr.asObservable();
    // Namespace
    currentNamespaceName = this.namespaceName.asObservable();
    currentNamespaceDescription = this.namespaceDescription.asObservable();
    currentNamespaceSegment = this.namespaceSegment.asObservable();
    currentNamespaceContentLib = this.namespaceContentLib.asObservable();
    currentNamespaceVmClass = this.namespaceVmClass.asObservable();
    currentCpuLimit = this.cpuLimit.asObservable();
    currentMemoryLimit = this.memLimit.asObservable();
    currentStorageLimit = this.storageLimit.asObservable();
    currentStorageSpec = this.storageSpec.asObservable();
    // Workload Cluster
    currentWrkClusterName = this.wrkClusterName.asObservable();
    currentWrkNamespaceName = this.wrkNamespaceName.asObservable();
    currentAllowedStorageClass = this.allowedStorageClass.asObservable();
    currentDefaultStorageClass = this.defaultStorageClass.asObservable();
    currentNodeStorageClass = this.nodeStorageClass.asObservable();
    currentServiceCidr = this.serviceCidr.asObservable();
    currentPodCidr = this.podCidr.asObservable();
    currentControlPlaneVmClass = this.controlPlaneVmClass.asObservable();
    currentWorkerVmClass = this.workerVmClass.asObservable();
    currentWrkWorkerNodeCount = this.wrkWorkerNodeCount.asObservable();
    currentEnableHA = this.enableHA.asObservable();
    currentClusterVersion = this.clusterVersion.asObservable();
    currentEnableTSM = this.enableTSM.asObservable();
    currentExactNamespaceExclusion = this.exactNamespaceExclusion.asObservable();
    currentStartsWithNamespaceExclusion = this.startsWithNamespaceExclusion.asObservable();
    //Additional volumes
    currentTkgsControlVolumes = this.tkgsControlVolumes.asObservable();
    currentTkgsWorkerVolumes = this.tkgsWorkerVolumes.asObservable();
    // VELERO FIELDS
    currentWrkClusterGroupName = this.wrkClusterGroupName.asObservable();
    currentWrkEnableDataProtection = this.wrkEnableDataProtection.asObservable();
    currentWrkDataProtectionCreds = this.wrkDataProtectionCreds.asObservable();
    currentWrkDataProtectionTargetLocation = this.wrkDataProtectionTargetLocation.asObservable();
    //Harbor
    currentEnableHarbor = this.enableHarbor.asObservable();
    currentHarborFqdn = this.harborFqdn.asObservable();
    currentHarborPassword = this.harborPassword.asObservable();
    currentHarborCertPath = this.harborCertPath.asObservable();
    currentHarborCertKey = this.harborCertKey.asObservable();
    // Global Settings
    currentDefaultCNI = this.defaultCNI.asObservable();
    
    currentTkgsEnableProxy = this.tkgsEnableProxy.asObservable();
    currentTkgsHttpProxyUrl = this.tkgsHttpProxyUrl.asObservable();
    currentTkgsHttpProxyUsername = this.tkgsHttpProxyUsername.asObservable();
    currentTkgsHttpProxyPassword = this.tkgsHttpsProxyPassword.asObservable();
    currentTkgsIsSameAsHttp = this.tkgsIsSameAsHttp.asObservable();
    currentTkgsHttpsProxyUrl = this.tkgsHttpsProxyUrl.asObservable();
    currentTkgsHttpsProxyUsername = this.tkgsHttpsProxyUsername.asObservable();
    currentTkgsHttpsProxyPassword = this.tkgsHttpsProxyPassword.asObservable();
    currentTkgsNoProxy = this.tkgsNoProxy.asObservable();
    currentTkgsProxyCert = this.tkgsProxyCert.asObservable();

    currentTkgsAdditionalCaPaths = this.tkgsAdditionalCAPaths.asObservable();
    currentTkgsAdditionalCaEndpointUrls = this.tkgsAdditionalCaEndpointUrls.asObservable();
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
    // currentEnableTSM = this.enableTSM.asObservable();
    // currentExactNamespaceExclusion = this.exactNamespaceExclusion.asObservable();
    // currentStartsWithNamespaceExclusion = this.startsWithNamespaceExclusion.asObservable();
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
    changeVCAddress(vcAddress:string) {
        this.vcAddress.next(vcAddress);
    }
    changeVCUser(vcUser:string) {
        this.vcUser.next(vcUser);
    }
    changeVCPass(vcPass:string) {
        this.vcPass.next(vcPass);
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
    changeInstanceUrl(url: string) {
        this.instanceUrl.next(url);
    }
    changeSupervisorClusterName(supervisorClusterName: string) {
        this.supervisorClusterName.next(supervisorClusterName);
    }
    changeSupervisorClusterGroupName(supervisorClusterGroupName: string){
        this.supervisorClusterGroupName.next(supervisorClusterGroupName);
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
    changeAviFqdn(aviFqdn: string) {
        this.aviFqdn.next(aviFqdn);
    }
    changeAviIp(aviIp: string) {
        this.aviIp.next(aviIp);
    }
    changeAviFqdn02(aviFqdn: string) {
        this.aviFqdn02.next(aviFqdn);
    }
    changeAviIp02(aviIp: string) {
        this.aviIp02.next(aviIp);
    }
    changeAviFqdn03(aviFqdn: string) {
        this.aviFqdn03.next(aviFqdn);
    }
    changeAviIp03(aviIp: string) {
        this.aviIp03.next(aviIp);
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
    changeAviPassword(aviPassword: string) {
        this.aviPassword .next(aviPassword);
    }
    changeAviBackupPassword(aviBackupPassword: string) {
        this.aviBackupPassword.next(aviBackupPassword);
    }
    changeAviSegment(aviSegment: string) {
        this.aviSegment.next(aviSegment);
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
    // Control Plane
    changeControlPlaneSize(controlPlaneSize: string) {
        this.controlPlaneSize.next(controlPlaneSize);
    }
    // Content Library
    changeContentLibrary(subscribedContentLib: string) {
        this.subscribedContentLib.next(subscribedContentLib);
    }
    // Storage Policy
    changeMasterStoragePolicy(masterStoragePolicy: string) {
        this.masterStoragePolicy.next(masterStoragePolicy);
    }
    changeEphemeralStoragePolicy(ephemeralStoragePolicy: string) {
        this.ephemeralStoragePolicy.next(ephemeralStoragePolicy);
    }
    changeImageStoragePolicy(imageStoragePolicy: string) {
        this.imageStoragePolicy.next(imageStoragePolicy);
    }
    // Mgmt Network
    changeMgmtGateway(mgmtGateway: string) {
        this.mgmtGateway.next(mgmtGateway);
    }
    changeMgmtSegment(mgmtSegment: string) {
        this.mgmtSegment.next(mgmtSegment);
    }
    changeMgmtStartIp(mgmtStartIp: string) {
        this.mgmtStartIp.next(mgmtStartIp);
    }
    changeMgmtDns(mgmtDns: string) {
        this.mgmtDns.next(mgmtDns);
    }
    changeMgmtNtp(mgmtNtp: string) {
        this.mgmtNtp.next(mgmtNtp);
    }
    changeMgmtSearchDomain(mgmtSearchDomain: string) {
        this.mgmtSearchDomain.next(mgmtSearchDomain);
    }
    // Workload Network
    changeWrkGateway(wrkGateway: string) {
        this.wrkGateway.next(wrkGateway);
    }
    changeWorkloadSegmentName(workloadSegName: string) {
        this.workloadSegmentName.next(workloadSegName);
    }
    changeWrkSegment(wrkSegment: string) {
        this.wrkSegment.next(wrkSegment);
    }
    changeWrkStartIp(wrkStartIp: string) {
        this.wrkStartIp.next(wrkStartIp);
    }
    changeWrkEndIp(wrkEndIp: string) {
        this.wrkEndIp.next(wrkEndIp);
    }
    changeWrkDns(wrkDns: string) {
        this.wrkDns.next(wrkDns);
    }
    changeWrkNtp(wrkNtp: string) {
        this.wrkNtp.next(wrkNtp);
    }
    changeWrkServiceCidr(wrkServiceCidr: string) {
        this.wrkServiceCidr.next(wrkServiceCidr);
    }
    // Namespace Setting
    changeNamespaceName(namespaceName: string) {
        this.namespaceName.next(namespaceName);
    }
    changeNamespaceDescription(namespaceDescription: string) {
        this.namespaceDescription.next(namespaceDescription);
    }
    changeNamespaceSegment(namespaceSegment: string) {
        this.namespaceSegment.next(namespaceSegment);
    }
    changeNamespaceContentLib(namespaceContentLib: string) {
        this.namespaceContentLib.next(namespaceContentLib);
    }
    changeNamespaceVmClass(namespaceVmClass: any) {
        this.namespaceVmClass.next(namespaceVmClass);
    }
    changeCpuLimit(cpuLimit: string) {
        this.cpuLimit.next(cpuLimit);
    }
    changeMemLimit(memLimit: string) {
        this.memLimit.next(memLimit);
    }
    changeStorageLimit(storageLimit: string) {
        this.storageLimit.next(storageLimit);
    }
    changeStorageSpec(storageSpec: any) {
        this.storageSpec.next(storageSpec);
    }
    // Workload Cluster Setting
    changeWrkClusterName(wrkClusterName: string) {
        this.wrkClusterName.next(wrkClusterName);
    }
    changeWrkNamespaceName(wrkNamespaceName: string) {
        this.wrkNamespaceName.next(wrkNamespaceName);
    }
    changeAllowedStorageClass(allowedStorageClass: any) {
        this.allowedStorageClass.next(allowedStorageClass);
    }
    changeDefaultStorageClass(defaultStorageClass: string) {
        this.defaultStorageClass.next(defaultStorageClass);
    }
    changeClusterVersion(version: string) {
        this.clusterVersion.next(version);
    }
    changeNodeStorageClass(nodeStorageClass: string) {
        this.nodeStorageClass.next(nodeStorageClass);
    }
    changeServiceCidr(serviceCidr: string) {
        this.serviceCidr.next(serviceCidr);
    }
    changePodCidr(podCidr: string) {
        this.podCidr.next(podCidr);
    }
    changeControlPlaneVmClass(controlPlaneVmClass: string) {
        this.controlPlaneVmClass.next(controlPlaneVmClass);
    }
    changeWorkerVmClass(workerVmClass: string) {
        this.workerVmClass.next(workerVmClass);
    }
    changeEnableHA(enableHA: boolean) {
        this.enableHA.next(enableHA);
    }
    changeWrkWorkerNodeCount(wrkWorkerNodeCount: string) {
        this.wrkWorkerNodeCount.next(wrkWorkerNodeCount);
    }
    //Additional Volumes
    changeTkgsControlVolumes(tkgsControlVolumes: any) {
        this.tkgsControlVolumes.next(tkgsControlVolumes);
    }
    changeTkgsWorkerVolumes(tkgsWorkerVolumes: any) {
        this.tkgsWorkerVolumes.next(tkgsWorkerVolumes);
    }
    // VELERO FIELDS
    changeWrkClusterGroupName(grp: string) {
        this.wrkClusterGroupName.next(grp);
    }
    changeWrkEnableDataProtection(enable: boolean) {
        this.wrkEnableDataProtection.next(enable);
    }
    changeWrkDataProtectionCreds(creds: string) {
        this.wrkDataProtectionCreds.next(creds);
    }
    changeWrkDataProtectionTargetLocation(location: string) {
        this.wrkDataProtectionTargetLocation.next(location);
    }
    //TSM
    changeEnableTSM(enableTSM: boolean) {
        this.enableTSM.next(enableTSM);
    }
    changeTsmExactNamespaceExclusion(exactNamespaceExclusion: string) {
        this.exactNamespaceExclusion.next(exactNamespaceExclusion);
    }
    changeTsmStartsWithNamespaceExclusion(startsWithNamespaceExclusion: string) {
        this.startsWithNamespaceExclusion.next(startsWithNamespaceExclusion);
    }
    //Harbor
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
    // Global Config
    changeDefaultCNI(cni: string) {
        this.defaultCNI.next(cni);
    }
    
    changeTkgsEnableProxy(enable: boolean) {
        this.tkgsEnableProxy.next(enable);
    }
    changeTkgsHttpProxyUrl(httpUrl: string) {
        this.tkgsHttpProxyUrl.next(httpUrl);
    }
    changeTkgsHttpProxyUsername(httpUser: string) {
        this.tkgsHttpProxyUsername.next(httpUser);
    }
    changeTkgsHttpProxyPassword(httpPass: string) {
        this.tkgsHttpsProxyPassword.next(httpPass);
    }
    changeTkgsIsSameAsHttp(same: boolean) {
        this.tkgsIsSameAsHttp.next(same);
    }
    changeTkgsHttpsProxyUrl(httpsUrl: string) {
        this.tkgsHttpsProxyUrl.next(httpsUrl);
    }
    changeTkgsHttpsProxyUsername(httpsUser: string) {
        this.tkgsHttpsProxyUsername.next(httpsUser);
    }
    changeTkgsHttpsProxyPassword(httpsPass: string) {
        this.tkgsHttpsProxyPassword.next(httpsPass);
    }
    changeTkgsNoProxy(noProxy: string) {
        this.tkgsNoProxy.next(noProxy);
    }
    changeTkgsProxyCert(cert: string) {
        this.tkgsProxyCert.next(cert);
    }

    changeTkgsAdditionalCAPaths(paths: any) {
        this.tkgsAdditionalCAPaths.next(paths);
    }
    changeTkgsAdditionalCaEndpointUrls(urls: any) {
        this.tkgsAdditionalCaEndpointUrls.next(urls);
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
