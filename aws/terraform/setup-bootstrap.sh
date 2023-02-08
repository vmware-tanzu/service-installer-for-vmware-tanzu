#!/bin/bash
set -o errexit
pwd
# load terraform directory for installation
cd terraform
pwd
echo "launching tkg bootstrap machine using terraform modules...."
terraform init \
          --backend \
          --backend-config="bucket=${TF_VAR_bucket_name}" \
          --backend-config="key=terraform/tkg-bootstrap" \
          --backend-config="region=${TF_VAR_region}";
terraform apply -auto-approve;
echo "bootstrap has been initialized...."
cd ..