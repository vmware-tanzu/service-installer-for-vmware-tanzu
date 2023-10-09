"""
Class to define methods for TKGs and TKGm utilities
"""
import logging
from tokenize import String


class TkgUtil:
    def __init__(self, run_config: object):
        self.run_config = run_config

    @staticmethod
    def isEnvTkgs_wcp(jsonspec) -> bool:
        """
        Method to check if TKGs environment is TKGs_wcp or not
         - In TKGs it's WCP --> Workload Control Plane
        :return: boolean
        """
        env_type = jsonspec["envSpec"]["envType"]
        if "tkgs-wcp" in env_type:
            return True
        else:
            return False


    @staticmethod
    def isEnvTkgs_ns(jsonspec) -> bool:
        """
        Method to check if TKGs environment is TKGs_ns or not
         - In TKGs it's NS --> NameSpace Workload
        :return: boolean
        """
        env_type = jsonspec["envSpec"]["envType"]
        if "tkgs-ns" in env_type:
            return True
        else:
            return False

    def get_desired_state_tkg_version(self) -> dict:
        """
        Method to get desired state TKG version for TKGm or TKGs

        return: dict of tkg version with valid version excluding None version
        """
        tkg_versions = {}
        tkgs_type = [attr for attr in dir(self.run_config.desired_state.version) if "tkg" in attr]
        for tkg_type in tkgs_type:
            if tkg_type == "tkgm":
                tkg_versions.update({"tkgm": self.run_config.desired_state.version.tkgm})
            elif tkg_type == "tkgs":
                tkg_versions.update({"tkgs": self.run_config.desired_state.version.tkgs})
            else:
                raise Exception(f"Invalid TKG type in desired state YAML file: {tkg_type}")
        filtered_tkg_versions = dict(filter(lambda val: val[1] is not None, tkg_versions.items()))
        if len(filtered_tkg_versions.keys()) > 1:
            raise Exception(f"Received multiple TKG types in desired state YAML: {filtered_tkg_versions}")
        else:
            return filtered_tkg_versions

    def get_desired_tkg_type(self):
        """
        Method to get desired state TkG type
        """
        tkgs_type = [attr for attr in dir(self.run_config.desired_state.version) if "tkg" in attr]
        return tkgs_type[0]


    def get_desired_state_env(self):
        """
        Method to get desired state env
        """
        return self.run_config.desired_state.version.env
