#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
source var.conf

chmod +x tanzu-essential-setup.sh
chmod +x tap-repo.sh
chmod +x tap-build-profile.sh
chmod +x tap-dev-namespace.sh
chmod +x tanzu-cli-setup.sh

chmod +x var-input-validatation.sh

./var-input-validatation.sh

echo  "Login to BUILD Cluster !!! "
aws eks --region $aws_region update-kubeconfig --name tap-build


echo "Step 1 => installing tanzu essential in BUILD Cluster !!!"
./tanzu-essential-setup.sh
echo "Step 2 => installing TAP Repo in BUILD Cluster !!! "
./tap-repo.sh
echo "Step 3 => installing TAP Build Profile !!! "
./tap-build-profile.sh
echo "Step 4 => installing TAP developer namespace in BUILD Cluster !!! "
./tap-dev-namespace.sh