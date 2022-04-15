#
# Photon 64 bit Demo VA top level makefile
#
#
# Please see below wiki page for details on VAI:
# https://wiki.eng.vmware.com/Virtual_Appliance_Development_Guide
#
# * To build Demo Photon VA:
#   > make all
#
# Prerequisites for running VM build/provision locally:
# 1. Current work client resides on a disk, which is NFS exported.
# 2. The work client disk has at least 10 GB in free space.
#
ifeq ($(OS), Windows_NT) # {
$(error ERROR: this build must be run on Linux.)
else # }{
TOPDIR=..
MAKEFILE_DIR=$(abspath $(dir $(firstword $(MAKEFILE))))
SRCROOT := $(abspath $(MAKEFILE_DIR)$(TOPDIR))
endif # }

all: publish


# See below wiki page for information on gobuild components system.
# https://wiki.eng.vmware.com/Build/Gobuild/Components/Faq
GOBUILD_TARGET := arcas
GOBUILD_AUTO_COMPONENTS ?= 1
include $(SRCROOT)/support/gobuild/make/defs.mk

VA_NAME := service-installer-for-VMware-Tanzu
VA_GUEST_ISO_NAME := csc-photon-3.0.0-x86_64.iso
VA_OS_TYPE := photon
BUILDROOT := $(BUILDROOT)/$(VA_NAME)
APPLPKGS_DIR := $(BUILDROOT)/appl-pkgs
VA_PROFILE := $(SRCROOT)/photon/photon.xml
STUDIO_OVF := $(GOBUILD_STUDIOVA_URL)/prod/exports/ovf/VMware_Studio.ovf
POSTINSTALL := $(BUILDROOT)/postinstall
# Script to patch studio build VM at build time.
PATCH_STUDIOVM_SCRIPT := $(SRCROOT)/photon/patch-studio-vm.sh
# See below section of wiki page for details on VA security hardening.
# https://wiki.eng.vmware.com/Virtual_Appliance_Development_Guide
# - Activation_of_security_hardening
VASECURITY_RPM_DIR := $(BUILDROOT)/vasecurity-RPM
VASECURITY_RPM_BUILDDIR := $(VASECURITY_RPM_DIR)/vasecurity
VASECURITY_DIR := $(SRCROOT)/photon/vasecurity
VASECURITY_RPM_SPEC := $(VASECURITY_DIR)/vasecurity.spec
OVERRIDDEN_PDIS := $(VASECURITY_DIR)/OverriddenPDIs
# PERL_LIBXML = $(GOBUILD_STUDIO_TESTFW_ROOT)/photon1

# VA version
VA_PRODUCT_VERSION := 1.1.0
VA_VERSION := $(VA_PRODUCT_VERSION).$(PRODUCT_BUILD_NUMBER)
VA_FULLVERSION := "$(VA_VERSION) Build $(BUILD_NUMBER)"
RPM_HOME := $(SRCROOT)/photon/rpm


