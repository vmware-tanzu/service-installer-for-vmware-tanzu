"""
General convention for adding fields:
- All the API endpoints must start with '/' prefix and the base URL must not have a trailing '/'
"""
from enum import Enum


class VmcEndpoint(str, Enum):
    BASE_URL = 'https://vmc.vmware.com/vmc/api'
    GET_ALL_ORGS = '/orgs'
    GET_ALL_SDDCS = '/sddcs'
