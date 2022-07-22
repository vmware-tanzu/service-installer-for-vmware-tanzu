# Ensure Make is run with bash shell as some syntax below is bash-specific
SHELL := /usr/bin/env bash

.DEFAULT_GOAL := help
# this need to be set by user, if needs modification and documentation also needs to be updated or may be each SIVT release
imagebuilder_repo ?= TKG-Image-Builder-for-Kubernetes-v1.22.8-on-TKG-v1.5.3
hardening_role = canonical-ubuntu-18.04-lts-stig-hardening
IMAGEBUILDER_TAG ?= v0.1.11_vmware.3
REGISTRY ?= projects.registry.vmware.com
TKR_VERSION ?= v1.21.2

## -------------11-------------------------
## Help
## --------------------------------------
##@ Helpers
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-27s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: fetch-git
fetch-git:
	rm -fr $(imagebuilder_repo) tkg-imagebuilder
	mkdir -p tkg-imagebuilder/tkg
	git clone https://github.com/vmwarecode/$(imagebuilder_repo).git
	cp -r $(imagebuilder_repo)/*/** tkg-imagebuilder

.PHONY: fetch-s3
fetch-s3:
	@[ "${BUCKET_NAME}" ] || ( echo ">> BUCKET_NAME is not set"; exit 1 )
	echo "fetching data from s3 bucket for STIG AMI building...."
	rm -fr tkg-imagebuilder
	mkdir -p tkg-imagebuilder
	aws s3 cp s3://${BUCKET_NAME}/tkr/tkr-${TKR_VERSION}/tkg tkg-imagebuilder/tkg --recursive
	aws s3 cp s3://${BUCKET_NAME}/tkr/tkr-${TKR_VERSION}/tkg.json tkg-imagebuilder/tkg.json
	aws s3 cp s3://${BUCKET_NAME}/tkr/tkr-${TKR_VERSION}/ubuntu-goss.yml tkg-imagebuilder/ubuntu-goss.yml
	aws s3 cp s3://${BUCKET_NAME}/tkr/tkr-${TKR_VERSION}/amazon-goss.yml tkg-imagebuilder/amazon-goss.yml

.PHONY: build-ubuntu-ami-online
build-ubuntu-ami-online:
	echo "building ubuntu based node OS online ami using docker and packer module...."
	# update roles only when Compliant sets to true
	if [[ "${COMPLIANT_DEPLOYMENT}" == "true" ]]; then \
  		echo "updating custom STIG roles"; \
		sed -i.bak "s/\"custom_role_names\":.*/\"custom_role_names\": \"\\\\\"\/home\/imagebuilder\/$(hardening_role) \/home\/imagebuilder\/tkg\\\\\"\",/g" tkg-imagebuilder/tkg.json; \
	fi
	sudo --preserve-env docker build --build-arg REGISTRY=$(REGISTRY) --build-arg IMAGEBUILDER_TAG=$(IMAGEBUILDER_TAG) -t $(REGISTRY)/tkg/stig-ami-builder:$(IMAGEBUILDER_TAG) .
	rm -fr $(imagebuilder_repo)
	sudo --preserve-env docker run --net host -it --rm --name stig-ami-builder \
		-e AWS_DEFAULT_REGION \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SESSION_TOKEN \
		-e UBUNTU_ADVANTAGE_PASSWORD \
		-e UBUNTU_ADVANTAGE_PASSWORD_UPDATES \
		-e PACKER_VAR_FILES='/home/imagebuilder/aws_settings.json /home/imagebuilder/tkg.json' \
		-v $(PWD)/aws_settings.json:/home/imagebuilder/aws_settings.json:Z \
		-v $(PWD)/tkg-imagebuilder/ubuntu-goss.yml:/home/imagebuilder/goss/goss.yaml:Z \
		"$(REGISTRY)/tkg/stig-ami-builder:$(IMAGEBUILDER_TAG)" \
		build-ami-ubuntu-1804

copy-ubuntu-aws-goss:
	cp tkg-imagebuilder/goss/amazon-ubuntu-*-goss-spec.yaml tkg-imagebuilder/ubuntu-goss.yml
copy-azure-goss:
	cp $(imagebuilder_repo)/$(imagebuilder_repo)/goss/azure-ubuntu-*-goss-spec.yaml  tkg-imagebuilder/goss.yml

.PHONY: ubuntu-stig-ami-online
ubuntu-stig-ami-online: fetch-git copy-ubuntu-aws-goss build-ubuntu-ami-online  ## Build ubuntu STIG hardened AMI

