# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
# tkg init --config ./tkg-aws.yaml  -i aws -p prod --ceip-participation false --name iz-aws --cni antrea -v 6

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      CreatedBy = "SIVT AWS infra provisioner"
    }
  }
  ignore_tags {
    keys = ["kubernetes.io"]
  }
}


module "airgapped_vpc_setup" {
  source         = "./vpc_setup"
  vpc_name       = var.vpc_name
  vpc_cidr       = var.vpc_cidr
  region = var.region
  ssh_key_name   = var.ssh_key_name
  cluster_name   = var.vpc_name
  default_zone   = "${var.region}b"
}

module "vpce_setup" {
  source        = "./vpc_endpoints"
  airgapped_vpc_id      = "${module.airgapped_vpc_setup.airgapped_vpc_id}"
  airgapped_main_route_id      = "${module.airgapped_vpc_setup.airgapped_vpc_main_route_table_id}"
  region = var.region
  airgapped_bucket   = var.bucket_name
  airgapped_subnet_id = "${module.airgapped_vpc_setup.airgapped_vpc_subnet_id}"
  airgapped_security_group_id = "${module.airgapped_vpc_setup.airgapped_vpc_security_group_id}"

}

module "ec2_instance_setup" {
  source        = "./ec2_setup"
  airgapped_vpc_id      = "${module.airgapped_vpc_setup.airgapped_vpc_id}"
  airgapped_subnet_id = "${module.airgapped_vpc_setup.airgapped_vpc_subnet_id}"
  region = var.region
  ssh_key_name   = var.ssh_key_name
}
