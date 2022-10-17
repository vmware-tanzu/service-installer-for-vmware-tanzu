#!/usr/local/bin/python3

#  Copyright 2022 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

__author__ = "Abhishek Inani"

import json
import os
import shutil
import requests

from constants.constants import Paths, KubernetesOva, MarketPlaceUrl

from util.logger_helper import LoggerHelper
from util.ShellHelper import runProcess
from model.run_config import RunConfig
from util.tkg_util import TkgUtil
from util.common_utils import checkenv
from util.govc_client import GovcClient
from util.local_cmd_helper import LocalCmdHelper
from util import cmd_runner
from util.common_utils import envCheck
from util.avi_api_helper import getProductSlugId
logger = LoggerHelper.get_logger(name='Docker Image Creation')


class GenerateTektonDockerImage:
    """Will generate Tekton docker image"""
    def __init__(self, root_dir, run_config: RunConfig) -> None:
        self.run_config = run_config
        self.version = None
        self.jsonpath = None
        self.pkg_dir = "tanzu_pkg"
        self.docker_img_name = "sivt_tekton"
        self.state_file_path = os.path.join(root_dir, Paths.STATE_PATH)
        self.tkg_util_obj = TkgUtil(run_config=self.run_config)
        self.tkg_version_dict = self.tkg_util_obj.get_desired_state_tkg_version()
        if "tkgs" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.TKGS_WCP_MASTER_SPEC_PATH)
            self.tkg_version = self.tkg_version_dict["tkgs"]
        elif "tkgm" in self.tkg_version_dict:
            self.jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
            self.tkg_version = self.tkg_version_dict["tkgm"]
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
        self.env = self.env[0]

        check_env_output = checkenv(self.jsonspec)
        if check_env_output is None:
            msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                  "incorrect spec provided."
            raise Exception(msg)
        self.govc_client = GovcClient(self.jsonspec, LocalCmdHelper())
        self.kube_config = os.path.join(self.run_config.root_dir, Paths.REPO_KUBE_TKG_CONFIG)
        self.kube_version = KubernetesOva.KUBERNETES_OVA_LATEST_VERSION
        self.reftoken = self.run_config.user_cred.refreshToken

    def generate_tkn_docker_image(self) -> None:
        """
        Method to generate Tekton docker image
        :return: None
        """
        file_grp = ["Tanzu Cli", "Kubectl Cluster CLI", "Yaml processor"]
        product = self.get_meta_details_marketplace()
        for grp in file_grp:
            meta_info = self.extract_meta_info(product, grp)
            self.download_files_from_marketplace(meta_info)
        self.build_docker_image()
        self.clean_downloads()

    def get_meta_details_marketplace(self):
        """
        Method to get metadetails of marketplace URL
        """
        solutionName = KubernetesOva.MARKETPLACE_KUBERNETES_SOLUTION_NAME
        logger.debug(("Solution Name: {}".format(solutionName)))

        if os.path.exists(self.pkg_dir):
            shutil.rmtree(self.pkg_dir)
        os.makedirs(self.pkg_dir)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "refreshToken": self.reftoken
        }
        json_object = json.dumps(payload, indent=4)
        sess = requests.request("POST", MarketPlaceUrl.URL + "/api/v1/user/login", headers=headers,
                                data=json_object, verify=False)
        if sess.status_code != 200:
            return None, "Failed to login and obtain csp-auth-token"
        else:
            self.token = sess.json()["access_token"]
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "csp-auth-token": self.token
        }
        slug = "true"
        _solutionName = getProductSlugId(MarketPlaceUrl.TANZU_PRODUCT, headers)
        if _solutionName[0] is None:
            return None, "Failed to find product on Marketplace " + str(_solutionName[1])
        solutionName = _solutionName[0]
        product = requests.get(
            MarketPlaceUrl.API_URL + "/products/" + solutionName + "?isSlug=" + slug + "&ownorg=false", headers=headers,
            verify=False)
        if product.status_code != 200:
            return None, "Failed to Obtain Product ID"
        else:
            return product

    def extract_meta_info(self, product, grp):
        """
        Method to extract meta information's
        :param: product: product of which meta details needed
        :param: grp: Group of which meta details needed
        """
        meta_dict = {}
        objectid = None
        file_name = None
        app_version = None
        metafileid = None
        product_id = product.json()['response']['data']['productid']
        for metalist in product.json()['response']['data']['metafilesList']:
            if metalist['appversion'] == self.tkg_version:
                if grp == "Kubectl Cluster CLI":
                    if metalist["version"] == self.kube_version[1:] and str(metalist["groupname"]).strip("\t") \
                            == grp:
                        objectid = metalist["metafileobjectsList"][0]['fileid']
                        file_name = metalist["metafileobjectsList"][0]['filename']
                        app_version = metalist['appversion']
                        metafileid = metalist['metafileid']
                        break
                else:
                    if str(metalist["groupname"]).strip("\t") == grp:
                        objectid = metalist["metafileobjectsList"][0]['fileid']
                        file_name = metalist["metafileobjectsList"][0]['filename']
                        app_version = metalist['appversion']
                        metafileid = metalist['metafileid']
                        break
        logger.info("ovaName: {ovaName} app_version: {app_version} metafileid: {metafileid}".format(ovaName=file_name,
                                                                                                    app_version=app_version,
                                                                                                    metafileid=metafileid))
        meta_dict.update({"object_id": objectid,
                          "app_version": app_version,
                          "metafile_id": metafileid,
                          "product_id": product_id,
                          "file_name": file_name})
        if (objectid or file_name or app_version or metafileid) is None:
            return None, "Failed to find the file details in Marketplace"
        return meta_dict

    def download_files_from_marketplace(self, meta_info):
        """"
        Method to download files from marketplace
        :param: meta_info: Meta information's collected in earleir method
        """
        logger.info("Downloading file - " + meta_info["file_name"])
        rcmd = cmd_runner.RunCmd()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "csp-auth-token": self.token
        }
        payload = {
            "eulaAccepted": "true",
            "appVersion": meta_info["app_version"],
            "metafileid": meta_info["metafile_id"],
            "metafileobjectid": meta_info["object_id"]
        }

        json_object = json.dumps(payload, indent=4).replace('\"true\"', 'true')
        logger.info('--------')
        logger.info('Marketplaceurl: {url} data: {data}'.format(url=MarketPlaceUrl.URL, data=json_object))
        presigned_url = requests.request("POST",
                                         MarketPlaceUrl.URL + "/api/v1/products/" + meta_info["product_id"] + "/download",
                                         headers=headers, data=json_object, verify=False)
        logger.info('presigned_url: {}'.format(presigned_url))
        logger.info('presigned_url text: {}'.format(presigned_url.text))
        if presigned_url.status_code != 200:
            return None, "Failed to obtain pre-signed URL"
        else:
            download_url = presigned_url.json()["response"]["presignedurl"]
        curl_inspect_cmd = 'curl -I -X GET {} --output /tmp/resp.txt'.format(download_url)
        rcmd.run_cmd_only(curl_inspect_cmd)
        with open('/tmp/resp.txt', 'r') as f:
            data_read = f.read()
        if 'HTTP/1.1 200 OK' in data_read:
            logger.info('Proceed to Download')
            ova_path = os.path.join(self.pkg_dir, meta_info["file_name"])
            self.download_file(download_url, ova_path)
        else:
            logger.info('Error in presigned url/key: {} '.format(data_read.split('\n')[0]))
            return None, "Invalid key/url"

    def build_docker_image(self):
        """
        Method to build docker image using dockerfile
        """
        logger.info("Building dokcer image using dockerfile")
        #tag = "v" + ''.join(self.tkg_version.split("."))
        tag = "tkn"
        dckr_cmd = ["docker", "build", "-t", f"{self.docker_img_name}:{tag}", "-f", "dockerfile", "."]
        runProcess(dckr_cmd)

    def download_file(self, url, dwl_file):
        """
        Method to download pre-requisites files needed to build docker image
        :param: URL to be downloaded
        :param: dwl_file: Output file name
        """
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(dwl_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return dwl_file

    def clean_downloads(self):
        """
        Method to clean unwanted downloaded tar files
        """
        clean_dwld = ["rm", "-rf", self.pkg_dir]
        runProcess(clean_dwld)
