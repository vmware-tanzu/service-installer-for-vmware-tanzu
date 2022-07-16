# Ensure Make is run with bash shell as some syntax below is bash-specific
SHELL := /usr/bin/env bash

.DEFAULT_GOAL := help
SSH_USER ?= ubuntu
IMAGEBUILDER_TAG ?= v0.1.11_vmware.3
REGISTRY ?= projects.registry.vmware.com
TKR_VERSION ?= v1.21.2
TKG_VERSION ?= v1.4.0

export SSH_USER
ABSOLUTE_PACKER_VAR_FILES := $(foreach f,$(abspath $(PACKER_VAR_FILES)),-var-file="$(f)" )

##@ help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-27s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
.PHONY: fetch-s3-and-build
fetch-s3-and-build:
	@[ "${BUCKET_NAME}" ] || ( echo ">> BUCKET_NAME is not set"; exit 1 )
	echo "fetching data from s3 bucket for bootstrap AMI building...."
	rm -fr tkg-imagebuilder
	mkdir -p tkg-imagebuilder
	aws s3 cp s3://${BUCKET_NAME}/tkg/tkg-${TKG_VERSION}/tanzu.tar tkg-imagebuilder/tanzu.tar
	aws s3 cp s3://${BUCKET_NAME}/tkr/tkr-${TKR_VERSION}/kubectl.gz tkg-imagebuilder/kubectl.gz
	aws s3 cp s3://${BUCKET_NAME}/kind/kind tkg-imagebuilder
	aws s3 cp s3://${BUCKET_NAME}/yq tkg-imagebuilder
	sudo --preserve-env docker build --build-arg REGISTRY=$(REGISTRY) --build-arg IMAGEBUILDER_TAG=$(IMAGEBUILDER_TAG) -t $(REGISTRY)/tkg/bootstrap-ami-builder:$(IMAGEBUILDER_TAG) .
	rm -fr tkg-imagebuilder

## --------------------------------------
## Build AMI
## --------------------------------------
##@ Build AMI
.PHONY: build-ubuntu-online
build-ubuntu-online: fetch-s3-and-build ## Build ubuntu OS AMI online
	echo "building ubuntu based bootstrap online ami using docker and packer module...."
	sudo --preserve-env docker run --net host --rm --name bootstrap-ami-builder \
		-e AWS_DEFAULT_REGION \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SESSION_TOKEN \
		-e TKG_VERSION \
		-e TKR_VERSION \
		-e COMPLIANT_DEPLOYMENT \
		-e PACKER_VAR_FILES='/home/imagebuilder/user.json' \
		-v $(PWD)/user.json:/home/imagebuilder/user.json \
		$(REGISTRY)/tkg/bootstrap-ami-builder:$(IMAGEBUILDER_TAG) \
		build-ubuntu-1804

.PHONY: build-ami-offline
build-ami-offline: fetch-s3-and-build ## Build AMI in air-gapped environment
	@[ "${VPC_ID}" ] || ( echo ">> VPC_ID is not set"; exit 1 )
	@[ "${SUBNET_ID}" ] || ( echo ">> SUBNET_ID is not set"; exit 1 )
	echo "building ubuntu based bootstrap offline ami using docker and packer module...."
	envsubst < local.list.txt > local.list
	 #to support gp2 volume type overriding packer json with -v tag
	sudo --preserve-env docker run --net host --rm --name bootstrap-ami-builder \
		-e VPC_ID \
		-e SUBNET_ID \
		-e TKG_VERSION \
		-e TKR_VERSION \
		-e REGISTRY \
		-e AWS_DEFAULT_REGION \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SESSION_TOKEN \
		-e BUCKET_NAME \
		-e PACKER_VAR_FILES='/home/imagebuilder/user.json' \
		-v $(PWD)/local.list:/home/imagebuilder/local.list \
		-v $(PWD)/roles/bootstrap/files/ca:/home/imagebuilder/roles/bootstrap/files/ca \
		-v $(PWD)/user_offline.json:/home/imagebuilder/user.json \
		-v $(PWD)/patch/volume_gp2_supported_packer.json:/home/imagebuilder/packer/packer.json \
		$(REGISTRY)/tkg/bootstrap-ami-builder:$(IMAGEBUILDER_TAG) \
		build-ubuntu-1804

.PHONY: build-amazon-linux2-bootstrap-ami
build-amazon-linux2-bootstrap-ami: fetch-s3-and-build ## Build amazon linux 2 AMI in air-gaped environment
	@[ "${VPC_ID}" ] || ( echo ">> VPC_ID is not set"; exit 1 )
	@[ "${SUBNET_ID}" ] || ( echo ">> SUBNET_ID is not set"; exit 1 )
	echo "building amazon linux 2 based bootstrap offline ami using docker and packer module...."
	sudo --preserve-env docker run --net host --rm --name bootstrap-ami-builder \
		-e VPC_ID \
		-e SUBNET_ID \
		-e TKG_VERSION \
		-e TKR_VERSION \
		-e REGISTRY \
		-e AWS_DEFAULT_REGION \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SESSION_TOKEN \
		-e BUCKET_NAME \
		-e PACKER_VAR_FILES='/home/imagebuilder/user.json' \
		-v $(PWD)/local.list:/home/imagebuilder/local.list \
		-v $(PWD)/roles/bootstrap/files/ca:/home/imagebuilder/roles/bootstrap/files/ca \
		-v $(PWD)/amazon_linux_2_offline.json:/home/imagebuilder/user.json \
		-v $(PWD)/patch/volume_gp2_supported_packer.json:/home/imagebuilder/packer/packer.json \
		$(REGISTRY)/tkg/bootstrap-ami-builder:$(IMAGEBUILDER_TAG) \
		build-amazon-bootstrap

build-amazon-bootstrap:
	echo "calling packer module for ami generation...."
	packer build $(ABSOLUTE_PACKER_VAR_FILES) -var-file=packer/amazon-linux-2.json -var-file=packer/ansible.json packer/packer.json

build-ubuntu-1804:
	echo "calling packer module for ami generation...."
	packer build $(ABSOLUTE_PACKER_VAR_FILES) -var-file=packer/ubuntu-1804.json -var-file=packer/ansible.json packer/packer.json
