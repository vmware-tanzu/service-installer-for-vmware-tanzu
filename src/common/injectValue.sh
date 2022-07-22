#!/bin/bash
set -o errexit

function inject_cert_manager() {
  dep="Deployment"
  yq eval "select(.kind == \"$dep\" and .metadata.name == \"$key_v\").spec.template.spec.containers[0].image |= \"$url\"" -i "$file"
  echo "Successfully injected cert manager values to  $file"
}

function inject_app_extention() {
  dep="App"
  yq eval "select(.kind == \"$dep\").spec.fetch[0].image.url |= \"$url\"" -i "$file"
  echo "Successfully injected app extention values to  $file"
}

function inject_contour() {
  yq eval ".contour.image.repository = \"$url\"" -i "$file"
  yq eval ".envoy.image.repository = \"$url\"" -i "$file"

  echo "Successfully injected contour values to  $file"
}

function inject_data_values_harbor() {
  yq eval ".image.repository = \"$url\"" -i "$file"

  echo "Successfully injected data values to  $file"
}

function inject_inline_secret() {
  yq eval ".grafana.secret.admin_password = \"$url\"" -i "$file"
  yq eval ".namespace = \"$key_v\"" -i "$file"
  yq eval ".grafana.service.type = \"NodePort\"" -i "$file"
  echo "Successfully injected contour values to  $file"
}

function inject_inline_fqdn() {
  yq eval ".ingress.virtual_host_fqdn = \"$url\"" -i "$file"

  echo "Successfully injected data values to  $file"
}

function inject_inline_ingress() {
  yq eval ".ingress.enabled = \"$url\"" -i "$file"

  echo "Successfully injected data values to  $file"
}

function inject_contour_tag() {
  yq eval ".contour.image.tag = \"$url\"" -i "$file"

  echo "Successfully injected contour values to  $file"
}

function inject_envoy_tag() {
  yq eval ".envoy.image.tag = \"$url\"" -i "$file"


  echo "Successfully injected contour values to  $file"
}

function inject_fluent_bit() {
  yq eval ".spec.fetch[0].image.url = \"$url\"" -i "$file"

  echo "Successfully injected fluent bit values to  $file"
}

function install_yq() {
  if ! which yq >/dev/null; then
    echo 'Please install yq version 4.5 or above from https://github.com/mikefarah/yq/releases'
    exit 1
  fi
}

function inject_inline_pro() {
  yq eval '.monitoring.ingress.tlsCertificate."tls.crt" = '\""$url\"" -i "$file"
  yq eval '.monitoring.ingress.tlsCertificate."tls.key" = '\""$key_v\"" -i "$file"
  echo "Successfully injected values to  $file"
}

function inject_inline_gra() {
  yq eval '.monitoring.grafana.ingress.tlsCertificate."tls.crt" = '\""$url\"" -i "$file"
  yq eval '.monitoring.grafana.ingress.tlsCertificate."tls.key" = '\""$key_v\"" -i "$file"
  echo "Successfully injected values to  $file"
}

function inject_inline_cert_dot4() {
  yq eval '.ingress.tlsCertificate."tls.crt" = '\""$url\"" -i "$file"
  yq eval '.ingress.tlsCertificate."tls.key" = '\""$key_v\"" -i "$file"
  echo "Successfully injected values to  $file"
}

function inject_nms() {
  yq eval '.metadata.namespace = '\""$url\"" -i "$file"
  echo "Successfully injected namespace values to  $file"
}

function removecomment() {
  yq eval '... comments=""' -i "$file"
}

function ineject_repo_overlay() {
  yq eval '.spec.template.spec.containers[0].image = '\""$url\"" -i "$file"
}

function inject_sc_grafana() {
  yq eval '.grafana.pvc.storageClassName = '\""$url\"" -i "$file"
  echo "Successfully injected storage class values to  $file"
}

