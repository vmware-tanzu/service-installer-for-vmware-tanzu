#!/bin/bash
set -o errexit
# load terraform harbor directory for installation
cd terraform-airgapped-vpc
pwd
echo "launching VPC setup using terraform modules...."
terraform init ;
terraform apply -auto-approve;
cd ..
echo "VPC has been created...."