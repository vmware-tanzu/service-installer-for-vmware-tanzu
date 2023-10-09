# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

# TODO

__author__ = "Abhishek Inani"

import argparse
import base64
import getpass
import json
import os
import pickle
import signal
import subprocess
import sys
import time
from threading import Thread

import requests
from pkg_resources import get_distribution
from python_terraform import Terraform

from src.common.cleanup.cleanup_constants import Cleanup
from src.common.operation.constants import ApiUrl, Component, CseMarketPlace, Env, Paths, SivtStatus
from src.common.util.arcas_deco import ArcasDecorator
from src.common.util.common_utils import CommonUtils
from src.common.util.file_helper import FileHelper
from src.common.util.harbor_utils import HarborUtils
from src.common.util.request_api_util import RequestApiUtil
from src.common.util.tiny_db_util import TinyDbUtil
from src.exceptions.custom_exceptions import JsonReadException
from src.vcd.aviConfig.avi_nsx_cloud import getCloudSate, isAviHaEnabled, nsx_cloud_creation

__version__ = get_distribution("arcas").version

ARCAS_OPS_DICT = {
    "vcf_pre_configuration": "self.vcf_pre_configuration",
    "vmc_pre_configuration": "self.vmc_pre_configuration",
    "avi_configuration": "self.avi_configuration",
    "shared_service_configuration": "self.shared_service_configuration",
    "workload_preconfig": "self.workload_preconfig",
    "workload_deploy": "self.workload_deploy",
    "tkg_mgmt_configuration": "self.management_configuration",
    "deployapp": "self.deploy_app",
    "session": "self.session",
    "deploy_extensions": "self.deploy_extensions",
    "avi_wcp_configuration": "self.avi_wcp_configuration",
    "enable_wcp": "self.enable_wcp",
    "create_supervisor_namespace": "self.create_supervisor_namespace",
    "create_workload_cluster": "self.create_workload_cluster",
    "vcd_avi_configuration": "self.vcd_avi_configuration",
    "avi_cloud_configuration": "self.avi_cloud_configuration",
    "vcd_org_configuration": "self.vcd_org_configuration",
    "cse_server_configuration": "self.cse_server_configuration",
}
SUPPORTED_NON_VCD_ENV_LIST = [Env.VSPHERE, Env.VMC, Env.VCF]
SUPPORTED_CLEANUP_OPTIONS = [
    Cleanup.ALL,
    Cleanup.VCF,
    Cleanup.VMC,
    Cleanup.AVI,
    Cleanup.MGMT_CLUSTER,
    Cleanup.SHARED_CLUSTER,
    Cleanup.WORKLOAD_CLUSTER,
    Cleanup.SUPERVISOR_NAMESPACE,
    Cleanup.TKG_WORKLOAD_CLUSTER,
    Cleanup.DISABLE_WCP,
    Cleanup.EXTENSION,
]
SUPPORTED_ENV_LIST = SUPPORTED_NON_VCD_ENV_LIST.copy() + [Env.VCD]
MANDATORY_PARAMS_LIST = ["env", "file"]
LOAD_TANZU_IMAGE_PARAMS = ["repo_name", "tkg_binaries_path"]
GET_STATUS_PARAMS = ["repo_name"]
CAT_DICT = {}
COOKIES = "/root/cookies.txt"
TOKEN = "/root/token.txt"