function inject_sc_prometheus() {
  yq eval '.prometheus.pvc.storageClassName = '\""$url\"" -i "$file"
  yq eval '.alertmanager.pvc.storageClassName = '\""$url\"" -i "$file"
  echo "Successfully injected storage class values to  $file"
}

function inject_sc_harbor() {
  yq eval '.persistence.persistentVolumeClaim.registry.storageClass = '\""$url\"" -i "$file"
  yq eval '.persistence.persistentVolumeClaim.jobservice.storageClass = '\""$url\"" -i "$file"
  yq eval '.persistence.persistentVolumeClaim.database.storageClass = '\""$url\"" -i "$file"
  yq eval '.persistence.persistentVolumeClaim.redis.storageClass = '\""$url\"" -i "$file"
  yq eval '.persistence.persistentVolumeClaim.trivy.storageClass = '\""$url\"" -i "$file"
  yq eval ".pspNames = \"vmware-system-restricted\"" -i "$file"
  echo "Successfully injected storage class values to  $file"
}

function inject_output_fluent() {
  yq eval '.fluent_bit.config.outputs = '\""$url\"" -i "$file"
  echo "Successfully injected Fluent-bit output values to  $file"
}

function inject_cni() {
  yq eval '.spec.defaultCNI = '\""$url\"" -i "$file"
  echo "Successfully cni values to  $file"
}
function delete_proxy_setting() {
    yq eval 'del(.spec.proxy)' -i "$file"
}

function inject_proxy() {
  yq eval '.spec.proxy.httpProxy = '\""$url\"" -i "$file"
  yq eval '.spec.proxy.httpsProxy = '\""$key_v\"" -i "$file"
  yq eval '.spec.proxy.noProxy += ' -i "$file"
  echo "Successfully injected proxy values to  $file"
}

function inject_trust() {
  yq eval '.spec.trust.additionalTrustedCAs += '\""$url\"" -i "$file"
  echo "Successfully injected trust certificate  $file"
}
function delete_trust() {
    yq eval 'del(.spec.trust)' -i "$file"
}


install_yq
url=$3
file=$1
key_v=$4
noProxy=$5

case "$2" in
        cert)
                inject_cert_manager
                ;;
        app_extention)
                inject_app_extention
                ;;
        contour)
                inject_contour
                ;;
        contour_tag)
                inject_contour_tag
                ;;
        envoy_tag)
                inject_envoy_tag
                ;;
        data_values_harbor)
                inject_data_values_harbor
                ;;
        fluent_bit)
                inject_fluent_bit
                ;;
        inject_cert_promethus)
                inject_inline_pro
                ;;
        inject_cert_grafana)
                inject_inline_gra
                ;;
        remove)
                removecomment
                ;;
        inject_secret)
                inject_inline_secret
                ;;
        inject_ingress_fqdn)
                inject_inline_fqdn
                ;;
        inject_ingress)
                inject_inline_ingress
                ;;
        inject_cert_dot4)
                inject_inline_cert_dot4
                ;;
        overlay)
                ineject_repo_overlay
                ;;
        inject_namespace)
                inject_nms
                ;;
        inject_sc_prometheus)
                inject_sc_prometheus
                ;;
        inject_sc_grafana)
                inject_sc_grafana
                ;;
        inject_sc_harbor)
                inject_sc_harbor
                ;;
        change_cni)
                inject_cni
                ;;
        change_proxy)
                inject_proxy
                ;;
        delete_proxy)
                delete_proxy_setting
                ;;
        change_trust)
                inject_trust
                ;;
        delete_trust)
                delete_trust
                ;;
        inject_output_fluent)
                inject_output_fluent
                ;;

        *)
                echo "Usage: $0 {cert|app_extention|contour|contour_tag|envoy_tag|data_values_harbor|fluent_bit|overlay}"
                echo ""
                echo "Use this shell script to change the value to yaml files"
esac


