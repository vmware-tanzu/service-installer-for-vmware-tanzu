data "aws_ami" "amazon-linux-2" {
  most_recent = true
  owners = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-ebs"]
  }
}


resource "aws_instance" "airgapped_jumpbox_ec2" {
  ami                         = "${data.aws_ami.amazon-linux-2.id}"
  key_name                    = "${var.ssh_key_name}"
  instance_type               = "t3.xlarge"
  subnet_id                   = "${var.airgapped_subnet_id}"
  vpc_security_group_ids      = ["${aws_security_group.default.id}"]
  root_block_device {
    volume_size = 50
  }
  tags = {
   Name = "airgapped_jumpbox_ec2"
  }
}

resource "aws_security_group" "default" {
  name        = "jumpbox-ec2-default-sg"
  description = "Default security group to allow inbound/outbound from the VPC"
  vpc_id      = "${var.airgapped_vpc_id}"
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
