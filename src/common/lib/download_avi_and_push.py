# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import hashlib
import os
from pathlib import Path

from flask import current_app

from common.common_utilities import file_as_bytes
from common.lib.market_place_operations import MarketPlaceUrl
from common.operation.constants import ControllerLocation


def push_to_content_library(govc_operations, file):
    """
    push AVI OVA to content library
    :param govc_operations: govc operations object
    :param file: local file path
    :return: success if ova pushed content lib else None
    """
    output = govc_operations.create_content_lib_if_not_exist(content_lib=ControllerLocation.CONTROLLER_CONTENT_LIBRARY)
    if not output:
        current_app.logger.info(f"Error in creating {ControllerLocation.CONTROLLER_CONTENT_LIBRARY}...")
        return None, f"Error in creating {ControllerLocation.CONTROLLER_CONTENT_LIBRARY}"
    current_app.logger.info("Pushing AVI controller to content library")
    output = govc_operations.govc_client.import_ova_to_content_lib(
        content_lib=ControllerLocation.CONTROLLER_CONTENT_LIBRARY, local_file=file
    )
    if output[1] != 0:
        return None, "Failed to upload AVI controller to content library"
    return "SUCCESS", 200


def download_avi_local(product_details, market_place_utils, govc_operations):
    """
    download ova and push it to content library
    :param product_details: avi product details from market place
    :param market_place_utils: marketplace utilities object
    :param govc_operations: govc operations object
    :return: success if ova pushed content lib else None
    """
    current_app.logger.info("Downloading AVI controller from MarketPlace...")
    product_output = market_place_utils.download_product(
        product_id=product_details["id"],
        file_id=product_details["file_id"],
        remote_file_name=product_details["filename"],
        local_file_path=ControllerLocation.OVA_DOWNLOAD_PATH,
        local_file_name=ControllerLocation.CONTROLLER_NAME + ".ova",
    )
    if not product_output[0]:
        current_app.logger.info("Error in downloading AVI controller from MarketPlace...")
        return None, "Error in downloading AVI controller from MarketPlace"
    return push_to_content_library(govc_operations=govc_operations, file=product_output[1])


def verify_check_sum_for_avi(product_details, local_avi_path):
    """
    verify the local downloaded AVI ova checksum
    :param product_details: avi product details from market place
    :param local_avi_path: local avi ova downloaded path
    :return: True if matches else False
    """
    current_app.logger.info("AVI ova is already downloaded, validating checksum...")
    current_app.logger.info("Retrieved solution name from MarketPlace...")
    checksum = product_details["checksum"]
    if checksum is None:
        current_app.logger.warn("Failed to get checksum of AVI Controller OVA from MarketPlace")
    else:
        current_app.logger.info("Validating checksum of downloaded file")
        original_checksum = hashlib.sha1(file_as_bytes(open(local_avi_path, "rb"))).hexdigest()
        return original_checksum.strip() == checksum.strip()


def download_avi_ova(govc_operations, avi_version, market_place_utils):
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
    # get AVI details from Marketplace AVI
    product_details = market_place_utils.get_product_details(
        product_name=MarketPlaceUrl.AVI_PRODUCT, product_version=avi_version
    )
    if not product_details:
        current_app.logger.error(f"AVI controller {avi_name} ova  is not found under {MarketPlaceUrl.AVI_PRODUCT}")
        return None, "Failed to AVI controller ova product details in market place"
    # AVI OVA is downloaded and not uploaded to content lib.
    if local_avi_path.exists():
        # verify local avi checksum
        if verify_check_sum_for_avi(product_details, local_avi_download_location):
            current_app.logger.info("Checksum verified for AVI Controller OVA")
            return push_to_content_library(govc_operations=govc_operations, file=local_avi_download_location)
        else:
            current_app.logger.warn(
                f"NSX ALB ova is present in {local_avi_path} directory but checksum is incorrect "
                f"deleting the file..."
            )
            delete_cmd = "rm " + str(local_avi_path)
            os.system(delete_cmd)
            # download avi on local upload it content lib
            return download_avi_local(
                product_details=product_details, market_place_utils=market_place_utils, govc_operations=govc_operations
            )
    else:
        # download avi on local upload it content lib
        current_app.logger.info("Downloading AVI controller from MarketPlace...")
        return download_avi_local(
            product_details=product_details, market_place_utils=market_place_utils, govc_operations=govc_operations
        )


def create_content_lib_push_ova(local_avi_download_location, govc_operations):
    """
    push local downloaded AVI OVA to content lib
    :param local_avi_download_location: local avi ova downloaded path
    :param govc_operations: govc operations object
    """
    output = govc_operations.create_content_lib_if_not_exist(content_lib=ControllerLocation.CONTROLLER_CONTENT_LIBRARY)
    if not output:
        current_app.logger.info(f"Error in creating {ControllerLocation.CONTROLLER_CONTENT_LIBRARY}...")
        return None, f"Error in creating {ControllerLocation.CONTROLLER_CONTENT_LIBRARY}"
    current_app.logger.info("Pushing AVI controller to content library")
    output = govc_operations.govc_client.import_ova_to_content_lib(
        content_lib=ControllerLocation.CONTROLLER_CONTENT_LIBRARY, local_file=local_avi_download_location
    )
    if output[1] != 0:
        return None, "Failed to upload AVI controller to content library"
    return "SUCCESS", 200
