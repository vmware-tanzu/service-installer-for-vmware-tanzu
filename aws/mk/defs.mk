include $(SRCROOT)/mk/defs_build.mk

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