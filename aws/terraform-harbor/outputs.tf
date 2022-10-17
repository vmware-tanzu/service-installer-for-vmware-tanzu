output "private_dns" {
  description = "Private DNS Name for harbor"
  value       = aws_instance.harbor.private_dns
}