class ArcasCli:
    """ "Arcas CLI class, landing class for all ARCAS operations"""

    def __init__(self):
        """Class constructor"""
        try:
            self.sivt_db_file = f"{Paths.SIVT_DB_FILE}"
            self.tiny_db = TinyDbUtil(self.sivt_db_file)
            self.req_api_obj = RequestApiUtil()
            self.file_helper = FileHelper()
            self.t1 = None
            self.pro = None
            self.headers = None
            self.payload = None
            self.stop_thread = False
            self.precheck = False
            self.skip_login = False

            self.arcas_deco = ArcasDecorator()
            self.parser = argparse.ArgumentParser(
                description="ARCAS/Service Installer for VMware Tanzu", add_help=False
            )
            # Defining independent variables
            self.parser.add_argument("--help", action="store_true", help="Arcas Usage")
            self.parser.add_argument("--version", action="store_true", help="Arcas currently installed version")

            # Defining mandatory variables for below operations
            self.parser.add_argument(
                "--env",
                help="IaaS Platform like 'vmc' or 'vsphere' or 'vcf'",
                choices=SUPPORTED_ENV_LIST,
                default=None,
            )
            self.parser.add_argument("--file", help="Absolute path for SIVT JSON file", default=None)

            # Load Tanzu image parameter
            self.parser.add_argument("--load_tanzu_image_to_harbor", action="store_true", help="Load images to harbor")
            self.parser.add_argument("--get_harbor_preloading_status", action="store_true", help="Get preload status")
            self.parser.add_argument("--repo_name", help="Harbor repo name", default=None)
            self.parser.add_argument("--tkg_binaries_path", help="Harbor repo name", default=None)

            # For VSphere-NSXT Parameters:
            self.parser.add_argument("--vcf_pre_configuration", action="store_true", help="VCF Pre configuration")

            # For VMC Parameters:
            self.parser.add_argument("--vmc_pre_configuration", action="store_true", help="VMC Pre configuration")

            # AVI Parameters:
            self.parser.add_argument("--avi_configuration", action="store_true", help="Deploy AVI")

            # For MGMT Cluster deploy:
            self.parser.add_argument("--tkg_mgmt_configuration", action="store_true", help="Deploy MGMT Cluster")

            # For Shared service deploy:
            self.parser.add_argument(
                "--shared_service_configuration", action="store_true", help="Deploy Shared service Cluster"
            )

            # For Workload deploy:
            self.parser.add_argument("--workload_preconfig", action="store_true", help="Workload Pre config")
            self.parser.add_argument("--workload_deploy", action="store_true", help="Deploy Workload Cluster")

            # TKGs: WCP enable:
            self.parser.add_argument("--avi_wcp_configuration", action="store_true", help="AVI WCP config")
            self.parser.add_argument("--enable_wcp", action="store_true", help="Enable WCP")

            # TKGs: Namespace and Workload:
            self.parser.add_argument(
                "--create_supervisor_namespace", action="store_true", help="Create supervisor cluster"
            )
            self.parser.add_argument("--create_workload_cluster", action="store_true", help="Create TKGs Workload")

            # For Extensions:
            self.parser.add_argument("--deploy_extensions", action="store_true", help="Deploy Extensions")

            # TKGs: wcp shutdown/bring up
            self.parser.add_argument("--wcp_bringup", action="store_true", help="WCP bring up")
            self.parser.add_argument("--wcp_shutdown", action="store_true", help="WCP Shutdown")

            # For VCD:
            self.parser.add_argument("--vcd_avi_configuration", action="store_true", help="VCD Avi config")
            self.parser.add_argument("--avi_cloud_configuration", action="store_true", help="AVI cloud config")
            self.parser.add_argument("--vcd_org_configuration", action="store_true", help="VCD org config")
            self.parser.add_argument("--cse_server_configuration", action="store_true", help="CSE server config")

            self.parser.add_argument("--verbose", action="store_true", help="Log verbosity")
            self.parser.add_argument("--status", action="store_true", help="Status of Arcas deployment")
            self.parser.add_argument("--cleanup", default=None, help="Arcas Cleanup", choices=SUPPORTED_CLEANUP_OPTIONS)
            self.parser.add_argument("--skip_precheck", action="store_true", help="Skip pre check")
            self.parser.add_argument("--skip_login_for_harbor", action="store_true")

            self.args, self.unknown = self.parser.parse_known_args()

            if self.unknown:
                self.parser.error(f"Unknown Arguments received: {self.unknown}")

            # Load Tanzu image to harbor Check
            if self.args.load_tanzu_image_to_harbor:
                self.verify_required_params(LOAD_TANZU_IMAGE_PARAMS)
                self.repo_name = self.args.repo_name
                self.tkg_bin_path = self.args.tkg_binaries_path
                self.harbor_util_obj = HarborUtils()

            # Preload Harbor status Check
            if self.args.get_harbor_preloading_status:
                self.verify_required_params(GET_STATUS_PARAMS)
                self.repo_name = self.args.repo_name
                self.harbor_util_obj = HarborUtils()

            # Check env and file is present, verify json file exists and valid
            if not any(
                [
                    self.args.help,
                    self.args.version,
                    self.args.get_harbor_preloading_status,
                    self.args.load_tanzu_image_to_harbor,
                    len(sys.argv) == 1,
                ]
            ):
                self.verify_required_params(MANDATORY_PARAMS_LIST)
                self.env = self.args.env
                self.json_file = self.args.file
                if not CommonUtils.is_file_exist(self.args.file):
                    raise FileNotFoundError(f"File not found: {self.json_file}")
                if not CommonUtils.is_json_valid(self.json_file):
                    raise JsonReadException("Json Read Exception occurred")
                self.set_payload_and_env()

        except argparse.ArgumentError as e:
            print(f"Exception Occurred: [ {e} ]")

    def set_payload_and_env(self):
        """
        Method to set headers and payload for requests API
        """
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Env": self.env,
        }

    def verify_required_params(self, reqd_params_list: list):
        """
        Method to verify and set the required parameters for command line options

        :param: reqd_params_list: List of required parameters to be validated against an argument
        """
        for arg in reqd_params_list:
            if eval(f"self.args.{arg}") is None:
                self.parser.error(f"Mandatory parameter --{arg} is missing")

    def arcas_usage(self):
        """
        Method to define arcas Usage
        """
        print(
            """
    Usage:
        For vSphere-VDS:
                   arcas --env vsphere --file <path_to_input_file>
                   [--avi_configuration][--tkg_mgmt_configuration]
                   [--shared_service_configuration][--workload_preconfig][--workload_deploy][--deploy_extensions]
        For vmc:
                   arcas --env  vmc --file <path_to_input_file>
                   [--vmc_pre_configuration][--avi_configuration][--tkg_mgmt_configuration]
                   [--shared_service_configuration][--workload_preconfig][--workload_deploy][--deploy_extensions]
        For vSphere-NSX-t:
                   arcas --env  vcf --file <path_to_input_file>
                   [--vcf_pre_configuration][--avi_configuration][--tkg_mgmt_configuration]
                   [--shared_service_configuration][--workload_preconfig][--workload_deploy][--deploy_extensions]
        For Tanzu with vSphere(VDS):
                  Enable WCP:
                   arcas --env vsphere --file <path_to_input_file>
                   [--avi_configuration][--avi_wcp_configuration][--enable_wcp]
                  Create Namespace and Workload Cluster:
                   arcas --env vsphere --file <path_to_input_file>
                   [--create_supervisor_namespace][--create_workload_cluster][--deploy_extensions]
                  Gracefully shutdown WCP:
                   arcas --env vsphere --file <path_to_input_file>
                   [--wcp_shutdown]
                  Bring back up the WCP cluster:
                   arcas --env vsphere --file <path_to_input_file>
                   [--wcp_bringup]
         For Vcd:
                   arcas --env vcd --file <path_to_input_file>
                   [--vcd_avi_configuration][--avi_cloud_configuration][--vcd_org_configuration]
                   [--cse_server_configuration]

    <path_to_input_file>: File used for deployment

    Cleanup Specific Flags :
        For vSphere-VDS:               arcas --env vsphere --file <path_to_input_file> --cleanup <cleanup_option>
        For vSphere-NSX-t:             arcas --env  vcf --file <path_to_input_file> --cleanup <cleanup_option>
        For vmc:                       arcas --env  vmc --file <path_to_input_file> --cleanup <cleanup_option>
        For Tanzu with vSphere(VDS):   arcas --env vsphere --file <path_to_input_file> --cleanup <cleanup_option>

        <cleanup_option>:   Common options are listed below and env specific options are provided under env sections.
                            Please note that cleanup options need to be run in reverse order of how they are
                            deployed i.e. order mentioned in above Usage section.

        Common options:
            all                             End to End cleanup
            avi_configuration               AVI Controller cleanup
            extensions                      Extensions cleanup
        TKG vSphere (VDS,NSX-t), VMC:
            tkgm_mgmt_cluster               Management cluster cleanup
            tkgm_shared_cluster             Shared cluster cleanup
            tkgm_workload_cluster           Workload cluter cleanup
        VMC:
            vmc_pre_configuration           VMC configuration cleanup
        vSphere-NSX-t:
            vcf_pre_configuration           NSX-t configuration cleanup
        Tanzu with vSphere(VDS):
            tkgs_supervisor_namespace       Supervisor namespace cleanup
            tkgs_workload_cluster           Workload cluster cleanup
            disable_wcp                     Disable wcp

    Available Flags:
        Mandatory Flags:
           --env                             IaaS Platform, 'vmc' or 'vsphere' or 'vcf'
           --file                            Path to Input File

        vSphere-NSX-t Specific Flag:
           --vcf_pre_configuration           Creates segments, Firewalls rules, Inventory Groups and Services
        VMC Specific Flag:
           --vmc_pre_configuration           Creates segments, Firewalls rules, Inventory Groups and Services
        TKGs Specific Flag:
           --avi_wcp_configuration           Configure avi cloud for wcp
           --create_supervisor_namespace     Create supervisor namespace
           --create_workload_cluster         Create workload cluster
           --enable_wcp                      Enable WCP

        Configuration Flags:
           --avi_configuration              Deploy and Configure AVI
           --tkg_mgmt_configuration         Configure ALB Components and Deploy TKG Management Cluster
           --shared_service_configuration   Configure ALB Components and Deploy TKG Shared Service Cluster and Labelling
           --workload_preconfig             Configure ALB for TKG Workload Cluster
           --workload_deploy                Deploy Workload Cluster and Add AKO Labels
           --deploy_extensions              Deploy extensions
           --help                           Help for Arcas
           --version                        Version Information
           --skip_precheck                  Skip preflight checks for the environment. Recommended only for test purpose
           --verbose                        Log Verbosity
           --get_harbor_preloading_status   Load tanzu image to harbor status
           --repo_name                      Harbor repository name
           --tkg_binaries_path              Absolute path for TKG binaries
           --status                         Get deployment status
    """
        )

    def arcas_version(self):
        """
        Method to get existing installed Arcas version
        """
        print(f"version: v{__version__}")
        self.safe_exit()

    def add_verbosity(self):
        """
        Method to print verbose logs
        """
        self.pro = subprocess.Popen(
            ["tail", "-n0", "-f", Paths.SIVT_LOG_FILE], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        for output in self.pro.stdout:
            if (self.pro.poll() is not None) or (len(output) == 0) or self.stop_thread:
                self.pro.kill()
                break
            output = output.rstrip()
            output = output.decode("utf-8")
            print(f"{output}")
        print("\n")

    def vcf_pre_configuration(self):
        print("Vcf_Pre_Configuration: Configuring vcf pre configuration")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env != Env.VCF:
                print("Only vcf env type is supported for vcf configuration.")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.VCF_PRECONFIG)
            res = self.req_api_obj.exec_req(
                req_type="POST", api_url=ApiUrl.VCF_PRE_CONFIG, headers=self.headers, data=open(self.json_file, "rb")
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.VCF_PRECONFIG)
                print("VCF pre configuration failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.VCF_PRECONFIG)
                print("VCF_Pre_Configuration: Configuring vcf pre configuration successfully")
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.VCF_PRECONFIG)
            print("VCF pre configuration failed " + str(e))
            self.safe_exit()

    def vmc_pre_configuration(self):
        """
        Method to call VMC Pre config API
        """
        print("Vmc_Pre_Configuration: Configuring vmc pre configuration")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env != Env.VMC:
                print("Only vmc env type is supported for vmc configuration.")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.VMC_PRECONFIG)
            res = self.req_api_obj.exec_req(
                req_type="POST", api_url=ApiUrl.VMC_PRE_CONFIG, headers=self.headers, data=open(self.json_file, "rb")
            )

            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.VMC_PRECONFIG)
                print("VCF pre configuration failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.VMC_PRECONFIG)
                print("VMC_Pre_Configuration: Configuring VMC pre configuration successfully")
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.VMC_PRECONFIG)
            print("VCF pre configuration failed " + str(e))
            self.safe_exit()

    def avi_configuration(self):
        """
        Method to call AVI config API
        """
        print("AVI_Configuration: Configuring AVI")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env not in SUPPORTED_ENV_LIST:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.AVI)
            res = self.req_api_obj.exec_req(
                req_type="POST",
                api_url=ApiUrl.AVI_CONFIG_URL[self.env],
                headers=self.headers,
                data=open(self.json_file, "rb"),
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.AVI)
                print("AVI configuration failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.AVI)
                print("AVI_Configuration: AVI configured Successfully")
                return "SUCCESS"
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.AVI)
            print("Exception : Avi configuration " + str(e))
            self.safe_exit()

    def shared_service_configuration(self):
        """
        Method to call Shared Service Config API
        """
        print("Shared_Service_Configuration: Configuring TKG Shared Services Cluster")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env not in SUPPORTED_NON_VCD_ENV_LIST:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.SHARED_SERVICE)

            res = self.req_api_obj.exec_req(
                req_type="POST",
                api_url=ApiUrl.SHARED_SERVICE_CONFIG_URL[self.env],
                headers=self.headers,
                data=open(self.json_file, "rb"),
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.SHARED_SERVICE)
                print("Shared service configuration failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.SHARED_SERVICE)
                print("Shared_Service_Configuration: TKG Shared Services Cluster deployed and configured Successfully")
                return "SUCCESS"
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.SHARED_SERVICE)
            print("Shared service configuration failed : " + str(e))
            self.safe_exit()

    def workload_preconfig(self):
        """
        Method to call Workload pre config
        """
        print("Workload_Preconfig: Configuring AVI objects for TKG Workload Clusters")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env not in SUPPORTED_NON_VCD_ENV_LIST:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.WORKLOAD_PRECONFIG)

            res = self.req_api_obj.exec_req(
                req_type="POST",
                api_url=ApiUrl.WORKLOAD_NTWRK_CONFIG_URL[self.env],
                headers=self.headers,
                data=open(self.json_file, "rb"),
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WORKLOAD_PRECONFIG)
                print("Workload pre configuration failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.WORKLOAD_PRECONFIG)
                print("Workload_Preconfig: AVI objects for TKG Workload Clusters Configured Successfully")
                return "SUCCESS"
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WORKLOAD_PRECONFIG)
            print("Workload pre configuration failed " + str(e))
            self.safe_exit()

    def workload_deploy(self):
        """
        Method to call workload deploy API
        """
        print("Workload_Deploy: Configuring TKG Workload Cluster")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env not in SUPPORTED_NON_VCD_ENV_LIST:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.WORKLOAD)

            res = self.req_api_obj.exec_req(
                req_type="POST",
                api_url=ApiUrl.WORKLOAD_CONFIG_URL[self.env],
                headers=self.headers,
                data=open(self.json_file, "rb"),
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WORKLOAD)
                print("Workload deploy failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.WORKLOAD)
                print("Workload_Deploy: TKG Workload Cluster deployed and configured Successfully")
                return "SUCCESS"
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WORKLOAD)
            print("Workload Cluster deployment failed " + str(e))
            self.safe_exit()

    def management_configuration(self):
        """
        Method to call Management config API
        """
        print("TKG_Mgmt_Configuration: Configuring TKG Management Cluster")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env not in SUPPORTED_NON_VCD_ENV_LIST:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.MGMT)

            res = self.req_api_obj.exec_req(
                req_type="POST",
                api_url=ApiUrl.MGMT_CONFIG_URL[self.env],
                headers=self.headers,
                data=open(self.json_file, "rb"),
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.MGMT)
                print("Management configuration failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.MGMT)
                print("TKG_Mgmt_Configuration: TKG Management cluster deployed and configured Successfully")
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.MGMT)
            print("Management configuration failed " + str(e))
            self.safe_exit()

    def deploy_app(self):
        """
        Method to call deploy app API
        """
        print("Deploying sample app....")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env not in SUPPORTED_NON_VCD_ENV_LIST:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()

            res = self.req_api_obj.exec_req(
                req_type="POST",
                api_url=ApiUrl.DEPLOY_APP_URL[self.env],
                headers=self.headers,
                data=open(self.json_file, "rb"),
            )
            if not self.req_api_obj.verify_resp(res):
                print("Deploy app: " + str(res.json()))
                self.safe_exit()
            else:
                print(str(res.json()["msg"]))
        except Exception as e:
            print("Deploy app failed " + str(e))
            self.safe_exit()

    def deploy_extensions(self):
        """
        Method to call Deploy extensions API
        """
        print("Deploy_Extensions: Deploying extensions")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env not in SUPPORTED_NON_VCD_ENV_LIST:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.EXTENSIONS)

            res = self.req_api_obj.exec_req(
                req_type="POST", api_url=ApiUrl.EXTENSIONS_URL, headers=self.headers, data=open(self.json_file, "rb")
            )

            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.EXTENSIONS)
                print("Deploy extensions failed" + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.EXTENSIONS)
                print("Deploy_Extensions: Deployed extensions Successfully")
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.EXTENSIONS)
            print("Deploy extensions failed" + str(e))
            self.safe_exit()

    def avi_wcp_configuration(self):
        """
        Method to call AVI WCP config API
        """
        print("AVI_WCP_Configuration: Configuring wcp")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env != Env.VSPHERE:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.WCP_CONFIG)

            res = self.req_api_obj.exec_req(
                req_type="POST",
                api_url=ApiUrl.AVI_WCP_CONFIG_URL,
                headers=self.headers,
                data=open(self.json_file, "rb"),
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WCP_CONFIG)
                print("Avi wcp configuration failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.WCP_CONFIG)
                print("AVI_Configuration: Configured wcp Successfully")
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WCP_CONFIG)
            print("AVI wcp configuration failed " + str(e))
            self.safe_exit()

    def enable_wcp(self):
        """
        Method to call Enable WCP API
        """
        print("Enable_Wcp: Enabling  WCP")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env != Env.VSPHERE:
                print("Wrong env type, please specify vmc or vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.WCP)

            res = self.req_api_obj.exec_req(
                req_type="POST", api_url=ApiUrl.ENABLE_WCP_URL, headers=self.headers, data=open(self.json_file, "rb")
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WCP)
                print("Enable WCP configuration failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.WCP)
                print("Enable_Wcp: Enabled WCP Successfully")
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WCP)
            print("Enable WCP configuration failed " + str(e))
            self.safe_exit()

    def create_supervisor_namespace(self):
        """
        Method to call supervisor namespace API
        """
        print("Supervisor_Name_Space: Creating supervisor namespace")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env != Env.VSPHERE:
                print("Wrong env type, please specify vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.NAMESPACE)

            res = self.req_api_obj.exec_req(
                req_type="POST",
                api_url=ApiUrl.SUPRVSR_NAMESPACE_URL,
                headers=self.headers,
                data=open(self.json_file, "rb"),
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.NAMESPACE)
                print("Supervisor namespace creation failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.NAMESPACE)
                print("Supervisor_Name_Space: Created supervisor name space Successfully")
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.NAMESPACE)
            print("Supervisor namespace creation failed " + str(e))
            self.safe_exit()

    def create_workload_cluster(self):
        """
        Method to call workload cluster API
        """
        print("Create_Workload_Cluster: Creating workload cluster")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env != Env.VSPHERE:
                print("Wrong env type, please specify vsphere")
                self.safe_exit()
            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.WORKLOAD)

            res = self.req_api_obj.exec_req(
                req_type="POST", api_url=ApiUrl.WORKLOAD_URL, headers=self.headers, data=open(self.json_file, "rb")
            )
            if not self.req_api_obj.verify_resp(res):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WORKLOAD)
                print("Create workload cluster failed " + str(res.json()))
                self.safe_exit()
            else:
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.WORKLOAD)
                print("Create_Workload_Cluster: Created workload cluster Successfully")
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.WORKLOAD)
            print("Create workload cluster failed " + str(e))
            self.safe_exit()

    def status(self):
        """
        Method to call status API
        """
        try:
            self.arcas_deco.table_decorator(
                table_title=f"ARCAS Deployment Status [v{__version__}]", table_fields=["Components", "Status"]
            )
            comp_list = self.tiny_db.get_all_db_entries()
            for comp in comp_list:
                elem = dict(comp)
                if elem["status"] != SivtStatus.NA and elem["status"] != self.env:
                    self.arcas_deco.add_row([elem["name"], elem["status"]])
            self.arcas_deco.table.align = "l"
            self.arcas_deco.print_table()
            self.safe_exit()
        except Exception as e:
            print("Error occurred while fetching deployment status -  " + str(e))
            self.safe_exit()

    def wcp_shutdown(self):
        """
        Method to call WCP shutdown API
        """
        print("ESXi username and password is required for the Gracefully shutting down WCP")
        msg = """\n
        Please provide username to connect to ESXi hosts: """
        user_response = input(msg)
        user_response = user_response.strip()
        esxi_user = user_response
        msg = """\n
        Please provide password to connect to ESXi hosts: """
        user_response = input(msg)
        user_response = user_response.strip()
        esxi_password = user_response
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Env": self.env,
            "User": esxi_user,
            "Password": esxi_password,
        }
        try:
            if self.env != Env.VSPHERE:
                print("Wrong env type, please specify vsphere")
                self.safe_exit()

            res = self.req_api_obj.exec_req(
                req_type="POST", api_url=ApiUrl.WCP_SHUTDOWN_URL, headers=headers, data=open(self.json_file, "rb")
            )
            if not self.req_api_obj.verify_resp(res):
                print("WCP shutdown failed: " + str(res.json()))
                self.safe_exit()
        except Exception as e:
            print("WCP shutdown failed: " + str(e))
            self.safe_exit()

    def wcp_bringup(self):
        """
        Method to call WCP bring up API
        """
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            if self.env != Env.VSPHERE:
                print("Wrong env type, please specify vsphere")
                self.safe_exit()

            res = self.req_api_obj.exec_req(
                req_type="POST", api_url=ApiUrl.WCP_BRINGUP_URL, headers=self.headers, data=open(self.json_file, "rb")
            )

            if not self.req_api_obj.verify_resp(res):
                print("WCP bringup failed: " + str(res.json()))
                self.safe_exit()
        except Exception as e:
            print("WCP bringup failed: " + str(e))
            self.safe_exit()

    def initialize_db(self):
        """
        Method to initialize tiny DB
        """
        self.tiny_db.initialize_db(env=self.env, json_file=self.json_file)

    def clean_up(self):
        """
        Method to call clean up API
        """
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        self.headers["x-access-tokens"] = token
        try:
            print("Session: Performing Cleanup for " + self.args.cleanup)
            cleanup_option = self.args.cleanup
            if self.env not in SUPPORTED_NON_VCD_ENV_LIST:
                print("Wrong env type, please specify vsphere, vmc or vcf")
                self.safe_exit()
            if cleanup_option == Cleanup.ALL:
                print("Fetching deployed components from environment")
                res = self.req_api_obj.exec_req(
                    req_type="POST",
                    api_url=ApiUrl.CLEANUP_PROMPT_URL,
                    headers=self.headers,
                    data=open(self.json_file, "rb"),
                )
                if not self.req_api_obj.verify_resp(res):
                    print("Cleanup failed: " + str(res.json()))
                    self.safe_exit()
                msg = (
                    """\nSkip cleanup of Content Libraries and Downloaded Kubernetes OVAs from vcenter env (Y/N) ? : """
                )
                user_response = input(msg)
                while user_response.lower() not in ["y", "yes", "no", "n"]:
                    msg = """\nSkip cleanup of Content Libraries and Downloaded Kubernetes OVAs from vcenter env (Y/N) ? : """
                    user_response = input(msg)
                user_response = user_response.strip()

                retain = True if user_response.lower() in ["y", "yes"] else False
                if retain:
                    print("Content-libraries and Kubernetes OVA will not be removed...")
                else:
                    print("Proceeding with complete cleanup...")

                comp_dict = {
                    "Workload Clusters": {"clstr_list": res.json()["WORKLOAD_CLUSTERS"], "retain": False},
                    "Management Clusters": {"clstr_list": res.json()["MANAGEMENT_CLUSTERS"], "retain": False},
                    "Kubernetes Templates": {"clstr_list": res.json()["KUBERNETES_TEMPLATES"], "retain": retain},
                    "Content Libraries": {"clstr_list": res.json()["CONTENT_LIBRARY"], "retain": retain},
                    "NSX Load Balancer": {"clstr_list": res.json()["AVI_VMS"], "retain": False},
                    "Resource Pools": {"clstr_list": res.json()["RESOURCE_POOLS"], "retain": False},
                    "Namespaces": {"clstr_list": res.json()["NAMESPACES"], "retain": False},
                    "Supervisor Clusters": {"clstr_list": res.json()["SUPERVISOR_CLUSTER"], "retain": False},
                    "Network Segments": {
                        "clstr_list": res.json()["NETWORK_SEGMENTS"] if self.env in [Env.VCF, Env.VMC] else "",
                        "retain": False,
                    },
                }
                print("""\n\nBelow resources from environment will be Cleaned-up.""")
                for comp, val in comp_dict.items():
                    if val["clstr_list"] and not val["retain"]:
                        print(f"{comp}: {val['clstr_list']}")
                msg = """\nPlease confirm if you wish to continue with cleanup (Y/N) ? : """

                user_response = input(msg)
                user_response = user_response.strip()
                if user_response.lower() == "y" or user_response.lower() == "yes":
                    print("Proceeding with cleanup...")
                elif user_response.lower() == "n" or user_response.lower() == "no":
                    print("Aborted Cleanup based on user response")
                    self.safe_exit()
                else:
                    print("Invalid response")
                    self.safe_exit()
                self.headers.update({"Retain": str(retain)})

            self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.CLEANUP)
            self.headers.update({"CLEANUP": cleanup_option})
            if (
                cleanup_option == Cleanup.AVI
                or cleanup_option == Cleanup.DISABLE_WCP
                or cleanup_option == Cleanup.MGMT_CLUSTER
            ):
                msg = (
                    """\nSkip cleanup of Content Libraries and Downloaded Kubernetes OVAs from vcenter vm (Y/N) ? : """
                )
                if cleanup_option == Cleanup.DISABLE_WCP:
                    msg = """\nSkip cleanup of Content Libraries from vcenter env (Y/N) ? : """
                elif cleanup_option == Cleanup.MGMT_CLUSTER:
                    msg = msg = """\nSkip cleanup of Deployed Kubernetes OVAs from vcenter env (Y/N) ? : """
                user_response = input(msg)
                while user_response.lower() not in ["y", "yes", "no", "n"]:
                    user_response = input(msg)
                user_response = user_response.strip()

                retain = True if user_response.lower() in ["y", "yes"] else False
                if retain:
                    print("Content-libraries and Kubernetes OVA will not be removed...")
                    self.headers.update({"Retain": "true"})
                else:
                    print("Proceeding with complete cleanup...")
                    self.headers.update({"Retain": "false"})
            response = self.req_api_obj.exec_req(
                req_type="POST", api_url=ApiUrl.CLEANUP_ENV_URL, headers=self.headers, data=open(self.json_file, "rb")
            )
            if not self.req_api_obj.verify_resp(response):
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.CLEANUP)
                print("Cleanup failed " + str(response.json()))
            else:
                # reset DB once cleanup is successful and set status of cleanup to pass
                self.tiny_db.truncate_db()
                self.initialize_db()
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.CLEANUP)
                print("Session: " + str(response.json()["msg"]))
                self.safe_exit()
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.CLEANUP)
            print("Cleanup failed: " + str(e))
            self.safe_exit()

    def skip_precheck(self):
        """
        Method to call skip precheck API
        """
        # self.precheck = True
        with open(Paths.SKIP_PRECHECK, "w") as fi:
            fi.write(str(self.precheck))

    def vcd_avi_configuration(self):
        """
        Method to call VCD AVI config API
        """
        if self.env == Env.VCD:
            file1 = self.json_file
            with open(file1, "r") as file_read:
                read = file_read.read()
            with open("/opt/vmware/arcas/src/vcd/tf-input.json", "w") as file_write:
                file_write.write(read)
            with open("/opt/vmware/arcas/src/vcd/tf-input.json", "r") as out:
                data1 = json.load(out)
            isDeploy = data1["envSpec"]["aviCtrlDeploySpec"]["deployAvi"]
            with open(TOKEN, "r") as file_read:
                token = file_read.read()
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Env": self.env,
                "x-access-tokens": token,
            }
            if str(isDeploy).lower() == "true":
                self.avi_configuration()
            else:
                print("INFO: Performing validations")
            isImportAviToVcd = self.get_state_from_vcd("avi")
            if isImportAviToVcd == "true":
                url = "http://localhost:5000/api/tanzu/upload_avi_cert"
                res = requests.request("POST", url, headers=headers, data=open(self.json_file, "rb"), verify=False)
                if res.json()["STATUS_CODE"] != 200:
                    print("Upload cert failed " + str(res.json()))
                    self.safe_exit()
                else:
                    print("INFO: Uploaded cert Successfully")
                out = {"import_ctrl": "true", "import_cloud": "false", "import_seg": "false"}
                with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "w") as file_out:
                    file_out.write(json.dumps(out, indent=4))
                os.environ["TF_LOG"] = "DEBUG"
                os.environ["TF_LOG_PATH"] = "/var/log/server/arcas.log"
                tf = Terraform(working_dir="/opt/vmware/arcas/src/vcd")
                return_code, stdout, stderr = tf.init(capture_output=False)
                return_code, stdout, stderr = tf.apply(
                    target="module.nsx-alb-res", capture_output=False, skip_plan=True, auto_approve=True
                )
                if return_code != 0:
                    print(stderr)
                    self.safe_exit()
            else:
                out = {"import_ctrl": "false", "import_cloud": "false", "import_seg": "false"}
                print("INFO: AVI imported to Vcd")

    def get_state_from_vcd(self, type):
        """
        Method to call get state from VCD
        """
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Env": self.env,
            "x-access-tokens": token,
        }
        cloud_state = getCloudSate(self.json_file)
        try:
            url = ApiUrl.VCD_URL[type]
        except KeyError:
            print("ERROR: Wrong type")
            url = ""
            self.safe_exit()
        response = requests.request("POST", url, headers=headers, data=open(self.json_file, "rb"), verify=False)
        if response.status_code != 200:
            print("ERROR: Failed to get list " + str(response.text))
            self.safe_exit()
        present = False
        with open(self.json_file, "r") as out:
            data1 = json.load(out)
        if type == "cloud":
            name = data1["envSpec"]["aviNsxCloudSpec"]["nsxtCloudVcdDisplayName"]
            res = response.json()["NSXT_CLOUD_VCD_LIST"]
        elif type == "avi":
            name = data1["envSpec"]["aviCtrlDeploySpec"]["aviVcdDisplayName"]
            res = response.json()["AVI_VCD_LIST"]
        elif type == "seg":
            name = data1["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["serviceEngineGroup"][
                "serviceEngineGroupVcdDisplayName"
            ]
            res = response.json()["SEG_VDC_LIST"]
        elif type == "org":
            name = data1["envSpec"]["cseSpec"]["svcOrgSpec"]["svcOrgName"]
            res = response.json()["ORG_LIST_VCD"]
        elif type == "org_vdc":
            name = data1["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["svcOrgVdcName"]
            res = response.json()["ORG_LIST_VCD"]
        elif type == "networks":
            name = data1["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["svcOrgVdcNetworkSpec"]["networkName"]
            res = response.json()["NETWORKS_LIST"]
        else:
            res = ""
            name = ""
            print("ERROR: Wrong type")
            self.safe_exit()
        for cloud in res:
            if cloud.strip() == name.strip():
                present = True
                break
        if type == "cloud":
            if cloud_state != "FOUND":
                print("ERROR:  Cloud not found in AVI")
                self.safe_exit()
        if present:
            import_cloud = "false"
        else:
            import_cloud = "true"
        return import_cloud

    def avi_cloud_configuration(self):
        """
        Method to call AVI cloud config
        """
        status = nsx_cloud_creation(self.json_file, True)
        if status[0] != "SUCCESS":
            self.safe_exit()
        with open(self.json_file, "r") as file_read:
            read = file_read.read()
        with open("/opt/vmware/arcas/src/vcd/tf-input.json", "w") as file_write:
            file_write.write(read)
        with open("/opt/vmware/arcas/src/vcd/tf-input.json", "r") as out1:
            data1 = json.load(out1)
        isDeployCloud = data1["envSpec"]["aviNsxCloudSpec"]["configureAviNsxtCloud"]
        isImported = self.get_state_from_vcd("cloud")
        with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "r") as out1:
            data2 = json.load(out1)
        out = {"import_ctrl": data2["import_ctrl"], "import_cloud": isImported, "import_seg": "false"}
        with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "w") as file_out:
            file_out.write(json.dumps(out, indent=4))
        if str(isDeployCloud).lower() == "true":
            print("INFO:  Validating Nsxt cloud Imported")
            if isImported == "true":
                os.environ["TF_LOG"] = "DEBUG"
                os.environ["TF_LOG_PATH"] = "/var/log/server/arcas.log"
                tf = Terraform(
                    working_dir="/opt/vmware/arcas/src/vcd", var_file="/opt/vmware/arcas/src/vcd/vars.tfvars.json"
                )
                return_code, stdout, stderr = tf.init(capture_output=False)
                return_code, stdout, stderr = tf.apply(
                    target="module.nsx-alb-res", capture_output=False, skip_plan=True, auto_approve=True
                )
                if return_code != 0:
                    print(stderr)
                    self.safe_exit()
            else:
                print("INFO: Nsx cloud is already imported to vcd")
        else:
            print("INFO:  User opted not to deploy cloud, validating if its present in vcd")
            isImported = self.get_state_from_vcd("cloud")
            if isImported == "false":
                print("INFO: Cloud already imported to vcd")
            else:
                print("ERROR: Cloud not imported to vcd")

    def vcd_org_configuration(self):
        """
        Method to call VCD org config
        """
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        with open(self.json_file, "r") as file_read:
            read = file_read.read()
        status = nsx_cloud_creation(self.json_file, True)
        if status[0] != "SUCCESS":
            self.safe_exit()
        with open("/opt/vmware/arcas/src/vcd/tf-input.json", "w") as file_write:
            file_write.write(read)
        os.environ["TF_LOG"] = "DEBUG"
        os.environ["TF_LOG_PATH"] = "/var/log/server/arcas.log"
        tf = Terraform(working_dir="/opt/vmware/arcas/src/vcd", var_file="/opt/vmware/arcas/src/vcd/vars.tfvars.json")
        return_code, stdout, stderr = tf.init(capture_output=False)
        isImportAvi_org_ToVcd = self.get_state_from_vcd("org")
        if isImportAvi_org_ToVcd == "true":
            return_code, stdout, stderr = tf.apply(
                target="module.org", capture_output=False, skip_plan=True, auto_approve=True
            )
            if return_code != 0:
                print(stderr)
                self.safe_exit()
        else:
            print("INFO: Org  is already imported")
        isImportAvi_org_Vcd = self.get_state_from_vcd("org_vdc")
        if isImportAvi_org_Vcd == "true":
            return_code, stdout, stderr = tf.apply(
                target="module.org-vdc", capture_output=False, skip_plan=True, auto_approve=True
            )
            if return_code != 0:
                print(stderr)
                self.safe_exit()
        else:
            print("INFO: Org Vcd is already imported")

        isImportAvi_seg_ToVcd = self.get_state_from_vcd("seg")
        if isImportAvi_seg_ToVcd == "true":
            with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "r") as out1:
                data2 = json.load(out1)
            out = {
                "import_ctrl": data2["import_ctrl"],
                "import_cloud": data2["import_cloud"],
                "import_seg": isImportAvi_seg_ToVcd,
            }
            with open("/opt/vmware/arcas/src/vcd/vars.tfvars.json", "w") as file_out:
                file_out.write(json.dumps(out, indent=4))
            return_code, stdout, stderr = tf.apply(
                target="module.nsx-alb-res", capture_output=False, skip_plan=True, auto_approve=True
            )
            if return_code != 0:
                print(stderr)
                self.safe_exit()
        else:
            print("INFO: Org Seg is already imported")

        # check gateway and network is present
        net_file = "/opt/vmware/arcas/src/vcd/net.json"
        isImport_network_ToVcd = self.get_state_from_vcd("networks")
        if isImport_network_ToVcd == "false":
            print("INFO: ORG Network is already created")

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Env": self.env,
            "x-access-tokens": token,
        }
        url = "http://localhost:5000/api/tanzu/listTier1Vcd"
        res = requests.request("POST", url, headers=headers, data=open(self.json_file, "rb"), verify=False)
        if res.json()["STATUS_CODE"] != 200:
            isimport_edge = "true"
        else:
            isimport_edge = "false"
            print("INFO: Tier-1 gateway is already created")

        out_net = {"create_t1_gtw": isimport_edge, "create_vcd_rtd_net": isImport_network_ToVcd}
        with open(net_file, "w") as file_out:
            file_out.write(json.dumps(out_net, indent=4))

        if isimport_edge == "true":
            return_code, stdout, stderr = tf.apply(
                target="module.networks", capture_output=False, skip_plan=True, auto_approve=True
            )
            if return_code != 0:
                print(stderr)
                self.safe_exit()

    def cse_server_configuration(self):
        """
        Method to call VCD server config
        """
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        with open(self.json_file, "r") as file_read:
            read = file_read.read()
        # with open(file) as f:
        #     data = json.load(f)
        with open("/opt/vmware/arcas/src/vcd/tf-input.json", "w") as file_write:
            file_write.write(read)
        os.environ["TF_LOG"] = "DEBUG"
        os.environ["TF_LOG_PATH"] = "/var/log/server/arcas.log"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Env": self.env,
            "x-access-tokens": token,
        }
        tf = Terraform(working_dir="/opt/vmware/arcas/src/vcd")
        return_code, stdout, stderr = tf.init(capture_output=False)
        if CAT_DICT["cse"] == "true" or CAT_DICT["k8s"] == "true":
            return_code, stdout, stderr = tf.apply(
                target="module.catalog", capture_output=False, skip_plan=True, auto_approve=True
            )
            if return_code != 0:
                print(stderr)
                self.safe_exit()
        else:
            print("INFO : Catalogs are already created")
        cse_upload_url = "http://localhost:5000/api/tanzu/upload_cse_catalog"
        response_cse = requests.request(
            "POST", cse_upload_url, headers=headers, data=open(self.json_file, "rb"), verify=False
        )
        cse_catalog = CseMarketPlace.CSE_OVA_NAME
        if response_cse.json()["STATUS_CODE"] != 200:
            print("ERROR: Failed " + str(response_cse.text))
            self.safe_exit()
        k8s_upload_url = "http://localhost:5000/api/tanzu/upload_k_catalog"
        response_ks8 = requests.request(
            "POST", k8s_upload_url, headers=headers, data=open(self.json_file, "rb"), verify=False
        )
        if response_ks8.json()["STATUS_CODE"] != 200:
            print("ERROR: Failed " + str(response_ks8.text))
            self.safe_exit()

        cse_server_config_file_path = "/opt/vmware/arcas/src/vcd/cse_server.json"
        out = {"token": "temp", "template_name": cse_catalog}
        with open(cse_server_config_file_path, "w") as file_out:
            file_out.write(json.dumps(out, indent=4))

        config_cse_plugin_url = "http://localhost:5000/api/tanzu/configure_cse_plugin"
        response_config_cse_plugin = requests.request(
            "POST", config_cse_plugin_url, headers=headers, data=open(self.json_file, "rb"), verify=False
        )
        if response_config_cse_plugin.json()["STATUS_CODE"] != 200:
            print("ERROR: Failed " + str(response_config_cse_plugin.text))
            self.safe_exit()
        return_code, stdout, stderr = tf.apply(
            target="module.cse-config", capture_output=False, skip_plan=True, auto_approve=True
        )
        if return_code != 0:
            print(stderr)
            self.safe_exit()
        create_server_config_url = "http://localhost:5000/api/tanzu/create_server_config_cse"
        response_cse_server_config = requests.request(
            "POST", create_server_config_url, headers=headers, data=open(self.json_file, "rb"), verify=False
        )
        if response_cse_server_config.json()["STATUS_CODE"] != 200:
            print("ERROR: Failed " + str(response_cse_server_config.text))
            self.safe_exit()

        access_token_url = "http://localhost:5000/api/tanzu/get_access_token_vapp"
        response_access_token = requests.request(
            "POST", access_token_url, headers=headers, data=open(self.json_file, "rb"), verify=False
        )
        if response_access_token.json()["STATUS_CODE"] != 200:
            print("ERROR: Failed " + str(response_access_token.text))
            self.safe_exit()

        cse_server_config_file_path = "/opt/vmware/arcas/src/vcd/cse_server.json"
        out = {"token": response_access_token.json()["token"], "template_name": cse_catalog}
        print("INFO: Waiting for 5m for upload to complete")
        time.sleep(300)
        with open(cse_server_config_file_path, "w") as file_out:
            file_out.write(json.dumps(out, indent=4))
        return_code, stdout, stderr = tf.apply(
            target="module.vapp", capture_output=False, skip_plan=True, auto_approve=True
        )
        if return_code != 0:
            print(stderr)
            self.safe_exit()

    def create_files(self, data, file):
        """
        Method to call create files
        """
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Env": self.env,
            "x-access-tokens": token,
        }
        list_catalog_url = "http://localhost:5000/api/tanzu/listCatalogVcd"
        cse_catalog = data["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["svcOrgCatalogSpec"]["cseOvaCatalogName"]
        response_catalog = requests.request(
            "POST", list_catalog_url, headers=headers, data=open(file, "rb"), verify=False
        )
        create_k8s_catalog = "false"
        create_catalog = "false"
        if response_catalog.json()["STATUS_CODE"] != 200:
            if str(response_catalog.json()["msg"]).__contains__("List is empty"):
                create_catalog = "true"
                create_k8s_catalog = "true"
            elif str(response_catalog.json()["msg"]).__contains__("Organization not found in VCD"):
                create_catalog = "true"
                create_k8s_catalog = "true"
            else:
                print("ERROR: Failed " + str(response_catalog.text))
                self.safe_exit()
        elif str(response_catalog.json()["msg"]).__contains__("List is empty"):
            create_catalog = "true"
            create_k8s_catalog = "true"
        else:
            cat_list = response_catalog.json()["CATALOG_LIST"]
            found = False
            if cat_list is not None:
                for cat in cat_list:
                    if cat == cse_catalog:
                        found = True
                        create_catalog = "true"
                        break
            else:
                create_catalog = "true"
            if found:
                create_catalog = "false"
        cse_config_file_path = "/opt/vmware/arcas/src/vcd/cseconfig.json"
        out = {
            "create_catalog": create_catalog,
            "upload_ova": "false",
            "catalog_item_name": cse_catalog,
            "ova_path": "/tmp/cse.ova",
        }
        with open(cse_config_file_path, "w") as file_out:
            file_out.write(json.dumps(out, indent=4))
        k8s_config_file_path = "/opt/vmware/arcas/src/vcd/kconfig.json"
        k8_catalog = data["envSpec"]["cseSpec"]["svcOrgVdcSpec"]["svcOrgCatalogSpec"]["k8sTemplatCatalogName"]
        if create_k8s_catalog == "true":
            pass
        else:
            found_ = False
            if cat_list is not None:
                for cat in cat_list:
                    if cat == k8s_config_file_path:
                        found_ = True
                        create_k8s_catalog = "true"
                        break
            else:
                create_k8s_catalog = "true"
            if found_:
                create_k8s_catalog = "false"
        out = {
            "create_catalog_k8s": create_k8s_catalog,
            "upload_ova_k8s": "false",
            "catalog_item_name_k8s": k8_catalog,
            "ova_path_k8s": "/tmp/k8s.ova",
        }
        with open(k8s_config_file_path, "w") as file_out:
            file_out.write(json.dumps(out, indent=4))

        cse_server_config_file_path = "/opt/vmware/arcas/src/vcd/cse_server.json"
        out = {"token": "temp_value", "template_name": "temp"}

        CAT_DICT["cse"] = create_k8s_catalog
        CAT_DICT["k8s"] = k8_catalog
        with open(cse_server_config_file_path, "w") as file_out:
            file_out.write(json.dumps(out, indent=4))

    def write_temp_json_file(self, file):
        """
        Method to call write temp json files
        """
        with open(file) as f:
            data = json.load(f)

        str_enc = str(data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["vcenterSsoPasswordBase64"])
        base64_bytes = str_enc.encode("ascii")
        enc_bytes = base64.b64decode(base64_bytes)
        VC_PASSWORD = enc_bytes.decode("ascii").rstrip("\n")
        sample_string_bytes = VC_PASSWORD.encode("ascii")

        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_string = base64_bytes.decode("ascii")
        vc_adrdress = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["vcenterAddress"]
        vc_user = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["vcenterSsoUser"]
        vc_datacenter = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["vcenterDatacenter"]
        vc_cluster = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["vcenterCluster"]

        vc_data_store = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["vcenterDatastore"]
        if not data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["contentLibraryName"]:
            lib = "TanzuAutomation-Lib"
        else:
            lib = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["contentLibraryName"]

        if not data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["aviOvaName"]:
            VC_AVI_OVA_NAME = "avi-controller"
        else:
            VC_AVI_OVA_NAME = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["aviOvaName"]

        if not data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["resourcePoolName"]:
            res = ""
        else:
            res = data["envSpec"]["aviCtrlDeploySpec"]["vcenterDetails"]["resourcePoolName"]
        if not data["envSpec"]["marketplaceSpec"]["refreshToken"]:
            refreshToken = ""
        else:
            refreshToken = data["envSpec"]["marketplaceSpec"]["refreshToken"]
        dns = data["envSpec"]["infraComponents"]["dnsServersIp"]
        searchDomains = data["envSpec"]["infraComponents"]["searchDomains"]
        ntpServers = data["envSpec"]["infraComponents"]["ntpServers"]
        net = data["envSpec"]["aviCtrlDeploySpec"]["aviMgmtNetwork"]["aviMgmtNetworkGatewayCidr"]
        mgmt_pg = data["envSpec"]["aviCtrlDeploySpec"]["aviMgmtNetwork"]["aviMgmtNetworkName"]

        enable_avi_ha = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["enableAviHa"]
        ctrl1_ip = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController01Ip"]
        ctrl1_fqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController01Fqdn"]
        if enable_avi_ha == "true":
            ctrl2_ip = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController02Ip"]
            ctrl2_fqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController02Fqdn"]
            ctrl3_ip = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController03Ip"]
            ctrl3_fqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController03Fqdn"]
            aviClusterIp = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviClusterIp"]
            aviClusterFqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviClusterFqdn"]
        else:
            ctrl2_ip = ""
            ctrl2_fqdn = ""
            ctrl3_ip = ""
            ctrl3_fqdn = ""
            aviClusterIp = ""
            aviClusterFqdn = ""
        str_enc_avi = str(data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviPasswordBase64"])
        base64_bytes_avi = str_enc_avi.encode("ascii")
        enc_bytes_avi = base64.b64decode(base64_bytes_avi)
        password_avi = enc_bytes_avi.decode("ascii").rstrip("\n")

        sample_string_bytes = password_avi.encode("ascii")

        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_password_avi = base64_bytes.decode("ascii")

        str_enc_avi = str(data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviBackupPassphraseBase64"])
        base64_bytes_avi = str_enc_avi.encode("ascii")
        enc_bytes_avi = base64.b64decode(base64_bytes_avi)
        password_avi_back = enc_bytes_avi.decode("ascii").rstrip("\n")
        sample_string_bytes = password_avi_back.encode("ascii")

        base64_bytes = base64.b64encode(sample_string_bytes)
        base64_string_back = base64_bytes.decode("ascii")
        aviSize = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviSize"]
        if not data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviCertPath"]:
            cert = ""
        else:
            cert = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviCertPath"]
        if not data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviCertKeyPath"]:
            cert_key = ""
        else:
            cert_key = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviCertKeyPath"]

        data = dict(
            envSpec=dict(
                vcenterDetails=dict(
                    vcenterAddress=vc_adrdress,
                    vcenterSsoUser=vc_user,
                    vcenterSsoPasswordBase64=base64_string,
                    vcenterDatacenter=vc_datacenter,
                    vcenterCluster=vc_cluster,
                    vcenterDatastore=vc_data_store,
                    contentLibraryName=lib,
                    aviOvaName=VC_AVI_OVA_NAME,
                    resourcePoolName=res,
                ),
                marketplaceSpec=dict(refreshToken=refreshToken),
                infraComponents=dict(dnsServersIp=dns, searchDomains=searchDomains, ntpServers=ntpServers),
            ),
            tkgComponentSpec=dict(
                aviMgmtNetwork=dict(aviMgmtNetworkName=mgmt_pg, aviMgmtNetworkGatewayCidr=net),
                aviComponents=dict(
                    aviPasswordBase64=base64_password_avi,
                    aviBackupPassphraseBase64=base64_string_back,
                    enableAviHa=enable_avi_ha,
                    aviController01Ip=ctrl1_ip,
                    aviController01Fqdn=ctrl1_fqdn,
                    aviController02Ip=ctrl2_ip,
                    aviController02Fqdn=ctrl2_fqdn,
                    aviController03Ip=ctrl3_ip,
                    aviController03Fqdn=ctrl3_fqdn,
                    aviClusterIp=aviClusterIp,
                    aviClusterFqdn=aviClusterFqdn,
                    aviSize=aviSize,
                    aviCertPath=cert,
                    aviCertKeyPath=cert_key,
                ),
                tkgMgmtComponents=dict(tkgMgmtDeploymentType="prod"),
            ),
        )
        with open("/opt/vmware/arcas/src/vcd/vcd_avi.json", "w") as f:
            json.dump(data, f)

    def precheck_env(self):
        print("Session: Performing prechecks")
        with open(TOKEN, "r") as file_read:
            token = file_read.read()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Env": self.env,
            "x-access-tokens": token,
        }
        if self.env == Env.VCD:
            headers1 = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Env": Env.VSPHERE,
                "x-access-tokens": token,
            }
            with open(self.json_file, "r") as file_read:
                data = json.load(file_read)
            isDeploy = data["envSpec"]["aviCtrlDeploySpec"]["deployAvi"]
            if isDeploy == "true":
                self.write_temp_json_file(self.json_file)
                url = "http://localhost:5000/api/tanzu/vmc/env/session"
                file1 = "/opt/vmware/arcas/src/vcd/vcd_avi.json"
                requests.request("POST", url, headers=headers1, data=open(file1, "rb"), verify=False)
            avi_var_file = "/opt/vmware/arcas/src/vcd/avi.json"
            isAviDeploy = data["envSpec"]["aviCtrlDeploySpec"]["deployAvi"]
            if isAviDeploy == "false":
                avi_fqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviClusterFqdn"]
                ip = avi_fqdn
            else:
                avi_fqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviController01Fqdn"]
                if isAviHaEnabled(data):
                    aviClusterFqdn = data["envSpec"]["aviCtrlDeploySpec"]["aviComponentsSpec"]["aviClusterFqdn"]
                    ip = aviClusterFqdn
                else:
                    ip = avi_fqdn
            out = {"aviFqdn": ip}
            with open(avi_var_file, "w") as file_out:
                file_out.write(json.dumps(out, indent=4))

            net_file = "/opt/vmware/arcas/src/vcd/net.json"

            out_net = {"create_t1_gtw": "true", "create_vcd_rtd_net": "true"}
            with open(net_file, "w") as file_out:
                file_out.write(json.dumps(out_net, indent=4))
            self.create_files(data, self.json_file)
            url = "http://localhost:5000/api/tanzu/getNsxManager"
            response = requests.request("POST", url, headers=headers, data=open(self.json_file, "rb"), verify=False)
            if response.json()["STATUS_CODE"] != 200:
                print("Precheck failed " + str(response.json()))
                self.safe_exit()
        try:
            if self.env == Env.VCD:
                url = "http://localhost:5000/api/tanzu/vcdprecheck"
            else:
                self.tiny_db.update_db_file(SivtStatus.IN_PROGRESS, Component.PRECHECK)
                url = "http://localhost:5000/api/tanzu/precheck"
            response = requests.request("POST", url, headers=headers, data=open(self.json_file, "rb"), verify=False)

            if response.json()["STATUS_CODE"] != 200:
                self.tiny_db.update_db_file(SivtStatus.FAILED, Component.PRECHECK)
                print("Precheck failed " + str(response.json()))
                self.safe_exit()
            else:
                print("Session: " + str(response.json()["msg"]))
                self.tiny_db.update_db_file(SivtStatus.SUCCESS, Component.PRECHECK)
        except Exception as e:
            self.tiny_db.update_db_file(SivtStatus.FAILED, Component.PRECHECK)
            print("Pre-check failed " + str(e))
            self.safe_exit()

    def display_logs(self):
        self.t1 = Thread(target=self.add_verbosity, name="t1")
        self.t1.start()

    def check_db_file(self):
        self.tiny_db.check_db_file(env=self.env, json_file=self.json_file)

    def is_session_active(self):
        url = ApiUrl.ACTIVE_SEESION
        session = requests.session()
        try:
            with open(COOKIES, "rb") as f:
                session.cookies.update(pickle.load(f))
        except Exception:
            return False
        response = session.get(url, verify=False)
        if response.status_code == 200:
            return True
        else:
            return False

    def run_arcas(self):
        """
        Method to execute Arcas project based on user inputs received
        """
        if len(sys.argv) == 1 or self.args.help:
            self.arcas_usage()
            sys.exit(0)
        if self.args.version:
            self.arcas_version()
        if self.args.skip_login_for_harbor:
            self.skip_login = True
        else:
            self.skip_login = False
        if not self.skip_login:
            if not self.is_session_active():
                server = """\nVc Server: """
                vc_server = input(server)
                username = """\nUsername: """
                user_name = input(username)
                password = getpass.getpass(prompt="Password: ")
                ecod_bytes = (user_name + ":" + password).encode("ascii")
                ecod_bytes = base64.b64encode(ecod_bytes)
                ecod_string = ecod_bytes.decode("ascii")
                headers = {"Accept": "application/json", "Authorization": "Basic " + ecod_string, "Server": vc_server}
                url = ApiUrl.LOGIN
                session = requests.session()
                response = session.post(url, headers=headers, verify=False)
                if response.status_code == 401 or response.status_code == 500:
                    print("Un-authorized")
                    self.safe_exit()
                else:
                    print("Logged in successfully")
                with open(COOKIES, "wb") as f:
                    pickle.dump(response.cookies, f)
                with open(TOKEN, "w") as file_out:
                    file_out.write(response.json()["token"])
        if self.args.verbose:
            self.display_logs()
        if self.args.load_tanzu_image_to_harbor:
            status_dict = self.harbor_util_obj.load_tanzu_image_to_harbor(self.repo_name, self.tkg_bin_path)
            if status_dict["status_code"] != 200:
                print("Harbor upload failed")
            self.safe_exit()
        if self.args.get_harbor_preloading_status:
            status_dict = self.harbor_util_obj.get_harbor_preloading_status(self.repo_name)
            if status_dict["status_code"] != 200:
                print("Preload status failed")
            self.safe_exit()
        if self.args.cleanup:
            self.clean_up()
            self.safe_exit()
        if self.args.wcp_shutdown:
            self.wcp_shutdown()
            self.safe_exit()
        if self.args.wcp_bringup:
            self.wcp_bringup()
            self.safe_exit()
        if self.args.skip_precheck:
            self.precheck = True
            self.skip_precheck()
        else:
            self.precheck = False
            self.skip_precheck()

        # Check DB file
        self.check_db_file()

        if self.args.status:
            self.status()
            self.safe_exit()

        # Precheck Env
        self.precheck_env()

        if self.precheck:
            self.tiny_db.update_db_file(SivtStatus.SKIP, Component.PRECHECK)

        try:
            for op, val in self.args.__dict__.items():
                if op in ARCAS_OPS_DICT and val:
                    eval(ARCAS_OPS_DICT[op])()
            self.safe_exit()
        except KeyError as e:
            print(f"Exception raised: [ {e} ]")
            self.safe_exit()

    def safe_exit(self):
        if not (self.pro is None):
            os.kill(self.pro.pid, signal.SIGTERM)
        if hasattr(self, "t1") and self.t1 is not None:
            if self.t1.isAlive():
                lock = self.t1._tstate_lock
                lock.release()
                self.t1._stop()
            else:
                self.t1.join()
        sys.exit(1)


def main():
    """
    Actual main method of the module
    """
    arc_cli = ArcasCli()
    arc_cli.run_arcas()


if __name__ == "__main__":
    arc_cli = ArcasCli()
    arc_cli.run_arcas()
