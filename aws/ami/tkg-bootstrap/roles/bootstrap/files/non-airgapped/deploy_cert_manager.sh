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
    tanzu package available list cert-manager.tanzu.vmware.com |  awk '{if(NR>1)print $2}' > cert_manager_version.txt
    bash version_check.sh cert_manager_version.txt
    cert_manager_version=`cat cert_manager_version.txt`
    if [[ $TANZU_VERSION == v0.28.1 ]]; then
      # from TKG 2.1.1
      # Tanzu package repo is added by default in namespace(tanzu-package-repo-global) in previous releases,
      # but now we need to add it manually in tkg-system namespace.
        tanzu package install cert-manager --package cert-manager.tanzu.vmware.com --namespace tanzu-packages --version $cert_manager_version
    else
        tanzu package install cert-manager --package-name cert-manager.tanzu.vmware.com --namespace tanzu-packages --version $cert_manager_version
    fi
  else
    echo "cert-manager is already installed...."
  fi
fi
