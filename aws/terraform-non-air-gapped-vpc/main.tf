# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
# tkg init --config ./tkg-aws.yaml  -i aws -p prod --ceip-participation false --name iz-aws --cni antrea -v 6

terraform {
  backend "s3" {}
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
      CreatedBy = "SIVT AWS"
    }
  }
  ignore_tags {
    keys = ["kubernetes.io"]
  }
}

variable "region" {
}

variable "ssh_key_name" {
}

variable "control_plane_cidr" {
  default = "172.16.0.0/16"
}

variable "worker_cidr" {
  default = "172.19.0.0/16"
}

variable "transit_block" {
  default = "172.16.0.0/12"
}

resource "aws_ec2_transit_gateway" "transitgw" {
  description = "transit gw"
}


module "management_vpc" {
  source        = "./infra_create"
  vpc_subnet    = var.control_plane_cidr
  transit_gw    = aws_ec2_transit_gateway.transitgw.id
  transit_block = var.transit_block
  name          = "management-vpc"
  jb_key_pair   = var.ssh_key_name
  cluster_name   = "management-vpc"
  azs           = ["${var.region}a", "${var.region}b", "${var.region}c"]
}

module "workload_vpc" {
  source        = "./infra_create"
  vpc_subnet    = var.worker_cidr // avoiding .17 and .18 so that we don't conflict with docker
  transit_gw    = aws_ec2_transit_gateway.transitgw.id
  transit_block = var.transit_block
  name          = "workload-vpc"
  cluster_name  = "workload-vpc"
  azs           = ["${var.region}a", "${var.region}b", "${var.region}c"]
  jb_key_pair   = var.ssh_key_name

}
