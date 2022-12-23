#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
source var.conf

chmod +x tanzu-essential-setup.sh
chmod +x tap-repo.sh
chmod +x tap-iterate-profile.sh
chmod +x tap-dev-namespace.sh

chmod +x var-input-validatation.sh

./var-input-validatation.sh

echo  "Login to iterate Cluster !!! "
aws eks --region $aws_region update-kubeconfig --name tap-iterate

#login to kubernets eks run cluster
#kubectl config get-contexts
#read -p "Select Kubernetes context of run cluster: " target_context
#kubectl config use-context $target_context

echo "Step 1 => installing tanzu essential in iterate cluster !!!"
./tanzu-essential-setup.sh
echo "Step 2 => installing TAP Repo in iterate cluster !!! "
./tap-repo.sh
echo "Step 3 => installing TAP iterate Profile !!! "
./tap-iterate-profile.sh
echo "Step 4 => installing TAP developer namespace in iterate cluster !!! "
./tap-dev-namespace.sh