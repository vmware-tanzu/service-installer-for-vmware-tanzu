# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import copy
import hashlib
import json
import os
from http import HTTPStatus
from pathlib import Path

from flask import current_app

from common.operation.constants import ControllerLocation, KubernetesOva, Paths
from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
from common.replace_value import replaceValue, replaceValueSysConfig
from common.util.file_helper import FileHelper
from common.util.request_api_util import RequestApiUtil
from exceptions.custom_exceptions import LoginFailedException


class MarketPlaceUrl:
    DOMAIN_URL = "https://gtw.marketplace.cloud.vmware.com"
    LOGIN_URL = "{domain_url}/api/v1/user/login"
    PRODUCT_URL = "{domain_url}/products/{solution_name}?isSlug={slug}&ownorg=false"
    DOWNLOAD_URL = "{domain_url}/api/v1/products/{product_id}/download"
    API_URL = "https://api.marketplace.cloud.vmware.com"
    PRODUCT_SEARCH_URL = (
        API_URL + "/products?managed=false&filters={%22Publishers%22:[%22318e72f1-7215-41fa-9016-ef4528b82d0a%22]}"
    )
    TANZU_PRODUCT = "Tanzu Kubernetes Grid"
    AVI_PRODUCT = "NSX Advanced Load Balancer"
    VCD_RPODUCT = "Service Installer for VMware Tanzu"


