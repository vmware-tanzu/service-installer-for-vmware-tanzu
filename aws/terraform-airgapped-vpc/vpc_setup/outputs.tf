output "airgapped_vpc_id" {
  value = "${aws_vpc.airgapped_vpc.id}"
}

output "airgapped_vpc_main_route_table_id" {
  value = "${aws_vpc.airgapped_vpc.main_route_table_id}"
}

output "airgapped_vpc_subnet_id" {
  value = "${aws_subnet.airgapped_private_subnet.id}"
}

output "airgapped_vpc_security_group_id" {
  value = "${aws_vpc.airgapped_vpc.default_security_group_id}"
}

output "az_zone" {
  value = "${aws_subnet.airgapped_private_subnet.availability_zone}"
}