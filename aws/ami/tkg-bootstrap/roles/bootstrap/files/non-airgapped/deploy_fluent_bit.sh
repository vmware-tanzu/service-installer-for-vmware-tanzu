#!/bin/bash
set -o errexit
# if argument passed as true deployment should start else no extension deployments
if [[ "$1" == "true" ]]; then
  # check if namespace is created
  source check_name_space.sh
  # fluent-bit, take out last fluent bit template version from package list
  fluent_bit_version=$(tanzu package available list fluent-bit.tanzu.vmware.com | awk 'END{print $2}')
  tanzu package install fluent-bit --package-name fluent-bit.tanzu.vmware.com --namespace tanzu-packages --version $fluent_bit_version
fi