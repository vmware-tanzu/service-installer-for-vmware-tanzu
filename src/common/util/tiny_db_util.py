# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

from tinydb import Query, TinyDB

__author__ = "Abhishek Inani"


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
