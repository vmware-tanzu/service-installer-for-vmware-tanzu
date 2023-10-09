variable "vpc_subnet" {
  default = "172.16.0.0/16"
  description = "Subnet range for the VPC"
}
variable "jumpbox" {
  default = "true"
  description = "region that bootstrap and tkg runs in" 
}
variable "name" {
  default = "tkg-sivt-aws-vpc"
  description = "Name of the VPC to be created"
}
variable "cluster_name" {
  default = "tkg-mgmt-aws"
  description = "cluster name"
}
variable "aws_region" {
  default = "us-west-2"
  description = "AWS region for creating VPC"
}