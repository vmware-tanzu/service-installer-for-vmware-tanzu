# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import base64
import json
from pathlib import Path

from common.common_utilities import isEnvTkgs_ns, isEnvTkgs_wcp
from common.model.vcfSpec import VcfMasterSpec
from common.model.vmcSpec import VmcMasterSpec
from common.model.vsphereSpec import VsphereMasterSpec
from common.model.vsphereTkgsSpec import VsphereTkgsMasterSpec
from common.model.vsphereTkgsSpecNameSpace import VsphereTkgsNameSpaceMasterSpec
from common.operation.constants import Env

__author__ = "Abhishek Inani"


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
