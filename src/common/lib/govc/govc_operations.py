# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import polling2
from flask import current_app

from common.lib.govc.govc_client import GOVClient
from common.operation.constants import ControllerLocation


class GOVCConstants:
    RESOURCE_PATH = "/Resources/{resource_pool}"
    VM_PATH = "/vm/{vm_name}"


class GOVCOperations:
    def __init__(
        self, vcenter_host, vcenter_username, vcenter_password, cluster_name, data_center, data_store, cmd_helper
    ):
        """ """
        self.vcenter_host = vcenter_host
        self.vcenter_username = vcenter_username
        self.vcenter_password = vcenter_password
        self.cluster_name = cluster_name
        self.data_center = data_center
        self.data_store = data_store
        self.govc_client = GOVClient(
            self.vcenter_host,
            self.vcenter_username,
            self.vcenter_password,
            self.cluster_name,
            self.data_center,
            self.data_store,
            cmd_helper,
        )

    @polling2.poll_decorator(step=5, timeout=10)
    def pool_objects(self, object_name, output_verify):
        """
        pool objects until they found and verify the output in object response
        """
        output = self.govc_client.find_objects_by_name(object_name=object_name)
        if not output:
            return False
        return all(data in output for data in output_verify)

    def validate_folder_and_resources_available(self, folder, resources, parent_resource_pool):
        """
        folder resource to verify in vCenter
        :param folder: folder to search for in resources
        :param resources: resource to search for in vCenter
        :param parent_resource_pool: parent resource to search in
        :returns: True if found else False
        """
        resource_pool = f"{parent_resource_pool}/{resources}" if parent_resource_pool else resources
        resource = GOVCConstants.RESOURCE_PATH.format(resource_pool=resource_pool)
        vm = GOVCConstants.VM_PATH.format(vm_name=folder)
        try:
            if self.pool_objects(object_name=folder, output_verify=[resource, vm]):
                current_app.logger.info("Folder and resources are available")
                return True
        except polling2.TimeoutException:
            # if object not found return False
            return False

    def get_network_folder(self, network_name):
        """
        search network name from vcenter
        :param network_name: network name to search for
        :returns: returns absolute path of the network else None
        """
        try:
            if self.pool_objects(object_name=network_name, output_verify=[network_name, "/network"]):
                # current_app.logger.info(f"Network is available {network_name}")
                return True
        except polling2.TimeoutException:
            # if object not found return False
            return False

    def get_library_id(self, lib_name):
        """
        take out library id from vcenter library name
        :param lib_name: name of the library
        :returns: library ID if found else None
        """
        output = self.govc_client.get_content_library_info(lib_name=lib_name)
        if len(output) == 0:
            return None
        # fetch library ID
        for lines in output:
            if "ID:" in lines:
                return lines.strip().split("ID:")[1].strip()
        return None

    def check_ova_is_present(self, content_library, ova_name):
        """
        check whether ova is present in content library or not
        :param content_library: content library to search for
        :param ova_name: ova name to search for
        :returns: True if ova is present in content library
        """
        output = self.govc_client.get_content_libraries(options=f"{content_library}/")
        for lines in output:
            if ova_name in lines:
                current_app.logger.info(f"{ova_name} is already present in content library {content_library}")
                return True
        else:
            return False

    def create_content_lib_if_not_exist(self, content_lib):
        """
        will create content library in vcenter with specified name, if not exists
        :param content_lib: name of the content lib needs to be created
        :returns: True if content library gets created else False
        """

        output = self.govc_client.get_content_libraries()
        for lines in output:
            if content_lib in lines:
                current_app.logger.info(f"{content_lib} is already present")
                return True
        else:
            output = self.govc_client.create_content_lib(content_lib=content_lib)
            if output != content_lib:
                return False
            return True

    def create_subscribed_library(self, lib_name, url, thumb_print=None):
        """
        creates subscribed content library with specified name in vcenter
        :param lib_name: content library name
        :param url: url for content library subscription
        :param thumb_print: thumbprint to use for library creation
        :returns: "SUCCESS" if passed else "ERROR"
        """
        try:
            output = self.govc_client.get_content_libraries()
            for lines in output:
                if lib_name in lines:
                    current_app.logger.info(ControllerLocation.SUBSCRIBED_CONTENT_LIBRARY + " is already present")
                    return "SUCCESS", "LIBRARY"
            output = self.govc_client.create_subscribed_content_lib(
                url=url, content_lib_name=lib_name, thumb_print=thumb_print
            )
            if "error" in output[0]:
                return None, "Failed to create content library"
            current_app.logger.info("Content library created successfully")
        except Exception as e:
            return None, "Failed in creating content lib" + str(e)
        return "SUCCESS", "LIBRARY"

    def check_vm_template_is_present(self, template):
        try:
            output = self.govc_client.list_all_vms()
            for vm in output:
                if template in vm:
                    return True
            return False
        except Exception as e:
            current_app.logger.error(f"Exception occurred while finding the template {template} - {str(e)}")
            return False
