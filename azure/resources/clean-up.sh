#!/usr/bin/env bash
# Nukes everything the deployed management cluster deployed
# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
MGMT_CLUSTER_NAME=$(tanzu clusters list  --include-management-cluster -o json | jq -r '.[] | select(any(.roles[]; . == "management")).name')
kubectl config use-context ${MGMT_CLUSTER_NAME}-admin@${MGMT_CLUSTER_NAME}
kubectl delete cluster -n default --all
tanzu management-cluster delete ${MGMT_CLUSTER_NAME} --yes