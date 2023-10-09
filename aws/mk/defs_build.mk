TCROOT ?= /build/toolchain

UNAME := $(shell uname)
ifeq ($(UNAME), Linux)
COREUTILS_ROOT:= $(TCROOT)/lin32/coreutils-6.12
DIST:= lin32
endif
ifeq ($(UNAME), Darwin)
COREUTILS_ROOT:= $(TCROOT)/mac32/coreutils-8.6
DIST:= mac32
MACOS:= true
endif
MKDIR         := $(COREUTILS_ROOT)/bin/mkdir
RM            := $(COREUTILS_ROOT)/bin/rm
CP            := $(COREUTILS_ROOT)/bin/cp
DIRNAME       := $(COREUTILS_ROOT)/bin/dirname
INSTALL       := $(COREUTILS_ROOT)/bin/install
LN            := $(COREUTILS_ROOT)/bin/ln
MV            := $(COREUTILS_ROOT)/bin/mv
LS            := $(COREUTILS_ROOT)/bin/ls
TAR           := $(TCROOT)/lin32/tar-1.20/bin/tar
ISOINFO       := $(TCROOT)/lin32/cdrtools-2.01/bin/isoinfo
GREP          := $(TCROOT)/lin32/grep-2.5.1a/bin/grep
RPMBUILD      := $(TCROOT)/lin32/rpm-4.3.3-18_nonptl/bin/rpmbuild
UNZIP         := $(TCROOT)/lin32/unzip-6.0/bin/unzip
CURL          := $(TCROOT)/lin32/curl-7.29.0/bin/curl
DOCKER_HOST	  := 'unix:///var/run/docker.sock'
DOCKER_EXEC   :=  sudo -n docker


OBJDIR ?= beta
MAINSRCROOT ?= $(SRCROOT)
CLIENTROOT ?= $(dir $(SRCROOT))
BUILDROOT ?= $(SRCROOT)/build
BUILDLOG_DIR ?= $(BUILDROOT)/logs
PUBLISH_DIR ?= $(BUILDROOT)/publish
BUILD_NUMBER ?= 000000

PRODUCT_VERSION := 1.0.0

extract-docker:
	which docker || tar -zxvf ${SRCROOT}/docker.tgz -C ${SRCROOT}
	@echo "***** Starting docker service..."

	sudo mkdir -m777 -p /build/docker
	echo "STORAGE_DRIVER=overlay" | sudo tee -a /etc/sysconfig/docker-storage-setup
	echo "EXTRA_DOCKER_STORAGE_OPTIONS='-g /build/docker'" | sudo tee -a /etc/sysconfig/docker-storage-setup

	sudo -n systemctl start docker

