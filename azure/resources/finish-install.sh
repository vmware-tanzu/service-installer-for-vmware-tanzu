#!/usr/bin/env bash
# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
# If you're not using vmw-cli to download,
# You need to have
# - tanzu-cli-bundle-linux-amd64.tar
# - tmc
# - kubectl-linux-amd64*.gz with kubectl in it
# - yq
if [[ ! -f vmw-cli ]]; then
    if [[ $1 == "" || $2 == "" ]]; then
        echo "Usage: $0 <myvmwuser> <myvmwpass> [or prepopulate $HOME/vmw-cli with the binaries]"
        exit 1
    fi
export VMWUSER="$1"
export VMWPASS="$2"
cd  $HOME
git clone https://github.com/z4ce/vmw-cli
cd vmw-cli
curl -o tmc 'https://tmc-cli.s3-us-west-2.amazonaws.com/tmc/0.4.3-fcb03104/linux/x64/tmc'
./vmw-cli ls
./vmw-cli ls vmware_tanzu_kubernetes_grid
./vmw-cli cp tanzu-cli-bundle-linux-amd64.tar.gz
./vmw-cli cp "$(./vmw-cli ls vmware_tanzu_kubernetes_grid | grep kubectl-linux | cut -d ' ' -f1)"
curl -o yq -L https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
fi

sudo install yq /usr/local/bin
sudo install tmc /usr/local/bin/tmc
yes | tar --overwrite -xzvf tanzu-cli-bundle-linux-amd64.tar.gz
yes | gunzip kubectl-*.gz
sudo install kubectl-linux-* /usr/local/bin/kubectl
cd cli/
sudo install core/*/tanzu-core-linux_amd64 /usr/local/bin/tanzu
yes | gunzip *.gz
sudo install imgpkg-linux-amd64-* /usr/local/bin/imgpkg
sudo install kapp-linux-amd64-* /usr/local/bin/kapp
sudo install kbld-linux-amd64-* /usr/local/bin/kbld
sudo install vendir-linux-amd64-* /usr/local/bin/vendir
sudo install ytt-linux-amd64-* /usr/local/bin/ytt
cd ..

tanzu plugin sync
tanzu config init

# Install completion scripts on jumpbox to enhance operator joy
tanzu completion bash >  $HOME/.config/tanzu/completion.bash.inc
printf "\n# Tanzu shell completion\nsource '$HOME/.config/tanzu/completion.bash.inc'\n" >> $HOME/.bash_profile

kubectl completion bash > ~/.config/tanzu/kubectl-completion.bash.inc
printf "
  source '$HOME/.config/tanzu/kubectl-completion.bash.inc'
  " >> $HOME/.bash_profile


# Management cluster creation will show successful with package errors
# This is because pinniped isn't configured yet, but this allows us to
# configure pinniped later, whereas if we don't enable it, it cannot
# do it later.
cd $HOME/tkg-install
export MGMT_CLUSTER_NAME=$(yq '.CLUSTER_NAME' ./management-*.yaml)
tanzu management-cluster create --file ./management-*.yaml
tanzu management-cluster kubeconfig get --admin
if [[ "$TMC_API_TOKEN" != "" ]]; then

    # how to login to tmc with tmc token
    tmc login --no-configure --name tkgaws-automation
    tmc managementcluster register $MGMT_CLUSTER_NAME -p TKG -o tmc-mgmt.yaml --default-cluster-group default
    kubectl apply -f tmc-mgmt.yaml
fi

kubectl config use-context ${MGMT_CLUSTER_NAME}-admin@${MGMT_CLUSTER_NAME}
kubectl get pods -A

setup_cluster() {
 #$1: Filename
 #$2: Cluster name
FILE_NAME="$1"
export CLUSTER_NAME="$2"
tanzu cluster create $CLUSTER_NAME --file $FILE_NAME



tanzu cluster kubeconfig get $CLUSTER_NAME --admin
kubectl config use-context $CLUSTER_NAME-admin@$CLUSTER_NAME

# Start installing packages
kubectl create namespace tanzu-packages
# cert manager
tanzu package install cert-manager --package-name cert-manager.tanzu.vmware.com --namespace tanzu-packages --version 1.5.3+vmware.2-tkg.1


# contour ingress
tanzu package install contour \
--package-name contour.tanzu.vmware.com \
--version 1.17.1+vmware.1-tkg.1 \
--values-file contour-data-values.yaml \
--namespace tanzu-packages
# fluent-bit
tanzu package install fluent-bit --package-name fluent-bit.tanzu.vmware.com --namespace tanzu-packages --version 1.7.5+vmware.2-tkg.1
# tanzu package installed list -A

# install prometheus
tanzu package install prometheus \
--package-name prometheus.tanzu.vmware.com \
--version 2.27.0+vmware.2-tkg.1 \
--values-file prometheus-data-values.yaml \
--namespace tanzu-packages

# install grafana

tanzu package install grafana \
--package-name grafana.tanzu.vmware.com \
--version 7.5.7+vmware.2-tkg.1 \
--values-file grafana-data-values.yaml \
--namespace tanzu-packages


# Harbor installation - To set your own passwords and secrets, update the following entries in the harbor-data-values.yaml file:
# hostname , harborAdminPassword,secretKey,database.password,core.secret,core.xsrfKey,jobservice.secret,registry.secret

tanzu package install harbor \
--package-name harbor.tanzu.vmware.com \
--version 2.3.3+vmware.1-tkg.1 \
--values-file harbor-data-values.yaml \
--namespace tanzu-packages


if [[ "$TMC_API_TOKEN" != "" ]]; then

    # how to login to tmc with tmc token
    tmc login --no-configure --name tkgaws-automation
    # cluster login
#    tanzu cluster kubeconfig get $CLUSTER_NAME  --admin --export-file ./$CLUSTER_NAME_admin_conf.yaml
#    kubectl config use-context $CLUSTER_NAME-admin@$CLUSTER_NAME --kubeconfig ./$CLUSTER_NAME_admin_conf.yaml
    tmc managementcluster -m $MGMT_CLUSTER_NAME provisioner -p default tanzukubernetescluster manage --cluster-group default $CLUSTER_NAME
    # attached tmc cluster command
    # tmc cluster attach --name $CLUSTER_NAME --cluster-group default -k ./$CLUSTER_NAME_admin_conf.yaml

    if [[ "$TO_TOKEN" != "" ]]; then
        # install tanzu Observability steps - fill the template file tanzu-Observability-config.yaml config details
        perl -p -i.bak -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg' to-registration.yaml
        tmc cluster integration create -f to-registration.yaml
        mv to-registration.yaml.bak to-registration.yaml
        # check pod status
        # kubectl get pods -n tanzu-observability-saas
        # validate TO integration status
        # tmc cluster integration get tanzu-observability-saas --cluster-name tkg-wl-aws -m tkg-mgmt-aws -p tkg-mgmt-aws
    fi

    if [[ "$SKIP_TSM" == "" ]]; then
            perl -p -i.bak -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg' tsm-registration.yaml
            tmc cluster integration create -f tsm-registration.yaml
            mv tsm-registration.yaml.bak tsm-registration.yaml
    fi

fi
}

shopt -s nullglob
# Don't like the special cases here.. but we can make it better later
for i in workload-*.yaml; do
	CLUS_NAME=$(yq '.CLUSTER_NAME' $i)
        setup_cluster $i $CLUS_NAME

done