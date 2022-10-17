#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import ipaddress
import iptools
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, validator
from pydantic.class_validators import root_validator

from constants.constants import CLUSTER_NODE_SIZES, CLUSTER_PLAN
from util.logger_helper import LoggerHelper

# https://pydantic-docs.helpmanual.io/usage/models/


logger = LoggerHelper.get_logger(Path(__file__).stem)


# validation
# https://pydantic-docs.helpmanual.io/usage/schema/


class Parameters(BaseModel):
    ip: str = Field(..., title="Ip Address", description="static ipv4 address for nsx-alb")
    gateway: str = Field(..., title="Gateway", description="")
    netmask: str = Field(..., title="Netmask", description="")


class VsphereVmc(BaseModel):
    orgName: str
    sddcName: str
    cspApiToken: str


class NetworkSegment(BaseModel):
    gatewayCidr: str
    dhcpStart: str
    dhcpEnd: str
    staticIpStart: Optional[str] = None
    staticIpEnd: Optional[str] = None

    @validator("gatewayCidr")
    def cidr_validator(cls, v: str):
        if not iptools.ipv4.validate_cidr(v):
            raise ValueError(f"Invalid IP address[{v}]. Provide a valid IP in CIDR format.")
        return v


class Deployment(BaseModel):
    datacenter: str
    datastore: str
    folder: str
    network: str
    resourcePool: str


class Deploy(Deployment):
    parameters: Optional[Parameters] = None


class DNSProfile(BaseModel):
    name: Optional[str] = Field(
        "tkg-alb-dns-profile", title="DNS profile name", description="Name for dns profile associated to ALB cloud"
    )
    domain: str


class Cloud(BaseModel):
    name: Optional[str] = Field(None, hidden=True)
    mgmtSEGroup: Optional[str] = Field(None, hidden=True)
    workloadSEGroupPrefix: Optional[str] = Field(None, hidden=True)
    ipamProfileName: Optional[str] = Field("tkg-alb-ipam-profile", hidden=True)
    dc: str
    network: str
    dnsProfile: DNSProfile


class DataNetwork(BaseModel):
    name: str
    cidr: str
    staticRange: str

    @validator("cidr")
    def cidr_validator(cls, v: str):
        ipaddress.ip_network(v)
        return v


class Backup(BaseModel):
    passphrase: str


class Cert(BaseModel):
    commonName: str


class Conf(BaseModel):
    dns: List[str]
    ntp: List[str]
    backup: Backup
    cert: Cert


class NsxAlb(BaseModel):
    vmName: str
    ovaPath: Optional[str]
    password: str
    deployment: Deploy
    segment: Optional[NetworkSegment] = None
    conf: Conf
    cloud: Cloud
    username: Optional[str] = Field("admin", hidden=True)
    dataNetwork: DataNetwork
    fqdn: Optional[str] = None


class Bind(BaseModel):
    dn: str
    password: str


class GroupSearch(BaseModel):
    baseDn: str = ""
    filter: str = ""
    groupAttribute: str = ""
    nameAttribute: str = ""
    userAttribute: str = ""


class UserSearch(BaseModel):
    baseDn: str = ""
    filter: str = ""
    nameAttribute: str = ""
    username: str = ""
    idAttribute: str = ""
    emailAttribute: str = ""


class LDAP(BaseModel):
    host: str
    rootCaBase64: str = ""
    bind: Bind
    groupSearch: GroupSearch
    userSearch: UserSearch


class Cluster(BaseModel):
    name: str
    plan: str
    size: str

    @validator("plan")
    def node_count_validator(cls, plan: str):
        if plan not in CLUSTER_PLAN:
            raise ValueError(f"Invalid plan specified[{plan}]. Available options: {CLUSTER_PLAN}")
        return plan

    @validator("size")
    def node_size_validator(cls, size: str):
        if size not in CLUSTER_NODE_SIZES:
            raise ValueError(f"Invalid size specified[{size}]. Available options: {CLUSTER_NODE_SIZES}")
        return size


