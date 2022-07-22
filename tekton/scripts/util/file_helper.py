#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import json
import os
import pkgutil
import re
from os.path import dirname
from pathlib import Path

import yaml
from constants.constants import Paths
from model.desired_state import DesiredState
from model.spec import MasterSpec
from model.status import State
from model.status import ScaleDetail
from model.status import RepaveDetail
from pydantic.main import BaseModel
from yaml.loader import SafeLoader

from util.logger_helper import LoggerHelper, log

logger = LoggerHelper.get_logger(Path(__file__).stem)


class FileHelper:
    @staticmethod
    def load_state(spec_path: str) -> State:
        # Open the file and load the file
        with open(spec_path) as f:
            data = yaml.load(f, Loader=SafeLoader)
        return State.parse_obj(data)

    @staticmethod
    def load_scale(spec_path: str) -> ScaleDetail:
        # Open the file and load the file
        with open(spec_path) as f:
            data = yaml.load(f, Loader=SafeLoader)
        return ScaleDetail.parse_obj(data)

    @staticmethod
    def load_repave(spec_path: str) -> RepaveDetail:
        # Open the file and load the file
        with open(spec_path) as f:
            data = yaml.load(f, Loader=SafeLoader)
        return RepaveDetail.parse_obj(data)

    @staticmethod
    def load_desired_state(spec_path: str) -> DesiredState:
        with open(spec_path) as f:
            data = yaml.load(f, Loader=SafeLoader)
        return DesiredState.parse_obj(data)

    @staticmethod
    def load_spec(spec_path: str) -> MasterSpec:
        # Open the file and load the file
        with open(spec_path) as f:
            data = yaml.load(f, Loader=SafeLoader)
        return MasterSpec.parse_obj(data)

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
    def dump_spec(spec: MasterSpec, file_path: str) -> str:
        # Open the file and load the file
        with open(file_path, "w") as f:
            yaml.dump(yaml.load(spec, Loader=SafeLoader), f)
        return file_path

    @staticmethod
    def dump_state(state: State, file_path: str):
        # Open the file and load the file
        with open(file_path, "w") as f:
            yaml.dump(yaml.load(state.json(), Loader=SafeLoader), f)

    @staticmethod
    def read_file(file_path):
        logger.debug(f"Read file : {file_path}")
        if not os.path.exists(file_path):
            logger.warning(f"file path doesn't exist : {file_path}")
            return ""
        with open(file_path, "r") as file:
            return file.read().strip()

    @staticmethod
    def read_resource(file_path):
        logger.debug(f"Read file : {file_path}")
        return pkgutil.get_data(__package__, "../" + file_path).decode()

    @staticmethod
    def get_link(file_path):
        logger.debug(f"Getting link for file : {file_path}")
        if not os.path.islink(file_path):
            logger.warning(f"Not a link : {file_path}")
            return None
        return os.readlink(file_path)

    @staticmethod
    def write_dict_to_file(file, json_dict):
        with open(file, "w") as outfile:
            json.dump(json_dict, outfile, indent=4)

    @staticmethod
    def write_to_file(content: str, file):
        with open(file, "w") as outfile:
            outfile.write(content)

    @staticmethod
    def make_parent_dirs(path: str):
        os.makedirs(dirname(path), exist_ok=True)

    @staticmethod
    def replace_pattern(src, target, pattern_replacement_list: list):
        """
        Replace a string in source file contents and store updated content on target file
        :param src: source file path
        :param target: target file path
        :param pattern_replacement_list: List containing pairs of (pattern_to_replace, replacement_value) values
        :return:
        """
        if not pattern_replacement_list or len(pattern_replacement_list) == 0:
            return
        try:
            with open(src, "r") as fin:
                data = fin.readlines()
        except IOError as ex:
            logger.error(f"Failed to read from file: {src}")
            raise ex

        text = "".join(data)
        text_updated = "".join(data)
        for pattern, replacement in pattern_replacement_list:
            text_updated = re.sub(pattern, replacement, text)
            text = text_updated

        try:
            with open(target, "w") as fout:
                fout.write(text_updated)
        except IOError as ex:
            logger.error(f"Failed to write to file: {target}")
            raise ex

    @staticmethod
    def yaml_from_model(model: BaseModel):
        return yaml.dump(yaml.safe_load(model.json()))

    @staticmethod
    @log("Cleanup kubeconfig repo")
    def clear_kubeconfig(root_dir):
        config_rel_paths = [Paths.REPO_KUBE_CONFIG, Paths.REPO_KUBE_TKG_CONFIG, Paths.REPO_TANZU_CONFIG]
        for rel_path in config_rel_paths:
            abs_path = os.path.join(root_dir, rel_path)
            if os.path.exists(abs_path):
                os.remove(abs_path)
