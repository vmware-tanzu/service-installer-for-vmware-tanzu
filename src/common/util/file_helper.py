import json
import yaml
import pkgutil
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
    def load_json(spec_path: str) -> dict:
        with open(spec_path) as f:
            data = json.load(f)
        return data

    @staticmethod
    def read_resource(file_path):
        current_app.logger.info(f"Read file : {file_path}")
        return pkgutil.get_data(__package__, "../" + file_path).decode()

    @staticmethod
    def write_to_file(content: str, file):
        with open(file, "w") as outfile:
            outfile.write(content)
