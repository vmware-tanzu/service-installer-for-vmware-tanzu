# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
output "management_vpc_id" {
  value = module.management_vpc.vpc_id
}
output "workload_vpc_id" {
  value = module.workload_vpc.vpc_id
}
output "management_private_subnet_id_1" {
  value = module.management_vpc.private_subnet
}
output "management_private_subnet_id_2" {
  value = module.management_vpc.private_subnet_1
}
output "management_private_subnet_id_3" {
  value = module.management_vpc.private_subnet_2
}
output "workload_private_subnet_id_1" {
  value = module.workload_vpc.private_subnet
}
output "workload_private_subnet_id_2" {
  value = module.workload_vpc.private_subnet_1
}
output "workload_private_subnet_id_3" {
  value = module.workload_vpc.private_subnet_2
}
output "management_public_subnet_id_1" {
  value = module.management_vpc.public_subnet
}
output "management_public_subnet_id_2" {
  value = module.management_vpc.public_subnet_1
}
output "management_public_subnet_id_3" {
  value = module.management_vpc.public_subnet_2
}
output "workload_public_subnet_id_1" {
  value = module.workload_vpc.public_subnet
}
output "workload_public_subnet_id_2" {
  value = module.workload_vpc.public_subnet_1
}
output "workload_public_subnet_id_3" {
  value = module.workload_vpc.public_subnet_2
}
output "az_zone" {
  value = module.management_vpc.availability_zone
}
output "az_zone_1" {
  value = module.management_vpc.availability_zone_1
}
output "az_zone_2" {
  value = module.management_vpc.availability_zone_2
}