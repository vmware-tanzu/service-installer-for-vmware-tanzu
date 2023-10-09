# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

from common.common_utilities import isEnvTkgs_ns, isEnvTkgs_wcp
from common.model.vcdSpec import VcdMasterSpec
from common.model.vcfSpec import VcfMasterSpec
from common.model.vmcSpec import VmcMasterSpec
from common.model.vsphereSpec import VsphereMasterSpec
from common.model.vsphereTkgsSpec import VsphereTkgsMasterSpec
from common.model.vsphereTkgsSpecNameSpace import VsphereTkgsNameSpaceMasterSpec
from common.operation.constants import ApiUrl, Component, Env, EnvType, Extension, RegexPattern
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
from common.util.tkgs_util import TkgsUtil

__author__ = "Abhishek Inani"

# dict mapping to API URL to update status on UI, with
API_COMPONENTS_MAPPING = {
    ApiUrl.PRE_CHECK: Component.PRECHECK,
    ApiUrl.AVI_CONFIG_URL[Env.VSPHERE]: Component.AVI,
    ApiUrl.AVI_WCP_CONFIG_URL: Component.WCP_CONFIG,
    ApiUrl.ENABLE_WCP_URL: Component.WCP,
    ApiUrl.SUPRVSR_NAMESPACE_URL: Component.NAMESPACE,
    ApiUrl.WORKLOAD_URL: Component.WORKLOAD,
    ApiUrl.EXTENSIONS_URL: Component.EXTENSIONS,
}


