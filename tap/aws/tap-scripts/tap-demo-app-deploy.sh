#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
source var.conf

echo "Build source code in build cluster !!!"

echo "Login to build cluster !!!"
aws eks --region $aws_region update-kubeconfig --name tap-build

echo "delete existing app"
tanzu apps workload delete --all

tanzu apps workload list

tanzu apps workload create "${TAP_APP_NAME}" --git-repo "${TAP_APP_GIT_URL}" --git-branch main --type web \
--label apps.tanzu.vmware.com/has-tests=true \
--label app.kubernetes.io/part-of="${TAP_APP_NAME}" --yes --dry-run > tap-demo-workload.yaml

tanzu apps workload create "${TAP_APP_NAME}" \
--git-repo "${TAP_APP_GIT_URL}" \
--git-branch main \
--git-tag tap-1.1 \
--type web \
--label app.kubernetes.io/part-of="${TAP_APP_NAME}" \
--label apps.tanzu.vmware.com/has-tests=true \
--yes

sleep 10

tanzu apps workload list

tanzu apps workload get "${TAP_APP_NAME}"

echo "generate tap-demo deliver.yaml workload "

kubectl get deliverables "${TAP_APP_NAME}" -o yaml |  yq 'del(.status)'  | yq 'del(.metadata.ownerReferences)' | yq 'del(.metadata.resourceVersion)' | yq 'del(.metadata.uid)' >  "${TAP_APP_NAME}-delivery.yaml"

cat ${TAP_APP_NAME}-delivery.yaml

echo "login to run cluster to deploy tap demo delivery workload"
aws eks --region $aws_region update-kubeconfig --name tap-run

kubectl apply -f ${TAP_APP_NAME}-delivery.yaml

kubectl get deliverable -A     

echo "get app url and copy into browser to test the app"
kubectl get ksvc



