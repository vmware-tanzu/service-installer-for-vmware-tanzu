# Ensure Make is run with bash shell as some syntax below is bash-specific
SHELL := /usr/bin/env bash
IMAGEBUILDER_TAG ?= v0.1.11_vmware.3
REGISTRY_CA_FILENAME ?= ca.crt
FIPS_ENABLED ?= true
CONTOUR_DEPLOYMENT ?= true
CERT_MANAGER_DEPLOYMENT ?= true
ENABLE_IDENTITY_MANAGEMENT ?= "false"
COMPLIANT_DEPLOYMENT ?= true
SKIP_TO ?= false
SKIP_TSM ?= false
export REGISTRY_CA_FILENAME
export IMAGEBUILDER_TAG
export COMPLIANT_DEPLOYMENT
export TF_VAR_bucket_name=$(BUCKET_NAME)
export TF_VAR_vpc_id=$(VPC_ID)
export TF_VAR_subnet_id=$(SUBNET_ID)
export TF_VAR_region=$(AWS_DEFAULT_REGION)
export TF_VAR_tkg_version=$(TKG_VERSION)
export TF_VAR_tkr_version=$(TKR_VERSION)
export TF_VAR_registry_ca_filename=$(REGISTRY_CA_FILENAME)
export TF_VAR_ssh_key_name=$(SSH_KEY_NAME)
export TF_VAR_az_zone=$(AWS_AZ_ZONE)
export TF_VAR_harbor_host_name=$(HARBOR_HOST_NAME)
export TF_VAR_prometheus_host_name=$(PROMETHEUS_HOST_NAME)
export TF_VAR_grafana_host_name=$(GRAFANA_HOST_NAME)
export TF_VAR_harbor_extension_password=$(HARBOR_EXTENSION_PASSWORD)
export TF_VAR_enable_identity_management=$(ENABLE_IDENTITY_MANAGEMENT)
export TF_VAR_identity_management_type=$(IDENTITY_MANAGEMENT_TYPE)
export TF_VAR_ldap_host=$(LDAP_HOST)
export TF_VAR_ldap_user_search_base_dn=$(LDAP_USER_SEARCH_BASE_DN)
export TF_VAR_ldap_group_search_base_dn=$(LDAP_GROUP_SEARCH_BASE_DN)
export TF_VAR_fips_enabled=$(FIPS_ENABLED)
export TF_VAR_oidc_identity_provider_client_id=$(OIDC_IDENTITY_PROVIDER_CLIENT_ID)
export TF_VAR_oidc_identity_provider_client_secret=$(OIDC_IDENTITY_PROVIDER_CLIENT_SECRET)
export TF_VAR_oidc_identity_provider_groups_claim=$(OIDC_IDENTITY_PROVIDER_GROUPS_CLAIM)
export TF_VAR_oidc_identity_provider_issuer_url=$(OIDC_IDENTITY_PROVIDER_ISSUER_URL)
export TF_VAR_oidc_identity_provider_scopes=$(OIDC_IDENTITY_PROVIDER_SCOPES)
export TF_VAR_oidc_identity_provider_username_claim=$(OIDC_IDENTITY_PROVIDER_USERNAME_CLAIM)
export TF_VAR_harbor_deployment=$(HARBOR_DEPLOYMENT)
export TF_VAR_prometheus_deployment=$(PROMETHEUS_DEPLOYMENT)
export TF_VAR_grafana_deployment=$(GRAFANA_DEPLOYMENT)
export TF_VAR_fluent_bit_deployment=$(FLUENT_BIT_DEPLOYMENT)
export TF_VAR_contour_deployment=$(CONTOUR_DEPLOYMENT)
export TF_VAR_cert_manager_deployment=$(CERT_MANAGER_DEPLOYMENT)
export TF_VAR_compliant_deployment=$(COMPLIANT_DEPLOYMENT)
export AWS_STS_REGIONAL_ENDPOINTS=regional
export TF_VAR_tmc_api_token=$(TMC_API_TOKEN)
export TF_VAR_to_token=$(TO_TOKEN)
export TF_VAR_to_url=$(TO_URL)
export TF_VAR_skip_to=$(SKIP_TO)
export TF_VAR_skip_tsm=$(SKIP_TSM)
.DEFAULT_GOAL := help
## --------------------------------------------------------------------------------------------------------
## verify that user has supplied corrects inputs as environment variables
## --------------------------------------------------------------------------------------------------------
##@ verify that user has supplied corrects inputs as environment variables
.PHONY: verify-aws-credentials
verify-aws-credentials: ## check aws credentials has been exported.
	@[ "${AWS_ACCESS_KEY_ID}" ] || ( echo ">> Please specify AWS Access Key ID from your AWS credentials, environment variable named {AWS_ACCESS_KEY_ID}"; exit 1 )
	@[ "${AWS_SECRET_ACCESS_KEY}" ] || ( echo ">> Please specify AWS Secret Access Key from your AWS credentials, environment variable named {AWS_SECRET_ACCESS_KEY}"; exit 1 )
	@[ "${AWS_SESSION_TOKEN}" ] || ( echo ">> IF you are using cloudgate or other tool for AWS login, environment variable named {AWS_SESSION_TOKEN}"; export AWS_SESSION_TOKEN='')


