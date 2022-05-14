#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from model.desired_state import DesiredState
from model.spec import MasterSpec
from model.status import State, ScaleDetail, RepaveDetail


class DeploymentPlatform(str, Enum):
    VMC = "vmc"
    VCF = "vcf"
    VSPHERE = "vsphere"


class VmcConfig(BaseModel):
    csp_access_token: str
    org_id: str
    sddc_id: str
    nsx_reverse_proxy_url: str
    vc_mgmt_ip: str
    vc_cloud_user: str
    vc_cloud_password: str
    vc_tls_thumbprint: str


class RunConfig(BaseModel):
    root_dir: str
    state: State
    desired_state: DesiredState
    support_matrix: dict
    deployment_platform: DeploymentPlatform
    vmc: Optional[VmcConfig]

class ScaleConfig(BaseModel):
    scaledetails: ScaleDetail

class RepaveConfig(BaseModel):
    repave_details: RepaveDetail
