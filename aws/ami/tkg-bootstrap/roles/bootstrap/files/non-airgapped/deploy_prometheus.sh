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
    prometheus_version=$(tanzu package available list prometheus.tanzu.vmware.com | awk 'END{print $2}')
    image_url=$(kubectl -n tanzu-package-repo-global get packages prometheus.tanzu.vmware.com.$prometheus_version -o jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}')
    imgpkg pull -b $image_url -o /tmp/prometheus-$prometheus_version
    cp /tmp/prometheus-$prometheus_version/config/values.yaml ./prometheus-data-values.yaml
    yq -i eval '... comments=""' ./prometheus-data-values.yaml
    #update hostname inside prometheus yaml
    yq eval -i '.ingress.virtual_host_fqdn = env(PROMETHEUS_HOSTNAME)' ./prometheus-data-values.yaml
    #enable ingress for prometheus
    yq eval -i '.ingress.enabled = true' ./prometheus-data-values.yaml
    # install prometheus
    tanzu package install prometheus --package-name prometheus.tanzu.vmware.com --version $prometheus_version --values-file prometheus-data-values.yaml --namespace tanzu-packages
  else
    echo "prometheus is already installed...."
  fi
fi