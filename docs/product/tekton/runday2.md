# Run Day 2 Operations Pipelines for Tanzu Kubernetes Grid

See [Day 2 Support Matrix](../README.md) for Day 2 support.

The pipelines support the following Day 2 operations:
- Perform Tanzu Kubernetes Grid cluster upgrade
- Perform resize of Workload clusters
- Perform Scale Up/Down of clusters

**Note:** It is recommended to perform one Day 2 operation at one instance. Multiple Day 2 operations cannot be executed in one run.

### PREPARATORY STEPS
Browse to the prepared Git repository (gitlab/github) and ensure the following:
   1. File `desired-state/day2-desired-state.yml` is updated with the required version. 
   2. Change `execute: true` for the desired Day 2 operation. 
   3. Change `target_cluster` to select the cluster for Day 2 operation. 
        - Grouping of clusters is also supported in target_cluster. 
        - `all` - To perform the Day 2 operation on all the clusters. 
        - `dev-lab*` - To perform the Day 2 operation on the clusters matching dev-lab name. 
        - `clustername` - To perform on one specific cluster.

### EXECUTION STEPS
1. From the Linux machine or Service Installer for VMware Tanzu VM, browse to the CI/CD directory. 
2. Execute: 
      ```bash
         ./prepare-sivt-tekton.sh --exec-day2-upgrade # for Upgrade operation
         ./prepare-sivt-tekton.sh --exec-day2-resize # for Resize operation
         ./prepare-sivt-tekton.sh --exec-day2-scale # for Scaling operation
      ```
The pipelines can be monitored from UI at:  `http://<IP of Linux/SIVT VM>:8085`        
                  
The pipelines can be monitored from CLI by executing:
```bash
            export KUBECONFIG=path to arcas-ci-cd-cluster.yaml
            tkn pr desc -L    
```
   
[Back to Main](../README.md)
