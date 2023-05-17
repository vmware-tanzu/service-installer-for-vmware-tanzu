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

variable "name" {
  default = "nonameset"
}
variable "jb_key_pair" {
}
variable "transit_gw" {
}
variable "transit_block" {
}
variable "cluster_name" {
}
