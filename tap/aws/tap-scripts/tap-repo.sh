#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
source var.conf

#login to kubernets eks cluster
#kubectl config get-contexts
#read -p "Target Context: " target_context
#kubectl config use-context $target_context

#read -p "Enter tanzu net user: " tanzu_net_reg_user
#read -p "Enter tanzu net password: " tanzu_net_reg_password

export INSTALL_REGISTRY_USERNAME=$tanzu_net_reg_user
export INSTALL_REGISTRY_PASSWORD=$tanzu_net_reg_password


kubectl create ns "${TAP_NAMESPACE}"

# tanzu registry secret creation
tanzu secret registry add tap-registry \
  --username "${INSTALL_REGISTRY_USERNAME}" --password "${INSTALL_REGISTRY_PASSWORD}" \
  --server "${INSTALL_REGISTRY_HOSTNAME}" \
  --export-to-all-namespaces --yes --namespace "${TAP_NAMESPACE}"

# tanzu repo add
tanzu package repository add tanzu-tap-repository \
  --url registry.tanzu.vmware.com/tanzu-application-platform/tap-packages:$TAP_VERSION \
  --namespace "${TAP_NAMESPACE}"

tanzu package repository get tanzu-tap-repository --namespace "${TAP_NAMESPACE}"

# tap available package list
tanzu package available list --namespace "${TAP_NAMESPACE}"