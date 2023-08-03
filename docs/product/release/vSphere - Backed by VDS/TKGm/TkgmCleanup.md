# Selective Cleanup Options for VMware Tanzu Kubernetes Grid Management

The Cleanup options provide selective cleanup functionality where individual components can be deleted separately for VMware Tanzu Kubernetes Grid Management (informally known as TKGm).

The following table describes the cleanup_option parameter values:

 >**Note** The `vmc_pre_configuration` cleanup_option only applies to VMC environment, and the `vcf_pre_configuration` only applies to NSX-T environment. The remaining options are common across vSphere, VMC, and NSX-t.


   cleanup_option                         | Description                                |
------------------------------------------| -------------------------------------------|
   all                                    | End-to-End cleanup                         |
   vmc_pre_configuration                  | VMC configuration cleanup                  |
   vcf_pre_configuration                  | NSX-T configuration cleanup                |
   avi_configuration                      | AVI Controller cleanup                     |
   tkgm_mgmt_cluster                      | Management cluster cleanup                 |
   tkgm_shared_cluster                    | Shared cluster cleanup                     |
   tkgm_workload_cluster                  | Workload cluster cleanup                   |
   extensions                             | Extensions cleanup                         |


## Cleanup commands

For selective cleanup, run the following commands. Update the `env` and `json_file_path` as per the env.

 >**Note** components need to be cleaned up in reverse order of how they are deployed.

***<env_type>***: Please mention 'vmc' or 'vsphere' or 'vcf'.

***<json_file_path>***: Please Refer sample json files from below env specific pages
- [For Vsphere-VDS](./TKOonVsphereVDStkg.md)
- [For Vsphere-NSX-T](../../vSphere%20-%20Backed%20by%20NSX-T/tkoVsphereNSXT.md)
- [For VMC](../../VMware%20Cloud%20on%20AWS%20-%20VMC/TKOonVMConAWS.md)

**End-to-end TKGm deployment cleanup**
```
arcas --env <env_type> --file <json_file_path> --cleanup all
```

**AVI Controller cleanup**
```
arcas --env <env_type> --file <json_file_path> --cleanup avi_configuration
```

**Management cluster cleanup**
```
arcas --env <env_type> --file <json_file_path> --cleanup tkgm_mgmt_cluster
```

**Shared cluster cleanup**
```
arcas --env <env_type> --file <json_file_path> --cleanup tkgm_shared_cluster
```

**Workload cluster cleanup**
```
arcas --env <env_type> --file <json_file_path> --cleanup tkgm_workload_cluster
```

**Extensions cleanup**
```
arcas --env <env_type> --file <json_file_path> --cleanup extensions
```

### NSX-T specific cleanup commands

**NSX-T configuration cleanup**
```
arcas --env vcf --file <json_file_path> --cleanup vcf_pre_configuration
```

### VMC specific cleanup commands

**VMC configuration cleanup**
```
arcas --env vmc --file <json_file_path> --cleanup vmc_pre_configuration
```
