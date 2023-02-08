#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import json
import os
from pathlib import Path

from jinja2 import Template

from constants.constants import Paths, VmPowerState, ControllerLocation
from model.run_config import RunConfig, DeploymentPlatform
from model.spec import MasterSpec
from util.cmd_helper import CmdHelper as Cli
from util.file_helper import FileHelper
from util.logger_helper import LoggerHelper

logger = LoggerHelper.get_logger(Path(__file__).stem)


# https://cloudmaniac.net/ova-ovf-deployment-using-govc-cli/


def template_avi_govc_config(spec: MasterSpec):
    config_json_j2 = FileHelper.read_resource(Paths.GOVC_AVI_DEPLOY_CONFIG_J2)
    t = Template(config_json_j2)
    config_json_str = t.render(spec=spec)
    FileHelper.write_dict_to_file(Paths.GOVC_AVI_DEPLOY_CONFIG, json.loads(config_json_str))


def template_avi_se_govc_config(spec):
    config_json_j2 = FileHelper.read_resource(Paths.GOVC_AVI_SE_DEPLOY_CONFIG_J2)
    t = Template(config_json_j2)
    config_json_str = t.render(spec=spec)
    FileHelper.write_dict_to_file(Paths.GOVC_AVI_SE_DEPLOY_CONFIG, json.loads(config_json_str))
    return Paths.GOVC_AVI_SE_DEPLOY_CONFIG


def export_govc_env_vars(run_config: RunConfig):
    if run_config.deployment_platform == DeploymentPlatform.VMC:
        os.putenv("GOVC_URL", run_config.vmc.vc_mgmt_ip)
        os.putenv("GOVC_USERNAME", run_config.vmc.vc_cloud_user)
        os.putenv("GOVC_PASSWORD", run_config.vmc.vc_cloud_password)
    elif run_config.deployment_platform == DeploymentPlatform.VSPHERE:
        os.putenv("GOVC_URL", run_config.spec.vsphere.server)
        os.putenv("GOVC_USERNAME", run_config.spec.vsphere.username)
        os.putenv("GOVC_PASSWORD", Cli.decode_password(run_config.spec.vsphere.password))
    elif run_config.deployment_platform == DeploymentPlatform.VCF:
        pass
    os.putenv("GOVC_INSECURE", str("true"))


def deploy_avi_controller_ova(run_config: RunConfig):
    if not ControllerLocation.OVA_LOCATION:
        ova_path = os.path.join(run_config.root_dir, Paths.ALB_OVA_PATH)
        ova_path = ova_path if Path(ova_path).is_file() else run_config.spec.avi.ovaPath
    else:
        ova_path = ControllerLocation.OVA_LOCATION
    logger.info("Deploy ALB using govc and ova: %s", os.path.basename(ova_path))
    template_avi_govc_config(run_config.spec)
    export_govc_env_vars(run_config)
    Cli.execute_cmd("govc about")
    logger.info(f"check if vm: {run_config.spec.avi.vmName} exist")
    count = int(
        Cli.execute_cmd_and_get_output(f"govc find . -type m  -name '{run_config.spec.avi.vmName}' | wc -l").strip())
    if count != 0:
        logger.info(f"VM with name: {run_config.spec.avi.vmName} already exist")
        return
    import_ova(options=Paths.GOVC_AVI_DEPLOY_CONFIG, dc=run_config.spec.avi.deployment.datacenter,
               ds=run_config.spec.avi.deployment.datastore, folder=run_config.spec.avi.deployment.folder,
               res_pool=run_config.spec.avi.deployment.resourcePool, ova_file=ova_path, name=run_config.spec.avi.vmName,
               replace_existing=False)


def get_alb_ip_address(run_config: RunConfig):
    export_govc_env_vars(run_config)
    # todo: -a for all ip, use -a for validating if present
    logger.info("Getting alb ip from vc...")
    ip_cmd = f"""
    govc vm.ip "$(govc find . -type m  -name '{run_config.spec.avi.vmName}')"
    """
    return Cli.execute_cmd_and_get_output(ip_cmd)


def load_node_template(run_config: RunConfig):
    logger.info("Loading node template")
    if not run_config.spec.tkg.common.nodeOva:
        logger.info("No node ova provided so skipping node template loading")
        return
    export_govc_env_vars(run_config)
    os.putenv("GOVC_DATACENTER", run_config.spec.tkg.management.deployment.datacenter)
    vm_name = Path(run_config.spec.tkg.common.nodeOva).stem
    find_vm_cmd = f'govc find . -type m -name "{vm_name}"'
    # fill config
    config_json_j2 = FileHelper.read_resource(Paths.GOVC_OVA_DEPLOY_CONFIG_J2)
    t = Template(config_json_j2)
    config_json = t.render(vm_name=vm_name)
    FileHelper.write_dict_to_file(Paths.GOVC_OVA_DEPLOY_CONFIG, json.loads(config_json))
    deploy_ova_cmd = f"""govc import.ova \\
        -options={Paths.GOVC_OVA_DEPLOY_CONFIG} \\
        -ds={run_config.spec.tkg.management.deployment.datastore} \\
        {run_config.spec.tkg.common.nodeOva}"""
    vms = Cli.execute_cmd_and_get_output(find_vm_cmd)
    if len(vms.strip()) == 0:
        Cli.execute_cmd(deploy_ova_cmd)


