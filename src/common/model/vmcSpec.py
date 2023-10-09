# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

from typing import Optional

from pydantic import BaseModel


class EnvSpec(BaseModel):
    sddcRefreshToken: str
    orgName: str
    sddcName: str
    resourcePoolName: str
    sddcDatacenter: str
    sddcCluster: str
    sddcDatastore: str
    contentLibraryName: str
    aviOvaName: str


class MarketplaceSpec(BaseModel):
    refreshToken: str


class EnvVariablesSpec(BaseModel):
    dnsServersIp: str
    ntpServersIp: str


class TmcDetails(BaseModel):
    tmcAvailability: Optional[str]
    tmcRefreshToken: str
    tmcInstanceURL: str


class TanzuObservabilityDetails(BaseModel):
    tanzuObservabilityAvailability: str
    tanzuObservabilityUrl: str
    tanzuObservabilityRefreshToken: str


class SaasEndpoints(BaseModel):
    tmcDetails: Optional[TmcDetails]
    tanzuObservabilityDetails: Optional[TanzuObservabilityDetails]


class AviMgmtNetworkSpec(BaseModel):
    aviMgmtGatewayCidr: str
    aviMgmtDhcpStartRange: str
    aviMgmtDhcpEndRange: str


class AviComponentSpec(BaseModel):
    aviPasswordBase64: str
    aviBackupPassPhraseBase64: str
    aviClusterIp: Optional[str]
    aviClusterFqdn: Optional[str]
    typeOfLicense: str


class TkgClusterVipNetwork(BaseModel):
    tkgClusterVipNetworkGatewayCidr: str
    tkgClusterVipDhcpStartRange: str
    tkgClusterVipDhcpEndRange: str
    tkgClusterVipIpStartRange: str
    tkgClusterVipIpEndRange: str


class TkgMgmtSpec(BaseModel):
    tkgMgmtNetworkName: str
    tkgMgmtGatewayCidr: str
    tkgMgmtClusterName: str
    tkgMgmtSize: str
    tkgMgmtClusterCidr: str
    tkgMgmtServiceCidr: str
    tkgMgmtDeploymentType: str
    tkgMgmtBaseOs: str


class TkgSharedClusterVeleroDataProtection(BaseModel):
    enableVelero: Optional[str]
    username: Optional[str]
    passwordBase64: Optional[str]
    bucketName: Optional[str]
    backupRegion: Optional[str]
    backupS3Url: Optional[str]
    backupPublicUrl: Optional[str]


class TkgSharedserviceRbacUserRoleSpec(BaseModel):
    clusterAdminUsers: str
    adminUsers: str
    editUsers: str
    viewUsers: str


class TkgSharedServiceSpec(BaseModel):
    tkgSharedGatewayCidr: Optional[str]
    tkgSharedDhcpStartRange: Optional[str]
    tkgSharedDhcpEndRange: Optional[str]
    tkgSharedClusterName: Optional[str]
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
    tkgSharedserviceBaseOs: Optional[str]
    tkgSharedserviceClusterGroupName: Optional[str]
    tkgSharedserviceEnableDataProtection: Optional[str]
    tkgSharedClusterCredential: Optional[str]
    tkgSharedClusterBackupLocation: Optional[str]
    tkgSharedClusterVeleroDataProtection: Optional[TkgSharedClusterVeleroDataProtection]
    tkgSharedserviceRbacUserRoleSpec: Optional[TkgSharedserviceRbacUserRoleSpec]


class TkgMgmtDataNetworkSpec(BaseModel):
    tkgMgmtDataGatewayCidr: str
    tkgMgmtDataDhcpStartRange: str
    tkgMgmtDataDhcpEndRange: str
    tkgMgmtDataServiceStartRange: str
    tkgMgmtDataServiceEndRange: str


class TkgWorkloadDataNetworkSpec(BaseModel):
    tkgWorkloadDataGatewayCidr: str
    tkgWorkloadDataDhcpStartRange: str
    tkgWorkloadDataDhcpEndRange: str
    tkgWorkloadDataServiceStartRange: str
    tkgWorkloadDataServiceEndRange: str


class NamespaceExclusions(BaseModel):
    exactName: str
    startsWith: str


class TkgWorkloadClusterVeleroDataProtection(BaseModel):
    enableVelero: Optional[str]
    username: Optional[str]
    passwordBase64: Optional[str]
    bucketName: Optional[str]
    backupRegion: Optional[str]
    backupS3Url: Optional[str]
    backupPublicUrl: Optional[str]


class TkgWorkloadRbacUserRoleSpec(BaseModel):
    clusterAdminUsers: str
    adminUsers: str
    editUsers: str
    viewUsers: str


class TkgWorkloadSpec(BaseModel):
    tkgWorkloadGatewayCidr: Optional[str]
    tkgWorkloadDhcpStartRange: Optional[str]
    tkgWorkloadDhcpEndRange: Optional[str]
    tkgWorkloadClusterName: Optional[str]
    tkgWorkloadSize: Optional[str]
    tkgWorkloadDeploymentType: Optional[str]
    tkgWorkloadWorkerMachineCount: Optional[str]
    tkgWorkloadClusterCidr: Optional[str]
    tkgWorkloadServiceCidr: Optional[str]
    tkgWorkloadTsmIntegration: Optional[str]
    tkgWorkloadBaseOs: Optional[str]
    tkgWorkloadKubeVersion: Optional[str]
    tkgWorkloadCpuSize: Optional[str]
    tkgWorkloadMemorySize: Optional[str]
    tkgWorkloadStorageSize: Optional[str]
    namespaceExclusions: Optional[NamespaceExclusions]
    tkgWorkloadBaseOs: Optional[str]
    tkgWorkloadClusterGroupName: Optional[str]
    tkgWorkloadEnableDataProtection: Optional[str]
    tkgWorkloadClusterCredential: Optional[str]
    tkgWorkloadClusterBackupLocation: Optional[str]
    tkgWorkloadClusterVeleroDataProtection: Optional[TkgWorkloadClusterVeleroDataProtection]
    tkgWorkloadRbacUserRoleSpec: Optional[TkgWorkloadRbacUserRoleSpec]


class HarborSpec(BaseModel):
    harborFqdn: str
    harborPasswordBase64: str
    harborCertPath: str
    harborCertKeyPath: str


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


class ComponentSpec(BaseModel):
    aviMgmtNetworkSpec: Optional[AviMgmtNetworkSpec]
    aviComponentSpec: Optional[AviComponentSpec]
    tkgClusterVipNetwork: Optional[TkgClusterVipNetwork]
    tkgMgmtSpec: Optional[TkgMgmtSpec]
    tkgSharedServiceSpec: Optional[TkgSharedServiceSpec]
    tkgMgmtDataNetworkSpec: Optional[TkgMgmtDataNetworkSpec]
    tkgWorkloadDataNetworkSpec: Optional[TkgWorkloadDataNetworkSpec]
    tkgWorkloadSpec: Optional[TkgWorkloadSpec]
    harborSpec: Optional[HarborSpec]
    identityManagementSpec: Optional[IdentityManagementSpec]


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


class VmcMasterSpec(BaseModel):
    envSpec: Optional[EnvSpec]
    marketplaceSpec: Optional[MarketplaceSpec]
    ceipParticipation: Optional[str]
    envVariablesSpec: Optional[EnvVariablesSpec]
    saasEndpoints: Optional[SaasEndpoints]
    componentSpec: Optional[ComponentSpec]
    tanzuExtensions: Optional[TanzuExtensions]
