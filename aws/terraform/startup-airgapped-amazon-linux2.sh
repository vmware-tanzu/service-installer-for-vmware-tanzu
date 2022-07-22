#! /bin/bash
cat << DELIMIT > /home/ec2-user/air-gapped/user-airgapped.env
## Edit the below Defaults to modify your air gapped env. You can also add in any envs found in tanzu cluster config
#AMI_ID to use when launching tkg not the bootstrap ami. If STIG will be stig_ami_id
AMI_ID=${node_ami_id}
# Name of CA file for image registry defaults to ca.crt
REGISTRY_CA_FILENAME=${registry_ca_filename}
# s3 bucket with registry ca cert
BUCKET_NAME=${bucket_name}
# IAM Role that is attached to IAM Instance Profile
IAM_ROLE=${iam_role}
AWS_NODE_AZ=${az_zone}
MANAGEMENT_CLUSTER_NAME=airgapped-mgmnt
WORKLOAD_CLUSTER_NAME=airgapped-workload
#Pulled from tfvars to be same as bootstrap ssh key
AWS_SSH_KEY_NAME=${ssh_key_name}
#Pulled from tfvars to be same as bootstrap region
AWS_REGION=${region}
## DNS NAME of docker registry only change if user provided registry
OFFLINE_REGISTRY=${registry_name}
#CLI_DIR=/home/ec2-user/packages/cli
#TKG_CUSTOM_IMAGE_REPOSITORY="$OFFLINE_REGISTRY/tkg"
CLUSTER_PLAN="dev"
ENABLE_AUDIT_LOGGING="true"
COMPLIANCE="stig"
ENABLE_SERVING_CERTS="false"
PROTECT_KERNEL_DEFAULTS="true"
HARBOR_DEPLOYMENT="${harbor_deployment}"
PROMETHEUS_DEPLOYMENT="${prometheus_deployment}"
GRAFANA_DEPLOYMENT="${grafana_deployment}"
FLUENT_BIT_DEPLOYMENT="${fluent_bit_deployment}"
CONTOUR_DEPLOYMENT="${contour_deployment}"
CERT_MANGER_DEPLOYMENT="${cert_manager_deployment}"
#AWS_VPC_ID=Defaults to vpc bootstrap runs in
#AWS_PRIVATE_SUBNET_ID=Defaults to subnet bootstrap uses if cluster plan is dev
#####REQUIRED FOR CLUSTER PLAN PRODUCTION
#AWS_NODE_AZ_1=
#AWS_NODE_AZ_2=
#AWS_PRIVATE_SUBNET_ID_1=
#AWS_PRIVATE_SUBNET_ID_2=
#CONTROL_PLANE_MACHINE_TYPE=
#NODE_MACHINE_TYPE=
#SERVICE_CIDR=
#CLUSTER_CIDR=
DELIMIT
# if user set fips enabled settings for TKG images
if [[ ${fips_enabled} == "true" ]]; then
	echo -e "TKG_CUSTOM_COMPATIBILITY_IMAGE_PATH=fips/tkg-compatibility" >> /home/ec2-user/air-gapped/user-airgapped.env
fi
# hostname and password for tkg extensions if not set then don't use it
if [[ -n "${harbor_host_name}" ]]; then
	echo -e "HARBOR_HOSTNAME=${harbor_host_name}" >> /home/ec2-user/air-gapped/user-airgapped.env
fi
if [[ -n "${prometheus_host_name}" ]]; then
	echo -e "PROMETHEUS_HOSTNAME=${prometheus_host_name}" >> /home/ec2-user/air-gapped/user-airgapped.env
fi
if [[ -n "${grafana_host_name}" ]]; then
	echo -e "GRAFANA_HOSTNAME=${grafana_host_name}" >> /home/ec2-user/air-gapped/user-airgapped.env
fi
if [[ -n "${harbor_extension_password}" ]]; then
	echo -e "HARBOR_PASSWORD=${harbor_extension_password}" >> /home/ec2-user/air-gapped/user-airgapped.env
fi
if [[ "${enable_identity_management}" == "true" ]]; then
  if [[ "${identity_management_type}" == "ldap" ]]; then
    echo -e "IDENTITY_MANAGEMENT_TYPE=${identity_management_type}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "LDAP_HOST=${ldap_host}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "LDAP_USER_SEARCH_BASE_DN=${ldap_user_search_base_dn}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "LDAP_GROUP_SEARCH_BASE_DN=${ldap_group_search_base_dn}" >> /home/ec2-user/air-gapped/user-airgapped.env
  elif [[ "${identity_management_type}" == "oidc" ]]; then
    echo -e "IDENTITY_MANAGEMENT_TYPE=${identity_management_type}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "OIDC_IDENTITY_PROVIDER_CLIENT_ID=${oidc_identity_provider_client_id}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "OIDC_IDENTITY_PROVIDER_CLIENT_SECRET=${oidc_identity_provider_client_secret}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "OIDC_IDENTITY_PROVIDER_GROUPS_CLAIM=${oidc_identity_provider_groups_claim}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "OIDC_IDENTITY_PROVIDER_ISSUER_URL=${oidc_identity_provider_issuer_url}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "OIDC_IDENTITY_PROVIDER_SCOPES=${oidc_identity_provider_scopes}" >> /home/ec2-user/air-gapped/user-airgapped.env
    echo -e "OIDC_IDENTITY_PROVIDER_USERNAME_CLAIM=${oidc_identity_provider_username_claim}" >> /home/ec2-user/air-gapped/user-airgapped.env
  else
    echo "Invalid identity management type provided for Pinniped - ${identity_management_type}"
  fi
fi
cd /home/ec2-user/air-gapped
sudo bash setup-airgapped.sh user-airgapped.env
