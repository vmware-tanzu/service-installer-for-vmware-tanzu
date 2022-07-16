#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import traceback
import logging
from pathlib import Path
import shutil
import subprocess
import shlex
from util.logger_helper import LoggerHelper

__author__ = 'smuthukumar'

logger = LoggerHelper.get_logger(Path(__file__).stem)
logging.getLogger("paramiko").setLevel(logging.WARNING)


"""
ToDO:
 1. for local run command with no output
 2. for local run command with output
 3. for local run long running command in background
 4. for file copy 
"""

class RunCmd:

    def run_cmd_only(self, cmd: str, ignore_errors=False, msg=None):
        logger.debug(f"Running cmd: {cmd}")
        try:
            subprocess.call(shlex.split(cmd), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            logger.error(f"Error: {traceback.format_exc()}\n Error executing: {cmd}")

    def run_cmd_output(self, cmd: str):

        logger.debug(f"Running cmd: {cmd}")
        try:
            cmd_out = subprocess.check_output(cmd, shell=True, encoding='UTF-8')
            return cmd_out
        except Exception:
            logger.error(f"Error: {traceback.format_exc()}")
            return None

    def local_file_copy(self, srcfile, destfile, follow_symlinks=False):
        logger.debug(f"Copying file {srcfile} to {destfile}")
        try:
            shutil.copyfile(srcfile, destfile, follow_symlinks=follow_symlinks)
        except FileNotFoundError:
            logger.error(f"Error: {traceback.format_exc ()}")

    def runShellCommandAndReturnOutputAsList(self, fin):
        try:
            proc = subprocess.Popen(
                fin,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE
            )

            output = proc.communicate()[0]
            if output.decode("utf-8").lower().__contains__("error"):
                returnCode = 1
            else:
                returnCode = 0
        except subprocess.CalledProcessError as e:
            returnCode = 1
            output = e.output
        return output.decode("utf-8").rstrip("\n\r").replace("\x1b[0m", "").replace("\x1b[1m",
                                                                                    "").split(
            "\n"), returnCode



