# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import os
import logging.config
# logging.config.fileConfig('../logging.conf', disable_existing_loggers=False)
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
logging.config.fileConfig('%s/logging.conf' % basepath)
logger = logging.getLogger(__name__)
