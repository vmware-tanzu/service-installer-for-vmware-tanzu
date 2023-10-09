# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
from pathlib import Path

from tinydb import Query, TinyDB

__author__ = "Abhishek Inani"

from common.operation.constants import Component, Env, SivtStatus
from common.util.common_utils import CommonUtils
from common.util.file_helper import FileHelper


class TinyDbUtil:
    def __init__(self, tiny_db_file: str):
        self.db_obj = TinyDB(tiny_db_file)
        self.tiny_db_file = tiny_db_file
        self.query_obj = Query()

    def update_db_file(self, sivt_status: str, sivt_comp: str):
        self.db_obj.update({"status": sivt_status}, self.query_obj.name == sivt_comp)

    def get_all_db_entries(self):
        return self.db_obj.all()

    def truncate_db(self):
        self.db_obj.truncate()

    def fetch_in_progress_job_status(self):
        return self.fetch_status(status=SivtStatus.IN_PROGRESS)

    def fetch_status(self, status):
        resp = self.db_obj.search(self.query_obj.status == status)
        return resp

    def check_db_file(self, env="", json_file=None):
        if not env:
            return
        if not CommonUtils.is_file_exist(self.tiny_db_file):
            print("DB file not exists, initializing DB")
            self.initialize_db(env=env, json_file=json_file)
        elif Path(self.tiny_db_file).stat().st_size == 0:
            print("DB file exists but empty, Creating it")
            self.initialize_db(env=env, json_file=json_file)
        env = env.lower()
        if not self.db_obj.contains(self.query_obj.status == env):
            print(f"DB file exists and have content, but existing env {env} missing, Creating it")
            self.truncate_db()
            self.initialize_db(env=env, json_file=json_file)

    def update_in_progress_to_error(self):
        result = self.fetch_in_progress_job_status()
        for data in result:
            self.db_obj.update({"status": SivtStatus.FAILED}, self.query_obj.name == data["name"])

    def initialize_db(self, env="", json_file=None):
        """
        Method to initialize tiny DB
        """
        try:
            items = [
                {"name": Component.ENV, "status": env},
                {"name": Component.PRECHECK, "status": SivtStatus.NOT_STARTED},
                {"name": Component.VCF_PRECONFIG, "status": SivtStatus.NOT_STARTED},
                {"name": Component.VMC_PRECONFIG, "status": SivtStatus.NOT_STARTED},
                {"name": Component.AVI, "status": SivtStatus.NOT_STARTED},
                {"name": Component.MGMT, "status": SivtStatus.NOT_STARTED},
                {"name": Component.WCP_CONFIG, "status": SivtStatus.NOT_STARTED},
                {"name": Component.WCP, "status": SivtStatus.NOT_STARTED},
                {"name": Component.NAMESPACE, "status": SivtStatus.NOT_STARTED},
                {"name": Component.SHARED_SERVICE, "status": SivtStatus.NOT_STARTED},
                {"name": Component.WORKLOAD_PRECONFIG, "status": SivtStatus.NOT_STARTED},
                {"name": Component.WORKLOAD, "status": SivtStatus.NOT_STARTED},
                {"name": Component.EXTENSIONS, "status": SivtStatus.NOT_STARTED},
                {"name": Component.CLEANUP, "status": SivtStatus.NOT_STARTED},
            ]

            self.db_obj.insert_multiple(items)

            if env != Env.VCF:
                self.update_db_file(SivtStatus.NA, Component.VCF_PRECONFIG)
            if env != Env.VMC:
                self.update_db_file(SivtStatus.NA, Component.VMC_PRECONFIG)

            try:
                if env == Env.VSPHERE:
                    json_data = FileHelper.load_json(json_file)
                    tkgs = json_data["envSpec"]["envType"]
                    if tkgs.lower() in ["tkgs-ns", "tkgs-wcp"]:
                        self.update_db_file(SivtStatus.NA, Component.MGMT)
                        self.update_db_file(SivtStatus.NA, Component.WORKLOAD_PRECONFIG)
                        self.update_db_file(SivtStatus.NA, Component.SHARED_SERVICE)
                    else:
                        self.update_db_file(SivtStatus.NA, Component.WCP_CONFIG)
                        self.update_db_file(SivtStatus.NA, Component.WCP)
                        self.update_db_file(SivtStatus.NA, Component.NAMESPACE)
            except KeyError:
                self.update_db_file(SivtStatus.NA, Component.WCP_CONFIG)
                self.update_db_file(SivtStatus.NA, Component.WCP)
                self.update_db_file(SivtStatus.NA, Component.NAMESPACE)
        except Exception:
            pass
