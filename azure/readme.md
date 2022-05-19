<!--
# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
-->
# TKGm Private Deployment on Azure Playbook

Based on the Reference Architecture, [TKO on Azure Hybrid-Cloud](https://github.com/vmware-tanzu-labs/tanzu-validated-solutions/blob/main/src/reference-designs/tko-on-azure-hybrid.md)

# Quick install

Configure your TMC instance with Tanzu Observability and Tanzu Service Mesh integrations before running the quick install.

Run 
```bash
az login
./tkgm-azure.sh <subscription_id> <tenant_id>
cd 3_bootstrap
ssh -o IdentitiesOnly=yes -i ./bootstrap.pem azureuser@xxx
```

Run the ssh command provided to access the jumpbox. On the jumpbox run

```bash
cd tkg-install
export TO_URL="http://your-wavefront-url"
export TO_TOKEN="your-wavefront-token"
export TMC_TOKEN="your-tmc-token"
chmod a+x ./finish-install.sh
./finish-install.sh <myvmw_username> <myvmw_password>
```

If you set `export SKIP_TSM=true`, the installation will skip installing TSM. If you do not set `TO_TOKEN`, the installation will skip installing Tanzu Observability. If you do not set `TMC_TOKEN`, the installation will skip TMC, TO, and TSM.

# Repository Contents

This repository is broken into 4 components:

* Keepers - defines long lasting components that are used by terraform
* Netsec - defines subnets, network security groups, and VNETs
* DNS - Used for Hybrid Azure deployments (not the quick install)
* Bootstrap - Used to create the jumpbox and prepopulate the jumpbox with relevant configuration

Each section is documented with its own README. The break out of sections is designed to align with separation of duties
as necessary to allow each team to apply the terraform for their responsibilities.

If you are unable to use the wrapper to install TKGm, you can follow this playbook to achieve the same results, or modify source code as necessary to achieve the changes you need.

1. Apply Terraform code in 0_keepers
    - `terraform apply -var="sub_id=..." -var="tenant_id=..."`
    - _where ... above represent your respective values_

1. Execute the run_cmd output instructions from 0_keepers
    - OS requirements will vary
    - e.g. `export ARM_ACCESS_KEY="$(terraform output -raw access_key)"`
    - e.g. `$env:ARM_ACCESS_KEY=(terraform output -raw access_key)`

1. Apply Terraform code in 1_netsec
    - `terraform apply -var="sub_id=..."`
    - _where ... above represent your respective values_

1. Apply Terraform code in 2_dns (as-needed)
    - This option only applies if you need an non-Azure source to resolve Azure Private DNS
    - `terraform apply -var="sub_id=..."`
    - _where ... above represent your respective values_

1. Apply Terraform code in 3_bootstrap
    - `terraform apply -var="sub_id=..."`
    - _where ... above represent your respective values_
    - ssh_cmd output will vary by OS, so mind your rules (if you're on Windows, you'll probably have to fix the ACLs on this file)

## TLDR

Modify terraform.tfvars as necessary for each TF config directory. Anything uncommented or otherwise added to the tfvars file will override defaults and effectively escape the validation deployment that is the default. If the architecture of the code is maintained, then changes to 0_keepers will carry forward into subsequent steps.

## Terraform, Infrastructure as Code

The examples given were designed to use an Azure Storage Account as a remote backend for Terraform's state management. "Keepers" below, is a prerequisite and does not get stored in a remote state (in fact, it establishes a place remote state can be stored).

The following components are divided in such a way that steps can be skipped if the answers to those features are provided by another, either pre-existent service or Central IT-provided. Each component supplies a set of resources that are intended to be passed forward, ideally through secret storage within a secure vault.

The components are as follows:

> Terraform runtime:
>
>- _Terraform v1.17_*
>- _hashicorp/azurerm v2.98.0_*

\* _See individual component directories for updates to these versions._

* Keepers
* Network and Network Security
* DNS (Intermediate)
* Deployment Prerequisites
* Tanzu Bootstrap

**In most cases of automation, we are making some assumptions on the consumer's behalf. I have tried to highlight those (outside of variables) below in case you need to modify those opinions!**

### Assumptions

**Tag Names** - In addition to those listed within the terraform.tfvars files, "StartDate" is in use within the code as an _origin date_ in case it's important to track that for resources. It's set once when the resource is created, and it should never be changed thereafter (by Terraform). Additional tags can be added to the map var type in terraform.tfvars.

**Azure Cloud** - This has never been built for anything outside of the standard "AzureCloud." Your mileage may vary on China or Government types.

**Naming** - the naming practice used herein could follow [published Microsoft Cloud Adoption Framework](https://docs.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming). In short, that's:  
> `<resource-type>-<app>-<env>-<region>-###`

You will likely have to modify this to fit your customer's needs. The liberties I've taken over this framework are as follows:  
> `<resource-type>-<bu>-<app>-<env>-<region-abbrv>-###`
where _###_ is useful where multiples are generated (automatic). Otherwise, it's not used. What's more, the naming standard is entirely based upon the various _prefix_ vars collected in terraform.tfvars. You are allowed to format those prefixes however you like, so the the rules above are just suggestions. The only enforcement takes place at the resource level where _\<resource-type\>_ is prepended to your prefix per Microsoft's guidelines where applicable, and suffixes are added in situations to maintain uniqueness.

- Resource-Type is aligned to [Microsoft published guidelines](https://docs.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-abbreviations) where possible
- region-abbrv can (and shoulbe) be an abbreviation. These examples are country-first and 4 characters:

> `East US 2 = use2`

**Modules** - Modules used herein are the epitome of assumptions. These modules have been constructed to perform a set of tasks against categorical resources to produce standardization. This is because they represent those parts of an organization that may perform work on the TKGm platform owner's behalf. For instance, the subnet modules can create route tables and associate NSGs as well. The important part of these modules is ultimately the output, and therefore you may arrive at these outputs in any number of ways.

### Keepers

> "Keepers" are those resources that preempt the state-managed resources deployed by Terraform for this solution. They do not need to be dedicated to the TKGm solution! Keepers currently include a **Storage Account** for state and an **Azure Key Vault** for secret storage.

**IMPORTANT** Update [terraform.tfvars](0_keepers/terraform.tfvars) for your environment

#### keepers - providers

Providers are maintained for all deployment directories out of the keepers directory. provider.tftpl is used to construct those files in future directories, so it's important to understand that relationship.
#### keepers - terraform.tfvars

- **sub\_id**: Azure Subscription ID
- **location**: Azure Region (_e.g. eastus2 or East US 2_)
- **prefix**: A prefix to resource names using your naming standards (_e.g. vmw-use2-svcname_)
- **prefix_short**: Some resources are limited in size and characters - this prefix solves for those (_e.g. vmwuse2svc_). **Can include 4-digits of randomized hexadecimal at the end**

> Tag values default to tags defined at the Subscription level, but are designed to be overriden by anything provided here

- **ServiceName**: Free text to name or describe your application, solution, or service
- **BusinessUnit**: Should align with a predetermined list of known BUs
- **Environment**: Should align with a predetermined list of environments
- **OwnerEmail**: A valid email for a responsible person or group of the resource(s)
- \<Optional Tags\>: _Such as RequestorEmail_

```Shell
**from the 0_keepers sub-directory**
terraform init
terraform validate
terraform apply
```

### Network and Security

> NetSec should be replaced by a solution wherein the Central IT team provides these details where necessary. Specifically, Central IT should build the VNET to be in compliance with ExpressRoute requirements and allow the development team to add their own subnets and Network Security Groups (see [Azure Landing Zones](https://docs.microsoft.com/en-us/azure/cloud-adoption-framework/ready/enterprise-scale/architecture))

**IMPORTANT** Update `terraform.tfvars` for your environment.

- **storage\_account\_name:** Storage account named pulled from the keepers.json where terraform state will be stored in perpetuity
- **container\_name:** Like a folder - generally "terraform-state"
- **key:** Further pathing for the storage and filename of your terraform state - must be unique (e.g. `bu/product/use2-s-net.tfstate`)
- **access\_key:** This can be found in your `keepers.json` and is the access_key credential used to read and write against the keeper storage account - SENSITIVE

#### netsec - terraform.tfvars (In addition to others listed previously...)

- **tkg\_cluster\_name:** The name passed into naming pertaining to the tanzu cli
- **core\_address\_space:** The VNET address space - it's the largest CIDR block specified for a network
- **boot\_diag\_sa\_name:** This name is passed to a storage account that is used for boot diagnostics - it should conform to Azure's naming requirements for storage accounts
- **vault_resource_group_name:** A Resource Group name provided by the output of `0_keepers`
- **vault_name:** The AKV name provided by the output of `0_keepers`

#### netsec - user_subnets.tf

This file is used to define the subnets used for TKGm and configure the subnets within Azure. Examples are provided, but the results are as follows (as defined within the associated modules):

> Subnets are modified via the large local map that is passed into the subnet module. Maps provided this way can either be passed in directly as a single map answering the argument requirement of the module, or the module can be looped through while reading each key from the map. In the former case, all subnets will get the same NSG. In the latter, each subnet gets its own NSG. NSGs are named within the map itself, so care should be given to that parameter.

```Shell
**from the 1_netsec sub-directory**
terraform init
terraform validate
terraform apply
```

### DNS

> DNS, in this solution, represents a BIND9 forwarder for Azure Private DNS. In order for on-prem resources to resolve Private DNS resources, conditional or zone forwarding must be in place on-prem to point to these DNS servers.

**IMPORTANT** Update `terraform.tfvars` for your environment

#### dns - terraform.tfvars (In addition to others listed above...)

- **subnet\_name:** Subnet name where DNS Forwarders will allocate internal IP(s) (output from `1_netsec`)
- **vnet\_name:** The VNET name (pre-existing - is output from `1_netsec`)
- **netsec\_resource\_group:** The resource group name where the pre-existing VNET lives
- **bindvms:** Count of VMs to deploy to host BIND9
- **boot\_diag\_sa\_name:** Pre-generated boot diagnostics storage account name (output from `1_netsec`)

```bash
**from the 2_dns sub-directory**
terraform init
terraform validate
terraform apply
```

## Tanzu Kubernetes Grid Automation

### Bootstrap VM (3_bootstrap)

> The Bootstrap VM is used for TKGm deployment activities and is setup from the start with the tanzu CLI and related binaries.
>
> **NOTE:** The bootstrap VM should be provided outbound access to the Internet during initial deployment to perform updates and pull software packages necessary for its role. The default deployment in this guide makes use of a NAT Gateway for the VNET and associated subnets to extend that.
>

**IMPORTANT** Update `terraform.tfvars` for your environment

#### boot - terraform.tfvars (In addition to others listed above...)

- **subnet\_name:** Subnet name where the bootstrap VM will allocate an internal IP (output from `1_netsec`)
- **vnet\_name:** The VNET name (pre-existing - is output from `1_netsec`)
- **netsec\_resource\_group:** The resource group name where the pre-existing VNET lives
- **boot\_diag\_sa\_name:** Pre-generated boot diagnostics storage account name (output from `1_netsec`)

```Shell
**from the 3_bootstrap sub-directory**
terraform init
terraform validate
terraform apply
```

> Creating the first management cluster is done through "kind" on the bootstrap VM and outputs from IaC above (captured in Azure KeyVault) should be compiled for the resultant answer files.

### Final Steps

Shell environment variables will need to be set for proxy configuration, and may be passed via the tfvars file as well:

```bash
export HTTP_PROXY="http://PROXY:PORT"
export HTTPS_PROXY="http://PROXY:PORT"
export NO_PROXY="CIDR_OR_DOMAIN_LIST"
```

Docker proxy config will need to be set. Add the following section to /etc/systemd/system/docker.service.d/http-proxy.conf:

```ini
[Service]
    Environment="HTTP_PROXY=http://PROXY:PORT"
    Environment="HTTPS_PROXY=http://PROXY:PORT"
    Environment="NO_PROXY=CIDR_OR_DOMAIN_LIST"
```

> **NOTE:** Docker will need to be restarted for this setting to take effect.

Apt does not use environmental proxy configurations, and instead uses its own file. You will need to modify (create as-needed) the file /etc/apt/apt.conf.d/proxy.conf with the following:

```shell
Acquire {
  HTTP::proxy "http://PROXY:PORT";
  HTTPS::proxy "http://PROXY:PORT";
}
```

Through Terraform, all other configuration files are written to the bootstrap VM with configuration values obtained through the Azure deployment. Sample configuration values are also provided for packages added to the cluster, should you wish to exercise those and add the packages. The default deployment uses one of tkgm-azure .ps1 or .sh to handle the cluster deployment automation. This script should have taken values from the deployment to do its work, but you may want to review the script(s) for accuracy depending on the changes you've made to the code.
