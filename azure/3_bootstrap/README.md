<!-- BEGIN_TF_DOCS -->
## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | n/a |
| <a name="provider_cloudinit"></a> [cloudinit](#provider\_cloudinit) | n/a |
| <a name="provider_local"></a> [local](#provider\_local) | n/a |
| <a name="provider_null"></a> [null](#provider\_null) | n/a |
| <a name="provider_tls"></a> [tls](#provider\_tls) | n/a |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_app_reg"></a> [app\_reg](#module\_app\_reg) | ../modules/app_reg | n/a |
| <a name="module_myip"></a> [myip](#module\_myip) | 4ops/myip/http | 1.0.0 |

## Resources

| Name | Type |
|------|------|
| [azurerm_key_vault_secret.AZURE_RESOURCE_GROUP](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_SSH_PUBLIC_KEY_B64](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.bootstrap_tls_private_key](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_linux_virtual_machine.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/linux_virtual_machine) | resource |
| [azurerm_network_interface.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_interface) | resource |
| [azurerm_network_interface_security_group_association.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_interface_security_group_association) | resource |
| [azurerm_network_security_group.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_security_group) | resource |
| [azurerm_public_ip.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/public_ip) | resource |
| [azurerm_resource_group.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group) | resource |
| [local_file.bootstrap_priv_key](https://registry.terraform.io/providers/hashicorp/local/latest/docs/resources/file) | resource |
| [null_resource.az_eula_2004](https://registry.terraform.io/providers/hashicorp/null/latest/docs/resources/resource) | resource |
| [tls_private_key.this](https://registry.terraform.io/providers/hashicorp/tls/latest/docs/resources/private_key) | resource |
| [azurerm_key_vault.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/key_vault) | data source |
| [azurerm_key_vault_secret.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/key_vault_secret) | data source |
| [azurerm_key_vault_secrets.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/key_vault_secrets) | data source |
| [cloudinit_config.this](https://registry.terraform.io/providers/hashicorp/cloudinit/latest/docs/data-sources/config) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_additional_tags"></a> [additional\_tags](#input\_additional\_tags) | A mapping of tags to assign to the resource. | `map(string)` | <pre>{<br>  "BusinessUnit": "MAPBU",<br>  "Environment": "Testing",<br>  "OwnerEmail": "tanzu@vmware.com",<br>  "ServiceName": "TKGm Reference Architecture"<br>}</pre> | no |
| <a name="input_boot_diag_sa_name"></a> [boot\_diag\_sa\_name](#input\_boot\_diag\_sa\_name) | The storage account name to be created for holding boot diag data for firewalls as well as NSG Flow logs. | `string` | `""` | no |
| <a name="input_dns_servers"></a> [dns\_servers](#input\_dns\_servers) | n/a | `list(string)` | `[]` | no |
| <a name="input_http_proxy"></a> [http\_proxy](#input\_http\_proxy) | Proxy settings for bootstrap and TKG cluster members, e.g. http://user:password@myproxy.com:1234 | `string` | `""` | no |
| <a name="input_https_proxy"></a> [https\_proxy](#input\_https\_proxy) | Proxy settings for bootstrap and TKG cluster members, e.g. http://user:password@myproxy.com:1234 | `string` | `""` | no |
| <a name="input_ipAcl"></a> [ipAcl](#input\_ipAcl) | The IP ACL to be used for the Storage Account and KeyVault.  If left blank, the local executor's IP address will be used. | `string` | `""` | no |
| <a name="input_location"></a> [location](#input\_location) | Azure regional location (keyword from Azure validated list) | `string` | `"eastus2"` | no |
| <a name="input_netsec_resource_group"></a> [netsec\_resource\_group](#input\_netsec\_resource\_group) | Resource Group name provided by 1\_netsec where the VNET and related resources exist. | `string` | `""` | no |
| <a name="input_no_proxy"></a> [no\_proxy](#input\_no\_proxy) | comma-separated list of hosts, CIDR, or domains to bypass proxy | `string` | `""` | no |
| <a name="input_prefix"></a> [prefix](#input\_prefix) | The prefix used for all infrastructure objects.  i.e. '<prefix>-vnet' or '<prefix>-web-nsg' | `string` | `"vmw-use2-tkgm"` | no |
| <a name="input_prefix_short"></a> [prefix\_short](#input\_prefix\_short) | This prefix is an abbreviated version of 'prefix' but designed for lower max character names. The short prefix should be a maximum of 8 chars (alpha-numeric) | `string` | `"vmwuse2tkgm"` | no |
| <a name="input_sub_id"></a> [sub\_id](#input\_sub\_id) | Azure subscription ID - resources created here. | `string` | n/a | yes |
| <a name="input_subnet_name"></a> [subnet\_name](#input\_subnet\_name) | Subnet name picked from the 1\_netsec/user-subnets.tf file. The bootstrap machine should live outside of the workload or controlplane subnets. | `string` | `"Admin"` | no |
| <a name="input_user"></a> [user](#input\_user) | Bootstrap VM (Ubuntu Linux) default username | `string` | `"azureuser"` | no |
| <a name="input_vault_name"></a> [vault\_name](#input\_vault\_name) | Azure Key Vault as built by 0\_keepers - fed by a state data source if left empty | `string` | `""` | no |
| <a name="input_vault_resource_group_name"></a> [vault\_resource\_group\_name](#input\_vault\_resource\_group\_name) | The resource group name for the vault provided by 0\_keepers - fed by a state data source if left empty | `string` | `""` | no |
| <a name="input_vnet_name"></a> [vnet\_name](#input\_vnet\_name) | The VNET provided by 1\_netsec. | `string` | `""` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_AZURE_RESOURCE_GROUP"></a> [AZURE\_RESOURCE\_GROUP](#output\_AZURE\_RESOURCE\_GROUP) | n/a |
| <a name="output_AZURE_SSH_PUBLIC_KEY_B64"></a> [AZURE\_SSH\_PUBLIC\_KEY\_B64](#output\_AZURE\_SSH\_PUBLIC\_KEY\_B64) | n/a |
| <a name="output_bootstrap_usr"></a> [bootstrap\_usr](#output\_bootstrap\_usr) | n/a |
| <a name="output_bootstrap_vm"></a> [bootstrap\_vm](#output\_bootstrap\_vm) | Outputs provided for convenience. Source of record should be considered the Azure Key Vault secret store provisioned by 0\_keepers! |
| <a name="output_ssh_pip_cmd"></a> [ssh\_pip\_cmd](#output\_ssh\_pip\_cmd) | Bootstrap Public IP can be presented in output if public IPs are used |
| <a name="output_ssh_priv_cmd"></a> [ssh\_priv\_cmd](#output\_ssh\_priv\_cmd) | Bootstrap Private IP can be presented in output if private IPs are used |
| <a name="output_tls_private_key"></a> [tls\_private\_key](#output\_tls\_private\_key) | n/a |
<!-- END_TF_DOCS -->