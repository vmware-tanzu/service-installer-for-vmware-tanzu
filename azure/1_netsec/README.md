<!-- BEGIN_TF_DOCS -->
## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | n/a |
| <a name="provider_terraform"></a> [terraform](#provider\_terraform) | n/a |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_myip"></a> [myip](#module\_myip) | 4ops/myip/http | 1.0.0 |
| <a name="module_nat_gw"></a> [nat\_gw](#module\_nat\_gw) | ../modules/nat_gw | n/a |
| <a name="module_subnet_w_nsg"></a> [subnet\_w\_nsg](#module\_subnet\_w\_nsg) | ../modules/subnet | n/a |
| <a name="module_vnet_base"></a> [vnet\_base](#module\_vnet\_base) | ../modules/vnet | n/a |

## Resources

| Name | Type |
|------|------|
| [azurerm_key_vault_secret.AZURE_CONTROL_PLANE_SUBNET_CIDR_mgmt](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_CONTROL_PLANE_SUBNET_CIDR_wrk](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_CONTROL_PLANE_SUBNET_NAME_mgmt](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_CONTROL_PLANE_SUBNET_NAME_wrk](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_FRONTEND_PRIVATE_IP](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_NODE_SUBNET_CIDR_mgmt](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_NODE_SUBNET_CIDR_wrk](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_NODE_SUBNET_NAME_mgmt](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_NODE_SUBNET_NAME_wrk](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_VNET_CIDR](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_VNET_NAME](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_VNET_RESOURCE_GROUP](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.CLUSTER_NAME_mgmt](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.CLUSTER_NAME_wrk](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_resource_group.rg](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group) | resource |
| [azurerm_key_vault.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/key_vault) | data source |
| [azurerm_storage_account.keeper](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/storage_account) | data source |
| [azurerm_subscription.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/subscription) | data source |
| [terraform_remote_state.keeper](https://registry.terraform.io/providers/hashicorp/terraform/latest/docs/data-sources/remote_state) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_CreateNetworkWatcher"></a> [CreateNetworkWatcher](#input\_CreateNetworkWatcher) | Affects the creation of a Network Watcher for the VNet.  0 = No, 1 = Yes | `number` | `0` | no |
| <a name="input_CreateNetworkWatcherRG"></a> [CreateNetworkWatcherRG](#input\_CreateNetworkWatcherRG) | Affects the creation of a Network Watcher Resource Group for the VNet.  0 = No, 1 = Yes | `number` | `0` | no |
| <a name="input_additional_tags"></a> [additional\_tags](#input\_additional\_tags) | n/a | `map` | <pre>{<br>  "BusinessUnit": "MAPBU",<br>  "Environment": "Testing",<br>  "OwnerEmail": "tanzu@vmware.com",<br>  "ServiceName": "TKGm Reference Architecture"<br>}</pre> | no |
| <a name="input_boot_diag_sa_name"></a> [boot\_diag\_sa\_name](#input\_boot\_diag\_sa\_name) | The storage account name to be created for holding boot diag data for firewalls as well as NSG Flow logs. | `string` | `""` | no |
| <a name="input_core_address_space"></a> [core\_address\_space](#input\_core\_address\_space) | Transit subnet range.  Range for small subnets used transit networks (generally to FWs) | `string` | `"10.1.2.0/24"` | no |
| <a name="input_create_nat_gateway"></a> [create\_nat\_gateway](#input\_create\_nat\_gateway) | This boolean controls whether a NAT Gateway is configured and attached to all the subnets of this VNET. It is necessary if this is a private cluster TKG install, as well as if there is no proxy or routing established to redirect Internet traffic. | `bool` | `true` | no |
| <a name="input_dns_list"></a> [dns\_list](#input\_dns\_list) | A list of IP addresses which, if needed, should probably match an on-prem or cloud-based target of DNS servers or load balancer(s) to allow for on-prem resolution. | `list(string)` | `[]` | no |
| <a name="input_ipAcl"></a> [ipAcl](#input\_ipAcl) | The IP/CIDR to be used for the Storage Account and KeyVault.  If left blank, the local executor's IP address will be used. | `string` | `""` | no |
| <a name="input_location"></a> [location](#input\_location) | The region/location where these resources will be deployed. | `string` | `"eastus2"` | no |
| <a name="input_prefix"></a> [prefix](#input\_prefix) | The prefix used for all infrastructure objects.  i.e. '<prefix>-vnet' or '<prefix>-web-nsg' | `string` | `"vmw-use2-netsec"` | no |
| <a name="input_prefix_short"></a> [prefix\_short](#input\_prefix\_short) | This prefix is an abbreviated version of 'prefix' but designed for lower max character names. The short prefix should be a maximum of 8 chars (alpha-numeric) | `string` | `"vmwuse2netsec"` | no |
| <a name="input_sub_id"></a> [sub\_id](#input\_sub\_id) | The subscription ID where these resources should be built. | `any` | n/a | yes |
| <a name="input_tkg_cluster_name"></a> [tkg\_cluster\_name](#input\_tkg\_cluster\_name) | n/a | `string` | `"vmw-use2-tkgm"` | no |
| <a name="input_vault_name"></a> [vault\_name](#input\_vault\_name) | n/a | `string` | `""` | no |
| <a name="input_vault_resource_group_name"></a> [vault\_resource\_group\_name](#input\_vault\_resource\_group\_name) | n/a | `string` | `""` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_boot_diag_sa_name"></a> [boot\_diag\_sa\_name](#output\_boot\_diag\_sa\_name) | n/a |
<!-- END_TF_DOCS -->