.PHONY: verify-pinniped-credentials
verify-pinniped-credentials: ## Check credentials for pinniped integration
	@echo "checking user exported inputs for Pinniped integration"
ifeq ($(ENABLE_IDENTITY_MANAGEMENT), true)
ifeq ($(IDENTITY_MANAGEMENT_TYPE), ldap)
	@[ "${LDAP_HOST}" ] || ( echo ">> Please specify the LDAP host, with environment variable {LDAP_HOST}"; exit 1 )
	@[ "${LDAP_USER_SEARCH_BASE_DN}" ] || ( echo ">> Please specify the LDAP User Search DN, with environment variable {LDAP_USER_SEARCH_BASE_DN}"; exit 1 )
	@[ "${LDAP_GROUP_SEARCH_BASE_DN}" ] || ( echo ">> Please specify the LDAP Group Search Base DN, with environment variable {LDAP_GROUP_SEARCH_BASE_DN}"; exit 1 )
else ifeq ($(IDENTITY_MANAGEMENT_TYPE), oidc)
	@[ "${OIDC_IDENTITY_PROVIDER_CLIENT_ID}" ] || ( echo ">> Please specify OIDC provider client ID, environment variable named {OIDC_IDENTITY_PROVIDER_CLIENT_ID}"; exit 1 )
	@[ "${OIDC_IDENTITY_PROVIDER_CLIENT_SECRET}" ] || ( echo ">> Please specify OIDC provider client secret, environment variable named {OIDC_IDENTITY_PROVIDER_CLIENT_SECRET}"; exit 1 )
	@[ "${OIDC_IDENTITY_PROVIDER_GROUPS_CLAIM}" ] || ( echo ">> Please specify OIDC provider groups claim, environment variable named {OIDC_IDENTITY_PROVIDER_GROUPS_CLAIM}"; exit 1 )
	@[ "${OIDC_IDENTITY_PROVIDER_ISSUER_URL}" ] || ( echo ">> Please specify OIDC provider issuer URL, environment variable named {OIDC_IDENTITY_PROVIDER_ISSUER_URL}"; exit 1 )
	@[ "${OIDC_IDENTITY_PROVIDER_SCOPES}" ] || ( echo ">> Please specify OIDC provider scopes, environment variable named {OIDC_IDENTITY_PROVIDER_SCOPES}"; exit 1 )
	@[ "${OIDC_IDENTITY_PROVIDER_USERNAME_CLAIM}" ] || ( echo ">> Please specify OIDC provider udername claim, environment variable named {OIDC_IDENTITY_PROVIDER_USERNAME_CLAIM}"; exit 1 )
else
	@echo "Pinniped is enabled but wrong identity management type provided. Please provide oidc or ldap for {IDENTITY_MANAGEMENT_TYPE} environment variable"; exit 1
endif
else
	@echo "Pinniped is not enabled. Hence, skipping pinniped credential validation"
