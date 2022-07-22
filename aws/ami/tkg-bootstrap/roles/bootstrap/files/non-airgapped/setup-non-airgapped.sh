#!/bin/bash
set -o errexit
set -o allexport
source non-airgapped.env
if [ -n "$1" ]; then
  source $1
fi
set +o allexport
val=$(curl http://169.254.169.254/latest/meta-data/iam/security-credentials/$IAM_ROLE)
export AWS_ACCESS_KEY_ID="$(echo $val | jq -r .AccessKeyId)"
export AWS_SECRET_ACCESS_KEY="$(echo $val | jq -r .SecretAccessKey)"
export AWS_SESSION_TOKEN="$(echo $val | jq -r .Token)"
[[ -z "$AWS_REGION" ]] && {
  echo "AWS_REGION is not set extracting"
  EC2_AVAIL_ZONE=`curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone`
  export AWS_REGION="`echo \"$EC2_AVAIL_ZONE\" | sed 's/[a-z]$//'`"
}
TANZU_VERSION=$(tanzu version | head -n 1 | awk '{print $2}')
if [[ $TANZU_VERSION =~ ^v1.4.* ]]; then
  tanzu plugin install --local $CLI_DIR all
  cat internal_lb.yaml > ~/.config/tanzu/tkg/providers/ytt/03_customizations/internal_lb.yaml
  BASTION_SG=".status.network.securityGroups.bastion.id"
else
  tanzu plugin sync
  export AWS_LOAD_BALANCER_SCHEME_INTERNAL=true
  BASTION_SG=".status.networkStatus.securityGroups.bastion.id"
fi
tanzu config init
cp -r ../04_user_customizations $HOME/.config/tanzu/tkg/providers/ytt
if [[ $TANZU_VERSION == v0.11.1 ]]; then
  pushd /root/.config/tanzu/tkg/providers/ytt/02_addons/kapp-controller
    sed -i '25,28d' kapp-controller_overlay.lib.yaml
    sed -i '24d' kapp-controller_addon_data.lib.yaml
  popd
fi
source update-bom.sh
#managment cluster name to override env variable
export CLUSTER_NAME=$MANAGEMENT_CLUSTER_NAME
export AWS_VPC_ID=$MGMT_AWS_VPC_ID
# Management cluster PRIVATE SUBNET ID's for TKG Installation
export AWS_PRIVATE_SUBNET_ID=$MGMT_AWS_PRIVATE_SUBNET_ID
export AWS_PRIVATE_SUBNET_ID_1=$MGMT_AWS_PRIVATE_SUBNET_ID_1
export AWS_PRIVATE_SUBNET_ID_2=$MGMT_AWS_PRIVATE_SUBNET_ID_2
# Management cluster PUBLIC SUBNET ID's for TKG Installation
export AWS_PUBLIC_SUBNET_ID=$MGMT_AWS_PUBLIC_SUBNET_ID
export AWS_PUBLIC_SUBNET_ID_1=$MGMT_AWS_PUBLIC_SUBNET_ID_1
export AWS_PUBLIC_SUBNET_ID_2=$MGMT_AWS_PUBLIC_SUBNET_ID_2
tanzu management-cluster create

# switch context to management cluster
tanzu management-cluster kubeconfig get --admin

kubectl config use-context $MANAGEMENT_CLUSTER_NAME-admin@$MANAGEMENT_CLUSTER_NAME
# connect TMC
if [[ "$TMC_API_TOKEN" != "" ]]; then
    # download TMC
    curl -o tmc 'https://tmc-cli.s3-us-west-2.amazonaws.com/tmc/0.4.3-fcb03104/linux/x64/tmc'
    chown ubuntu:ubuntu tmc
    chmod +x tmc
    cp ./tmc /usr/local/bin/
    # how to login to tmc with tmc token
    tmc login --no-configure --name tkgaws-automation
    tmc managementcluster register $MANAGEMENT_CLUSTER_NAME -p TKG -o tmc-mgmt.yaml --default-cluster-group default
    kubectl apply -f tmc-mgmt.yaml
fi
# method to create workload cluster
setup_workload_cluster()
{
    # $1: work load cluster name for the deployment
    # $2: user input env file
  export WORK_CLUSTER_NAME=$1
  # creating workload cluster
  CLUSTER_NAME=$WORK_CLUSTER_NAME tanzu cluster create $WORK_CLUSTER_NAME

  # switch context to workload cluster
  tanzu cluster kubeconfig get $WORK_CLUSTER_NAME --admin
  kubectl config use-context $WORK_CLUSTER_NAME-admin@$WORK_CLUSTER_NAME
  # install tkg extensions
  source deploy_tkg_extensions.sh $2

  # connect TMC workload cluster
  if [[ "$TMC_API_TOKEN" != "" ]]; then

      # tmc configuration
      tmc login --no-configure --name tkgaws-automation
      # attached tmc cluster command
      tmc managementcluster -m $MANAGEMENT_CLUSTER_NAME provisioner -p default tanzukubernetescluster manage --cluster-group default $WORK_CLUSTER_NAME
       if [[ "$SKIP_TO" == "false" ]]; then
          # install tanzu Observability steps - fill the template file tanzu-Observability-config.yaml config details

          perl -p -i.bak -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg' to-registration.yaml
          tmc cluster integration create -f to-registration.yaml
          mv to-registration.yaml.bak to-registration.yaml
          # check pod status
          # kubectl get pods -n tanzu-observability-saas
          # validate TO integration status
          # tmc cluster integration get tanzu-observability-saas --cluster-name tkg-wl-aws -m $MGMT_CLUSTER_NAME -p $MGMT_CLUSTER_NAME
      fi
      if [[ "$SKIP_TSM" == "false" ]]; then
              perl -p -i.bak -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg' tsm-registration.yaml
              tmc cluster integration create -f tsm-registration.yaml
              mv tsm-registration.yaml.bak tsm-registration.yaml
      fi

  fi
}
# we need more than 4 CPU's if TSM integration needs to be done, thats why changing instance type
if [ ${TMC_API_TOKEN} != "" ] && [ "${SKIP_TSM}" == "false" ]; then
  export NODE_MACHINE_TYPE=$TSM_WORKER_MACHINE
  export NODE_MACHINE_TYPE_1=$TSM_WORKER_MACHINE
  export NODE_MACHINE_TYPE_2=$TSM_WORKER_MACHINE
fi
#Workload cluster name to override env variable
export AWS_VPC_ID=$WORKLOAD_AWS_VPC_ID
# Workload cluster PRIVATE SUBNET ID's for TKG Installation
export AWS_PRIVATE_SUBNET_ID=$WORKLOAD_AWS_PRIVATE_SUBNET_ID
export AWS_PRIVATE_SUBNET_ID_1=$WORKLOAD_AWS_PRIVATE_SUBNET_ID_1
export AWS_PRIVATE_SUBNET_ID_2=$WORKLOAD_AWS_PRIVATE_SUBNET_ID_2
# Workload cluster PUBLIC SUBNET ID's for TKG Installation
export AWS_PUBLIC_SUBNET_ID=$WORKLOAD_AWS_PUBLIC_SUBNET_ID
export AWS_PUBLIC_SUBNET_ID_1=$WORKLOAD_AWS_PUBLIC_SUBNET_ID_1
export AWS_PUBLIC_SUBNET_ID_2=$WORKLOAD_AWS_PUBLIC_SUBNET_ID_2
setup_workload_cluster $WORKLOAD_CLUSTER_NAME $1
# Workload cluster inside management VPC
export AWS_VPC_ID=$MGMT_AWS_VPC_ID
# Workload cluster PRIVATE SUBNET ID's for TKG Installation
export AWS_PRIVATE_SUBNET_ID=$MGMT_AWS_PRIVATE_SUBNET_ID
export AWS_PRIVATE_SUBNET_ID_1=$MGMT_AWS_PRIVATE_SUBNET_ID_1
export AWS_PRIVATE_SUBNET_ID_2=$MGMT_AWS_PRIVATE_SUBNET_ID_2
# Workload cluster PUBLIC SUBNET ID's for TKG Installation
export AWS_PUBLIC_SUBNET_ID=$MGMT_AWS_PUBLIC_SUBNET_ID
export AWS_PUBLIC_SUBNET_ID_1=$MGMT_AWS_PUBLIC_SUBNET_ID_1
export AWS_PUBLIC_SUBNET_ID_2=$MGMT_AWS_PUBLIC_SUBNET_ID_2
setup_workload_cluster $WORKLOAD_CLUSTER_NAME_2 $1