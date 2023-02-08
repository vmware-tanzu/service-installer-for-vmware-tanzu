#!/bin/bash
set -o errexit
pwd
# load terraform harbor directory for installation
cd terraform-harbor
pwd
if [ -z ${USE_EXISTING_REGISTRY+x} ]; then
  echo "launching harbor using terraform modules...."
  terraform init \
          --backend \
          --backend-config="bucket=$TF_VAR_bucket_name" \
          --backend-config="key=terraform/harbor-state" \
          --backend-config="region=$TF_VAR_region"; \
  terraform apply -auto-approve;
cd ..
echo "harbor has been initialized...."
fi