endif
## --------------------------------------------------------------------------------------------------------
## verify that user has supplied all the inputs as environment variables for running complete deployments
## --------------------------------------------------------------------------------------------------------
.PHONY: verify-all-inputs
verify-all-inputs: verify-aws-credentials verify-pinniped-credentials ## check user supplied inputs
	echo "checking users exported inputs before running installation"
	@[ "${BUCKET_NAME}" ] || ( echo ">> Please specify S3 bucket name for dependency download, with environment variable {BUCKET_NAME}"; exit 1 ) # will be removed once the TAR Ball is ready
	@[ "${VPC_ID}" ] || ( echo ">> Please specify VPC ID for installation, with environment variable {VPC_ID}"; exit 1 )
	@[ "${SUBNET_ID}" ] || ( echo ">> Please specify private Subnet ID for installation, with environment variable {SUBNET_ID}"; exit 1 )
	@[ "${AWS_DEFAULT_REGION}" ] || ( echo ">> Please specify AWS region for installation, with environment variable {AWS_DEFAULT_REGION}"; exit 1 )
	@[ "${TKG_VERSION}" ] || ( echo ">> Please specify TKG version for installation, with environment variable {TKG_VERSION}"; exit 1 )
	@[ "${TKR_VERSION}" ] || ( echo ">> Please specify TKR version for installation,, with environment variable {TKR_VERSION}"; exit 1 )
	@[ "${SSH_KEY_NAME}" ] || ( echo ">>  Please specify AWS ssh key pair name for installation, with environment variable {SSH_KEY_NAME}"; exit 1 )
	@[ "${AWS_AZ_ZONE}" ] || ( echo ">>Please specify AWS zone name for installation,, with environment variable {AWS_AZ_ZONE}"; exit 1 )
.PHONY: verify-non-airgap-inputs
verify-non-airgap-inputs: verify-aws-credentials verify-pinniped-credentials ## check user supplied inputs for non-airgap environment
verify-non-airgap-inputs:
	echo "checking users exported inputs before running installation"
	@[ "${BUCKET_NAME}" ] || ( echo ">> Please specify S3 bucket name for dependency download, with environment variable {BUCKET_NAME}"; exit 1 ) # will be removed once the TAR Ball is ready
	@[ "${AWS_DEFAULT_REGION}" ] || ( echo ">> Please specify AWS region for installation, with environment variable {AWS_DEFAULT_REGION}"; exit 1 )
	@[ "${TKG_VERSION}" ] || ( echo ">> Please specify TKG version for installation, with environment variable {TKG_VERSION}"; exit 1 )
	@[ "${TKR_VERSION}" ] || ( echo ">> Please specify TKR version for installation,, with environment variable {TKR_VERSION}"; exit 1 )
	@[ "${SSH_KEY_NAME}" ] || ( echo ">>  Please specify AWS ssh key pair name for installation, with environment variable {SSH_KEY_NAME}"; exit 1 )

##@ help
help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-27s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

## --------------------------------------
## Prechecks
## --------------------------------------
##@ Prechecks

.PHONY: vpc-endpoints-prechecks
vpc-endpoints-prechecks: ## Check if all the required endpoints are attached to airgap VPC
	@echo "Performing pre-checks on provided VPC"
	chmod +x terraform/vpc-endpoints-prechecks.sh
	terraform/vpc-endpoints-prechecks.sh;

## --------------------------------------
## Build ubuntu AMI's for internet connected AWS
## --------------------------------------
##@ Build ubuntu based AMI's for internet connected AWS
.PHONY: build-ubuntu-node-ami-online
build-ubuntu-node-ami-online: export VPC_ID=$(shell cat ./terraform/terraform.tfvars | grep -w "management_vpc_id" | cut -d"=" -f2| sed 's/ //g' | sed 's/"//g')
build-ubuntu-node-ami-online: export SUBNET_ID=$(shell cat ./terraform/terraform.tfvars | grep -w "management_public_subnet_id_1" | cut -d"=" -f2| sed 's/ //g' | sed 's/"//g')
build-ubuntu-node-ami-online: ## build ubuntu based Node AMI online (non-airgap)
	cd ami/stig && make ubuntu-stig-ami-online && cd ../../
