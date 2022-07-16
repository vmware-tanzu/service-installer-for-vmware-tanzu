terraform{
backend "s3" {}
}

data "template_file" "init" {
  template = "${file("startup.sh")}"

  vars = {
    region="${var.region}"
    bucket_name="${var.bucket_name}"
    cert_path="${var.cert_path}"
    cert_key_path="${var.cert_key_path}"
    cert_ca_path="${var.cert_ca_path}"
    create_certs="${var.create_certs}"
    cert_st="${var.cert_st}"
    cert_l="${var.cert_l}"
    cert_o="${var.cert_o}"
    cert_ou="${var.cert_ou}"
    harbor_pwd="${var.harbor_pwd}"
    tkg_version="${var.tkg_version}"
    tkr_version="${var.tkr_version}"
  }
}
data "aws_ami" "amazon-linux-2" {
  most_recent = true
  owners = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-ebs"]
  }
}

resource "aws_instance" "harbor" {
  ami                         = "${data.aws_ami.amazon-linux-2.id}"
  key_name                    = "${var.ssh_key_name}"
  instance_type               = "t3.medium"
  iam_instance_profile        = "tkg-s3-viewer"
  subnet_id                   = "${var.subnet_id}"
  vpc_security_group_ids      = ["${aws_security_group.default.id}"]
  root_block_device {
    volume_size = 50
  }
  tags = {
   Name = "harbor-tkg"
  }
  user_data = "${data.template_file.init.rendered}"
}
resource "aws_security_group" "default" {
  name        = "harbor-default-sg"
  description = "Default security group to allow inbound/outbound from the VPC"
  vpc_id      = "${var.vpc_id}"
  ingress {
    from_port = "0"
    to_port   = "0"
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port = "0"
    to_port   = "0"
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