.PHONY: docker-aws-with-s3
docker-aws-with-s3: fetch-s3 create-ami  ## Build AMI fetching tkg and goss from s3


.PHONY: docker-run
docker-aws-offline: fetch-s3 ## Build AMI in air-gapped environment
docker-aws-offline: export KUBERNETES_SEMVER=$(shell cat tkg-imagebuilder/tkg.json |jq -r .kubernetes_semver | sed -e 's/+/\%2B/g')
docker-aws-offline: export KUBERNETES_CNI_SEMVER=$(shell cat tkg-imagebuilder/tkg.json |jq -r .kubernetes_cni_semver | sed -e 's/+/\%2B/g')
docker-aws-offline: export PAUSE_TAG=$(shell cat tkg-imagebuilder/tkg.json | jq -r .pause_image | cut -d ":" -f2)
docker-aws-offline:
	envsubst < local.list.txt > local.list
	sed -i.bak "s/\"custom_role_names\":.*/\"custom_role_names\": \"\\\\\"\/home\/imagebuilder\/$(hardening_role) \/home\/imagebuilder\/tkg\\\\\"\",/g" tkg-imagebuilder/tkg.json
	echo "building offline STIG AMI using docker and packer module...."
	sudo --preserve-env docker build --build-arg REGISTRY=$(REGISTRY) --build-arg IMAGEBUILDER_TAG=$(IMAGEBUILDER_TAG) -t $(REGISTRY)/tkg/stig-ami-builder:$(IMAGEBUILDER_TAG) .
	sudo --preserve-env docker run --net host -it --rm --name stig-ami-builder \
		-e DEBUG \
		-e AWS_DEFAULT_REGION \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SESSION_TOKEN \
		-e OFFLINE_INSTALL=yes \
		-e KUBERNETES_SEMVER \
		-e KUBERNETES_CNI_SEMVER \
		-e PAUSE_TAG \
		-e VPC_ID \
		-e SUBNET_ID \
		-e BUCKET_NAME \
		-e TKR_VERSION \
		-e REGISTRY \
		-e PACKER_VAR_FILES='/home/imagebuilder/aws_settings.json /home/imagebuilder/tkg.json /home/imagebuilder/tkg_offline.json' \
		-v $(PWD)/local.list:/home/imagebuilder/local.list:Z \
		-v $(PWD)/tkg_offline.json:/home/imagebuilder/tkg_offline.json:Z \
		-v $(PWD)/aws_settings_offline.json:/home/imagebuilder/aws_settings.json:Z \
		-v $(PWD)/roles/canonical-ubuntu-18.04-lts-stig-hardening/files/ca:/home/imagebuilder/canonical-ubuntu-18.04-lts-stig-hardening/files/ca/:Z \
		-v $(PWD)/patch/volume_gp2_supported_packer.json:/home/imagebuilder/packer/ami/packer.json:Z \
		-v $(PWD)/tkg-imagebuilder/ubuntu-goss.yml:/home/imagebuilder/goss/goss.yaml:Z \
		"$(REGISTRY)/tkg/stig-ami-builder:$(IMAGEBUILDER_TAG)" \
		build-ami-ubuntu-1804

setup-azure:
	@[ "${AZURE_SUBSCRIPTION_ID}" ] || ( echo ">> AZURE_SUBSCRIPTION_ID is not set"; exit 1 )
	@[ "${AZURE_TENANT_ID}" ] || ( echo ">> AZURE_TENANT_ID is not set"; exit 1 )
	@[ "${AZURE_CLIENT_ID}" ] || ( echo ">> AZURE_CLIENT_ID is not set"; exit 1 )
	@[ "${AZURE_CLIENT_SECRET}" ] || ( echo ">> AZURE_CLIENT_SECRET is not set"; exit 1 )
	sed -i.bak "s/\"custom_role_names\":.*/\"custom_role_names\": \"\\\\\"\/home\/imagebuilder\/$(hardening_role) \/home\/imagebuilder\/tkg\\\\\"\",/g" tkg-imagebuilder/tkg.json
	envsubst < azure-creds.env.txt > azure-creds.env
	docker build --build-arg REGISTRY=$(REGISTRY) --build-arg IMAGEBUILDER_TAG=$(IMAGEBUILDER_TAG) -t $(REGISTRY)/tkg/stig-vhd-builder:$(IMAGEBUILDER_TAG) .
	rm -fr $(imagebuilder_repo) tkg-imagebuilder

