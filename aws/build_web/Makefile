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
AIRGAPPED_CHILD := new_dependencies_final
NON_AIRGAPPED_CHILD := non_airgapped
OTHER_FILE := other_new_1_5_3.tar
TKG_FILE  := tkg_final_new_1_5_3.tar
TKR_FILE := tkr_new_1_5_3.tar
NON_AIRGAPPED_FILE := tkg_non_airgapped.tar

OUTPUT_DEPENDENCIES := tkg_sivtAutomation_aws_airgap_1_5_3.tar
OUTPUT_DEPENDENCIES1 := tkg_tkr_aws_airgap_dependency_1_5_3.tar
OUTPUT_DEPENDENCIES2 := tkg_sivtAutomation_aws_non_airgap_1_5_3.tar

build-image: extract-docker
	$(DOCKER_EXEC) build --build-arg REGISTRY=$(REGISTRY) --build-arg IMAGEBUILDER_TAG=$(IMAGEBUILDER_TAG) -t $(REGISTRY)/tkg/bootstrap-ami-builder:$(IMAGEBUILDER_TAG) .


tkg-1click:
	@echo "***** Building tkg-1click $(TKG-1CLICK)..."
	mkdir airgap_deployment_binaries
	mkdir deployment_binaries
	cd $(TKG-1CLICK) && cd .. && tar -cvf sivt-aws-federal.tar sivt-aws-federal/ && tar -xvf sivt-aws-federal.tar --directory $(TKG-1CLICK)/build_web/airgap_deployment_binaries && rm -rf $(TKG-1CLICK)/build_web/airgap_deployment_binaries/sivt-aws-federal/.gitmodules  $(TKG-1CLICK)/build_web/airgap_deployment_binaries/sivt-aws-federal/.gitignore $(TKG-1CLICK)/build_web/airgap_deployment_binaries/sivt-aws-federal/.git && cp -r $(TKG-1CLICK)/build_web/airgap_deployment_binaries/* $(TKG-1CLICK)/build_web/deployment_binaries
	@echo "***** Completed tkg-1click $(TKG-1CLICK)..."

download-deps: tkg-1click
	@echo "***** Downloading dependencies********"
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(BASE)/$(AIRGAPPED_CHILD)/$(OTHER_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(BASE)/$(AIRGAPPED_CHILD)/$(TKG_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(BASE)/$(AIRGAPPED_CHILD)/$(TKR_FILE)
	wget https://build-artifactory.eng.vmware.com/artifactory/tko_dependencies-generic-local/$(BASE)/$(NON_AIRGAPPED_CHILD)/$(NON_AIRGAPPED_FILE)
	tar -xvf $(NON_AIRGAPPED_FILE) --directory deployment_binaries
	cd deployment_binaries && cp -R image/* . && rm -rf image
	tar -cvf $(OUTPUT_DEPENDENCIES2) deployment_binaries/
	tar -xvf $(TKG_FILE) --directory airgap_deployment_binaries
	tar -xvf $(TKR_FILE) --directory airgap_deployment_binaries
	tar -cvf $(OUTPUT_DEPENDENCIES1) airgap_deployment_binaries/
	tar -xvf $(OTHER_FILE) --directory airgap_deployment_binaries
	rm -rf $(OTHER_FILE) $(TKG_FILE) $(TKR_FILE)
	cd airgap_deployment_binaries && cp -R other/* . && rm -rf other
	tar -cvf $(OUTPUT_DEPENDENCIES) airgap_deployment_binaries/
	rm -rf airgap_deployment_binaries
	@echo "***** publishing completed successfully..."

publish: download-deps
	@echo "***** publishing deliverable to $(PUBLISH_DIR)"
	mkdir -p $(PUBLISH_DIR)/
	cp $(OUTPUT_DEPENDENCIES) $(PUBLISH_DIR)/
	cp $(OUTPUT_DEPENDENCIES1) $(PUBLISH_DIR)/
	cp $(OUTPUT_DEPENDENCIES2) $(PUBLISH_DIR)/
	cp $(TKG-1CLICK)/build_web/AWSFederalAirgap-DeploymentGuide.md $(PUBLISH_DIR)/
	cp $(TKG-1CLICK)/build_web/ReleaseNotes.md $(PUBLISH_DIR)/
	@echo "***** publishing completed successfully..."

clean:
	@echo "***** Cleaning..."
	@echo $(UNAME)
	$(RM) -rf $(PUBLISH_DIR)/
	@echo "***** Cleaning completed successfully..."
