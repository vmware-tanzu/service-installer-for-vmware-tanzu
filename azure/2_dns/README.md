<!-- BEGIN_TF_DOCS -->
## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | n/a |
| <a name="provider_cloudinit"></a> [cloudinit](#provider\_cloudinit) | n/a |
| <a name="provider_random"></a> [random](#provider\_random) | n/a |
| <a name="provider_terraform"></a> [terraform](#provider\_terraform) | n/a |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_bindvm"></a> [bindvm](#module\_bindvm) | ../modules/vm | n/a |

## Resources

| Name | Type |
|------|------|
| [azurerm_network_interface_security_group_association.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_interface_security_group_association) | resource |
| [azurerm_network_security_group.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_security_group) | resource |
| [random_id.this](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id) | resource |
| [azurerm_resource_group.netsec](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/resource_group) | data source |
| [azurerm_storage_account.bootdiag](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/storage_account) | data source |
| [azurerm_subnet.netsec](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/subnet) | data source |
| [azurerm_virtual_network.netsec](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/virtual_network) | data source |
| [cloudinit_config.this](https://registry.terraform.io/providers/hashicorp/cloudinit/latest/docs/data-sources/config) | data source |
| [terraform_remote_state.keeper](https://registry.terraform.io/providers/hashicorp/terraform/latest/docs/data-sources/remote_state) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_additional_tags"></a> [additional\_tags](#input\_additional\_tags) | A mapping of tags to assign to the resource. | `map(string)` | <pre>{<br>  "BusinessUnit": "MAPBU",<br>  "Environment": "Testing",<br>  "OwnerEmail": "tanzu@vmware.com",<br>  "ServiceName": "TKGm Reference Architecture"<br>}</pre> | no |
| <a name="input_bindvms"></a> [bindvms](#input\_bindvms) | A number of VMs to create which host Bind for DNS forwarding to Azure. | `number` | `2` | no |
| <a name="input_boot_diag_sa_name"></a> [boot\_diag\_sa\_name](#input\_boot\_diag\_sa\_name) | The storage account name to be created for holding boot diag data for firewalls as well as NSG Flow logs. | `string` | `""` | no |
| <a name="input_location"></a> [location](#input\_location) | Azure regional location (keyword from Azure validated list) | `string` | `"eastus2"` | no |
| <a name="input_netsec_resource_group"></a> [netsec\_resource\_group](#input\_netsec\_resource\_group) | Value defined from 1\_netsec | `string` | `"rg-vmw-use2-netsec"` | no |
| <a name="input_prefix"></a> [prefix](#input\_prefix) | The prefix used for all infrastructure objects.  i.e. '<prefix>-vnet' or '<prefix>-web-nsg' | `string` | `"vmw-use2-dnsfwd"` | no |
| <a name="input_sub_id"></a> [sub\_id](#input\_sub\_id) | Azure subscription ID - resources created here. | `string` | n/a | yes |
| <a name="input_subnet_name"></a> [subnet\_name](#input\_subnet\_name) | Value defined from 1\_netsec (user-subnets) | `string` | `"TKGM-Admin"` | no |
| <a name="input_vnet_name"></a> [vnet\_name](#input\_vnet\_name) | Value defined from 1\_netsec | `string` | `"vnet-vmw-use2-netsec"` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_bindvms"></a> [bindvms](#output\_bindvms) | n/a |
<!-- END_TF_DOCS -->