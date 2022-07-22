terraform{
backend "s3" {}
}
locals {
  amazon_airgap = "${var.base_os_family == "amazon-linux-2" ? "startup-airgapped-amazon-linux2.sh" : ""}"
  ubuntu_non_airgap = "${var.base_os_family == "non-airgapped-ubuntu" ? "startup-non-airgap-ubuntu-bootstrap.sh" : ""}"
  ubuntu_airgap = "${var.base_os_family != "non-airgapped-ubuntu" && var.base_os_family != "amazon-linux-2" ? "startup-airgapped-ubuntu.sh" : ""}"
  env = "${coalesce(local.amazon_airgap, local.ubuntu_non_airgap, local.ubuntu_airgap)}"
}
data "template_file" "init" {

  template = "${file(local.env)}"
  vars = {
    az_zone="${var.az_zone}"
    vpc_id="${var.vpc_id}"
    subnet_id="${var.subnet_id}"
    ssh_key_name="${var.ssh_key_name}"
    region="${var.region}"
    node_ami_id="${var.node_ami_id}"
    bucket_name="${var.bucket_name}"
    registry_name="${var.registry_name}"
    iam_role="${var.iam_role}"
    registry_ca_filename="${var.registry_ca_filename}"
    harbor_host_name="${var.harbor_host_name}"
    prometheus_host_name="${var.prometheus_host_name}"
    grafana_host_name="${var.grafana_host_name}"
    harbor_extension_password="${var.harbor_extension_password}"
    enable_identity_management = "${var.enable_identity_management}"
    identity_management_type = "${var.identity_management_type}"
    oidc_identity_provider_client_id = "${var.oidc_identity_provider_client_id}"
    oidc_identity_provider_client_secret="${var.oidc_identity_provider_client_secret}"
    oidc_identity_provider_groups_claim="${var.oidc_identity_provider_groups_claim}"
    oidc_identity_provider_issuer_url="${var.oidc_identity_provider_issuer_url}"
    oidc_identity_provider_scopes="${var.oidc_identity_provider_scopes}"
    oidc_identity_provider_username_claim="${var.oidc_identity_provider_username_claim}"
    ldap_host = "${var.ldap_host}"
    ldap_user_search_base_dn = "${var.ldap_user_search_base_dn}"
    ldap_group_search_base_dn = "${var.ldap_group_search_base_dn}"
    fips_enabled="${var.fips_enabled}"
    harbor_deployment="${var.harbor_deployment}"
    prometheus_deployment="${var.prometheus_deployment}"
    grafana_deployment="${var.grafana_deployment}"
    fluent_bit_deployment="${var.fluent_bit_deployment}"
    contour_deployment="${var.contour_deployment}"
    cert_manager_deployment="${var.cert_manager_deployment}"
    management_vpc_id="${var.management_vpc_id}"
    workload_vpc_id="${var.workload_vpc_id}"
    management_private_subnet_id_1="${var.management_private_subnet_id_1}"
    management_private_subnet_id_2="${var.management_private_subnet_id_2}"
    management_private_subnet_id_3="${var.management_private_subnet_id_3}"
    workload_private_subnet_id_1="${var.workload_private_subnet_id_1}"
    workload_private_subnet_id_2="${var.workload_private_subnet_id_2}"
    workload_private_subnet_id_3="${var.workload_private_subnet_id_3}"
    management_public_subnet_id_1="${var.management_public_subnet_id_1}"
    management_public_subnet_id_2="${var.management_public_subnet_id_2}"
    management_public_subnet_id_3="${var.management_public_subnet_id_3}"
    workload_public_subnet_id_1="${var.workload_public_subnet_id_1}"
    workload_public_subnet_id_2="${var.workload_public_subnet_id_2}"
    workload_public_subnet_id_3="${var.workload_public_subnet_id_3}"
    az_zone_1="${var.az_zone_1}"
    az_zone_2="${var.az_zone_2}"
    compliant_deployment="${var.compliant_deployment}"
    tmc_api_token="${var.tmc_api_token}"
    to_token="${var.to_token}"
    to_url="${var.to_url}"
    skip_to="${var.skip_to}"
    skip_tsm="${var.skip_tsm}"
  }
}

resource "aws_instance" "bootstrap" {
  ami                         = "${var.bs_ami_id}"
  key_name                    = "${var.ssh_key_name}"
  instance_type               = "t3.medium"
  iam_instance_profile        = "tkg-bootstrap"
  subnet_id                   = "${var.subnet_id}"
  vpc_security_group_ids      = ["${aws_security_group.default.id}"]
  root_block_device {
    volume_size = 10
  }
  tags = {
    Name = "tkg-bootstrap"
  }
  user_data = "${data.template_file.init.rendered}"
}
resource "aws_security_group" "default" {
  name        = "bootstrap-default-sg"
  description = "Default security group to allow inbound/outbound from the VPC"
  vpc_id      = "${var.vpc_id}"
  ingress {
    from_port = "0"
    to_port   = "0"
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port = "0"
    to_port   = "0"
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
