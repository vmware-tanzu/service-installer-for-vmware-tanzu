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
    tmcAvailability: str
    tmcRefreshToken: str
    tmcInstanceURL: str


class TanzuObservabilityDetails(BaseModel):
    tanzuObservabilityAvailability: str
    tanzuObservabilityUrl: str
    tanzuObservabilityRefreshToken: str


class SaasEndpoints(BaseModel):
    tmcDetails: TmcDetails
    tanzuObservabilityDetails: TanzuObservabilityDetails


class AviMgmtNetworkSpec(BaseModel):
    aviMgmtGatewayCidr: str
    aviMgmtDhcpStartRange: str
    aviMgmtDhcpEndRange: str


class AviComponentSpec(BaseModel):
    aviPasswordBase64: str
    aviBackupPassPhraseBase64: str
    aviClusterIp: Optional[str]
    aviClusterFqdn: Optional[str]


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


class TkgSharedServiceSpec(BaseModel):
    tkgSharedGatewayCidr: str
    tkgSharedDhcpStartRange: str
    tkgSharedDhcpEndRange: str
    tkgSharedClusterName: str
    tkgSharedserviceSize: str
    tkgSharedserviceDeploymentType: str
    tkgSharedserviceWorkerMachineCount: str
    tkgSharedserviceClusterCidr: str
    tkgSharedserviceServiceCidr: str
    tkgSharedserviceBaseOs: str
    tkgSharedserviceKubeVersion: str
    tkgSharedserviceCpuSize: str
    tkgSharedserviceMemorySize: str
    tkgSharedserviceStorageSize: str
    tkgSharedserviceBaseOs: str


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


class TkgWorkloadSpec(BaseModel):
    tkgWorkloadGatewayCidr: str
    tkgWorkloadDhcpStartRange: str
    tkgWorkloadDhcpEndRange: str
    tkgWorkloadClusterName: str
    tkgWorkloadSize: str
    tkgWorkloadDeploymentType: str
    tkgWorkloadWorkerMachineCount: str
    tkgWorkloadClusterCidr: str
    tkgWorkloadServiceCidr: str
    tkgWorkloadTsmIntegration: str
    tkgWorkloadBaseOs: str
    tkgWorkloadKubeVersion: str
    tkgWorkloadCpuSize: str
    tkgWorkloadMemorySize: str
    tkgWorkloadStorageSize: str
    namespaceExclusions: NamespaceExclusions
    tkgWorkloadBaseOs: str


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
    aviMgmtNetworkSpec: AviMgmtNetworkSpec
    aviComponentSpec: AviComponentSpec
    tkgClusterVipNetwork: TkgClusterVipNetwork
    tkgMgmtSpec: TkgMgmtSpec
    tkgSharedServiceSpec: TkgSharedServiceSpec
    tkgMgmtDataNetworkSpec: TkgMgmtDataNetworkSpec
    tkgWorkloadDataNetworkSpec: TkgWorkloadDataNetworkSpec
    tkgWorkloadSpec: TkgWorkloadSpec
    harborSpec: HarborSpec
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
    envSpec: EnvSpec
    marketplaceSpec: Optional[MarketplaceSpec]
    ceipParticipation: str
    envVariablesSpec: EnvVariablesSpec
    saasEndpoints: SaasEndpoints
    componentSpec: ComponentSpec
    tanzuExtensions: Optional[TanzuExtensions]
