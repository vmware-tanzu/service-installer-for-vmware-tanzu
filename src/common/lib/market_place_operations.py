# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import copy
import json
import os

import requests
from flask import current_app

from common.operation.ShellHelper import runShellCommandAndReturnOutputAsList
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
        self.download_payload = {"deploymentFileId": "file_id", "eulaAccepted": "true", "productId": "product_id"}
        self.market_place_token = self.login_to_market_place()

    def login_to_market_place(self):
        """
        Uses marketplace login url and fetch access token for api authentication
        :return: the access token from marketplace
        """
        payload = {"refreshToken": self.refresh_token}
        json_object = json.dumps(payload, indent=4)
        sess = requests.request(
            "POST",
            MarketPlaceUrl.LOGIN_URL.format(domain_url=MarketPlaceUrl.DOMAIN_URL),
            headers=self.headers,
            data=json_object,
            verify=False,
        )
        if sess.status_code != 200:
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
                product = requests.get(MarketPlaceUrl.PRODUCT_SEARCH_URL, headers=headers, verify=False)
                if product.status_code != 200:
                    return None, "Failed to search  product " + product_name + " on Marketplace."
                for pro in product.json()["response"]["dataList"]:
                    if str(pro["displayname"]) == product_name:
                        return str(pro["slug"]), "SUCCESS"
            except Exception as e:
                return None, str(e)
        except Exception as e:
            return None, str(e)

    def get_product_details(self, product_name, product_version):
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
        product = requests.get(
            product_url,
            headers=headers,
            verify=False,
        )
        if product.status_code != 200:
            return None, "Failed to Obtain Product ID"
        else:
            product_checksum = None
            product_file_id = None
            product_filename = None
            product_id = product.json()["response"]["data"]["productid"]
            for metalist in product.json()["response"]["data"]["productdeploymentfilesList"]:
                if metalist["appversion"] == product_version and metalist["status"] == "ACTIVE":
                    product_checksum = metalist["hashdigest"]
                    product_file_id = metalist["fileid"]
                    product_filename = metalist["name"]
                    break
        return {
            "checksum": product_checksum,
            "file_id": product_file_id,
            "id": product_id,
            "filename": product_filename,
        }

    def download_product(self, product_id, file_id, remote_file_name, local_file_path, local_file_name):
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
        payload = copy.copy(self.download_payload)
        payload["deploymentFileId"] = file_id
        payload["productId"] = product_id
        current_app.logger.info(f"Retrieved product ID {product_id} from MarketPlace...")
        json_object = json.dumps(payload, indent=4).replace('"true"', "true")
        pre_signed_download_url = MarketPlaceUrl.DOWNLOAD_URL.format(
            domain_url=MarketPlaceUrl.DOMAIN_URL, product_id=product_id
        )
        pre_signed_url = requests.request(
            "POST", pre_signed_download_url, headers=headers, data=json_object, verify=False
        )
        if pre_signed_url.status_code != 200:
            return None, "Failed to obtain pre-signed URL"
        else:
            download_url = pre_signed_url.json()["response"]["presignedurl"]
        current_app.logger.info(f"Retrieved download URL {download_url} from MarketPlace...")
        current_app.logger.info(f"Downloading file and will be saved to {product_complete_path} on SIVT VM")
        current_app.logger.info("Download will take about 5 minutes to complete...")
        response_csfr = requests.request("GET", download_url, headers=headers, verify=False, timeout=600)
        if response_csfr.status_code != 200:
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
