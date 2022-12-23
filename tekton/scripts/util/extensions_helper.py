#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

import os, sys
import re
import traceback
import json
from util import cmd_runner
from pathlib import Path
import base64
import logging

from util.logger_helper import LoggerHelper, log

logger = LoggerHelper.get_logger(Path(__file__).stem)

def checkTanzuExtensionEnabled(jsonspec):
    try:
        tanzu_ext = str(
            jsonspec['tanzuExtensions']['enableExtensions'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False

def checkPromethusEnabled(jsonspec):
    try:
        tanzu_ext = str(
            jsonspec['tanzuExtensions']['monitoring']['enableLoggingExtension'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_syslog_endpoint_enabled(jsonspec):
    try:
        tanzu_ext = str(
            jsonspec['tanzuExtensions']['logging']['syslogEndpoint']['enableSyslogEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_http_endpoint_enabled(jsonspec):
    try:
        tanzu_ext = str(
            jsonspec['tanzuExtensions']['logging']['httpEndpoint']['enableHttpEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_elastic_search_endpoint_enabled(jsonspec):
    try:
        tanzu_ext = str(
            jsonspec['tanzuExtensions']['logging']['elasticSearchEndpoint'][
                'enableElasticSearchEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_kafka_endpoint_endpoint_enabled(jsonspec):
    try:
        tanzu_ext = str(
            jsonspec['tanzuExtensions']['logging']['kafkaEndpoint']['enableKafkaEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False


def check_fluent_bit_splunk_endpoint_endpoint_enabled(jsonspec):
    try:
        tanzu_ext = str(
            jsonspec['tanzuExtensions']['logging']['splunkEndpoint']['enableSplunkEndpoint'])
        if tanzu_ext.lower() == "true":
            return True
        else:
            return False
    except Exception:
        return False