arcas-script-rpm: apply-build-settings
	@echo "Packaging arcas scripts as rpm package"
	$(MKDIR) -p $(APPLPKGS_DIR)

	@echo "**************** Assembling arcas-script-rpm ***************"
	sed 's|{build.version}|$(VA_PRODUCT_VERSION)|g' $(RPM_HOME)/arcas-scripts-rpm.spec --in-place
	cd $(RPM_HOME) && \
	chmod u+x make-scripts-rpm.sh && \
	./make-scripts-rpm.sh
	cd '$(SRCROOT)/photon'
	$(INSTALL) $(RPM_HOME)/*.rpm $(APPLPKGS_DIR)

# Below target is to package va_hardening scripts into rpm format.
# It serves as sample code for packaging application software as rpm package,
# to be installed or updated through software packages manager on the VA.
va-security:
	$(MKDIR) -p $(APPLPKGS_DIR)
	$(MKDIR) -p $(VASECURITY_RPM_BUILDDIR)
	# Untar hardening scripts
	$(MKDIR) -p $(GOBUILD_VA_HARDENING_ROOT)
	$(WGET) $(GOBUILD_VA_HARDENING_URL)/photon_hardening.tar.gz -P $(GOBUILD_VA_HARDENING_ROOT)/
	$(TAR) -xzf $(GOBUILD_VA_HARDENING_ROOT)/photon_hardening.tar.gz -C \
	   $(VASECURITY_RPM_BUILDDIR)
	# Pick up per-branch file, 'OverriddenPDIs', if it exists
	[ -e $(OVERRIDDEN_PDIS) ] && \
	   $(CP) -f $(OVERRIDDEN_PDIS) $(VASECURITY_RPM_BUILDDIR)/vahardening
	@echo "**** Building vasecurity rpm..."
	$(RPMBUILD) -bb $(VASECURITY_RPM_SPEC) --define 'version $(VA_VERSION)' \
	    --define 'release $(BUILD_NUMBER)' --define '_builddir $(VASECURITY_RPM_DIR)' \
	    --define '_rpmdir $(BUILDROOT)'

apply-build-settings:
	@echo "***** Adding build number $(BUILD_NUMBER) to the VA profile at $(VA_PROFILE)"
	sed -i 's/@@BUILD_NUMBER@@/$(BUILD_NUMBER)/g' $(VA_PROFILE)
	@echo "***** Adding product version $(VA_VERSION) to the VA profile at $(VA_PROFILE)"
	sed -i 's/@@VA_VERSION@@/$(VA_VERSION)/g' $(VA_PROFILE)

	@echo "***** VA profile content"
	@cat $(VA_PROFILE)

# Below target serves as sample code on putting application packages and any
# other dependent packages into APPLPKGS_DIR.
# During studio VA provision process, it installs all packages found under
# APPLPKGS_DIR onto the VA right after base OS installation.
va-pkgs: arcas-script-rpm va-security
	$(MKDIR) -p $(APPLPKGS_DIR)
	$(INSTALL) $(BUILDROOT)/noarch/*.rpm $(APPLPKGS_DIR)

# Below target involves build-va script, the driver to create VA with use
# of VMware Studio in our build system.
photon-va: va-pkgs
	$(MKDIR) -p $(BUILDLOG_DIR) $(PUBLISH_DIR)
	$(GOBUILD_VA_BUILD_ROOT)/build-va.py \
	    --va-name $(VA_NAME) \
	    --va-version $(VA_VERSION) \
	    --va-fullversion $(VA_FULLVERSION) \
	    --profile $(VA_PROFILE) \
	    --iso $(GOBUILD_CSC_PHOTON_ROOT)/$(VA_GUEST_ISO_NAME) \
	    --os-type $(VA_OS_TYPE) \
	    --appliance-pkgs-dir $(APPLPKGS_DIR) \
	    --buildnumber $(BUILD_NUMBER) \
	    --clientroot $(CLIENTROOT) \
	    --buildroot $(BUILDROOT) \
	    --logdir $(BUILDLOG_DIR) \
	    --studio-ovf $(STUDIO_OVF) \
	    --sign-keyid $(KEYID) \
	    --patch-buildvm-script $(PATCH_STUDIOVM_SCRIPT) \
	    --os-packages audit \
	    --verbose \
	    $(CREATE_OSS_TGZ_FLAG)
	@echo "***** $(VA_NAME) build has completed successfully."


# Anything under PUBLISH_DIR will be published as build deliverable,
# made available on buildweb.
publish: photon-va
	@echo "***** Publishing VA build deliverable to $(PUBLISH_DIR)..."
	$(MKDIR) -p $(PUBLISH_DIR)
	$(RM) -rf $(PUBLISH_DIR)/exports
	$(MV) -f $(BUILDROOT)/exports $(PUBLISH_DIR)
	$(MV) -f $(BUILDROOT)/profile.xml $(PUBLISH_DIR)
	$(CP) -f $(PUBLISH_DIR)/exports/ova/*.ova $(PUBLISH_DIR)/
	$(CP) -f $(SRCROOT)/photon/open_source_license* $(PUBLISH_DIR)/

	$(MKDIR) -p $(VA_NAME)-$(VA_VERSION)-$(BUILD_NUMBER)_updaterepo
	$(CP) -rf $(PUBLISH_DIR)/exports/Update_Repo/* $(VA_NAME)-$(VA_VERSION)-$(BUILD_NUMBER)_updaterepo
	$(ZIP) -r $(PUBLISH_DIR)/$(VA_NAME)-$(VA_VERSION)-$(BUILD_NUMBER)_updaterepo.zip $(VA_NAME)-$(VA_VERSION)-$(BUILD_NUMBER)_updaterepo

ifneq ($(CREATE_OSS_TGZ),)
	$(MV) -f $(BUILDROOT)/*.oss.tgz $(PUBLISH_DIR)
endif

clean:
	$(RM) -rf $(BUILDROOT)
