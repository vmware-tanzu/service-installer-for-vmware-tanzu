# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
[CmdletBinding()]
param (
    [Parameter(HelpMessage="Azure Subscription ID", Mandatory)]
    [String]
    $SubscriptionId=$env:TF_VAR_sub_id,

    [Parameter(HelpMessage="Azure Active Directory Tenant ID or 'Parent Management Group' ID", Mandatory)]
    [String]
    $TenantId=$env:TF_VAR_tenant_id
)

$env:TF_IN_AUTOMATION = 'true'
$env:TF_VAR_sub_id = $SubscriptionId
$env:TF_VAR_tenant_id = $TenantId

# Establish 'keepers' which used throughout and can cross into unrelated deployments
Set-Location 0_keepers
terraform init -input=false
terraform apply -input=false -auto-approve
$env:ARM_ACCESS_KEY = (terraform output -raw access_key)
Set-Location ..

# Create network and security resources
Set-Location 1_netsec
terraform init -input=false
terraform apply -input=false -auto-approve
Set-Location ..

# Create the bootstrap machine for TKGm
Set-Location 3_bootstrap
terraform init -input=false
terraform apply -input=false -auto-approve

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$fileSystemRights = "FullControl"
$type = "Allow"
$fileSystemAccessRuleArgumentList = $identity, $fileSystemRights, $type
$fileSystemAccessRule = New-Object -TypeName System.Security.AccessControl.FileSystemAccessRule -ArgumentList $fileSystemAccessRuleArgumentList

$isProtected = $true
$preserveInheritance = $false
$NewAcl = Get-Acl -Path "./bootstrap.pem"
$NewAcl.SetAccessRuleProtection($isProtected, $preserveInheritance)
$NewAcl.SetAccessRule($fileSystemAccessRule)
Set-Acl -Path "./bootstrap.pem" -AclObject $NewAcl
Set-Location ..