#!/bin/bash
set -o errexit
wait_timer=0
echo "looking ca cert inside s3 bucket path is:" \
     "s3://${TF_VAR_bucket_name}/harbor/ca.crt; ....."
if [ -z ${USE_EXISTING_REGISTRY+x} ]; then
  : "${TF_VAR_bucket_name?TF_VAR_bucket_name is not set}"
  until aws s3 ls s3://"$TF_VAR_bucket_name"/harbor/ca.crt; do
    echo  Harbor still starting waiting 60 seconds
    sleep 60
    # sometime harbor don't comes up due to some errors, waiting for harbor to come up in an hour
    wait_timer=$(($wait_timer+1))
    if [ $wait_timer -eq 60 ];
    then
      echo "harbor not comes up in an hour please login to harbor machine <> and" \
      "check /var/log/cloud-init-output.log"; exit 1;
    fi

  done
  echo "harbor is up and running reading its dns name...."
  pushd terraform-harbor &> /dev/null
     REGISTRY=$(terraform output -json | jq -r .private_dns.value)
     echo "harbor is running at ${REGISTRY}...."
     export REGISTRY
  popd &> /dev/null
  if [[ $1 == "--download-ca" ]]; then
    : "${BUCKET_NAME?BUCKET_NAME is not set}"
    : "${REGISTRY_CA_FILENAME?REGISTRY_CA_FILENAME is not set}"
    echo "downloading ca cert from the bucket...."
    aws s3 cp s3://"${BUCKET_NAME}"/harbor/ca.crt ami/tkg-bootstrap/roles/bootstrap/files/ca/"${REGISTRY_CA_FILENAME}" > /dev/null
		cp ami/tkg-bootstrap/roles/bootstrap/files/ca/"${REGISTRY_CA_FILENAME}" ami/stig/roles/canonical-ubuntu-18.04-lts-stig-hardening/files/ca/"${REGISTRY_CA_FILENAME}" > /dev/null
  fi
fi
echo "${REGISTRY}" > registry.txt