import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable()
export  class VsphereNsxtDataService {
    private useInputFile = new BehaviorSubject<boolean>(false);
    // Dumy Component Form Control
    private dnsServer = new BehaviorSubject('');
    private ntpServer = new BehaviorSubject('');
    private searchDomain = new BehaviorSubject('');
    // Arcas Bootstrap VM Proxy
    private arcasEnableProxy = new BehaviorSubject<boolean>(false);
    private arcasHttpProxyUrl = new BehaviorSubject('');
    private arcasHttpProxyUsername = new BehaviorSubject('');
    private arcasHttpProxyPassword = new BehaviorSubject('');
    private arcasIsSameAsHttp = new BehaviorSubject<boolean>(false);
    private arcasHttpsProxyUrl = new BehaviorSubject('');
    private arcasHttpsProxyUsername = new BehaviorSubject('');
    private arcasHttpsProxyPassword  = new BehaviorSubject('');
    private arcasNoProxy = new BehaviorSubject('');
    // Iaas Provider
    private vcAddress = new BehaviorSubject('');
    private vcUser = new BehaviorSubject('');
    private vcPass = new BehaviorSubject('');
    private nsxtAddress = new BehaviorSubject('');
    private nsxtUsername = new BehaviorSubject('');
    private nsxtPassword = new BehaviorSubject('');
    private datastore = new BehaviorSubject('');
    private cluster = new BehaviorSubject('');
    private datacenter = new BehaviorSubject('');
    private contentLib = new BehaviorSubject('');
    private ovaImage = new BehaviorSubject('');
    private resourcePool = new BehaviorSubject('');
    private tier1Router = new BehaviorSubject('');
    private nsxtOverlay = new BehaviorSubject('');
    private custUsername = new BehaviorSubject('');
    private custPassword = new BehaviorSubject('');
    private jwtToken = new BehaviorSubject('');
    private kubernetesOva = new BehaviorSubject('');
    private customerConnect = new BehaviorSubject<boolean>(false);
    private isMarketplace = new BehaviorSubject<boolean>(false);
    private marketplaceRefreshToken = new BehaviorSubject('');
    // TMC
    private enableTMC = new BehaviorSubject<boolean>(false);
    private apiToken = new BehaviorSubject('');
    private instanceUrl = new BehaviorSubject('');
    private enableTO = new BehaviorSubject<boolean>(false);
    private toURL = new BehaviorSubject('');
    private toApiToken = new BehaviorSubject('');
    // Custom Repo
    private enableRepo = new BehaviorSubject<boolean>(false);
    private repoImage = new BehaviorSubject('');
    private caCert = new BehaviorSubject<boolean>(true);
    private repoUsername = new BehaviorSubject('');
    private repoPassword = new BehaviorSubject('');
    // AVI Components
    private aviPassword = new BehaviorSubject('');
    private aviBackupPassword = new BehaviorSubject('');
    private aviSize = new BehaviorSubject('');
    // AVI HA fields
    private enableHA = new BehaviorSubject<boolean>(false);
    private aviFqdn = new BehaviorSubject('');
    private aviIp = new BehaviorSubject('');
    private aviFqdn02 = new BehaviorSubject('');
    private aviIp02 = new BehaviorSubject('');
    private aviFqdn03 = new BehaviorSubject('');
    private aviIp03 = new BehaviorSubject('');
    private clusterIp = new BehaviorSubject('');
    private clusterFqdn = new BehaviorSubject('');
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
    // Identity Management Provider
    private enableIdentityManagement = new BehaviorSubject<boolean>(false);
    private identityManagementType = new BehaviorSubject('');
    // OIDC
    private oidcIssuerUrl = new BehaviorSubject('');
    private oidcClientId = new BehaviorSubject('');
    private oidcClientSecret = new BehaviorSubject('');
    private oidcScopes = new BehaviorSubject('');
    private oidcUsernameClaim = new BehaviorSubject('');
    private oidcGroupsClaim = new BehaviorSubject('');
    // LDAP
    private ldapEndpointIp = new BehaviorSubject('');
    private ldapEndpointPort = new BehaviorSubject('');
    private ldapBindPW = new BehaviorSubject('');
    private ldapBindDN = new BehaviorSubject('');
    private ldapUserSearchBaseDN = new BehaviorSubject('');
    private ldapUserSearchFilter = new BehaviorSubject('');
    private ldapUserSearchUsername = new BehaviorSubject('');
    private ldapGroupSearchBaseDN = new BehaviorSubject('');
    private ldapGroupSearchFilter = new BehaviorSubject('');
    private ldapGroupSearchUserAttr = new BehaviorSubject('');
    private ldapGroupSearchGroupAttr = new BehaviorSubject('');
    private ldapGroupSearchNameAttr = new BehaviorSubject('');
    private ldapRootCAData = new BehaviorSubject('');
    private ldapTestUserName = new BehaviorSubject('');
    private ldapTestGroupName = new BehaviorSubject('');
    // TKG Mgmt Data
    private tkgMgmtDataSegment = new BehaviorSubject('');
    private tkgMgmtDataGateway = new BehaviorSubject('');
    private tkgMgmtDataDhcpStart = new BehaviorSubject('');
    private tkgMgmtDataDhcpEnd = new BehaviorSubject('');
    // Mgmt Cluster
    private mgmtDeploymentType = new BehaviorSubject('');
    private mgmtDeploymentSize = new BehaviorSubject('');
    private mgmtSegment = new BehaviorSubject('');
    private mgmtGateway = new BehaviorSubject('');
    private mgmtControlPlane = new BehaviorSubject('');
    private mgmtClusterName = new BehaviorSubject('');
    private mgmtEnableProxy = new BehaviorSubject<boolean>(false);
    private mgmtHttpProxyUrl = new BehaviorSubject('');
    private mgmtHttpProxyUsername = new BehaviorSubject('');
    private mgmtHttpProxyPassword = new BehaviorSubject('');
    private mgmtIsSameAsHttp = new BehaviorSubject<boolean>(false);
    private mgmtHttpsProxyUrl = new BehaviorSubject('');
    private mgmtHttpsProxyUsername = new BehaviorSubject('');
    private mgmtHttpsProxyPassword  = new BehaviorSubject('');
    private mgmtNoProxy = new BehaviorSubject('');
    private mgmtClusterCidr = new BehaviorSubject('100.96.0.0/11');
    private mgmtServiceCidr = new BehaviorSubject('100.64.0.0/13');
    private mgmtBaseImage = new BehaviorSubject('');
    private mgmtCpu = new BehaviorSubject('');
    private mgmtMemory = new BehaviorSubject('');
    private mgmtStorage = new BehaviorSubject('');
    private mgmtClusterAdminUsers = new BehaviorSubject('');
    private mgmtAdminUsers = new BehaviorSubject('');
    private mgmtEditUsers = new BehaviorSubject('');
    private mgmtViewUsers = new BehaviorSubject('');
    // VELERO FIELDS
    private mgmtClusterGroupName = new BehaviorSubject('');
    // Shared Cluster
    private sharedDeploymentType = new BehaviorSubject('');
    private sharedDeploymentSize = new BehaviorSubject('');
    private sharedSegment = new BehaviorSubject('');
    private sharedGateway = new BehaviorSubject('');
    private sharedDhcpStart = new BehaviorSubject('');
    private sharedDhcpEnd = new BehaviorSubject('');
    private sharedControlPlane = new BehaviorSubject('');
    private sharedClusterName = new BehaviorSubject('');
    private sharedWorkerNodeCount = new BehaviorSubject('');
    private sharedEnableProxy = new BehaviorSubject<boolean>(false);
    private sharedHttpProxyUrl = new BehaviorSubject('');
    private sharedHttpProxyUsername = new BehaviorSubject('');
    private sharedHttpProxyPassword = new BehaviorSubject('');
    private sharedIsSameAsHttp = new BehaviorSubject<boolean>(false);
    private sharedHttpsProxyUrl = new BehaviorSubject('');
    private sharedHttpsProxyUsername = new BehaviorSubject('');
    private sharedHttpsProxyPassword  = new BehaviorSubject('');
    private sharedNoProxy = new BehaviorSubject('');
    private sharedClusterCidr = new BehaviorSubject('100.96.0.0/11');
    private sharedServiceCidr = new BehaviorSubject('100.64.0.0/13');
    private enableHarbor = new BehaviorSubject<boolean>(false);
    private harborFqdn = new BehaviorSubject('');
    private harborPassword = new BehaviorSubject('');
    private harborCertPath = new BehaviorSubject('');
    private harborCertKey = new BehaviorSubject('');
    private sharedBaseImage = new BehaviorSubject('');
    private sharedBaseImageVersion = new BehaviorSubject('');
    private sharedCpu = new BehaviorSubject('');
    private sharedMemory = new BehaviorSubject('');
    private sharedStorage = new BehaviorSubject('');
    private sharedClusterAdminUsers = new BehaviorSubject('');
    private sharedAdminUsers = new BehaviorSubject('');
    private sharedEditUsers = new BehaviorSubject('');
    private sharedViewUsers = new BehaviorSubject('');
    // VELERO fields
    private sharedEnableDataProtection = new BehaviorSubject<boolean>(false);
    private sharedClusterGroupName = new BehaviorSubject('');
    private sharedDataProtectionCreds = new BehaviorSubject('');
    private sharedDataProtectionTargetLocation = new BehaviorSubject('');
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
    // TKG Workload Data
    private tkgWrkDataSegment = new BehaviorSubject('');
    private tkgWrkDataGateway = new BehaviorSubject('');
    private tkgWrkDataDhcpStart = new BehaviorSubject('');
    private tkgWrkDataDhcpEnd = new BehaviorSubject('');
    // Workload Cluster
    private wrkDeploymentType = new BehaviorSubject('');
    private wrkDeploymentSize = new BehaviorSubject('');
    private wrkSegment = new BehaviorSubject('');
    private wrkGateway = new BehaviorSubject('');
    private wrkDhcpStart = new BehaviorSubject('');
    private wrkDhcpEnd = new BehaviorSubject('');
    private wrkWorkerNodeCount = new BehaviorSubject('');
    private wrkControlPlane = new BehaviorSubject('');
    private wrkClusterName = new BehaviorSubject('');
    private wrkEnableProxy = new BehaviorSubject<boolean>(false);
    private wrkHttpProxyUrl = new BehaviorSubject('');
    private wrkHttpProxyUsername = new BehaviorSubject('');
    private wrkHttpProxyPassword = new BehaviorSubject('');
    private wrkIsSameAsHttp = new BehaviorSubject<boolean>(false);
    private wrkHttpsProxyUrl = new BehaviorSubject('');
    private wrkHttpsProxyUsername = new BehaviorSubject('');
    private wrkHttpsProxyPassword  = new BehaviorSubject('');
    private wrkNoProxy = new BehaviorSubject('');
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
    private wrkClusterAdminUsers = new BehaviorSubject('');
    private wrkAdminUsers = new BehaviorSubject('');
    private wrkEditUsers = new BehaviorSubject('');
    private wrkViewUsers = new BehaviorSubject('');
    // VELERO fields
    private wrkEnableDataProtection = new BehaviorSubject<boolean>(false);
    private wrkClusterGroupName = new BehaviorSubject('');
    private wrkDataProtectionCreds = new BehaviorSubject('');
    private wrkDataProtectionTargetLocation = new BehaviorSubject('');

