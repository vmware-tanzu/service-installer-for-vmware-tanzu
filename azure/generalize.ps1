Remove-Item -Path .\0_keepers\terraform.tfstate*
Remove-Item -Path .\0_keepers\.terraform.lock.hcl
Remove-Item -Recurse -Path .\0_keepers\.terraform -Force
Remove-Item -Path .\1_netsec\.terraform.lock.hcl
Remove-Item -Path .\1_netsec\provider.tf
Remove-Item -Recurse -Path .\1_netsec\.terraform -Force
Remove-Item -Path .\2_dns\.terraform.lock.hcl
Remove-Item -Path .\2_dns\provider.tf
Remove-Item -Recurse -Path .\2_dns\.terraform -Force
Remove-Item -Path .\3_bootstrap\.terraform.lock.hcl
Remove-Item -Path .\3_bootstrap\data.tf
Remove-Item -Path .\3_bootstrap\provider.tf
Remove-Item -Recurse -Path .\3_bootstrap\.terraform -Force
Remove-Item -Recurse -Path .\3_bootstrap\bootstrap.pem