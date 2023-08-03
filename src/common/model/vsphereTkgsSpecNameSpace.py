# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

from typing import List, Optional

from pydantic import BaseModel


class VcenterDetails(BaseModel):
    vcenterAddress: str
    vcenterSsoUser: str
    vcenterSsoPasswordBase64: str
    vcenterDatacenter: str
    vcenterCluster: str


class TmcDetails(BaseModel):
    tmcAvailability: str
    tmcRefreshToken: str
    tmcInstanceURL: str
    tmcSupervisorClusterName: str


class TanzuObservabilityDetails(BaseModel):
    tanzuObservabilityAvailability: str
    tanzuObservabilityUrl: str
    tanzuObservabilityRefreshToken: str


class SaasEndpoints(BaseModel):
    tmcDetails: TmcDetails
    tanzuObservabilityDetails: TanzuObservabilityDetails


class EnvSpec(BaseModel):
    vcenterDetails: VcenterDetails
    envType: str
    saasEndpoints: SaasEndpoints


class TkgsVsphereNamespaceResourceSpec(BaseModel):
    cpuLimit: Optional[int]
    memoryLimit: Optional[int]
    storageRequestLimit: Optional[int]


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


class VolumesSpec(BaseModel):
    def __getitem__(self, x):
        return getattr(self, x)

    name: str
    mountPath: str
    storage: str
    storageClass: str


class TkgsVsphereWorkloadClusterSpec(BaseModel):
    tkgsVsphereNamespaceName: str
    tkgsVsphereWorkloadClusterName: str
    tkgsVsphereWorkloadClusterVersion: str
    tkgsVsphereWorkloadClusterKind: str
    allowedStorageClasses: List[str]
    defaultStorageClass: str
    nodeStorageClass: str
    serviceCidrBlocks: str
    podCidrBlocks: str
    controlPlaneVmClass: str
    workerVmClass: str
    workerNodeCount: str
    enableControlPlaneHa: str
    tkgWorkloadTsmIntegration: str
    namespaceExclusions: NamespaceExclusions
    tkgsWorkloadClusterGroupName: str
    tkgsWorkloadEnableDataProtection: str
    tkgWorkloadClusterCredential: str
    tkgWorkloadClusterBackupLocation: str
    controlPlaneVolumes: List[VolumesSpec]
    workerVolumes: List[VolumesSpec]
    tkgWorkloadClusterVeleroDataProtection: TkgWorkloadClusterVeleroDataProtection


class NamespaceStorage(BaseModel):
    def __getitem__(self, x):
        return getattr(self, x)

    storagePolicy: str


class TkgsVsphereNamespaceSpec(BaseModel):
    tkgsVsphereNamespaceName: str
    tkgsVsphereNamespaceDescription: str
    tkgsVsphereNamespaceContentLibrary: str
    tkgsVsphereNamespaceVmClasses: List[str]
    tkgsVsphereNamespaceResourceSpec: TkgsVsphereNamespaceResourceSpec
    tkgsVsphereNamespaceStorageSpec: List[NamespaceStorage]
    tkgsVsphereWorkloadClusterSpec: TkgsVsphereWorkloadClusterSpec


class ProxySpec(BaseModel):
    enableProxy: str
    httpProxy: str
    httpsProxy: str
    noProxy: str
    proxyCert: str


class AdditionalTrustedCAs(BaseModel):
    paths: List[str]
    endpointUrls: List[str]


class TkgServiceConfig(BaseModel):
    proxySpec: ProxySpec
    defaultCNI: str
    additionalTrustedCAs: AdditionalTrustedCAs


class TkgsWorkloadNetwork(BaseModel):
    tkgsWorkloadNetworkName: str
    tkgsWorkloadPortgroupName: str
    tkgsWorkloadNetworkGatewayCidr: str
    tkgsWorkloadNetworkStartRange: str
    tkgsWorkloadNetworkEndRange: str
    tkgsWorkloadServiceCidr: str


class TkgsComponentSpec(BaseModel):
    tkgsWorkloadNetwork: TkgsWorkloadNetwork
    tkgsVsphereNamespaceSpec: TkgsVsphereNamespaceSpec
    tkgServiceConfig: TkgServiceConfig


class Monitoring(BaseModel):
    enableLoggingExtension: str
    prometheusFqdn: str
    prometheusCertPath: str
    prometheusCertKeyPath: str
    grafanaFqdn: str
    grafanaCertPath: str
    grafanaCertKeyPath: str
    grafanaPasswordBase64: str


class SyslogEndpoint(BaseModel):
    enableSyslogEndpoint: str
    syslogEndpointAddress: str
    syslogEndpointPort: str
    syslogEndpointMode: str
    syslogEndpointFormat: str


class HttpEndpoint(BaseModel):
    enableHttpEndpoint: str
    httpEndpointAddress: str
    httpEndpointPort: str
    httpEndpointUri: str
    httpEndpointHeaderKeyValue: str


class KafkaEndpoint(BaseModel):
    enableKafkaEndpoint: str
    kafkaBrokerServiceName: str
    kafkaTopicName: str


class Logging(BaseModel):
    syslogEndpoint: SyslogEndpoint
    httpEndpoint: HttpEndpoint
    kafkaEndpoint: KafkaEndpoint


class HarborSpec(BaseModel):
    enableHarborExtension: str
    harborFqdn: str
    harborPasswordBase64: str
    harborCertPath: str
    harborCertKeyPath: str


class TanzuExtensions(BaseModel):
    enableExtensions: str
    tkgClustersName: str
    harborSpec: HarborSpec
    logging: Logging
    monitoring: Monitoring


class VsphereTkgsNameSpaceMasterSpec(BaseModel):
    envSpec: EnvSpec
    tkgsComponentSpec: TkgsComponentSpec
    tanzuExtensions: TanzuExtensions
