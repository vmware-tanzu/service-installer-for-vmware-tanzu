#!/bin/bash
set -o errexit
# if argument passed as true deployment should start else no extension deployments
if [[ "$1" == "true" ]]; then
  # if contour is already there no need for installation.
  installation=$(tanzu package installed list -A | awk '$1 == "contour" {print $1}')
  if [[ -z "$installation" ]]; then
    # check if namespace is created
    source check_name_space.sh
    echo "contour not exist....creating it..."
    # contour ingress
    tanzu package available list contour.tanzu.vmware.com |  awk '{if(NR>1)print $2}' > contour_version.txt
    bash version_check.sh contour_version.txt
    contour_version=`cat contour_version.txt`
    image_url=$(kubectl -n tkg-system get packages contour.tanzu.vmware.com.$contour_version -o jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}')
    imgpkg pull -b $image_url -o /tmp/contour-$contour_version
    cp /tmp/contour-$contour_version/config/values.yaml ./contour-data-values.yaml
    yq -i eval '... comments=""' ./contour-data-values.yaml
    yq eval -i '.infrastructure_provider="aws" | .envoy.service.type="LoadBalancer"' ./contour-data-values.yaml
    if [[ $TANZU_VERSION == v0.28.1 ]]; then
        # from TKG 2.1.1
        # --package-name has been changes to --package,
        tanzu package install contour --package contour.tanzu.vmware.com --version $contour_version --values-file contour-data-values.yaml --namespace tanzu-packages
    else
        tanzu package install contour --package-name contour.tanzu.vmware.com --version $contour_version --values-file contour-data-values.yaml --namespace tanzu-packages
    fi
  else
    echo "contour is already installed...."
  fi
fi
