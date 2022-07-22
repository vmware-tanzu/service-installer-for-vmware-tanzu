#!/bin/bash
set -o errexit

if ! aws cloudformation describe-stacks --stack-name sivt-federal-aws-vmware-com > /dev/null; then
    #echo "Performing pre-checks on IAM Profiles, Roles and Policies"
    #deleteProfiles=""
    #deleteRoles=""
    #deletePolicies=""
    #profilesAndRoles=("control-plane.tkg.cloud.vmware.com" "controllers.tkg.cloud.vmware.com" "nodes.tkg.cloud.vmware.com" "tkg-s3-viewer" "tkg-bootstrap")
    #roles=("control-plane.tkg.cloud.vmware.com" "controllers.tkg.cloud.vmware.com" "nodes.tkg.cloud.vmware.com" "tkg-s3-role" "tkg-bootstrap")
    #policies=("control-plane.tkg.cloud.vmware.com" "controllers.tkg.cloud.vmware.com" "nodes.tkg.cloud.vmware.com" "tkg-airgapped-bucket")

    #check if profiles are existing
    #for profile in "${profilesAndRoles[@]}"; do   # The quotes are necessary here
    #    if ! aws iam get-instance-profile --instance-profile-name "${profile}" &> /dev/null; then
    #      echo "${profile} - profile not found"
    #    else
    #      deleteProfiles="${deleteProfiles} ${profile}"
    #    fi
    #done

    #check if roles are existing
    #for role in "${roles[@]}"; do   # The quotes are necessary here
    #    if ! aws iam get-role --role-name "${role}" &> /dev/null; then
    #      echo "${role} - role not found"
    #    else
    #     deleteRoles="${deleteRoles} ${role}"
    #    fi
    #done

    #Check if policies are existing
    #policiesOutput=$(aws iam list-policies --scope Local)
    #while read name ; do
    #  if [[ "${policies[*]}" =~ ${name} ]]; then
    #    deletePolicies="${deletePolicies} ${name}";
        #echo "${name} -> policy found";
   #     fi;
   #   done < <(echo "$policiesOutput" | jq  -r '.Policies[]|"\(.PolicyName)"')

   # if [[ ! ("${deleteRoles}" == "") || ! ("${deleteProfiles}" == "") || ! ("${deletePolicies}" == "") ]] ;then
   #   echo "Pre-checks for cloudformation failed. Please delete below listed IAM Profiles, Roles and Policies and retry."
   #   if [ "${deleteRoles}" == "" ]; then echo "Roles - None"; else echo "Roles - ${deleteRoles}"; fi
   #   if [ "${deleteProfiles}" == "" ]; then echo "Profiles - None"; else echo "Profiles - ${deleteProfiles}"; fi
   #   if [ "${deletePolicies}" == "" ]; then echo "Policies - None"; else echo "Policies - ${deletePolicies}"; fi
   # else
      echo "Building cloudformation stack on AWS with name sivt-federal-aws-vmware-com"
      aws cloudformation create-stack \
        --stack-name sivt-federal-aws-vmware-com  \
        --template-body file://cloud-formation-iamtemplate  \
        --parameters ParameterKey=TKGBucketParameter,ParameterValue=$BUCKET_NAME \
        --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM;
      echo "Waiting for stack to finish creating";
      aws cloudformation wait stack-create-complete --stack-name sivt-federal-aws-vmware-com;
      echo "Cloudformation creation is completed."
   # fi
else
	echo "Cloud Formation named sivt-federal-aws-vmware-com Already Exists";
fi