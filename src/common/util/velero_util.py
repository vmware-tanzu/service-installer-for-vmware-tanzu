# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause


__author__ = "Tasmiya Bano"

import json
import time
from http import HTTPStatus

from flask import current_app

from common.constants.constants import KubectlCommands
from common.constants.tmc_api_constants import TmcConstants, TmcPayloads, VeleroAPI
from common.lib.tkg_cli_client import TkgCliClient
from common.operation.constants import Env, Extension, Repo, Type
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
from common.util.common_utils import CommonUtils
from common.util.file_helper import FileHelper
from common.util.kubectl_util import KubectlUtil
from common.util.local_cmd_helper import LocalCmdHelper
from common.util.request_api_util import RequestApiUtil
from common.util.saas_util import SaaSUtil
from common.util.tkgs_util import TkgsUtil


class VeleroUtil:
    def __init__(self, env, spec):
        self.env = env
        self.spec = spec
        self.saas_util = SaaSUtil(self.env, self.spec)

    def enable_velero(self, type, cluster, mgmt_cluster):
        if self.saas_util.check_tmc_enabled():
            if TmcVelero.check_data_protection_enabled(self.env, self.spec, type):
                tmc_velero: TmcVelero = TmcVelero(self.env, self.spec)
                response = tmc_velero.enable_data_protection(cluster, mgmt_cluster)
                if response[0]:
                    return True
                else:
                    current_app.logger.error(response[1])
                    return False
        if StandaloneVelero.check_data_protection_enabled(self.env, self.spec, type):
            self.cluster_login(cluster)
            standalone_velero = StandaloneVelero(self.env, self.spec)
            response = standalone_velero.enable_data_protection(type)
            if response[0]:
                return True
            else:
                current_app.logger.error(response[1])
                return False
        current_app.logger.info(f"Data Protection is not enabled for cluster {cluster}")
        return True

    def cluster_login(self, cluster):
        if TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
            tkgs_util = TkgsUtil(self.spec)
            context_output = tkgs_util.login_to_cluster(cluster)
            if not context_output[0]:
                raise Exception(f"Failed to switch to {cluster} context")
        else:
            tkg_client = TkgCliClient(LocalCmdHelper())
            tkg_client.get_admin_context(cluster)
            context_command = KubectlUtil.SET_KUBECTL_CONTEXT.format(cluster=cluster)
            context_output = runShellCommandAndReturnOutputAsList(context_command)
            if context_output[1] != 0:
                raise Exception(f"Failed to switch to {cluster} context")
        current_app.logger.info(f"Switched to {cluster} context")


