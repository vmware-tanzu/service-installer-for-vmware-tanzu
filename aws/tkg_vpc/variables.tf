# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
variable "vpc_subnet" {
  default     = "192.168.0.0/16"
  description = "The vpc subnet"
  type        = string
}

variable "azs" {
  default     = ["us-east-2a", "us-east-2b", "us-east-2c"]
  description = "List of VPCs"
  type        = list(string)
}
variable "jumpbox" {
  default     = false
  description = "jumpbox? true/false"
  type        = bool
}

variable "jumpbox_ip" {
  default     = ""
  description = "if provided along with jb_key_pair and jb_keyfile, will create a file for installing into this vpc"
  type        = string
}

variable "name" {
  default = "nonameset"
}
variable "jb_key_pair" {
  default = "tkg-kp"
}

variable "jb_keyfile" {
  default = "~/tkg-kp.pem"
}

variable "cluster_name" {
  default = "tkg-mgmt-aws"
}

variable "transit_gw" {
}
variable "transit_block" {
}

variable "harbor_admin_password" {
  default = ""
} 