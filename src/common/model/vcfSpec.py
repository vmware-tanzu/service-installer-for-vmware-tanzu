# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

from typing import Optional

from pydantic import BaseModel


class VcenterDetails(BaseModel):
    vcenterAddress: str
    vcenterSsoUser: str
    vcenterSsoPasswordBase64: str
    resourcePoolName: str
    vcenterDatacenter: str
    vcenterCluster: str
    vcenterDatastore: str
    contentLibraryName: str
    aviOvaName: str
    nsxtAddress: Optional[str]
    nsxtUser: Optional[str]
    nsxtUserPasswordBase64: Optional[str]
    nsxtTier1RouterDisplayName: Optional[str]
    nsxtOverlay: Optional[str]


class MarketplaceSpec(BaseModel):
    refreshToken: str


class CustomRepositorySpec(BaseModel):
    tkgCustomImageRepository: Optional[str]
    tkgCustomImageRepositoryPublicCaCert: Optional[str]


class CompliantSpec(BaseModel):
    compliantDeployment: Optional[str]


class TmcDetails(BaseModel):
    tmcAvailability: Optional[str]
    tmcRefreshToken: str
    tmcInstanceURL: str


class TanzuObservabilityDetails(BaseModel):
    tanzuObservabilityAvailability: str
    tanzuObservabilityUrl: str
    tanzuObservabilityRefreshToken: str


class SaasEndpoints(BaseModel):
    tmcDetails: TmcDetails
    tanzuObservabilityDetails: Optional[TanzuObservabilityDetails]


class InfraComponents(BaseModel):
    dnsServersIp: str
    ntpServers: str
    searchDomains: str


class ProxyDetails(BaseModel):
    enableProxy: str
    httpProxy: str
    httpsProxy: str
    noProxy: str
    proxyCert: str


class ProxySpec(BaseModel):
    arcasVm: ProxyDetails
    tkgMgmt: ProxyDetails
    tkgSharedservice: ProxyDetails
    tkgWorkload: ProxyDetails


class EnvSpec(BaseModel):
    vcenterDetails: Optional[VcenterDetails]
    envType: Optional[str]
    marketplaceSpec: Optional[MarketplaceSpec]
    ceipParticipation: Optional[str]
    customRepositorySpec: Optional[CustomRepositorySpec]
    compliantSpec: Optional[CompliantSpec]
    saasEndpoints: Optional[SaasEndpoints]
    infraComponents: Optional[InfraComponents]
    proxySpec: Optional[ProxySpec]


class AviMgmtNetwork(BaseModel):
    aviMgmtNetworkName: str
    aviMgmtNetworkGatewayCidr: str
    aviMgmtServiceIpStartRange: str
    aviMgmtServiceIpEndRange: str


class TkgClusterVipNetwork(BaseModel):
    tkgClusterVipNetworkName: str
    tkgClusterVipNetworkGatewayCidr: str
    tkgClusterVipIpStartRange: str
    tkgClusterVipIpEndRange: str


class AviComponents(BaseModel):
    aviPasswordBase64: str
    aviBackupPassphraseBase64: str
    aviController01Ip: str
    aviController01Fqdn: str
    aviController02Ip: Optional[str]
    aviController02Fqdn: Optional[str]
    aviController03Ip: Optional[str]
    aviController03Fqdn: Optional[str]
    aviClusterIp: Optional[str]
    aviClusterFqdn: Optional[str]
    enableAviHa: Optional[str]
    typeOfLicense: Optional[str]
    aviSize: Optional[str]
    aviCertPath: Optional[str]
    aviCertKeyPath: Optional[str]


class TkgMgmtComponents(BaseModel):
    tkgMgmtNetworkName: str
    tkgMgmtGatewayCidr: str
    tkgMgmtClusterName: str
    tkgMgmtSize: str
    tkgMgmtDeploymentType: str
    tkgMgmtClusterCidr: str
    tkgMgmtBaseOs: str
    tkgMgmtServiceCidr: str
    tkgMgmtClusterGroupName: str