create-vhd: setup-azure
	docker run --net host -it --rm --name stig-vhd-builder \
		-e UBUNTU_ADVANTAGE_PASSWORD \
		-e UBUNTU_ADVANTAGE_PASSWORD_UPDATES \
		-e PACKER_VAR_FILES='/home/imagebuilder/azure_settings.json /home/imagebuilder/tkg.json' \
		-v $(PWD)/azure_settings.json:/home/imagebuilder/azure_settings.json:Z \
		--env-file azure-creds.env \
		"$(REGISTRY)/tkg/stig-vhd-builder:$(IMAGEBUILDER_TAG)" \
		build-azure-sig-ubuntu-1804

create-vhd-gen2: setup-azure
	docker run --net host -it --rm --name stig-vhd-builder \
		-e UBUNTU_ADVANTAGE_PASSWORD \
		-e UBUNTU_ADVANTAGE_PASSWORD_UPDATES \
		-e PACKER_VAR_FILES='/home/imagebuilder/azure_settings.json /home/imagebuilder/tkg.json' \
		-v $(PWD)/azure_settings.json:/home/imagebuilder/azure_settings.json:Z \
		--env-file azure-creds.env \
		"$(REGISTRY)/tkg/stig-vhd-builder:$(IMAGEBUILDER_TAG)" \
		build-azure-sig-ubuntu-1804-gen2

.PHONY: docker-azure
docker-azure: fetch-git copy-azure-goss create-vhd ## Build Azure Image Definition

.PHONY: docker-azure-gen2
docker-azure-gen2: fetch-git copy-azure-goss create-vhd-gen2 ## Build Azure Image Definition gen2

.PHONY: build-amazon-linux2-node-ami
build-amazon-linux2-node-ami: fetch-s3 ## Build amazon linux 2 AMI for node OS's in air-gapped environment
build-amazon-linux2-node-ami: export KUBERNETES_SEMVER=$(shell cat tkg-imagebuilder/tkg.json |jq -r .kubernetes_semver | sed -e 's/+/\%2B/g')
build-amazon-linux2-node-ami: export KUBERNETES_CNI_SEMVER=$(shell cat tkg-imagebuilder/tkg.json |jq -r .kubernetes_cni_semver | sed -e 's/+/\%2B/g')
build-amazon-linux2-node-ami: export PAUSE_TAG=$(shell cat tkg-imagebuilder/tkg.json | jq -r .pause_image | cut -d ":" -f2)
build-amazon-linux2-node-ami:
	#to support gp2 volume type overriding packer json with -v tag, as well as amazon goss yaml needed for verification
	sudo --preserve-env docker build --build-arg goss_yml=tkg-imagebuilder/amazon-goss.yml --build-arg REGISTRY=$(REGISTRY) --build-arg IMAGEBUILDER_TAG=$(IMAGEBUILDER_TAG) -t $(REGISTRY)/tkg/amazon-linux-2-ami-builder:$(IMAGEBUILDER_TAG) .
	sudo --preserve-env docker run --net host -it --rm --name stig-ami-builder \
		-e DEBUG \
		-e AWS_DEFAULT_REGION \
		-e AWS_SECRET_ACCESS_KEY \
		-e AWS_ACCESS_KEY_ID \
		-e AWS_SESSION_TOKEN \
		-e OFFLINE_INSTALL=yes \
		-e KUBERNETES_SEMVER \
		-e KUBERNETES_CNI_SEMVER \
		-e PAUSE_TAG \
		-e VPC_ID \
		-e SUBNET_ID \
		-e BUCKET_NAME \
		-e TKR_VERSION \
		-e REGISTRY \
		-e PACKER_VAR_FILES='/home/imagebuilder/aws_settings.json /home/imagebuilder/tkg.json /home/imagebuilder/tkg_offline.json' \
		-v $(PWD)/tkg_offline.json:/home/imagebuilder/tkg_offline.json:Z \
		-v $(PWD)/aws_amazon_2_settings_offline.json:/home/imagebuilder/aws_settings.json:Z \
		-v $(PWD)/patch/volume_gp2_supported_packer.json:/home/imagebuilder/packer/ami/packer.json:Z \
		-v $(PWD)/tkg-imagebuilder/amazon-goss.yml:/home/imagebuilder/goss/goss.yaml:Z \
		"$(REGISTRY)/tkg/amazon-linux-2-ami-builder:$(IMAGEBUILDER_TAG)" \
		build-ami-amazon-2