class CommonUtils:
    @staticmethod
    def is_file_exist(file_name) -> bool:
        """
        Method to check if file exists or not

        param file_name: file name with path

        return: return true if pass else return fail
        """
        return Path(file_name).exists()

    @staticmethod
    def is_json_valid(input_file):
        try:
            with open(input_file, "r") as openfile:
                json.load(openfile)
        except ValueError:
            return False
        return True

    @staticmethod
    def decode_password(password):
        """
        encode given password
        :param password: encoded password string
        :return: decoded string
        """
        base64_bytes = password.encode("ascii")
        enc_bytes = base64.b64decode(base64_bytes)
        return enc_bytes.decode("ascii").rstrip("\n")

    @staticmethod
    def encode_utf(text_string):
        base64_bytes = base64.b64encode(text_string.encode("utf-8"))
        return str(base64_bytes, "utf-8")

    @staticmethod
    def encode_password(password):
        """
        decode given password
        :param password: password string
        :return: encoded password string
        """
        ecod_bytes = password.encode("ascii")
        ecod_bytes = base64.b64encode(ecod_bytes)
        ecod_string = ecod_bytes.decode("ascii")
        return ecod_string

    @staticmethod
    def update_progress_bar(size_uploaded, size_file, size_bar=50):
        perc_uploaded = round(size_uploaded / size_file * 100)
        progress = round(perc_uploaded / 100 * size_bar)
        status_bar = f"Harbor preload status : {'▒' * progress}{' ' * (size_bar - progress)}"
        print(f"\r{status_bar} | {perc_uploaded}%", end="")

    @staticmethod
    def get_spec_obj(env):
        if env == Env.VMC:
            return VmcMasterSpec
        elif env == Env.VCF:
            return VcfMasterSpec
        elif env == Env.VCD:
            return VcdMasterSpec
        elif env == Env.VSPHERE:
            if isEnvTkgs_wcp(env):
                return VsphereTkgsMasterSpec
            elif isEnvTkgs_ns(env):
                return VsphereTkgsNameSpaceMasterSpec
            else:
                return VsphereMasterSpec

    @staticmethod
    def get_os_flavor(env, spec):
        """
        Validate photon OS is selected for TMC integration
        :param env: env type
        :param spec: VMC, VCF or Vsphere sepc object
        :param is_shared: True, if shared cluster else False
        :param is_workload: True if workload cluster else, False
        :return: 200 if success else, 500
        """
        if env == Env.VMC:
            mgmt_os = spec.componentSpec.tkgMgmtSpec.tkgMgmtBaseOs
            shared_os = spec.componentSpec.tkgSharedServiceSpec.tkgSharedserviceBaseOs
            wrkl_os = spec.componentSpec.tkgWorkloadSpec.tkgWorkloadBaseOs
        elif env == Env.VSPHERE:
            mgmt_os = spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtBaseOs
            shared_os = spec.tkgComponentSpec.tkgMgmtComponents.tkgSharedserviceBaseOs
            wrkl_os = spec.tkgWorkloadComponents.tkgWorkloadBaseOs
        elif env == Env.VCF:
            mgmt_os = spec.tkgComponentSpec.tkgMgmtComponents.tkgMgmtBaseOs
            shared_os = spec.tkgComponentSpec.tkgSharedserviceSpec.tkgSharedserviceBaseOs
            wrkl_os = spec.tkgWorkloadComponents.tkgWorkloadBaseOs
        else:
            return None, "Invalid env provided"

        return mgmt_os.lower(), wrkl_os.lower(), shared_os.lower()

    @staticmethod
    def is_avi_non_orchestrated(spec):
        try:
            mode = spec.tkgComponentSpec.aviComponents.modeOfDeployment
            if mode == "non-orchestrated":
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def is_airGapped_enabled(env, spec):
        if env == Env.VMC:
            air_gapped = ""
        else:
            try:
                air_gapped = spec.envSpec.customRepositorySpec.tkgCustomImageRepository
            except Exception:
                return False
        if not air_gapped.lower():
            return False
        else:
            return True

    @staticmethod
    def get_avi_license_type(env, spec):
        """
        fetches the license for AVI deployment, by default license will be set to enterprise
        """
        license_type = "enterprise"
        if env == Env.VSPHERE:
            if isEnvTkgs_wcp(env):
                license_type = spec.tkgsComponentSpec.aviComponents.typeOfLicense
            else:
                license_type = spec.tkgComponentSpec.aviComponents.typeOfLicense
        elif env == Env.VMC:
            license_type = spec.componentSpec.aviComponentSpec.typeOfLicense
        return license_type

    @staticmethod
    def prepare_status_json_output(resp):
        json_data = {}
        for data in resp:
            json_data[data["name"].split(" (")[0]] = data["status"]
        return json_data

    @staticmethod
    def match_endpoint(endpoint_path):
        for ep, component in API_COMPONENTS_MAPPING.items():
            parsed_url = urlparse(ep)
            if endpoint_path in parsed_url.path:
                return component
        else:
            return False

    @staticmethod
    def seperate_netmask_and_ip(cidr):
        return str(cidr).split("/")

    @staticmethod
    def create_directory(directory_path):
        try:
            command = f"mkdir -p {directory_path}"
            create_output = runShellCommandAndReturnOutputAsList(command)
            if create_output[1] != 0:
                return False
            else:
                return True
        except Exception:
            return False

    @staticmethod
    def is_identity_management_enabled(env, spec):
        try:
            if not TkgsUtil.is_env_tkgs_wcp(spec, env) and not TkgsUtil.is_env_tkgs_ns(spec, env):
                if env == Env.VMC:
                    idm = spec.componentSpec.identityManagementSpec.identityManagementType
                elif env == Env.VSPHERE or env == Env.VCF:
                    idm = spec.tkgComponentSpec.identityManagementSpec.identityManagementType
                if (idm.lower() == "oidc") or (idm.lower() == "ldap"):
                    return True
                else:
                    return False
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def check_mgmt_proxy_enabled(env, spec):
        if env == Env.VMC:
            mgmt_proxy = "false"
        else:
            try:
                mgmt_proxy = spec.envSpec.proxySpec.tkgMgmt.enableProxy
            except Exception:
                return False
        if mgmt_proxy.lower() == "true":
            return True
        else:
            return False

    @staticmethod
    def is_compliant_deployment(spec):
        try:
            compliant_deployment = spec.envSpe.compliantSpec.compliantDeployment
            if compliant_deployment == "false":
                return False
            elif compliant_deployment == "true":
                return True
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def load_bom_file(spec):
        if CommonUtils.is_compliant_deployment(spec):
            bom_file = Extension.FIPS_BOM_LOCATION_14
        else:
            bom_file = Extension.BOM_LOCATION_14
        try:
            with open(bom_file, "r") as stream:
                try:
                    data = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    return None, "Failed to find key " + str(exc)
                return data, "SUCCESS"
        except Exception as e:
            return None, "Failed to read bom file " + str(e)

    @staticmethod
    def runSsh(vc_user):
        os.system("rm -rf /root/.ssh/id_rsa")
        os.system("ssh-keygen -t rsa -b 4096 -C '" + vc_user + "' -f /root/.ssh/id_rsa -N ''")
        os.system("eval $(ssh-agent)")
        os.system("ssh-add /root/.ssh/id_rsa")
        with open("/root/.ssh/id_rsa.pub", "r") as f:
            re = f.readline()
        return re

    @staticmethod
    def grab_host_from_url(url):
        m = re.search(RegexPattern.URL_REGEX_PORT, url)
        if not m.group("host"):
            return None
        else:
            return m.group("host")

    @staticmethod
    def grab_port_from_url(url):
        m = re.search(RegexPattern.URL_REGEX_PORT, url)
        if not m.group("port"):
            return "443"
        else:
            return m.group("port")

    @staticmethod
    def is_env_tkgm(env, spec):
        try:
            if env == Env.VSPHERE:
                tkgs = spec.envSpec.envType
                if tkgs.lower() == EnvType.TKGM:
                    return True
                else:
                    return False
            else:
                return True
        except KeyError:
            return False
