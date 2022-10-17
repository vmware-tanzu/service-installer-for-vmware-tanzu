#!/usr/local/bin/python3

#  Copyright 2022 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause
import json
import os
import ruamel.yaml # pip install ruamel.yaml
from constants.constants import Paths, Avi_Version, Avi_Tkgs_Version, Env
from util.avi_api_helper import obtain_avi_version, check_controller_is_up
from util.logger_helper import LoggerHelper, log
from util.cmd_helper import CmdHelper
from model.run_config import RunConfig
from util.tkg_util import TkgUtil
from util.common_utils import checkenv, getClusterID
from util.govc_client import GovcClient
from util.local_cmd_helper import LocalCmdHelper
from util.common_utils import getClusterStatusOnTanzu
from util.ShellHelper import runShellCommandAndReturnOutput
from util.cleanup_util import CleanUpUtil
from util.common_utils import envCheck
from workflows.ra_nsxt_workflow import RaNSXTWorkflow

logger = LoggerHelper.get_logger(name='Pre Setup')


class PreSetup:
    """PreSetup class is responsible to perform Pre Checks before deploying any of clusters/nodes"""
    def __init__(self, root_dir, run_config: RunConfig) -> None:
        self.run_config = run_config
        self.version = None
        self.jsonpath = None
        self.state_file_path = os.path.join(root_dir, Paths.STATE_PATH)
        self.tkg_util_obj = TkgUtil(run_config=self.run_config)
        self.tkg_version_dict = self.tkg_util_obj.get_desired_state_tkg_version()
        if "tkgs" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_WCP_MASTER_SPEC_PATH)
        elif "tkgm" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        else:
            raise Exception(f"Could not find supported TKG version: {self.tkg_version_dict}")

        with open(self.jsonpath) as f:
            self.jsonspec = json.load(f)
        self.env = envCheck(self.run_config)
        if self.env[1] != 200:
            logger.error("Wrong env provided " + self.env[0])
            d = {
                "responseType": "ERROR",
                "msg": "Wrong env provided " + self.env[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500
        self.env = self.env[0]

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)
        self.govc_client = GovcClient(self.jsonspec, LocalCmdHelper())
        self.kube_config = os.path.join(self.run_config.root_dir, Paths.REPO_KUBE_TKG_CONFIG)
        self.isEnvTkgs_wcp = TkgUtil.isEnvTkgs_wcp(self.jsonspec)
        self.isEnvTkgs_ns = TkgUtil.isEnvTkgs_ns(self.jsonspec)
        self.get_vcenter_details()
        self.get_avi_details()
        self.get_tkg_mgmt_details()
        self.cleanup_obj = CleanUpUtil()

    def get_vcenter_details(self) -> None:
        """
        Method to get vCenter Details from JSON file
        :return: None
        """
        self.vcenter_dict = {}
        try:
            self.vcenter_dict.update({'vcenter_ip': self.jsonspec['envSpec']['vcenterDetails']['vcenterAddress'],
                                      'vcenter_password': CmdHelper.decode_base64(
                                          self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoPasswordBase64']),
                                      'vcenter_username': self.jsonspec['envSpec']['vcenterDetails']['vcenterSsoUser'],
                                      'vcenter_cluster_name': self.jsonspec['envSpec']['vcenterDetails']['vcenterCluster'],
                                      'vcenter_datacenter': self.jsonspec['envSpec']['vcenterDetails']['vcenterDatacenter'],
                                      'vcenter_data_store': self.jsonspec['envSpec']['vcenterDetails']['vcenterDatastore']
                                      })
        except KeyError as e:
            logger.warning(f"Field {e} not configured in vcenterDetails")
            pass

    def get_avi_details(self) -> None:
        """
        Method to get all AVI related details in a dict
        :return : None
        """
        self.avi_dict = {}
        if self.isEnvTkgs_wcp:
            self.avi_dict.update({"avi_fqdn": self.jsonspec['tkgsComponentSpec']['aviComponents']['aviController01Fqdn']})
        else:
            self.avi_dict.update(
                {"avi_fqdn": self.jsonspec['tkgComponentSpec']['aviComponents']['aviController01Fqdn']})

    def get_tkg_mgmt_details(self) -> None:
        """
        Method to get MGMT details in a dict
        return: None
        """
        if not self.isEnvTkgs_wcp and not self.isEnvTkgs_ns:
            self.mgmt_cluster_name = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgMgmtClusterName']
            self.wrkld_cluster_name = self.jsonspec['tkgWorkloadComponents']['tkgWorkloadClusterName']
            if self.env == Env.VCF:
                self.shrd_cluster_name = self.jsonspec['tkgComponentSpec']['tkgSharedserviceSpec'][
                'tkgSharedserviceClusterName']
            elif self.env == Env.VSPHERE:
                self.shrd_cluster_name = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
                'tkgSharedserviceClusterName']
        else:
            self.mgmt_cluster_name = None

    @log("Pre Check AVI")
    def pre_check_avi(self) -> tuple:
        """
        Method to check that AVI is deployed or not already
        return: tuple
                  state_dict = {"avi":{"deployed": True/False,
                             "version": AVI version,
                             "health": "UP/DOWN",
                             "name": Name of AVI deployed}
                  msg = "User defined message"
        """
        if self.env == Env.VCF:
            RaNSXTWorkflow(self.run_config).configure_avi_nsxt_config()
        if TkgUtil.isEnvTkgs_wcp(self.jsonspec):
            avi_required = Avi_Tkgs_Version.VSPHERE_AVI_VERSION
        else:
            avi_required = Avi_Version.VSPHERE_AVI_VERSION

        state_dict = {"avi":{"deployed": False,
                             "version": avi_required,
                             "health": "DOWN",
                             "name": self.avi_dict["avi_fqdn"]}}
        msg = "AVI not deployed"

        # Verify AVI deployed
        ip = self.govc_client.get_vm_ip(vm_name=self.avi_dict["avi_fqdn"],
                                   datacenter_name=self.vcenter_dict["vcenter_datacenter"])
        if ip is None:
            msg = "Could not find VM IP. Seems AVI not deployed"
            return state_dict, msg
        else:
            ip = ip[0]
            deployed_avi_version = obtain_avi_version(ip, self.jsonspec)
            if deployed_avi_version[0] is None:
                return state_dict, msg

        # AVI Deployed --> Verify AVI version
        if deployed_avi_version[0] == avi_required:
            state_dict["avi"]["deployed"] = True
        else:
            state_dict["avi"]["version"] = deployed_avi_version[0]
            msg = f"AVI Version mis-matched : Deployed: {deployed_avi_version[0]} & Required: {avi_required}"
            return state_dict, msg

        # AVI Deployed --> AVI Version Verified --> Verify AVI name
        # TODO: How to verify avi fqdn name

        # AVI Deployed --> AVI Version --> AVI name --> Verify AVI state
        if "UP" in check_controller_is_up(ip):
            state_dict["avi"]["deployed"] = True
            state_dict["avi"]["health"] = "UP"
        else:
            msg = "AVI state not UP: Deployed but AVI is not UP"
            return state_dict, msg

        # Update state.yml file
        self.update_state_yml(state_dict)
        return state_dict, "Pre Check PASSED for AVI"

    @log("Pre Check MGMT")
    def pre_check_mgmt(self):
        """
        Method to check that MGMT cluster is deployed or not already
        """
        state_dict = {"mgmt": {"deployed": False,
                              "health": "DOWN",
                              "name": self.mgmt_cluster_name}}
        msg = "Pre Check Failed: "
        if self.isEnvTkgs_wcp or self.isEnvTkgs_ns:
            msg = "MGMT Cluster not required for TKGs"
            return state_dict, msg
        # login to Tanzu
        tanzu_login_cmd = ["tanzu", "login", "--server", self.mgmt_cluster_name]
        out = runShellCommandAndReturnOutput(tanzu_login_cmd)
        if f"successfully logged in to management cluster using the kubeconfig {self.mgmt_cluster_name}" in out[0]:
            mgmt_status_dict = getClusterStatusOnTanzu(cluster_name=self.mgmt_cluster_name,
                                              return_dict=True)
            logger.debug(mgmt_status_dict)
            if mgmt_status_dict["deployed"]:
                state_dict["mgmt"]["deployed"] = True
                if mgmt_status_dict["running"]:
                    state_dict["mgmt"]["health"] = "UP"
                    msg = f"Pre Check PASSED: MGMT Cluster '{self.mgmt_cluster_name}' is already Deployed and UP"
                else:
                    msg = msg + f"MGMT Cluster '{self.mgmt_cluster_name}' NOT UP"
            else:
                msg = msg + f"MGMT Cluster '{self.mgmt_cluster_name}' not Deployed"
        elif f"Error: could not find server \"{self.mgmt_cluster_name}\"" in out[0]:
            msg = msg + f"MGMT Cluster '{self.mgmt_cluster_name}' is not deployed"
        else:
            msg = msg + f"Couldn't login to MGMT Cluster '{self.mgmt_cluster_name}'"
            logger.error(f"ERROR: {out[0]}")

        # Update state.yml file
        self.update_state_yml(state_dict)
        return state_dict, msg

    @log("Pre Check WorkLoad")
    def pre_check_wrkld(self):
        """
        Method to check that Workload cluster is deployed or not already
        """
        state_dict = {"workload_clusters": {"deployed": False,
                               "health": "DOWN",
                               "name": self.wrkld_cluster_name}}
        msg = "Pre Check Failed: "

        # login to Tanzu
        tanzu_login_cmd = ["tanzu", "login", "--server", self.mgmt_cluster_name]
        out = runShellCommandAndReturnOutput(tanzu_login_cmd)
        if f"successfully logged in to management cluster using the kubeconfig {self.mgmt_cluster_name}" in out[0]:
            cluster_status_dict = getClusterStatusOnTanzu(cluster_name=self.wrkld_cluster_name,
                                                       return_dict=True)
            logger.debug(cluster_status_dict)
            if cluster_status_dict["deployed"]:
                state_dict["workload_clusters"]["deployed"] = True
                if cluster_status_dict["running"]:
                    state_dict["workload_clusters"]["health"] = "UP"
                    msg = f"Pre Check PASSED: WORKLOAD Cluster '{self.wrkld_cluster_name}' is already Deployed and UP"
                else:
                    msg = msg + f"WORKLOAD Cluster '{self.wrkld_cluster_name}' NOT UP"
            else:
                msg = msg + f"WORKLOAD Cluster '{self.wrkld_cluster_name}' not Deployed"
        elif f"Error: could not find server \"{self.wrkld_cluster_name}\"" in out[0]:
            msg = msg + f"WORKLOAD Cluster '{self.wrkld_cluster_name}' is not deployed"
        else:
            msg = msg + f"Couldn't login to MGMT Cluster '{self.mgmt_cluster_name}'"
            logger.error(f"ERROR: {out[0]}")

        # Update state.yml file
        self.update_state_yml(state_dict)
        return state_dict, msg

    @log("Pre Check Shared")
    def pre_check_shrd(self):
        """
        Method to check that Shared cluster is deployed or not already
        """
        state_dict = {"shared_services": {"deployed": False,
                                "health": "DOWN",
                                "name": self.shrd_cluster_name}}
        msg = "Pre Check Failed: "

        # login to Tanzu
        tanzu_login_cmd = ["tanzu", "login", "--server", self.mgmt_cluster_name]
        out = runShellCommandAndReturnOutput(tanzu_login_cmd)
        if f"successfully logged in to management cluster using the kubeconfig {self.mgmt_cluster_name}" in out[0]:
            cluster_status_dict = getClusterStatusOnTanzu(cluster_name=self.shrd_cluster_name,
                                                          return_dict=True)
            logger.debug(cluster_status_dict)
            if cluster_status_dict["deployed"]:
                state_dict["shared_services"]["deployed"] = True
                if cluster_status_dict["running"]:
                    state_dict["shared_services"]["health"] = "UP"
                    msg = f"Pre Check PASSED: SHARED Cluster '{self.shrd_cluster_name}' is already Deployed and UP"
                else:
                    msg = msg + f"SHARED Cluster '{self.shrd_cluster_name}' NOT UP"
            else:
                msg = msg + f"SHARED Cluster '{self.shrd_cluster_name}' not Deployed"
        elif f"Error: could not find server \"{self.shrd_cluster_name}\"" in out[0]:
            msg = msg + f"SHARED Cluster '{self.shrd_cluster_name}' is not deployed"
        else:
            msg = msg + f"Couldn't login to management Cluster '{self.mgmt_cluster_name}'"
            logger.error(f"ERROR: {out[0]}")

        # Update state.yml file
        self.update_state_yml(state_dict)
        return state_dict, msg

    @log("Pre Check Enable WCP")
    def pre_check_enable_wcp(self):
        state_dict = {"enable_wcp": {"enabled": False,
                                     "health": "DOWN"}}
        msg = "WCP not enabled"

        cluster_id = getClusterID(self.vcenter_dict["vcenter_ip"],
                         self.vcenter_dict["vcenter_username"],
                         self.vcenter_dict["vcenter_password"],
                         self.vcenter_dict["vcenter_cluster_name"],
                         self.jsonspec)
        if cluster_id[1] != 200:
            d = {
                "responseType": "ERROR",
                "msg": cluster_id[0],
                "ERROR_CODE": 500
            }
            return json.dumps(d), 500

        cluster_id = cluster_id[0]
        is_wcp_enabled = self.cleanup_obj.getWCPStatus(cluster_id, self.jsonspec)
        if is_wcp_enabled[0]:
            state_dict["enable_wcp"]["enabled"] = True
            msg = "WCP Already Enabled"
            if is_wcp_enabled[1] == "RUNNING":
                state_dict["enable_wcp"]["state"] = "UP"
                msg = msg + " AND RUNNING"
            else:
                msg = msg + " AND NOT RUNNING"
            return state_dict, msg
        return state_dict, msg

    def update_state_yml(self, state_dict: dict):
        config, ind, bsi = ruamel.yaml.util.load_yaml_guess_indent(open(self.state_file_path))
        for key, val in state_dict.items():
            instances = config[key]
            for item_key, item_val in val.items():
                if key == "workload_clusters":
                    instances[0][item_key] = item_val
                else:
                    instances[item_key] = item_val

        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=ind, sequence=ind, offset=bsi)
        with open(self.state_file_path, 'w') as fp:
            yaml.dump(config, fp)
