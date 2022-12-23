# Copyright 2021 VMware, Inc.  All rights reserved. -- VMware Confidential

CAP_BRANCH = "1.5"
CAP_CLN = "a2153702b0205518fc9cc57426dde9b7153a62a2"
CAP_BUILDTYPE = "release"
CAP_DELIVERABLE = [
    r"publish/cap-lin.zip",
]
CAP_FILES = {
    "linux-centos8": CAP_DELIVERABLE,
    "linux-centos8-vm": CAP_DELIVERABLE,
}

CAYMAN_HARBOR_PRODUCT = "cayman_harbor"
CAYMAN_HARBOR_BRANCH = "vmware-2.5.3"
CAYMAN_HARBOR_CLN = "287fa737dd69f2155b1ac8d4b530dbe9a73b363c"
CAYMAN_HARBOR_BUILDTYPE = "release"
CAYMAN_HARBOR_URL_ENABLED = True
CAYMAN_HARBOR_FILES = {
    "linux-centos8": [
        r"publish/lin64/harbor/harbor-offline-installer.*",
    ],
    "linux-centos8-vm": [
        r"publish/lin64/harbor/harbor-offline-installer.*",
    ],
}
CAYMAN_HARBOR_BUILDTYPES = {
    "obj": "obj",
    "beta": "beta",
    "release": "release",
    "opt": "beta",
}
