# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import logging

from common.constants.constants import KubectlCommands
from common.util.base_cmd_helper import BaseCmdHelper

# TODO: Replace with existing logger implementation
logger = logging.getLogger()


class KubectlClient:
    def __init__(self, cmd_runner: BaseCmdHelper):
        self.cmd_runner = cmd_runner

    def delete_cluster_context(self, cluster_name):
        logger.info(f"Deleting kubectl context for {cluster_name} cluster")
        delete_kubectl_context = KubectlCommands.DELETE_KUBECTL_CONTEXT.format(cluster=cluster_name)
        return self.cmd_runner.run_cmd(delete_kubectl_context)

    def delete_cluster_context_tkgs(self, cluster_name):
        logger.info(f"Deleting kubectl context for {cluster_name} cluster")
        delete_kubectl_context = KubectlCommands.DELETE_KUBECTL_CONTEXT_TKGS.format(cluster=cluster_name)
        return self.cmd_runner.run_cmd(delete_kubectl_context)

    def delete_cluster(self, cluster_name):
        logger.info(f"Deleting kubectl cluster for {cluster_name} cluster")
        delete_kubectl_cluster = KubectlCommands.DELETE_KUBECTL_CLUSTER.format(cluster=cluster_name)
        return self.cmd_runner.run_cmd(delete_kubectl_cluster)
