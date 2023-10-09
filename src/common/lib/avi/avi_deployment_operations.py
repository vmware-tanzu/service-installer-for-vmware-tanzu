# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

from http import HTTPStatus

from flask import current_app

from common.lib.avi.avi_admin_operations import AVIAdminOps
from common.lib.avi.avi_constants import AVIConfig
from common.util.request_api_util import RequestApiUtil


class AVIDeploymentOps:
    """
    class can be used for deploying and configuring initial AVI setup
    """

    def __init__(
        self,
        govc_client,
        avi_controller_ova_path,
        required_avi_version,
        data_center,
        avi_size,
        tenant_vrf,
        backup_pass_phrase,
        is_tkgs,
        dns_ip,
        ntp_ip,
        search_domains,
        avi_password,
        license_type="enterprise",
    ):
        """
        #TODO spec
        :param govc_client: govc client object
        :param avi_controller_ova_path: absolute path for of AVI controller ova in content library
        :param required_avi_version: expected avi version for the deployment
        :param data_center: data center for AVI deployment
        :param tenant_vrf: tenant vrf set False for VMC deployment
        :param backup_pass_phrase: backup pass phrase for AVI deployment
        :param avi_size: size of the AVI node
        :param is_tkgs: flag to be set True for TKGs deployment
        :param dns_ip: DNS IP to be set on AVI VM
        :param ntp_ip: NTP IP to be set on AVI VM
        :param search_domains: search domains to be set on AVI VM
        :param license_type: avi license type
        :param avi_password: avi password for the deployed VM
        :env:
        """
        self.govc_client = govc_client
        self.avi_controller_ova_path = avi_controller_ova_path
        self.required_avi_version = required_avi_version
        self.data_center = data_center
        self.avi_size = avi_size
        self.tenant_vrf = tenant_vrf
        self.avi_admin_ops = None
        self.backup_pass_phrase = backup_pass_phrase
        self.avi_size = avi_size
        self.is_tkgs = is_tkgs
        self.dns_ip = dns_ip
        self.ntp_ip = ntp_ip
        self.search_domains = search_domains
        self.avi_password = avi_password
        self.license_type = license_type

    def _deploy_avi_controller(self, avi_vm_name, deploy_options, cpu, memory):
        """
        deploy VM on vcenter using govc client
        """
        self.govc_client.deploy_library_ova(
            location=self.avi_controller_ova_path, name=avi_vm_name, options=deploy_options
        )
        self.govc_client.set_vm_config(vm_name=avi_vm_name, cpu=cpu, memory=memory)
        self.govc_client.power_on_vm(vm_name=avi_vm_name)
        return self.govc_client.get_vm_ip(wait_time="30m", vm_name=avi_vm_name)

    def _configure_avi(self):
        """
        configure initial avi settings after avi deployment
        """
        csrf = self.avi_admin_ops.obtain_first_csrf()
        if csrf[0] is None:
            msg = "Failed to get First csrf value."
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        if csrf[0] == "SUCCESS":
            current_app.logger.info("Password of appliance already changed")
        else:
            if self.avi_admin_ops.set_avi_admin_password() is None:
                msg = "Failed to set the AVI admin password"
                current_app.logger.error(msg)
                return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        csrf2 = self.avi_admin_ops.obtain_second_csrf()
        if csrf2 is None:
            msg = "Failed to get csrf from new set password"
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("Obtained csrf with new credential successfully")
        if self.avi_admin_ops.get_system_configuration() is None:
            msg = "Failed to set the system configuration"
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("Fetched system configuration successfully")
        # update for TKgs deployment
        if self.is_tkgs:
            AVIAdminOps.update_portal_config()
        AVIAdminOps.update_system_config(
            ntp_server_ip=self.ntp_ip, dns_server_ip=self.dns_ip, search_domains=self.search_domains
        )

        if self.license_type is None:
            self.license_type = "enterprise"
        AVIAdminOps.update_license_config(type_of_avi_license=self.license_type)
        if self.avi_admin_ops.set_dns_ntp_smtp_settings() is None:
            msg = "Set DNS NTP SMTP failed."
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("Set DNS NTP SMTP successfully")
        if self.avi_admin_ops.disable_welcome_screen() is None:
            msg = "Failed to deactivate welcome screen"
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("Deactivate welcome screen successfully")
        backup_url = self.avi_admin_ops.get_backup_configuration()
        if backup_url[0] is None:
            msg = "Failed to get backup configuration"
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            current_app.logger.info("Fetched backup configuration successfully")
        current_app.logger.info("Set backup pass phrase")
        set_backup = self.avi_admin_ops.set_backup_phrase(backup_url[0], self.backup_pass_phrase)
        if set_backup[0] is None:
            msg = f"Failed to set backup pass phrase {str(set_backup[1])}"
            current_app.logger.error(msg)
            return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
        return RequestApiUtil.send_ok(message="Configured AVI"), HTTPStatus.OK

    def deploy_and_configure_avi(self, deploy_options, perform_other_task, vm_name):
        """
        external facing method for verify AVI and deploying it as well as configuring it
        :param deploy_options: AVI deploy VM options, config, data center, cluster etc
        :param perform_other_task: flag set to True, for main node deployment False, for HA node deployment
        :param vm_name: avi VM name
        """
        try:
            avi_ip = None
            fetched_ip = self.govc_client.get_vm_ip(vm_name=vm_name)
            if fetched_ip is not None:
                self.avi_admin_ops = AVIAdminOps(avi_host=fetched_ip[0], avi_password=self.avi_password)
                avi_ip = fetched_ip[0]
                current_app.logger.info("Received IP: " + fetched_ip[0] + " for VM: " + vm_name)
                current_app.logger.info("Checking if controller with IP : " + fetched_ip[0] + " is already UP")
                check_controller_up = self.avi_admin_ops.check_controller_is_up(only_check=True)
                if check_controller_up is None:
                    current_app.logger.error(
                        "Controller with IP: " + fetched_ip[0] + " is not UP, recommended to cleanup"
                        " or use a different FQDN for the "
                        "controller VM"
                    )
                    msg = "Controller is already deployed but is not UP"
                    return RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
                else:
                    current_app.logger.info("Controller is already deployed and is UP and Running")

            else:
                current_app.logger.info("Deploying AVI controller..")
                size = str(self.avi_size).lower()
                if size not in ["essentials", "small", "medium", "large"]:
                    msg = f"Wrong AVI size provided, supported essentials/small/medium/large got {size}"
                    current_app.logger.error(msg)
                    RequestApiUtil.send_error(message=msg), HTTPStatus.INTERNAL_SERVER_ERROR
                cpu = AVIConfig.AVI_SIZE[size]["cpu"]
                memory = AVIConfig.AVI_SIZE[size]["memory"]
                fetched_ip = self._deploy_avi_controller(
                    deploy_options=deploy_options, cpu=cpu, memory=memory, avi_vm_name=vm_name
                )
                self.avi_admin_ops = AVIAdminOps(avi_host=fetched_ip[0], avi_password=self.avi_password)
                avi_ip = fetched_ip[0]
                if fetched_ip is None:
                    message = "Failed to get IP of AVI controller on waiting 30m"
                    current_app.logger.error(message)
                    return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR
                current_app.logger.info("Checking controller is up")
                if self.avi_admin_ops.check_controller_is_up(only_check=False) is None:
                    message = "Controller service is not up"
                    current_app.logger.error(message)
                    return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR
        except Exception as e:
            message = f"Failed to deploy the VM from library due to {str(e)}"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR

        self.avi_admin_ops = AVIAdminOps(avi_host=avi_ip, avi_password=self.avi_password)
        deployed_avi_version = self.avi_admin_ops.obtain_avi_version()
        if deployed_avi_version[0] is None:
            message = f"Failed to login and obtain AVI version {str(deployed_avi_version[1])}"
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR
        avi_version = deployed_avi_version[0]
        if str(avi_version) != self.required_avi_version:
            message = (
                f"Deployed avi version {str(avi_version)} is not supported, supported version is: "
                f"{self.required_avi_version}"
            )
            current_app.logger.error(message)
            return RequestApiUtil.send_error(message=message), HTTPStatus.INTERNAL_SERVER_ERROR
        if perform_other_task:
            return self._configure_avi()
        return RequestApiUtil.send_ok(message="Configured AVI"), HTTPStatus.OK
