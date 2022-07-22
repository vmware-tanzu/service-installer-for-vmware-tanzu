#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import base64
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from util.logger_helper import LoggerHelper, log_debug

logger = LoggerHelper.get_logger(Path(__file__).stem)


def timer(func):
    def inner(*args, **kwargs):
        start = datetime.now()
        logger.info("Execution of %s Starts at: %s", func.__name__, start)
        result = func(*args, **kwargs)
        end = datetime.now()
        logger.info("Execution Time for %s: start:%s, end:%s, duration: %s", func.__name__, start, end, (end - start))
        return result

    return inner


def remove_prefix(self: str, prefix: str = "/") -> str:
    if self.startswith(prefix):
        return self[len(prefix):]
    else:
        return self[:]


def remove_suffix(self: str, suffix: str = "/") -> str:
    # suffix='' should not call self[:-0].
    if suffix and self.endswith(suffix):
        return self[: -len(suffix)]
    else:
        return self[:]


class CmdHelper:
    @staticmethod
    def execute_cmd(cmd, check=False) -> int:
        logger.debug("Execute command : %s", cmd)
        error_code = os.system(cmd)
        if error_code != 0 and check:
            logger.error("Error executing cmd : %s", cmd)
            raise Exception("Error executing command")
        return error_code

    @staticmethod
    @log_debug
    def execute_cmd_and_get_output(cmd) -> str:
        try:
            logger.debug("Execute command : %s", cmd)
            return subprocess.getoutput(cmd)
        except subprocess.CalledProcessError:
            logger.error("Error executing cmd : %s", cmd)
            return ""

    @staticmethod
    def decode_password(encoded_password: str):
        if encoded_password.startswith("<encoded:"):
            x = remove_prefix(encoded_password, "<encoded:")
            y = remove_suffix(x, ">").encode("utf-8")
            return base64.b64decode(y).decode("utf-8")
        return encoded_password

    @staticmethod
    def decode_base64(base64_encoded_string: str) -> str:
        return base64.b64decode(base64_encoded_string).decode("utf-8")

    @staticmethod
    def encode_base64(plaintext_string: str) -> str:
        return base64.b64encode(bytes(plaintext_string, "utf-8")).decode("utf-8")

    @staticmethod
    def escape_ansi(line):
        ansi_escape = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]")
        return ansi_escape.sub("", line)
