#! /bin/bash
set -o allexport
source non-airgapped.env
source user-inputs.env
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
kubectl config use-context ${MANAGEMENT_CLUSTER_NAME}-admin@${MANAGEMENT_CLUSTER_NAME}
kubectl delete cluster -n default --all
tanzu management-cluster delete ${MANAGEMENT_CLUSTER_NAME} --yes
#cleanup K8S elb remaining security groups, leftover of cluster deletion
while IFS= read -r line; do
  echo "Deleting security_groups $line"
  aws ec2 delete-security-group --group-id $line --region $AWS_REGION
done < <(aws ec2 describe-security-groups --filters Name=description,Values="Security group for Kubernetes ELB*" --region $AWS_REGION --query SecurityGroups[*].[GroupId] --output text)
# delete tmc cluster
if [[ "$TMC_API_TOKEN" != "" ]]; then
  echo "Deleting management cluster from tmc"
  tmc mc delete ${MANAGEMENT_CLUSTER_NAME} -f
fi