.PHONY: build-ubuntu-bootstrap-ami-online
build-ubuntu-bootstrap-ami-online: export VPC_ID=$(shell cat ./terraform/terraform.tfvars | grep -w "management_vpc_id" | cut -d"=" -f2| sed 's/ //g' | sed 's/"//g')
build-ubuntu-bootstrap-ami-online: export SUBNET_ID=$(shell cat ./terraform/terraform.tfvars | grep -w "management_public_subnet_id_1" | cut -d"=" -f2| sed 's/ //g' | sed 's/"//g')
build-ubuntu-bootstrap-ami-online: ## build ubuntu based bootstrap AMI online (non-airgap)
	cd ami/tkg-bootstrap && make build-ubuntu-online && cd ../../
.PHONY:all-ubuntu-ami-non-airgapped
all-ubuntu-ami-non-airgapped: build-ubuntu-bootstrap-ami-online build-ubuntu-node-ami-online ## build ubuntu based online AMI's for non-airgap env
## --------------------------------------
## Build AMI Offline
## --------------------------------------
##@ Build AMI offline
.PHONY: full-stig-ami-offline
build-stig-ami-offline: setup-registry-ca stig-ami-offline ## build-stig-ami and place certs

stig-ami-offline: export REGISTRY=$(shell cat registry.txt)
stig-ami-offline: ## build STIG ami
	# we need this in same line with && if any of the command failed code needs to stop.
	echo "building node os ami and hardening it with STIG compliance....."
	cd ami/stig && make docker-aws-offline && cd ..

.PHONY: build-tkg-bootstrap-ami-offline
build-tkg-bootstrap-ami-offline: setup-registry-ca tkg-bootstrap-ami-offline ## build-tkg-bootstrap-ami-offline

tkg-bootstrap-ami-offline: export REGISTRY=$(shell cat registry.txt)
tkg-bootstrap-ami-offline:  ## Build bootstrap ami
	# we need this in same line with && if any of the command failed code needs to stop.
	echo "building bootstrap ami....."
	cd ami/tkg-bootstrap && make build-ami-offline && cd ../../

.PHONY: all-ami-offline
all-ami-offline: setup-registry-ca tkg-bootstrap-ami-offline stig-ami-offline ## build-tkg-bootstrap-ami-offline build-stig-ami-offline

## --------------------------------------
## VPC
## --------------------------------------
##@ VPC
#.PHONY: create-vpc-subnets
#create-vpc-subnets:  ## Create VPC and subnets
#	echo "WARNING: Automation script currently supports VPC creation only on internet connected environment"
#	echo "Starting VPC creation"
#	@[ "${TF_VAR_bucket_name}" ] || ( echo ">> TF_VAR_bucket_name is not set"; exit 1 )
#	@[ "${TF_VAR_region}" ] || ( echo ">> TF_VAR_region is not set"; exit 1 )
#	pushd terraform-vpc; \
#		pwd; \
#		terraform init \
#			--backend \
#			--backend-config="bucket=${TF_VAR_bucket_name}" \
#			--backend-config="key=terraform/tkg-vpc" \
#			--backend-config="region=${TF_VAR_region}" \
#			--backend-config="azs=["${TF_VAR_region}a", "${TF_VAR_region}b", "${TF_VAR_region}c"]";\
#		terraform apply -auto-approve; \
#	popd
.PHONY: create-non-airgapped-multi-vpc-infra
create-non-airgapped-multi-vpc-infra:  ## Create Multiple VPC setup and subnets
	echo "Starting VPC creation for non-airgapped deployment"
	##remove existing data files
	rm -f terraform/terraform.tfvars
	chmod +x terraform-non-air-gapped-vpc/setup-vpc.sh
	terraform-non-air-gapped-vpc/setup-vpc.sh;

.PHONY: fetch-aws-infra-id
fetch-aws-infra-id:  ## fetch subnet, vpc id's needed for multiple VPC deployments
	echo "Fetching infra setup non-airgapped deployment"
	cd terraform-non-air-gapped-vpc; chmod +x fetch-values.sh ; bash fetch-values.sh;

.PHONY: destroy-multi-vpc-infra
destroy-multi-vpc-infra: ## Delete multiple vpc non-airgapped via terraform
	pushd terraform-non-air-gapped-vpc; \
		pwd; \
		terraform apply -destroy -auto-approve; \
	popd;
