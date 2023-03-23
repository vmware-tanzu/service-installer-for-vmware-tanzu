variable "vpc_id" {
  description = "VPC id that bootstrap runs in" 
}
variable "az_zone" {
  description = "AZ Zone to deploy k8s into" 
}
variable "region" {
  description = "region that bootstrap and tkg runs in" 
}
variable "subnet_id" {
  description = "subnet id that bootstrap runs in" 
}
variable "bs_ami_id" {
  description = "ami id of the bootstrap server"
}
variable "node_ami_id" {
  description = "ami id of tkg cluster nodes"
}
variable "ssh_key_name" {
  default = "default"
  description = "ssh_key_name to use for bootstrap and aws"
}
variable "bucket_name" {
  description = "s3 bucket name that contains ca with role called bucket_name-viewer"
}
variable "registry_name" {
  description = "dns name of docker registry"
  default = "projects.registry.vmware.com"
}
variable "iam_role" {
  description = "Name of IAM Role that is attached to iam instance profile"
  default = "tkg-bootstrap"
}
variable "registry_ca_filename" {
  description = "Name of ca file for private registry"
  default = "ca.crt"
}
variable "harbor_host_name" {
  description = "Name of hostname to be used for harbor extension"
}
variable "prometheus_host_name" {
  description = "Name of hostname to be used for prometheus extension"
}
variable "grafana_host_name" {
  description = "Name of hostname to be used for grafana extension"
}
variable "harbor_extension_password" {
  description = "Password to be used for harbor extension"
}
variable "enable_identity_management" {
  description = "Set it to true to enable Pinniped"
}
variable "identity_management_type" {
  description = "Identity management type, this must be oidc or ldap"
}
variable "ldap_host" {
  description = "The IP or DNS address of your LDAP server"
}
variable "ldap_user_search_base_dn" {
  description = "The point from which to start the LDAP search"
}
variable "ldap_group_search_base_dn" {
  description = "The point from which to start the LDAP search"
}
variable "oidc_identity_provider_client_id" {
  description = "The client_id value that you obtain from your OIDC provider"
}
variable "oidc_identity_provider_client_secret" {
  description = "The Base64 secret value that you obtain from your OIDC provider."
}
variable "oidc_identity_provider_groups_claim" {
  description = "The name of your groups claim. This is used to set a user’s group in the JSON Web Token (JWT) claim."
}
variable "oidc_identity_provider_issuer_url" {
  description = "The IP or DNS address of your OIDC server."
}
variable "oidc_identity_provider_scopes" {
  description = "A comma separated list of additional scopes to request in the token response."
}
variable "oidc_identity_provider_username_claim" {
  description = "The name of your username claim."
}
variable "fips_enabled" {
  description = "Whether or not the tkg version you are using has fips enabled"
  default = "true"
}
variable "base_os_family" {
  description = "Name of base os for TKG installer node OS"
  default =  "ubuntu"
}
variable "harbor_deployment" {
  description = "harbor as extension deployment on workload cluster or not"
  default = "false"
}
variable "prometheus_deployment" {
  description = "prometheus as extension deployment on workload cluster or not"
  default = "false"
}
variable "grafana_deployment" {
  description ="grafana as extension deployment on workload cluster or not"
  default = "false"
}
variable "fluent_bit_deployment" {
  description = "fluent bit as extension deployment on workload cluster or not"
  default = "false"
}
variable "contour_deployment" {
  description = "contour as extension deployment on workload cluster or not"
  default = "true"
}
variable "cert_manager_deployment" {
  description = "cert manager as extension deployment on workload cluster or not"
  default = "true"
}
variable "management_vpc_id" {
  description = "Non-airgapped Management Cluster VPC ID"
  default = ""
}
variable "workload_vpc_id" {
  description = "Non-airgapped Workload Cluster VPC ID"
  default = ""
}
variable "management_private_subnet_id_1" {
  description = "Non-airgapped Management Cluster Private Subnet ID 1"
  default = ""
}
variable "management_private_subnet_id_2" {
  description = "Non-airgapped Management Cluster Private Subnet ID 2"
  default = ""
}
variable "management_private_subnet_id_3" {
  description = "Non-airgapped Management Cluster Private Subnet ID 3"
  default = ""
}
variable "workload_private_subnet_id_1" {
  description = "Non-airgapped Workload Cluster Private Subnet ID 1"
  default = ""
}
variable "workload_private_subnet_id_2" {
  description = "Non-airgapped Workload Cluster Private Subnet ID 2"
  default = ""
}
variable "workload_private_subnet_id_3" {
  description = "Non-airgapped Workload Cluster Private Subnet ID 3"
  default = ""
}
variable "management_public_subnet_id_1" {
  description = "Non-airgapped Management Cluster Public Subnet ID 1"
  default = ""
}
variable "management_public_subnet_id_2" {
  description = "Non-airgapped Management Cluster Public Subnet ID 2"
  default = ""
}
variable "management_public_subnet_id_3" {
  description = "Non-airgapped Management Cluster Public Subnet ID 3"
  default = ""
}
variable "workload_public_subnet_id_1" {
  description = "Non-airgapped Workload Cluster Public Subnet ID 1"
  default = ""
}
variable "workload_public_subnet_id_2" {
  description = "Non-airgapped Workload Cluster Public Subnet ID 2"
  default = ""
}
variable "workload_public_subnet_id_3" {
  description = "Non-airgapped Workload Cluster Public Subnet ID 3"
  default = ""
}
variable "az_zone_1" {
  description = "AWS Zone 2 for HA"
  default = ""
}
variable "az_zone_2" {
  description = "AWS Zone 3 for HA"
  default = ""
}
variable "compliant_deployment" {
  description = "Non airgapped Complaint Deployment checks to perform compliant deployment or not"
}
variable "tmc_api_token" {
  description = "TMC API Token for clusters handling"
  default=""
}
variable "to_token" {
  description = "Tanzu Observability API Token for clusters handling"
  default=""
}
variable "to_url" {
  description = "Tanzu Observability URL for clusters handling"
  default=""
}
variable "skip_to" {
  description = "SKIP TO deployment"
  default=""
}
variable "skip_tsm" {
  description = "SKIP TSM deployment"
  default=""
}