class MarketPlaceUtils:
    """
    class will deal with all MarketPlace operations
    """

    def __init__(self, refresh_token):
        """
        During initialization, it will login to marketplace with CSP refresh token
        :param str refresh_token: refresh token from marketplace
        """
        self.refresh_token = refresh_token
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        self.avi_download_payload = {"deploymentFileId": "file_id", "eulaAccepted": "true", "productId": "product_id"}
        self.kubernetes_download_payload = {
            "eulaAccepted": "true",
            "appVersion": "app_version",
            "metafileid": "metafile_id",
            "metafileobjectid": "object_id",
        }
        self.market_place_token = self.login_to_market_place()

    def login_to_market_place(self):
        """
        Uses marketplace login url and fetch access token for api authentication
        :return: the access token from marketplace
        """
        payload = {"refreshToken": self.refresh_token}
        json_object = json.dumps(payload, indent=4)
        sess = RequestApiUtil.exec_req(
            "POST",
            MarketPlaceUrl.LOGIN_URL.format(domain_url=MarketPlaceUrl.DOMAIN_URL),
            headers=self.headers,
            data=json_object,
            verify=False,
        )
        if not RequestApiUtil.verify_resp(resp=sess, status_code=HTTPStatus.OK):
            # TODO raise exception
            raise LoginFailedException("Failed to login and obtain csp-auth-token")
        else:
            token = sess.json()["access_token"]
        return token

    def get_product_slug_id(self, product_name):
        """
        get product slug id using product name
        :returns: slug id of the product if found else NONE
        """
        try:
            headers = copy.copy(self.headers)
            token = {"csp-auth-token": self.market_place_token}
            headers.update(token)
            try:
                product = RequestApiUtil.exec_req(
                    "GET", MarketPlaceUrl.PRODUCT_SEARCH_URL, headers=headers, verify=False
                )
                if not RequestApiUtil.verify_resp(resp=product, status_code=HTTPStatus.OK):
                    return None, "Failed to search  product " + product_name + " on Marketplace."
                for pro in product.json()["response"]["dataList"]:
                    if str(pro["displayname"]) == product_name:
                        return str(pro["slug"]), "SUCCESS"
            except Exception as e:
                return None, str(e)
        except Exception as e:
            return None, str(e)

    def get_product_details(self, product_name):
        """
        get product details from marketplace using product name and version
        :param product_name: name of the product
        :param product_version: version of the product
        :return: products details of the product
        """
        slug = "true"
        headers = copy.copy(self.headers)
        token = {"csp-auth-token": self.market_place_token}
        headers.update(token)
        solution_name = self.get_product_slug_id(product_name)
        current_app.logger.info(f"Retrieved solution name {solution_name} from MarketPlace...")
        if solution_name[0] is None:
            return None, "Failed to find product on Marketplace " + str(solution_name[1])
        solution_name = solution_name[0]
        product_url = MarketPlaceUrl.PRODUCT_URL.format(
            domain_url=MarketPlaceUrl.API_URL, solution_name=solution_name, slug=slug
        )
        product = RequestApiUtil.exec_req(
            "GET",
            product_url,
            headers=headers,
            verify=False,
        )
        if not RequestApiUtil.verify_resp(resp=product, status_code=HTTPStatus.OK):
            return None, "Failed to Obtain Product ID"
        return product.json(), "SUCCESS"

    def download_product(self, product_id, payload, remote_file_name, local_file_path, local_file_name):
        """
        download product from marketplace and copy it to specified location
        :param product_id: product id of the product needs to download.
        :param file_id: file id of the product
        :param remote_file_name: file name of the product
        :param local_file_path: local directory where product needs to downloaded
        :param local_file_name: local file name of the product
        :return: True, the complete path of file downloaded else None
        """
        headers = copy.copy(self.headers)
        token = {"csp-auth-token": self.market_place_token}
        headers.update(token)
        product_complete_path = os.path.join(local_file_path, local_file_name)
        current_app.logger.info(f"Retrieved product ID {product_id} from MarketPlace...")
        json_object = json.dumps(payload, indent=4).replace('"true"', "true")
        pre_signed_download_url = MarketPlaceUrl.DOWNLOAD_URL.format(
            domain_url=MarketPlaceUrl.DOMAIN_URL, product_id=product_id
        )
        pre_signed_url = RequestApiUtil.exec_req(
            "POST", pre_signed_download_url, headers=headers, data=json_object, verify=False
        )
        if not RequestApiUtil.verify_resp(resp=pre_signed_url, status_code=HTTPStatus.OK):
            return None, "Failed to obtain pre-signed URL"
        else:
            download_url = pre_signed_url.json()["response"]["presignedurl"]
        current_app.logger.info(f"Retrieved download URL {download_url} from MarketPlace...")
        current_app.logger.info(f"Downloading file and will be saved to {product_complete_path} on SIVT VM")
        current_app.logger.info("Download will take about 5 minutes to complete...")
        response_csfr = RequestApiUtil.exec_req("GET", download_url, headers=headers, verify=False, timeout=600)
        if not RequestApiUtil.verify_resp(resp=response_csfr, status_code=HTTPStatus.OK):
            return None, response_csfr.text
        else:
            current_app.logger.info(
                f"{remote_file_name} Downloading completed putting it to {product_complete_path}..."
            )
            command = ["rm", "-rf", remote_file_name]
            runShellCommandAndReturnOutputAsList(command)
            with open(remote_file_name, "wb") as f:
                f.write(response_csfr.content)
        command = ["cp", remote_file_name, product_complete_path]
        output = runShellCommandAndReturnOutputAsList(command)
        if len(output[0][0]) > 1:
            current_app.logger.error(f"Error in copying: {output[0]}")
            return None, output[0]
        return True, product_complete_path

    def push_to_content_library(self, govc_operations, file):
        """
        push AVI OVA to content library
        :param govc_operations: govc operations object
        :param file: local file path
        :return: success if ova pushed content lib else None
        """
        output = govc_operations.create_content_lib_if_not_exist(
            content_lib=ControllerLocation.CONTROLLER_CONTENT_LIBRARY
        )
        if not output:
            current_app.logger.info(f"Error in creating {ControllerLocation.CONTROLLER_CONTENT_LIBRARY}...")
            return None, f"Error in creating {ControllerLocation.CONTROLLER_CONTENT_LIBRARY}"
        current_app.logger.info("Pushing AVI controller to content library")
        output = govc_operations.govc_client.import_ova_to_content_lib(
            content_lib=ControllerLocation.CONTROLLER_CONTENT_LIBRARY, local_file=file
        )
        if output is None or output == "":
            return None, "Failed to upload AVI controller to content library"
        return "SUCCESS", 200

    def download_avi_local(self, product_details, govc_operations):
        """
        download ova and push it to content library
        :param product_details: avi product details from market place
        :param market_place_utils: marketplace utilities object
        :param govc_operations: govc operations object
        :return: success if ova pushed content lib else None
        """
        current_app.logger.info("Downloading AVI controller from MarketPlace...")
        payload = copy.copy(self.avi_download_payload)
        payload["deploymentFileId"] = product_details["file_id"]
        payload["productId"] = product_details["id"]
        product_output = self.download_product(
            payload=payload,
            product_id=product_details["id"],
            remote_file_name=product_details["filename"],
            local_file_path=ControllerLocation.OVA_DOWNLOAD_PATH,
            local_file_name=ControllerLocation.CONTROLLER_NAME + ".ova",
        )
        if not product_output[0]:
            current_app.logger.info("Error in downloading AVI controller from MarketPlace...")
            return None, "Error in downloading AVI controller from MarketPlace"
        return self.push_to_content_library(govc_operations=govc_operations, file=product_output[1])

    def verify_check_sum_for_ova(self, product_details, local_ova_path):
        """
        verify the local downloaded AVI ova checksum
        :param product_details: avi product details from market place
        :param local_ova_path: local ova downloaded path
        :return: True if matches else False
        """
        current_app.logger.info("AVI ova is already downloaded, validating checksum...")
        current_app.logger.info("Retrieved solution name from MarketPlace...")
        checksum = product_details["checksum"]
        if checksum is None:
            current_app.logger.warn("Failed to get checksum of AVI Controller OVA from MarketPlace")
        else:
            current_app.logger.info("Validating checksum of downloaded file")
            original_checksum = hashlib.sha1(FileHelper.file_as_bytes(open(local_ova_path, "rb"))).hexdigest()
            return original_checksum.strip() == checksum.strip()

    def download_avi_ova(self, govc_operations, avi_version):
        """
         check whether ova is present in content lib or not
         if local ova exists then verify its checksum with market place ova
        :param govc_operations: govc operations object
        :param avi_version: avi version needs to be downloaded
        :param market_place_utils:
        """
        avi_ova_name = ControllerLocation.CONTROLLER_NAME + ".ova"
        avi_name = ControllerLocation.CONTROLLER_NAME
        local_avi_download_location = os.path.join(ControllerLocation.OVA_DOWNLOAD_PATH, avi_ova_name)
        local_avi_path = Path(local_avi_download_location)
        # verify AVI OVA in content lib
        content_lib = "/" + ControllerLocation.CONTROLLER_CONTENT_LIBRARY + "/"
        if govc_operations.check_ova_is_present(content_library=content_lib, ova_name=avi_name):
            current_app.logger.info(f"AVI controller {avi_name} ova  is already present in content library")
            return "SUCCESS", 200
        else:
            current_app.logger.info(f"AVI controller {avi_name} ova  is not present in content library")
        # get AVI details from Marketplace AVI
        product_details = self.get_product_details(product_name=MarketPlaceUrl.AVI_PRODUCT)
        if product_details[0] is None:
            current_app.logger.error(f"AVI controller {avi_name} ova  is not found under {MarketPlaceUrl.AVI_PRODUCT}")
            return None, "Failed to AVI controller ova product details in market place"

        product_checksum = None
        product_file_id = None
        product_filename = None
        product_id = product_details[0]["response"]["data"]["productid"]
        for metalist in product_details[0]["response"]["data"]["productdeploymentfilesList"]:
            if metalist["appversion"] == avi_version and metalist["status"] == "ACTIVE":
                product_checksum = metalist["hashdigest"]
                product_file_id = metalist["fileid"]
                product_filename = metalist["name"]
                break
        product_details = {
            "checksum": product_checksum,
            "file_id": product_file_id,
            "id": product_id,
            "filename": product_filename,
        }

        # AVI OVA is downloaded and not uploaded to content lib.
        if local_avi_path.exists():
            # verify local avi checksum
            if self.verify_check_sum_for_ova(product_details, local_avi_download_location):
                current_app.logger.info("Checksum verified for AVI Controller OVA")
                return self.push_to_content_library(govc_operations=govc_operations, file=local_avi_download_location)
            else:
                current_app.logger.warn(
                    f"NSX ALB ova is present in {local_avi_path} directory but checksum is incorrect "
                    f"deleting the file..."
                )
                FileHelper.delete_file(str(local_avi_path))
                # download avi on local upload it to content lib
                return self.download_avi_local(product_details=product_details, govc_operations=govc_operations)
        else:
            # download avi on local upload it to content lib
            current_app.logger.info("Downloading AVI controller from MarketPlace...")
            return self.download_avi_local(product_details=product_details, govc_operations=govc_operations)

    def download_kuberenetes_ova_local(self, product_details, local_file_name):
        payload = copy.copy(self.kubernetes_download_payload)
        payload["appVersion"] = product_details["app_version"]
        payload["metafileid"] = product_details["metafileid"]
        payload["metafileobjectid"] = product_details["objectid"]

        download_response = self.download_product(
            product_id=product_details["product_id"],
            payload=payload,
            remote_file_name=product_details["remote_file_name"],
            local_file_path=ControllerLocation.OVA_DOWNLOAD_PATH,
            local_file_name=local_file_name,
        )
        if download_response[0] is None:
            return None, download_response[1]
        return download_response[1], "Kubernetes OVA download successful"

    def download_kubernetes_ova(self, govc_operations, network, kubernetes_ova_version, base_os, base_os_version):
        if base_os == "photon":
            ova_groupname = KubernetesOva.MARKETPLACE_PHOTON_GROUPNAME
            file = KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + kubernetes_ova_version
            template = KubernetesOva.MARKETPLACE_PHOTON_KUBERNETES_FILE_NAME + "-" + kubernetes_ova_version
        elif base_os == "ubuntu":
            ova_groupname = KubernetesOva.MARKETPLACE_UBUTNU_GROUPNAME
            file = KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + kubernetes_ova_version
            template = KubernetesOva.MARKETPLACE_UBUNTU_KUBERNETES_FILE_NAME + "-" + kubernetes_ova_version
        else:
            return None, "Invalid ova type " + base_os

        filename = file + ".ova"

        if govc_operations.check_vm_template_is_present(template):
            return "SUCCESS", "ALREADY_PRESENT"

        product_details = self.get_product_details(MarketPlaceUrl.TANZU_PRODUCT)
        if product_details[0] is None:
            return None, product_details[1]
        else:
            product_id = product_details[0]["response"]["data"]["productid"]
            for metalist in product_details[0]["response"]["data"]["metafilesList"]:
                if (
                    metalist["version"] == base_os_version[1:]
                    and str(metalist["groupname"]).strip("\t") == ova_groupname
                    and metalist["status"] == "ACTIVE"
                ):
                    objectid = metalist["metafileobjectsList"][0]["fileid"]
                    ovaName = metalist["metafileobjectsList"][0]["filename"]
                    app_version = metalist["appversion"]
                    metafileid = metalist["metafileid"]
                    checksum = metalist["metafileobjectsList"][0]["hashdigest"]

        if (objectid or ovaName or app_version or metafileid) is None:
            return None, "Failed to find the file details in Marketplace"

        product_details = {
            "app_version": app_version,
            "metafileid": metafileid,
            "objectid": objectid,
            "checksum": checksum,
            "product_id": product_id,
            "remote_file_name": ovaName,
        }

        my_file = os.path.join(ControllerLocation.OVA_DOWNLOAD_PATH, filename)
        download_ova = True
        if Path(my_file).exists():
            if self.verify_check_sum_for_ova(product_details, my_file):
                current_app.logger.info("Kubernetes ova is already downloaded and checksum verified for the OVA")
                download_ova = False
            else:
                FileHelper.delete_file(my_file)

        if download_ova:
            download_response = self.download_kuberenetes_ova_local(product_details, filename)
            if download_response[0] is None:
                return None, download_response[1]

        replaceValueSysConfig(Paths.KUBE_OVA_JSON, "Name", "name", file)
        replaceValue(Paths.KUBE_OVA_JSON, "NetworkMapping", "Network", network)
        current_app.logger.info("Pushing " + file + " to vcenter and making as template")

        output = govc_operations.govc_client.deploy_ova_template(Paths.KUBE_OVA_JSON, my_file)
        if output is None or output == "":
            return None, "Failed export kubernetes ova to vCenter"
        return "SUCCESS", "DEPLOYED"
