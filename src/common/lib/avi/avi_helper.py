# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
from http import HTTPStatus

import polling2
from flask import current_app

from common.lib.avi.avi_constants import AVIDataFiles
from common.util.file_helper import FileHelper
from common.util.request_api_util import RequestApiUtil


class AVIHelper:
    """
    list of static methods for AVI operation help
    """

    @staticmethod
    def pem_file_to_lines(file_path):
        """
        change pem file content to the lines
        """
        lines = FileHelper.read_lines_from_file(file_path=file_path)
        certificate = ""
        for ln in lines:
            if ln != "\n":
                certificate += ln.strip().replace("\r", "") + r"\n"
        return certificate.strip("\n")

    @staticmethod
    @polling2.poll_decorator(step=10, timeout=600)
    def poll_api_response_10_secs_counter(url, headers, verify, data=None):
        """
        polling method for SE response
        """
        response = RequestApiUtil.exec_req("GET", url, headers=headers, data=data, verify=verify)
        if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return response.json()["count"] > 1
        current_app.logger.info("Waited for for api and retrying")

    @staticmethod
    def generate_vsphere_configured_subnets(begin_ip, end_ip, prefix_ip, prefix_mask):
        file_name = AVIDataFiles.NETWORK_DETAILS
        data = FileHelper.load_json(spec_path=file_name)
        listing = []
        list_of_static_ip = []
        test = dict(
            range=dict(begin=dict(addr=begin_ip, type="V4"), end=dict(addr=end_ip, type="V4")),
            type="STATIC_IPS_FOR_VIP_AND_SE",
        )
        list_of_static_ip.append(test)
        listing.append(
            dict(
                prefix=dict(ip_addr=dict(addr=prefix_ip, type="V4"), mask=prefix_mask),
                static_ip_ranges=list_of_static_ip,
            )
        )
        dic = dict(configured_subnets=listing)
        data.update(dic)
        FileHelper.dump_json(file=file_name, json_dict=data)

    @staticmethod
    def generate_vsphere_configure_subnets_for_se_and_vip(begin_ip, end_ip, prefix_ip, prefix_mask):
        file_name = AVIDataFiles.NETWORK_DETAILS
        data = FileHelper.load_json(spec_path=file_name)
        se_start_ip = begin_ip
        vip_end_ip = end_ip
        split_ip_array = begin_ip.split(".")
        split_ip_array = ".".join(split_ip_array[:3]), ".".join(split_ip_array[3:])
        se_end_ip = split_ip_array[0] + "." + str(int(split_ip_array[1]) + 19)
        vip_start_ip = split_ip_array[0] + "." + str(int(split_ip_array[1]) + 20)
        listing = []
        list_of_static_ip = []
        se_test = dict(
            range=dict(begin=dict(addr=se_start_ip, type="V4"), end=dict(addr=se_end_ip, type="V4")),
            type="STATIC_IPS_FOR_SE",
        )
        vip_test = dict(
            range=dict(begin=dict(addr=vip_start_ip, type="V4"), end=dict(addr=vip_end_ip, type="V4")),
            type="STATIC_IPS_FOR_VIP",
        )

        list_of_static_ip.append(se_test)
        list_of_static_ip.append(vip_test)
        listing.append(
            dict(
                prefix=dict(ip_addr=dict(addr=prefix_ip, type="V4"), mask=prefix_mask),
                static_ip_ranges=list_of_static_ip,
            )
        )
        dic = dict(configured_subnets=listing)
        data.update(dic)
        dhcp_dic = dict(dhcp_enabled=False)
        data.update(dhcp_dic)
        FileHelper.dump_json(file=file_name, json_dict=data)

    @staticmethod
    def generate_vsphere_configured_subnets_for_se(se_begin_ip, se_end_ip, prefix_ip, prefix_mask):
        file_name = AVIDataFiles.NETWORK_DETAILS
        data = FileHelper.load_json(spec_path=file_name)
        listing = []
        list_of_static_ip = []
        test1 = dict(
            range=dict(begin=dict(addr=se_begin_ip, type="V4"), end=dict(addr=se_end_ip, type="V4")),
            type="STATIC_IPS_FOR_SE",
        )
        list_of_static_ip.append(test1)
        listing.append(
            dict(
                prefix=dict(ip_addr=dict(addr=prefix_ip, type="V4"), mask=prefix_mask),
                static_ip_ranges=list_of_static_ip,
            )
        )
        dic = dict(configured_subnets=listing)
        data.update(dic)
        FileHelper.dump_json(file=file_name, json_dict=data)
