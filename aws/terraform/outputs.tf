output "private_dns" {
  description = "Private DNS Name for tkg bootstrap"
  value       = aws_instance.bootstrap.private_dns
}
output "public_ip" {
  description = "Public IP for tkg bootstrap for non-airgapped connection"
  value       = aws_instance.bootstrap.public_ip
}
