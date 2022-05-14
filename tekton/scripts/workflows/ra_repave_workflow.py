#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import random
import string
import json
import time
from constants.constants import Paths, RegexPattern, KubectlCommands
from lib.tkg_cli_client import TkgCliClient
from lib.kubectl_client import KubectlClient
from model.run_config import RunConfig, RepaveConfig
from util.logger_helper import LoggerHelper
import traceback
from util.common_utils import checkenv
from util.cmd_runner import RunCmd
from util.ShellHelper import runShellCommandAndReturnOutputAsList, verifyPodsAreRunning,\
    grabKubectlCommand, grabPipeOutput
import ruamel.yaml
from ruamel.yaml.comments import CommentedMap

logger = LoggerHelper.get_logger(name='repave_workflow')

class RepaveWorkflow:
    def __init__(self, run_config: RunConfig, repave_config: RepaveConfig):
        self.repave_config = repave_config
        self.run_config = run_config
        jsonpath = os.path.join(self.run_config.root_dir, Paths.MASTER_SPEC_PATH)
        self.tanzu_client = TkgCliClient()
        self.kube_client = KubectlClient()
        self.rcmd = RunCmd()
        self.workername = ''
        self.new_worker_name = ''
        self.cpu_change = ''
        self.memory_change = ''

        with open(jsonpath) as f:
            self.jsonspec = json.load(f)
        try:
            check_env_output = checkenv(self.jsonspec)
            print("check_env_output: {}".format(check_env_output))
            if check_env_output is None:
                msg = "Failed to connect to VC. Possible connection to VC is not available or " \
                      "incorrect spec provided."
                logger.error(msg)
                sys.exit(-1)
        except Exception:
            logger.error(traceback.format_exc())

        logger.debug("Get tanzu login for entire flow")
        self.management_cluster = self.jsonspec['tkgComponentSpec']['tkgMgmtComponents'][
            'tkgMgmtClusterName']
        self.tanzu_client.login(cluster_name=self.management_cluster)
        self.repavedetails = self.repave_config.repave_details.repaveinfo

    def replace_md(self, filedump):
        """
        1. replace spec-spec-name to worker name
        :param filedump:
        :return: True, yaml file on Success
                None on failure
        """
        try:
            current_cluster_name = filedump['spec']['template']['spec']['infrastructureRef']['name']
            replace_new_name = self.new_worker_name
            filedump['spec']['template']['spec']['infrastructureRef']['name'] = replace_new_name
            logger.info(f"Replacing md {current_cluster_name} with {replace_new_name}")
            replaced_values = json.dumps(filedump)

            def block_style(base):
                """set all mapping and sequneces to block-style"""
                if isinstance(base, CommentedMap):
                    for k in base:
                        block_style(base[k])
                    base.fa.set_block_style()
                if isinstance(base, list):
                    for item in base:
                        block_style(item)
                    base.fa.set_block_style()
                return base

            data = ruamel.yaml.round_trip_load(replaced_values)
            block_style(data)
            yaml_converted = ruamel.yaml.round_trip_dump(data)
            target_file = '/tmp/modified-md.yaml'
            with open(target_file, 'w') as fw:
                fw.write(yaml_converted)
            return True, target_file
        except Exception:
            logger.error("Error Encountered: {}".format(traceback))

    def replace_values_cpu_mem(self, filedump, skip_cpu, skip_mem):
        """
        1. Replace worker name for either cpu/mem or both replacement
        2. if cpu/memory, replace as required
        3. output formatted to yaml
        :param filedump:
        :param skip_cpu:
        :param skip_mem:
        :return: True, yamlfile on Success
                 None on Failure
        """
        try:
            current_worker_name = filedump['metadata']['name']
            current_cpu_count = filedump['spec']['template']['spec']['numCPUs']
            current_memory_size = filedump['spec']['template']['spec']['memoryMiB']

            # replace worker name

            generated_worker_name = ''.join(
                random.choice(string.ascii_lowercase + string.digits) for _ in range(5))
            mod_worker_name = f'{current_worker_name}-{generated_worker_name}'
            self.new_worker_name = mod_worker_name
            filedump['metadata']['name'] = mod_worker_name
            logger.debug(
                f'Current worker: {current_worker_name} \t Renamed: {mod_worker_name}')
            # check cpu / mem
            if skip_cpu:
                logger.debug(f'Current memorysize: {current_memory_size} \t Resized:'
                             f' {self.memory_change}')
                filedump['spec']['template']['spec']['memoryMiB'] = int(self.memory_change)
            elif skip_mem:
                logger.debug(f'Current CPUCount: {current_cpu_count} \t Resized: {self.cpu_change}')
                filedump['spec']['template']['spec']['numCPUs'] = int(self.cpu_change)
            else:
                logger.debug(f'Current CPUCount: {current_cpu_count} \t Resized: {self.cpu_change}')
                filedump['spec']['template']['spec']['memoryMiB'] = int(self.memory_change)
                filedump['spec']['template']['spec']['numCPUs'] = int(self.cpu_change)

            replaced_values = json.dumps(filedump)

            def block_style(base):
                """set all mapping and sequneces to block-style"""
                if isinstance(base, CommentedMap):
                    for k in base:
                        block_style(base[k])
                    base.fa.set_block_style()
                if isinstance(base, list):
                    for item in base:
                        block_style(item)
                    base.fa.set_block_style()
                return base
            data = ruamel.yaml.round_trip_load(replaced_values)
            block_style(data)
            yaml_converted = ruamel.yaml.round_trip_dump(data)
            target_file = '/tmp/modified.yaml'
            with open(target_file, 'w') as fw:
                fw.write(yaml_converted)
            return True, target_file

        except Exception:
            logger.error("Error Encountered:{}".format(traceback.format_exc()))
            return None

    def check_state_md(self, target_deployment):

        md_running = ["kubectl", "get", "machines"]
        md_grep = ["grep", target_deployment]
        count_md = 0
        command_status_md = grabPipeOutput(md_running, md_grep)
        found = False
        if verifyPodsAreRunning(target_deployment, command_status_md[0], RegexPattern.RUNNING):
            found = True

        while not verifyPodsAreRunning(target_deployment, command_status_md[0],
                                       RegexPattern.RUNNING) and count_md < 20:
            command_status = grabPipeOutput(md_running, md_grep)
            if verifyPodsAreRunning(target_deployment, command_status[0], RegexPattern.RUNNING):
                return True
            count_md = count_md + 1
            time.sleep(30)
            logger.info("Waited for  " + str(count_md * 30) + "s, retrying.")
        if not found:
            logger.error("Machine deployments are not running on waiting " + str(count_md * 30))
            return None

    def trigger_repave(self, skip_cpu, skip_mem):
        
        """
        1. switch to mgmt context
        2. get the template of the cluster to separate yml file
        3. change cpu and memory based on skip params
        4. remove last applied in yml file
        5. rename clustername to cluster-repaved-random_number2
        6. k apply changed file
        7. get machinedeployment of clustername to separate dep.yml file
        8. change cluster name from 5
        9. k apply dep yml file

        :param skip_cpu:
        :param skip_mem:

        :return: True on success
                None on failure
        """

        try:
            # switch to mgmt context
            commands = ["tanzu", "management-cluster", "kubeconfig", "get", self.management_cluster,
                        "--admin"]
            kube_context_cmd = grabKubectlCommand(commands, RegexPattern.SWITCH_CONTEXT_KUBECTL)
            if kube_context_cmd is None:
                logger.error("Failed to get switch to management cluster context command")                
                return None
            list_switch_cmd = str(kube_context_cmd).split(" ")
            status = runShellCommandAndReturnOutputAsList(list_switch_cmd)
            if status[1] != 0:
                logger.error(
                    "Failed to get switch to management cluster context " + str(status[0]))
                return None

            # get the template of the cluster to separate yml file
            # kubectl get VsphereMachineTemplate tekton-shared-cluster-worker -o yaml
            k_template_cmd_out = self.kube_client.get_vsphere_template_json(self.workername)
            if k_template_cmd_out is None:
                logger.error("Unable to get template of workernode. Bail out")
                return None
            target_file = '/tmp/modfile.json'
            with open(target_file, 'w') as fw:
                fw.write(k_template_cmd_out)

            with open(target_file, 'r') as f:
                filedump = json.load(f)

            status, config_file = self.replace_values_cpu_mem(filedump, skip_cpu, skip_mem)
            if status is None:
                logger.error("Error Encountered in replacing values...")
                return None

            # apply the modified file
            apply_out = self.rcmd.run_cmd_output(KubectlCommands.APPLY.format(config_file=
                                                                              config_file))
            logger.info("Applied Out: {}".format(apply_out))
            # get machinedeployment new_worker_name
            target_deployment = self.workername.replace('-worker', '-md-0')
            k_md_cmd_out = self.kube_client.get_machinedeployment_json(target_deployment)
            if k_md_cmd_out is None:
                logger.error("Unable to get template of workernode. Bail out")
                return None
            md_target_file = '/tmp/modfile-md.json'
            with open(md_target_file, 'w') as fw:
                fw.write(k_md_cmd_out)

            with open(md_target_file, 'r') as f:
                filedump = json.load(f)

            status, config_file = self.replace_md(filedump)
            if status is None:
                logger.error("Error Encountered in replacing values...")
                return None
            # apply the modified file
            apply_out = self.rcmd.run_cmd_output(KubectlCommands.APPLY.format(config_file=
                                                                              config_file))
            logger.info("Apply Out: {}".format(apply_out))
            # check for all running state from Provisioning state
            status_md = self.check_state_md(target_deployment)
            if status_md is None:
                logger.error("Machine deployments are not running on waiting")
                raise Exception("Machine deployments are not running on waiting")
            else:
                logger.info("Completed repave operation for shared services cluster...")
                return True

        except Exception:
            logger.error(traceback.format_exc())
            return None
        pass

    def execute_repave(self):
        try:
            # precheck for right entries in scale.yml to identify the cluster
            # to be scaled and the controlnode and worker node to be scaled
            logger.info("====Perform precheck======")
            if not self.repavedetails.execute:
                logger.info("Repave operation is not enabled.")
                d = {
                    "responseType": "SUCCESS",
                    "msg": "Repave operation is not enabled",
                    "ERROR_CODE": 200
                }
                return json.dumps(d), 200

            # Check if mgmt needs scaling
            if self.repavedetails.mgmt.execute_repave:
                logger.info("Repave operation is not currently supported for management."
                            "Proceed to next enabled workload cluster")
            # Proceed for next cluster
            # Check if shared_services needs scaling
            if not self.repavedetails.shared_services.execute_repave:
                logger.info("Scale operation is not enabled for shared cluster.")
            else:
                logger.info("Starting repaving of Shared Service cluster")
                self.workername = self.repavedetails.shared_services.workername

                # TODO: kubectl check applied memory/cpu changes to existing template
                # even if they are equal to the existing configuration.
                # Implement precheck by getting template file and
                # parsing the cpu/memory before applying.

                # Continue on applying cpu/memory changes

                skip_cpu = False
                skip_mem = False
                self.cpu_change = self.repavedetails.shared_services.repave_cpu
                self.memory_change = self.repavedetails.shared_services.repave_memory_mb

                if not self.cpu_change:
                    skip_cpu = True
                if not self.memory_change:
                    skip_mem = True
                if skip_cpu and skip_mem:
                    logger.error("Both CPU/Memory spec are not specified.")
                    raise Exception('Specify either resources')

                shared_operation = self.trigger_repave(skip_cpu, skip_mem)
                if shared_operation is None:
                    raise Exception("Error encountered during resize operation on shared cluster")
                else:
                    logger.info("Completed shared services resize operation...")

            if not self.repavedetails.workload_clusters.execute_repave:
                logger.info("Scale operation is not enabled for workload_clusters.")
            else:
                logger.info("Starting repaving of Workload cluster")
                self.workername = self.repavedetails.workload_clusters.workername
                # Continue on applying cpu/memory changes
                skip_cpu = False
                skip_mem = False
                self.cpu_change = self.repavedetails.workload_clusters.repave_cpu
                self.memory_change = self.repavedetails.workload_clusters.repave_memory_mb
                if not self.cpu_change:
                    skip_cpu = True
                if not self.memory_change:
                    skip_mem = True
                if skip_cpu and skip_mem:
                    logger.error("Both CPU/Memory spec are not specified.")
                    raise Exception('Specify either resources')
                shared_operation = self.trigger_repave(skip_cpu, skip_mem)
                if shared_operation is None:
                    raise Exception("Error encountered during resize operation on workload cluster")
                else:
                    logger.info("Completed workload_clusters resize operation...")

            logger.info("All Resize operations have been completed..")
            d = {
                "responseType": "SUCCESS",
                "msg": "Resize operation completed",
                "ERROR_CODE": 200
            }
            return json.dumps(d), 200
        except Exception:
            logger.error("Error Encountered: {}".format(traceback.format_exc()))

