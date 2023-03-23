#!/bin/bash
set -o errexit
# load terraform harbor directory for installation
cd terraform-non-air-gapped-vpc
pwd
echo "launching VPC setup using terraform modules...."
terraform init \
        --backend \
        --backend-config="bucket=$TF_VAR_bucket_name" \
        --backend-config="key=terraform/vpc-state" \
        --backend-config="region=$TF_VAR_region"; \
terraform apply -auto-approve;
cd ..
echo "VPC has been created...."