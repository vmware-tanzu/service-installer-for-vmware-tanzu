# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json
import os
import pkgutil

import yaml
from flask import current_app
from yaml.loader import SafeLoader


class FileHelper:
    @staticmethod
    def load_yaml(spec_path: str) -> dict:
        with open(spec_path) as f:
            data = yaml.load(f, Loader=SafeLoader)
        return data

    @staticmethod
    def dump_yaml(data, file_path: str):
        with open(file_path, "w") as f:
            yaml.dump(data, f)
        return

    @staticmethod
    def dump_json(file, json_dict):
        with open(file, "w") as outfile:
            json.dump(json_dict, outfile, indent=4)

    @staticmethod
    def load_json(spec_path: str, mode: str = "r") -> dict:
        with open(spec_path, mode) as f:
            data = json.load(f)
        return data

    @staticmethod
    def read_resource(file_path):
        current_app.logger.info(f"Read file : {file_path}")
        return pkgutil.get_data(__package__, "../" + file_path).decode()

    @staticmethod
    def read_lines_from_file(file_path):
        with open(file_path) as fd:
            lines = fd.readlines()
            return lines

    @staticmethod
    def read_line_from_file(file_path):
        with open(file_path) as fd:
            lines = fd.readline()
            return lines

    @staticmethod
    def write_to_file(content: str, file):
        with open(file, "w") as outfile:
            outfile.write(content)

    @staticmethod
    def delete_file(file_path: str):
        if os.path.exists(file_path):
            os.remove(file_path)

    @staticmethod
    def file_as_bytes(file_path):
        with file_path:
            return file_path.read()
