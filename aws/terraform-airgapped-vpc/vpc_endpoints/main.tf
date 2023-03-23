resource "aws_vpc_endpoint" "s3" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.s3"
  route_table_ids = [var.airgapped_main_route_id]
  vpc_endpoint_type = "Gateway"
}

resource "aws_vpc_endpoint" "ec2" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.ec2"
  subnet_ids = [var.airgapped_subnet_id]
  security_group_ids = [var.airgapped_security_group_id]
  private_dns_enabled = true
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "ec2_messages" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.ec2messages"
  subnet_ids = [var.airgapped_subnet_id]
  security_group_ids = [var.airgapped_security_group_id]
  private_dns_enabled = true
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "elastic_load_balancing" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.elasticloadbalancing"
  subnet_ids = [var.airgapped_subnet_id]
  security_group_ids = [var.airgapped_security_group_id]
  private_dns_enabled = true
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "ssm" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.ssm"
  subnet_ids = [var.airgapped_subnet_id]
  security_group_ids = [var.airgapped_security_group_id]
  private_dns_enabled = true
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "cloudformation" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.cloudformation"
  subnet_ids = [var.airgapped_subnet_id]
  security_group_ids = [var.airgapped_security_group_id]
  private_dns_enabled = true
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.secretsmanager"
  subnet_ids = [var.airgapped_subnet_id]
  security_group_ids = [var.airgapped_security_group_id]
  private_dns_enabled = true
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "ssm-messages" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.ssmmessages"
  subnet_ids = [var.airgapped_subnet_id]
  security_group_ids = [var.airgapped_security_group_id]
  private_dns_enabled = true
  vpc_endpoint_type = "Interface"
}

resource "aws_vpc_endpoint" "sts" {
  vpc_id       = var.airgapped_vpc_id
  service_name = "com.amazonaws.${var.region}.sts"
  subnet_ids = [var.airgapped_subnet_id]
  security_group_ids = [var.airgapped_security_group_id]
  private_dns_enabled = true
  vpc_endpoint_type = "Interface"
}

resource "aws_s3_bucket" "airgapped_bucket" {
  bucket = var.airgapped_bucket
  force_destroy = true
}

resource "aws_s3_bucket_policy" "allow_access_from_another_account" {
  bucket = aws_s3_bucket.airgapped_bucket.id
  policy = jsonencode({
      "Version" = "2012-10-17"
      "Statement" = [
        {
          "Sid" = "Access-to-specific-VPCE-only"
          "Effect" = "Allow"
          "Principal" = "*"
          "Action" = "s3:GetObject"
          "Resource" = "arn:aws:s3:::${aws_s3_bucket.airgapped_bucket.bucket}/*"
          "Condition" = {
              "StringEquals" = {
                "aws:sourceVpce" = "${aws_vpc_endpoint.s3.id}"
              }
          }
        }
      ]
    })
}


resource "aws_s3_bucket_public_access_block" "example" {
  bucket = aws_s3_bucket.airgapped_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}