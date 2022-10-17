# Copyright 2017 VMware, Inc.  All rights reserved. -- VMware Confidential

"""
Arcas Appliance component spec.
"""

# Photon OS ISO
CSC_PHOTON_BRANCH = 'photon3-vmw-updates'
CSC_PHOTON_CLN = 10058579
CSC_PHOTON_BUILDTYPE = 'release'
CSC_PHOTON_DELIVERABLE = [
    r'publish/csc-photon-.*x86_64\.iso',
    r'publish/csc-photon-.*x86_64\.src\.iso',
    r'publish/csc-photon-.*x86_64\.pkginfo\.txt'
]
CSC_PHOTON_FILES = {
    'linux64': CSC_PHOTON_DELIVERABLE,
    'linux': CSC_PHOTON_DELIVERABLE,
    'linux64-vm': CSC_PHOTON_DELIVERABLE,
    'linux-centos72-gc32': CSC_PHOTON_DELIVERABLE,
    'linux-centos64-64': CSC_PHOTON_DELIVERABLE
}

VA_BUILD_BRANCH = 'main'
VA_BUILD_CLN = 2461305
VA_BUILD_BUILDTYPE = 'release'
VA_BUILD_HOSTTYPES = {
    'linux64': 'linux',
    'linux': 'linux',
    'linux64-vm': 'linux',
    'linux-centos72-gc32': 'linux',
    'linux-centos64-64': 'linux'
}

CAYMAN_OPENJDK_PRODUCT = 'cayman_openjdk'
CAYMAN_OPENJDK_BRANCH = 'vmware-prebuilt-jdk11'
CAYMAN_OPENJDK_CLN = '57283f5c67de38ab66e0e8298fbbe994b14e7b83'
CAYMAN_OPENJDK_BUILDTYPE = "release"
CAYMAN_OPENJDK_URL_ENABLED = True
CAYMAN_OPENJDK_FILES = {
    'linux': [r'publish/.*', ],
    'linux64': [r'publish/.*', ],
    'linux64-vm': [r'publish/.*', ],
    'linux-centos64-64': [r'publish/.*', ]
}

VA_HARDENING_BRANCH = 'vahardening-photon'
VA_HARDENING_CLN = 2235500
VA_HARDENING_BUILDTYPE = 'release'
VA_HARDENING_ENABLED = True
VA_HARDENING_DELIVERABLE = [
    r'publish/photon_vasecurity-11\.3\.0-.*\.noarch.rpm$',
]
VA_HARDENING_FILES = {
    'linux64': VA_HARDENING_DELIVERABLE,
    'linux64-vm': VA_HARDENING_DELIVERABLE,
    'linux': VA_HARDENING_DELIVERABLE,
    'linux-centos72-gc32': VA_HARDENING_DELIVERABLE,
    'linux-centos64-64': VA_HARDENING_DELIVERABLE
}

STUDIOVA_BRANCH = 'test-vmstudio-disk-size'
STUDIOVA_CLN = '04f28f196879dd33d393faa1f1685d45a1e7a1db'  # Studio 3.0.0.7
STUDIOVA_BUILDTYPE = 'beta'
STUDIOVA_URL_ENABLED = True
STUDIOVA_DELIVERABLE = [
    r'publish/prod/exports/ova/.*.ova$',
    r'publish/prod/profile.xml$',
]
STUDIOVA_FILES = {
    'linux64': STUDIOVA_DELIVERABLE,
    'linux': STUDIOVA_DELIVERABLE,
    'linux64-vm': STUDIOVA_DELIVERABLE,
    'linux-centos72-gc32': STUDIOVA_DELIVERABLE,
    'linux-centos64-64': STUDIOVA_DELIVERABLE
}

CAYMAN_HARBOR_PRODUCT = 'cayman_harbor'
CAYMAN_HARBOR_BRANCH = 'vmware-2.5.3'
CAYMAN_HARBOR_CLN = '287fa737dd69f2155b1ac8d4b530dbe9a73b363c'
CAYMAN_HARBOR_BUILDTYPE = "release"
CAYMAN_HARBOR_URL_ENABLED = True
CAYMAN_HARBOR_FILES = {
    'linux': [ r'publish/.*', ],
    'linux64': [ r'publish/.*', ],
    'linux64-vm': [ r'publish/.*', ],
    'linux-centos64-64': [ r'publish/.*', ]
}
CAYMAN_HARBOR_BUILDTYPES = {
    'obj': 'obj',
    'beta': 'beta',
    'release': 'release',
    'opt': 'beta',
}

ARCAS_BRANCH = 'master'
ARCAS_CLN = '17dc621cdef916974e212f648fed627a41a8fce0'
ARCAS_BUILDTYPE = 'beta'
