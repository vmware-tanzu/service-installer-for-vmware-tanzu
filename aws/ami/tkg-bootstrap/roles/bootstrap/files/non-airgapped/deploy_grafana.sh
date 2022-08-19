#!/bin/bash
set -o errexit
# if argument passed as true deployment should start else no extension deployments
if [[ "$1" == "true" ]]; then
  # cert-manager, prometheus and contour is a pre-requisite
  echo "deploying cert manager, as garfana is dependent on it....."
  source deploy_cert_manager.sh "true"
  echo "deploying contour, as garfana is dependent on it......"
  source deploy_contour.sh "true"
  echo "deploying prometheus, as grafana is dependent on it......"
  source deploy_prometheus.sh "true"
  # grafana version, take out last grafana template version from package list
  grafana_version=$(tanzu package available list grafana.tanzu.vmware.com | awk 'END{print $2}')
  image_url=$(kubectl -n tanzu-package-repo-global get packages grafana.tanzu.vmware.com.$grafana_version -o jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}')
  imgpkg pull -b $image_url -o /tmp/grafana-$grafana_version
  cp /tmp/grafana-$grafana_version/config/values.yaml ./grafana-data-values.yaml
  yq -i eval '... comments=""' ./grafana-data-values.yaml
  #update hostname inside grafana yaml
  yq eval -i '.ingress.virtual_host_fqdn = env(GRAFANA_HOSTNAME)' ./grafana-data-values.yaml
  #enable ingress for grafana, service type should set to clusterIp as envoy has been used for ingress
  yq eval -i '.ingress.enabled = true' ./grafana-data-values.yaml
  yq eval -i '.grafana.service.type = "ClusterIP"' ./grafana-data-values.yaml
  yq eval -i '.namespace = "tanzu-system-dashboards"' ./grafana-data-values.yaml
  # install grafana
  tanzu package install grafana --package-name grafana.tanzu.vmware.com --version $grafana_version --values-file grafana-data-values.yaml --namespace tanzu-packages
fi