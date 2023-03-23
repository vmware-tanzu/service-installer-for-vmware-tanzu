#!/bin/bash
set -o errexit
# if argument passed as true deployment should start else no extension deployments
if [[ "$1" == "true" ]]; then
  # cert-manager, prometheus and contour is a pre-requisite
  echo "deploying cert manager, as grafana is dependent on it....."
  source deploy_cert_manager.sh "true"
  echo "deploying contour, as grafana is dependent on it......"
  source deploy_contour.sh "true"
  echo "deploying prometheus, as grafana is dependent on it......"
  source deploy_prometheus.sh "true"
  # grafana version, take out last grafana template version from package list
  tanzu package available list grafana.tanzu.vmware.com |  awk '{if(NR>1)print $2}' > grafana_version.txt
  bash version_check.sh grafana_version.txt
  grafana_version=`cat grafana_version.txt`
  image_url=$(kubectl -n tkg-system get packages grafana.tanzu.vmware.com.$grafana_version -o jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}')
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
  if [[ $TANZU_VERSION == v0.28.0 ]]; then
      # from TKG 2.1.0
      # --package-name has been changes to --package,
      tanzu package install grafana --package grafana.tanzu.vmware.com --version $grafana_version --values-file grafana-data-values.yaml --namespace tanzu-packages
  else
      tanzu package install grafana --package-name grafana.tanzu.vmware.com --version $grafana_version --values-file grafana-data-values.yaml --namespace tanzu-packages
  fi
fi