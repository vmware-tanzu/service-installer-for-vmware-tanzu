#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path

import yaml

from constants.constants import (TKG_EXTENSIONS_ROOT, Paths, PrepareEnvCommands, TanzuToolsCommands, TKGCommands)
from model.desired_state import DesiredState
from model.spec import Bootstrap, MasterSpec
from model.status import State
from util.cmd_helper import CmdHelper
from util.file_helper import FileHelper
from util.govc_helper import load_node_template
from util.logger_helper import LoggerHelper
from util.ssh_helper import SshHelper
from util.tanzu_utils import TanzuUtils

logger = LoggerHelper.get_logger(Path(__file__).stem)


class EnvValidator:
    def __init__(self, root_dir) -> None:
        self.root_dir = root_dir
        self.spec: MasterSpec = FileHelper.load_spec(os.path.join(self.root_dir, Paths.MASTER_SPEC_PATH))
        self.bootstrap: Bootstrap = self.spec.bootstrap
        self.desired_state: DesiredState = FileHelper.load_desired_state(
            os.path.join(self.root_dir, Paths.DESIRED_STATE_PATH)
        )
        self.support_matrix = yaml.safe_load(FileHelper.read_resource(Paths.SUPPORT_MATRIX_FILE))
        self.version_matrix = self.support_matrix["matrix"][self.desired_state.version.tkg]
        self.state: State = FileHelper.load_state(os.path.join(self.root_dir, Paths.STATE_PATH))

    def validate_all(self):
        with SshHelper(self.bootstrap.server, self.bootstrap.username,
                       CmdHelper.decode_password(self.bootstrap.password),
                       self.spec.onDocker) as ssh:
            self.validate_tanzu_version(ssh)
            self.validate_tools(ssh)
            # self.validate_extension_dir(ssh)
            if self.spec.onDocker:
                ssh.run_cmd(cmd=PrepareEnvCommands.VALIDATE_DOCKER_RUNNING)

    def validate_tanzu_version(self, ssh):
        code, version_raw = ssh.run_cmd_output(TKGCommands.VERSION)
        version = [line for line in version_raw.split("\n") if "version" in line][0]
        if not any(k in version for k in self.support_matrix["matrix"].keys()):
            raise EnvironmentError(f"Tanzu cli version unsupported. \n{version}")

        if self.desired_state.version.tkg not in version:
            raise ValueError(
                f"Desired state version({self.desired_state.version.tkg}) and tanzu cli version  does not match"
            )

    def validate_tools(self, ssh: SshHelper):
        for tool in TanzuToolsCommands:
            self.get_tool_version(ssh, tool)

    def validate_extension_dir(self, ssh: SshHelper):
        versions = [self.desired_state.version.tkg]
        if self.state.shared_services.deployed:
            versions.append(self.state.shared_services.version)
        for version in versions:
            if version >= "1.4.0":
                code, ls_files_raw = ssh.run_cmd_output(f"ls /tanzu/packages")
            else:
                code, ls_files_raw = ssh.run_cmd_output(f"ls {TKG_EXTENSIONS_ROOT[version]}")
            if code != 0:
                raise EnvironmentError(f"Error while listing extension folder - {TKG_EXTENSIONS_ROOT[version]}")

    def get_tool_version(self, ssh: SshHelper, tool: dict):
        cmd = tool["version"]
        binary = tool["matrix-key"]
        code, version_raw = ssh.run_cmd_output(cmd)
        if code == 127:
            raise EnvironmentError(
                f"{binary} command not found, possible error: /usr/local/bin is not added to env path or {binary} not installed"
            )
        if code != 0:
            raise EnvironmentError(f"Error while fetching {binary} version")

        version = str(version_raw).removeprefix(tool["prefix"]).strip().split("\n")[0].strip()

        if version != self.version_matrix[binary]:
            logger.warn(f"Version Mismatch for {binary}")
        return version

    def prepare_env(self):
        logger.info("Preparing environment")
        if self.spec.onDocker:
            self.prepare_docker_env()
        else:
            self.prepare_host_env()
        load_node_template(self.spec)

    def prepare_host_env(self):
        tkg_version = self.desired_state.version.tkg
        with SshHelper(self.bootstrap.server, self.bootstrap.username,
                       CmdHelper.decode_password(self.bootstrap.password),
                       self.spec.onDocker) as ssh:
            ssh.run_cmd(PrepareEnvCommands.CLEANUP_ALL)
            ssh.copy_file(
                Paths.LOCAL_TKG_BINARY_PATH.format(root_dir=self.root_dir),
                f"{PrepareEnvCommands.ROOT_DIR}/tanzu-cli-bundle-linux-amd64.tar",
            )
            ssh.copy_file(
                Paths.LOCAL_KUBECTL_BINARY_PATH.format(root_dir=self.root_dir, version=self.version_matrix["kubectl"]),
                Paths.REMOTE_KUBECTL_BINARY_PATH.format(root_dir=PrepareEnvCommands.ROOT_DIR, version=self.version_matrix["kubectl"])
            )
            ssh.copy_file(
                Paths.LOCAL_TMC_BINARY_PATH.format(root_dir=self.root_dir), Paths.REMOTE_TMC_BINARY_PATH.format(root_dir=PrepareEnvCommands.ROOT_DIR))

            # Following lines are commented as we're not using the tanzu-binary.tar.gz
            # ssh.run_cmd(PrepareEnvCommands.UNTAR_BINARY.format(version=tkg_version))
            # if self.state.sharedService.deployed:
            #     if tkg_version >= "1.4.0":
            #         ssh.run_cmd(PrepareEnvCommands.COPY_PKG.format(version=self.state.sharedService.version))
            #         ssh.run_cmd(PrepareEnvCommands.INSTALL_PKG.format(version=self.state.sharedService.version))
            #     else:
            #         ssh.run_cmd(PrepareEnvCommands.COPY_EXT.format(version=self.state.sharedService.version))
            #         ssh.run_cmd(PrepareEnvCommands.INSTALL_EXT.format(version=self.state.sharedService.version))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_TANZU.format(version=tkg_version))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_KUBECTL.format(version=self.version_matrix["kubectl"]))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_PLUGIN)
            ssh.run_cmd(PrepareEnvCommands.INSTALL_YQ.format(version=self.version_matrix["yq"]))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_YTT.format(version=self.version_matrix["ytt"]))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_KAPP.format(version=self.version_matrix["kapp"]))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_KBLD.format(version=self.version_matrix["kbld"]))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_IMGPKG.format(version=self.version_matrix["imgpkg"]))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_JQ.format(version=self.version_matrix["jq"]))
            ssh.run_cmd(PrepareEnvCommands.INSTALL_TMC)
            # if tkg_version >= "1.4.0":
            #     ssh.run_cmd(PrepareEnvCommands.INSTALL_PKG.format(version=tkg_version))
            # else:
            #     ssh.run_cmd(PrepareEnvCommands.INSTALL_EXT.format(version=tkg_version))
            ssh.run_cmd(PrepareEnvCommands.CLEANUP_TANZU_DIR)
        if (
                self.state.shared_services.deployed
                or self.state.mgmt.deployed
                or any(wl.deployed for wl in self.state.workload_clusters)
        ):
            logger.info("Found existing deployment in state repo.")
            logger.info("Pulling kube-config and tanzu config to bootstrap machine.")
            TanzuUtils(self.root_dir).push_config(logger)
        logger.info("Completed environment cleanup and setup.")

    def prepare_docker_env(self):
        tkg_version = self.desired_state.version.tkg
        with SshHelper(self.bootstrap.server, self.bootstrap.username,
                       CmdHelper.decode_password(self.bootstrap.password),
                       self.spec.onDocker) as ssh:
            ssh.run_cmd(cmd=PrepareEnvCommands.DOCKER_RUN_CMD.format(image_name=self.spec.imageName,
                                                                     tkg_version=tkg_version))
            logger.info("docker container started")
            ssh.run_cmd(cmd=PrepareEnvCommands.CLEANUP_KIND_CONTAINERS)
