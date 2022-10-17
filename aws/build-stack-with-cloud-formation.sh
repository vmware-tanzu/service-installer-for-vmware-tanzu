#!/bin/bash
set -o errexit

check_roles_profile_policies()
{
  echo "Performing pre-checks on IAM Profiles, Roles and Policies"
  deleteProfiles=""
  deleteRoles=""
  deletePolicies=""
  # check if profiles are existing
  for profile in "${a_instance_profiles[@]}"; do   # The quotes are necessary here
    if ! aws iam get-instance-profile --instance-profile-name "${profile}" &> /dev/null; then
      echo "${profile} - profile not found"
    else
      deleteProfiles="${deleteProfiles} ${profile}"
    fi
  done
  #check if roles are existing
  for role in "${a_roles[@]}"; do   # The quotes are necessary here
    if ! aws iam get-role --role-name "${role}" &> /dev/null; then
      echo "${role} - role not found"
    else
      deleteRoles="${deleteRoles} ${role}"
    fi
  done
  #Check if policies are existing
  policiesOutput=$(aws iam list-policies --scope Local)
  while read name ; do
    if [[ "${a_policies[*]}" =~ ${name} ]]; then
      deletePolicies="${deletePolicies} ${name}";
      echo "${name} -> policy found";
    fi;
   done < <(echo "$policiesOutput" | jq  -r '.Policies[]|"\(.PolicyName)"')

  if [[ ! ("${deleteRoles}" == "") || ! ("${deleteProfiles}" == "") || ! ("${deletePolicies}" == "") ]] ;then
    echo "Pre-checks for cloudformation failed. Below listed IAM Profiles, Roles and Policies found are already created ,
    code will not going to create it, please make sure they are correctly created."
    if [ "${deleteRoles}" == "" ]; then echo "Roles - None"; else echo "Roles - ${deleteRoles}"; fi
    if [ "${deleteProfiles}" == "" ]; then echo "Profiles - None"; else echo "Profiles - ${deleteProfiles}"; fi
    if [ "${deletePolicies}" == "" ]; then echo "Policies - None"; else echo "Policies - ${deletePolicies}"; fi
    return 55
  else
    return 0
  fi

}

#TKG required roles/profile and polices creation using cloud formation stack
if ! aws cloudformation describe-stacks --stack-name tkg-aws-vmware-com > /dev/null; then
  a_instance_profiles=("control-plane.tkg.cloud.vmware.com" "controllers.tkg.cloud.vmware.com" "nodes.tkg.cloud.vmware.com" )
  a_roles=("control-plane.tkg.cloud.vmware.com" "controllers.tkg.cloud.vmware.com" "nodes.tkg.cloud.vmware.com")
  a_policies=("control-plane.tkg.cloud.vmware.com" "controllers.tkg.cloud.vmware.com" "nodes.tkg.cloud.vmware.com")
  if [[ "${DEPLOYMENT_ENVIRONMENT}" == "non-airgapped" ]]; then
    # to ignore return error from check_roles_profile_policies
    set +o errexit
    check_roles_profile_policies
  fi
  # if roles and policies are there, code will not create else it just show user a message
  if [ $? -eq 0 ]; then
    set -o errexit
    echo "Building cloudformation stack on AWS with name tkg-aws-vmware-com"
    aws cloudformation create-stack \
        --stack-name tkg-aws-vmware-com  \
        --template-body file://tanzu-cloud-formation-iamtemplate.yaml  \
        --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM;
    echo "Waiting for stack to finish creating";
    aws cloudformation wait stack-create-complete --stack-name tkg-aws-vmware-com;
    echo "Cloudformation creation is completed."
  fi
else
	echo "Cloud Formation named tkg-aws-vmware-com Already Exists";
fi
# SIVT automation required roles/profile and polices creation using cloud formation stack
if ! aws cloudformation describe-stacks --stack-name sivt-federal-aws-vmware-com > /dev/null; then
  instance_profiles=("tkg-s3-viewer" "tkg-bootstrap")
  roles=("tkg-s3-role" "tkg-bootstrap")
  policies=("tkg-airgapped-bucket")
  a_instance_profiles=( ${instance_profiles[@]/#/$AWS_DEFAULT_REGION-} )
  a_roles=( ${roles[@]/#/$AWS_DEFAULT_REGION-} )
  a_policies=( ${policies[@]/#/$AWS_DEFAULT_REGION-} )
  if [[ "$DEPLOYMENT_ENVIRONMENT" == "non-airgapped" ]]; then
    # to ignore return error from check_roles_profile_policies
    set +o errexit
    check_roles_profile_policies
  fi
  # if roles and policies are there, code will not create else it just show user a message
  if [ $? -eq 0 ]; then
    set -o errexit
    echo "Building cloudformation stack on AWS with name sivt-federal-aws-vmware-com"
    aws cloudformation create-stack \
          --stack-name sivt-federal-aws-vmware-com  \
          --template-body file://sivt-cloud-formation-iamtemplate.yaml  \
          --parameters ParameterKey=TKGBucketParameter,ParameterValue=$BUCKET_NAME \
          --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM;
    echo "Waiting for stack to finish creating";
    aws cloudformation wait stack-create-complete --stack-name sivt-federal-aws-vmware-com;
    echo "Cloudformation creation is completed."
  fi
else
        echo "Cloud Formation named sivt-federal-aws-vmware-com Already Exists";
fi