#!/bin/bash
set -o errexit
set -o allexport
source airgapped.env
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
[[ -z "$AWS_VPC_ID" ]] && {
  echo "AWS_VPC_ID is not set extracting"
  macid=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/)
  export AWS_VPC_ID=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/${macid}/vpc-id)
}
if [[ -z "$AWS_PRIVATE_SUBNET_ID" ]] && [[ $CLUSTER_PLAN == "dev" ]]; then
  echo "AWS_PRIVATE_SUBNET_ID is not set and cluster plan is dev extracting"
  macid=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/)
  export AWS_PRIVATE_SUBNET_ID=$(curl http://169.254.169.254/latest/meta-data/network/interfaces/macs/${macid}/subnet-id)
fi
mkdir -p /etc/docker/certs.d/$OFFLINE_REGISTRY/
#check for OS and copy certificates accordingly
os_version=$(grep -E -w 'NAME' /etc/os-release | awk -F "=" '{print $2}')
if [[ "$os_version" == *Amazon* ]]; then
  cp /etc/pki/ca-trust/source/anchors/$REGISTRY_CA_FILENAME /etc/docker/certs.d/$OFFLINE_REGISTRY/
else
  cp /usr/local/share/ca-certificates/$REGISTRY_CA_FILENAME /etc/docker/certs.d/$OFFLINE_REGISTRY/
fi
systemctl restart docker
export TKG_CUSTOM_IMAGE_REPOSITORY_CA_PATH="/etc/docker/certs.d/$OFFLINE_REGISTRY/$REGISTRY_CA_FILENAME"
export TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE=$(base64 -w 0 /etc/docker/certs.d/$OFFLINE_REGISTRY/$REGISTRY_CA_FILENAME)
[[ -z "$TKG_CUSTOM_IMAGE_REPOSTIORY" ]] && {
   echo "TKG_CUSTOM_IMAGE_REPOSITORY not set setting to $OFFLINE_REGISTRY/tkg"
   export TKG_CUSTOM_IMAGE_REPOSITORY=$OFFLINE_REGISTRY/tkg
}
export TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY=false

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
REGISTRY_IP=$(nslookup $OFFLINE_REGISTRY | awk -F': ' 'NR==6 { print $2 } ')
REGISTRY_IP_ESC=$(sed 's/[\*\.]/\\&/g' <<<"$REGISTRY_IP")
OFFLINE_REGISTRY_ESC=$(sed 's/[\*\.]/\\&/g' <<<"$OFFLINE_REGISTRY")
sed -i.bak "s/PRIVATE-REGISTRY-IP/$REGISTRY_IP_ESC/g; s/PRIVATE-REGISTRY-HOSTNAME/$OFFLINE_REGISTRY_ESC/g" iaas-overlay.yaml
sed -i.bak "s/PRIVATE-REGISTRY-IP/$REGISTRY_IP_ESC/g; s/PRIVATE-REGISTRY-HOSTNAME/$OFFLINE_REGISTRY_ESC/g" tkr_overlay.lib.yaml
cat iaas-overlay.yaml >>  ~/.config/tanzu/tkg/providers/infrastructure-$INFRASTRUCTURE_PROVIDER/ytt/$INFRASTRUCTURE_PROVIDER-overlay.yaml
cp tkr_overlay.lib.yaml  ~/.config/tanzu/tkg/providers/ytt/03_customizations/01_tkr/tkr_overlay.lib.yaml
#workload cluster name to override env variable
export CLUSTER_NAME=$MANAGEMENT_CLUSTER_NAME
tanzu management-cluster create

# switch context to management cluster
tanzu management-cluster kubeconfig get --admin

kubectl config use-context $MANAGEMENT_CLUSTER_NAME-admin@$MANAGEMENT_CLUSTER_NAME
# creating workload cluster
CLUSTER_NAME=$WORKLOAD_CLUSTER_NAME tanzu cluster create $WORKLOAD_CLUSTER_NAME

echo "Updating bootstrap security groups to allow ssh to new clusters, workload as well as management"
instance_id=$(curl -XGET http://169.254.169.254/latest/meta-data/instance-id)
security_groups=$(curl -XGET http://169.254.169.254/latest/meta-data/security-groups)
management_bastion_sg=$(kubectl get awsclusters -n tkg-system $MANAGEMENT_CLUSTER_NAME -o=custom-columns=bastionId:$BASTION_SG --no-headers)
workload_bastion_sg=$(kubectl get awsclusters -n default $WORKLOAD_CLUSTER_NAME -o=custom-columns=bastionId:$BASTION_SG --no-headers)
default_sg=$(aws ec2 describe-security-groups --region=$AWS_REGION | jq -r --arg security_groups "$security_groups" '.SecurityGroups[] | select(.GroupName==$security_groups) | .GroupId' | tr -d '"')
aws ec2 modify-instance-attribute --instance-id $instance_id --groups $management_bastion_sg $workload_bastion_sg $default_sg --region $AWS_REGION
echo "updated bootstrap to have following security groups: $default_sg $management_bastion_sg $workload_bastion_sg"

# switch context to workload cluster
tanzu cluster kubeconfig get $WORKLOAD_CLUSTER_NAME --admin
kubectl config use-context $WORKLOAD_CLUSTER_NAME-admin@$WORKLOAD_CLUSTER_NAME
# install tkg extensions
source deploy_tkg_extensions.sh $1