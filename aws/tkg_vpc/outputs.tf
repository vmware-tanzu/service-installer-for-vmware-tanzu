# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause

output "vpc_id" {
  value = aws_vpc.main.id
}
output "subnet_ids" {
  value = [aws_subnet.priv_a.id, aws_subnet.priv_b.id, aws_subnet.priv_c.id]
}
output "priv_subnet_a" {
  value = aws_subnet.priv_a.id
}
output "priv_subnet_b" {
  value = aws_subnet.priv_b.id
}
output "priv_subnet_c" {
  value = aws_subnet.priv_c.id
}
output "pub_subnet_a" {
  value = aws_subnet.pub_a.id
}
output "pub_subnet_b" {
  value = aws_subnet.pub_b.id
}
output "pub_subnet_c" {
  value = aws_subnet.pub_c.id
}

output "az1" {
  value = var.azs[0]
}
output "az2" {
  value = var.azs[1]
}
output "az3" {
  value = var.azs[2]
}
output "jumpbox_dns" {
  value = aws_eip.bar[*].public_ip
}
output "jumpbox_ip" {
  value = var.jumpbox ? aws_instance.ubuntu[0].public_ip : ""
}
