# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
import os

from flask import current_app
from jinja2 import Template

from common.certificate_base64 import getBase64CertWriteToFile
from common.common_utilities import (
    checkAirGappedIsEnabled,
    checkEnableIdentityManagement,
    getVCthumbprint,
    grabHostFromUrl,
    grabPortFromUrl,
)
from common.operation.constants import AkoType, Env, Paths, Tkg_version
from common.util.cluster_yaml_data_util import VCFDeployData, VDSDeployData, VMCDeployData
from common.util.file_helper import FileHelper
from common.util.kubectl_util import KubectlUtil


class ClusterYaml:
    def __init__(self, env, spec):
        self.env = env
        self.spec = spec
        self.object_mapping = {Env.VMC: VMCDeployData, Env.VCF: VCFDeployData, Env.VSPHERE: VDSDeployData}

    def _cluster_data_object(self, cluster_type):
        return self.object_mapping[self.env](self.spec, cluster_type)

    def generate_cluster_yaml(
        self,
        cluster_name,
        cluster_plan,
        data_center,
        data_store_path,
        folder_path,
        mgmt_network,
        vsphere_password,
        shared_cluster_resource_pool,
        vsphere_server,
        ssh_key,
        vsphere_user_name,
        machine_count,
        size,
        cluster_type,
    ):
        cluster_object = self._cluster_data_object(cluster_type=cluster_type)
        current_app.logger.debug(cluster_object)
        t = Template(cluster_object.yaml_template)
        yaml_output_path = os.path.join(Paths.CLUSTER_PATH, cluster_name, cluster_name + ".yaml")
        data_center = "/" + data_center
        air_gapped_repo = ""
        repo_certificate = ""
        if checkEnableIdentityManagement(self.env):
            identity_mgmt_type = cluster_object.identity_mgmt_type
        else:
            identity_mgmt_type = ""
        if checkAirGappedIsEnabled(self.env):
            air_gapped_repo = self.spec.envSpec.customRepositorySpec.tkgCustomImageRepository
            air_gapped_repo = air_gapped_repo.replace("https://", "").replace("http://", "")
            os.putenv("TKG_BOM_IMAGE_TAG", Tkg_version.TAG)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY", air_gapped_repo)
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY", "False")
            getBase64CertWriteToFile(grabHostFromUrl(air_gapped_repo), grabPortFromUrl(air_gapped_repo))
            with open("cert.txt", "r") as file2:
                repo_cert = file2.readline()
            repo_certificate = repo_cert
            os.putenv("TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE", repo_certificate)
        vsphere_thumb_print = getVCthumbprint()
        FileHelper.write_to_file(
            t.render(
                config=self.spec,
                clustercidr=cluster_object.cluster_data.cluster_cidr,
                sharedClusterName=cluster_name,
                clusterPlan=cluster_plan,
                servicecidr=cluster_object.cluster_data.service_cidr,
                datacenter=data_center,
                dataStorePath=data_store_path,
                avi_label_key=AkoType.KEY,
                avi_label_value=cluster_object.cluster_data.ako_name,
                folderPath=folder_path,
                ceip=cluster_object.ceip,
                isProxyCert=cluster_object.is_proxy_cert,
                proxyCert=cluster_object.proxy_cert,
                mgmt_network=mgmt_network,
                vspherePassword=vsphere_password,
                sharedClusterResourcePool=shared_cluster_resource_pool,
                vsphereServer=vsphere_server,
                sshKey=ssh_key,
                vsphereUseName=vsphere_user_name,
                controlPlaneSize=size,
                machineCount=machine_count,
                workerSize=size,
                type=cluster_type,
                air_gapped_repo=air_gapped_repo,
                repo_certificate=repo_certificate,
                osName=cluster_object.cluster_data.os_name,
                osVersion=cluster_object.cluster_data.os_version,
                size=cluster_object.cluster_data.cluster_size,
                control_plane_vcpu=cluster_object.cluster_data.cpu_size,
                control_plane_disk_gb=cluster_object.cluster_data.disk_size,
                control_plane_mem_mb=cluster_object.cluster_data.control_plane_mem_mb,
                identity_mgmt_type=identity_mgmt_type,
                tkg_version=Tkg_version.TKG_VERSION,
                vsphere_tls_thumbprint=vsphere_thumb_print,
            ),
            yaml_output_path,
        )
        kubectl_util = KubectlUtil()
        tkr = kubectl_util.get_kube_version_full_name(cluster_object.cluster_data.kube_version, get_name=True)
        return tkr[0]
