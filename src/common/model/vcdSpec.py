from typing import Optional, List
from pydantic import BaseModel, Field, validator


class MarketplaceSpec(BaseModel):
    refreshToken: Optional[str]


class InfraComponents(BaseModel):
    dnsServersIp: Optional[str]
    ntpServers: Optional[str]


class VcdComponentSpec(BaseModel):
    vcdAddress: Optional[str]
    vcdSysAdminUserName: Optional[str]
    vcdSysAdminPasswordBase64: Optional[str]


class VcdSpec(BaseModel):
    vcdComponentSpec: Optional[VcdComponentSpec]


class VcenterDetails(BaseModel):
    vcenterAddress: Optional[str]
    vcenterSsoUser: Optional[str]
    vcenterSsoPasswordBase64: Optional[str]
    vcenterDatacenter: Optional[str]
    vcenterCluster: Optional[str]
    vcenterDatastore: Optional[str]
    contentLibraryName: Optional[str]
    aviOvaName: Optional[str]
    resourcePoolName: Optional[str]


class AviMgmtNetwork(BaseModel):
    aviMgmtNetworkName: Optional[str]


class AviComponentsSpec(BaseModel):
    aviUsername: Optional[str]
    aviPasswordBase64: Optional[str]
    aviBackupPassphraseBase64: Optional[str]
    enableAviHa: Optional[str]
    aviController01Ip: Optional[str]
    aviController01Fqdn: Optional[str]
    aviController02Ip: Optional[str]
    aviController02Fqdn: Optional[str]
    aviController03Ip: Optional[str]
    aviController03Fqdn: Optional[str]
    aviClusterIp: Optional[str]
    aviClusterFqdn: Optional[str]
    aviSize: Optional[str]
    aviCertPath: Optional[str]
    aviCertKeyPath: Optional[str]


class AviCtrlDeploySpec(BaseModel):
    deployAvi: Optional[str]
    vcenterDetails: Optional[VcenterDetails]
    aviMgmtNetwork: Optional[AviMgmtNetwork]
    aviComponentsSpec: Optional[AviComponentsSpec]
    aviVcdDisplayName: Optional[str]


class NsxDetails(BaseModel):
    nsxtAddress: Optional[str]
    nsxtUser: Optional[str]
    nsxtUserPasswordBase64: Optional[str]
    nsxtTier1SeMgmtName: Optional[str]
    nsxtOverlay: Optional[str]


class AviSeTier1Details(BaseModel):
    nsxtTier1SeMgmtNetworkName: Optional[str]
    nsxtOverlay: Optional[str]


class AviSeMgmtNetwork(BaseModel):
    aviSeMgmtNetworkName: Optional[str]
    aviSeMgmtNetworkGatewayCidr: Optional[str]
    aviSeMgmtNetworkDhcpStartRange: Optional[str]
    aviSeMgmtNetworkDhcpEndRange: Optional[str]


class AviNsxCloudSpec(BaseModel):
    configureAviNsxtCloud: Optional[str]
    nsxDetails: Optional[NsxDetails]
    aviNsxCloudName: Optional[str]
    vcenterDetails: Optional[VcenterDetails]
    aviSeTier1Details: Optional[AviSeTier1Details]
    aviSeMgmtNetwork: Optional[AviSeMgmtNetwork]
    nsxtCloudVcdDisplayName: Optional[str]


class NsxDetails(BaseModel):
    nsxtAddress: Optional[str]
    nsxtUser: Optional[str]
    nsxtUserPasswordBase64: Optional[str]


class AviNsxCloudSpec(BaseModel):
    configureAviNsxtCloud: Optional[str]
    nsxDetails: Optional[NsxDetails]
    aviNsxCloudName: Optional[str]
    vcenterDetails: Optional[VcenterDetails]
    aviSeTier1Details: Optional[AviSeTier1Details]
    aviSeMgmtNetwork: Optional[AviSeMgmtNetwork]
    nsxtCloudVcdDisplayName: Optional[str]


class SvcOrgSpec(BaseModel):
    svcOrgName: Optional[str]
    svcOrgFullName: Optional[str]


class SvcOrgCatalogSpec(BaseModel):
    cseOvaCatalogName: Optional[str]
    k8sTemplatCatalogName: Optional[str]


