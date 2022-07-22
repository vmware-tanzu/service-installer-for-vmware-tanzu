from typing import Optional, List
from pydantic import BaseModel, Field, validator


class VcenterDetails(BaseModel):
    vcenterAddress: str
    vcenterSsoUser: str
    vcenterSsoPasswordBase64: str
    vcenterDatacenter: str
    vcenterCluster: str
    vcenterDatastore: str


class ResourceSpec(BaseModel):
    customerConnectUser: str
    customerConnectPasswordBase64: str
    aviPulseJwtToken: str


class TmcDetails(BaseModel):
    tmcAvailability: str
    tmcRefreshToken: str
    tmcSupervisorClusterName: str


class TanzuObservabilityDetails(BaseModel):
    tanzuObservabilityAvailability: str
    tanzuObservabilityUrl: str
    tanzuObservabilityRefreshToken: str


class SaasEndpoints(BaseModel):
    tmcDetails: TmcDetails
    tanzuObservabilityDetails: TanzuObservabilityDetails


class InfraComponents(BaseModel):
    dnsServersIp: str
    searchDomains: str
    ntpServers: str


class EnvSpec(BaseModel):
    vcenterDetails: VcenterDetails
    envType: Optional[str]
    resourceSpec: ResourceSpec
    saasEndpoints: SaasEndpoints
    infraComponents: InfraComponents


class AviMgmtNetwork(BaseModel):
    aviMgmtNetworkName: str
    aviMgmtNetworkGatewayCidr: str
    aviMgmtServiceIpStartRange: str
    aviMgmtServiceIpEndRange: str


class AviComponents(BaseModel):
    aviPasswordBase64: str
    aviBackupPassphraseBase64: str
    aviController01Ip: str
    aviController01Fqdn: str


class TkgsVipNetwork(BaseModel):
    tkgsVipNetworkName: str
    tkgsVipNetworkGatewayCidr: str
    tkgsVipIpStartRange: str
    tkgsVipIpEndRange: str


class TkgsMgmtNetworkSpec(BaseModel):
    tkgsMgmtNetworkName: str
    tkgsMgmtNetworkGatewayCidr: str
    tkgsMgmtNetworkStartingIp: str
    tkgsMgmtNetworkDnsServers: str
    tkgsMgmtNetworkSearchDomains: str
    tkgsMgmtNetworkNtpServers: str


class TkgsPrimaryWorkloadNetwork(BaseModel):
    tkgsPrimaryWorkloadPortgroupName: str
    tkgsPrimaryWorkloadNetworkGatewayCidr: str
    tkgsPrimaryWorkloadNetworkStartRange: str
    tkgsPrimaryWorkloadNetworkEndRange: str
    tkgsWorkloadDnsServers: str
    tkgsWorkloadServiceCidr: str


class TkgsStoragePolicySpec(BaseModel):
    masterStoragePolicy: str
    ephemeralStoragePolicy: str
    imageStoragePolicy: str


class TkgsVsphereNamespaceResourceSpec(BaseModel):
    cpuLimit: int
    memoryLimit: int
    storageRequestLimit: int


class TkgsVsphereNamespaceSpec(BaseModel):
    tkgsVsphereNamespaceName: str
    tkgsVsphereNamespaceDescription: str
    tkgsVsphereNamespaceWorkloadNetwork: str
    tkgsVsphereNamespaceContentLibrary: str
    tkgsVsphereNamespaceVmClasses: List[str]
    tkgsVsphereNamespaceResourceSpec: TkgsVsphereNamespaceResourceSpec


class NamespaceStorage(BaseModel):
    storageLimit: int
    storagePolicy: str


class TkgsVsphereNamespaceStorageSpec(BaseModel):
    List[NamespaceStorage]


class TkgsVsphereWorkloadClusterSpec(BaseModel):
    tkgsVsphereNamespaceName: str
    tkgsVsphereWorkloadClusterName: str
    allowedStorageClasses: List[str]
    defaultStorageClass: str
    nodeStorageClass: str
    serviceCidrBlocks: str
    podCidrBlocks: str
    controlPlaneVmClass: str
    workerVmClass: str
    workerNodeCount: str
    enableControlPlaneHa: str


class TkgsComponentSpec(BaseModel):
    controlPlaneSize: str
    tkgsContentLibrary: str
    aviMgmtNetwork: AviMgmtNetwork
    aviComponents: AviComponents
    tkgsVipNetwork: TkgsVipNetwork
    tkgsMgmtNetworkSpec: TkgsMgmtNetworkSpec
    tkgsPrimaryWorkloadNetwork: TkgsPrimaryWorkloadNetwork
    tkgsStoragePolicySpec: TkgsStoragePolicySpec
    tkgsVsphereNamespaceSpec: TkgsVsphereNamespaceSpec
    tkgsVsphereNamespaceStorageSpec: TkgsVsphereNamespaceStorageSpec
    tkgsVsphereWorkloadClusterSpec: TkgsVsphereWorkloadClusterSpec


class VsphereTkgsMasterSpec(BaseModel):
    envSpec: Optional[EnvSpec]
    tkgsComponentSpec: Optional[TkgsComponentSpec]
