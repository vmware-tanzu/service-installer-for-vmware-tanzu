import ipaddress
import os
import time

import ruamel
from flask import current_app, jsonify

from common.common_utilities import (
    checkAirGappedIsEnabled,
    checkAviL7EnabledForShared,
    checkAviL7EnabledForWorkload,
    createClusterFolder,
    envCheck,
)
from common.lib.avi.avi_infra_operations import AVIInfraOps
from common.operation.constants import AkoType, AppName, Cloud, Env, Paths, Type
from common.operation.ShellHelper import grabPipeOutput, runShellCommandAndReturnOutputAsList
from common.util.common_utils import CommonUtils
from common.util.tanzu_util import TanzuUtil

__author__ = "Pooja Deshmukh"


class AkoConfigConstants:
    VSPHERE_VCF_SHARED_AKO_FILE_NAME = "tkgvsphere-ako-shared-services-cluster.yaml"
    VSPHERE_VCF_WORKLOAD_AKO_FILE_NAME = "ako_vsphere_workloadset1.yaml"
    VSPHERE_VCF_SHARED_AKO_NAME = "install-ako-for-shared-services-cluster"
    VSPHERE_VCF_WORKLOAD_AKO_NAME = "install-ako-for-workload-set01"


class AkoConfigUtils:
    def __init__(self, spec, cluster_type, avi_fqdn, password_avi, vcenter_ip, vcenter_username, password):
        self.cluster_type = cluster_type
        self.spec = spec
        env = envCheck()
        if env[1] != 200:
            message = f"Wrong env provided {env[0]}"
            current_app.logger.error(message)
            raise Exception(str(message))
        self.env = env[0]
        self.AviInfraObj = AVIInfraOps(avi_fqdn, password_avi, vcenter_ip, vcenter_username, password)

    def create_ako_file(
        self,
        ip,
        cluster_name,
        tkgMgmtDataVipCidr,
        tkgMgmtDataPg,
        cluster_vip_name,
        cluster_network,
        cluster_vip_cidr,
        tier1_path,
    ):
        if checkAirGappedIsEnabled(self.env):
            air_gapped_repo = str(self.spec.envSpec.customRepositorySpec.tkgCustomImageRepository)
            air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
        cloud_name = Cloud.CLOUD_NAME_VSPHERE
        cluster_nw = dict(networkName=cluster_network)
        lis_ = [cluster_nw]
        if self.cluster_type == Type.SHARED:
            se_cloud = Cloud.SE_GROUP_NAME_VSPHERE
            lis_avi7 = lis_
        elif self.cluster_type == Type.WORKLOAD:
            se_cloud = Cloud.SE_WORKLOAD_GROUP_NAME_VSPHERE
            # TODO: modify it for gateway_address
            net = self.spec.tkgWorkloadComponents.tkgWorkloadGatewayCidr
            network = str(ipaddress.IPv4Network(net, strict=False))
            list_cidrs = [network]
            workload_nw_avi7 = dict(networkName=cluster_network, cidrs=list_cidrs)
            lis_avi7 = [workload_nw_avi7]

        if self.check_aviL7_enabled_for_cluster():
            extra_config = dict(
                cniPlugin="antrea",
                disableStaticRouteSync=True,
                ingress=dict(
                    disableIngressClass=False,
                    defaultIngressController=False,
                    nodeNetworkList=lis_avi7,
                    serviceType="NodePortLocal",
                    shardVSSize="MEDIUM",
                ),
            )
            if self.env == Env.VCF:
                se_cloud = se_cloud.replace("vsphere", "nsxt")
                cloud_name = cloud_name.replace("vsphere", "nsxt")
                extra_config = dict(
                    cniPlugin="antrea",
                    disableStaticRouteSync=True,
                    l4Config=dict(autoFQDN="disabled"),
                    layer7Only=False,
                    networksConfig=dict(enableRHI=False, nsxtT1LR=tier1_path),
                    ingress=dict(
                        disableIngressClass=False,
                        nodeNetworkList=lis_,
                        serviceType="NodePortLocal",
                        shardVSSize="MEDIUM",
                    ),
                )
        else:
            extra_config = dict(
                cniPlugin="antrea",
                disableStaticRouteSync=True,
                ingress=dict(defaultIngressController=False, disableIngressClass=True, nodeNetworkList=lis_),
            )
            if self.env == Env.VCF:
                se_cloud = se_cloud.replace("vsphere", "nsxt")
                cloud_name = cloud_name.replace("vsphere", "nsxt")
                extra_config = dict(
                    cniPlugin="antrea",
                    disableStaticRouteSync=True,
                    l4Config=dict(autoFQDN="disabled"),
                    layer7Only=False,
                    networksConfig=dict(enableRHI=False, nsxtT1LR=tier1_path),
                    ingress=dict(defaultIngressController=True, disableIngressClass=True, nodeNetworkList=lis_),
                )

        data = dict(
            apiVersion="networking.tkg.tanzu.vmware.com/v1alpha1",
            kind="AKODeploymentConfig",
            metadata=dict(
                generation=2,
                name=self.fetch_ako_name(),
            ),
            spec=dict(
                adminCredentialRef=dict(name="avi-controller-credentials", namespace="tkg-system-networking"),
                certificateAuthorityRef=dict(name="avi-controller-ca", namespace="tkg-system-networking"),
                cloudName=cloud_name,
                clusterSelector=dict(matchLabels=dict(type=self.fetch_ako_label_for_cluster())),
                controller=ip,
                controlPlaneNetwork=dict(cidr=cluster_vip_cidr, name=cluster_vip_name),
                dataNetwork=dict(cidr=tkgMgmtDataVipCidr, name=tkgMgmtDataPg),
                extraConfigs=extra_config,
                serviceEngineGroup=se_cloud,
            ),
        )
        filePath = os.path.join(Paths.CLUSTER_PATH, cluster_name, self.fetch_ako_yaml_file_name())
        with open(filePath, "w") as outfile:
            yaml = ruamel.yaml.YAML()
            yaml.indent(mapping=2, sequence=4, offset=3)
            yaml.dump(data, outfile)

    def ako_deployment_config_for_cluster(self, avi_ip, management_cluster, cluster_name, cluster_network):
        # common function for VDS, NSX-T and VMC
        cmd_status = TanzuUtil.switch_to_management_context(management_cluster)
        if cmd_status[1] != 200:
            current_app.logger.error("Failed to get switch to management cluster context " + str(cmd_status[0]))
            raise Exception("Failed to get switch to management cluster context " + str(cmd_status[0]))
        podRunninng_ako_main = ["kubectl", "get", "pods", "-A"]
        podRunninng_ako_grep = ["grep", AppName.AKO]
        time.sleep(30)
        timer = 30
        ako_pod_running = False
        while timer < 600:
            current_app.logger.info("Check AKO pods are running. Waited for " + str(timer) + "s retrying")
            command_status_ako = grabPipeOutput(podRunninng_ako_main, podRunninng_ako_grep)
            if command_status_ako[1] != 0:
                time.sleep(30)
                timer = timer + 30
            else:
                ako_pod_running = True
                break
        if not ako_pod_running:
            current_app.logger.error("AKO pods are not running on waiting for 10m " + command_status_ako[0])
            raise Exception("AKO pods are not running on waiting for 10m " + str(command_status_ako[0]))

        if not createClusterFolder(cluster_name):
            raise Exception("Failed to create directory: " + str(Paths.CLUSTER_PATH + cluster_name))
        current_app.logger.info(
            "Checking if AKO Deployment Config already exists for Shared services cluster: " + cluster_name
        )
        command_main = ["kubectl", "get", "adc"]
        command_grep = ["grep", self.fetch_ako_name()]
        command_status_adc = grabPipeOutput(command_main, command_grep)
        if command_status_adc[1] == 0:
            current_app.logger.debug("Found an already existing AKO Deployment Config: " + self.fetch_ako_name())
            command = ["kubectl", "delete", "adc", self.fetch_ako_name()]
            status = runShellCommandAndReturnOutputAsList(command)
            if status[1] != 0:
                raise Exception("Failed to delete an already present AKO Deployment config")
        if self.env == Env.VSPHERE:
            self.vsphere_prepare_ako_config(avi_ip, cluster_name, cluster_network)
        if self.env == Env.VCF:
            self.vcf_prepare_ako_config(avi_ip, cluster_name, cluster_network)
        yaml_file_path = os.path.join(Paths.CLUSTER_PATH, cluster_name, self.fetch_ako_yaml_file_name())
        listOfCommand = ["kubectl", "create", "-f", yaml_file_path, "--validate=false"]
        status = runShellCommandAndReturnOutputAsList(listOfCommand)
        if status[1] != 0:
            if not str(status[0]).__contains__("already has a value"):
                current_app.logger.error("Failed to apply ako" + str(status[0]))
                raise Exception("Failed to create new AkoDeploymentConfig " + str(status[0]))
        current_app.logger.info("Successfully created a new AkoDeploymentConfig for shared services cluster")
        return True

    def vsphere_prepare_ako_config(self, avi_ip, cluster_name, cluster_network):
        try:
            tkg_cluster_vip_name = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
            tkg_mgmt_data_pg = self.spec.tkgMgmtDataNetwork.tkgMgmtDataNetworkName
            if self.cluster_type == Type.WORKLOAD:
                tkg_mgmt_data_pg = self.spec.tkgWorkloadDataNetwork.tkgWorkloadDataNetworkName
            tkg_mgmt_data_netmask = self.AviInfraObj.get_vip_network_ip_netmask(tkg_mgmt_data_pg)
            cluster_vip_cidr = self.AviInfraObj.get_vip_network_ip_netmask(tkg_cluster_vip_name)
            if cluster_vip_cidr[0] is None or cluster_vip_cidr[0] == "NOT_FOUND":
                current_app.logger.error("Failed to get Cluster VIP netmask")
                raise Exception("Failed to get Cluster VIP netmask")
            tier1 = ""
            self.create_ako_file(
                avi_ip,
                cluster_name,
                tkg_mgmt_data_netmask[0],
                tkg_mgmt_data_pg,
                tkg_cluster_vip_name,
                cluster_network,
                cluster_vip_cidr[0],
                tier1,
            )
        except Exception as e:
            error = "One of the following values is not present in input file: "
            "tkgMgmtDataNetworkName, tkgWorkloadDataNetwork, tkgClusterVipNetworkName"
            current_app.logger.error(error)
            raise Exception(error + str(e))

    def vcf_prepare_ako_config(self, avi_ip, cluster_name, cluster_network):
        try:
            tkg_cluster_vip_name = self.spec.tkgComponentSpec.tkgClusterVipNetwork.tkgClusterVipNetworkName
            tkg_cluster_network = tkg_cluster_vip_name
            if self.cluster_type == Type.WORKLOAD and CommonUtils.is_avi_non_orchestrated(self.spec):
                tkg_cluster_network = self.spec.tkgWorkloadDataNetwork.tkgWorkloadDataNetworkName
            cluster_vip_cidr = self.AviInfraObj.get_vip_network_ip_netmask(tkg_cluster_vip_name)
            if cluster_vip_cidr[0] is None or cluster_vip_cidr[0] == "NOT_FOUND":
                current_app.logger.error("Failed to get Cluster VIP netmask")
                d = {"responseType": "ERROR", "msg": "Failed to get Cluster VIP netmask", "STATUS_CODE": 500}
                return jsonify(d), 500
            tkg_network_cidr = self.AviInfraObj.get_vip_network_ip_netmask(tkg_cluster_network)
            status, value = self.AviInfraObj._get_cloud_connect_user()
            nsxt_cred = value["nsxUUid"]
            nsxt_tier1_route_name = str(self.spec.envSpec.vcenterDetails.nsxtTier1RouterDisplayName)
            nsxt_address = str(self.spec.envSpec.vcenterDetails.nsxtAddress)
            tier1_status, tier1_id = self.AviInfraObj.fetch_tier1_gateway_id(
                nsxt_cred, nsxt_tier1_route_name, nsxt_address
            )
            if tier1_status is None:
                current_app.logger.error("Failed to get Tier 1 details " + str(tier1_id))
                raise Exception("Failed to get Tier 1 details " + str(tier1_id))
            tier1 = tier1_id
            self.create_ako_file(
                avi_ip,
                cluster_name,
                tkg_network_cidr[0],
                tkg_cluster_network,
                tkg_cluster_vip_name,
                cluster_network,
                cluster_vip_cidr[0],
                tier1,
            )
        except Exception as ex:
            current_app.logger.error(ex)
            raise Exception(str(ex))

    def fetch_ako_yaml_file_name(self):
        if self.cluster_type == Type.SHARED:
            return AkoConfigConstants.VSPHERE_VCF_SHARED_AKO_FILE_NAME
        elif self.cluster_type == Type.WORKLOAD:
            return AkoConfigConstants.VSPHERE_VCF_WORKLOAD_AKO_FILE_NAME

    def fetch_ako_name(self):
        if self.cluster_type == Type.SHARED:
            return AkoConfigConstants.VSPHERE_VCF_SHARED_AKO_NAME
        elif self.cluster_type == Type.WORKLOAD:
            return AkoConfigConstants.VSPHERE_VCF_WORKLOAD_AKO_NAME

    def fetch_ako_label_for_cluster(self):
        if self.cluster_type == Type.WORKLOAD:
            return AkoType.WORKLOAD_CLUSTER_SELECTOR
        elif self.cluster_type == Type.SHARED:
            return AkoType.SHARED_CLUSTER_SELECTOR

    def check_aviL7_enabled_for_cluster(self):
        if self.cluster_type == Type.SHARED:
            return checkAviL7EnabledForShared(self.env)
        elif self.cluster_type == Type.WORKLOAD:
            return checkAviL7EnabledForWorkload(self.env)
