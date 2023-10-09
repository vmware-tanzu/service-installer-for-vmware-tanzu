import base64
from http import HTTPStatus

from flask import current_app, request

from common.cleanup.cleanup_constants import Cleanup, VCenter
from common.common_utilities import isEnvTkgm, isEnvTkgs_ns, isEnvTkgs_wcp
from common.operation.constants import Env, ResourcePoolAndFolderName, Type
from common.session.session_acquire import fetch_vmc_env
from common.util.request_api_util import RequestApiUtil

__author__ = "Pooja Deshmukh"


def getVcenterConfig(env, spec):
    if env == Env.VSPHERE or env == Env.VCF:
        vCenter = spec.envSpec.vcenterDetails.vcenterAddress
        vCenter_user = spec.envSpec.vcenterDetails.vcenterSsoUser
        str_enc = str(spec.envSpec.vcenterDetails.vcenterSsoPasswordBase64)
        base64_bytes = str_enc.encode("ascii")
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode("ascii").rstrip("\n")
        vCenter_datacenter = spec.envSpec.vcenterDetails.vcenterDatacenter
        vCenter_cluster = spec.envSpec.vcenterDetails.vcenterCluster
        if isEnvTkgs_ns(env) or isEnvTkgs_wcp(env):
            parent_rp = None
        else:
            parent_rp = spec.envSpec.vcenterDetails.resourcePoolName
            management_cluster = spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
            if env == Env.VCF:
                shared_cluster = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceClusterName
            else:
                shared_cluster = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceClusterName
            workload_cluster = spec.tkgWorkloadComponents.tkgWorkloadClusterName

    elif env == Env.VMC:
        status = fetch_vmc_env(request.get_json(force=True))
        if status[1] != 200:
            message = "Failed to capture VMC setup details"
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        vCenter = current_app.config["VC_IP"]
        vCenter_user = current_app.config["VC_USER"]
        VC_PASSWORD = current_app.config["VC_PASSWORD"]
        if not (vCenter or vCenter_user or VC_PASSWORD):
            message = "Failed to capture VMC setup details"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
        vCenter_datacenter = spec.envSpec.sddcDatacenter
        vCenter_cluster = spec.envSpec.sddcCluster
        parent_rp = spec.envSpec.resourcePoolName
        if isEnvTkgm(env):
            management_cluster = spec.componentSpec.tkgMgmtSpec.tkgMgmtClusterName
            shared_cluster = spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterName
            workload_cluster = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterName

    VC = {
        VCenter.vCenter: vCenter,
        VCenter.user: vCenter_user,
        VCenter.PASSWORD: VC_PASSWORD,
        VCenter.datacenter: vCenter_datacenter,
        VCenter.cluster: vCenter_cluster,
        VCenter.parent_rp: parent_rp,
    }
    if isEnvTkgm(env):
        VC[VCenter.management_cluster] = management_cluster
        VC[VCenter.shared_cluster] = shared_cluster
        VC[VCenter.workload_cluster] = workload_cluster

    return VC, HTTPStatus.OK


def validateTKGsFile(env, cleanup):
    """
    Method to validate json for tkgs env for cleanup
    """
    if isEnvTkgs_wcp(env):
        if (
            cleanup == Cleanup.EXTENSION
            or cleanup == Cleanup.TKG_WORKLOAD_CLUSTER
            or cleanup == Cleanup.SUPERVISOR_NAMESPACE
        ):
            message = "Wrong file provided, Please specify namespace file for extension, tkgs workload cluster and namespace deletion"
            current_app.logger.warn(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    if isEnvTkgs_ns(env):
        if cleanup == Cleanup.AVI or cleanup == Cleanup.DISABLE_WCP:
            message = "Wrong file provided, Please specify wcp file for Avi and disabling wcp."
            current_app.logger.warn(message)
            return RequestApiUtil.send_error(message), HTTPStatus.INTERNAL_SERVER_ERROR
    message = "Env file validated succesfully"
    current_app.logger.info(message)
    return RequestApiUtil.send_ok(message), HTTPStatus.OK


def get_cluster_names(env, spec):
    """
    param: env
    Method to get cluster names based on env
    returns clusters dict containing key value pair of cluster names
    """
    if env == Env.VMC:
        management_cluster = spec.componentSpec.tkgMgmtSpec.tkgMgmtClusterName
        shared_cluster = spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterName
        workload_cluster = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterName
    elif env == Env.VSPHERE:
        management_cluster = spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
        shared_cluster = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceClusterName
        workload_cluster = spec.tkgWorkloadComponents.tkgWorkloadClusterName
    elif env == Env.VCF:
        management_cluster = spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtClusterName
        shared_cluster = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceClusterName
        workload_cluster = spec.tkgWorkloadComponents.tkgWorkloadClusterName

    clusters = {Type.MANAGEMENT: management_cluster, Type.SHARED: shared_cluster, Type.WORKLOAD: workload_cluster}
    return clusters


def get_required_resource_folder_pool(env):
    """
    :param env
    Method to get list of resource pools and folders names for env
    :returns dict of delete_pool and folders
    """
    # modifying vcf to vsphere , boht have same delete_pool and folders values
    if env == Env.VCF:
        env = Env.VSPHERE
    delete_pool = {
        Env.VMC: {
            Type.AVI: ResourcePoolAndFolderName.AVI_Components_FOLDER,
            Type.MANAGEMENT: ResourcePoolAndFolderName.TKG_Mgmt_RP,
            Type.SHARED: ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME,
            Type.WORKLOAD: ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL,
        },
        Env.VSPHERE: {
            Type.AVI: ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE,
            Type.MANAGEMENT: ResourcePoolAndFolderName.TKG_Mgmt_RP_VSPHERE,
            Type.SHARED: ResourcePoolAndFolderName.SHARED_RESOURCE_POOL_NAME_VCENTER,
            Type.WORKLOAD: ResourcePoolAndFolderName.WORKLOAD_RESOURCE_POOL_VSPHERE,
        },
    }

    folders = {
        Env.VMC: {
            Type.AVI: ResourcePoolAndFolderName.AVI_Components_FOLDER,
            Type.MANAGEMENT: ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder,
            Type.SHARED: ResourcePoolAndFolderName.SHARED_FOLDER_NAME,
            Type.WORKLOAD: ResourcePoolAndFolderName.WORKLOAD_FOLDER,
        },
        Env.VSPHERE: {
            Type.AVI: ResourcePoolAndFolderName.AVI_Components_FOLDER_VSPHERE,
            Type.MANAGEMENT: ResourcePoolAndFolderName.TKG_Mgmt_Components_Folder_VSPHERE,
            Type.SHARED: ResourcePoolAndFolderName.SHARED_FOLDER_NAME_VSPHERE,
            Type.WORKLOAD: ResourcePoolAndFolderName.WORKLOAD_FOLDER_VSPHERE,
        },
    }

    return {"delete_pool": delete_pool[env], "folders": folders[env]}
