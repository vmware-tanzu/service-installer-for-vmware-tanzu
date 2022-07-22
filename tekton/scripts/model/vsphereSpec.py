#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from typing import Optional
from pydantic import BaseModel, Field, validator

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
    tkgCustomImageRepository: str
    tkgCustomImageRepositoryPublicCaCert: str


class TmcDetails(BaseModel):
    tmcAvailability: str
    tmcRefreshToken: str


class TanzuObservabilityDetails(BaseModel):
    tanzuObservabilityAvailability: str
    tanzuObservabilityUrl: str
    tanzuObservabilityRefreshToken: str


class SaasEndpoints(BaseModel):
    tmcDetails: TmcDetails
    tanzuObservabilityDetails: TanzuObservabilityDetails


class InfraComponents(BaseModel):
    dnsServersIp: str
    ntpServers: str


class ProxyDetails(BaseModel):
    enableProxy: str
    httpProxy: str
    httpsProxy: str
    noProxy: str


class ProxySpec(BaseModel):
    arcasVm: ProxyDetails
    tkgMgmt: ProxyDetails
    tkgSharedservice: ProxyDetails
    tkgWorkload: ProxyDetails


class EnvSpec(BaseModel):
    vcenterDetails: VcenterDetails
    envType: Optional[str]
    marketplaceSpec: MarketplaceSpec
    customRepositorySpec: CustomRepositorySpec
    saasEndpoints: SaasEndpoints
    infraComponents: InfraComponents
    proxySpec: ProxySpec


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


class TkgMgmtComponents(BaseModel):
    tkgMgmtNetworkName: str
    tkgMgmtGatewayCidr: str
    tkgMgmtClusterName: str
    tkgMgmtSize: str
    tkgMgmtDeploymentType: str
    tkgMgmtClusterCidr: str
    tkgMgmtServiceCidr: str
    tkgSharedserviceClusterName: Optional[str]
    tkgSharedserviceSize: Optional[str]
    tkgSharedserviceDeploymentType: Optional[str]
    tkgSharedserviceWorkerMachineCount: Optional[str]
    tkgSharedserviceClusterCidr: Optional[str]
    tkgSharedserviceServiceCidr: Optional[str]


class TkgSharedserviceSpec(BaseModel):
    tkgSharedserviceNetworkName: str
    tkgSharedserviceGatewayCidr: str
    tkgSharedserviceDhcpStartRange: str
    tkgSharedserviceDhcpEndRange: str
    tkgSharedserviceClusterName: str
    tkgSharedserviceSize: str
    tkgSharedserviceDeploymentType: str
    tkgSharedserviceWorkerMachineCount: str
    tkgSharedserviceClusterCidr: str
    tkgSharedserviceServiceCidr: str


class TkgComponentSpec(BaseModel):
    aviMgmtNetwork: AviMgmtNetwork
    tkgClusterVipNetwork: TkgClusterVipNetwork
    aviComponents: AviComponents
    tkgMgmtComponents: TkgMgmtComponents
    tkgSharedserviceSpec: Optional[TkgSharedserviceSpec]


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


class TkgWorkloadComponents(BaseModel):
    tkgWorkloadNetworkName: str
    tkgWorkloadGatewayCidr: str
    tkgWorkloadClusterName: str
    tkgWorkloadSize: str
    tkgWorkloadDeploymentType: str
    tkgWorkloadWorkerMachineCount: str
    tkgWorkloadClusterCidr: str
    tkgWorkloadServiceCidr: str
    tkgWorkloadTsmIntegration: str
    namespaceExclusions: NamespaceExclusions


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
    syslogEndpoint: Optional[SyslogEndpoint]
    httpEndpoint: Optional[HttpEndpoint]
    elasticSearchEndpoint: Optional[ElasticSearchEndpoint]
    kafkaEndpoint: Optional[KafkaEndpoint]
    splunkEndpoint: Optional[SplunkEndpoint]


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


class VsphereMasterSpec(BaseModel):
    envSpec: Optional[EnvSpec]
    tkgComponentSpec: Optional[TkgComponentSpec]
    tkgMgmtDataNetwork: Optional[TkgMgmtDataNetwork]
    tkgWorkloadDataNetwork: Optional[TkgWorkloadDataNetwork]
    tkgWorkloadComponents: Optional[TkgWorkloadComponents]
    harborSpec: Optional[HarborSpec]
    tanzuExtensions: Optional[TanzuExtensions]
