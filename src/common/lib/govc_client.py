import os
import json
from flask import current_app
from common.constants.constants import GovcCommands, VmPowerState
from common.util.base_cmd_helper import BaseCmdHelper


class GovcClient:
    def __init__(self, config, cmd_helper: BaseCmdHelper):
        self.cmd_runner = cmd_helper
        self.vcenter_ip = config['VC_IP']
        self.vcenter_username = config['VC_USER']
        self.vcenter_password = config['VC_PASSWORD']
        self.skip_verification = True
        self.set_env_vars()

    def set_env_vars(self):
        current_app.logger.info("Setting GOVC environment variables")
        os.environ["GOVC_URL"] = self.vcenter_ip
        os.environ["GOVC_USERNAME"] = self.vcenter_username
        os.environ["GOVC_PASSWORD"] = self.vcenter_password
        os.environ["GOVC_INSECURE"] = json.dumps(self.skip_verification)
        # current_app.logger.info(f"ENV variables: {os.environ}")

    def find_datacenter_by_name(self, datacenter_name, options=''):
        cmd = GovcCommands.FIND_DATACENTER_BY_NAME.format(dc_name=datacenter_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output.strip() if output and output.strip() != '' else None

    def find_clusters_by_name(self, cluster_name, options=''):
        cmd = GovcCommands.FIND_CLUSTERS_BY_NAME.format(clu_name=cluster_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split('\n')

    def find_resource_pools_by_name(self, pool_name, options=''):
        cmd = GovcCommands.FIND_RESOURCE_POOLS_BY_NAME.format(clu_name=pool_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split('\n')

    def delete_resource_pool(self, rp_path, options=''):
        cmd = GovcCommands.DELETE_RESOURCE_POOL.format(path=rp_path, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split('\n')

    def find_folders_by_name(self, folder_name, options=''):
        cmd = GovcCommands.FIND_FOLDERS_BY_NAME.format(folder_name=folder_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split('\n')

    def find_vms_by_name(self, vm_name, options=''):
        cmd = GovcCommands.FIND_VMS_BY_NAME.format(vm_name=vm_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split('\n')

    def find_networks_by_name(self, network_name, options=''):
        cmd = GovcCommands.FIND_NETWORKS_BY_NAME.format(network_name=network_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split('\n')

    def create_resource_pool(self, pool, options=''):
        """
        Create a resource pool if not exists and return the absolute path of the resource pool
        """
        existing_pools = self.find_resource_pools_by_name(pool.split('/')[-1])
        if not existing_pools or pool not in existing_pools:
            cmd = GovcCommands.CREATE_RESOURCE_POOL.format(pool=pool, options=options)
            self.cmd_runner.run_cmd(cmd)
        return pool

    def create_folder(self, folder, options=''):
        """
        Create a folder if not exists and return the absolute path of the folder
        """
        existing_folders = self.find_folders_by_name(folder.split('/')[-1])
        if not existing_folders or folder not in existing_folders:
            cmd = GovcCommands.CREATE_FOLDER.format(folder=folder, options=options)
            self.cmd_runner.run_cmd(cmd)
        return folder

    def check_network_exists(self, network_name, options=''):
        existing_networks = self.find_networks_by_name(network_name, options)
        return existing_networks and any(network_name == nw.split('/')[-1] for nw in existing_networks)

    def deploy_library_ova(self, location, name, options=''):
        cmd = GovcCommands.DEPLOY_LIBRARY_OVA.format(location=location, name=name, options=options)
        self.cmd_runner.run_cmd(cmd)

    def get_vm_ip(self, vm_name, datacenter_name, wait_time='5m'):
        if not self.find_vms_by_name(vm_name):
            return None
        options = ''
        if wait_time:
            options += f'-wait {wait_time}'
        cmd = GovcCommands.GET_VM_IP.format(name=vm_name, datacenter=datacenter_name, options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split('\n')

    def get_vm_power_state(self, vm_name):
        power_state_filter = "-runtime.powerState {state}"
        for v in VmPowerState.__members__.values():
            if self.find_vms_by_name(vm_name, options=power_state_filter.format(state=v.value)):
                return v
        raise ValueError(f"VM not found by name {vm_name}")

    def get_vm_path(self, vm_name, datacenter_name):
        if not self.find_vms_by_name(vm_name):
            return None
        cmd = GovcCommands.GET_VM_PATH.format(name=vm_name, datacenter=datacenter_name)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split("\n")[1].split("Path:")[1].strip()

    def power_off_vm(self, path):
        cmd = GovcCommands.POWER_OFF_VM.format(vm_path=path)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip()

    def delete_vm(self, vmname, path):
        if not path:
            return None
        if self.get_vm_power_state(vm_name=vmname) == VmPowerState.ON:
            self.power_off_vm(path)
        cmd = GovcCommands.DELETE_VM.format(vm_path=path)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip()

    def get_content_libraries(self, options=''):
        cmd = GovcCommands.GET_CONTENT_LIBRARIES.format(options=options)
        exit_code, output = self.cmd_runner.run_cmd_output(cmd)
        return output if output is None or output.strip() == '' else output.strip().split("\n")

