# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
module "subnet_addrs" {
  source = "hashicorp/subnets/cidr"

  base_cidr_block = var.vpc_cidr
  networks = [
    {
      name     = "private_subnet"
      new_bits = 8
    }
  ]
}


# Create a VPC
resource "aws_vpc" "airgapped_vpc" {
  cidr_block = var.vpc_cidr
  enable_dns_hostnames = true
  tags = {
    Name = "${var.vpc_name}"
  }

}

resource "aws_subnet" "airgapped_private_subnet" {
  vpc_id            = aws_vpc.airgapped_vpc.id
  cidr_block        = module.subnet_addrs.network_cidr_blocks.private_subnet
  availability_zone = var.default_zone
  tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "true",
    "kubernetes.io/role/internal-elb"           = "1",
    Name                                        = "airgapped_private_subnet"
  }
}

resource "aws_route_table_association" "route_table_and_subnet" {
  subnet_id      = aws_subnet.airgapped_private_subnet.id
  route_table_id = aws_vpc.airgapped_vpc.main_route_table_id
}

resource "aws_default_security_group" "default" {
  vpc_id = aws_vpc.airgapped_vpc.id

  ingress {
    from_port = "0"
    to_port   = "0"
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
