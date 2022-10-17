#  Copyright 2021 VMware, Inc
#  SPDX-License-Identifier: BSD-2-Clause

from typing import Optional
from pydantic import BaseModel


class GitAccess(BaseModel):
    host: str
    repository: str
    branch: str
    username: str
    password: str


class UserCredentials(BaseModel):
    git: GitAccess
    imagename: str
    imagepullpolicy: Optional[str] = "Never"
    refreshToken: str
