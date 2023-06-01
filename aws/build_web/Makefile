ifeq ($(OS), Windows_NT) # {
$(error ERROR: this build must be run on Linux.)
else # }{
TOPDIR=..
MAKEFILE_DIR=$(abspath $(dir $(firstword $(MAKEFILE))))
SRCROOT := $(abspath $(MAKEFILE_DIR)$(TOPDIR))
endif # }

include $(SRCROOT)/mk/defs_build.mk

all: clean publish
	@echo "***** Build completed successfully..."

TKG-1CLICK :=  $(SRCROOT)
TKG_VERSION := 1.5.3
TKR_VERSION := 1.22.8
aws := $(TKG-1CLICK)/build_web/aws
IMAGEBUILDER_TAG := v0.1.11_vmware.3
REGISTRY := projects.registry.vmware.com

BASE := tkg_1_5_3
AIRGAPPED_CHILD := aws-tkgm-all-dependencies
NON_AIRGAPPED_CHILD := aws-tkgm-non-airgap-dependedcies
OTHER_FILE := other.tar
OTHER_FILE_DIR := new_dependencies_final
TKG_1_FILE  := tkg.tar.001
TKG_2_FILE  := tkg.tar.002
TKG_3_FILE  := tkg.tar.003
TKR_1_FILE := tkr.tar.001
TKR_2_FILE := tkr.tar.002
NON_AIRGAPPED_FILE := 211_tkg_non_airgapped.tar

OUTPUT_DEPENDENCIES := service-installer-for-AWS-Tanzu-with-Dependency.tar.gz
OUTPUT_DEPENDENCIES2 := service-installer-for-AWS-Tanzu.tar.gz


build-image: extract-docker
	$(DOCKER_EXEC) build --build-arg REGISTRY=$(REGISTRY) --build-arg IMAGEBUILDER_TAG=$(IMAGEBUILDER_TAG) -t $(REGISTRY)/tkg/bootstrap-ami-builder:$(IMAGEBUILDER_TAG) .


tkg-1click:
	@echo "***** Building tkg-1click $(TKG-1CLICK)..."
	mkdir -p airgap_deployment_binaries/tkg
	mkdir deployment_binaries
	cd $(TKG-1CLICK) && cd .. && tar -cvf sivt-aws-federal.tar sivt-aws-federal/ && tar -xvf sivt-aws-federal.tar --directory $(TKG-1CLICK)/build_web/airgap_deployment_binaries && rm -rf $(TKG-1CLICK)/build_web/airgap_deployment_binaries/sivt-aws-federal/.gitmodules  $(TKG-1CLICK)/build_web/airgap_deployment_binaries/sivt-aws-federal/.gitignore $(TKG-1CLICK)/build_web/airgap_deployment_binaries/sivt-aws-federal/.git && cp -r $(TKG-1CLICK)/build_web/airgap_deployment_binaries/* $(TKG-1CLICK)/build_web/deployment_binaries
	@echo "***** Completed tkg-1click $(TKG-1CLICK)..."

download-deps: tkg-1click
	@echo "***** Downloading dependencies********"
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(AIRGAPPED_CHILD)/other-files/$(OTHER_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(AIRGAPPED_CHILD)/$(TKG_1_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(AIRGAPPED_CHILD)/$(TKG_2_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(AIRGAPPED_CHILD)/$(TKG_3_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(AIRGAPPED_CHILD)/$(TKR_1_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(AIRGAPPED_CHILD)/$(TKR_2_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(NON_AIRGAPPED_CHILD)/$(NON_AIRGAPPED_FILE)
	tar -xvf $(NON_AIRGAPPED_FILE) --directory deployment_binaries
	cd deployment_binaries && cp -R image/* . && rm -rf image
	tar -czf $(OUTPUT_DEPENDENCIES2) deployment_binaries/
	rm -rf deployment_binaries
	cat $(TKG_1_FILE) $(TKG_2_FILE) $(TKG_3_FILE) | tar -xv --directory airgap_deployment_binaries
	cat $(TKR_1_FILE) $(TKR_2_FILE) | tar -xv --directory airgap_deployment_binaries
	tar -xvf $(OTHER_FILE) --directory airgap_deployment_binaries
	# move all binaries to
	rm -rf $(OTHER_FILE) $(TKG_1_FILE) $(TKG_2_FILE) $(TKG_3_FILE) $(TKR_1_FILE) $(TKR_2_FILE)
	cd airgap_deployment_binaries && cp -R other/* . && rm -rf other
	tar -czf $(OUTPUT_DEPENDENCIES) airgap_deployment_binaries/
	rm -rf airgap_deployment_binaries
	@echo "***** publishing completed successfully..."

publish: download-deps
	@echo "***** publishing deliverable to $(PUBLISH_DIR)"
	mkdir -p $(PUBLISH_DIR)/
	cp $(OUTPUT_DEPENDENCIES) $(PUBLISH_DIR)/
	cp $(OUTPUT_DEPENDENCIES2) $(PUBLISH_DIR)/
	@echo "***** publishing completed successfully..."

clean:
	@echo "***** Cleaning..."
	@echo $(UNAME)
	$(RM) -rf $(PUBLISH_DIR)/
	@echo "***** Cleaning completed successfully..."
