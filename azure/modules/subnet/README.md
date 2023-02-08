<!-- BEGIN_TF_DOCS -->
## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | 3.0.2 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [azurerm_network_security_group.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_security_group) | resource |
| [azurerm_network_security_rule.Worker_allow_HealthProbe_in](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_security_rule) | resource |
| [azurerm_network_security_rule.Worker_allow_Select_in](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_security_rule) | resource |
| [azurerm_network_watcher_flow_log.tier](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_watcher_flow_log) | resource |
| [azurerm_subnet.tier_net](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet) | resource |
| [azurerm_subnet_network_security_group_association.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet_network_security_group_association) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_flow_log_data"></a> [flow\_log\_data](#input\_flow\_log\_data) | This map contains all of the log analytics data needed to set up NSG flow logs.  It contains the following:<br>    "law\_id" -- Log Analytics ID<br>    "law\_workspace\_id" -- Log Analytics Workspace ID<br>    "nw\_name" -- Network Watcher Name for this spoke/region<br>    "nw\_rg\_name" -- Resource Group Name for the Network Watcher in this spoke/region<br>    "flow\_log\_sa\_id" -- Boot Diagnostics Storage Account ID (used for both boot diag and nsg flow logs) | `map(string)` | n/a | yes |
| <a name="input_local_data"></a> [local\_data](#input\_local\_data) | A map containing all of the information required to build a unique spoke. | `any` | n/a | yes |
| <a name="input_subnet_settings"></a> [subnet\_settings](#input\_subnet\_settings) | STAGE | <pre>map(<br>    object({<br>      resource_group_name                            = string,<br>      virtual_network_name                           = string,<br>      address_prefixes                               = list(string),<br>      service_endpoints                              = list(string),<br>      enforce_private_link_endpoint_network_policies = bool,<br>      enforce_private_link_service_network_policies  = bool,<br>      service_endpoint_policy_ids                    = list(string),<br>      delegation_name                                = string,<br>      service_delegation_name                        = string,<br>      service_delegation_actions                     = list(string),<br>      nsg_name                                       = string,<br>    })<br>  )</pre> | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_subnets"></a> [subnets](#output\_subnets) | A map of subnets created from this module |
<!-- END_TF_DOCS -->