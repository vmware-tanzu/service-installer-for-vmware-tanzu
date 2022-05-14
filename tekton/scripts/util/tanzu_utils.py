#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from pathlib import Path

from constants.constants import Paths
from model.desired_state import DesiredState
from model.spec import Bootstrap, MasterSpec
from model.status import State
from util.file_helper import FileHelper
from util.logger_helper import LoggerHelper
from util.cmd_runner import RunCmd

logger = LoggerHelper.get_logger(Path(__file__).stem)

class TanzuUtils:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.spec: MasterSpec = FileHelper.load_spec(os.path.join(self.root_dir,
                                                                  Paths.MASTER_SPEC_PATH))
        self.bootstrap: Bootstrap = self.spec.bootstrap
        self.desired_state: DesiredState = FileHelper.load_desired_state(
            os.path.join(self.root_dir, Paths.DESIRED_STATE_PATH)
        )
        self.state: State = FileHelper.load_state(os.path.join(self.root_dir, Paths.STATE_PATH))
        self.repo_kube_config = os.path.join(self.root_dir, Paths.REPO_KUBE_CONFIG)
        self.repo_kube_tkg_config = os.path.join(self.root_dir, Paths.REPO_KUBE_TKG_CONFIG)
        self.repo_tanzu_config = os.path.join(self.root_dir, Paths.REPO_TANZU_CONFIG)
        self.repo_tanzu_config_new = os.path.join(self.root_dir, Paths.REPO_TANZU_CONFIG_NEW)
        self.runcmd = RunCmd()
        FileHelper.make_parent_dirs(self.repo_kube_config)
        FileHelper.make_parent_dirs(self.repo_kube_tkg_config)
        FileHelper.make_parent_dirs(self.repo_tanzu_config)
        FileHelper.make_parent_dirs(self.repo_tanzu_config_new)

    def pull_config(self):

        # with SshHelper(self.bootstrap.server,
        # self.bootstrap.username, CmdHelper.decode_
        # password(self.bootstrap.password), self.spec.onDocker) as ssh:
        self.pull_kube_config()
        self.pull_kube_tkg_config()
        self.pull_tanzu_config()

    def pull_kube_config(self):
        remote_kube_config = Paths.REMOTE_KUBE_CONFIG
        try:
            self.runcmd.run_cmd_only(f"ls {remote_kube_config}")
        except Exception as ex:
            return
        self.runcmd.local_file_copy(remote_kube_config, self.repo_kube_config)
        # ssh.copy_file_from_remote(remote_kube_config, self.repo_kube_config)

    def pull_kube_tkg_config(self):
        remote_kube_config = Paths.REMOTE_KUBE_TKG_CONFIG
        try:
            self.runcmd.run_cmd_only(f"ls {remote_kube_config}")
        except Exception as ex:
            return
        self.runcmd.local_file_copy(remote_kube_config, self.repo_kube_tkg_config)

    def pull_tanzu_config(self):
        if self.desired_state.version.tkg >= '1.4.0':
            remote_tanzu_config_new = Paths.REMOTE_TANZU_CONFIG_NEW
            try:
                self.runcmd.run_cmd_only(f"ls {remote_tanzu_config_new}")
                # ssh.run_cmd(f"ls {remote_tanzu_config_new}")
            except Exception as ex:
                return
            self.runcmd.local_file_copy(remote_tanzu_config_new, self.repo_tanzu_config_new)
            # ssh.copy_file_from_remote(remote_tanzu_config_new, self.repo_tanzu_config_new)
        else:
            remote_tanzu_config = Paths.REMOTE_TANZU_CONFIG
            try:
                self.runcmd.run_cmd_only(f"ls {remote_tanzu_config}")
                # ssh.run_cmd(f"ls {remote_tanzu_config}")
            except Exception as ex:
                return
            self.runcmd.local_file_copy(remote_tanzu_config, self.repo_tanzu_config)
            # ssh.copy_file_from_remote(remote_tanzu_config, self.repo_tanzu_config)

    def push_config(self, logger):
        logger.info("Copying config files")
        self.runcmd.run_cmd_only(f"mkdir -p /root/.kube /root/.kube-tkg")
        # with SshHelper(self.bootstrap.server, self.bootstrap.username, CmdHelper.decode_password(self.bootstrap.password), self.spec.onDocker) as ssh:
        # subprocess.run(f"mkdir -p {}/root/.kube /root/.kube-tkg")
        #root_dir = "/workspace/shared-data/kubeconfig"
        # subprocess.run(f"mkdir -p {self.root_dir/} /root/.kube /root/.kube-tkg")
        # cp_cmd = "cp {} {}".format(self.repo_kube_tkg_config, Paths.REMOTE_KUBE_TKG_CONFIG)
        self.runcmd.local_file_copy(self.repo_kube_tkg_config, Paths.REMOTE_KUBE_TKG_CONFIG)
        self.runcmd.local_file_copy(self.repo_kube_config, Paths.REMOTE_KUBE_CONFIG)
        # cp_cmd = "cp {} {}".format(self.repo_kube_config, Paths.REMOTE_KUBE_CONFIG)
        # subprocess.run(cp_cmd)
        if self.desired_state.version.tkg >= '1.4.0' and not self.state.shared_services.upgradedFrom:
            # cp_cmd = "cp {} {}".format(self.repo_tanzu_config_new, Paths.REMOTE_TANZU_CONFIG_NEW)
            self.runcmd.local_file_copy(self.repo_tanzu_config_new, Paths.REMOTE_TANZU_CONFIG_NEW)
            # subprocess.run(cp_cmd)
            # ssh.copy_file(self.repo_tanzu_config_new, Paths.REMOTE_TANZU_CONFIG_NEW)
        # elif self.desired_state.version.tkg == '1.4.0':
        #     ssh.copy_file(self.repo_tanzu_config, Paths.REMOTE_TANZU_CONFIG_NEW)
        # else:
        #     # For versions 1.3.0 and 1.3.1
        #     ssh.copy_file(self.repo_tanzu_config, Paths.REMOTE_TANZU_CONFIG)

    def push_config_without_errors(self, logger):
        try:
            self.push_config(logger)
        except Exception as e:
            logger.error("Unable to push config to remote containers")
