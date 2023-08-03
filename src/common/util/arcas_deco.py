# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

__author__: str = "Abhishek Inani"

try:
    if __import__("prettytable"):
        import prettytable

        # import PTable       # PTable just need to be installed not import, if imported will give ModuleNotFound
except ImportError as e:
    print(f"Package not found : {e}")
    print(
        """Install using:
                    1. pip3 install prettytable
                    2. pip3 install PTable
             """
    )
    sys.exit(0)


class ArcasDecorator:
    def __init__(self):
        self.table = prettytable.PrettyTable()

    def add_row(self, row):
        self.table.add_row(row)

    def add_column(self, title: str, col):
        self.table.add_column(title, col)

    def print_table(self):
        # log.info('\n' + str(self.table))
        print("\n" + str(self.table))

    def table_decorator(self, table_title: str, table_fields: list = None):
        self.table.title = table_title
        if table_fields:
            self.table.field_names = table_fields

    @staticmethod
    def table_footer(tbl, text, dc):
        res = f"{tbl._vertical_char} {text}{' ' * (tbl._widths[0] - len(text))} {tbl._vertical_char}"

        for idx, item in enumerate(tbl.field_names):
            if idx == 0:
                continue
            if item not in dc.keys():
                res += f"{' ' * (tbl._widths[idx] + 1)} {tbl._vertical_char}"
            else:
                res += f"{' ' * (tbl._widths[idx] - len(str(dc[item])))} {dc[item]} {tbl._vertical_char}"

        res += f"\n{tbl._hrule}"
        return res
