#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
source var.conf

#kubectl config get-contexts
#read -p "Target EKS Context: " target_context

#kubectl config use-context $target_context

#read -p "Enter custom registry url (harbor/azure registry etc): " registry_url
#read -p "Enter custom registry user: " registry_user
#read -p "Enter custom registry password: " registry_password

#export TAP_NAMESPACE="tap-install"
export TAP_REGISTRY_USER=$registry_user
export TAP_REGISTRY_SERVER_ORIGINAL=$registry_url
if [ $registry_url = "${DOCKERHUB_REGISTRY_URL}" ]
then
  export TAP_REGISTRY_SERVER=$TAP_REGISTRY_USER
  export TAP_REGISTRY_REPOSITORY=$TAP_REGISTRY_USER
else
  export TAP_REGISTRY_SERVER=$registry_url
  export TAP_REGISTRY_REPOSITORY="supply-chain"
fi
export TAP_REGISTRY_PASSWORD=$registry_password
#export TAP_VERSION=1.1.0
export INSTALL_REGISTRY_USERNAME=$tanzu_net_reg_user
export INSTALL_REGISTRY_PASSWORD=$tanzu_net_reg_password


cat <<EOF | tee tap-values-build.yaml
profile: build
ceip_policy_disclosed: true
buildservice:
  kp_default_repository: "${TAP_REGISTRY_SERVER}/build-service"
  kp_default_repository_username: "${TAP_REGISTRY_USER}"
  kp_default_repository_password: "${TAP_REGISTRY_PASSWORD}"
  tanzunet_username: "${INSTALL_REGISTRY_USERNAME}"
  tanzunet_password: "${INSTALL_REGISTRY_PASSWORD}"
  descriptor_name: "full"
  enable_automatic_dependency_updates: true
supply_chain: basic
ootb_supply_chain_basic:    
  registry:
    server: "${TAP_REGISTRY_SERVER_ORIGINAL}"
    repository: "${TAP_REGISTRY_REPOSITORY}"
  gitops:
    ssh_secret: ""
  cluster_builder: default
  service_account: default
grype:
  namespace: "default" 
  targetImagePullSecret: "tap-registry"
  metadataStore:
    url: "http://metadata-store.${tap_view_app_domain}"
    caSecret:
        name: store-ca-cert
        importFromNamespace: metadata-store-secrets
    authSecret:
        name: store-auth-token
        importFromNamespace: metadata-store-secrets
scanning:
  metadataStore:
    url: "" # Disable embedded integration since it's deprecated

image_policy_webhook:
  allow_unmatched_images: true

EOF

tanzu package install tap -p tap.tanzu.vmware.com -v $TAP_VERSION --values-file tap-values-build.yaml -n "${TAP_NAMESPACE}"

tanzu package installed get tap -n "${TAP_NAMESPACE}"

# check all build cluster package installed succesfully
tanzu package installed list -A

# check ingress external ip
kubectl get svc -n tanzu-system-ingress
