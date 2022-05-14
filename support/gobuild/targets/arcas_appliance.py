# Copyright 2008 VMware, Inc.  All rights reserved. -- VMware Confidential
"""
ARCAS gobuild product module.
"""
import os
import re

import helpers.target
import helpers.ant
import helpers.env
import helpers.make
import specs.arcas_appliance

ALLOW_OFFICIAL_KEY='allow.elfofficialkey'

class DemoVA(helpers.target.Target, helpers.make.MakeHelper):
    """
    Base class for ARCAS Appliance projects.
    """

    """
    ARCAS Appliance using Photon as guest base OS with source in git repository.
    """
    def __init__(self):
        self.productname = 'Service installer for VMware Tanzu'
        self.longprodname = 'Builds arcas'
        self.shortname = 'arcas'
        self.prodversion = '1.2.0'
        self.sourcerootname = 'arcas'
        self.sourceroot = '%(buildroot)/' + self.sourcerootname

    def GetBuildProductVersion(self, hosttype):
        return self.prodversion

    def GetClusterRequirements(self):
        return ['linux64-vm']

    def GetOptions(self):
        """
        Return a list of flags this target supports.
        """
        return [
            (ALLOW_OFFICIAL_KEY, False,
             'Whether or not allow official key to be turned on.'
             ' This flag is controlled by gobuildharness.')
        ]

    def GetStorageInfo(self, hosttype):
        storages = []
        if hosttype.startswith('linux'):
            storages += [{'type': 'source', 'src': self.productname + '/'}]
        storages += [{'type': 'build', 'src': self.productname + '/build/'}]
        return storages

    def _GetEnvironment(self, hosttype):
        env = helpers.env.SafeEnvironment(hosttype)
        path = []
        if hosttype.startswith('windows'):
            tcroot = os.environ.get('TCROOT', 'C:/TCROOT-not-set')
            path += [r'%s\win32\coreutils-5.3.0\bin' % tcroot]
        elif hosttype.startswith('linux'):
            pkgs = [
                'coreutils-5.97',
                'diffutils-2.8',
                'file-4.19',
                'findutils-4.2.27',
                'gawk-3.1.6',
                'grep-2.5.1a',
                'gzip-1.3.5',
                'mktemp-1.5',
                'rpm-4.3.3-18_nonptl',
                'sed-4.1.5',
                'cpio-2.9',
                'zip-3.0',
                'tar-1.23',
                'zlib-1.2.7',
            ]
            path = ['/build/toolchain/lin32/%s/bin' % p for p in pkgs]
            path += [
                '/usr/bin',
                '/bin',
                '/usr/local/sbin',
                '/usr/local/bin',
                '/usr/local/var',
                '/usr/sbin',
                '/sbin',
            ]
        path += [env['PATH']]
        env['PATH'] = os.pathsep.join(path)
        OVF_OFFICIAL_KEY = 1
        if self.options.get(ALLOW_OFFICIAL_KEY) and OVF_OFFICIAL_KEY:
            self.log.debug('Turning on official OVF signing.')
            env['OVF_OFFICIAL_KEY'] = '1'
        env['CREATE_OSS_TGZ'] = '1'
        return env


class PhotonVA(DemoVA):
    """
    PhotonVA VA using Photon as guest base OS with source in git repository.
    """
    def GetBuildProductNames(self):
        return {
            'name': self.productname,
            'longname': 'Service installer for VMware Tanzu with source in git using Photon OS as guest base OS'
        }

    def GetRepositories(self, hosttype):
        src = 'core-build/arcas.git;%(branch);'

        repos = [{
            'rcs': 'git',
            'src': src,
            'dst': 'arcas',
        }]
        return repos

    def GetCommands(self, hosttype):
        target = 'all'
        flags = {}
        return [{
            'desc': 'Building arcas from git repo',
            'root': self.sourceroot + '/photon',
            'log': '%s.log' % target,
            'command': self._Command(hosttype, target, **flags),
            'env': self._GetEnvironment(hosttype),
        }]

    def GetComponentDependencies(self):
        comps = {}
        comps['csc-photon'] = {
            'branch': specs.arcas_appliance.CSC_PHOTON_BRANCH,
            'change': specs.arcas_appliance.CSC_PHOTON_CLN,
            'buildtype': specs.arcas_appliance.CSC_PHOTON_BUILDTYPE,
            'files': specs.arcas_appliance.CSC_PHOTON_FILES,
        }
        comps['va_hardening'] = {
            'branch': specs.arcas_appliance.VA_HARDENING_BRANCH,
            'change': specs.arcas_appliance.VA_HARDENING_CLN,
            'buildtype': specs.arcas_appliance.VA_HARDENING_BUILDTYPE,
            'url_enabled': specs.arcas_appliance.VA_HARDENING_ENABLED,
            'files': specs.arcas_appliance.VA_HARDENING_FILES,
        }
        comps['studiova'] = {
            'branch': specs.arcas_appliance.STUDIOVA_BRANCH,
            'change': specs.arcas_appliance.STUDIOVA_CLN,
            'buildtype': specs.arcas_appliance.STUDIOVA_BUILDTYPE,
            'url_enabled': specs.arcas_appliance.STUDIOVA_URL_ENABLED,
            'files': specs.arcas_appliance.STUDIOVA_FILES,
        }
        comps['va_build'] = {
            'branch': specs.arcas_appliance.VA_BUILD_BRANCH,
            'change': specs.arcas_appliance.VA_BUILD_CLN,
            'buildtype': specs.arcas_appliance.VA_BUILD_BUILDTYPE,
            'hosttypes': specs.arcas_appliance.VA_BUILD_HOSTTYPES,
        }
        return comps
