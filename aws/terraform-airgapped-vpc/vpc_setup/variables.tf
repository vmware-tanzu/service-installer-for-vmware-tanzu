variable "vpc_name" {
  description = "Name for the VPC which going to be provisioned"
}

variable "cluster_name" {
  description = "Name for the VPC which going to be provisioned"
}

variable "vpc_cidr" {
  description = "Name for the VPC which going to be provisioned"
}

variable "region" {
  description = "Name of the default region where Airgapped infra provision needs to started"
}

variable "default_zone" {
  description = "Name of the default availability zone where Airgapped infra provision needs to started"
}

variable "ssh_key_name" {
}