## --------------------------------------
## TKG
## --------------------------------------
##@ TKG
.PHONY: install
install: check-for-ca install-tkg ## Deploy bootstrap via terraform
install-tkg: export TF_VAR_bs_ami_id=$(shell aws ec2 describe-images --owner self  --filters "Name=name,Values=tkg-$$TKG_VERSION-$$TKR_VERSION*bootstrap-ubuntu-*" --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' --output text)
install-tkg: export TF_VAR_node_ami_id=$(shell aws ec2 describe-images --owner self  --filters "Name=name,Values=capa-ami-ubuntu-*-$$TKR_VERSION*" --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' --output text)
install-tkg: export TF_VAR_registry_name=$(shell cat registry.txt)
install-tkg:
	@[ "${TF_VAR_bucket_name}" ] || ( echo ">> TF_VAR_bucket_name is not set"; exit 1 )
	@[ "${TF_VAR_region}" ] || ( echo ">> TF_VAR_region is not set"; exit 1 )
	echo "running tkg bootstrap installer...."
	chmod +x terraform/setup-bootstrap.sh
	# run bootstrap setup inside terraform dir
	terraform/setup-bootstrap.sh;
.PHONY: install-ubuntu-non-airgap
install-ubuntu-non-airgap: export TF_VAR_bs_ami_id=$(shell aws ec2 describe-images --owner self  --filters "Name=name,Values=tkg-$$TKG_VERSION-$$TKR_VERSION*bootstrap-ubuntu-*" --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' --output text)
install-ubuntu-non-airgap: export TF_VAR_node_ami_id=$(shell aws ec2 describe-images --owner self  --filters "Name=name,Values=capa-ami-ubuntu-*-$$TKR_VERSION*" --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' --output text)
install-ubuntu-non-airgap: export TF_VAR_vpc_id=$(shell cat ./terraform/terraform.tfvars | grep -w "management_vpc_id" | cut -d"=" -f2| sed 's/ //g' | sed 's/"//g')
install-ubuntu-non-airgap: export TF_VAR_subnet_id=$(shell cat ./terraform/terraform.tfvars | grep -w "management_public_subnet_id_1" | cut -d"=" -f2| sed 's/ //g' | sed 's/"//g')
install-ubuntu-non-airgap: export TF_VAR_base_os_family=non-airgapped-ubuntu
install-ubuntu-non-airgap: ## Deploy TKG non-airgap bootstrap via terraform
	@[ "${TF_VAR_region}" ] || ( echo ">> TF_VAR_region is not set"; exit 1 )
	echo "running tkg bootstrap installer...."
	chmod +x terraform/setup-bootstrap.sh
	# run bootstrap setup inside terraform dir
	terraform/setup-bootstrap.sh;
.PHONY: destroy
destroy: export TF_VAR_bs_ami_id=destroy
destroy: export TF_VAR_node_ami_id=destroy
destroy: export TF_VAR_registry_name="destroy"
destroy:  ## Delete bootstrap via terraform
	pushd terraform; \
		pwd; \
		TF_VAR_registry_name="destroy" terraform apply -destroy -auto-approve; \
	popd
## --------------------------------------
## Harbor
## --------------------------------------
##@ Harbor
.PHONY: install-harbor
install-harbor:  ## Deploy harbor via terraform
	@[ "${TF_VAR_bucket_name}" ] || ( echo ">> TF_VAR_bucket_name is not set"; exit 1 )
	@[ "${TF_VAR_region}" ] || ( echo ">> TF_VAR_region is not set"; exit 1 )
	echo "running harbor installer...."
	# run harbor setup inside terraform harbor dir
	chmod +x terraform-harbor/setup-harbor.sh
	terraform-harbor/setup-harbor.sh;

.PHONY: destroy-harbor
destroy-harbor:  ## Delete harbor via terraform
	@[ "${BUCKET_NAME}" ] || ( echo ">> BUCKET_NAME is not set"; exit 1 )
	if [ -z $${USE_EXISTING_REGISTRY+x} ]; then \
		pushd terraform-harbor; \
			pwd; \
			terraform apply -destroy -auto-approve; \
		popd;\
		aws s3 rm s3://$(BUCKET_NAME)/harbor/ca.crt; \
	fi
## --------------------------------------
## Cloud Formation
## --------------------------------------
##@ Cloud Formation
.PHONY: cf
cf: ## Make Cloud Formation if it doesn't exist
	@[ "${BUCKET_NAME}" ] || ( echo ">> BUCKET_NAME is not set"; exit 1 )
	bash build-stack-with-cloud-formation.sh
#commenting for release 1.0
#.PHONY: cf-kms
#cf-kms: ## Make Cloud Formation with kms if it doesn't exist
#	@[ "${BUCKET_NAME}" ] || ( echo ">> BUCKET_NAME is not set"; exit 1 )
#	@[ "${S3_KMS_ARN}" ] || ( echo ">> S3_KMS_ARN is not set"; exit 1 )
#
#	if ! aws cloudformation describe-stacks --stack-name tkg-1click-vmware-com > /dev/null; then \
#		echo "Adding Cloud Formation for TKG 1 click with kms";\
#		aws cloudformation create-stack \
#			--stack-name tkg-1click-vmware-com  \
#			--template-body file://1clickiamtemplate-kms  \
#			--parameters ParameterKey=TKGBucketParameter,ParameterValue=$(BUCKET_NAME) ParameterKey=S3KMSArnParameter,ParameterValue=$(S3_KMS_ARN) \
#			--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM;\
#		echo "Waiting for stack to finish creating";\
#		aws cloudformation wait stack-create-complete --stack-name tkg-1click-vmware-com; \
#	else \
#		echo "Cloud Formation Already Exists";\
#	fi
## --------------------------------------
## Setup Registry Certificates
## --------------------------------------
##@ Setup Registry Certificates
.PHONY: setup-registry-ca
setup-registry-ca: check-for-ca-download setup-docker
check-for-ca: ## Check for CA
	@[ "${REGISTRY_CA_FILENAME}" ] || ( echo ">> REGISTRY_CA_FILENAME is not set"; exit 1 )
	REGISTRY_CA_FILENAME=$(REGISTRY_CA_FILENAME) source check-harbor-status.sh
check-for-ca-download: ## check for CA download
	@[ "${REGISTRY_CA_FILENAME}" ] || ( echo ">> REGISTRY_CA_FILENAME is not set"; exit 1 )
	REGISTRY_CA_FILENAME=$(REGISTRY_CA_FILENAME) source check-harbor-status.sh --download-ca
setup-docker: export REGISTRY=$(shell cat registry.txt)
setup-docker: ## setup docker
	@[ "${REGISTRY}" ] || ( echo ">> REGISTRY is not set"; exit 1 )
	@[ "${REGISTRY_CA_FILENAME}" ] || ( echo ">> REGISTRY_CA_FILENAME is not set"; exit 1 )
	echo "setting up docker with new cert and restarting it...."
	sudo mkdir -p /etc/docker/certs.d/$(REGISTRY)
	sudo cp ami/stig/roles/canonical-ubuntu-18.04-lts-stig-hardening/files/ca/$(REGISTRY_CA_FILENAME) /etc/docker/certs.d/$(REGISTRY)/$(REGISTRY_CA_FILENAME)
	sudo systemctl restart docker
## --------------------------------------
## 1Click
## --------------------------------------
##@ 1Click
#commenting for release 1.0
#.PHONY: all-no-iam
#all-no-iam: install-harbor all-ami-offline install ## End to End 1 click with no iam
.PHONY: all
all: verify-all-inputs vpc-endpoints-prechecks cf install-harbor check-for-ca-download setup-docker tkg-bootstrap-ami-offline stig-ami-offline install ## End to End 1 click, runs commands in this order - [verify-all-inputs cf install-harbor check-for-ca-download setup-docker tkg-bootstrap-ami-offline stig-ami-offline install]
.PHONY: non-airgapped-deployment-without-vpc
non-airgapped-deployment-without-vpc: verify-non-airgap-inputs cf build-ubuntu-bootstrap-ami-online build-ubuntu-node-ami-online install-ubuntu-non-airgap  ## build ubuntu based online AMI's for non-airgap env without creating vpc
.PHONY: non-airgapped-deployment-with-vpc
non-airgapped-deployment-with-vpc: verify-non-airgap-inputs create-non-airgapped-multi-vpc-infra fetch-aws-infra-id cf build-ubuntu-bootstrap-ami-online build-ubuntu-node-ami-online install-ubuntu-non-airgap ## build ubuntu based online AMI's for non-airgap env without creating vpc
.PHONY: destroy-all
destroy-all: destroy destroy-harbor ## Delete bootstrap And Harbor for Airgapped deployment
.PHONY: destroy-non-airgapped
destroy-non-airgapped: destroy destroy-multi-vpc-infra ## Delete Bootstrap machine and VPC for non-airgapped deployment
## --------------------------------------
## Dependency Management
## --------------------------------------
##@ Dependency Management
# 1.3 comment download-deps as its pointing to public s3 bucket which we don't support.
#.PHONY: download-deps
#download-deps: ## Download the dependencies from an env with internet
#	@[ "${TKG_VERSION}" ] || ( echo ">> TKG_VERSION is not set"; exit 1 )
#	@[ "${TKR_VERSION}" ] || ( echo ">> TKR_VERSION is not set"; exit 1 )
#	mkdir -p tkg-1click-dependencies
#	pushd tkg-1click-dependencies;\
#		mkdir -p tkg/tkg-$(TKG_VERSION);\
#		aws s3 cp s3://tkg-1click-dependencies/tkg/tkg-$(TKG_VERSION) tkg/tkg-$(TKG_VERSION) --recursive;\
#		mkdir -p tkr/tkr-$(TKR_VERSION);\
#		aws s3 cp s3://tkg-1click-dependencies/tkr/tkr-$(TKR_VERSION) tkr/tkr-$(TKR_VERSION) --recursive;\
#		mkdir -p os;\
#		aws s3 cp s3://tkg-1click-dependencies/os os --recursive;\
#		mkdir -p harbor;\
#		aws s3 cp s3://tkg-1click-dependencies/harbor harbor --recursive;\
#		aws s3 cp s3://tkg-1click-dependencies/yq .;\
#		aws s3 cp s3://tkg-1click-dependencies/goss-linux-amd64 .;\
#		mkdir -p kind;\
#		aws s3 cp s3://tkg-1click-dependencies/kind kind --recursive;\
#	popd
.PHONY: upload-deps
upload-deps: ## Upload dependencies from dir to bucket
	@[ "${BUCKET_NAME}" ] || ( echo ">> BUCKET_NAME is not set"; exit 1 )
	@[ "${DEPS_DIR}" ] || ( echo ">> DEPS_DIR is not set"; exit 1 )
	aws s3 cp $(DEPS_DIR) s3://$(BUCKET_NAME) --recursive
.PHONY: upload-images
upload-images: ## Upload images to your registry in airgapped env
	@[ "${REGISTRY}" ] || ( echo ">> REGISTRY is not set"; exit 1 )
	@[ "${REGISTRY_CA_PATH}" ] || ( echo ">> REGISTRY_CA_PATH is not set to full path to registry ca ie /etc/docker/certs.d/myharbor.com/ca.crt"; exit 1 )
	@[ "${BUCKET_NAME}" ] || ( echo ">> BUCKET_NAME is not set"; exit 1 )
	@[ "${TKG_VERSION}" ] || ( echo ">> TKG_VERSION is not set"; exit 1 )
	@[ "${TKR_VERSION}" ] || ( echo ">> TKR_VERSION is not set"; exit 1 )
	@[ "${IMGPKG_USERNAME}" ] || (echo ">> IMGPKG_USERNAME is not set"; exit 1)
	@[ "${IMGPKG_PASSWORD}" ] || [ "${IMGPKG_TOKEN}" ] || (echo ">> IMGPKG_PASSWORD or IMGPKG_TOKEN is not set"; exit 1)
	mkdir -p images-tkg
	aws s3 cp --recursive s3://$(BUCKET_NAME)/tkg/tkg-$(TKG_VERSION)/images images-tkg
	aws s3 cp --recursive s3://$(BUCKET_NAME)/tkr/tkr-$(TKR_VERSION)/images images-tkg
	chmod u+x images-tkg/publish-tkg-images-fromtar.sh images-tkg/publish-tkr-images-fromtar.sh
	aws s3 cp s3://$(BUCKET_NAME)/tkg/tkg-$(TKG_VERSION)/tanzu.tar .
	tar -xvf tanzu.tar
	pushd cli;\
	  gzip -d imgpkg*.gz;\
	  chmod +x imgpkg*;\
	  sudo mv imgpkg* /usr/bin/imgpkg;\
	popd
	rm -rf cli
	rm -rf tanzu.tar
	pushd images-tkg;\
	  TKG_CUSTOM_IMAGE_REPOSITORY_CA_PATH=$(REGISTRY_CA_PATH) TKG_CUSTOM_IMAGE_REPOSITORY=$(REGISTRY)/tkg ./publish-tkg-images-fromtar.sh;\
	  TKG_CUSTOM_IMAGE_REPOSITORY_CA_PATH=$(REGISTRY_CA_PATH) TKG_CUSTOM_IMAGE_REPOSITORY=$(REGISTRY)/tkg ./publish-tkr-images-fromtar.sh;\
	popd;
	rm -rf images-tkg;
	mkdir -p image-builder
	aws s3 cp s3://$(BUCKET_NAME)/harbor image-builder --recursive --include "*.tar" --exclude "*.tar.gz"
	pushd image-builder;\
	  ls -l *.tar | awk '{print $$9}'|xargs --replace  -n1 imgpkg copy  --tar {} --to-repo $(REGISTRY)/tkg/image-builder --registry-ca-cert-path $(REGISTRY_CA_PATH);\
	popd
	rm -rf image-builder
	cp $(REGISTRY_CA_PATH) ami/tkg-bootstrap/roles/bootstrap/files/ca
	cp $(REGISTRY_CA_PATH) ami/stig/roles/canonical-ubuntu-18.04-lts-stig-hardening/files/ca/

## --------------------------------------
## Build offline AMI's for Amazon Linux 2
## --------------------------------------
##@ Build offline AMI's for Amazon Linux 2
.PHONY: al2-node-ami-offline
al2-node-ami-offline: export REGISTRY=$(shell cat registry.txt)## build amazon linux2 ami's for TKG clusters
al2-node-ami-offline:
	# we need this in same line with && if any of the command failed code needs to stop.
	echo "building node os amazon linux 2 ami for ....."
	cd ami/stig && make build-amazon-linux2-node-ami && cd ..

.PHONY: al2-bootstrap-ami-offline
al2-bootstrap-ami-offline: export REGISTRY=$(shell cat registry.txt)## build amazon linux2 ami's for bootstrap
al2-bootstrap-ami-offline:
	# we need this in same line with && if any of the command failed code needs to stop.
	echo "building bootstrap amazon 2 linux based ami....."
	cd ami/tkg-bootstrap && make build-amazon-linux2-bootstrap-ami && cd ../../

.PHONY: all-al2-offline-ami
all-al2-offline-ami: setup-registry-ca al2-bootstrap-ami-offline al2-node-ami-offline ## build amazon linux2 ami's for bootstrap and TKG clusters

.PHONY: install-tkg-on-al2 ## install tkg on AWS, considering Amazon Linux 2 as base OS for Bootstrap and TKG clusters
# fetch bootstrap ami id using ami name
install-tkg-on-al2: export TF_VAR_bs_ami_id=$(shell aws ec2 describe-images --owner self  --filters "Name=name,Values=tkg-$$TKG_VERSION-$$TKR_VERSION*bootstrap-amazon-*" --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' --output text)
# fetch node os ami id using ami name
install-tkg-on-al2: export TF_VAR_node_ami_id=$(shell aws ec2 describe-images --owner self  --filters "Name=name,Values=capa-ami-amazon-*-$$TKR_VERSION*" --query 'reverse(sort_by(Images, &CreationDate))[0].ImageId' --output text)
install-tkg-on-al2: export TF_VAR_registry_name=$(shell cat registry.txt)
install-tkg-on-al2: export TF_VAR_base_os_family=amazon-linux-2## install tkg on AWS, considering Amazon Linux 2 as base OS for Bootstrap and TKG clusters
install-tkg-on-al2:
	@[ "${TF_VAR_bucket_name}" ] || ( echo ">> TF_VAR_bucket_name is not set"; exit 1 )
	@[ "${TF_VAR_region}" ] || ( echo ">> TF_VAR_region is not set"; exit 1 )
	echo "running tkg bootstrap installer...."
	chmod +x terraform/setup-bootstrap.sh
	# run bootstrap setup inside terraform dir
	terraform/setup-bootstrap.sh;