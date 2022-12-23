TCROOT ?= /build/toolchain
COREUTILS_ROOT:= $(TCROOT)/lin32/coreutils-6.12
MKDIR         := $(COREUTILS_ROOT)/bin/mkdir
RM            := $(COREUTILS_ROOT)/bin/rm
CP            := $(COREUTILS_ROOT)/bin/cp
CHMOD         := $(COREUTILS_ROOT)/bin/chmod
DIRNAME       := $(COREUTILS_ROOT)/bin/dirname
INSTALL       := $(COREUTILS_ROOT)/bin/install
LN            := $(COREUTILS_ROOT)/bin/ln
MV            := $(COREUTILS_ROOT)/bin/mv
LS            := $(COREUTILS_ROOT)/bin/ls
TAR           := $(TCROOT)/lin32/tar-1.20/bin/tar
ISOINFO       := $(TCROOT)/lin32/cdrtools-2.01/bin/isoinfo
GREP          := $(TCROOT)/lin32/grep-2.5.1a/bin/grep
RPMBUILD      := $(TCROOT)/lin32/rpm-4.3.3-18_nonptl/bin/rpmbuild
OVFTOOL       := $(TCROOT)/lin32/ovftool-4.3.0-1
ZIP           := $(TCROOT)/lin32/zip-3.0/bin/zip
UNZIP		  := $(TCROOT)/lin32/unzip-6.0/bin/unzip
CURL          := $(TCROOT)/lin32/curl-7.38.0/bin/curl
WGET          := $(TCROOT)/lin32/wget-1.11.2/bin/wget
PYTHON          := $(TCROOT)/lin64/python-3.5.1/bin/python
export PATH:=$(OVFTOOL):$(PATH)

OBJDIR ?= beta
MAINSRCROOT ?= $(SRCROOT)
CLIENTROOT ?= $(dir $(SRCROOT))
BUILDROOT ?= $(SRCROOT)/build
BUILDLOG_DIR ?= $(BUILDROOT)/logs
PUBLISH_DIR ?= $(BUILDROOT)/publish
BUILD_NUMBER ?= 000000
DOCKER_EXEC   := sudo -n docker

# OVF sign key.
ifneq ($(OVF_OFFICIAL_KEY),)
   KEYID := ovf_klnext
else
   KEYID := ovf_test
endif

# Flag to create OSS tarfile.
ifneq ($(CREATE_OSS_TGZ),)
   CREATE_OSS_TGZ_FLAG := --generate-osstgz
else
   CREATE_OSS_TGZ_FLAG :=
endif

# Gobuild components download target.
include $(MAINSRCROOT)/support/gobuild/make/auto-components.mk
%-deps:
	$(RM) -rf $(BUILDROOT)/$(OBJDIR)/gobuild/specinfo
	$(MAKE) GOBUILD_TARGET=$* \
	   GOBUILD_AUTO_COMPONENTS_DOWNLOAD=$${GOBUILD_AUTO_COMPONENTS_DOWNLOAD-1} \
	   GOBUILD_AUTO_COMPONENTS_REQUEST=$${GOBUILD_AUTO_COMPONENTS_REQUEST-1} \
	   $*-deps

load-docker:
	sudo yum install -y yum-utils -y
	sudo yum-config-manager \
    				--add-repo \
    				https://download.docker.com/linux/centos/docker-ce.repo
	sudo yum install docker-ce docker-ce-cli containerd.io -y
	@echo "********* Starting docker service *********"
	sudo -n systemctl start docker