# Copyright 2008 VMware, Inc.  All rights reserved. -- VMware Confidential
"""
tkg1click gobuild product module.
"""
import os
import re

import helpers.target
import helpers.ant
import helpers.env
import helpers.make

ALLOW_OFFICIAL_KEY='allow.elfofficialkey'

class Tkg1click(helpers.target.Target, helpers.make.MakeHelper):
    """
    tkg-1click

    The simplest gobuild integration imaginable.  Creates a build
    that does nothing but echo "Hello, World!" on the command line.
    Things obviously can get more complex from here.
    """

    def __init__(self):
       self.productname = 'sivt-aws-federal'
       self.longprodname = 'sivt-aws-federal'
       self.shortname = 'sivt-aws-federal'
       self.prodversion = '1.3.0'
       self.sourcerootname = 'sivt-aws-federal'
       self.sourceroot = '%(buildroot)/' + self.sourcerootname


    def GetBuildProductNames(self):
        return {
            'name': 'sivt-aws-federal',
            'longname': 'sivt-aws-federal',
        }

    def GetRepositories(self, hosttype):
        repos = [{
            'rcs': 'git',
            'src': 'core-build/sivt-aws-federal.git;%(branch);',
            'dst': self.sourcerootname,
        }]
        return repos

    def GetComponentDependencies(self):
      comps = {}
      return comps

    def GetClusterRequirements(self):
        return ['linux-centos72-gc32']

    def GetCommands(self, hosttype):
        target = '-B all'
        flags = {}
        return [{
            'desc': 'Building sivt-aws-federal from git repo',
            'root': self.sourceroot + '/build_web',
            'log': 'all.log',
            'command': self._Command(hosttype, target, **flags),
            'env': self._GetEnvironment(hosttype),
        }]

    def GetStorageInfo(self, hosttype):
        storages = []
        if hosttype.startswith('linux'):
            storages += [{'type': 'source', 'src': self.sourcerootname + '/'}]
        return storages

    def GetBuildProductVersion(self, hosttype):
        return self.prodversion

    def _GetEnvironment(self, hosttype):
        env = helpers.env.SafeEnvironment(hosttype)
        path = []
        if hosttype.startswith('windows'):
            tcroot = os.environ.get('TCROOT', 'C:/TCROOT-not-set')
            path += [r'%s\win32\coreutils-5.3.0\bin' % tcroot]
        elif hosttype.startswith('linux'):
            pkgs = [
                'bzip2-1.0.6-1',
                'coreutils-8.6',
                'cpio-2.9',
                'diffutils-2.8',
                'file-4.19',
                'findutils-4.2.27',
                'gawk-3.1.5',
                'grep-2.5.1a',
                'gzip-1.5',
                'jdk-1.8.0_121',
                'mktemp-1.5',
                'sed-4.1.5',
                'tar-1.23',
                ]
            path = ['/build/toolchain/lin64/%s/bin' % p for p in pkgs]
            path += ['/build/toolchain/noarch/apache-maven-3.3.9/bin']
            path += ['/build/toolchain/lin32/rpm-4.3.3-18_nonptl/bin']
            path += [env['PATH']]

            #expect nodejs to be installed base dir
            path += [self.sourceroot+'/nodejs8/lin64/bin']
            #path += [self.sourceroot+'/docker']
            path += ["/usr/local/bin","/bin","/usr/bin","/usr/local/sbin","/usr/sbin","/sbin"]

            env['PATH'] = os.pathsep.join(path)
            env['JAVA_HOME'] = "/build/toolchain/lin32/jdk-1.8.0_121"

            OVF_OFFICIAL_KEY = 1
            if self.options.get(ALLOW_OFFICIAL_KEY) and OVF_OFFICIAL_KEY:
                self.log.debug('Turning on official OVF signing.')
                env['OVF_OFFICIAL_KEY'] = '1'
                env['CREATE_OSS_TGZ'] = '1'

                env['TCROOT'] = '/build/toolchain'
                env['DCSROOT'] = '%s' % self.sourceroot

        return env
