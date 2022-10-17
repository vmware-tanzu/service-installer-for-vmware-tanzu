#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
source var.conf

chmod +x tanzu-essential-setup.sh
chmod +x tap-repo.sh
chmod +x tap-view-profile.sh
chmod +x tap-dev-namespace.sh

chmod +x var-input-validatation.sh

./var-input-validatation.sh

echo  "Login to View Cluster !!! "
#login to kubernets eks run cluster
aws eks --region $aws_region update-kubeconfig --name tap-view


#kubectl config get-contexts
#read -p "Select Kubernetes context of view cluster: " target_context
#kubectl config use-context $target_context
echo "Step 1 => installing tanzu cli and tanzu essential in VIEW cluster !!!"
./tanzu-essential-setup.sh
echo "Step 2 => installing TAP Repo in VIEW cluster !!! "
./tap-repo.sh
echo "Step 3 => installing TAP VIEW  Profile !!! "
./tap-view-profile.sh
echo "Step 4 => installing TAP developer namespace in VIEW cluster !!! "
./tap-dev-namespace.sh