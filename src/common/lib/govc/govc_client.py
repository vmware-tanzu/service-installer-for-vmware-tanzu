# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json
import os

from flask import current_app

from common.lib.govc.govc_constants import GovcCommands, VmPowerState
from common.util.base_cmd_helper import BaseCmdHelper


class GOVClient:
    """
    wrapper class for running all vcenter operation using govc commands
    """

    def __init__(
        self,
        vcenter_host,
        vcenter_username,
        vcenter_password,
        cluster_name,
        data_center,
        data_store,
        cmd_helper: BaseCmdHelper,
    ):
        """
        :param vcenter_host: vcenter host ip/fqdn
        :param vcenter_username: vcenter username
        :param vcenter_password: vcenter password decoded password
        :param cluster_name: cluster from vcenter
        :param data_center: data center name from vcenter
        :param data_store: data store name from vcenter
        :param cmd_helper: command helper for running govc command
        """
        self.cmd_runner = cmd_helper
        self.vcenter_host = vcenter_host
        self.vcenter_username = vcenter_username
        self.vcenter_password = vcenter_password
        self.cluster_name = cluster_name
        self.data_center = data_center
        self.data_store = data_store
        self.skip_verification = True
        self.set_env_vars()

    def set_env_vars(self):
        """
        set up environment variables before running any govc command
        """
        # current_app.logger.info("Setting GOVC environment variables")
        os.environ["GOVC_URL"] = self.vcenter_host
        os.environ["GOVC_USERNAME"] = self.vcenter_username
        os.environ["GOVC_PASSWORD"] = self.vcenter_password
        os.environ["GOVC_INSECURE"] = json.dumps(self.skip_verification)

    def find_datacenter_by_name(self, data_center, options=""):
        """
        function to get datacenter name from vcenter
        :returns: name of the data center with absolute path e.g. /stig-dc, if not found then NONE
        """
        cmd = GovcCommands.FIND_DATACENTER_BY_NAME.format(dc_name=data_center, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output.strip() if output and output.strip() != "" else None

    def find_objects_by_name(self, object_name, options=""):
        """
        finds object from vcenter with specified name
        :param object_name: object name to search for
        :param options: extra options
        :returns: found objects in string form with absolute path e.g. /stig-dc, if not found then NONE
        """
        cmd = GovcCommands.FIND_OBJECTS_BY_NAME.format(object_name=object_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output.strip() if output and output.strip() != "" else None

    def find_clusters_by_name(self, cluster_name, options=""):
        """
        finds object from vcenter with specified name
        :param cluster_name: cluster name to search for
        :param options: extra options
        :returns: found objects in string form with absolute path e.g. /stig-dc, if not found then NONE
        """
        cmd = GovcCommands.FIND_CLUSTERS_BY_NAME.format(clu_name=cluster_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def find_resource_pools_by_name(self, pool_name, options=""):
        """
        finds resource pool from vcenter with specified name
        :param pool_name: pool name to search for
        :param options: extra options
        :returns: found pool in string form with absolute path e.g.
        /stig-dc/host/stig/Resources/tkg-vsphere-tkg-Mgmt', if not found then NONE
        """
        cmd = GovcCommands.FIND_RESOURCE_POOLS_BY_NAME.format(rp_name=pool_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def delete_resource_pool(self, rp_path, options=""):
        """
        delete resource pool from vcenter with specified absolute path,
        :param rp_path: absolute resource pool path e.g. /stig-dc/host/stig/Resources/tkg-vsphere-tkg-Mgmt
        :param options: extra options
        :returns: ''
        """
        cmd = GovcCommands.DELETE_RESOURCE_POOL.format(path=rp_path, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def find_folders_by_name(self, folder_name, options=""):
        """
        find folder with specified folder name
        :param folder_name: name of the folder
        :param options: extra options
        :returns: found pool in string form with absolute path e.g.
        /stig-dc/host/stig/Resources/tkg-vsphere-tkg-Mgmt', if not found then NONE
        """
        cmd = GovcCommands.FIND_FOLDERS_BY_NAME.format(folder_name=folder_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def find_vms_by_name(self, vm_name, options=""):
        """
        find vm from vcenter with specified name,
        :param vm_name: vm name to search e.g. 'NTP'
        :param options: extra options
        :returns: absolute path of the found VM e.g. /stig-dc/vm/NTP
        """
        cmd = GovcCommands.FIND_VMS_BY_NAME.format(vm_name=vm_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def find_networks_by_name(self, network_name, options=""):
        """
        find network from vcenter with specified name,
        :param network_name: network name to search e.g. 'VC-MGMT'
        :param options: extra options
        :returns: ''
        """
        cmd = GovcCommands.FIND_NETWORKS_BY_NAME.format(network_name=network_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def create_resource_pool(self, pool, options=""):
        """
        Create a resource pool if not exists and return the absolute path of the resource pool
        :param pool: pool name to be created
        :param options: extra options
        :returns: created pool name
        """
        existing_pools = self.find_resource_pools_by_name(pool.split("/")[-1])
        if not existing_pools or pool not in existing_pools:
            cmd = GovcCommands.CREATE_RESOURCE_POOL.format(pool=pool, options=options)
            self.cmd_runner.run_cmd(cmd)
        return pool

    def create_folder(self, folder, options=""):
        """
        Create a folder if not exists and return the absolute path of the folder
        :param folder: folder name to be created
        :param options: extra options
        :returns: created folder name
        """
        existing_folders = self.find_folders_by_name(folder.split("/")[-1])
        if not existing_folders or folder not in existing_folders:
            cmd = GovcCommands.CREATE_FOLDER.format(folder=folder, options=options)
            self.cmd_runner.run_cmd(cmd)
        return folder

    def create_content_lib(self, content_lib):
        """
        Create a content library if not exists and return the absolute path of the libraries
        :param content_lib: folder name to be created
        :returns: created content_lib name
        """
        existing_lib = self.get_content_libraries(content_lib.split("/")[-1])
        if not existing_lib or content_lib not in existing_lib:
            cmd = GovcCommands.CREATE_CONTENT_LIB.format(
                lib=content_lib, data_center=self.data_center, data_store=self.data_store
            )
            self.cmd_runner.run_cmd(cmd)
        return content_lib

    def check_network_exists(self, network_name, options=""):
        """
        check if the network exists or not with specified network name
        :param network_name: name of the network
        :param options: extra options
        :returns: return TRUE of exists else not
        """
        existing_networks = self.find_networks_by_name(network_name, options)
        return existing_networks and any(network_name == nw.split("/")[-1] for nw in existing_networks)

    def deploy_library_ova(self, location, name, options=""):
        """
        deploy the ova in library
        :param location: specified location for ova deployment
        :param name: name of the ova
        :param options: extra options
        :returns:
        """
        cmd = GovcCommands.DEPLOY_LIBRARY_OVA.format(location=location, name=name, options=options)
        self.cmd_runner.run_cmd(cmd)

    def get_vm_ip(self, vm_name, wait_time="5m"):
        """
        get vm ip with specified vm_name
        :param vm_name: name of the vm
        :param wait_time:
        :returns: vm ip
        """
        if not self.find_vms_by_name(vm_name):
            return None
        options = ""
        if wait_time:
            options += f"-wait {wait_time}"
        if self.get_vm_power_state(vm_name=vm_name) == VmPowerState.OFF:
            current_app.logger.warn(vm_name + " is in power-off state")
            return None
        cmd = GovcCommands.GET_VM_IP.format(name=vm_name, datacenter=self.data_center, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def get_vm_power_state(self, vm_name):
        """
        get vm state with specified vm name
        :param vm_name: name of the vm
        :returns: vm state
        """
        power_state_filter = "-runtime.powerState {state}"
        for v in VmPowerState.__members__.values():
            if self.find_vms_by_name(vm_name, options=power_state_filter.format(state=v.value)):
                return v
        raise ValueError(f"VM not found by name {vm_name}")

    def get_vm_path(self, vm_name):
        """
        get vm absolute with specified vm name
        :param vm_name: name of the vm
        :returns: vm absolute path
        """
        if not self.find_vms_by_name(vm_name):
            return None
        cmd = GovcCommands.GET_VM_PATH.format(name=vm_name, datacenter=self.data_center)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return (
            output
            if output is None or output.strip() == ""
            else output.strip().split("\n")[1].split("Path:")[1].strip()
        )

    def power_off_vm(self, path):
        """
        power of the vm with specified path
        :param path: absolute path of the vm
        :returns:
        """
        cmd = GovcCommands.POWER_OFF_VM.format(vm_path=path)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip()

    def power_on_vm(self, vm_name):
        cmd = GovcCommands.POWER_ON_VM.format(data_center=self.data_center, vm_name=vm_name)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip()

    def set_vm_config(self, vm_name, cpu, memory):
        cmd = GovcCommands.SET_VM_CONFIG.format(data_center=self.data_center, vm_name=vm_name, cpu=cpu, memory=memory)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip()

    def delete_vm(self, vm_name, path):
        """
        delete the vm with specified name
        :param vm_name: name of the vm
        :param path: path of the vm
        :returns: return TRUE of exists else not
        """
        if not path:
            return None
        if self.get_vm_power_state(vm_name=vm_name) == VmPowerState.ON:
            self.power_off_vm(path)
        cmd = GovcCommands.DELETE_VM.format(vm_path=path)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip()

    def get_content_libraries(self, options=""):
        """
        list all content libraries in vcenter
        :param options: extra options
        :returns: all content libraries
        """
        cmd = GovcCommands.GET_CONTENT_LIBRARIES.format(options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def get_content_library_info(self, lib_name):
        """
        content library info with specified lib name from vcenter
        :param lib_name: name of the content libraries
        :returns: content library info
        """
        cmd = GovcCommands.GET_CONTENT_LIBRARY_INFO.format(name=lib_name)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def import_ova_to_content_lib(self, content_lib, local_file):
        """
        push the ova to specified content lib in vcenter
        :param content_lib: name of the content lib
        :param local_file: local file path
        :returns:
        """
        cmd = GovcCommands.IMPORT_OVA_TO_CONTENT_LIB.format(content_lib=content_lib, local_path=local_file)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")

    def create_subscribed_content_lib(self, url, content_lib_name, thumb_print):
        """
        create subscribed content library into vcenter, thumb_print needed for proxy environment deployment
        :param url: url from where content library needs to be subscribed.
        :param content_lib_name: name of the content lib to be created.
        :param thumb_print: thumbprint to use for proxy environment
        :returns:
        """
        if thumb_print:
            cmd = GovcCommands.CREATE_SUBSCRIBED_CONTENT_LIB_WITH_THUMB_PRINT.format(
                url=url,
                name=content_lib_name,
                thumb_print=thumb_print,
                data_store=self.data_store,
                datacenter=self.data_center,
            )
        else:
            cmd = GovcCommands.CREATE_SUBSCRIBED_CONTENT_LIB.format(
                url=url,
                name=content_lib_name,
                thumb_print=thumb_print,
                data_store=self.data_store,
                datacenter=self.data_center,
            )
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == "" else output.strip().split("\n")
