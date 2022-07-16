"""
Class to define methods for TKGs and TKGm utilities
"""


class TkgUtil:
    def __init__(self):
        pass

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


