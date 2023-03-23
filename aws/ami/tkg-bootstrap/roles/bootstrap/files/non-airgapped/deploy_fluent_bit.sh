#!/bin/bash
set -o errexit
# if argument passed as true deployment should start else no extension deployments
if [[ "$1" == "true" ]]; then
  # check if namespace is created
  source check_name_space.sh
  # fluent-bit, take out last fluent bit template version from package list
  tanzu package available list fluent-bit.tanzu.vmware.com |  awk '{if(NR>1)print $2}' > fluent_bit_version.txt
  bash version_check.sh fluent_bit_version.txt
  fluent_bit_version=`cat fluent_bit_version.txt`
  if [[ $TANZU_VERSION == v0.28.0 ]]; then
      # from TKG 2.1.0
      # --package-name has been changes to --package,
      tanzu package install fluent-bit --package fluent-bit.tanzu.vmware.com --namespace tanzu-packages --version $fluent_bit_version
  else
      tanzu package install fluent-bit --package-name fluent-bit.tanzu.vmware.com --namespace tanzu-packages --version $fluent_bit_version
  fi
fi