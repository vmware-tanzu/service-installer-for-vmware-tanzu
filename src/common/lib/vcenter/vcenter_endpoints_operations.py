# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause


import base64

import requests
from flask import current_app, jsonify

from common.common_utilities import getIpFromHost, is_ipv4
from common.util.request_api_util import RequestApiUtil


class VCEndpointURLs:
    # url belongs to VCENTER URL e.g. https//vcenter.tanzu.lab
    VC_SESSION = "{url}/rest/com/vmware/cis/session"
    STORAGE_POLICES = "{url}/api/vcenter/storage/policies"
    VC_API_SESSION = "{url}/api/session"
    VC_API_HOST = "{url}/api/vcenter/host"
    VC_CLUSTER = "{url}/api/vcenter/namespace-management/clusters/{cluster_id}"
    VC_DATACENTER = "{url}/api/vcenter/datacenter?names={dc_name}"
    VC_CLUSTER_DC = "{url}/api/vcenter/cluster?names={cluster}&datacenters={datacenter_id}"
    VC_NAMESPACE = "{url}/api/vcenter/namespaces/instances/{name_space}"


class VCEndpointOperations:
    def __init__(self, vcenter_host, vcenter_username, vcenter_password):
        self.vcenter_host = vcenter_host
        self.vcenter_username = vcenter_username
        self.vcenter_password = vcenter_password
        self.vcenter_url = "https://" + vcenter_host

    def get_session(self):
        """
        Make call to vc to get session
        :returns: session
        """
        url = VCEndpointURLs.VC_SESSION.format(url=self.vcenter_url)
        sess = requests.post(url, auth=(self.vcenter_username, self.vcenter_password), verify=False)
        if sess.status_code != 200:
            response = RequestApiUtil.create_json_object(
                "Failed to fetch session ID for vCenter - " + self.vcenter_url, "ERROR", sess.status_code
            )
            return response, sess.status_code
        else:
            vc_session = sess.json()["value"]

        return vc_session, 200

    def vc_cluster(self, vcenter_server, cluster_id):
        sess = requests.post(
            VCEndpointURLs.VC_SESSION.format(url="https://" + str(vcenter_server)),
            auth=(self.vcenter_username, self.vcenter_password),
            verify=False,
        )
        if sess.status_code != 200:
            current_app.logger.error("Connection to vCenter failed")
            return sess
        else:
            vc_session = sess.json()["value"]

        header = {"Accept": "application/json", "Content-Type": "application/json", "vmware-api-session-id": vc_session}

        url = VCEndpointURLs.VC_CLUSTER.format(url="https://" + str(vcenter_server), cluster_id=cluster_id)

        response = requests.request("GET", url, headers=header, verify=False)
        return response

    def get_storage_policies(self):
        """
        list down all the storage policies inside vcenter
        :returns: all policies list
        """
        try:
            vc_session, status_code = self.get_session()
            if status_code != 200:
                return vc_session, status_code
            header = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "vmware-api-session-id": vc_session,
            }
            url = VCEndpointURLs.STORAGE_POLICES.format(url=self.vcenter_url)
            storage_policies = requests.request("GET", url, headers=header, verify=False)
            if storage_policies.status_code != 200:
                d = {"responseType": "ERROR", "msg": "Failed to fetch storage policies", "STATUS_CODE": 500}
                return jsonify(d), 500

            return storage_policies.json(), 200

        except Exception as e:
            current_app.logger.error(e)
            d = {
                "responseType": "ERROR",
                "msg": "Exception occurred while fetching storage policies",
                "STATUS_CODE": 500,
            }
            return jsonify(d), 500

    def get_policy_id(self, policy_name):
        """
        fetch policy id from policy name
        :param policy_name: policy name search for
        :returns: policy id of the passed policy name
        """
        try:
            policies = self.get_storage_policies()
            if policies[1] != 200:
                return None, 500
            for policy in policies[0]:
                if policy["name"] == policy_name:
                    return policy["policy"], 200
            else:
                current_app.logger.error("Provided policy not found - " + policy_name)
                return None, 500
        except Exception as e:
            current_app.logger.error(e)
            return None, 500

    def get_ESXI_IPs(self):
        """
        list down IP's of all ESXI host machine avialble in vCenter
        :returns: list of all ESXI IP's
        """
        try:
            encoded_bytes = (self.vcenter_username + ":" + self.vcenter_password).encode("ascii")
            encoded_bytes = base64.b64encode(encoded_bytes)
            encoded_string = encoded_bytes.decode("ascii")
            url = VCEndpointURLs.VC_API_SESSION.format(url=self.vcenter_url)
            headers = {"Authorization": ("Basic " + encoded_string)}
            response = requests.request("POST", url, headers=headers, verify=False)
            if response.status_code != 201:
                return None, response.status_code
            url = VCEndpointURLs.VC_API_HOST.format(url=self.vcenter_url)
            header = {"vmware-api-session-id": response.json()}
            response = requests.request("GET", url, headers=header, verify=False)
            if response.status_code != 200:
                return None, response.text
            ips = ""
            for esx in response.json():
                if not is_ipv4(esx):
                    ips += getIpFromHost(esx["name"]) + ","
                else:
                    ips += esx["name"] + ","
            if not ips:
                return None, "EMPTY"
            return ips.strip(","), "SUCCESS"
        except Exception as e:
            return None, str(e)
