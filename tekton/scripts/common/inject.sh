#!/bin/bash
set -o errexit

function inject_inline() {
  yq eval ".harborAdminPassword = \"$harborAdminPassword\"" -i "$1"
  yq eval ".hostname = \"$hostname\"" -i "$1"
  yq eval '.tlsCertificate."tls.crt" = '\""$crt\"" -i "$1"
  yq eval '.tlsCertificate."tls.key" = '\""$key\"" -i "$1"
  echo "Successfully injected values to  $1"
}

function install_yq() {
  if ! which yq >/dev/null; then
    echo 'Please install yq version 4.5 or above from https://github.com/mikefarah/yq/releases'
    exit 1
  fi
}

# insert values
harborAdminPassword=$2
hostname=$3
crt=$4
key=$5

install_yq
inject_inline "$1" "$2" "$3" "$4" "$5"