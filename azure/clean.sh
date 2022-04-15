#!/bin/bash
# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
export TF_IN_AUTOMATION='true'
export TF_VAR_sub_id=$1
export TF_VAR_tenant_id=$2

if [ $# -eq 0 ]
    then
        echo "You must supply Azure subscription and tenant IDs to this script!"
        exit
fi

if [ -z "$2" ]
    then 
        echo "The second argument should be a valid Azure tenant ID."
        exit
fi


cd 0_keepers
export ARM_ACCESS_KEY="$(terraform output -raw access_key)"
cd ..

# Delete bootstrap
cd 3_bootstrap
terraform destroy -auto-approve
cd ..

# Delete NetSec
cd 1_netsec
terraform destroy -auto-approve
cd ..

# Establish 'keepers' which used throughout and can cross into unrelated deployments
cd 0_keepers
terraform destroy -auto-approve
cd ..

rm -rf  ./0_keepers/terraform.tfstate* \
        ./0_keepers/.terraform.lock.hcl \
        ./0_keepers/.terraform \
        ./1_netsec/.terraform.lock.hcl \
        ./1_netsec/provider.tf \
        ./1_netsec/.terraform -Force \
        ./2_dns/.terraform.lock.hcl \
        ./2_dns/provider.tf \
        ./2_dns/.terraform \
        ./3_bootstrap/.terraform.lock.hcl \
        ./3_bootstrap/data.tf \
        ./3_bootstrap/provider.tf \
        ./3_bootstrap/.terraform \
        ./3_bootstrap/bootstrap.pem