output "VPC_ID" {
  value = module.airgapped_vpc_setup.airgapped_vpc_id
}
output "SUBNET_ID" {
  value = module.airgapped_vpc_setup.airgapped_vpc_subnet_id
}
output "EC2_IP" {
  value = module.ec2_instance_setup.ec2_ip
}
output "AWS_AZ_ZONE" {
  value = module.airgapped_vpc_setup.az_zone
}