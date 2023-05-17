#!/bin/bash
set -o errexit
# if argument passed as true deployment should start else no extension deployments
if [[ "$1" == "true" ]]; then
    # make sure that cert-manger, contour is installed
    echo "deploying cert manager, as harbor is dependent on it....."
    source deploy_cert_manager.sh "true"
    echo "deploying contour, as harbor is dependent on it......"
    source deploy_contour.sh "true"
    # Harbor installation - To set your own passwords and secrets, update the following entries in the harbor-data-values.yaml file:
    # hostname , harborAdminPassword,secretKey,database.password,core.secret,core.xsrfKey,jobservice.secret,registry.secret
    # get latest available harbor package version for download
    tanzu package available list harbor.tanzu.vmware.com |  awk '{if(NR>1)print $2}' > harbor_version.txt
    bash version_check.sh harbor_version.txt
    harbor_version=`cat harbor_version.txt`

    # pull input yaml file for habor to update according to user
    image_url=$(kubectl -n tkg-system get packages harbor.tanzu.vmware.com.$harbor_version -o jsonpath='{.spec.template.spec.fetch[0].imgpkgBundle.image}')
    imgpkg pull -b $image_url -o /tmp/harbor-package-$harbor_version

    # copy yaml file inside current dir
    cp /tmp/harbor-package-$harbor_version/config/values.yaml ./harbor-data-values.yaml

    # generate random passwords for harbor yaml
    # hostname , harborAdminPassword,secretKey,database.password,core.secret,core.xsrfKey,jobservice.secret,registry.secret
    bash /tmp/harbor-package-$harbor_version/config/scripts/generate-passwords.sh harbor-data-values.yaml

    #update hostname inside yaml file
    yq eval -i '.hostname = env(HARBOR_HOSTNAME)' ./harbor-data-values.yaml
    #update harbor admin pasword
    yq eval -i '.harborAdminPassword = env(HARBOR_PASSWORD)' ./harbor-data-values.yaml
    # remove comments from yaml file
    yq -i eval '... comments=""' ./harbor-data-values.yaml
    if [[ $TANZU_VERSION == v0.28.1 ]]; then
      # from TKG 2.1.1
      # --package-name has been changes to --package,
      tanzu package install harbor --package harbor.tanzu.vmware.com --version $harbor_version --values-file harbor-data-values.yaml --namespace tanzu-packages
    else
      tanzu package install harbor --package-name harbor.tanzu.vmware.com --version $harbor_version --values-file harbor-data-values.yaml --namespace tanzu-packages
    fi
fi
