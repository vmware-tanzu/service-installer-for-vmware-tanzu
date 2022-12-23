#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
source var.conf

chmod +x tanzu-essential-setup.sh
chmod +x tap-repo.sh
chmod +x tap-run-profile.sh
chmod +x tap-dev-namespace.sh

chmod +x var-input-validatation.sh

./var-input-validatation.sh

echo  "Login to RUN Cluster !!! "
aws eks --region $aws_region update-kubeconfig --name tap-run

#login to kubernets eks run cluster
#kubectl config get-contexts
#read -p "Select Kubernetes context of run cluster: " target_context
#kubectl config use-context $target_context

echo "Step 1 => installing tanzu essential in RUN cluster !!!"
./tanzu-essential-setup.sh
echo "Step 2 => installing TAP Repo in RUN cluster !!! "
./tap-repo.sh
echo "Step 3 => installing TAP RUN Profile !!! "
./tap-run-profile.sh
echo "Step 4 => installing TAP developer namespace in RUN cluster !!! "
./tap-dev-namespace.sh