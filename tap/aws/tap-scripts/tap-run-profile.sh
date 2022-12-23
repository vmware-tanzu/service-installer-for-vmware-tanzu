#!/bin/bash
# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

#kubectl config get-contexts
#read -p "Target EKS Context: " target_context

#kubectl config use-context $target_context

#read -p "Enter custom registry url (harbor/azure registry etc): " registry_url
#read -p "Enter custom registry user: " registry_user
#read -p "Enter custom registry password: " registry_password
#read -p "Enter cnrs domain: " tap_cnrs_domain
#read -p "Enter app live view domain: " alv_domain

source var.conf

#export TAP_NAMESPACE="tap-install"
export TAP_REGISTRY_SERVER=$registry_url
export TAP_REGISTRY_USER=$registry_user
export TAP_REGISTRY_PASSWORD=$registry_password
export TAP_CNRS_DOMAIN=$tap_run_cnrs_domain
##export TAP_VERSION=1.1.0

cat <<EOF | tee tap-values-run.yaml
profile: run
ceip_policy_disclosed: true
supply_chain: basic

contour:
  infrastructure_provider: aws
  envoy:
    service:
      aws:
        LBType: nlb
cnrs:
  domain_name: "${tap_run_cnrs_domain}"

appliveview_connector:
  backend:
    sslDisabled: "true"
    host: appliveview.$alv_domain

EOF

tanzu package install tap -p tap.tanzu.vmware.com -v $TAP_VERSION --values-file tap-values-run.yaml -n "${TAP_NAMESPACE}"
tanzu package installed get tap -n "${TAP_NAMESPACE}"

# check all build cluster package installed succesfully
tanzu package installed list -A

# check ingress external ip
kubectl get svc -n tanzu-system-ingress

echo "pick external ip from service output  and configure DNS wild card(*) into your DNS server like aws route 53 etc"
echo "example - *.run.customer0.io ==> <ingress external ip/cname>"