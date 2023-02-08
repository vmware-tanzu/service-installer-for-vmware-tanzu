#!/usr/local/bin/python3

#  Copyright 2022 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

__author__ = "Abhishek Inani"

import json
import os
import shutil
import requests
import shlex
import argparse
import subprocess


class MarketPlaceUrl:
    """Class to define Marketplace URLs and other URLs"""
    URL = "https://gtw.marketplace.cloud.vmware.com"
    API_URL = "https://api.marketplace.cloud.vmware.com"
    PRODUCT_SEARCH_URL = API_URL + "/products?managed=false&filters={%22Publishers%22:[%22318e72f1-7215-41fa-9016-ef4528b82d0a%22]}"
    TANZU_PRODUCT = "Tanzu Kubernetes Grid"
    AVI_PRODUCT = "NSX Advanced Load Balancer"

class GenerateTektonDockerImage:
    """Will generate Tekton docker image"""
    KIND_RELEASE_URL = "https://kind.sigs.k8s.io/dl/v0.17.0/kind-linux-amd64"
    def __init__(self) -> None:
        try:
            self.kubernetes_ova_dict = {"1.5.3": {"KUBERNETES_OVA_LATEST_VERSION": "v1.22.8",
                                                  "MARKETPLACE_KUBERNETES_SOLUTION_NAME": "tanzu-kubernetes-grid-1-1"},
                                        "1.5.4": {"KUBERNETES_OVA_LATEST_VERSION": "v1.22.9",
                                                  "MARKETPLACE_KUBERNETES_SOLUTION_NAME": "tanzu-kubernetes-grid-1-1"},
                                        "1.6.0": {"KUBERNETES_OVA_LATEST_VERSION": "v1.23.8",
                                                  "MARKETPLACE_KUBERNETES_SOLUTION_NAME": "tanzu-kubernetes-grid-1-1"}}
        except Exception as e:
            print(f"ERROR: Please specify supported tkg version: {e}")
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--tkg_version", help="TKG release version like 1.5.3, 1.5.4 etc", required=True)
        self.parser.add_argument("--refresh_token", help="Market place token", required=True)
        args = self.parser.parse_args()

        self.tkg_version = args.tkg_version
        self.reftoken = args.refresh_token

        self.pkg_dir = "tanzu_pkg"
        self.docker_img_name = "sivt_tekton"
        self.docker_img_tag = "v" + ''.join(self.tkg_version.split("."))

        self.kube_version = self.kubernetes_ova_dict[self.tkg_version]["KUBERNETES_OVA_LATEST_VERSION"]

    def generate_tkn_docker_image(self) -> bool:
        """
        Method to generate Tekton docker image
        :return: None
        """
        file_grp = ["Tanzu Cli", "Kubectl Cluster CLI", "Yaml processor"]
        try:
            product, msg = self.get_meta_details_marketplace()
            if product is None:
                print("Check if refresh token are correctly provided or not")
                raise Exception(msg)
            for grp in file_grp:
                meta_info = self.extract_meta_info(product, grp)
                self.download_files_from_marketplace(meta_info)
            self.download_external_binaries()
            status = self.build_docker_image()
            self.clean_downloads()
            return status
        except Exception as e:
            print(f"Exception occurred as {e}")
            return False

    def get_meta_details_marketplace(self):
        """
        Method to get metadetails of marketplace URL
        """
        try:

            solutionName = self.kubernetes_ova_dict[self.tkg_version]["MARKETPLACE_KUBERNETES_SOLUTION_NAME"]
            print(("Solution Name: {}".format(solutionName)))

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
                                    data=json_object)
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
            _solutionName = GenerateTektonDockerImage.get_product_slug_id(MarketPlaceUrl.TANZU_PRODUCT, headers)
            if _solutionName[0] is None:
                return None, "Failed to find product on Marketplace " + str(_solutionName[1])
            solutionName = _solutionName[0]
            product = requests.get(
                MarketPlaceUrl.API_URL + "/products/" + solutionName + "?isSlug=" + slug + "&ownorg=false",
                headers=headers)
            if product.status_code != 200:
                return None, "Failed to Obtain Product ID"
            else:
                return product, "SUCCESS"
        except Exception as e:
            print(f"Exception occurred: [ {e} ]")
            return None, False

    def extract_meta_info(self, product, grp):
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
            print("ovaName: {ovaName} app_version: {app_version} metafileid: {metafileid}".format(ovaName=file_name,
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
        except Exception as e:
            print(f"Exception occurred as [ {e} ]")
            return False

    def download_files_from_marketplace(self, meta_info):
        """"
        Method to download files from marketplace
        :param: meta_info: Meta information's collected in earleir method
        """
        try:

            print("Downloading file - " + meta_info["file_name"])
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
            print('--------')
            print('Marketplaceurl: {url} data: {data}'.format(url=MarketPlaceUrl.URL, data=json_object))
            presigned_url = requests.request("POST",
                                             MarketPlaceUrl.URL + "/api/v1/products/" + meta_info["product_id"] + "/download",
                                             headers=headers, data=json_object)
            print('presigned_url: {}'.format(presigned_url))
            print('presigned_url text: {}'.format(presigned_url.text))
            if presigned_url.status_code != 200:
                return None, "Failed to obtain pre-signed URL"
            else:
                download_url = presigned_url.json()["response"]["presignedurl"]
            curl_inspect_cmd = f"curl -I -X GET {download_url} --output /tmp/resp.txt"
            GenerateTektonDockerImage.execute(shlex.split(curl_inspect_cmd))
            with open('/tmp/resp.txt', 'r') as f:
                data_read = f.read()
            if 'HTTP/1.1 200 OK' in data_read:
                print('Proceed to Download')
                ova_path = os.path.join(self.pkg_dir, meta_info["file_name"])
                self.download_file(download_url, ova_path)
            else:
                print('Error in presigned url/key: {} '.format(data_read.split('\n')[0]))
                return None, "Invalid key/url"
        except Exception as e:
            print(f"Exception occurred as [ {e} ]")
            return False

    def download_external_binaries(self):
        """
        Method to download binaries other than VMware domain
        """
        # Download kind binary
        kind_bin_file = os.path.join(self.pkg_dir, "kind")
        self.download_file(GenerateTektonDockerImage.KIND_RELEASE_URL, kind_bin_file)

    def build_docker_image(self):
        """
        Method to build docker image using dockerfile
        """
        try:
            print("Building dokcer image using dockerfile")

            dckr_cmd = f"docker build -t {self.docker_img_name}:{self.docker_img_tag} -f dockerfile ."
            GenerateTektonDockerImage.execute(shlex.split(dckr_cmd))

            # Verify if docker image is created successfully or not
            vrfy_dkr_cmd = f"docker image inspect {self.docker_img_name}:{self.docker_img_tag}"
            out, code = GenerateTektonDockerImage.execute(shlex.split(vrfy_dkr_cmd), capture_output=True)

            if json.loads(out)[0]["RepoTags"][0] != f"{self.docker_img_name}:{self.docker_img_tag}":
                return False
            return True
        except Exception as e:
            print(f"Exception occurred as [ {e} ]")
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
        try:
            if os.path.isdir(self.pkg_dir):
                shutil.rmtree(self.pkg_dir)
        except OSError as e:
            print(f"Error: [ {e} ]")

    @staticmethod
    def get_product_slug_id(product_name, headers) -> tuple:
        """
        Method to return product slugid from Marketplace
        """
        try:
            product = requests.get(
                MarketPlaceUrl.PRODUCT_SEARCH_URL, headers=headers)
            if product.status_code != 200:
                return None, f"Failed to search  product {product_name} on Marketplace."
            for pro in product.json()["response"]["dataList"]:
                if str(pro["displayname"]) == product_name:
                    return str(pro["slug"]), "SUCCESS"
        except Exception as e:
            return None, str(e)

    @staticmethod
    def execute(cmd, capture_output=False):
        """"
        Method to execute commands using subprocess module"""
        print(f"Command to execute: \n\"{' '.join(cmd)}\"")
        if capture_output:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE
                )
                output = proc.communicate()[0]
                formatted_output = output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m", "")
                print(
                    f"Output: \n {'*' * 10}Output Start{'*' * 10}\n{formatted_output}\n{'*' * 10}Output End{'*' * 10}")
                return_code = 1 if formatted_output.__contains__("error") else 0
            except subprocess.CalledProcessError as e:
                return_code = 1
                formatted_output = e.output
            return formatted_output.rstrip("\n\r"), return_code
        else:
            popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
            for stdout_line in iter(popen.stdout.readline, ""):
                print(stdout_line)
            popen.stdout.close()
            return_code = popen.wait()
            if return_code:
                raise subprocess.CalledProcessError(return_code, cmd)


if __name__ == "__main__":
    dckr_img = GenerateTektonDockerImage()
    dckr_img.generate_tkn_docker_image()