def find_vms(folder, vm_name):
    find_vm_cmd = f'govc find {folder or "."} -type m -name "{vm_name}"'
    vms = Cli.execute_cmd_and_get_output(find_vm_cmd).strip()
    if len(vms) == 0:
        return False
    return vms.split("\n")


def teardown_env(spec: MasterSpec):
    export_govc_env_vars(spec)
    logger.info("Deleting ALB")
    delete_vm(find_vms(spec.avi.deployment.folder, spec.avi.vmName))
    delete_vm(find_vms(f"{spec.avi.deployment.datacenter}/vm/AviSeFolder", "Avi-se-*"))
    logger.info("Deleting tkg clusters")
    delete_vm(find_vms(spec.tkg.management.deployment.folder, f"{spec.tkg.management.cluster.name}*"))
    delete_vm(find_vms(spec.tkg.sharedService.deployment.folder, f"{spec.tkg.sharedService.cluster.name}*"))
    for wl in spec.tkg.workloadClusters:
        delete_vm(find_vms(wl.deployment.folder, f"{wl.cluster.name}*"))


def delete_vm(vm_paths):
    if not vm_paths:
        return
    logger.info(f"Deleting vms {vm_paths}")
    for vm_path in vm_paths:
        power_off_cmd = f"govc vm.power -off -force {vm_path}"
        delete_cmd = f"govc vm.destroy {vm_path}"
        Cli.execute_cmd_and_get_output(power_off_cmd)
        Cli.execute_cmd_and_get_output(delete_cmd)


def find_vm_by_name(name, is_template=False):
    logger.info(f"Check if VM exists by name: [{name}]")
    cmd = f"govc find . -type m -config.template {is_template} -name {name}"
    output = Cli.execute_cmd_and_get_output(cmd)
    if len(output) == 0:
        return None
    return output.strip().split('\n')


def import_ova(options, dc, ds, folder, res_pool, ova_file, name, template=False, replace_existing=True):
    vm = find_vm_by_name(name, is_template=template)
    if replace_existing and vm:
        delete_vm(vm)
    elif vm:
        logger.info(f"VM exists by name {name}: {vm}. Skipping import")
        return vm
    logger.info(f"Importing OVA by name: {name}")
    cmd = f"govc import.ova -options {options} -dc {dc} -ds {ds} -folder {folder} -pool {res_pool} {ova_file}"
    Cli.execute_cmd_and_get_output(cmd)
    if not find_vm_by_name(name, is_template=template):
        msg = f"Failed to import OVA. No VM found by name: {name}"
        logger.error(msg)
        raise Exception(msg)


def change_vm_network(vm, network_list):
    for index, target in enumerate(network_list):
        cmd = f"govc vm.network.change -vm {vm} -net {target} ethernet-{index}"
        Cli.execute_cmd_and_get_output(cmd)


def connect_networks(vm, network_list):
    cmd = f"govc device.connect -vm {vm} {' '.join(network_list)}"
    Cli.execute_cmd_and_get_output(cmd)


def change_vms_power_state(vm_list, power_state: VmPowerState):
    cmd = f"govc vm.power -{power_state}=true {' '.join(vm_list)}"
    Cli.execute_cmd_and_get_output(cmd)


def wait_for_vm_to_get_ip(vm, wait_time="5m"):
    cmd = f"govc vm.ip -wait {wait_time} {vm}"
    ip = Cli.execute_cmd_and_get_output(cmd)
    if ip and ip != '':
        return ip
    raise ValueError(f"Failed to get IP for vm [{vm}] after waiting for {wait_time}. {ip}")


def update_vm_cpu_memory(name, cpus, memory):
    cmd = f"govc vm.change -vm {name} -c={cpus} -m={memory}"
    Cli.execute_cmd_and_get_output(cmd)


def get_vm_power_state(name):
    logger.info(f"Getting power state for VM: [{name}]")
    cmd = f'govc vm.info {name} | grep "Power state"'
    res = Cli.execute_cmd_and_get_output(cmd)
    return VmPowerState.ON if res and "poweredOn" in res else VmPowerState.OFF


def get_vm_mac_addresses(name):
    cmd = f"govc device.info -vm {name} -json 'ethernet-*'"
    res = Cli.execute_cmd_and_get_output(cmd)
    if not res:
        raise ValueError(f"Failed to get mac addresses for vm [{name}]. {res}")
    device_mac_addresses = dict()
    try:
        devices = json.loads(res)["Devices"]
        for device in devices:
            device_mac_addresses[device["Name"]] = device["MacAddress"]
        return device_mac_addresses
    except Exception as ex:
        logger.error(f"Failed to get mac addresses for vm [{name}]. {res}")
        raise ex