class tkgSharedserviceRbacUserRoleSpec(BaseModel):
    clusterAdminUsers: Optional[str]
    adminUsers: Optional[str]
    editUsers: Optional[str]
    viewUsers: Optional[str]


class tkgWorkloadRbacUserRoleSpec(BaseModel):
    clusterAdminUsers: Optional[str]
    adminUsers: Optional[str]
    editUsers: Optional[str]
    viewUsers: Optional[str]


class TkgSharedClusterVeleroDataProtection(BaseModel):
    enableVelero: str
    username: str
    passwordBase64: str
    bucketName: str
    backupRegion: str
    backupS3Url: str
    backupPublicUrl: str


class TkgSharedserviceSpec(BaseModel):
    tkgSharedserviceNetworkName: Optional[str]
    tkgSharedserviceGatewayCidr: Optional[str]
    tkgSharedserviceDhcpStartRange: Optional[str]
    tkgSharedserviceDhcpEndRange: Optional[str]
    tkgSharedserviceClusterName: Optional[str]
    tkgSharedserviceSize: Optional[str]
    tkgSharedserviceDeploymentType: Optional[str]
    tkgSharedserviceWorkerMachineCount: Optional[str]
    tkgSharedserviceClusterCidr: Optional[str]
    tkgSharedserviceServiceCidr: Optional[str]
    tkgSharedserviceBaseOs: Optional[str]
    tkgSharedserviceKubeVersion: Optional[str]
    tkgSharedserviceCpuSize: Optional[str]
    tkgSharedserviceMemorySize: Optional[str]
    tkgSharedserviceStorageSize: Optional[str]
    tkgSharedserviceClusterGroupName: Optional[str]
    tkgSharedserviceEnableDataProtection: Optional[str]
    tkgSharedClusterCredential: Optional[str]
    tkgSharedClusterCredential: Optional[str]
    tkgSharedClusterBackupLocation: Optional[str]
    tkgSharedClusterVeleroDataProtection: Optional[TkgSharedClusterVeleroDataProtection]
    tkgSharedserviceRbacUserRoleSpec: Optional[tkgSharedserviceRbacUserRoleSpec]
    tkgSharedserviceClusterGroupName: Optional[str]


class OidcSpec(BaseModel):
    oidcIssuerUrl: str
    oidcClientId: str
    oidcClientSecret: str
    oidcScopes: str
    oidcUsernameClaim: str
    oidcGroupsClaim: str


class LdapSpec(BaseModel):
    ldapEndpointIp: str
    ldapEndpointPort: str
    ldapBindPWBase64: str
    ldapBindDN: str
    ldapUserSearchBaseDN: str
    ldapUserSearchFilter: str
    ldapUserSearchUsername: str
    ldapGroupSearchBaseDN: str
    ldapGroupSearchFilter: str
    ldapGroupSearchUserAttr: str
    ldapGroupSearchGroupAttr: str
    ldapGroupSearchNameAttr: str
    ldapRootCAData: str


class IdentityManagementSpec(BaseModel):
    identityManagementType: str
    oidcSpec: Optional[OidcSpec]
    ldapSpec: Optional[LdapSpec]


class TkgComponentSpec(BaseModel):
    aviMgmtNetwork: Optional[AviMgmtNetwork]
    tkgClusterVipNetwork: Optional[TkgClusterVipNetwork]
    aviComponents: Optional[AviComponents]
    tkgMgmtComponents: Optional[TkgMgmtComponents]
    tkgSharedserviceSpec: Optional[TkgSharedserviceSpec]
    identityManagementSpec: Optional[IdentityManagementSpec]


class TkgMgmtDataNetwork(BaseModel):
    tkgMgmtDataNetworkName: str
    tkgMgmtDataNetworkGatewayCidr: str
    tkgMgmtAviServiceIpStartRange: str
    tkgMgmtAviServiceIpEndRange: str


class TkgWorkloadDataNetwork(BaseModel):
    tkgWorkloadDataNetworkName: str
    tkgWorkloadDataNetworkGatewayCidr: str
    tkgWorkloadAviServiceIpStartRange: str
    tkgWorkloadAviServiceIpEndRange: str


class NamespaceExclusions(BaseModel):
    exactName: str
    startsWith: str


