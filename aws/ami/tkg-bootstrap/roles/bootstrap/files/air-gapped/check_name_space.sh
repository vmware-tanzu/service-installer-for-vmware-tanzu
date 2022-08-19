#!/bin/bash
set +o errexit
name_space=$(kubectl get  namespace tanzu-packages)
if [[ "$name_space" == *tanzu-packages* ]]; then
        echo "namespace already has been created"
else
        # Start installing packages inside namespace
        echo "creating namespace named tanzu-packages"
        kubectl create namespace tanzu-packages
fi
set -o errexit