    currentInputFileStatus = this.useInputFile.asObservable();
    // Dumy Component Form Control Current Values
    currentDnsValue = this.dnsServer.asObservable();
    currentNtpValue = this.ntpServer.asObservable();
    currentSearchDomainValue = this.searchDomain.asObservable();
    // Infra
    currentArcasEnableProxy = this.arcasEnableProxy.asObservable();
    currentArcasHttpProxyUrl = this.arcasHttpProxyUrl.asObservable();
    currentArcasHttpProxyUsername = this.arcasHttpProxyUsername.asObservable();
    currentArcasHttpProxyPassword = this.arcasHttpProxyPassword.asObservable();
    currentArcasIsSameAsHttp = this.arcasIsSameAsHttp.asObservable();
    currentArcasHttpsProxyUrl = this.arcasHttpsProxyUrl.asObservable();
    currentArcasHttpsProxyUsername = this.arcasHttpsProxyUsername.asObservable();
    currentArcasHttpsProxyPassword = this.arcasHttpsProxyPassword.asObservable();
    currentArcasNoProxy = this.arcasNoProxy.asObservable();
    // Iaas Provider
    currentVcAddress = this.vcAddress.asObservable();
    currentVcUser = this.vcUser.asObservable();
    currentVcPass = this.vcPass.asObservable();
    currentNsxtAddress = this.nsxtAddress.asObservable();
    currentNsxtUsername = this.nsxtUsername.asObservable();
    currentNsxtPassword = this.nsxtPassword.asObservable();
    currentDatastore = this.datastore.asObservable();
    currentCluster = this.cluster.asObservable();
    currentDatacenter = this.datacenter.asObservable();
    currentContentLib = this.contentLib.asObservable();
    currentOvaImage = this.ovaImage.asObservable();
    currentResourcePool = this.resourcePool.asObservable();
    currentTier1Router = this.tier1Router.asObservable();
    currentNsxtOverlay = this.nsxtOverlay.asObservable();
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
    currentInstanceUrl = this.instanceUrl.asObservable();
    currentEnableTO = this.enableTO.asObservable();
    currentTOUrl = this.toURL.asObservable();
    currentTOApiToken = this.toApiToken.asObservable();
    // Custom Repo
    currentEnableRepo = this.enableRepo.asObservable();
    currentRepoImage = this.repoImage.asObservable();
    currentCaCert = this.caCert.asObservable();
    currentRepoUsername = this.repoUsername.asObservable();
    currentRepoPassword = this.repoPassword.asObservable();
    // AVI Components
    currentAviHA = this.enableHA.asObservable();
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
    // Identity Management Provider
    currentEnableIdentityManagement = this.enableIdentityManagement.asObservable();
    currentIdentityManagementType = this.identityManagementType.asObservable();
    // OIDC
    currentOidcIssuerUrl = this.oidcIssuerUrl.asObservable();
    currentOidcClientId = this.oidcClientId.asObservable();
    currentOidcClientSecret = this.oidcClientSecret.asObservable();
    currentOidcScopes = this.oidcScopes.asObservable();
    currentOidcUsernameClaim = this.oidcUsernameClaim.asObservable();
    currentOidcGroupsClaim = this.oidcGroupsClaim.asObservable();
    // LDAP
    currentLdapEndpointIp = this.ldapEndpointIp.asObservable();
    currentLdapEndpointPort = this.ldapEndpointPort.asObservable();
    currentLdapBindPW = this.ldapBindPW.asObservable();
    currentLdapBindDN = this.ldapBindDN.asObservable();
    currentLdapUserSearchBaseDN = this.ldapUserSearchBaseDN.asObservable();
    currentLdapUserSearchFilter = this.ldapUserSearchFilter.asObservable();
    currentLdapUserSearchUsername = this.ldapUserSearchUsername.asObservable();
    currentLdapGroupSearchBaseDN = this.ldapGroupSearchBaseDN.asObservable();
    currentLdapGroupSearchFilter = this.ldapGroupSearchFilter.asObservable();
    currentLdapGroupSearchUserAttr = this.ldapGroupSearchUserAttr.asObservable();
    currentLdapGroupSearchGroupAttr = this.ldapGroupSearchGroupAttr.asObservable();
    currentLdapGroupSearchNameAttr = this.ldapGroupSearchNameAttr.asObservable();
    currentLdapRootCAData = this.ldapRootCAData.asObservable();
    currentLdapTestUserName = this.ldapTestUserName.asObservable();
    currentLdapTestGroupName = this.ldapTestGroupName.asObservable();
    // TKG Mgmt Data
    currentTkgMgmtDataSegment = this.tkgMgmtDataSegment.asObservable();
    currentTkgMgmtDataGateway = this.tkgMgmtDataGateway.asObservable();
    currentTkgMgmtDataDhcpStart = this.tkgMgmtDataDhcpStart.asObservable();
    currentTkgMgmtDataDhcpEnd = this.tkgMgmtDataDhcpEnd.asObservable();
    // Mgmt Cluster
    currentMgmtDeploymentType = this.mgmtDeploymentType.asObservable();
    currentMgmtDeploymentSize = this.mgmtDeploymentSize.asObservable();
    currentMgmtSegment = this.mgmtSegment.asObservable();
    currentMgmtGateway = this.mgmtGateway.asObservable();
    currentMgmtControlPlane = this.mgmtControlPlane.asObservable();
    currentMgmtClusterName = this.mgmtClusterName.asObservable();
    currentMgmtEnableProxy = this.mgmtEnableProxy.asObservable();
    currentMgmtHttpProxyUrl = this.mgmtHttpProxyUrl.asObservable();
    currentMgmtHttpProxyUsername = this.mgmtHttpProxyUsername.asObservable();
    currentMgmtHttpProxyPassword = this.mgmtHttpProxyPassword.asObservable();
    currentMgmtIsSameAsHttp = this.mgmtIsSameAsHttp.asObservable();
    currentMgmtHttpsProxyUrl = this.mgmtHttpsProxyUrl.asObservable();
    currentMgmtHttpsProxyUsername = this.mgmtHttpsProxyUsername.asObservable();
    currentMgmtHttpsProxyPassword = this.mgmtHttpsProxyPassword.asObservable();
    currentMgmtNoProxy = this.mgmtNoProxy.asObservable();
    currentMgmtClusterCidr = this.mgmtClusterCidr.asObservable();
    currentMgmtServiceCidr = this.mgmtServiceCidr.asObservable();
    currentMgmtBaseImage = this.mgmtBaseImage.asObservable();
    currentMgmtCpu = this.mgmtCpu.asObservable();
    currentMgmtMemory = this.mgmtMemory.asObservable();
    currentMgmtStorage = this.mgmtStorage.asObservable();
    currentMgmtClusterAdminUsers = this.mgmtClusterAdminUsers.asObservable();
    currentMgmtAdminUsers = this.mgmtAdminUsers.asObservable();
    currentMgmtEditUsers = this.mgmtEditUsers.asObservable();
    currentMgmtViewUsers = this.mgmtViewUsers.asObservable();
    // VELERO FIELDS
    currentMgmtClusterGroupName = this.mgmtClusterGroupName.asObservable();
    // Shared Cluster
    currentSharedDeploymentType = this.sharedDeploymentType.asObservable();
    currentSharedDeploymentSize = this.sharedDeploymentSize.asObservable();
    currentSharedControlPlane = this.sharedControlPlane.asObservable();
    currentSharedClusterName = this.sharedClusterName.asObservable();
    currentSharedGateway = this.sharedGateway.asObservable();
    currentSharedSegment = this.sharedSegment.asObservable();
    currentSharedDhcpStart = this.sharedDhcpStart.asObservable();
    currentSharedDhcpEnd = this.sharedDhcpEnd.asObservable();
    currentSharedWorkerNodeCount = this.sharedWorkerNodeCount.asObservable();
    currentSharedEnableProxy = this.sharedEnableProxy.asObservable();
    currentSharedHttpProxyUrl = this.sharedHttpProxyUrl.asObservable();
    currentSharedHttpProxyUsername = this.sharedHttpProxyUsername.asObservable();
    currentSharedHttpProxyPassword = this.sharedHttpProxyPassword.asObservable();
    currentSharedIsSameAsHttp = this.sharedIsSameAsHttp.asObservable();
    currentSharedHttpsProxyUrl = this.sharedHttpsProxyUrl.asObservable();
    currentSharedHttpsProxyUsername = this.sharedHttpsProxyUsername.asObservable();
    currenSharedHttpsProxyPassword = this.sharedHttpsProxyPassword.asObservable();
    currentSharedNoProxy = this.sharedNoProxy.asObservable();
    currentSharedClusterCidr = this.sharedClusterCidr.asObservable();
    currentSharedServiceCidr = this.sharedServiceCidr.asObservable();
    currentSharedBaseImage = this.sharedBaseImage.asObservable();
    currentSharedBaseImageVersion = this.sharedBaseImageVersion.asObservable();
    currentEnableHarbor = this.enableHarbor.asObservable();
    currentHarborFqdn = this.harborFqdn.asObservable();
    currentHarborPassword = this.harborPassword.asObservable();
    currentHarborCertPath = this.harborCertPath.asObservable();
    currentHarborCertKey = this.harborCertKey.asObservable();
    currentSharedCpu = this.sharedCpu.asObservable();
    currentSharedMemory = this.sharedMemory.asObservable();
    currentSharedStorage = this.sharedStorage.asObservable();
    currentSharedClusterAdminUsers = this.sharedClusterAdminUsers.asObservable();
    currentSharedAdminUsers = this.sharedAdminUsers.asObservable();
    currentSharedEditUsers = this.sharedEditUsers.asObservable();
    currentSharedViewUsers = this.sharedViewUsers.asObservable();
    // VELERO FIELDS
    currentSharedClusterGroupName = this.sharedClusterGroupName.asObservable();
    currentSharedEnableDataProtection = this.sharedEnableDataProtection.asObservable();
    currentSharedDataProtectionCreds = this.sharedDataProtectionCreds.asObservable();
    currentSharedDataProtectionTargetLocation = this.sharedDataProtectionTargetLocation.asObservable();
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
    // TKG Workload Data
    currentTkgWrkDataSegment = this.tkgWrkDataSegment.asObservable();
    currentTkgWrkDataGateway = this.tkgWrkDataGateway.asObservable();
    currentTkgWrkDataDhcpStart = this.tkgWrkDataDhcpStart.asObservable();
    currentTkgWrkDataDhcpEnd = this.tkgWrkDataDhcpEnd.asObservable();
    // Workload Cluster
    currentWrkDeploymentType = this.wrkDeploymentType.asObservable();
    currentWrkDeploymentSize = this.wrkDeploymentSize.asObservable();
    currentWrkSegment = this.wrkSegment.asObservable();
    currentWrkGateway = this.wrkGateway.asObservable();
    currentWrkDhcpStart = this.wrkDhcpStart.asObservable();
    currentWrkDhcpEnd = this.wrkDhcpEnd.asObservable();
    currentWrkWorkerNodeCount = this.wrkWorkerNodeCount.asObservable();
    currentWrkControlPlane = this.wrkControlPlane.asObservable();
    currentWrkClusterName = this.wrkClusterName.asObservable();
    currentWrkEnableProxy = this.wrkEnableProxy.asObservable();
    currentWrkHttpProxyUrl = this.wrkHttpProxyUrl.asObservable();
    currentWrkHttpProxyUsername = this.wrkHttpProxyUsername.asObservable();
    currentWrkHttpProxyPassword = this.wrkHttpProxyPassword.asObservable();
    currentWrkIsSameAsHttp = this.wrkIsSameAsHttp.asObservable();
    currentWrkHttpsProxyUrl = this.wrkHttpsProxyUrl.asObservable();
    currentWrkHttpsProxyUsername = this.wrkHttpsProxyUsername.asObservable();
    currentWrkHttpsProxyPassword = this.wrkHttpsProxyPassword.asObservable();
    currentWrkNoProxy = this.wrkNoProxy.asObservable();
    currentWrkClusterCidr = this.wrkClusterCidr.asObservable();
    currentWrkServiceCidr = this.wrkServiceCidr.asObservable();
    currentWrkBaseImage = this.wrkBaseImage.asObservable();
    currentWrkBaseImageVersion = this.wrkBaseImageVersion.asObservable();
    currentEnableTSM = this.enableTSM.asObservable();
    currentExactNamespaceExclusion = this.exactNamespaceExclusion.asObservable();
    currentStartsWithNamespaceExclusion = this.startsWithNamespaceExclusion.asObservable();
    currentWrkCpu = this.wrkCpu.asObservable();
    currentWrkMemory = this.wrkMemory.asObservable();
    currentWrkStorage = this.wrkStorage.asObservable();
    currentWrkClusterAdminUsers = this.wrkClusterAdminUsers.asObservable();
    currentWrkAdminUsers = this.wrkAdminUsers.asObservable();
    currentWrkEditUsers = this.wrkEditUsers.asObservable();
    currentWrkViewUsers = this.wrkViewUsers.asObservable();
    // VELERO FIELDS
    currentWrkClusterGroupName = this.wrkClusterGroupName.asObservable();
    currentWrkEnableDataProtection = this.wrkEnableDataProtection.asObservable();
    currentWrkDataProtectionCreds = this.wrkDataProtectionCreds.asObservable();
    currentWrkDataProtectionTargetLocation = this.wrkDataProtectionTargetLocation.asObservable();
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
    // Arcas Bootstrap VM
    changeArcasEnableProxy(arcasEnableProxy: boolean) {
        this.arcasEnableProxy.next(arcasEnableProxy);
    }
    changeArcasHttpProxyUrl(arcasHttpProxyUrl: string) {
        this.arcasHttpProxyUrl.next(arcasHttpProxyUrl);
    }
    changeArcasHttpProxyUsername(arcasHttpProxyUsername: string) {
        this.arcasHttpProxyUsername.next(arcasHttpProxyUsername);
    }
    changeArcasHttpProxyPassword(arcasHttpProxyPassword: string) {
        this.arcasHttpProxyPassword.next(arcasHttpProxyPassword);
    }
    changeArcasIsSameAsHttp(arcasIsSameAsHttp: boolean) {
        this.arcasIsSameAsHttp.next(arcasIsSameAsHttp);
    }
    changeArcasHttpsProxyUrl(arcasHttpsProxyUrl: string) {
        this.arcasHttpsProxyUrl.next(arcasHttpsProxyUrl);
    }
    changeArcasHttpsProxyUsername(arcasHttpsProxyUsername) {
        this.arcasHttpsProxyUsername.next(arcasHttpsProxyUsername);
    }
    changeArcasHttpsProxyPassword(arcasHttpsProxyPassword: string) {
        this.arcasHttpsProxyPassword.next(arcasHttpsProxyPassword);
    }
    changeArcasNoProxy(arcasNoProxy: string) {
        this.arcasNoProxy.next(arcasNoProxy);
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
    changeNsxtAddress(vcAddress:string) {
        this.nsxtAddress.next(vcAddress);
    }
    changeNsxtUsername(vcAddress:string) {
        this.nsxtUsername.next(vcAddress);
    }
    changeNsxtPassword(vcAddress:string) {
        this.nsxtPassword.next(vcAddress);
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
    changeResourcePool(resourcePool: string) {
        this.resourcePool.next(resourcePool);
    }
    changeTier1Router(tier1Router: string) {
        this.tier1Router.next(tier1Router);
    }
    changeNsxtOverlay(nsxtOverlay: string) {
        this.nsxtOverlay.next(nsxtOverlay);
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
    changeEnableTO(enableTO: boolean) {
        this.enableTO.next(enableTO);
    }
    changeTOUrl(toURL: string) {
        this.toURL.next(toURL);
    }
    changeTOApiToken(toApiToken: string) {
        this.toApiToken.next(toApiToken);
    }
    // Custom Repo
    changeEnableRepoSettings(enableRepo: boolean) {
        this.enableRepo.next(enableRepo );
    }
    changeRepoImage(repoImage: string) {
        this.repoImage.next(repoImage);
    }
    changeCaCert(caCert: boolean) {
        this.caCert.next(caCert);
    }
    changeRepoUsername(repoUsername: string) {
        this.repoUsername.next(repoUsername);
    }
    changeRepoPassword(repoPassword: string) {
        this.repoPassword.next(repoPassword);
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
        this.enableHA.next(enableHa);
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
    // Identity Management Provider
    changeEnableIdentityManagement(idmEnable: boolean) {
        this.enableIdentityManagement.next(idmEnable);
    }
    changeIdentityManagementType(idmType: string) {
        this.identityManagementType.next(idmType);
    }
    // OIDC
    changeOidcIssuerUrl(issuerUrl: string) {
        this.oidcIssuerUrl.next(issuerUrl);
    }
    changeOidcClientId(clientId: string) {
        this.oidcClientId.next(clientId);
    }
    changeOidcClientSecret(clientSecret: string) {
        this.oidcClientSecret.next(clientSecret);
    }
    changeOidcScopes(scopes: string) {
        this.oidcScopes.next(scopes);
    }
    changeOidcUsernameClaim(usernameClaim: string) {
        this.oidcUsernameClaim.next(usernameClaim);
    }
    changeOidcGroupClaim(groupsClaim: string) {
        this.oidcGroupsClaim.next(groupsClaim);
    }
    changeLdapEndpointIp(endpointIp: string){
        this.ldapEndpointIp.next(endpointIp);
    }
    changeLdapEndpointPort(endpointPort: string){
        this.ldapEndpointPort.next(endpointPort);
    }
    changeLdapBindPw(pw: string){
        this.ldapBindPW.next(pw);
    }
    changeLdapBindDN(bindDN: string) {
        this.ldapBindDN.next(bindDN);
    }
    changeLdapUserSearchBaseDN(baseDN: string){
        this.ldapUserSearchBaseDN.next(baseDN);
    }
    changeLdapUserSearchFilter(filter: string) {
        this.ldapUserSearchFilter.next(filter);
    }
    changeLdapUserSearchUsername(uname: string) {
        this.ldapUserSearchUsername.next(uname);
    }
    changeLdapGroupSearchBaseDN(baseDN: string){
        this.ldapGroupSearchBaseDN.next(baseDN);
    }
    changeLdapGroupSearchFilter(filter: string){
        this.ldapGroupSearchFilter.next(filter);
    }
    changeLdapGroupSearchUserAttr(attr: string){
        this.ldapGroupSearchUserAttr.next(attr);
    }
    changeLdapGroupSearchGroupAttr(attr: string){
        this.ldapGroupSearchGroupAttr.next(attr);
    }
    changeLdapGroupSearchNameAttr(attr: string){
        this.ldapGroupSearchNameAttr.next(attr);
    }
    changeLdapRootCAData(ca: string){
        this.ldapRootCAData.next(ca);
    }
    changeLdapTestUserName(user: string){
        this.ldapTestUserName.next(user);
    }
    changeLdapTestGroupName(grp: string){
        this.ldapTestGroupName.next(grp);
    }
    // TKG Mgmt Data
    changeTkgMgmtDataSegment(tkgMgmtDataSegment: string) {
        this.tkgMgmtDataSegment.next(tkgMgmtDataSegment);
    }
    changeTkgMgmtDataGateway(tkgMgmtDataGateway: string) {
        this.tkgMgmtDataGateway.next(tkgMgmtDataGateway);
    }
    changeTkgMgmtDataDhcpStart(tkgMgmtDataDhcpStart: string) {
        this.tkgMgmtDataDhcpStart.next(tkgMgmtDataDhcpStart);
    }
    changeTkgMgmtDataDhcpEnd(tkgMgmtDataDhcpEnd: string) {
        this.tkgMgmtDataDhcpEnd.next(tkgMgmtDataDhcpEnd);
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
    changeMgmtControlPlane(mgmtControlPlane: string) {
        this.mgmtControlPlane.next(mgmtControlPlane);
    }
    changeMgmtClusterName(mgmtClusterName: string) {
        this.mgmtClusterName.next(mgmtClusterName);
    }
    changeMgmtEnableProxy(mgmtEnableProxy: boolean) {
        this.mgmtEnableProxy.next(mgmtEnableProxy);
    }
    changeMgmtHttpProxyUrl(mgmtHttpProxyUrl: string) {
        this.mgmtHttpProxyUrl.next(mgmtHttpProxyUrl);
    }
    changeMgmtHttpProxyUsername(mgmtHttpProxyUsername: string) {
        this.mgmtHttpProxyUsername.next(mgmtHttpProxyUsername);
    }
    changeMgmtHttpProxyPassword(mgmtHttpProxyPassword: string) {
        this.mgmtHttpProxyPassword.next(mgmtHttpProxyPassword);
    }
    changeMgmtIsSameAsHttp(mgmtIsSameAsHttp: boolean) {
        this.mgmtIsSameAsHttp.next(mgmtIsSameAsHttp);
    }
    changeMgmtHttpsProxyUrl(mgmtHttpsProxyUrl: string) {
        this.mgmtHttpsProxyUrl.next(mgmtHttpsProxyUrl);
    }
    changeMgmtHttpsProxyUsername(mgmtHttpsProxyUsername) {
        this.mgmtHttpsProxyUsername.next(mgmtHttpsProxyUsername);
    }
    changeMgmtHttpsProxyPassword(mgmtHttpsProxyPassword: string) {
        this.mgmtHttpsProxyPassword.next(mgmtHttpsProxyPassword);
    }
    changeMgmtNoProxy(mgmtNoProxy: string) {
        this.mgmtNoProxy.next(mgmtNoProxy);
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
    changeMgmtClusterAdminUsers(clusterAdminUsers: string) {
        this.mgmtClusterAdminUsers.next(clusterAdminUsers);
    }
    changeMgmtAdminUsers(adminUsers: string) {
        this.mgmtAdminUsers.next(adminUsers);
    }
    changeMgmtEditUsers(editUsers: string) {
        this.mgmtEditUsers.next(editUsers);
    }
    changeMgmtViewUsers(viewUsers: string) {
        this.mgmtViewUsers.next(viewUsers);
    }
    // VELERO FIELDS
    changeMgmtClusterGroupName(grp: string) {
        this.mgmtClusterGroupName.next(grp);
    }
    // Shared Cluster
    changeSharedDeploymentType(sharedDeploymentType: string) {
        this.sharedDeploymentType.next(sharedDeploymentType);
    }
    changeSharedDeploymentSize(sharedDeploymentSize: string) {
        this.sharedDeploymentSize.next(sharedDeploymentSize);
    }
    changeSharedControlPlane(sharedControlPlane: string) {
        this.sharedControlPlane.next(sharedControlPlane);
    }
    changeSharedClusterName(sharedClusterName: string) {
        this.sharedClusterName.next(sharedClusterName);
    }
    changeSharedWorkerNodeCount(sharedWorkerNodeCount: string) {
        this.sharedWorkerNodeCount.next(sharedWorkerNodeCount);
    }
    changeSharedGatewayAddress(sharedGateway: string) {
        this.sharedGateway.next(sharedGateway);
    }
    changeSharedDhcpStart(sharedDhcpStart: string) {
        this.sharedDhcpStart.next(sharedDhcpStart);
    }
    changeSharedDhcpEnd(sharedDhcpEnd: string) {
        this.sharedDhcpEnd.next(sharedDhcpEnd);
    }
    changeSharedSegmentName(sharedSegment: string) {
        this.sharedSegment.next(sharedSegment);
    }
    changeSharedEnableProxy(sharedEnableProxy: boolean) {
        this.sharedEnableProxy.next(sharedEnableProxy);
    }
    changeSharedHttpProxyUrl(sharedHttpProxyUrl: string) {
        this.sharedHttpProxyUrl.next(sharedHttpProxyUrl);
    }
    changeSharedHttpProxyUsername(sharedHttpProxyUsername: string) {
        this.sharedHttpProxyUsername.next(sharedHttpProxyUsername);
    }
    changeSharedHttpProxyPassword(sharedHttpProxyPassword: string) {
        this.sharedHttpProxyPassword.next(sharedHttpProxyPassword);
    }
    changeSharedIsSameAsHttp(sharedIsSameAsHttp: boolean) {
        this.sharedIsSameAsHttp.next(sharedIsSameAsHttp);
    }
    changeSharedHttpsProxyUrl(sharedHttpsProxyUrl: string) {
        this.sharedHttpsProxyUrl.next(sharedHttpsProxyUrl);
    }
    changeSharedHttpsProxyUsername(sharedHttpsProxyUsername) {
        this.sharedHttpsProxyUsername.next(sharedHttpsProxyUsername);
    }
    changeSharedHttpsProxyPassword(sharedHttpsProxyPassword: string) {
        this.sharedHttpsProxyPassword.next(sharedHttpsProxyPassword);
    }
    changeSharedNoProxy(sharedNoProxy: string) {
        this.sharedNoProxy.next(sharedNoProxy);
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
    changeSharedCpu(sharedCpu: string){
        this.sharedCpu.next(sharedCpu);
    }
    changeSharedMemory(sharedMemory: string){
        this.sharedMemory.next(sharedMemory);
    }
    changeSharedStorage(sharedStorage: string){
        this.sharedStorage.next(sharedStorage);
    }
    changeSharedClusterAdminUsers(clusterAdminUsers: string) {
        this.sharedClusterAdminUsers.next(clusterAdminUsers);
    }
    changeSharedAdminUsers(adminUsers: string) {
        this.sharedAdminUsers.next(adminUsers);
    }
    changeSharedEditUsers(editUsers: string) {
        this.sharedEditUsers.next(editUsers);
    }
    changeSharedViewUsers(viewUsers: string) {
        this.sharedViewUsers.next(viewUsers);
    }
    // VELERO FIELDS
    changeSharedClusterGroupName(grp: string) {
        this.sharedClusterGroupName.next(grp);
    }
    changeSharedEnableDataProtection(enable: boolean) {
        this.sharedEnableDataProtection.next(enable);
    }
    changeSharedDataProtectionCreds(creds: string) {
        this.sharedDataProtectionCreds.next(creds);
    }
    changeSharedDataProtectionTargetLocation(location: string) {
        this.sharedDataProtectionTargetLocation.next(location);
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
    // TKG Workload Data
    changeTkgWrkDataSegment(tkgWrkDataSegment: string) {
        this.tkgWrkDataSegment.next(tkgWrkDataSegment);
    }
    changeTkgWrkDataGateway(tkgWrkDataGateway: string) {
        this.tkgWrkDataGateway.next(tkgWrkDataGateway);
    }
    changeTkgWrkDataDhcpStart(tkgWrkDataDhcpStart: string) {
        this.tkgWrkDataDhcpStart.next(tkgWrkDataDhcpStart);
    }
    changeTkgWrkDataDhcpEnd(tkgWrkDataDhcpEnd: string) {
        this.tkgWrkDataDhcpEnd.next(tkgWrkDataDhcpEnd);
    }
    // Workload Cluster
    changeWrkDeploymentType(wrkDeploymentType: string) {
        this.wrkDeploymentType.next(wrkDeploymentType);
    }
    changeWrkDeploymentSize(wrkDeploymentSize: string) {
        this.wrkDeploymentSize.next(wrkDeploymentSize);
    }
    changeWrkSegment(wrkSegment: string) {
        this.wrkSegment.next(wrkSegment);
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
    changeWrkControlPlane(wrkControlPlane: string) {
        this.wrkControlPlane.next(wrkControlPlane);
    }
    changeWrkClusterName(wrkClusterName: string) {
        this.wrkClusterName.next(wrkClusterName);
    }
    changeWrkWorkerNodeCount(wrkWorkerNodeCount: string) {
        this.wrkWorkerNodeCount.next(wrkWorkerNodeCount);
    }
    changeWrkEnableProxy(wrkEnableProxy: boolean) {
        this.wrkEnableProxy.next(wrkEnableProxy);
    }
    changeWrkHttpProxyUrl(wrkHttpProxyUrl: string) {
        this.wrkHttpProxyUrl.next(wrkHttpProxyUrl);
    }
    changeWrkHttpProxyUsername(wrkHttpProxyUsername: string) {
        this.wrkHttpProxyUsername.next(wrkHttpProxyUsername);
    }
    changeWrkHttpProxyPassword(wrkHttpProxyPassword: string) {
        this.wrkHttpProxyPassword.next(wrkHttpProxyPassword);
    }
    changeWrkIsSameAsHttp(wrkIsSameAsHttp: boolean) {
        this.wrkIsSameAsHttp.next(wrkIsSameAsHttp);
    }
    changeWrkHttpsProxyUrl(wrkHttpsProxyUrl: string) {
        this.wrkHttpsProxyUrl.next(wrkHttpsProxyUrl);
    }
    changeWrkHttpsProxyUsername(wrkHttpsProxyUsername) {
        this.wrkHttpsProxyUsername.next(wrkHttpsProxyUsername);
    }
    changeWrkHttpsProxyPassword(wrkHttpsProxyPassword: string) {
        this.wrkHttpsProxyPassword.next(wrkHttpsProxyPassword);
    }
    changeWrkNoProxy(wrkNoProxy: string) {
        this.wrkNoProxy.next(wrkNoProxy);
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
    changeEnableTSM(enableTSM: boolean) {
        this.enableTSM.next(enableTSM);
    }
    changeTsmExactNamespaceExclusion(exactNamespaceExclusion: string) {
        this.exactNamespaceExclusion.next(exactNamespaceExclusion);
    }
    changeTsmStartsWithNamespaceExclusion(startsWithNamespaceExclusion: string) {
        this.startsWithNamespaceExclusion.next(startsWithNamespaceExclusion);
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
    changeWrkClusterAdminUsers(clusterAdminUsers: string){
        this.wrkClusterAdminUsers.next(clusterAdminUsers);
    }
    changeWrkAdminUsers(adminUsers: string) {
        this.wrkAdminUsers.next(adminUsers);
    }
    changeWrkEditUsers(editUsers: string) {
        this.wrkEditUsers.next(editUsers);
    }
    changeWrkViewUsers(viewUsers: string) {
        this.wrkViewUsers.next(viewUsers);
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
}
