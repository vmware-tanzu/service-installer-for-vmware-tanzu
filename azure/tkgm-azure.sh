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

# Establish 'keepers' which used throughout and can cross into unrelated deployments
cd 0_keepers
terraform init -input=false
terraform apply -input=false -auto-approve
export ARM_ACCESS_KEY="$(terraform output -raw access_key)"
cd ..

# Create network and security resources
cd 1_netsec
terraform init -input=false
terraform apply -input=false -auto-approve
cd ..

# Create the bootstrap machine for TKGm
cd 3_bootstrap
terraform init -input=false
terraform apply -input=false -auto-approve
cd ..