class TmcVelero:
    def __init__(self, env, spec):
        self.env = env
        self.spec = spec

        self.saas_util = SaaSUtil(self.env, self.spec)

    @staticmethod
    def check_data_protection_enabled(env, spec, type):
        if type == Type.SHARED:
            if env == Env.VMC:
                is_enabled = spec.componentSpec.tkgSharedServiceSpec.tkgSharedserviceEnableDataProtection
            elif env == Env.VCF:
                is_enabled = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceEnableDataProtection
            elif env == Env.VSPHERE:
                is_enabled = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceEnableDataProtection
        elif type == Type.WORKLOAD:
            if TkgsUtil.is_env_tkgs_ns(spec, env):
                is_enabled = (
                    spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsWorkloadEnableDataProtection
                )
            elif env == Env.VCF or env == Env.VSPHERE:
                is_enabled = spec.tkgWorkloadComponents.tkgWorkloadEnableDataProtection
            elif env == Env.VMC:
                is_enabled = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadEnableDataProtection
        if is_enabled.lower() == "true":
            return True
        else:
            return False

    def enable_data_protection(self, cluster, mgmt_cluster):
        try:
            current_app.logger.info("Enabling data protection on cluster " + cluster)
            url = VeleroAPI.GET_CLUSTER_INFO.format(tmc_url=self.saas_util.tmc_url, cluster=cluster)

            if TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
                provisioner_name = (
                    self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsVsphereNamespaceName
                )
            else:
                provisioner_name = "default"

            param = {"full_name.managementClusterName": mgmt_cluster, "full_name.provisionerName": provisioner_name}

            response = RequestApiUtil.exec_req("GET", url, headers=SaaSUtil.tmc_header, params=param, verify=False)
            if not RequestApiUtil.verify_resp(response, HTTPStatus.OK):
                current_app.logger.error(response)
                return False, "Failed to fetch cluster details to enable data protection"

            org_id = response.json()["cluster"]["fullName"]["orgId"]
            url = VeleroAPI.ENABLE_DP.format(tmc_url=self.saas_util.tmc_url, cluster=cluster)

            payload = TmcPayloads.ENABLE_DATA_PROTECTION.format(
                org_id=org_id, mgmt_cluster=mgmt_cluster, provisioner_name=provisioner_name, workload_cluster=cluster
            )

            json_payload = json.loads(payload)
            json_payload = json.dumps(json_payload, indent=4)

            if not self.is_data_protection_enabled(json_payload, cluster):
                current_app.logger.info("Enabling data protection...")
                enable_response = RequestApiUtil.exec_req(
                    "POST", url, headers=SaaSUtil.tmc_header, data=json_payload, verify=False
                )
                if not RequestApiUtil.verify_resp(enable_response, HTTPStatus.OK):
                    current_app.logger.error(enable_response)
                    return False, "Failed to enable data protection on cluster " + cluster

                count = 0
                enabled = False
                status = RequestApiUtil.exec_req(
                    "GET", url, headers=SaaSUtil.tmc_header, data=json_payload, verify=False
                )
                try:
                    if status.json()["dataProtections"][0]["status"]["phase"] == "READY":
                        enabled = True
                    else:
                        current_app.logger.info("Waiting for data protection enablement to complete...")
                except Exception:
                    pass

                while count < 90 and not enabled:
                    status = RequestApiUtil.exec_req(
                        "GET", url, headers=SaaSUtil.tmc_header, data=json_payload, verify=False
                    )
                    if status.json()["dataProtections"][0]["status"]["phase"] == "READY":
                        enabled = True
                        break
                    elif status.json()["dataProtections"][0]["status"]["phase"] == "ERROR":
                        current_app.logger.error("Data protection is enabled but its status is ERROR")
                        current_app.logger.error(status.json()["dataProtections"][0]["status"]["phaseInfo"])
                        enabled = True
                        break
                    else:
                        current_app.logger.info(
                            "Data protection status " + status.json()["dataProtections"][0]["status"]["phase"]
                        )
                        current_app.logger.info("Waited for " + str(count * 10) + "s, retrying...")
                        time.sleep(10)
                        count = count + 1

                if not enabled:
                    current_app.logger.error("Data protection is not enabled even after " + str(count * 10) + "s wait")
                    return False, "Timed out waiting for data protection to be enabled"
                else:
                    return True, "Data protection on cluster " + cluster + " enabled successfully"
            else:
                return True, "Data protection is already enabled on cluster " + cluster
        except Exception as e:
            current_app.logger.error(str(e))
            return False, "Exception occured while enabling data protection on cluster"

    @staticmethod
    def validate_backup_location(spec, env, tmc_url, tmc_header, cluster_type):
        try:
            if TkgsUtil.is_env_tkgs_ns(spec, env) and cluster_type.lower() == Type.SHARED:
                return False, "Invalid inputs provided for validation of data backup location"
            if env == Env.VMC:
                if cluster_type.lower() == Type.SHARED:
                    backup_location = spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterBackupLocation
                    cluster_group = spec.componentSpec.tkgSharedServiceSpec.tkgSharedserviceClusterGroupName
                elif cluster_type.lower() == Type.WORKLOAD:
                    backup_location = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterBackupLocation
                    cluster_group = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterGroupName
                else:
                    return False, "Invalid cluster type provided"
            else:
                if cluster_type.lower() == Type.SHARED:
                    if not TkgsUtil.is_env_tkgs_ns(spec, env) and not TkgsUtil.is_env_tkgs_wcp(spec, env):
                        if env == Env.VCF:
                            backup_location = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterBackupLocation
                            cluster_group = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceClusterGroupName
                        else:
                            backup_location = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterBackupLocation
                            cluster_group = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceClusterGroupName
                elif cluster_type.lower() == Type.WORKLOAD:
                    if TkgsUtil.is_env_tkgs_ns(spec, env):
                        backup_location = (
                            spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterBackupLocation
                        )
                        cluster_group = (
                            spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgsWorkloadClusterGroupName
                        )
                    else:
                        backup_location = spec.tkgWorkloadComponents.tkgWorkloadClusterBackupLocation
                        cluster_group = spec.tkgWorkloadComponents.tkgWorkloadClusterGroupName
                else:
                    return False, "Invalid cluster type provided"

            if not backup_location:
                return False, "Backup location is None"

            if not cluster_group:
                return False, "cluster_group is None"

            clusterGroups = TmcVelero.list_cluster_groups(tmc_url, tmc_header)
            if not clusterGroups[0]:
                return False, clusterGroups[1]

            if cluster_group not in clusterGroups[1]:
                return False, "Cluster Group " + cluster_group + " not found"

            url = VeleroAPI.GET_LOCATION_INFO.format(tmc_url=tmc_url, location=backup_location)

            response = RequestApiUtil.exec_req("GET", url, headers=tmc_header, data={}, verify=False)
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.NOT_FOUND):
                return (
                    False,
                    "Provided backup location for " + backup_location + " not found for " + cluster_type + " cluster",
                )
            elif not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                current_app.logger.error(response.json())
                return False, "Failed to fetch backup locations for data protection"

            if response.json()["backupLocation"]["status"]["phase"] == "READY":
                current_app.logger.info(backup_location + " backup location is valid")
            else:
                return (
                    False,
                    backup_location
                    + " backup location status is "
                    + response.json()["backupLocation"]["status"]["phase"],
                )

            current_app.logger.info("Proceeding to check if backup location is associated with provided cluster group")
            assigned_groups = response.json()["backupLocation"]["spec"]["assignedGroups"]
            for group in assigned_groups:
                if group["clustergroup"]["name"] == cluster_group:
                    return True, "Cluster group and backup location association validated"

            return False, "Cluster group " + cluster_group + " is not assigned to backup location " + backup_location

        except Exception as e:
            current_app.logger.error(str(e))
            return False, "Exception occurred while validating backup location"

    @staticmethod
    def list_cluster_groups(tmc_url, tmc_header):
        try:
            cluster_groups = []
            url = VeleroAPI.LIST_CLUSTER_GROUPS.format(tmc_url=tmc_url)
            response = RequestApiUtil.exec_req("GET", url, headers=tmc_header, data={}, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                current_app.logger.error(response)
                return False, "Failed to fetch cluster groups for data protection"

            for group in response.json()["clusterGroups"]:
                cluster_groups.append(group["fullName"]["name"])

            return True, cluster_groups
        except Exception as e:
            current_app.logger.error("Exception occurred while fetching cluster groups")
            return False, str(e)

    def is_data_protection_enabled(self, payload, cluster):
        url = VeleroAPI.ENABLE_DP.format(tmc_url=self.saas_util.tmc_url, cluster=cluster)
        status = RequestApiUtil.exec_req("GET", url, headers=SaaSUtil.tmc_header, data=payload, verify=False)
        try:
            if RequestApiUtil.verify_resp(status, status_code=HTTPStatus.OK):
                if status.json()["dataProtections"][0]["status"]["phase"] == "READY":
                    return True
                elif status.json()["dataProtections"][0]["status"]["phase"] == "ERROR":
                    current_app.logger.error("Data protection is enabled but its status is ERROR")
                    current_app.logger.error(status.json()["dataProtections"][0]["status"]["phaseInfo"])
                    return True
            else:
                current_app.logger.error(f"Data protection is not enabled for the cluster {cluster}")
                return False
        except Exception:
            return False

    @staticmethod
    def validate_cluster_credential(spec, env, tmc_url, tmc_header, cluster_type):
        try:
            if TkgsUtil.is_env_tkgs_ns(spec, env) and cluster_type.lower() == Type.SHARED:
                return False, "Invalid environment type provided for validation of data protection credentials"
            if env == Env.VMC:
                if cluster_type.lower() == Type.SHARED:
                    credential_name = spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterCredential
                    backup_location = spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterBackupLocation
                elif cluster_type.lower() == Type.WORKLOAD:
                    credential_name = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterCredential
                    backup_location = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterBackupLocation
                else:
                    return False, "Invalid cluster type provided"
            else:
                if cluster_type.lower() == Type.SHARED:
                    if not TkgsUtil.is_env_tkgs_ns(spec, env) and not TkgsUtil.is_env_tkgs_wcp(spec, env):
                        if env == Env.VCF:
                            credential_name = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterCredential
                            backup_location = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterBackupLocation
                        else:
                            credential_name = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterCredential
                            backup_location = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterBackupLocation
                elif cluster_type.lower() == Type.WORKLOAD:
                    if TkgsUtil.is_env_tkgs_ns(spec, env):
                        credential_name = (
                            spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterCredential
                        )
                        backup_location = (
                            spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterBackupLocation
                        )
                    else:
                        credential_name = spec.tkgWorkloadComponents.tkgWorkloadClusterCredential
                        backup_location = spec.tkgWorkloadComponents.tkgWorkloadClusterBackupLocation
                else:
                    return False, "Invalid cluster type provided"

            if not credential_name:
                return False, "Cluster Credential Name not found"

            url = VeleroAPI.GET_CRED_INFO.format(tmc_url=tmc_url, credential=credential_name)

            response = RequestApiUtil.exec_req("GET", url, headers=tmc_header, verify=False)
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.NOT_FOUND):
                return False, "Provided credential name for data protection not found"
            elif not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                current_app.logger.error(response.json())
                return False, "Failed to fetch provided credential for data protection"

            if response.json()["credential"]["status"]["phase"] == "CREATED":
                current_app.logger.info(credential_name + " credential is valid")
            else:
                return (
                    False,
                    credential_name
                    + " cluster credential status is "
                    + response.json()["credential"]["status"]["phase"],
                )

            current_app.logger.info(
                "Proceeding to check if credential "
                + credential_name
                + "is associated with selected backup location "
                + backup_location
            )

            url = VeleroAPI.GET_LOCATION_INFO.format(tmc_url=tmc_url, location=backup_location)

            response = RequestApiUtil.exec_req("GET", url, headers=tmc_header, verify=False)
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.NOT_FOUND):
                return False, "Provided backup location for " + backup_location + "not found"

            if response.json()["backupLocation"]["spec"]["credential"]["name"] == credential_name:
                return (
                    True,
                    "Credential "
                    + credential_name
                    + " validated successfully against backup location "
                    + backup_location,
                )

            return False, "Credential " + credential_name + " is not associated with " + backup_location
        except Exception as e:
            current_app.logger.error(str(e))
            return False, "Exception occurred while validating cluster credential"


