variable "vpc_name" {
  default = "sivt-airgapped-vpc"
  description = "Name for the VPC which going to be provisioned"
}

variable "vpc_cidr" {
  default = "10.1.0.0/16"
  description = "Name for the VPC which going to be provisioned"
}

variable "region" {
  description = "Name of the default region where Airgapped infra provision needs to started"
}

variable "ssh_key_name" {
  description = "SSH key pair for EC2 launch"
}

variable "bucket_name" {
  description = "Bucket name to be create for S3 dependencies"
}