class TkgWorkloadClusterVeleroDataProtection(BaseModel):
    enableVelero: str
    username: str
    passwordBase64: str
    bucketName: str
    backupRegion: str
    backupS3Url: str
    backupPublicUrl: str


class TkgWorkloadComponents(BaseModel):
    tkgWorkloadNetworkName: Optional[str]
    tkgWorkloadGatewayCidr: Optional[str]
    tkgWorkloadDhcpStartRange: Optional[str]
    tkgWorkloadDhcpEndRange: Optional[str]
    tkgWorkloadClusterName: Optional[str]
    tkgWorkloadSize: Optional[str]
    tkgWorkloadCpuSize: Optional[str]
    tkgWorkloadMemorySize: Optional[str]
    tkgWorkloadStorageSize: Optional[str]
    tkgWorkloadDeploymentType: Optional[str]
    tkgWorkloadWorkerMachineCount: Optional[str]
    tkgWorkloadClusterCidr: Optional[str]
    tkgWorkloadServiceCidr: Optional[str]
    tkgWorkloadTsmIntegration: Optional[str]
    namespaceExclusions: Optional[NamespaceExclusions]
    tkgWorkloadBaseOs: Optional[str]
    tkgWorkloadKubeVersion: Optional[str]
    tkgWorkloadEnableAviL7: Optional[str]
    tkgWorkloadClusterGroupName: Optional[str]
    tkgWorkloadEnableDataProtection: Optional[str]
    tkgWorkloadClusterCredential: Optional[str]
    tkgWorkloadClusterVeleroDataProtection: Optional[TkgWorkloadClusterVeleroDataProtection]
    tkgWorkloadRbacUserRoleSpec: Optional[tkgWorkloadRbacUserRoleSpec]
    tkgWorkloadClusterGroupName: Optional[str]


class HarborSpec(BaseModel):
    enableHarborExtension: str
    harborFqdn: str
    harborPasswordBase64: str
    harborCertPath: str
    harborCertKeyPath: str


class SyslogEndpoint(BaseModel):
    enableSyslogEndpoint: str
    syslogEndpointAddress: str
    syslogEndpointPort: str
    syslogEndpointPort: str
    syslogEndpointFormat: str


class HttpEndpoint(BaseModel):
    enableHttpEndpoint: str
    httpEndpointAddress: str
    httpEndpointPort: str
    httpEndpointUri: str
    httpEndpointHeaderKeyValue: str


class ElasticSearchEndpoint(BaseModel):
    enableElasticSearchEndpoint: str
    elasticSearchEndpointAddress: str
    elasticSearchEndpointPort: str


class KafkaEndpoint(BaseModel):
    enableKafkaEndpoint: str
    kafkaBrokerServiceName: str
    kafkaTopicName: str


class SplunkEndpoint(BaseModel):
    enableSplunkEndpoint: str
    splunkEndpointAddress: str
    splunkEndpointPort: str
    splunkEndpointToken: str


class Logging(BaseModel):
    syslogEndpoint: SyslogEndpoint
    httpEndpoint: HttpEndpoint
    kafkaEndpoint: KafkaEndpoint


class Monitoring(BaseModel):
    enableLoggingExtension: str
    prometheusFqdn: str
    prometheusCertPath: str
    prometheusCertKeyPath: str
    grafanaFqdn: str
    grafanaCertPath: str
    grafanaCertKeyPath: str
    grafanaPasswordBase64: str


class TanzuExtensions(BaseModel):
    tkgClustersName: str
    enableExtensions: str
    logging: Logging
    monitoring: Monitoring


class VcfMasterSpec(BaseModel):
    envSpec: Optional[EnvSpec]
    tkgComponentSpec: Optional[TkgComponentSpec]
    tkgMgmtDataNetwork: Optional[TkgMgmtDataNetwork]
    tkgWorkloadDataNetwork: Optional[TkgWorkloadDataNetwork]
    tkgWorkloadComponents: Optional[TkgWorkloadComponents]
    harborSpec: Optional[HarborSpec]
    tanzuExtensions: Optional[TanzuExtensions]