class SvcOrgVdcNetworkSpec(BaseModel):
    networkName: Optional[str]
    gatewayCIDR: Optional[str]
    staticIpPoolStartAddress: Optional[str]
    staticIpPoolEndAddress: Optional[str]
    primaryDNS: Optional[str]
    secondaryDNS: Optional[str]
    dnsSuffix: Optional[str]


class Tier0GatewaySpec(BaseModel):
    importTier0: Optional[str]
    tier0Router: Optional[str]
    tier0GatewayName: Optional[str]
    extNetGatewayCIDR: Optional[str]
    extNetStartIP: Optional[str]
    extNetEndIP: Optional[str]


class Tier1GatewaySpec(BaseModel):
    tier1GatewayName: Optional[str]
    isDedicated: Optional[str]
    primaryIp: Optional[str]
    ipAllocationStartIP: Optional[str]
    ipAllocationEndIP: Optional[str]


class SvcOrgVdcGatewaySpec(BaseModel):
    tier0GatewaySpec: Optional[Tier0GatewaySpec]
    tier1GatewaySpec: Optional[Tier1GatewaySpec]


class VcenterPlacementDetails(BaseModel):
    vcenterDatacenter: Optional[str]
    vcenterCluster: Optional[str]
    vcenterDatastore: Optional[str]
    vcenterContentSeLibrary: Optional[str]

class ServiceEngineGroup(BaseModel):
    createSeGroup: Optional[str]
    serviceEngineGroupName: Optional[str]
    serviceEngineGroupVcdDisplayName: Optional[str]
    reservationType: Optional[str]
    supportedFeatureSet: Optional[str]
    vcenterPlacementDetails: Optional[VcenterPlacementDetails]


class StoragePolicies(BaseModel):
    storagePolicy: Optional[str]
    storageLimit: Optional[int]


class StoragePolicySpec(BaseModel):
    storagePolicies: Optional[List[StoragePolicies]]
    defaultStoragePolicy: Optional[str]


class SvcOrgVdcResourceSpec(BaseModel):
    providerVDC: Optional[str]
    cpuAllocation: Optional[int]
    cpuGuaranteed: Optional[int]
    memoryAllocation: Optional[int]
    memoryGuaranteed: Optional[int]
    vcpuSpeed: Optional[int]
    isElastic: Optional[str]
    includeMemoryOverhead: Optional[str]
    vmQuota: Optional[int]
    storagePolicySpec: Optional[StoragePolicySpec]
    thinProvisioning: Optional[str]
    fastProvisioning: Optional[str]
    networkPoolName: Optional[str]
    networkQuota: Optional[int]


class SvcOrgVdcSpec(BaseModel):
    svcOrgVdcName: Optional[str]
    svcOrgVdcResourceSpec: Optional[SvcOrgVdcResourceSpec]
    serviceEngineGroup: Optional[ServiceEngineGroup]
    svcOrgVdcGatewaySpec: Optional[SvcOrgVdcGatewaySpec]
    svcOrgVdcNetworkSpec: Optional[SvcOrgVdcNetworkSpec]
    svcOrgCatalogSpec: Optional[SvcOrgCatalogSpec]


class CustomCseProperties(BaseModel):
    cseSvcAccountName: Optional[str]
    cseSvcAccountPasswordBase64: Optional[str]


class CseServerDeploySpec(BaseModel):
    vAppName: Optional[str]
    customCseProperties: Optional[CustomCseProperties]


class CseSpec(BaseModel):
    svcOrgSpec: Optional[SvcOrgSpec]
    svcOrgVdcSpec: Optional[SvcOrgVdcSpec]
    cseServerDeploySpec: Optional[CseServerDeploySpec]


class EnvSpec(BaseModel):
    vcdSpec: Optional[VcdSpec]
    envType: Optional[str]
    marketplaceSpec: Optional[MarketplaceSpec]
    infraComponents: Optional[InfraComponents]
    ceipParticipation: Optional[str]
    aviCtrlDeploySpec: Optional[AviCtrlDeploySpec]
    aviNsxCloudSpec: Optional[AviNsxCloudSpec]
    cseSpec: Optional[CseSpec]


class VcdMasterSpec(BaseModel):
    envSpec: Optional[EnvSpec]
