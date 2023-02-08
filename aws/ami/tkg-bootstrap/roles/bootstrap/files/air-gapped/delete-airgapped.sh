#! /bin/bash
set -o allexport
source airgapped.env
source user-airgapped.env
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
export TKG_CUSTOM_IMAGE_REPOSITORY_CA_CERTIFICATE=$(base64 -w 0 /etc/docker/certs.d/$OFFLINE_REGISTRY/ca.crt)
export TKG_CUSTOM_IMAGE_REPOSITORY_CA_PATH="/etc/docker/certs.d/$OFFLINE_REGISTRY/ca.crt"
[[ -z "$TKG_CUSTOM_IMAGE_REPOSTIORY" ]] && {
   echo "TKG_CUSTOM_IMAGE_REPOSITORY not set setting to $OFFLINE_REGISTRY/tkg"
   export TKG_CUSTOM_IMAGE_REPOSITORY=$OFFLINE_REGISTRY/tkg
}
export TKG_CUSTOM_IMAGE_REPOSITORY_SKIP_TLS_VERIFY=false
echo "Unsetting bastion security group from bootstrap"
instance_id=$(curl -XGET http://169.254.169.254/latest/meta-data/instance-id)
security_groups=$(curl -XGET http://169.254.169.254/latest/meta-data/security-groups| grep -v $MANAGEMENT_CLUSTER_NAME-bastion | grep -v $WORKLOAD_CLUSTER_NAME-bastion)
default_sg=$(aws ec2 describe-security-groups --region=$AWS_REGION | jq -r --arg security_groups "$security_groups" '.SecurityGroups[] | select(.GroupName==$security_groups) | .GroupId' | tr -d '"')
aws ec2 modify-instance-attribute --instance-id $instance_id --groups $default_sg --region $AWS_REGION
echo "updated bootstrap to have following security groups: $default_sg"
kubectl config use-context ${MANAGEMENT_CLUSTER_NAME}-admin@${MANAGEMENT_CLUSTER_NAME}
kubectl delete cluster -n default --all
tanzu management-cluster delete ${MANAGEMENT_CLUSTER_NAME} --yes
