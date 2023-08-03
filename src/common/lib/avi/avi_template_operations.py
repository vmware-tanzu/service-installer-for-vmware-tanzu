# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json
from http import HTTPStatus
from pathlib import Path

from flask import current_app

from common.constants.alb_api_constants import AlbEndpoint, AlbPayload
from common.lib.avi.avi_base_operations import AVIBaseOperations
from common.lib.avi.avi_constants import AVIDataFiles
from common.lib.avi.avi_helper import AVIHelper
from common.operation.constants import CertName
from common.replace_value import replaceCertConfig
from common.util.file_helper import FileHelper
from common.util.request_api_util import RequestApiUtil


class AVITemplateOperations(AVIBaseOperations):
    """
    class for handling AVI certificate endpoints
    """

    def __init__(self, avi_host, password, cert_name):
        """ """
        super().__init__(avi_host, password)
        self.avi_version = self.obtain_avi_version()[0]
        self.second_csrf = self.obtain_second_csrf()
        self.headers = self._operation_headers(self.second_csrf)
        self.cert_name = cert_name

    def _get_ssl_certificate_status(self, cert_name):
        """
        get ssl certificate status with specified cert name
        :param cert_name: name of the cert
        """
        url = AlbEndpoint.CRUD_SSL_CERT.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            for res in response.json()["results"]:
                if res["name"] == cert_name:
                    return res["url"], "SUCCESS"
            return "NOT_FOUND", "SUCCESS"

    def get_avi_certificate(self, cert_name):
        """
        fetch certificate from AVI
        :param cert_name: name of the cert
        """
        url = AlbEndpoint.CRUD_SSL_CERT.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            current_app.logger.error("Failed to get certificate " + response.text)
            return None, response.text
        else:
            for res in response.json()["results"]:
                if res["name"] == cert_name:
                    return res["certificate"]["certificate"], "SUCCESS"
        return "NOT_FOUND", "FAILED"

    def _import_ssl_certificate(self, cert_name, certificate, certificate_key):
        """
        import ssl certificate inside AVI controller using AVI endpoints
        :param cert_name: name of the certificate
        :param certificate: certificate data
        :param certificate_key:  certificate key
        """
        body = AlbPayload.IMPORT_CERT.format(cert=certificate, cert_key=certificate_key)
        url = AlbEndpoint.IMPORT_SSL_CERTIFICATE.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("POST", url, headers=self.headers, data=body, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            output = response.json()
            dic = {
                "issuer_common_name": output["certificate"]["issuer"]["common_name"],
                "issuer_distinguished_name": output["certificate"]["issuer"]["distinguished_name"],
                "subject_common_name": output["certificate"]["subject"]["common_name"],
                "subject_organization_unit": output["certificate"]["subject"]["organization_unit"],
                "subject_organization": output["certificate"]["subject"]["organization"],
                "subject_locality": output["certificate"]["subject"]["locality"],
                "subject_state": output["certificate"]["subject"]["state"],
                "subject_country": output["certificate"]["subject"]["country"],
                "subject_distinguished_name": output["certificate"]["subject"]["distinguished_name"],
                "not_after": output["certificate"]["not_after"],
                "cert_name": cert_name,
            }
            return dic, "SUCCESS"

    def _create_imported_ssl_certificate(self, cert_name, imported_cert, cert_data, key_data):
        """
        :param cert_name:
        :param imported_cert: imported cert data from AVI
        :param cert_data: cert data to be updated on AVI
        :param key_data: key data to be updated on AVI
        """
        body = AlbPayload.IMPORTED_CERTIFICATE.format(
            cert=cert_data,
            subject_common_name=imported_cert["subject_common_name"],
            org_unit=imported_cert["subject_organization_unit"],
            org=imported_cert["subject_organization"],
            location=imported_cert["subject_locality"],
            state_name=imported_cert["subject_state"],
            country_name=imported_cert["subject_country"],
            distinguished_name=imported_cert["subject_distinguished_name"],
            not_after_time=imported_cert["not_after"],
            cert_name=cert_name,
            cert_key=key_data,
        )
        url = AlbEndpoint.CRUD_SSL_CERT.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("POST", url, headers=self.headers, data=body, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            return response.json()["url"], "SUCCESS"

    def generate_ssl_certificate(self, list_of_ips):
        """
        :param list_of_ips: list of AVI ips and AVI fqdn's
        """
        san = json.dumps(list_of_ips)
        body = AlbPayload.SELF_SIGNED_CERT.format(name=CertName.NAME, common_name=CertName.COMMON_NAME, san_list=san)
        url = AlbEndpoint.CRUD_SSL_CERT.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("POST", url, headers=self.headers, data=body, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            return response.json()["url"], "SUCCESS"

    def _get_current_cert_config(self, generated_ssl_url):
        """
        fetch cert config and push it in config json file
        :param generated_ssl_url: generated ssl url
        """
        url = AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            FileHelper.delete_file(AVIDataFiles.SYS_CONFIG)
            FileHelper.dump_json(file=AVIDataFiles.SYS_CONFIG, json_dict=response.json())
            replaceCertConfig(
                AVIDataFiles.SYS_CONFIG, "portal_configuration", "sslkeyandcertificate_refs", generated_ssl_url
            )
            return response.json()["url"], "SUCCESS"

    def _replace_with_new_cert(self):
        """
        update AVI cert with new onw
        """
        json_object = FileHelper.load_json(spec_path=AVIDataFiles.SYS_CONFIG)
        json_object_mo = json.dumps(json_object, indent=4)
        url = f"{AlbEndpoint.CRUD_SYSTEM_CONFIG.format(ip=self.avi_host)}/?include_name="
        response = RequestApiUtil.exec_req("PUT", url, headers=self.headers, data=json_object_mo, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            return "SUCCESS", HTTPStatus.OK

    def _configure_alb_license(self, license_key):
        """
        apply license to AVi server
        :param license_key: license key to apply on AVI
        """
        body = AlbPayload.LICENSE.format(serial_number=license_key)
        url = AlbEndpoint.LICENSE_URL.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        json_object = response.json()["licenses"]
        for data in json_object:
            if data["license_string"] == license_key:
                return "SUCCESS", "Already license is applied"
        response = RequestApiUtil.exec_req("PUT", url, headers=self.headers, data=body, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        json_object = response.json()["licenses"]
        for data in json_object:
            if data["license_string"] == license_key:
                return "SUCCESS", "License is applied successfully"
        return None, "Failed to apply License"

    def manage_avi_certificates(self, avi_hosts: list, cert_path: str, cert_key: str) -> tuple:
        """
        act as starting point for applying license on AVI. call further methods for the operation
        :param avi_hosts: list of AVI hosts and IPs to apply certificate
        :param cert_path: cert file path
        :param cert_key: cert key file path
        """
        # will be populated for avi path and key
        import_cert = None
        avi_controller_cert = None
        avi_controller_cert_key = None
        license_key = ""
        if cert_path and cert_key:
            exist = True
            msg1 = ""
            msg2 = ""
            if not Path(cert_path).exists():
                exist = False
                msg1 = "Certificate does not exist, please copy certificate file to location " + cert_path
            if not Path(cert_key).exists():
                exist = False
                msg2 = "Certificate key does not exist, please copy key file to location " + cert_key
            if not exist:
                message = msg1 + " " + msg2
                current_app.logger.error(message)
                return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR, False
            current_app.logger.info("Converting pem to one line")
            avi_controller_cert = AVIHelper.pem_file_to_lines(cert_path)
            avi_controller_cert_key = AVIHelper.pem_file_to_lines(cert_key)
            if not avi_controller_cert or not avi_controller_cert_key:
                message = "Certificate or key provided is empty"
                current_app.logger.error(message)
                return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR, False
            import_cert, error = self._import_ssl_certificate(
                cert_name=self.cert_name, certificate=avi_controller_cert, certificate_key=avi_controller_cert_key
            )
            if import_cert is None:
                message = "AVI cert import failed " + str(error)
                current_app.logger.error(message)
                return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR, False
            self.cert_name = import_cert["cert_name"]
        get_cert = self._get_ssl_certificate_status(self.cert_name)
        if get_cert[0] is None:
            message = "Failed to get certificate status " + str(get_cert[1])
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR, False

        if get_cert[0] == "NOT_FOUND":
            current_app.logger.info("Generating cert")
            if cert_path and cert_key:
                res = self._create_imported_ssl_certificate(
                    cert_name=self.cert_name,
                    imported_cert=import_cert,
                    cert_data=avi_controller_cert,
                    key_data=avi_controller_cert_key,
                )
            else:
                res = self.generate_ssl_certificate(list_of_ips=avi_hosts)
            url = res[0]
            if res[0] is None:
                message = "Failed to generate the ssl certificate"
                current_app.logger.error(message)
                return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR, False
        else:
            url = get_cert[0]
        get_cert = self._get_current_cert_config(url)
        if get_cert[0] is None:
            message = "Failed to get current certificate"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR, False
        current_app.logger.info("Replacing cert")
        replace_cert = self._replace_with_new_cert()
        if replace_cert[0] is None:
            message = "Failed replace the certificate" + replace_cert[1]
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR, False
        # TODO license_key is always blank check with others
        if license_key:
            res, status = self._configure_alb_license(license_key)
            if res is None:
                message = "Failed to apply licenses " + str(status)
                current_app.logger.error(message)
                return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR, False
            current_app.logger.info(status)
        msg = "Certificate managed successfully"
        return RequestApiUtil.send_ok(message=msg), HTTPStatus.OK, True

    def _ipam_creator(self, ipam_body):
        """
        helper function for ipam creation takes ipam body as input.
        """
        url = AlbEndpoint.PROFILE.format(ip=self.avi_host)
        json_object = json.dumps(ipam_body, indent=4)
        response = RequestApiUtil.exec_req("POST", url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.CREATED):
            return None, response.text
        else:
            return response.json()["url"], "SUCCESS"

    def create_ipam(self, main_network_url, data_network_url, vip_network_url, name):
        """
        create IPAM in AVI for vsphere
        :param main_network_url: main node network URL reference
        :param data_network_url: Data network URL reference
        :param vip_network_url: VIP network URL reference
        :param name: name of the ipam
        """
        ipam_body = AlbPayload.NSXT_IPAM_BODY.format(
            name=name, network_url=main_network_url, data_networ_url=data_network_url, vip_network=vip_network_url
        )
        return self._ipam_creator(ipam_body=ipam_body)

    def create_ipam_nsxt_cloud(self, vip_network_url, data_network_url, name):
        """
        create IPAM in AVI for NSXT-cloud
        :param data_network_url: Data network URL reference
        :param vip_network_url: VIP network URL reference
        :param name: name of the ipam
        """
        ipam_body = AlbPayload.IPAM_BODY.format(
            name=name, data_networ_url=data_network_url, vip_network=vip_network_url
        )
        return self._ipam_creator(ipam_body)

    def create_ipam_arch(self, vip_network_url, data_network_url, name):
        """
        create IPAM in AVI for non-orchestrated cloud deployment
        :param data_network_url: Data network URL reference
        :param vip_network_url: VIP network URL reference
        :param name: name of the ipam
        """
        ipam_body = AlbPayload.ORCH_IPAM_BODY.format(
            name=name, data_networ_url=data_network_url, vip_network=vip_network_url
        )
        return self._ipam_creator(ipam_body)

    def get_ipam(self, name):
        """
        :param name: fetch ipam with provided name
        :return: ipam data
        """
        url = AlbEndpoint.PROFILE.format(ip=self.avi_host)
        response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            FileHelper.delete_file(AVIDataFiles.IPAM_DETAILS)
            FileHelper.dump_json(file=AVIDataFiles.IPAM_DETAILS, json_dict=response.json())
            for res in response.json()["results"]:
                if res["name"] == name:
                    return res["url"], "SUCCESS"
        return "NOT_FOUND", "SUCCESS"

    def update_ipam(self, new_cloud_url):
        """
        update IPAM in cloud
        :param new_cloud_url: cloud url to update with IPAM
        :return:
        """
        new_cloud_json = FileHelper.load_json(AVIDataFiles.NEW_CLOUD_IPAM_DETAILS)
        json_object = json.dumps(new_cloud_json, indent=4)
        response = RequestApiUtil.exec_req("PUT", new_cloud_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            return response.json(), "SUCCESS"

    def update_ipam_profile(self, ipam_name, network_url):
        """
        :param network_url: network url of the network to be updated IPAM
        :param ipam_name: network url of the network name provided
        """
        ipam_json = FileHelper.load_json(AVIDataFiles.IPAM_DETAILS)
        ipam_obj = dict()
        for ipam in ipam_json["results"]:
            if ipam["name"] == ipam_name:
                ipam_obj = ipam
                break
        ipam_url = ipam_obj["url"]
        response = RequestApiUtil.exec_req("GET", ipam_url, headers=self.headers, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        update = response.json()
        networks = []
        for usable in update["internal_profile"]["usable_networks"]:
            if usable["nw_ref"] == str(network_url):
                return "Already configured", "SUCCESS"
            networks.append(usable)
        networks.append({"nw_ref": network_url})
        update["internal_profile"]["usable_networks"] = networks
        FileHelper.dump_json(file=AVIDataFiles.IPAM_DETAILS_GET, json_dict=update)
        updated_body = FileHelper.load_json(AVIDataFiles.IPAM_DETAILS_GET)
        json_object = json.dumps(updated_body, indent=4)
        response = RequestApiUtil.exec_req("PUT", ipam_url, headers=self.headers, data=json_object, verify=False)
        if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
            return None, response.text
        else:
            return response.json()["url"], "SUCCESS"

    def create_dns_nsxt_cloud(self, dns_domain, dns_profile_name):
        """
        Update DNS in NSX-T cloud
        :param dns_domain: name of the DNS to add
        :param dns_profile_name: name of the profile to be update
        """
        try:
            body = AlbPayload.NSXT_DNS_BODY.format(dns_domain=dns_domain, dns_profile_name=dns_profile_name)
            dns_url = AlbEndpoint.PROFILE.format(ip=self.avi_host)
            response = RequestApiUtil.exec_req("POST", dns_url, headers=self.headers, data=body, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text
            else:
                return response.json()["url"], response.json()["uuid"], "SUCCESS"
        except (KeyError, TypeError) as e:
            current_app.logger.error(str(e))
            return None, "Exception occurred while creation DNS profile for NSXT-T Cloud "
        except Exception as e:
            current_app.logger.error(f"exception in {str(e)}")
            return None, "Exception occurred while creation DNS profile for NSXT-T Cloud "

    def associate_ipam_nsxt_cloud(self, nsxt_cloud_uuid, ipam_url, dns_url):
        """
        Add IPAM to NSXT-cloud
        """
        try:
            url = AlbEndpoint.GET_CLOUD.format(ip=self.avi_host, cloud_uuid=nsxt_cloud_uuid)
            cloud_details_response = RequestApiUtil.exec_req("GET", url, headers=self.headers, verify=False)
            if not RequestApiUtil.verify_resp(cloud_details_response, status_code=HTTPStatus.OK):
                return None, "Failed to fetch IPAM details for NSXT Cloud"

            # append ipam details to response
            ipam_details = {"ipam_provider_ref": ipam_url, "dns_provider_ref": dns_url}
            json_response = cloud_details_response.json()
            json_response.update(ipam_details)
            json_object = json.dumps(json_response, indent=4)

            response = RequestApiUtil.exec_req("PUT", url, headers=self.headers, data=json_object, verify=False)
            if not RequestApiUtil.verify_resp(response, status_code=HTTPStatus.OK):
                return None, response.text

            return "SUCCESS", "IPAM/DNS association with NSXT Cloud completed"
        except (KeyError, TypeError) as e:
            current_app.logger.error(str(e))
            return None, "Exception occurred during association of DNS and IPAM profile with NSX-T Cloud"
        except Exception as e:
            current_app.logger.error(f"exception in {str(e)}")
            return None, "Exception occurred during association of DNS and IPAM profile with NSX-T Cloud"
