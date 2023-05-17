output "ec2_ip" {
  value = aws_instance.airgapped_jumpbox_ec2.private_ip
}