class NodeConfig(BaseModel):
    endpoint: Optional[str]
    diskGib: int
    memoryMib: int
    cpus: int
    count: Optional[int] = None
    repave: Optional[bool] = False

    @validator("count")
    def node_count_validator(cls, v: str):
        if v < str(1):
            raise ValueError("node count should be greater than 1")
        return v

    @validator("endpoint")
    def validate_endpoint(cls, endpoint: str):
        if endpoint is not None:
            try:
                ipaddress.ip_address(endpoint)
            except Exception as e:
                logger.error("%s", e)
                raise ValueError(f"Invalid endpoint: {endpoint}, provide valid ip")
        return endpoint


class Mgmt(BaseModel):
    cluster: Cluster
    deployment: Deployment
    sshKey: str
    controlPlane: NodeConfig
    worker: NodeConfig
    segment: Optional[NetworkSegment] = None
    dataVipSegment: Optional[NetworkSegment] = None
    clusterVipSegment: Optional[NetworkSegment] = None
    ldap: Optional[LDAP] = None

    @root_validator(pre=True)
    def check_object(cls, v):
        cluster_name = v.get("cluster").get("name")
        if v.get("worker").get("endpoint") is not None:
            logger.warn("Invalid 'endpoint' key for worker configuration")
        # if re.match("ssh-rsa AAAA[0-9A-Za-z+/]+[=]{0,3} ", v.get("sshKey")) is None:
        #     raise ValueError("Provide correct ssh key")
        if re.match("^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$", cluster_name) is None:
            raise ValueError(
                f"""
                invalid cluster name {cluster_name}: must consist of lower case alphanumeric characters, '-' or '.',
                and must start and end with an alphanumeric character (e.g. 'example.com', 
                regex used for validation is '[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*')
                """
            )
        if v.get("controlPlane").get("repave") is not None or v.get("worker").get("repave") is not None:
            logger.warn("repave for management-cluster not available")
        return v


class HarborStorageSpec(BaseModel):
    datastore: str
    name: str


class HarborSpec(BaseModel):
    adminPassword: str
    hostname: str
    storage: Optional[HarborStorageSpec] = None

    @validator("adminPassword")
    def pass_length(cls, v: str):
        if len(v) < 16:
            raise ValueError("length of harbor password should be greater than 16")
        return v


class RFC2136DnsSpec(BaseModel):
    dnsServer: str
    domainName: str
    tsigKeyName: str
    tsigSecret: str


class SharedExtensions(BaseModel):
    externalDnsRfc2136: Optional[RFC2136DnsSpec] = None
    harbor: HarborSpec


class SharedServices(BaseModel):
    cluster: Cluster
    deployment: Deployment
    sshKey: str
    controlPlane: NodeConfig
    worker: NodeConfig
    segment: Optional[NetworkSegment] = None
    packagesTargetNamespace: Optional[str] = "my-packages"
    extensionsSpec: Optional[SharedExtensions] = None

    @root_validator(pre=True)
    def check_object(cls, v):
        worker = v.get("worker")
        cluster_name = v.get("cluster").get("name")
        control_plane = v.get("controlPlane")
        if worker.get("endpoint") is not None:
            logger.warn("Invalid 'endpoint' key for worker configuration")
        if control_plane.get("count") is not None and control_plane.get("count") % 2 == 0:
            raise ValueError("control-plane count has to be odd")
        # if re.match("ssh-rsa AAAA[0-9A-Za-z+/]+[=]{0,3} ", v.get("sshKey")) is None:
        #     raise ValueError("Provide correct ssh key")
        if re.match("^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$", cluster_name) is None:
            raise ValueError(
                f"""
                invalid cluster name {cluster_name}: must consist of lower case alphanumeric characters, '-' or '.',
                and must start and end with an alphanumeric character (e.g. 'example.com', 
                regex used for validation is '[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*')
                """
            )
        if v.get("controlPlane").get("repave") is not None:
            logger.warn("repave for control-plane not available")
        return v


