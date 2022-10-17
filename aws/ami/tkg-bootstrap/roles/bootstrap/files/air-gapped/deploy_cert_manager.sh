#!/bin/bash
set -o errexit
# if argument passed as true deployment should start else no extension deployments
if [[ "$1" == "true" ]]; then
   # if cert manager is already there no need for installation.
  installation=$(tanzu package installed list -A | awk '$1 == "cert-manager" {print $1}')
  if [[ -z "$installation" ]]; then
    # check if namespace is created
    source check_name_space.sh
    # cert manager on workload cluster
    cert_manager_version=$(tanzu package available list cert-manager.tanzu.vmware.com | awk 'END{print $2}')
    tanzu package install cert-manager --package-name cert-manager.tanzu.vmware.com --namespace tanzu-packages --version $cert_manager_version
  else
    echo "cert-manager is already installed...."
  fi
fi