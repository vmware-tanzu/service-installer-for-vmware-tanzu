# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      CreatedBy = "Arcas"
    }
  }
  
}
