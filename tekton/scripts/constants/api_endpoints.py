"""
General convention for adding fields:
- All the API endpoints must start with '/' prefix and the base URL must not have a trailing '/'
"""
#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from enum import Enum


class NSXT(str, Enum):
    VMC_BASE_URL = "{url}/orgs/{org_id}/sddcs/{sddc_id}"
    LIST_SEGMENTS = '/policy/api/v1/infra/tier-1s/{gw_id}/segments/'
    CRUD_SEGMENT = '/policy/api/v1/infra/tier-1s/{gw_id}/segments/{segment_id}'
    LIST_GROUPS = '/policy/api/v1/infra/domains/{gw_id}/groups/'
    CRUD_GROUP = '/policy/api/v1/infra/domains/{gw_id}/groups/{group_id}'
    LIST_SERVICES = '/policy/api/v1/infra/services'
    CRUD_SERVICE = '/policy/api/v1/infra/services/{service_id}'
    LIST_GATEWAY_FIREWALL_RULES = '/policy/api/v1/infra/domains/{gw_id}/gateway-policies/{gw_policy_id}/rules'
    CRUD_GATEWAY_FIREWALL_RULE = '/policy/api/v1/infra/domains/{gw_id}/gateway-policies/{gw_policy_id}/rules/{rule_id}'


class VMC(str, Enum):
    BASE_URL = 'https://vmc.vmware.com/vmc/api'
    GET_ALL_ORGS = '/orgs'
    GET_ALL_SDDCS = '/sddcs'
