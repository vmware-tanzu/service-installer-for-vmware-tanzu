# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

from abc import abstractmethod


class extensions_types:
    @abstractmethod
    def fluent_bit(self, fluent_bit_type):
        pass

    @abstractmethod
    def grafana(self):
        pass

    @abstractmethod
    def logging(self):
        pass

    @abstractmethod
    def prometheus(self):
        pass


class deploy_extensions:
    @abstractmethod
    def deploy(self, extension_name):
        pass
