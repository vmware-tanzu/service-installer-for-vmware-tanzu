# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json
import pathlib
import time
from http import HTTPStatus
from json import JSONDecodeError
from pathlib import Path

import polling2
from flask import current_app

from common.common_utilities import envCheck
from common.constants.alb_api_constants import AlbEndpoint, AlbPayload
from common.lib.avi.avi_base_operations import AVIBaseOperations
from common.lib.avi.avi_constants import AVIDataFiles
from common.lib.avi.avi_helper import AVIHelper
from common.operation.constants import Cloud, ControllerLocation, Env, NSXtCloud, ServiceName, VrfType
from common.replace_value import replaceValueSysConfig
from common.util.file_helper import FileHelper
from common.util.request_api_util import RequestApiUtil


class AVIInfraOps(AVIBaseOperations):
    COUNT = 0
    VC_NAME = "SIVT_VC"

    def __init__(self, avi_host, password, vcenter_host, vcenter_user_name, vcenter_password):
        """ """
        super().__init__(avi_host, password)
        self.avi_version = self.obtain_avi_version()[0]
        self.second_csrf = self.obtain_second_csrf()
        self.headers = self._operation_headers(self.second_csrf)
        self.headers = self._operation_headers(self.second_csrf)
        self.vcenter_host = vcenter_host
        self.vcenter_user_name = vcenter_user_name
        self.vcenter_password = vcenter_password

        env = envCheck()
        if env[1] != 200:
            message = f"Wrong env provided {env[0]}"
            current_app.logger.error(message)
            raise Exception(str(message))
        self.env = env[0]

    def fetch_content_library(self, content_library_name=None):
        """
        :param content_library_name: content library name to fetch from
        :return: returns content library id if it's found in vCenter
        """
        try:
            if not content_library_name:
                content_library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
            url = AlbEndpoint.RETRIEVE_CONTENT_LIB.format(ip=self.avi_host)
            body = {
                "host": self.vcenter_host,
                "username": self.vcenter_user_name,
                "password": self.vcenter_password,
            }
            json_object = json.dumps(body, indent=4)
            response = RequestApiUtil.exec_req("POST", url, headers=self.headers, data=json_object, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            for library in response.json()["resource"]["vcenter_clibs"]:
                if library["name"] == content_library_name:
                    return "Success", library["id"]
            return None, "CONTENT_LIBRARY_NOT_FOUND"
        except Exception as e:
            return None, str(e)

    def create_new_cloud(self, cloud_name, datacenter, license_type="enterprise"):
        """
        create new cloud in AVI
        :param cloud_name: name of the cloud to be crated on AVI
        :param datacenter: datacenter
        :param license_type: type of AVI license essentials/enterprise
        :return: new cloud url response
        """
        if "/" in str(datacenter):
            dc = datacenter[datacenter.rindex("/") + 1 :]
        else:
            dc = datacenter
        library, status_lib = self.fetch_content_library(content_library_name="")
        if library is None:
            return None, status_lib
        true_content_lib_body = {
            "vcenter_configuration": {
                "use_content_lib": True,
                "content_lib": {"id": status_lib},
            }
        }
        false_content_lib_body = {
            "vcenter_configuration": {
                "use_content_lib": False,
            }
        }
        content_lib_body = false_content_lib_body if license_type == "essentials" else true_content_lib_body
        body = AlbPayload.CREATE_CLOUD.format(
            name=cloud_name,
            vcenter_host=self.vcenter_host,
            vcenter_user_name=self.vcenter_user_name,
            vcenter_password=self.vcenter_password,
            data_center=dc,
        )
        body = json.loads(body)
        body["vcenter_configuration"].update(content_lib_body["vcenter_configuration"])
        json_object = json.dumps(body, indent=4)
        cloud_url = AlbEndpoint.CLOUD.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("POST", cloud_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            FileHelper.delete_file(file_path=AVIDataFiles.NEW_CLOUD_INFO)
            response_obj = response.json()
            FileHelper.dump_json(json_dict=response_obj, file=AVIDataFiles.NEW_CLOUD_INFO)
            return response_obj["url"], "SUCCESS"

    def _get_cloud_data(self, cloud_name):
        """
        helper method in fetching cloud data with the help of cloud data
        """
        url = AlbEndpoint.CLOUD.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            for res in response.json()["results"]:
                if res["name"] == cloud_name:
                    return True, response.json(), res
        return "NOT_FOUND", "SUCCESS"

    def get_cloud_status(self, cloud_name):
        """
        fetch the status of cloud from AVI
        :param cloud_name: name of the cloud to fetch from vCenter
        :return: cloud status from AVI
        """
        data = self._get_cloud_data(cloud_name=cloud_name)
        if data[0] is None or data[0] == "NOT_FOUND":
            return data
        FileHelper.delete_file(file_path=AVIDataFiles.NEW_CLOUD_INFO)
        FileHelper.dump_json(file=AVIDataFiles.NEW_CLOUD_INFO, json_dict=data[1])
        return data[2]["url"], "SUCCESS"

    def get_SE_cloud_status(self, se_group_name):
        """
        fetch cloud SE status from AVI
        :param se_group_name: SE group name
        :return:
        """
        url = AlbEndpoint.SE_GROUP.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            for res in response.json()["results"]:
                if res["name"] == se_group_name:
                    return res["url"], "SUCCESS"
        return "NOT_FOUND", "SUCCESS"

    def get_vip_network_ip_netmask(self, name):
        """
        fetch vip network netmask from AVI cloud
        :param name: name of the network
        :return: VIP netmask if found else None
        """
        body = {}
        network_url = AlbEndpoint.NETWORK.format(ip=self.avi_host)
        try:
            response = RequestApiUtil.exec_req("GET", network_url, headers=self.headers, data=body, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            else:
                for res in response.json()["results"]:
                    if res["name"] == name:
                        for sub in res["configured_subnets"]:
                            return str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]), "SUCCESS"
                else:
                    next_url = None if not response.json()["next"] else response.json()["next"]
                    while len(next_url) > 0:
                        response_csrf = RequestApiUtil.exec_req(
                            "GET", next_url, headers=self.headers, data=body, verify=False
                        )
                        for res in response_csrf.json()["results"]:
                            if res["name"] == name:
                                for sub in res["configured_subnets"]:
                                    return (
                                        str(sub["prefix"]["ip_addr"]["addr"]) + "/" + str(sub["prefix"]["mask"]),
                                        "SUCCESS",
                                    )
                        next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
            return "NOT_FOUND", "FAILED"
        except KeyError:
            return "NOT_FOUND", "FAILED"

    def get_vip_network(self, name):
        body = {}
        network_url = AlbEndpoint.NETWORK.format(ip=self.avi_host)
        try:
            response_csrf = RequestApiUtil.exec_req("GET", network_url, headers=self.headers, data=body, verify=False)
            if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
                return None, response_csrf.text
            else:
                for re in response_csrf.json()["results"]:
                    if re["name"] == name:
                        return re["url"], "SUCCESS"
                else:
                    next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
                    while len(next_url) > 0:
                        response_csrf = RequestApiUtil.exec_req(
                            "GET", next_url, headers=self.headers, data=body, verify=False
                        )
                        for re in response_csrf.json()["results"]:
                            if re["name"] == name:
                                return re["url"], "SUCCESS"
                        next_url = None if not response_csrf.json()["next"] else response_csrf.json()["next"]
            return "NOT_FOUND", "SUCCESS"
        except KeyError:
            return "NOT_FOUND", "SUCCESS"

    def create_vip_network(self, name, cloud_url, network_gateway, network_netmask, start_ip, end_ip):
        """
        fetch vip network netmask from AVI cloud
        :param cloud_url: url of the cloud
        :param name: name of the network
        :param network_gateway: name of the network
        :param network_netmask: name of the network
        :param start_ip: name of the network
        :param end_ip: name of the network
        :return: VIP netmask if found else None
        """
        json_object = AlbPayload.CREATE_NETWORK.format(
            name=name,
            cloud_url=cloud_url,
            static_ip_start=start_ip,
            static_ip_end=end_ip,
            subnet_ip=network_gateway,
            netmask=network_netmask,
        )
        network_url = AlbEndpoint.NETWORK.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("POST", network_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            return response.json()["url"], "SUCCESS"

    def get_vrf_and_next_route_id(self, cloud_uuid, name, route_ip):
        """
        get VRF and route id from Cloud
        :param cloud_uuid: cloud uuid to fetch data from
        :param name: name of the VRF
        :param route_ip: route IP for fetching
        :return:
        """
        route_id = 0
        url = AlbEndpoint.GET_VRF.format(ip=self.avi_host, name=name, cloud_uuid=cloud_uuid)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            data_list = []
            for res in response.json()["results"]:
                if res["name"] == name:
                    try:
                        for st in res["static_routes"]:
                            data_list.append(int(st["route_id"]))
                            current_app.logger.info(st["next_hop"]["addr"])
                            current_app.logger.info(route_ip)
                            if st["next_hop"]["addr"] == route_ip:
                                return res["url"], "Already_Configured"
                        data_list.sort()
                        route_id = int(data_list[-1]) + 1
                    except KeyError:
                        pass
                    if name == VrfType.MANAGEMENT:
                        route_id = 1
                    return res["url"], route_id
                else:
                    return None, "NOT_FOUND"
            return None, "NOT_FOUND"

    def add_static_route(self, vrf_url, route_ip, route_id):
        """
        add static route to the VRF
        :param vrf_url: VRF url for routing to add
        :param route_ip:  next route ip for VRF
        :param route_id: route id for VRF context
        :return:
        """
        # TODO not sure on this logic
        if route_id == 0:
            route_id = 1
        json_object = AlbPayload.ADD_STATIC_ROUTE.format(route_ip=route_ip, route_id=route_id)
        response = RequestApiUtil.exec_req("PATCH", vrf_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            return "SUCCESS", HTTPStatus.OK

    def get_network_url(self, network_name, cloud_name):
        """
        fetch network url from cloud name with passed network name
        :param network_name:
        :param cloud_name:
        :return:
        """
        new_cloud_json = FileHelper.load_json(spec_path=AVIDataFiles.NEW_CLOUD_DETAILS)
        cloud_uuid = None
        if "uuid" in new_cloud_json:
            cloud_uuid = new_cloud_json["uuid"]
        else:
            for res in new_cloud_json["results"]:
                if res["name"] == cloud_name:
                    cloud_uuid = res["uuid"]
        if cloud_uuid is None:
            return None, "Failed", "ERROR"
        url = AlbEndpoint.GET_NETWORK_INVENTORY.format(ip=self.avi_host, cloud_uuid=cloud_uuid)
        try:
            # poll response for check SE is up or not.
            AVIHelper.poll_api_response_10_secs_counter(url, headers=self.headers, verify=False)
            response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            else:
                for se in response.json()["results"]:
                    if se["config"]["name"] == network_name:
                        return se["config"]["url"], se["config"]["uuid"], "FOUND", "SUCCESS"
                else:
                    next_url = "" if not response.json()["next"] else response.json()["next"]
                    while len(next_url) > 0:
                        response = RequestApiUtil.exec_req("GET", next_url, headers=self.headers, verify=False)
                        for se in response.json()["results"]:
                            if se["config"]["name"] == network_name:
                                return se["config"]["url"], se["config"]["uuid"], "FOUND", "SUCCESS"
                        next_url = "" if not response.json()["next"] else response.json()["next"]
            return None, "NOT_FOUND", "Failed"
        except polling2.TimeoutException:
            current_app.logger.error("Waited for 600 secs but service engine is not up")
            return None, "Failed", "ERROR"
        except KeyError:
            return None, "NOT_FOUND", "Failed"

    def get_network_details(self, network_url):
        """
        fetch network details from network url
        :param network_url: network url
        :return:
        """
        details = {}
        response = RequestApiUtil.exec_req("GET", network_url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            details["error"] = response.text
            return None, "Failed", details
        try:
            data = response.json()
            details["subnet_ip"] = data["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
            if self.env == Env.VSPHERE:
                details["vim_ref"] = data["vimgrnw_ref"]
            details["subnet_mask"] = data["configured_subnets"][0]["prefix"]["mask"]
            return "AlreadyConfigured", HTTPStatus.OK, details
        except KeyError as ke:
            current_app.logger.debug(f"error in fetching ip pools {ke}")
            current_app.logger.info("Ip pools are not configured, configuring it")
        except JSONDecodeError as de:
            current_app.logger.debug(f"error in fetching ip pools {de}")
            current_app.logger.info("Ip pools are not configured, configuring it")
        except Exception as ex:
            current_app.logger.debug(f"error in fetching ip pools {ex}")
            current_app.logger.info("Ip pools are not configured, configuring it")
        FileHelper.delete_file(file_path=AVIDataFiles.NETWORK_DETAILS)
        FileHelper.dump_json(file=AVIDataFiles.NETWORK_DETAILS, json_dict=response.json())
        """
         if isSeRequired:
        generateVsphereConfiguredSubnetsForSe(
            "managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask)
        )
        else:
        if env == Env.VSPHERE:
            generateVsphereConfiguredSubnets(
                "managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask)
            )
        else:
            generateVsphereConfiguredSubnetsForSeandVIP(
                "managementNetworkDetails.json", startIp, endIp, prefixIp, int(netmask)
            )
        can we move outside?
        """
        return "SUCCESS", HTTPStatus.OK, details

    def create_virtual_service(self, avi_cloud_uuid, se_name, vip_network_url, se_count, tier_id, vrf_url_tier1):
        body = {}
        url = AlbEndpoint.AVI_SERVICE_ENGINE.format(ip=self.avi_host, se_name=se_name, avi_cloud_uuid=avi_cloud_uuid)
        response_csrf = RequestApiUtil.exec_req("GET", url, headers=self.headers, data=body, verify=False)
        if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
            return None, response_csrf.text
        else:
            json_out = response_csrf.json()["results"][0]
            cloud_ref = json_out["cloud_ref"]
            service_engine_group_url = json_out["url"]
            se_uuid = json_out["uuid"]
            type = VrfType.GLOBAL
            cloud_ref_ = cloud_ref[cloud_ref.rindex("/") + 1 :]
            se_group_url = AlbEndpoint.AVI_SE_GROUP.format(
                ip=self.avi_host, cloud_ref=cloud_ref_, service_engine_uuid=se_uuid
            )
            response = RequestApiUtil.exec_req("GET", se_group_url, headers=self.headers, data=body, verify=False)
            if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
                return None, response.text
            create_vs = False
            try:
                service_engines = response.json()["results"][0]["serviceengines"]
                if len(service_engines) > (se_count - 1):
                    current_app.logger.info("Required service engines are already created")
                else:
                    create_vs = True
            except Exception:
                create_vs = True
            if create_vs:
                current_app.logger.info("Creating virtual service")
                vrf_get_url = AlbEndpoint.GET_VRF.format(ip=self.avi_host, name=type, cloud_uuid=avi_cloud_uuid)
                response_csrf = RequestApiUtil.exec_req(
                    "GET", vrf_get_url, headers=self.headers, data=body, verify=False
                )
                if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
                    return None, response_csrf.text
                vrf_url = ""
                for res in response_csrf.json()["results"]:
                    if res["name"] == type:
                        vrf_url = res["url"]
                        break
                if not vrf_url:
                    return None, "VRF_URL_NOT_FOUND"
                get_vip_network_details = self.get_network_details(vip_network_url)
                if get_vip_network_details[0] is None:
                    return None, "Failed to get vip network details " + str(get_vip_network_details[2])
                if get_vip_network_details[0] == "AlreadyConfigured":
                    current_app.logger.info("Vip Ip pools are already configured.")
                    ip_pre = get_vip_network_details[2]["subnet_ip"]
                    mask = get_vip_network_details[2]["subnet_mask"]
                else:
                    return None, "Vip Ip pools are not configured."
                virtual_service_vip_url = AlbEndpoint.AVI_VIRTUAL_SERVICE_VIP.format(ip=self.avi_host)
                response = RequestApiUtil.exec_req(
                    "GET", virtual_service_vip_url, headers=self.headers, data=body, verify=False
                )
                if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                    return None, response.text
                is_vip_created = False
                vip_url = ""
                try:
                    for r in response.json()["results"]:
                        if r["name"] == ServiceName.SIVT_SERVICE_VIP:
                            is_vip_created = True
                            vip_url = r["url"]
                            break
                except Exception:
                    current_app.logger.info("No virtual service vip created")
                if not is_vip_created:
                    if self.env == Env.VCF:
                        body = AlbPayload.VIRTUAL_SERVICE_NSX_VIP.format(
                            cloud_ref=cloud_ref,
                            virtual_service_name_vip=ServiceName.SIVT_SERVICE_VIP,
                            vrf_context_ref=vrf_url_tier1,
                            network_ref=vip_network_url,
                            addr=ip_pre,
                            mask=mask,
                            tier_1_gw_uuid=tier_id,
                        )
                    else:
                        body = AlbPayload.VIRTUAL_SERVICE_VIP.format(
                            cloud_ref=cloud_ref,
                            virtual_service_name_vip=ServiceName.SIVT_SERVICE_VIP,
                            vrf_context_ref=vrf_url,
                            network_ref=vip_network_url,
                            addr=ip_pre,
                            mask=mask,
                        )
                    response = RequestApiUtil.exec_req(
                        "POST", virtual_service_vip_url, headers=self.headers, data=body, verify=False
                    )
                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
                        return None, response.text
                    vip_url = response.json()["url"]
                if not vip_url:
                    return None, "virtual service vip url not found"
                virtual_service_url = AlbEndpoint.AVI_VIRTUAL_SERVICE.format(ip=self.avi_host)
                response = RequestApiUtil.exec_req(
                    "GET", virtual_service_url, headers=self.headers, data=body, verify=False
                )
                if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                    return None, response.text
                isVsCreated = False
                try:
                    for r in response.json()["results"]:
                        if r["name"] == ServiceName.SIVT_SERVICE:
                            isVsCreated = True
                            break
                except Exception:
                    current_app.logger.info("No virtual service created")
                if not isVsCreated:
                    if self.env == Env.VCF:
                        body = AlbPayload.NSX_VIRTUAL_SERVICE.format(
                            cloud_ref=cloud_ref,
                            se_group_ref=service_engine_group_url,
                            vsvip_ref=vip_url,
                            tier_1_vrf_context_url=vrf_url_tier1,
                        )
                    else:
                        body = AlbPayload.VIRTUAL_SERVICE.format(
                            cloud_ref=cloud_ref, se_group_ref=service_engine_group_url, vsvip_ref=vip_url
                        )
                    response = RequestApiUtil.exec_req(
                        "POST", virtual_service_url, headers=self.headers, data=body, verify=False
                    )
                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
                        return None, response.text
                body = {}
                counter = 0
                counter_se = 0
                initialized = False
                try:
                    if se_count == 2:
                        for i in range(1):
                            while counter_se < 90:
                                response = RequestApiUtil.exec_req(
                                    "GET", se_group_url, headers=self.headers, data=body, verify=False
                                )
                                if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                                    return None, response.text
                                config = response.json()["results"][0]
                                try:
                                    seurl = config["serviceengines"][i]
                                    initialized = True
                                    break
                                except Exception:
                                    current_app.logger.info(
                                        "Waited " + str(counter_se * 10) + "s for service engines to be " "initialized"
                                    )
                                counter_se = counter_se + 1
                                time.sleep(30)
                            if not initialized:
                                return None, "Service engines not initialized  in 45m"
                            current_app.logger.info("Checking status of service engine " + str(seurl))
                            response = RequestApiUtil.exec_req(
                                "GET", seurl, headers=self.headers, data=body, verify=False
                            )
                            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                                return None, response.text
                            isConnected = False
                            try:
                                status = response.json()["se_connected"]
                                while not status and counter < 60:
                                    response = RequestApiUtil.exec_req(
                                        "GET", seurl, headers=self.headers, data=body, verify=False
                                    )
                                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                                        return None, response.text
                                    status = response.json()["se_connected"]
                                    if status:
                                        isConnected = True
                                        break
                                    counter = counter + 1
                                    time.sleep(30)
                                    current_app.logger.info(
                                        "Waited " + str(counter * 30) + "s,to check se  connected status retrying"
                                    )
                                if not isConnected:
                                    return (
                                        None,
                                        "Waited "
                                        + str(counter * 30)
                                        + "s,to check se  connected and is not in connected state",
                                    )
                                else:
                                    current_app.logger.info(str(seurl) + " is  now in connected state")
                                counter = 0
                            except Exception as e:
                                return None, str(e)

                    if se_count == 4:
                        for i in range(2, 3):
                            seurl = config["serviceengines"][i]
                            current_app.logger.info("Checking status of service engine " + str(seurl))
                            response = RequestApiUtil.exec_req(
                                "GET", seurl, headers=self.headers, data=body, verify=False
                            )
                            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                                return None, response.text
                            current_app.logger.info(response.json())
                            isConnected = False
                            try:
                                status = response.json()["se_connected"]
                                while not status and counter < 60:
                                    response = RequestApiUtil.exec_req(
                                        "GET", seurl, headers=self.headers, data=body, verify=False
                                    )
                                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                                        return None, response.text
                                    if status:
                                        isConnected = True
                                        break
                                    counter = counter + 1
                                    time.sleep(10)
                                    current_app.logger.info(
                                        "Waited " + str(counter * 10) + "s,to check se  connected status retrying"
                                    )
                                if not isConnected:
                                    return (
                                        None,
                                        "Waited "
                                        + str(counter * 10)
                                        + "s,to check se  connected and is not in connected state",
                                    )
                            except Exception as e:
                                return None, str(e)
                except Exception as e:
                    return None, str(e)
                try:
                    current_app.logger.info("Deleting Virtual service")
                    response = RequestApiUtil.exec_req(
                        "GET", virtual_service_vip_url, headers=self.headers, data=body, verify=False
                    )
                    if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                        return None, response.text
                    vip_url = ""
                    try:
                        for r in response.json()["results"]:
                            if r["name"] == ServiceName.SIVT_SERVICE_VIP:
                                vip_url = r["url"]
                                break
                    except Exception:
                        current_app.logger.info("No virtual service vip created")
                    vs_url = ""
                    virtual_service_url = AlbEndpoint.AVI_VIRTUAL_SERVICE.format(ip=self.avi_host)
                    response = RequestApiUtil.exec_req(
                        "GET", virtual_service_url, headers=self.headers, data=body, verify=False
                    )
                    try:
                        for r in response.json()["results"]:
                            if r["name"] == ServiceName.SIVT_SERVICE:
                                vs_url = r["url"]
                                break
                    except Exception:
                        current_app.logger.info("No virtual service created")
                    RequestApiUtil.exec_req("DELETE", vs_url, headers=self.headers, data=body, verify=False)
                    RequestApiUtil.exec_req("DELETE", vip_url, headers=self.headers, data=body, verify=False)
                except Exception:
                    pass
                return "SUCCESS", "Required Service engines successfully created"
            else:
                return "SUCCESS", "Required Service engines are already present"

    def create_nsxt_cloud(
        self, nsx_address, nsx_username, nsx_password, nsx_overlay, teir1_route, avi_mgmt, cluster_vip_nw
    ):
        try:
            cloud_connect_user, cred = self.create_cloud_connect_user(nsx_username, nsx_password)
            if cloud_connect_user is None:
                return None, cred
            nsxt_cred = cred["nsxUUid"]
            zone, status_zone = self._fetch_transport_zone_id(nsx_overlay, nsx_address, nsxt_cred)
            if zone is None:
                return None, status_zone
            tier1_id, status_tier1 = self.fetch_tier1_gateway_id(nsxt_cred, teir1_route, nsx_address)
            if tier1_id is None:
                return None, status_tier1

            # tz_id, status_tz = fetchTransportZoneId(ip, headers, nsxt_cred)
            # if tz_id is None:
            #     return None, status_tz

            seg_id, status_seg = self.fetch_segments_id(
                nsxt_cred, status_zone, status_tier1, nsx_address, avi_mgmt, cluster_vip_nw
            )
            if seg_id is None:
                return None, status_seg
            status, value = self.create_cloud_connect_user(nsx_username, nsx_password)

            if isinstance(value, tuple):
                nsx_url = value[2]
            else:
                nsx_url = value["nsx_user_url"]
            body = {
                "dhcp_enabled": True,
                "dns_resolution_on_se": False,
                "enable_vip_on_all_interfaces": False,
                "enable_vip_static_routes": False,
                "ip6_autocfg_enabled": False,
                "maintenance_mode": False,
                "mtu": 1500,
                "nsxt_configuration": {
                    "site_id": "default",
                    "domain_id": "default",
                    "enforcementpoint_id": "default",
                    "automate_dfw_rules": False,
                    "data_network_config": {
                        "transport_zone": status_zone,
                        "tz_type": "OVERLAY",
                        "tier1_segment_config": {
                            "segment_config_mode": "TIER1_SEGMENT_MANUAL",
                            "manual": {
                                "tier1_lrs": [{"segment_id": status_seg["cluster_vip"], "tier1_lr_id": status_tier1}]
                            },
                        },
                    },
                    "management_network_config": {
                        "transport_zone": status_zone,
                        "tz_type": "OVERLAY",
                        "overlay_segment": {"segment_id": status_seg["avi_mgmt"], "tier1_lr_id": status_tier1},
                    },
                    "nsxt_credentials_ref": nsx_url,
                    "nsxt_url": nsx_address,
                },
                "obj_name_prefix": Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt"),
                "name": Cloud.CLOUD_NAME_VSPHERE.replace("vsphere", "nsxt"),
                "prefer_static_routes": False,
                "state_based_dns_registration": True,
                "vmc_deployment": False,
                "vtype": "CLOUD_NSXT",
            }
            json_object = json.dumps(body, indent=4)
            url = AlbEndpoint.CLOUD.format(ip=self.avi_host)
            response_csrf = RequestApiUtil.exec_req("POST", url, headers=self.headers, data=json_object, verify=False)
            if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.CREATED):
                return None, response_csrf.text
            else:
                FileHelper.delete_file(AVIDataFiles.NEW_CLOUD_INFO)
                FileHelper.dump_json(file=AVIDataFiles.NEW_CLOUD_DETAILS, json_dict=response_csrf.json())
                return response_csrf.json()["url"], "SUCCESS"
        except Exception as e:
            return None, str(e)

    def _details_of_cloud(self, new_cloud_url):
        """
        helper method for fetching cloud details using cloud url
        :param new_cloud_url: url of the cloud
        """
        response = RequestApiUtil.exec_req("GET", new_cloud_url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            json_resp = response.json()
            FileHelper.delete_file(file_path=AVIDataFiles.NEW_CLOUD_DETAILS)
            FileHelper.dump_json(file=AVIDataFiles.NEW_CLOUD_DETAILS, json_dict=json_resp)
            return True, json_resp

    def get_details_of_new_cloud(self, new_cloud_url, vim_ref, subnet_ip, subnet_mask):
        """
        get details of new cloud from the AVI
        :param new_cloud_url: new cloud URL
        :param vim_ref:
        :param subnet_ip:
        :param subnet_mask:
        :return:
        """
        response = self._details_of_cloud(new_cloud_url=new_cloud_url)
        if not response[0]:
            return response
        else:
            replaceValueSysConfig(
                AVIDataFiles.NEW_CLOUD_DETAILS, "vcenter_configuration", "management_network", vim_ref
            )
            ip_val = dict(ip_addr=dict(addr=subnet_ip, type="V4"), mask=subnet_mask)
            replaceValueSysConfig(
                AVIDataFiles.NEW_CLOUD_DETAILS, "vcenter_configuration", "management_ip_subnet", ip_val
            )
            return response[1], "SUCCESS"

    def get_details_of_new_cloud_arch(self, new_cloud_url, new_ipam_url, se_group_url):
        """
        :param new_cloud_url:
        :param new_ipam_url:
        :param se_group_url:
        :return:
        """
        response = self._details_of_cloud(new_cloud_url=new_cloud_url)
        if not response[0]:
            return response
        else:
            replaceValueSysConfig(AVIDataFiles.NEW_CLOUD_DETAILS, "ipam_provider_ref", "name", new_ipam_url)
            replaceValueSysConfig(AVIDataFiles.NEW_CLOUD_DETAILS, "se_group_template_ref", "name", se_group_url)
            return response[1], "SUCCESS"

    def update_network_with_ip_pools(self, network_url):
        """
        update network with IP pools using provided network url
        :param network_url: URL of the network
        :return:
        """
        json_object = FileHelper.load_json(AVIDataFiles.NETWORK_DETAILS)
        if self.env == Env.VCF:
            dhcp_dic = dict(dhcp_enabled=False)
            json_object.update(dhcp_dic)
        json_object_m = json.dumps(json_object, indent=4)
        details = {}
        response = RequestApiUtil.exec_req("PUT", network_url, headers=self.headers, data=json_object_m, verify=False)
        # it can be pooling as update always gives 200
        # TODO can be pooling but P
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            count = 0
            if "Cannot edit network properties till network sync from Service Engines is complete" in response.text:
                while count < 10:
                    time.sleep(60)
                    response = RequestApiUtil.exec_req(
                        "PUT", network_url, headers=self.headers, data=json_object_m, verify=False
                    )
                    if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                        break
                    current_app.logger.info("waited for " + str(count * 60) + "s sync to complete")
                    count = count + 1

            else:
                return HTTPStatus.INTERNAL_SERVER_ERROR, response.text, details
        json_obj = response.json()
        details["subnet_ip"] = json_obj["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
        details["subnet_mask"] = json_obj["configured_subnets"][0]["prefix"]["mask"]
        if self.env == Env.VSPHERE:
            details["vimref"] = json_obj["vimgrnw_ref"]
        # details["vimref"] = json_obj["vimgrnw_ref"]
        return HTTPStatus.OK, "SUCCESS", details

    def get_network_details_vip(self, vip_network_url, start_ip, end_ip, prefix_ip, netmask):
        payload = {}
        details = {}
        response_csrf = RequestApiUtil.exec_req(
            "GET", vip_network_url, headers=self.headers, data=payload, verify=False
        )
        if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
            details["error"] = response_csrf.text
            return None, "Failed", details
        try:
            add = response_csrf.json()["configured_subnets"][0]["prefix"]["ip_addr"]["addr"]
            details["subnet_ip"] = add
            details["subnet_mask"] = response_csrf.json()["configured_subnets"][0]["prefix"]["mask"]
            details["vim_ref"] = response_csrf.json()["vimgrnw_ref"]
            return "AlreadyConfigured", 200, details
        except Exception:
            current_app.logger.info("Ip pools are not configured, configuring it")

        FileHelper.delete_file(AVIDataFiles.NETWORK_DETAILS)
        FileHelper.dump_json(file=AVIDataFiles.NETWORK_DETAILS, json_dict=response_csrf.json())
        if self.env == Env.VSPHERE:
            AVIHelper.generate_vsphere_configured_subnets(start_ip, end_ip, prefix_ip, netmask)
        else:
            AVIHelper.generate_vsphere_configure_subnets_for_se_and_vip(start_ip, end_ip, prefix_ip, netmask)
        return "SUCCESS", 200, details

    def get_details_of_new_cloud_add_ipam(self, new_cloud_url, ipam_url):
        """
        update cloud data with ipam details
        :param new_cloud_url:
        :param ipam_url:
        :return:
        """
        response = RequestApiUtil.exec_req("GET", new_cloud_url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            json_object = response.json()
            json_object["ipam_provider_ref"] = ipam_url
            FileHelper.delete_file(file_path=AVIDataFiles.NEW_CLOUD_IPAM_DETAILS)
            FileHelper.dump_json(json_dict=json_object, file=AVIDataFiles.NEW_CLOUD_IPAM_DETAILS)
            return json_object, "SUCCESS"

    def update_new_cloud(self, new_cloud_url):
        """
        update cloud data
        :param new_cloud_url: cloud url
        :return:
        """
        new_cloud_json = FileHelper.load_json(AVIDataFiles.NEW_CLOUD_INFO)
        json_object = json.dumps(new_cloud_json, indent=4)
        response = RequestApiUtil.exec_req("PUT", new_cloud_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            return response.json(), "SUCCESS"

    def generate_se_ova(self, cloud_name):
        current_app.logger.info("Generating service engine ova")
        new_cloud_json = FileHelper.load_json(AVIDataFiles.NEW_CLOUD_INFO)
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except Exception:
            for re in new_cloud_json["results"]:
                if re["name"] == cloud_name:
                    uuid = re["uuid"]
        if uuid is None:
            return None, "NOT_FOUND"
        body = {"file_format": "ova", "cloud_uuid": uuid}
        modified = json.dumps(body, indent=4)
        url = AlbEndpoint.GENERATE_SE_OVA.format(ip=self.avi_host)
        start = time.time()
        response_csrf = RequestApiUtil.exec_req(
            "POST", url, headers=self.headers, data=modified, verify=False, timeout=1800
        )
        if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.CREATED):
            return None, response_csrf.text
        else:
            end = time.time()
            difference = int(end - start)
            if difference < 5:
                current_app.logger.info("Service engine ova is already generated")
            return "SUCCESS", 200

    def download_se_ova(self, avi_uuid, cloud_name):
        with open(AVIDataFiles.NEW_CLOUD_INFO, "r") as file2:
            new_cloud_json = json.load(file2)
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except Exception:
            for re in new_cloud_json["results"]:
                if re["name"] == cloud_name:
                    uuid = re["uuid"]
        if uuid is None:
            return None, "NOT_FOUND"
        current_app.config["se_ova_path"] = AVIDataFiles.AVI_SE_OVA.format(avi_uuid=avi_uuid)
        my_file = Path(AVIDataFiles.AVI_SE_OVA.format(avi_uuid=avi_uuid))
        se_ova_path = AVIDataFiles.AVI_SE_OVA.format(avi_uuid=avi_uuid)
        if my_file.exists():
            current_app.logger.info("Service engine ova is already downloaded")
            return "SUCCESS", 200, se_ova_path
        url = AlbEndpoint.DOWNLOAD_SE_OVA.format(ip=self.avi_host, uuid=uuid)
        payload = {}
        response_csrf = RequestApiUtil.exec_req(
            "GET", url, headers=self.headers, data=payload, verify=False, timeout=1800
        )
        if not RequestApiUtil.verify_resp(response_csrf, status_code=HTTPStatus.OK):
            return None, response_csrf.text
        else:
            for txt_file in pathlib.Path("/tmp").glob("*.ova"):
                FileHelper.delete_file(str(txt_file.absolute()))
            with open(r"/tmp/" + avi_uuid + ".ova", "wb") as f:
                f.write(response_csrf.content)
            current_app.logger.info("Service engine ova downloaded")
            return "SUCCESS", 200, se_ova_path

    def get_cluster_url(self, cluster_name):
        """
        get cluster data using cluster name
        :param cluster_name:
        :return:
        """
        url = AlbEndpoint.GET_CLUSTER_RUNTIME.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            if str(cluster_name).__contains__("/"):
                cluster_name = cluster_name[cluster_name.rindex("/") + 1 :]
            for cluster in response.json()["results"]:
                if cluster["name"] == cluster_name:
                    return cluster["url"], "SUCCESS"
            return "NOT_FOUND", "FAILED"

    def update_vip_network_ip_pools(self, network_url, start_ip, end_ip, prefix_ip, prefix_mask):
        """
        update vip network with IP pools
        :param network_url: network url to update
        :param start_ip:
        :param end_ip:
        :param prefix_ip:
        :param prefix_mask:
        :return:
        """
        response = self.get_network_details(network_url=network_url)
        if response[0] is None:
            return "Failed to get VIP network details", HTTPStatus.INTERNAL_SERVER_ERROR
        if response[0] == "AlreadyConfigured":
            current_app.logger.info("Vip Ip pools are already configured.")
            ip_pre = response[2]["subnet_ip"] + "/" + str(response[2]["subnet_mask"])
        else:
            AVIHelper.generate_vsphere_configured_subnets(
                begin_ip=start_ip, end_ip=end_ip, prefix_ip=prefix_ip, prefix_mask=prefix_mask
            )
            update_resp = self.update_network_with_ip_pools(network_url=network_url)
            if update_resp[0] != HTTPStatus.OK:
                return f"Failed to update VIP network ip pools {str(update_resp[1])}", HTTPStatus.INTERNAL_SERVER_ERROR
            ip_pre = update_resp[2]["subnet_ip"] + "/" + str(update_resp[2]["subnet_mask"])
        FileHelper.write_to_file(content=ip_pre, file=AVIDataFiles.VIP_IP_TXT)
        return "SUCCESS", HTTPStatus.OK

    def change_se_group_and_set_interfaces(self, url_from_service_engine):
        """
        update SE engine details
        :param url_from_service_engine: SE engine URL
        """
        json_object = FileHelper.load_json(spec_path=AVIDataFiles.SERVICE_ENGINE_DETAILS_1)
        json_object_m = json.dumps(json_object, indent=4)
        response = RequestApiUtil.exec_req(
            "PUT", url_from_service_engine, headers=self.headers, data=json_object_m, verify=False, timeout=600
        )
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            return response.json(), HTTPStatus.OK

    def fetch_service_engine_url(self, count_se, controller_name, cloud_name):
        """
        fetch SE engine URL
        Cloud.CLOUD_NAME.replace("vmc", "vsphere"):
        :param count_se:
        :param controller_name: name of the controller
        :param cloud_name: name of the cloud
        """
        uuid_response = self._get_cloud_uuid(cloud_name=cloud_name)
        if not uuid_response[0]:
            return uuid_response
        uuid = uuid_response[0]
        AVIInfraOps.COUNT = 0
        url = AlbEndpoint.SERVICE_ENGINE_INVENTORY.format(ip=self.avi_host, uuid=uuid)
        current_app.logger.info("Checking if all services are up.")
        count = 0
        response = None
        # TODO pooling but need multiple request calls
        while count < 60:
            try:
                current_app.logger.info("Waited for " + str(count * 10) + "s retrying")
                response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
                if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                    response_json = response.json()
                    if response_json["count"] > count_se:
                        for se in response_json["results"]:
                            if str(se["config"]["name"]).strip() == str(controller_name).strip():
                                current_app.logger.info("Successfully deployed se engine")
                                return se["config"]["url"], "FOUND", "SUCCESS"
                count = count + 1
                time.sleep(10)
            except KeyError:
                pass
        if response is None:
            current_app.logger.info("Waited for " + str(count * 10) + "s but service engine is not up")
            return None, "Failed", "ERROR"
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        elif count >= 59:
            return None, "NOT_FOUND", "TIME_OUT"
        return None, "NOT_FOUND", "Failed"

    @staticmethod
    def _verify_se_api_response(response):
        """
        helper method to verify SE response
        """
        try:
            se_count = 0
            AVIInfraOps.COUNT += 1
            current_app.logger.info("Waited for " + str(AVIInfraOps.COUNT * 10) + "s retrying")
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                response_json = response.json()
                length = len(response_json["results"])
                for se in response_json["results"]:
                    if str(se["runtime"]["se_connected"]).strip().lower() == "true":
                        se_count = se_count + 1
                        return se_count == length
                return se_count == length
        except KeyError:
            pass

    @staticmethod
    def _verify_cloud_placement(response):
        """
        helper method to verify SE response
        """
        try:
            AVIInfraOps.COUNT += 1
            current_app.logger.info("Waited for " + str(AVIInfraOps.COUNT * 10) + "s retrying")
            if RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                if response.json()["state"] == "CLOUD_STATE_PLACEMENT_READY":
                    return True
        except KeyError:
            pass

    @staticmethod
    def _get_cloud_uuid(cloud_name):
        """
        fetch cloud uuid from the response
        """
        new_cloud_json = FileHelper.load_json(spec_path=AVIDataFiles.NEW_CLOUD_INFO)
        uuid = None
        try:
            uuid = new_cloud_json["uuid"]
        except KeyError:
            for res in new_cloud_json["results"]:
                if res["name"] == cloud_name:
                    uuid = res["uuid"]
                    break
        if uuid is None:
            return None, "Failed", "ERROR"
        return uuid, "SUCCESS"

    def check_se_engine_status(self, cloud_name):
        """
        fetch SE engine status from with passed cloud name
        :param cloud_name: name of the cloud from which SE engine needs to fetched
        """
        uuid_response = self._get_cloud_uuid(cloud_name=cloud_name)
        if not uuid_response[0]:
            return uuid_response
        uuid = uuid_response[0]
        AVIInfraOps.COUNT = 0
        url = AlbEndpoint.SERVICE_ENGINE_INVENTORY.format(ip=self.avi_host, uuid=uuid)
        current_app.logger.info("Checking if all services are up.")
        try:
            polling2.poll(
                lambda: RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False),
                check_success=self._verify_se_api_response,
                step=10,
                timeout=600,
            )
        except polling2.TimeoutException:
            current_app.logger.error("Waited for 600 secs but service engine is not up")
            return None, "Failed", "ERROR"
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            current_app.logger.info("All services are up and running")
            return "SUCCESS", "CHECKED", "UP"

    def enable_dhcp(self, network_name, cloud_name):
        """
        enable dhcp on the network
        :param network_name: network name on which DHCP needs to be enabled.
        :param cloud_name: cloud name needed to fetch network from AVI controller
        """
        network_response = self.get_network_url(network_name=network_name, cloud_name=cloud_name)
        if network_response[0] is None:
            message = f"Failed to get network url {network_name}"
            current_app.logger.error(message)
            return None, HTTPStatus.INTERNAL_SERVER_ERROR
        url = network_response[0]
        network_details_response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(network_details_response, status_code=HTTPStatus.OK):
            message = f"Failed to get network details {network_details_response.text}"
            current_app.logger.error(message)
            return None, HTTPStatus.INTERNAL_SERVER_ERROR
        # fetch and update dhcp
        data = network_details_response.json()
        data["dhcp_enabled"] = True
        # push changes
        network_details_response = RequestApiUtil.exec_req(
            "PUT", url, headers=self.headers, data=json.dumps(data), verify=False
        )
        if not RequestApiUtil.verify_resp(network_details_response, status_code=HTTPStatus.OK):
            message = f"Failed to update network details {network_details_response.text}"
            current_app.logger.error(message)
            return None, HTTPStatus.INTERNAL_SERVER_ERROR

        return "SUCCESS", HTTPStatus.OK

    def wait_for_cloud_placement(self, cloud_name):
        """
        waiting for the cloud status to be available
        :param cloud_name: name of the cloud
        """
        data = self._get_cloud_data(cloud_name=cloud_name)
        if data[0] is None or data[0] == "NOT_FOUND":
            return None, data[1]
        cloud_uuid = data[2]["uuid"]
        status_url = AlbEndpoint.CLOUD_STATUS.format(ip=self.avi_host, uuid=cloud_uuid)
        AVIInfraOps.COUNT = 0
        try:
            polling2.poll(
                lambda: RequestApiUtil.exec_req("GET", status_url, headers=self.headers, verify=False),
                check_success=self._verify_cloud_placement,
                step=10,
                timeout=900,
            )
        except polling2.TimeoutException:
            current_app.logger.error("Waited for 600 secs but service engine is not up")
            return None, "Failed", "ERROR"
        response = RequestApiUtil.exec_req("GET", status_url, headers=self.headers, verify=False)
        return "SUCCESS", "READY", response.json()["state"]

    def create_se_cloud(
        self, cloud_url, se_group_name, cluster_url, data_store, se_name_prefix, license_type="enterprise"
    ):
        """
        create SE engine inside a cloud
        :param cloud_url: cloud url for the SE engine
        :param se_group_name: name of the SE group
        :param cluster_url: cluster url
        :param data_store: data store for vcenter where SE VM launched
        :param se_name_prefix: prefix for SE name
        :param license_type: type of license
        """
        se_url = AlbEndpoint.SE_GROUP.format(ip=self.avi_host)
        body = AlbPayload.SE_CLOUD_BODY.format(
            cloud_url=cloud_url,
            se_group_name=se_group_name,
            cluster_url=cluster_url,
            se_name_prefix=se_name_prefix,
            data_store=data_store,
        )
        body_update = AlbPayload.ESSENTIAL_SE_BODY if license_type == "essentials" else AlbPayload.ENTERPRISE_SE_BODY
        body = json.loads(body)
        body_update = json.loads(body_update)
        # body with license data
        body.update(body_update)
        json_object = json.dumps(body)
        response = RequestApiUtil.exec_req("POST", se_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            return response.json()["url"], "SUCCESS"

    def create_nsxt_se_cloud(
        self, cloud_url, se_group_name, nsx_cloud_info, se_name_prefix, datastore, license_type="enterprise"
    ):
        """
        create SE engine inside a NSX cloud
        :param cloud_url: cloud url for the SE engine
        :param se_group_name: name of the SE group
        :param nsx_cloud_info: cluster url
        :param se_name_prefix: prefix for SE name
        :param license_type: type of license
        """
        body = AlbPayload.NSXT_SE_CLOUD_BODY.format(
            cloud_url=cloud_url,
            se_group_name=se_group_name,
            se_name_prefix=se_name_prefix,
            vcenter_url=nsx_cloud_info["vcenter_url"],
            cluster_id=nsx_cloud_info["cluster"],
            data_store=datastore,
        )

        se_url = AlbEndpoint.SE_GROUP.format(ip=self.avi_host)
        body_update = AlbPayload.ESSENTIAL_SE_BODY if license_type == "essentials" else AlbPayload.ENTERPRISE_SE_BODY
        body = json.loads(body)
        body_update = json.loads(body_update)
        # body with license data
        body.update(body_update)
        json_object = json.dumps(body)
        response = RequestApiUtil.exec_req("POST", se_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            return response.json()["url"], "SUCCESS"

    def create_SE_cloud_arch(self, cloud_url, se_group_name, se_name_prefix, license_type, datastore):
        """
        create SE engine for non-orchestrated cloud
        :param cloud_url: cloud url for the SE engine
        :param se_group_name: name of the SE group
        :param se_name_prefix: prefix for SE name
        """
        if str(datastore).__contains__("/"):
            datastore = datastore[datastore.rindex("/") + 1 :]
        body = AlbPayload.CREATE_SE_GROUP.format(
            cloud_url=cloud_url, se_group_name=se_group_name, se_name_prefix=se_name_prefix, datastore=datastore
        )
        body_update = AlbPayload.ESSENTIAL_SE_BODY if license_type == "essentials" else AlbPayload.ENTERPRISE_SE_BODY
        body = json.loads(body)
        body_update = json.loads(body_update)
        # body with license data
        body.update(body_update)
        json_object = json.dumps(body)
        se_url = AlbEndpoint.SE_GROUP.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("POST", se_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            return response.json()["url"], "SUCCESS"

    def _get_cloud_connect_user(self):
        """
        cloud connection credentials fetching for NSX Cloud
        """
        connect_url = AlbEndpoint.CLOUD_CONNECT.format(ip=self.avi_host)
        payload = {}
        try:
            response = RequestApiUtil.exec_req("GET", connect_url, headers=self.headers, data=payload, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return "API_FAILURE", response.text
            vcenter_cred = False
            nsx_cred = False
            uuid = {}
            list_ = response.json()["results"]
            if len(list_) == 0:
                return "EMPTY", "EMPTY"
            for result in list_:
                if result["name"] == NSXtCloud.VCENTER_CREDENTIALS:
                    uuid["vcenterUUId"] = result["uuid"]
                    uuid["vcenter_user_url"] = result["url"]
                    vcenter_cred = True
                if result["name"] == NSXtCloud.NSXT_CREDENTIALS:
                    uuid["nsxUUid"] = result["uuid"]
                    uuid["nsx_user_url"] = result["url"]
                    nsx_cred = True
            if vcenter_cred and nsx_cred:
                return "BOTH_CRED_CREATED", uuid
            found = False
            if vcenter_cred:
                found = True
                tuple_ = "VCENTER_CRED_FOUND", uuid["vcenterUUId"], uuid["vcenter_user_url"]
            if nsx_cred:
                found = True
                tuple_ = "NSX_CRED_FOUND", uuid["nsxUUid"], uuid["nsx_user_url"]
            if found:
                return "ONE_CRED_FOUND", tuple_
            return "NO_CRED_FOUND", "NO_CRED_FOUND"
        except (KeyError, TypeError) as e:
            return "EXCEPTION", "Failed " + str(e)
        except Exception as e:
            current_app.logger.info(f"exception in cloud connection {str(e)}")
            return "EXCEPTION", "Failed " + str(e)

    def create_cloud_connect_user(self, nsx_username, nsx_password):
        """
        create connection with NSX to vcenter
        :param nsx_username:
        :param nsx_password: NSXT credentials
        """
        connect_url = AlbEndpoint.CLOUD_CONNECT.format(ip=self.avi_host)
        try:
            body_nsx = {
                "name": NSXtCloud.NSXT_CREDENTIALS,
                "nsxt_credentials": {"username": nsx_username, "password": nsx_password},
            }
            body_vcenter = {
                "name": NSXtCloud.VCENTER_CREDENTIALS,
                "vcenter_credentials": {"username": self.vcenter_user_name, "password": self.vcenter_password},
            }
            status_ = {}
            list_body = []
            body_vcenter = json.dumps(body_vcenter, indent=4)
            body_nsx = json.dumps(body_nsx, indent=4)
            cloud_user, status = self._get_cloud_connect_user()
            if str(cloud_user) == "EXCEPTION" or str(cloud_user) == "API_FAILURE":
                return None, status
            if str(status) == "NO_CRED_FOUND" or str(status) == "EMPTY":
                current_app.logger.info("Creating Nsx and vcenter credential")
                list_body.append(body_vcenter)
                list_body.append(body_nsx)
            if str(cloud_user) == "ONE_CRED_FOUND":
                if str(status[0]) == "VCENTER_CRED_FOUND":
                    current_app.logger.info("Creating Nsx credentials")
                    status_["vcenterUUId"] = status[1]["uuid"]
                    list_body.append(body_nsx)
                elif str(status[0]) == "NSX_CRED_FOUND":
                    current_app.logger.info("Creating Vcenter credentials")
                    status_["nsxUUid"] = status[1]["uuid"]
                    list_body.append(body_vcenter)
            if str(cloud_user) != "BOTH_CRED_CREATED":
                for body in list_body:
                    response_csrf = RequestApiUtil.exec_req(
                        "POST", connect_url, headers=self.headers, data=body, verify=False
                    )
                    if response_csrf.status_code != 201:
                        return None, response_csrf.text
                    try:
                        status_["nsxUUid"] = response_csrf.json()["uuid"]
                    except KeyError:
                        pass
                    try:
                        status_["vcenterUUId"] = response_csrf.json()["uuid"]
                    except KeyError:
                        pass
                    time.sleep(10)
                if len(status_) < 2:
                    return None, "INSUFFICIENT_ITEMS " + str(status_)
                return "SUCCESS", status_
            else:
                return "SUCCESS", status
        except (KeyError, TypeError) as e:
            return None, str(e)
        except Exception as e:
            current_app.logger.info(f"exception in create cloud connection {str(e)}")
            return None, str(e)

    def fetch_tier1_gateway_id(self, nsxt_credential, nsxt_tier1_route_name, nsxt_address):
        """
        fetch NSX tier1 gateway ID
        :param nsxt_credential: NSXT credentials
        :param nsxt_tier1_route_name: NSXT route name
        :param nsxt_address: NSX-T address
        """
        try:
            tier_url = AlbEndpoint.NSXT_TIER.format(ip=self.avi_host)
            body = {"host": nsxt_address, "credentials_uuid": nsxt_credential}
            json_object = json.dumps(body, indent=4)
            response = RequestApiUtil.exec_req("POST", tier_url, headers=self.headers, data=json_object, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            for library in response.json()["resource"]["nsxt_tier1routers"]:
                if library["name"] == nsxt_tier1_route_name:
                    return "Success", library["id"]
            return None, "TIER1_GATEWAY_ID_NOT_FOUND"
        except (KeyError, TypeError) as e:
            return None, str(e)
        except Exception as e:
            current_app.logger.info(f"exception in fetch tier1 gateway {str(e)}")
            return None, str(e)

    def _fetch_transport_zone_id(self, nsxt_overlays, nsxt_address, nsxt_credential):
        """
        fetch NSX transport zone id
        :param nsxt_credential: NSXT credentials
        :param nsxt_overlays: NSXT overlay name
        :param nsxt_address: NSX-T address
        """
        try:
            tz_zone_url = AlbEndpoint.NSXT_TRANSPORT_ZONES.format(ip=self.avi_host)
            body = {"host": nsxt_address, "credentials_uuid": nsxt_credential}
            json_object = json.dumps(body, indent=4)
            response = RequestApiUtil.exec_req(
                "POST", tz_zone_url, headers=self.headers, data=json_object, verify=False
            )
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            for library in response.json()["resource"]["nsxt_transportzones"]:
                if library["name"] == nsxt_overlays and library["tz_type"] == "OVERLAY":
                    return "Success", library["id"]
            return None, "TRANSPORT_ZONE_ID_NOT_FOUND"
        except (KeyError, TypeError) as e:
            return None, str(e)
        except Exception as e:
            current_app.logger.info(f"exception in fetch transport zone {str(e)}")
            return None, str(e)

    def _fetch_vcenter_id(self, nsxt_credential, tz_id, nsx_address):
        """
        fetch vcenter ID from AVI endpoint
        vcenter_password, nsx_password
        :param nsxt_credential: NSXT credentials
        :param nsx_password: NSX-T password
        """
        try:
            nsx_vcenter_url = AlbEndpoint.NSXT_VCENTER.format(ip=self.avi_host)
            body = {"host": nsx_address, "credentials_uuid": nsxt_credential, "transport_zone_id": tz_id}
            json_object = json.dumps(body, indent=4)
            import socket

            try:
                vc_ip = socket.gethostbyname(self.vcenter_host)
            except Exception as e:
                return None, str(e)
            response = RequestApiUtil.exec_req(
                "POST", nsx_vcenter_url, headers=self.headers, data=json_object, verify=False
            )
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            for library in response.json()["resource"]["vcenter_ips"]:
                if library["vcenter_ip"]["addr"] == vc_ip:
                    return "Success", library["vcenter_ip"]["addr"]
            return None, "VC_NOT_FOUND"
        except (KeyError, TypeError) as e:
            return None, str(e)
        except Exception as e:
            current_app.logger.info(f"exception in fetch vcenter id {str(e)}")
            return None, str(e)

    def fetch_segments_id(self, nsxt_credential, tz_id, tier1_id, nsx_address, avi_mgmt, tkg_cluster_vip_name):
        """
        fetch segments id
        """
        try:
            nsx_segment_url = AlbEndpoint.NSXT_SEGMENTS.format(ip=self.avi_host)
            # TODO
            body = {
                "host": nsx_address,
                "credentials_uuid": nsxt_credential,
                "transport_zone_id": tz_id,
                "tier1_id": tier1_id,
            }
            json_object = json.dumps(body, indent=4)
            response = RequestApiUtil.exec_req(
                "POST", nsx_segment_url, headers=self.headers, data=json_object, verify=False
            )
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            seg_id = {}
            for library in response.json()["resource"]["nsxt_segments"]:
                if library["name"] == avi_mgmt:
                    seg_id["avi_mgmt"] = library["id"]
                elif library["name"] == tkg_cluster_vip_name:
                    seg_id["cluster_vip"] = library["id"]
                if len(seg_id) == 2:
                    break
            if len(seg_id) < 2:
                return None, "SEGMENT_NOT_FOUND " + str(seg_id)
            return "Success", seg_id
        except (KeyError, TypeError) as e:
            return None, str(e)
        except Exception as e:
            current_app.logger.info(f"exception in fetch segments id {str(e)}")
            return None, str(e)

    def create_new_cloud_arch(self, cloud_name):
        """
        create new non-orchestrated cloud
        :param cloud_name: cloud name to get created
        """
        cloud_url = AlbEndpoint.CLOUD.format(ip=self.avi_host)
        body = AlbPayload.CREATE_ORCH_CLOUD.format(name=cloud_name)
        response = RequestApiUtil.exec_req("POST", cloud_url, headers=self.headers, data=body, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            FileHelper.delete_file(file_path=AVIDataFiles.NEW_CLOUD_INFO)
            json_out = response.json()
            FileHelper.dump_json(json_dict=json_out, file=AVIDataFiles.NEW_CLOUD_INFO)
            return json_out["url"], "SUCCESS"

    def _fetch_vc_info(self, cloud_uuid, vc_name):
        """
        fetch vc info from provided cloud data
        :param cloud_uuid: uuid of the cloud
        :param vc_name: name of the vc to fetch cloud data from
        """
        vcenter_url = AlbEndpoint.CLOUD_VCENTER_SERVER.format(ip=self.avi_host, uuid=cloud_uuid)
        response = RequestApiUtil.exec_req("GET", vcenter_url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        vc_info = {}
        try:
            for vc in response.json()["results"]:
                if vc["name"] == vc_name:
                    vc_info["vcenter_url"] = vc["url"]
                    vc_info["vc_uuid"] = vc["uuid"]
            return vc_info, "SUCCESS"
        except KeyError:
            return vc_info, "SUCCESS"

    def _verify_vc_cluster(self, cloud_uuid, vc_info, vcenter_cluster):
        """
        verify vc cluster fetched from cloud data
        """
        cluster_url = AlbEndpoint.NSXT_CLUSTERS.format(ip=self.avi_host)

        payload = {"cloud_uuid": cloud_uuid, "vcenter_uuid": vc_info["vc_uuid"]}
        payload = json.dumps(payload, indent=4)
        response = RequestApiUtil.exec_req("POST", cluster_url, headers=self.headers, data=payload, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        for cluster in response.json()["resource"]["nsxt_clusters"]:
            if cluster["name"] == vcenter_cluster:
                vc_info["cluster"] = cluster["vc_mobj_id"]
                break
        return "SUCCESS", vc_info

    def configure_vcenter_in_nsxt_cloud(
        self,
        cloud_name,
        cloud_url,
        vcenter_cluster,
        vc_content_library_name,
        nsx_username,
        nsx_password,
        nsxt_overlays,
        nsxt_address,
    ):
        """
        add vcenter into nxt cloud
        :param cloud_name: name of the NSX cloud
        :param cloud_url: url of the cloud
        :param vcenter_cluster: vcenter cluster in plain english
        :param vc_content_library_name: vcenter content library name for OVA
        :param nsx_username: nsxt creds in english
        :param nsx_password: nsxt creds in english
        :param nsxt_overlays: nsxt overlays
        :param nsxt_address: nsxt address
        """
        try:
            uuid_response = self._get_cloud_uuid(cloud_name=cloud_name)
            if not uuid_response[0]:
                current_app.logger.error(f"{cloud_name} cloud not found")
                return None, f"{cloud_name} cloud not found"
            uuid = uuid_response[0]
            vc_info = self._fetch_vc_info(cloud_uuid=uuid, vc_name=AVIInfraOps.VC_NAME)
            if vc_info[0] is None:
                return vc_info
            if len(vc_info[0]) > 0:
                vc_response = self._verify_vc_cluster(
                    cloud_uuid=uuid, vc_info=vc_info[0], vcenter_cluster=vcenter_cluster
                )
                return vc_response
            else:
                cloud_connect_user, cred = self.create_cloud_connect_user(nsx_username, nsx_password)
                if cloud_connect_user is None:
                    return None, cred
                vcenter_credential = cred["vcenterUUId"]
                nsxt_credential = cred["nsxUUid"]
                if not vc_content_library_name:
                    vc_content_library_name = ControllerLocation.CONTROLLER_CONTENT_LIBRARY
                library, status_lib = self.fetch_content_library(vc_content_library_name)
                if library is None:
                    return None, status_lib
                tz_id, status_tz = self._fetch_transport_zone_id(nsxt_overlays, nsxt_address, nsxt_credential)
                if tz_id is None:
                    return None, status_tz
                vc_id, status_vc = self._fetch_vcenter_id(nsxt_credential, status_tz, nsxt_address)
                if vc_id is None:
                    return None, status_vc
                tenant_ref = (f"https://{self.avi_host}/api/tenant/admin",)
                vcenter_credentials_ref = f"https://{self.avi_host}/api/cloudconnectoruser/{vcenter_credential}"
                vcenter_url = AlbEndpoint.VCENTER_SERVER.format(ip=self.avi_host)
                payload = AlbPayload.VCENTER_NSX_PAYLOAD.format(
                    cloud_url=cloud_url,
                    content_lib=status_lib,
                    vc_content_library_name=vc_content_library_name,
                    vc_name=AVIInfraOps.VC_NAME,
                    tenant_ref=tenant_ref,
                    vcenter_creds_ref=vcenter_credentials_ref,
                    vcenter_url=status_vc,
                )
                # payload = json.dumps(payload, indent=4)
                response = RequestApiUtil.exec_req(
                    "POST", vcenter_url, headers=self.headers, data=payload, verify=False
                )
                if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
                    return None, response.text
                vc_info = self._fetch_vc_info(cloud_uuid=uuid, vc_name=AVIInfraOps.VC_NAME)
                if vc_info[0] is None:
                    return vc_info
                vc_response = self._verify_vc_cluster(
                    cloud_uuid=uuid, vc_info=vc_info[0], vcenter_cluster=vcenter_cluster
                )
                return vc_response
        except (KeyError, TypeError) as e:
            return None, str(e)
        except Exception as e:
            current_app.logger.info(f"exception in vcenter creation for NSXT cloud {str(e)}")
            return None, str(e)
