<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.1 |
| <a name="requirement_azuread"></a> [azuread](#requirement\_azuread) | = 2.18.0 |
| <a name="requirement_azurerm"></a> [azurerm](#requirement\_azurerm) | < 3.0 |
| <a name="requirement_local"></a> [local](#requirement\_local) | = 2.1.0 |
| <a name="requirement_null"></a> [null](#requirement\_null) | = 3.1.0 |
| <a name="requirement_random"></a> [random](#requirement\_random) | ~> 3.1.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_azuread"></a> [azuread](#provider\_azuread) | = 2.18.0 |
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | < 3.0 |
| <a name="provider_local"></a> [local](#provider\_local) | = 2.1.0 |
| <a name="provider_null"></a> [null](#provider\_null) | = 3.1.0 |
| <a name="provider_random"></a> [random](#provider\_random) | ~> 3.1.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_akv"></a> [akv](#module\_akv) | ../modules/akv | n/a |
| <a name="module_myip"></a> [myip](#module\_myip) | 4ops/myip/http | 1.0.0 |

## Resources

| Name | Type |
|------|------|
| [azurerm_key_vault_secret.AZURE_LOCATION](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_SUBSCRIPTION_ID](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_key_vault_secret.AZURE_TENANT_ID](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/key_vault_secret) | resource |
| [azurerm_resource_group.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/resource_group) | resource |
| [azurerm_storage_account.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/storage_account) | resource |
| [local_file.bootstrap_data](https://registry.terraform.io/providers/hashicorp/local/2.1.0/docs/resources/file) | resource |
| [local_file.bootstrap_prov](https://registry.terraform.io/providers/hashicorp/local/2.1.0/docs/resources/file) | resource |
| [local_file.dns_prov](https://registry.terraform.io/providers/hashicorp/local/2.1.0/docs/resources/file) | resource |
| [local_file.netsec_prov](https://registry.terraform.io/providers/hashicorp/local/2.1.0/docs/resources/file) | resource |
| [null_resource.ctr_state](https://registry.terraform.io/providers/hashicorp/null/3.1.0/docs/resources/resource) | resource |
| [random_id.this](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id) | resource |
| [azuread_group.this](https://registry.terraform.io/providers/hashicorp/azuread/2.18.0/docs/data-sources/group) | data source |
| [azurerm_client_config.current](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/client_config) | data source |
| [azurerm_subscription.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/data-sources/subscription) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_acl_group"></a> [acl\_group](#input\_acl\_group) | The Azure Active Directory group to be used for access policies.  If left blank, the local executor's account will be used instead of a group. | `string` | `""` | no |
| <a name="input_additional_tags"></a> [additional\_tags](#input\_additional\_tags) | n/a | `map` | <pre>{<br>  "BusinessUnit": "MAPBU",<br>  "Environment": "Testing",<br>  "OwnerEmail": "tanzu@vmware.com",<br>  "ServiceName": "TKGm Reference Architecture"<br>}</pre> | no |
| <a name="input_ipAcl"></a> [ipAcl](#input\_ipAcl) | The IP/CIDR ACL to be used for the Storage Account and KeyVault.  If left blank, the local executor's IP address will be used. | `string` | `""` | no |
| <a name="input_location"></a> [location](#input\_location) | The region/location where these resources will be deployed. | `string` | `"eastus2"` | no |
| <a name="input_prefix"></a> [prefix](#input\_prefix) | The prefix used for all infrastructure objects.  i.e. '<prefix>-vnet' or '<prefix>-web-nsg' | `string` | `"vmw-use2-keeper"` | no |
| <a name="input_prefix_short"></a> [prefix\_short](#input\_prefix\_short) | This prefix is an abbreviated version of 'prefix' but designed for lower max character names. The short prefix should be a maximum of 8 chars (alpha-numeric) | `string` | `"vmwuse2keep"` | no |
| <a name="input_sub_id"></a> [sub\_id](#input\_sub\_id) | The subscription ID where these resources should be built. | `any` | n/a | yes |
| <a name="input_tenant_id"></a> [tenant\_id](#input\_tenant\_id) | The tenant ID (Azure Active Directory) linked to your subscription. | `any` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_access_key"></a> [access\_key](#output\_access\_key) | n/a |
| <a name="output_keeper_resource_group_name"></a> [keeper\_resource\_group\_name](#output\_keeper\_resource\_group\_name) | n/a |
| <a name="output_key_vault"></a> [key\_vault](#output\_key\_vault) | n/a |
| <a name="output_random_seed"></a> [random\_seed](#output\_random\_seed) | n/a |
| <a name="output_run_me"></a> [run\_me](#output\_run\_me) | n/a |
| <a name="output_storage_account"></a> [storage\_account](#output\_storage\_account) | n/a |
<!-- END_TF_DOCS -->