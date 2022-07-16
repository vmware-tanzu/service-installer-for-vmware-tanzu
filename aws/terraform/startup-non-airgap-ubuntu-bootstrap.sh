#! /bin/bash
cat << DELIMIT > /home/ubuntu/non-airgapped/user-inputs.env
## Edit the below Defaults to modify your air gapped env. You can also add in any envs found in tanzu cluster config
#AMI_ID to use when launching tkg not the bootstrap ami. If STIG will be stig_ami_id
AMI_ID=${node_ami_id}
# Management Cluster VPC ID for TKG Installation
MGMT_AWS_VPC_ID=${management_vpc_id}
# Workload Cluster VPC ID for TKG Installation
WORKLOAD_AWS_VPC_ID=${workload_vpc_id}
# Management cluster PRIVATE SUBNET ID's for TKG Installation
MGMT_AWS_PRIVATE_SUBNET_ID=${management_private_subnet_id_1}
MGMT_AWS_PRIVATE_SUBNET_ID_1=${management_private_subnet_id_2}
MGMT_AWS_PRIVATE_SUBNET_ID_2=${management_private_subnet_id_3}
# Management cluster PUBLIC SUBNET ID's for TKG Installation
MGMT_AWS_PUBLIC_SUBNET_ID=${management_public_subnet_id_1}
MGMT_AWS_PUBLIC_SUBNET_ID_1=${management_public_subnet_id_2}
MGMT_AWS_PUBLIC_SUBNET_ID_2=${management_public_subnet_id_3}
# Workload cluster PRIVATE SUBNET ID's for TKG Installation
WORKLOAD_AWS_PRIVATE_SUBNET_ID=${workload_private_subnet_id_1}
WORKLOAD_AWS_PRIVATE_SUBNET_ID_1=${workload_private_subnet_id_2}
WORKLOAD_AWS_PRIVATE_SUBNET_ID_2=${workload_private_subnet_id_3}
# Workload cluster PUBLIC SUBNET ID's for TKG Installation
WORKLOAD_AWS_PUBLIC_SUBNET_ID=${workload_public_subnet_id_1}
WORKLOAD_AWS_PUBLIC_SUBNET_ID_1=${workload_public_subnet_id_2}
WORKLOAD_AWS_PUBLIC_SUBNET_ID_2=${workload_public_subnet_id_3}
# AWS ZONE
AWS_NODE_AZ=${az_zone}
AWS_NODE_AZ_1=${az_zone_1}
AWS_NODE_AZ_2=${az_zone_2}
# IAM Role that is attached to IAM Instance Profile
IAM_ROLE=${iam_role}
MANAGEMENT_CLUSTER_NAME=tkg-mgmnt
WORKLOAD_CLUSTER_NAME=tkg-workload
WORKLOAD_CLUSTER_NAME_2=tkg-workload-2
#Pulled from tfvars to be same as bootstrap ssh key
AWS_SSH_KEY_NAME=${ssh_key_name}
#Pulled from tfvars to be same as bootstrap region
AWS_REGION=${region}
CLUSTER_PLAN="prod"
ENABLE_AUDIT_LOGGING="true"
ENABLE_SERVING_CERTS="false"
PROTECT_KERNEL_DEFAULTS="true"
HARBOR_DEPLOYMENT="${harbor_deployment}"
PROMETHEUS_DEPLOYMENT="${prometheus_deployment}"
GRAFANA_DEPLOYMENT="${grafana_deployment}"
FLUENT_BIT_DEPLOYMENT="${fluent_bit_deployment}"
CONTOUR_DEPLOYMENT="${contour_deployment}"
CERT_MANGER_DEPLOYMENT="${cert_manager_deployment}"
# TMC Communication token
TMC_API_TOKEN="${tmc_api_token}"
# TO token
TO_URL="${to_url}"
TO_TOKEN="${to_token}"
SKIP_TO="${skip_to}"
SKIP_TSM="${skip_tsm}"
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
if [ ${fips_enabled} == "true" ] && [ "${compliant_deployment}" == "true" ]; then
	echo -e "TKG_CUSTOM_COMPATIBILITY_IMAGE_PATH=fips/tkg-compatibility" >> /home/ubuntu/non-airgapped/user-inputs.env
	echo -e "COMPLIANCE=\"stig\"" >> /home/ubuntu/non-airgapped/user-inputs.env
fi
# hostname and password for tkg extensions if not set then don't use it
if [[ -n "${harbor_host_name}" ]]; then
	echo -e "HARBOR_HOSTNAME=${harbor_host_name}" >> /home/ubuntu/non-airgapped/user-inputs.env
fi
if [[ -n "${prometheus_host_name}" ]]; then
	echo -e "PROMETHEUS_HOSTNAME=${prometheus_host_name}" >> /home/ubuntu/non-airgapped/user-inputs.env
fi
if [[ -n "${grafana_host_name}" ]]; then
	echo -e "GRAFANA_HOSTNAME=${grafana_host_name}" >> /home/ubuntu/non-airgapped/user-inputs.env
fi
if [[ -n "${harbor_extension_password}" ]]; then
	echo -e "HARBOR_PASSWORD=${harbor_extension_password}" >> /home/ubuntu/non-airgapped/user-inputs.env
fi
if [[ -n "${harbor_extension_password}" ]]; then
	echo -e "HARBOR_PASSWORD=${harbor_extension_password}" >> /home/ubuntu/non-airgapped/user-inputs.env
fi
if [[ "${enable_identity_management}" == "true" ]]; then
  if [[ "${identity_management_type}" == "ldap" ]]; then
    echo -e "IDENTITY_MANAGEMENT_TYPE=${identity_management_type}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "LDAP_HOST=${ldap_host}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "LDAP_USER_SEARCH_BASE_DN=${ldap_user_search_base_dn}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "LDAP_GROUP_SEARCH_BASE_DN=${ldap_group_search_base_dn}" >> /home/ubuntu/non-airgapped/user-inputs.env
  elif [[ "${identity_management_type}" == "oidc" ]]; then
    echo -e "IDENTITY_MANAGEMENT_TYPE=${identity_management_type}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "OIDC_IDENTITY_PROVIDER_CLIENT_ID=${oidc_identity_provider_client_id}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "OIDC_IDENTITY_PROVIDER_CLIENT_SECRET=${oidc_identity_provider_client_secret}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "OIDC_IDENTITY_PROVIDER_GROUPS_CLAIM=${oidc_identity_provider_groups_claim}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "OIDC_IDENTITY_PROVIDER_ISSUER_URL=${oidc_identity_provider_issuer_url}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "OIDC_IDENTITY_PROVIDER_SCOPES=${oidc_identity_provider_scopes}" >> /home/ubuntu/non-airgapped/user-inputs.env
    echo -e "OIDC_IDENTITY_PROVIDER_USERNAME_CLAIM=${oidc_identity_provider_username_claim}" >> /home/ubuntu/non-airgapped/user-inputs.env
  else
    echo "Invalid identity management type provided for Pinniped - ${identity_management_type}"
  fi
fi
cd /home/ubuntu/non-airgapped
sudo bash setup-non-airgapped.sh user-inputs.env
