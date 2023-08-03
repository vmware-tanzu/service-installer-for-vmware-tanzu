output "vpc_id" {
  value = aws_vpc.main.id
}
output "private_subnet" {
  value = aws_subnet.priv_a.id
}
output "private_subnet_1" {
  value = aws_subnet.priv_b.id
}
output "private_subnet_2" {
  value = aws_subnet.priv_c.id
}
output "public_subnet" {
  value = aws_subnet.pub_a.id
}
output "public_subnet_1" {
  value = aws_subnet.pub_b.id
}
output "public_subnet_2" {
  value = aws_subnet.pub_c.id
}
output "availability_zone" {
  value = aws_subnet.pub_a.availability_zone
}
output "availability_zone_1" {
  value = aws_subnet.pub_b.availability_zone
}
output "availability_zone_2" {
  value = aws_subnet.pub_c.availability_zone
}
