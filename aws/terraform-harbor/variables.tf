variable "vpc_id" {
  description = "VPC id that bootstrap runs in" 
}
variable "region" {
  description = "region that bootstrap and tkg runs in" 
}
variable "subnet_id" {
  description = "subnet id that bootstrap runs in" 
}
variable "ssh_key_name" {
  default = "default"
  description = "ssh_key_name to use for bootstrap and aws"
}
variable "create_certs" {
  default = "true"
  description = "Whether or not to make self signed certs"
}
variable "harbor_pwd" {
  default = "H@rborPwd123"
  description = "Harbor Admin Password"
}
variable "cert_l" {
  default = "Minneapolis"
  description = "L in cert CN(city/location)"
}
variable "cert_st" {
  default = "Minnesota"
  description = "ST in cert CN(state)"
}
variable "cert_o" {
  default = "VmWare"
  description = "O in cert CN(Organization)"
}
variable "cert_ou" {
  default = "VmWare R&D"
  description = "OU in cert CN(Organizational Unit"
}
variable "cert_path" {
  default = ""
  description = "Path to cert if not creating own"
}
variable "cert_key_path" {
  default = ""
  description = "Path to private key if not creating own"
}
variable "cert_ca_path" {
  default = ""
  description = "Path to ca file if not creating own"
}
variable "bucket_name" {
  default = ""
  description = "Bucket with tkg debs"
}
variable "tkg_version" {
  default = "v1.5.1"
  description = "TKG Version"
}
variable "tkr_version" {
  default = "v1.22.5"
  description = "TKR Version short name"
}