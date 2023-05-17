#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os
from constants.constants import Paths
from lib.tkg_cli_client import TkgCliClient
from util.logger_helper import LoggerHelper
from util.cmd_runner import RunCmd
import yaml

logger = LoggerHelper.get_logger(name='ra_day2_operation_workflow')

class RaDay2WorkflowCheck:
    """
    Though the first layer of day2 operations selected are done by day2_precheck tasks, perform
    check that only one day2 operation is selected.

    """

    def __init__(self, run_config):

        self.run_config = run_config
        self.day2_data_dict = {}
        self.update_dict = {}
        self.resize_dict = {}
        self.scale_dict = {}
        self.tanzu_client = TkgCliClient()
        self.rcmd = RunCmd()

    def validate_day2_ops(self):

        """
            Check only one type of operation is enabled for day2 operation.
        :return:
        """

        self.get_day2_desired_state_operation()
        day2_check = sum([self.update_dict['execute'], self.resize_dict['execute'],
                          self.scale_dict['execute']])
        if str(day2_check) != "1":
            logger.error("Invalid day2 operations selected. Only one day2 oepration supported")
            raise Exception(f"Update Execute: {self.update_dict['execute']}\n"
                            f"Resize Execute: {self.resize_dict['execute']}\n",
                            f"Scale Execute: {self.scale_dict['execute']}")

    def get_day2_desired_state_operation(self):

        """
        Get the day 2 desired state file.
        """

        day2_desired_file = os.path.join(self.run_config.root_dir, Paths.DAY2_PATH)
        with open(day2_desired_file) as stream:
            try:
                self.day2_data_dict = (yaml.safe_load(stream))
            except yaml.YAMLError as exc:
                logger.error(f"Error Encountered parsing yaml error: {exc}")
        for k, v in (self.day2_data_dict.items()):
            logger.info(f"-=-=-=-=-=-=-=-=={k, v}-=-=-=-=")
            if 'update' in k:
                self.update_dict = v
            if 'resize' in k:
                self.resize_dict = v
            if 'scale' in k:
                self.scale_dict = v
        logger.info(f"update dict: {self.update_dict}")



