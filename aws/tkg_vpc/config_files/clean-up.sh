#!/usr/bin/env bash
# Nukes everything the deployed management cluster deployed
# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
MGMT_CLUSTER_NAME=$(tanzu clusters list  --include-management-cluster -o json | jq -r '.[] | select(any(.roles[]; . == "management")).name')
kubectl config use-context ${MGMT_CLUSTER_NAME}-admin@${MGMT_CLUSTER_NAME}
kubectl delete cluster -n default --all
#On AWS, this sets the region which is necessary.. on other IAAS it just fails
#But doesn't make any difference.
export AWS_REGION=$(curl http://169.254.169.254/latest/meta-data/placement/region)
tanzu management-cluster delete ${MGMT_CLUSTER_NAME} --yes
