# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
module "subnet_addrs" {
  source = "hashicorp/subnets/cidr"

  base_cidr_block = var.vpc_subnet
  networks = [
    {
      name     = "az1_public"
      new_bits = 8
    },
    {
      name     = "az2_public"
      new_bits = 8
    },
    {
      name     = "az3_public"
      new_bits = 8
    },
    {
      name     = "az3_jumpnet"
      new_bits = 8
    },
  ]
}


# Create a VPC
resource "aws_vpc" "main" {
  cidr_block = var.vpc_subnet
  tags = {
    Name = "${var.name}"
  }

}


resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "pub_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = module.subnet_addrs.network_cidr_blocks.az1_public
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags                    = { "kubernetes.io/cluster/${var.cluster_name}" = "true", "kubernetes.io/role/elb" = "1", Name = "pub-a" }
}
resource "aws_subnet" "pub_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = module.subnet_addrs.network_cidr_blocks.az2_public
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true
  tags                    = { "kubernetes.io/cluster/${var.cluster_name}" = "true", "kubernetes.io/role/elb" = "1", Name = "pub-b" }
}
resource "aws_subnet" "pub_c" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = module.subnet_addrs.network_cidr_blocks.az3_public
  availability_zone       = "${var.aws_region}c"
  map_public_ip_on_launch = true
  tags                    = { "kubernetes.io/cluster/${var.cluster_name}" = "true", "kubernetes.io/role/elb" = "1", Name = "pub-c" }
}
resource "aws_eip" "nat" {
  vpc = true
}

resource "aws_nat_gateway" "gw" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.pub_a.id
  depends_on    = [aws_internet_gateway.gw]
}


resource "aws_route_table_association" "pub-1a" {
  subnet_id      = aws_subnet.pub_a.id
  route_table_id = aws_route_table.r.id
}

resource "aws_route_table_association" "pub-1b" {
  subnet_id      = aws_subnet.pub_b.id
  route_table_id = aws_route_table.r.id
}

resource "aws_route_table_association" "pub-1c" {
  subnet_id      = aws_subnet.pub_c.id
  route_table_id = aws_route_table.r.id
}

resource "aws_route_table" "p" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.gw.id
  }

  tags = {
    Name = "${var.name}-nat"
  }
}


resource "aws_route_table" "r" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "${var.name}-igw"
  }
}