class StandaloneVelero(VeleroUtil):
    VELERO_COMMAND = (
        "velero install --provider aws --plugins {plugin_registry} --image {image_registry} "
        "--bucket {bucket} --secret-file {secret_file} --use-volume-snapshots=false --use-restic "
        "--backup-location-config region={region} s3ForcePathStyle=true s3Url={s3_url} publicUrl={public_url}"
    )

    def __init__(self, env, spec):
        self.env = env
        self.spec = spec

    @staticmethod
    def check_data_protection_enabled(env, spec, type):
        try:
            if type == Type.SHARED:
                if env == Env.VMC:
                    is_enabled = (
                        spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterVeleroDataProtection.enableVelero
                    )
                elif env == Env.VCF:
                    is_enabled = (
                        spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterVeleroDataProtection.enableVelero
                    )
                elif env == Env.VSPHERE:
                    is_enabled = (
                        spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterVeleroDataProtection.enableVelero
                    )
                else:
                    is_enabled = "false"
            elif type == Type.WORKLOAD:
                if TkgsUtil.is_env_tkgs_ns(spec, env):
                    is_enabled = (
                        spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterVeleroDataProtection.enableVelero
                    )
                elif env == Env.VCF or env == Env.VSPHERE:
                    is_enabled = spec.tkgWorkloadComponents.tkgWorkloadClusterVeleroDataProtection.enableVelero
                elif env == Env.VMC:
                    is_enabled = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterVeleroDataProtection.enableVelero
            if is_enabled.lower() == "true":
                return True
            else:
                return False
        except Exception:
            return False

    def read_velero_param_dict(self, type):
        try:
            if type == Type.SHARED:
                if self.env == Env.VMC:
                    username = (
                        self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterVeleroDataProtection.username
                    )
                    password_base64 = (
                        self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterVeleroDataProtection.passwordBase64
                    )
                    bucket_name = (
                        self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterVeleroDataProtection.bucketName
                    )
                    backup_region = (
                        self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterVeleroDataProtection.backupRegion
                    )
                    backup_s3_url = (
                        self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterVeleroDataProtection.backupS3Url
                    )
                    backup_public_url = (
                        self.spec.componentSpec.tkgSharedServiceSpec.tkgSharedClusterVeleroDataProtection.backupPublicUrl
                    )
                elif self.env == Env.VCF:
                    username = (
                        self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterVeleroDataProtection.username
                    )
                    password_base64 = (
                        self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterVeleroDataProtection.passwordBase64
                    )
                    bucket_name = (
                        self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterVeleroDataProtection.bucketName
                    )
                    backup_region = (
                        self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterVeleroDataProtection.backupRegion
                    )
                    backup_s3_url = (
                        self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterVeleroDataProtection.backupS3Url
                    )
                    backup_public_url = (
                        self.spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedClusterVeleroDataProtection.backupPublicUrl
                    )
                elif self.env == Env.VSPHERE:
                    username = (
                        self.spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterVeleroDataProtection.username
                    )
                    password_base64 = (
                        self.spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterVeleroDataProtection.passwordBase64
                    )
                    bucket_name = (
                        self.spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterVeleroDataProtection.bucketName
                    )
                    backup_region = (
                        self.spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterVeleroDataProtection.backupRegion
                    )
                    backup_s3_url = (
                        self.spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterVeleroDataProtection.backupS3Url
                    )
                    backup_public_url = (
                        self.spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedClusterVeleroDataProtection.backupPublicUrl
                    )
            else:
                if TkgsUtil.is_env_tkgs_ns(self.spec, self.env):
                    username = (
                        self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterVeleroDataProtection.username
                    )
                    password_base64 = (
                        self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterVeleroDataProtection.passwordBase64
                    )
                    bucket_name = (
                        self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterVeleroDataProtection.bucketName
                    )
                    backup_region = (
                        self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterVeleroDataProtection.backupRegion
                    )
                    backup_s3_url = (
                        self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterVeleroDataProtection.backupS3Url
                    )
                    backup_public_url = (
                        self.spec.tkgsComponentSpec.tkgsVsphereNamespaceSpec.tkgsVsphereWorkloadClusterSpec.tkgWorkloadClusterVeleroDataProtection.backupPublicUrl
                    )
                elif self.env == Env.VCF or self.env == Env.VSPHERE:
                    username = self.spec.tkgWorkloadComponents.tkgWorkloadClusterVeleroDataProtection.username
                    password_base64 = (
                        self.spec.tkgWorkloadComponents.tkgWorkloadClusterVeleroDataProtection.passwordBase64
                    )
                    bucket_name = self.spec.tkgWorkloadComponents.tkgWorkloadClusterVeleroDataProtection.bucketName
                    backup_region = self.spec.tkgWorkloadComponents.tkgWorkloadClusterVeleroDataProtection.backupRegion
                    backup_s3_url = self.spec.tkgWorkloadComponents.tkgWorkloadClusterVeleroDataProtection.backupS3Url
                    backup_public_url = (
                        self.spec.tkgWorkloadComponents.tkgWorkloadClusterVeleroDataProtection.backupPublicUrl
                    )
                elif self.env == Env.VMC:
                    username = self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterVeleroDataProtection.username
                    password_base64 = (
                        self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterVeleroDataProtection.passwordBase64
                    )
                    bucket_name = (
                        self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterVeleroDataProtection.bucketName
                    )
                    backup_region = (
                        self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterVeleroDataProtection.backupRegion
                    )
                    backup_s3_url = (
                        self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterVeleroDataProtection.backupS3Url
                    )
                    backup_public_url = (
                        self.spec.componentSpec.tkgWorkloadSpec.tkgWorkloadClusterVeleroDataProtection.backupPublicUrl
                    )

            velero_params = dict(
                username=username,
                password=CommonUtils.decode_password(password_base64),
                bucket=bucket_name,
                region=backup_region,
                s3Url=backup_s3_url,
                publicUrl=backup_public_url,
            )
            return True, velero_params
        except Exception as e:
            current_app.logger.error("Exception occurred while fetching velero parameters for " + type + " cluster")
            return False, str(e)

    def create_velero_secret_file(self, username, password):
        try:
            data = f"""[default]
        aws_access_key_id="{username}"
        aws_secret_access_key="{password}"
            """
            file_name = TmcConstants.VELERO_SECRET_FILE
            FileHelper.delete_file(file_name)
            FileHelper.write_to_file(data, file_name)

            return True, file_name
        except Exception as e:
            current_app.logger.error("Exception occurred while creating velero credentials file")
            return False, str(e)

    def check_and_resolve_velero_pod_status(self, pod_status_output):
        try:
            pod_status_output.pop(0)
            iter = 0
            while iter < len(pod_status_output):
                if not pod_status_output[iter].__contains__("Running"):
                    return False, "ImagePullBackOff"
                iter = iter + 1
            return True, "Running"
        except Exception:
            current_app.logger.error("Failed to get velero and restic pod status")
            return False, "Error"

    def enable_data_protection(self, type):
        """
        read_velero_param_dict , create_velero_secret_file, check_and_resolve_velero_pod_status
        :param type:
        :return:
        """
        try:
            current_app.logger.info("Reading Velero parameter from the input JSON file")
            velero_params = self.read_velero_param_dict(type)
            if not velero_params[0]:
                current_app.logger.error(velero_params[1])
                return False, "Some Exception occurred while fetching velero parameters from input file"
            velero_params = velero_params[1]
            if CommonUtils.is_airGapped_enabled(self.env, self.spec):
                current_app.logger.info("The environment is airgapped")
                repo = self.spec.envSpec.customRepositorySpec.tkgCustomImageRepository
                repo = repo.replace("https://", "").replace("http://", "")
                if repo[-1] != "/":
                    repo = repo + "/"
                plugin_registry = repo + Extension.VELERO_PLUGIN_IMAGE_LOCATION
                image_registry = repo + Extension.VELERO_CONTAINER_IMAGE
            else:
                repo = Repo.PUBLIC_REPO
                plugin_registry = repo + Extension.VELERO_PLUGIN_IMAGE_LOCATION
                image_registry = repo + Extension.VELERO_CONTAINER_IMAGE

            current_app.logger.info("Creating Velero secret credential file")
            secret_file = self.create_velero_secret_file(velero_params["username"], velero_params["password"])
            if not secret_file[0]:
                current_app.logger.error("Unable to create a credential file for Velero")
                current_app.logger.error(secret_file[1])
                return False, secret_file[1]
            secret_file = secret_file[1]
            current_app.logger.info("Starting installation of Velero on " + type + " cluster")

            command = StandaloneVelero.VELERO_COMMAND.format(
                plugin_registry=plugin_registry,
                image_registry=image_registry,
                bucket=velero_params["bucket"],
                secret_file=secret_file,
                region=velero_params["region"],
                s3_url=velero_params["s3Url"],
                public_url=velero_params["publicUrl"],
            )
            velero_output = runShellCommandAndReturnOutputAsList(command)
            if velero_output[1] != 0:
                current_app.logger.error("Failed to install Velero on " + type + " cluster")
                current_app.logger.error(str(velero_output[0]))
                return False, "Failed to install Velero on " + type + " cluster"
            current_app.logger.info("Successfully installed Velero on " + type + " cluster")
            current_app.logger.info("Checking Velero pod status")
            command = KubectlCommands.LIST_PODS.format(namespace="velero")
            velero_pod_status_output = runShellCommandAndReturnOutputAsList(command)
            velero_pod_status = self.check_and_resolve_velero_pod_status(velero_pod_status_output[0])
            timer = 0
            pod_status = False
            while timer < 300:
                if not velero_pod_status[0]:
                    current_app.logger.info("Velero pods are in " + velero_pod_status[1] + " status.")
                    current_app.logger.info("Waiting 30 secs for pods to be in RUNNING state")
                    time.sleep(30)
                    velero_pod_status_output = runShellCommandAndReturnOutputAsList(command)
                    velero_pod_status = self.check_and_resolve_velero_pod_status(velero_pod_status_output[0])
                    timer = timer + 30
                else:
                    current_app.logger.info("All the pods are in RUNNING state after " + str(timer) + " seconds.")
                    pod_status = True
                    break
            if not pod_status:
                current_app.logger.error("Velero pods are in " + velero_pod_status[1] + " status.")
            FileHelper.delete_file(secret_file)
            current_app.logger.info("Successfully removed file : " + secret_file)
            return True, "Successfully installed Velero on " + type + " cluster"
        except Exception as e:
            current_app.logger.error("Some exception occurred while installing Velero on " + type + " cluster")
            current_app.logger.error(str(e))
            return False, str(e)
