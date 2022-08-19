#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import subprocess

from util.base_cmd_helper import BaseCmdHelper


class LocalCmdHelper(BaseCmdHelper):
    def run_cmd(self, cmd: str, ignore_errors=False) -> int:

        command = cmd.split()
        op = subprocess.run(command, check=not ignore_errors)

        return op.returncode

    def run_cmd_output(self, cmd: str, ignore_errors=False) -> tuple:

        command = cmd.split()
        op = subprocess.run(command, check=not ignore_errors, capture_output=True)

        return op.returncode, op.stdout.decode()
