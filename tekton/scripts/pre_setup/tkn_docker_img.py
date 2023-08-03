#!/usr/local/bin/python3

#  Copyright 2022 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

__author__ = "Selva, Abhishek Inani"

import json
import os
import re
import shutil
import requests
import shlex
import yaml
import subprocess
import logging
import traceback
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s:%(lineno)d | %(levelname)s | %(message)s')

class DockerHelper:

    def __init__(self):
        self.cmd = ''
        self.logger = logging.getLogger('DockerHelper')

    def run_process(self, cmd):
        self.logger.debug(f"Command to execute: \n\"{' '.join(cmd)}\"")
        popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
        for stdout_line in iter(popen.stdout.readline, ""):
            self.logger.debug(stdout_line)
        popen.stdout.close()
        return_code = popen.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, cmd)

    def run_return_output(self, fin):
        try:
            self.logger.debug(f"Command to execute: \n\"{' '.join(fin)}\"")
            proc = subprocess.Popen(
                fin,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE
            )
            output = proc.communicate()[0]
            formatted_output = output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m", "")
            self.logger.debug(
                f"Output: \n {'*' * 10}Output Start{'*' * 10}\n{formatted_output}\n{'*' * 10}Output End{'*' * 10}")
            return_code = 1 if formatted_output.__contains__("error") else 0
        except subprocess.CalledProcessError as e:
            return_code = 1
            formatted_output = e.output
        return formatted_output.rstrip("\n\r"), return_code

    def run_cmd_only(self, cmd: str, ignore_errors=False, msg=None):
        self.logger.debug(f"Running cmd: {cmd}")
        try:
            subprocess.call(shlex.split(cmd), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            self.logger.error(f"Error: {traceback.format_exc()}\n Error executing: {cmd}")

    def get_product_slug_id(self, product_name, headers):
        try:
            product = requests.get(
                MarketPlaceUrl.PRODUCT_SEARCH_URL, headers=headers,
                verify=False)
            if product.status_code != 200:
                return None, "Failed to search  product " + product_name + " on Marketplace."
            for pro in product.json()["response"]["dataList"]:
                if str(pro["displayname"]) == product_name:
                    return str(pro["slug"]), "SUCCESS"
        except Exception as e:
            return None, str(e)


class MarketPlaceUrl:
    URL = "https://gtw.marketplace.cloud.vmware.com"
    API_URL = "https://api.marketplace.cloud.vmware.com"
    PRODUCT_SEARCH_URL = API_URL + "/products?managed=false&filters={%22Publishers%22:[%22318e72f1-7215-41fa-9016-ef4528b82d0a%22]}"
    TANZU_PRODUCT = "Tanzu Kubernetes Grid"
    AVI_PRODUCT = "NSX Advanced Load Balancer"
    MARKETPLACE_KUBERNETES_SOLUTION_NAME = "tanzu-kubernetes-grid-1-1"

class GenerateTektonDockerImage:

    """Will generate Tekton docker image"""
    KIND_RELEASE_URL = "https://kind.sigs.k8s.io/dl/v0.17.0/kind-linux-amd64"

    def __init__(self, support_matrix_filepath) -> None:

        """
        All supported version of 2.x.x TKG* are considered backward compatible in Tekton 2.0
        The support-matrix file is updated every release.
        Docker images of every supported matrix release is built and loaded in cluster.
        Iterate through supported_tkg_version_list for multiple versions.
        Update support-matrix file for future release like tkg: ['2.1.0', '2.1.1']
        :param support_matrix_filepath:
        :return: None
        """

        self.token = None
        self.version = None
        self.jsonpath = None
        self.pkg_dir = "tanzu_pkg"
        self.sivt_docker_image = "sivt_tekton"
        self.tekton_worker_image = "tekton_worker"
        self.docker_helper = DockerHelper()
        self.logger = logging.getLogger('DockerImageBuilder')

        with open(support_matrix_filepath) as stream:
            try:
                support_matrix_dict = (yaml.safe_load(stream))
            except yaml.YAMLError as exc:
                raise Exception(f"Error Encountered parsing yaml error: {exc}")

        self.supported_tkg_version_list = support_matrix_dict['matrix']['tkg']

        values_file = os.path.join('.', 'values.yaml')
        with open(values_file) as stream:
            try:
                day2_data_dict = (yaml.safe_load(stream))
            except yaml.YAMLError as exc:
                raise Exception(f"Error Encountered parsing yaml error: {exc}")
        self.refresh_token = day2_data_dict['refreshToken']

    def check_docker_image_exists(self, docker_img):
        """Checks if this docker image exists.

        Args:
            docker_img (str): Name of a docker image.
        """
        try:
            cmd = ["docker", "inspect", "--type=image", docker_img]
            # The 'docker inspect ...' will return 0 if image exists and 1 otherwise.
            output, retcode = self.docker_helper.run_return_output(cmd)
            if "No such image" in output:
                retcode = 1
            return retcode
        except OSError as error:
            logging.error("DockerImageExists (image=%s) "
                               "check failed with message: '%s'" % (docker_img, str(error)))

    def generate_tkn_docker_image(self) -> bool:

        """
            Download three major binaries of tanzu, kubectl and yq cli based on version
            Iterate through supported_tkg_version_list to generate all supported
            docker images of supported matrix.
            docker images are tagged as sivt_tekton:v210, sivt_tekton:v211

        :return: None if Success
                 Bailout if Failure
        """
        file_grp = ["Tanzu Cli", "Kubectl Cluster CLI", "Yaml processor"]
        dckr_img_list = []
        status_dict = {}
        try:
            required_dckr_img_list = [f"{self.sivt_docker_image}:v{''.join(tkg_version.split('.'))}" for tkg_version in self.supported_tkg_version_list]
            required_dckr_img_list.append(f"{self.tekton_worker_image}:latest")

            for dckr_img in required_dckr_img_list:
                ret = self.check_docker_image_exists(dckr_img)
                if ret != 0:
                    dckr_img_list.append(dckr_img)
                else:
                    logging.info(f"Docker image: {dckr_img} exists. Skipping creating it....")

            for img in dckr_img_list:
                self.logger.info(f"Start building {img} image")
                if img == f"{self.tekton_worker_image}:latest":
                    status = self.build_docker_image(tkg_version='None', worker=True)
                    status_dict.update({img: status})
                elif img.startswith(f"{self.sivt_docker_image}:v"):
                    product, msg = self.get_meta_details_marketplace()
                    if product is None:
                        self.logger.error("Check if refresh token are correctly provided or not")
                        raise Exception(msg)

                    for tkg_version in self.supported_tkg_version_list:
                        for grp in file_grp:
                            meta_info = self.extract_meta_info(tkg_version, product, grp)
                            self.download_files_from_marketplace(meta_info)

                        self.download_external_binaries()
                        status = self.build_docker_image(tkg_version)
                        self.clean_downloads()
                        status_dict.update({img: status})
            logging.info(f"{status_dict}")
            return True if all([status for _, status in status_dict.items()]) else False
        except Exception as e:
            self.logger.error(f"Exception occurred as {e}")
            return False

    def get_meta_details_marketplace(self):

        """
        Method to get metadetails of marketplace URL
        """
        try:

            solution_name = MarketPlaceUrl.MARKETPLACE_KUBERNETES_SOLUTION_NAME

            self.logger.debug(("Solution Name: {}".format(solution_name)))

            if os.path.exists(self.pkg_dir):
                shutil.rmtree(self.pkg_dir)
            os.makedirs(self.pkg_dir)
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            payload = {
                "refreshToken": self.refresh_token
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
            _solution_name = self.docker_helper.get_product_slug_id(MarketPlaceUrl.TANZU_PRODUCT, headers)
            if _solution_name[0] is None:
                return None, "Failed to find product on Marketplace " + str(_solution_name[1])
            soln_name = _solution_name[0]
            self.logger.debug(f"Solution Name: {soln_name}")
            constructed_url = MarketPlaceUrl.API_URL + "/products/" + soln_name + "?isSlug=" + slug + "&ownorg=false"
            product = requests.get(constructed_url, headers=headers, verify=False)

            if product.status_code != 200:
                self.logger.debug(f"Product get text:{product.text} statuscode: {product.status_code}")
                return None, "Failed to Obtain Product ID"
            else:
                return product, "SUCCESS"

        except Exception as e:
            self.logger.error(f"Exception occurred: [ {e} ]")
            return None, False

    def extract_meta_info(self, tkg_version, product, grp):
        """
        Method to extract meta information's
        :param: product: product of which meta details needed
        :param: grp: Group of which meta details needed
        """
        try:
            meta_dict = {}
            objectid = None
            file_name = None
            app_version = None
            metafileid = None
            product_id = product.json()['response']['data']['productid']
            for metalist in product.json()['response']['data']['metafilesList']:
                if metalist['appversion'] == tkg_version:
                    if grp == "Kubectl Cluster CLI":
                        if str(metalist["groupname"]).strip("\t") == grp:
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
            self.logger.info(f"fileName: {file_name} app_version: {app_version} metafileid: {metafileid}")
            meta_dict.update({"object_id": objectid,
                              "app_version": app_version,
                              "metafile_id": metafileid,
                              "product_id": product_id,
                              "file_name": file_name})
            if (objectid or file_name or app_version or metafileid) is None:
                return None, "Failed to find the file details in Marketplace"
            return meta_dict
        except Exception as e:
            self.logger.error(f"Exception occurred as [ {e} ]")
            return False

    def download_files_from_marketplace(self, meta_info):
        """"
        Method to download files from marketplace
        :param: meta_info: Meta information's collected in earleir method
        """
        try:

            self.logger.info("Downloading file - " + meta_info["file_name"])
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
            self.logger.info('Marketplaceurl: {url} data: {data}'.format(url=MarketPlaceUrl.URL, data=json_object))
            constructed_url = MarketPlaceUrl.URL + "/api/v1/products/" + meta_info["product_id"] + "/download"
            presigned_url = requests.request("POST", constructed_url, headers=headers, data=json_object, verify=False)
            self.logger.info('presigned_url: {}'.format(presigned_url))
            self.logger.info('presigned_url text: {}'.format(presigned_url.text))
            if presigned_url.status_code != 200:
                return None, "Failed to obtain pre-signed URL"
            else:
                download_url = presigned_url.json()["response"]["presignedurl"]
            curl_inspect_cmd = 'curl -I -X GET {} --output /tmp/resp.txt'.format(download_url)
            self.docker_helper.run_cmd_only(curl_inspect_cmd)
            with open('/tmp/resp.txt', 'r') as f:
                data_read = f.read()
            if 'HTTP/1.1 200 OK' in data_read:
                self.logger.info('Proceed to Download')
                ova_path = os.path.join(self.pkg_dir, meta_info["file_name"])
                self.download_file(download_url, ova_path)
            else:
                self.logger.info('Error in presigned url/key: {} '.format(data_read.split('\n')[0]))
                return None, "Invalid key/url"
        except Exception as e:
            self.logger.error(f"Exception occurred as [ {e} ]")
            return False

    def download_external_binaries(self):
        """
        Method to download binaries other than VMware domain
        """
        # Download kind binary
        kind_bin_file = os.path.join(self.pkg_dir, "kind")
        self.download_file(GenerateTektonDockerImage.KIND_RELEASE_URL, kind_bin_file)

    def build_docker_image(self, tkg_version, worker=False):
        """
        Method to build docker image using dockerfile
        """
        try:
            # TODO: Move worker check in simple check.

            if worker:
                self.logger.info("Building tekton worker docker image using worker dockerfile")
                self.logger.info("Docker image creating in progress, may take 3~4 minutes")
                tag = 'latest'
                dckr_cmd = f"docker build -t {self.tekton_worker_image}:{tag} -f worker_dockerfile ."
                self.docker_helper.run_process(shlex.split(dckr_cmd))
                # Verify if docker image is created successfully or not
                vrfy_dkr_cmd = f"docker image inspect {self.tekton_worker_image}:{tag}"
                out, code = self.docker_helper.run_return_output(shlex.split(vrfy_dkr_cmd))
                if json.loads(out)[0]["RepoTags"][0] != f"{self.tekton_worker_image}:{tag}":
                    return False

            else:
                self.logger.info("Building docker image using sivt_tekton_dockerfile")
                self.logger.info("Loading image would take 3~4 minutes.")
                tag = "v" + ''.join(tkg_version.split("."))
                dckr_cmd = f"docker build -t {self.sivt_docker_image}:{tag} -f sivt_tekton_dockerfile ."
                self.logger.debug(f"Docker build command: {dckr_cmd}")
                self.docker_helper.run_process(shlex.split(dckr_cmd))

                # Verify if docker image is created successfully or not
                vrfy_dkr_cmd = f"docker image inspect {self.sivt_docker_image}:{tag}"
                out, code = self.docker_helper.run_return_output(shlex.split(vrfy_dkr_cmd))

                if json.loads(out)[0]["RepoTags"][0] != f"{self.sivt_docker_image}:{tag}":
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Exception occurred as [ {e} ]")
            return False

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
        self.docker_helper.run_process(clean_dwld)


if __name__ == "__main__":
    support_matrix_file_path = os.path.join("scripts", "template/support-matrix.yml")
    gen_dock_obj = GenerateTektonDockerImage(support_matrix_file_path)
    status = gen_dock_obj.generate_tkn_docker_image()
    if not status:
        raise Exception("Unable to build docker images")
