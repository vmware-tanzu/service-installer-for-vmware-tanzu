#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Version(BaseModel):
    tkg: str


class DesiredState(BaseModel):
    version: Version
    bomImageTag: Optional[str] = None
