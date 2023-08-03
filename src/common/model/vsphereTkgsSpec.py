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
    vcenterDatastore: Optional[str]


class TmcDetails(BaseModel):
    tmcAvailability: str
    tmcRefreshToken: str
    tmcInstanceURL: str
    tmcSupervisorClusterName: str
    tmcSupervisorClusterGroupName: Optional[str]


class TanzuObservabilityDetails(BaseModel):
    tanzuObservabilityAvailability: str
    tanzuObservabilityUrl: str
    tanzuObservabilityRefreshToken: str


class SaasEndpoints(BaseModel):
    tmcDetails: TmcDetails
    tanzuObservabilityDetails: Optional[TanzuObservabilityDetails]


class InfraComponents(BaseModel):
    dnsServersIp: str
    searchDomains: str
    ntpServers: str


class EnvSpec(BaseModel):
    vcenterDetails: VcenterDetails
    envType: Optional[str]
    saasEndpoints: SaasEndpoints
    infraComponents: Optional[InfraComponents]


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
    aviController02Ip: Optional[str]
    aviController02Fqdn: Optional[str]
    aviController03Ip: Optional[str]
    aviController03Fqdn: Optional[str]
    aviClusterIp: Optional[str]
    aviClusterFqdn: Optional[str]


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
    subscribedContentLibraryName: str


class TkgsPrimaryWorkloadNetwork(BaseModel):
    tkgsPrimaryWorkloadPortgroupName: str
    tkgsPrimaryWorkloadNetworkGatewayCidr: str
    tkgsPrimaryWorkloadNetworkStartRange: str
    tkgsPrimaryWorkloadNetworkEndRange: str
    tkgsPrimaryWorkloadNetworkName: str
    tkgsWorkloadDnsServers: str
    tkgsWorkloadNtpServers: str
    tkgsWorkloadServiceCidr: str


class TkgsStoragePolicySpec(BaseModel):
    masterStoragePolicy: str
    ephemeralStoragePolicy: str
    imageStoragePolicy: str


class TkgsVsphereNamespaceResourceSpec(BaseModel):
    cpuLimit: Optional[int]
    memoryLimit: Optional[int]
    storageRequestLimit: Optional[int]


class TkgsVsphereWorkloadClusterSpec(BaseModel):
    tkgsVsphereNamespaceName: str
    tkgsVsphereWorkloadClusterKind: str
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


class TkgsVsphereNamespaceSpec(BaseModel):
    tkgsVsphereNamespaceName: str
    tkgsVsphereNamespaceDescription: str
    tkgsVsphereNamespaceWorkloadNetwork: Optional[str]
    tkgsVsphereNamespaceContentLibrary: str
    tkgsVsphereNamespaceVmClasses: List[str]
    tkgsVsphereNamespaceResourceSpec: TkgsVsphereNamespaceResourceSpec
    tkgsVsphereWorkloadClusterSpec: TkgsVsphereWorkloadClusterSpec


class NamespaceStorage(BaseModel):
    storageLimit: int
    storagePolicy: str


class TkgsVsphereNamespaceStorageSpec(BaseModel):
    List[NamespaceStorage]


class TkgsComponentSpec(BaseModel):
    controlPlaneSize: Optional[str]
    tkgsContentLibrary: Optional[str]
    aviMgmtNetwork: Optional[AviMgmtNetwork]
    aviComponents: Optional[AviComponents]
    tkgsVipNetwork: Optional[TkgsVipNetwork]
    tkgsMgmtNetworkSpec: Optional[TkgsMgmtNetworkSpec]
    tkgsPrimaryWorkloadNetwork: Optional[TkgsPrimaryWorkloadNetwork]
    tkgsStoragePolicySpec: Optional[TkgsStoragePolicySpec]
    tkgsVsphereNamespaceSpec: Optional[TkgsVsphereNamespaceSpec]
    tkgsVsphereNamespaceStorageSpec: Optional[TkgsVsphereNamespaceStorageSpec]


class VsphereTkgsMasterSpec(BaseModel):
    envSpec: Optional[EnvSpec]
    tkgsComponentSpec: Optional[TkgsComponentSpec]
