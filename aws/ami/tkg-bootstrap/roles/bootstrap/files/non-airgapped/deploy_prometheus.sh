#!/bin/bash
set -o errexit
# if argument passed as true deployment should start else no extension deployments
if [[ "$1" == "true" ]]; then
  # if prometheus is already there no need for installation.
  installation=$(tanzu package installed list -A | awk '$1 == "prometheus" {print $1}')
  if [[ -z "$installation" ]]; then
    echo "prometheus not exist....creating it..."
    # cert-manager and contour is a pre-requisite
    echo "deploying cert-manager, as prometheus is dependent on it......"
    source deploy_cert_manager.sh "true"
    echo "deploying contour, as prometheus is dependent on it......"
    source deploy_contour.sh "true"
    # prometheus version, take out last prometheus template version from package list
    tanzu package available list prometheus.tanzu.vmware.com |  awk '{if(NR>1)print $2}' > prometheus_version.txt
    bash version_check.sh prometheus_version.txt
    prometheus_version=`cat prometheus_version.txt`
    image_url=$(kubectl -n tkg-system get packages prometheus.tanzu.vmware.com.$prometheus_version -o jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}')
    imgpkg pull -b $image_url -o /tmp/prometheus-$prometheus_version
    cp /tmp/prometheus-$prometheus_version/config/values.yaml ./prometheus-data-values.yaml
    yq -i eval '... comments=""' ./prometheus-data-values.yaml
    #update hostname inside prometheus yaml
    yq eval -i '.ingress.virtual_host_fqdn = env(PROMETHEUS_HOSTNAME)' ./prometheus-data-values.yaml
    #enable ingress for prometheus
    yq eval -i '.ingress.enabled = true' ./prometheus-data-values.yaml
    # install prometheus
    if [[ $TANZU_VERSION == v0.28.1 ]]; then
        # from TKG 2.1.1
        # --package-name has been changes to --package,
        tanzu package install prometheus --package prometheus.tanzu.vmware.com --version $prometheus_version --values-file prometheus-data-values.yaml --namespace tanzu-packages
    else
        tanzu package install prometheus --package-name prometheus.tanzu.vmware.com --version $prometheus_version --values-file prometheus-data-values.yaml --namespace tanzu-packages
    fi
  else
    echo "prometheus is already installed...."
  fi
fi
