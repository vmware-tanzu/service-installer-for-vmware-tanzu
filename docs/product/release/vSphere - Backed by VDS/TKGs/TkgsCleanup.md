# Selective Cleanup Options for VMware Tanzu Kubernetes Grid Service

Cleanup options provide selective cleanup functionality where individual components can be deleted separately for VMware Tanzu Kubernetes Grid Service (informally known as TKGs).

The following table describes the cleanup_option parameter values:

   cleanup_option                         | Description                                |
------------------------------------------| -------------------------------------------|
   all                                    | End-to-End cleanup                         |
   avi_configuration                      | AVI Controller cleanup                     |
   disable_wcp                            | Disable wcp                                |
   tkgs_supervisor_namespace              | Supervisor namespace cleanup               |
   tkgs_workload_cluster                  | Workload cluster cleanup                   |
   extensions                             | Extensions cleanup                         |


## Cleanup commands

For selective cleanup, run the following commands:
>**Note** components need to be cleaned up in reverse order of how they are deployed.

For more information about `vsphere-dvs-tkgs-wcp.json` and `vsphere-dvs-tkgs-namespace.json` sample files, see [TKGs](./TKOonVsphereVDStkgs.md).

**End-to-end TKGs deployment cleanup**
```
arcas --env vsphere --file /path/to/vsphere-dvs-tkgs-wcp.json --cleanup all
```

**AVI Controller cleanup**
```
arcas --env vsphere --file /path/to/vsphere-dvs-tkgs-wcp.json --cleanup avi_configuration
```

**Disable wcp**
```
arcas --env vsphere --file /path/to/vsphere-dvs-tkgs-wcp.json --cleanup disable_wcp
```

**Supervisor namespace cleanup**
```
arcas --env vsphere --file /path/to/vsphere-dvs-tkgs-namespace.json --cleanup tkgs_supervisor_namespace
```

**Workload cluster cleanup**
```
arcas --env vsphere --file /path/to/vsphere-dvs-tkgs-namespace.json --cleanup tkgs_workload_cluster
```

**Extensions cleanup**
```
arcas --env vsphere --file /path/to/vsphere-dvs-tkgs-namespace.json --cleanup extensions
```
