#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class HealthEnum(str, Enum):
    UP = "UP"
    DOWN = "DOWN"


class ExtensionState(BaseModel):
    deployed: bool
    upgraded: bool


class SharedExtensionState(BaseModel):
    certManager: ExtensionState
    contour: ExtensionState
    externalDns: ExtensionState
    harbor: ExtensionState

class IntegrationState(BaseModel):
    attached: bool

    
class CommonIntegrationState(BaseModel):
    tmc: IntegrationState


class WorkloadExtensionState(BaseModel):
    certManager: ExtensionState
    contour: ExtensionState
    prometheus: ExtensionState
    grafana: ExtensionState


class Info(BaseModel):
    name: Optional[str] = ""
    deployed: bool
    version: str
    health: HealthEnum = HealthEnum.DOWN


class SharedClusterInfo(BaseModel):
    name: Optional[str] = ""
    deployed: bool
    version: str
    upgradedFrom: Optional[str] = None
    health: HealthEnum = HealthEnum.DOWN
    extensions: SharedExtensionState
    integrations: Optional[CommonIntegrationState]


class WorkloadClusterInfo(BaseModel):
    name: Optional[str] = ""
    deployed: bool
    version: str
    health: HealthEnum = HealthEnum.DOWN
    extensions: WorkloadExtensionState
    integrations: Optional[CommonIntegrationState]


class State(BaseModel):
    avi: Info
    mgmt: Info
    shared_services: SharedClusterInfo
    workload_clusters: Optional[List[WorkloadClusterInfo]] = []


def new_extension_state() -> ExtensionState:
    return ExtensionState(deployed=False, upgraded=False)


def get_fresh_state() -> State:
    info = Info(deployed=False, health=HealthEnum.DOWN, version="")
    extension_state = ExtensionState(deployed=False, upgraded=False)
    shared_extensions = SharedExtensionState(certManager=extension_state, contour=extension_state,
                                             externalDns=extension_state, harbor=extension_state)
    shared_cluster_info = SharedClusterInfo(deployed=False, health=HealthEnum.DOWN, version="",
                                            extensions=shared_extensions)
    return State(avi=info, mgmt=info, shared_services=shared_cluster_info, workload_clusters=[])
