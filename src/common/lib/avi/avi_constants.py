# Copyright 2021 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause


class AVIConfig:
    AVI_SIZE = {
        "essentials": {"cpu": "4", "memory": "24576"},
        "small": {"cpu": "6", "memory": "24576"},
        "medium": {"cpu": "10", "memory": "32768"},
        "large": {"cpu": "16", "memory": "49152"},
    }
    # TODO as part of app config??
    DEFAULT_PASSWORD = "58NFaGDJm(PJH0G"
    DEFAULT_USERNAME = "admin"


class AVIDataFiles:
    SYS_CONFIG = "systemConfig.json"
    SYS_CONFIG_1 = "systemConfig1.json"
    IPAM_DETAILS = "ipam_details.json"
    NEW_CLOUD_IPAM_DETAILS = "detailsOfNewCloudIpam.json"
    NEW_CLOUD_DETAILS = "newCloudInfo.json"
    IPAM_DETAILS_GET = "ipam_details_get.json"
    NEW_CLOUD_INFO = "newCloudInfo.json"
    NETWORK_DETAILS = "managementNetworkDetails.json"
    VIP_IP_TXT = "network_details.json"
    SERVICE_ENGINE_DETAILS_1 = "detailsOfServiceEngine1.json"
    DETAILS_OF_IPAM = "detailsOfIpam.json"
    AVI_SE_OVA = "/tmp/{avi_uuid}.ova"