class GrafanaSpec(BaseModel):
    adminPassword: str


class WorkloadExtensions(BaseModel):
    grafana: GrafanaSpec


class WorkloadCluster(BaseModel):
    cluster: Cluster
    deployment: Deployment
    sshKey: str
    controlPlane: NodeConfig
    worker: NodeConfig
    segment: Optional[NetworkSegment] = None
    dataVipSegment: Optional[NetworkSegment] = None
    packagesTargetNamespace: Optional[str] = "my-packages"
    extensionsSpec: Optional[WorkloadExtensions] = None

    @root_validator(pre=True)
    def check_object(cls, v):
        worker = v.get("worker")
        cluster_name = v.get("cluster").get("name")
        control_plane = v.get("controlPlane")

        if worker.get("endpoint") is not None:
            logger.warn("Invalid 'endpoint' key for worker configuration")
        if control_plane.get("count") is not None and control_plane.get("count") % 2 == 0:
            raise ValueError("control-plane count has to be odd")
        # if re.match("ssh-rsa AAAA[0-9A-Za-z+/]+[=]{0,3} ", v.get("sshKey")) is None:
        #     # https://gist.github.com/paranoiq/1932126
        #     raise ValueError("Provide correct ssh key")
        if re.match("^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$", cluster_name) is None:
            raise ValueError(
                f"""
                invalid cluster name {cluster_name}: must consist of lower case alphanumeric characters, '-' or '.',
                and must start and end with an alphanumeric character (e.g. 'example.com', 
                regex used for validation is '[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*')
                """
            )
        if v.get("controlPlane").get("repave") is not None:
            logger.warn("repave for control-plane not available")
        return v


class Proxy(BaseModel):
    http: str
    https: str
    noProxy: str


class NodeTemplateConfig(BaseModel):
    osName: str
    osVersion: str


class CommonTkgConfig(BaseModel):
    proxy: Optional[Proxy]
    node: Optional[NodeTemplateConfig]
    nodeOva: Optional[str] = Field(
        None,
        title="Node Ova",
        description="Provide node ova url. The node template will be loaded to vcenter if the template is missing.",
    )
    tmcRegistrationUrl: Optional[str] = Field(
        None,
        title="TMC Registration url",
        description="Register Your Management Cluster with Tanzu Mission Control using the url",
    )
    dnsServers: List[str]
    ntpServers: List[str]


class Tkg(BaseModel):
    common: Optional[CommonTkgConfig]
    management: Mgmt
    sharedService: SharedServices
    workloadClusters: Optional[List[WorkloadCluster]] = []


class Vsphere(BaseModel):
    server: str
    username: str
    password: str
    tlsThumbprint: str

    @root_validator(pre=True)
    def check_object(cls, v):
        if re.match("^([A-Z0-9][A-Z0-9][:])*[A-Z0-9][A-Z0-9]$", v.get("tlsThumbprint")) is None:
            raise ValueError(
                f"""
                Invalid tls thumbprint, generate thumbprint: 
                openssl x509 -noout -fingerprint -sha1 -inform pem -in <(openssl s_client -connect {v.get("server")}:443)
                """
            )
        return v


class Bootstrap(BaseModel):
    server: str
    username: str
    password: str


class Tmc(BaseModel):
    isEnabled: str = Field(default=False)
    apiToken: str
    clusterGroup: Optional[str] = None


class Integrations(BaseModel):
    tmc: Optional[Tmc]


class MasterSpec(BaseModel):
    bootstrap: Bootstrap
    vsphere: Vsphere
    # vmc: VsphereVmc
    tkg: Tkg
    #integrations: Integrations
    avi: NsxAlb
    onDocker: bool = Field(default=False, hidden=True)
    imageName: str = Field(default="10.202.233.205:80/library/tanzu-cli-image", hidden=True)
