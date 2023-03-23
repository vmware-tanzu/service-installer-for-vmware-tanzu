# Execute Day 0 Tanzu Kubernetes Grid Deployment Pipelines from command line.

See [Day 0 Support Matrix](../README.md) for Day 0 support.

### PREPARATORY STEPS
Browse to the prepared Git repository (gitlab/github) and ensure the following:
   1. File `desired-state/day0-desired-state.yml` is updated with the required version as supported in Pipeline Support Matrix.
      1. Example:
            ```bash
                  tkgm: 2.1.0 # for 2.1.0 tkgm Deployment
                  tkgs: 2.1 # for tkgs Deployment

                  env: vsphere # for tkgm DVS based deployment and for tkgs.
                  env: vcf # for tkgm NSX-T based deployment.
            ```

   2. For deployment on Tanzu Kubernetes Grid, `config/deployment.json` is to updated with the right values. 
   3. For deployment on vSphere with Tanzu, `config/deployment-config-ns.json` and `config/deployment-config-wcp.json` are to be updated with the right values. 

**Note:** These files can also be generated using Service Installer for VMware Tanzu and the deployment files can also be used here in pipelines.

### EXECUTION STEPS
1. From the Linux machine or Service Installer for VMware Tanzu VM, browse to the CI/CD directory. 
2. For deployment on Tanzu Kubernetes Grid, execute: 
      ```bash
         ./prepare-sivt-tekton.sh --exec-day0
      ```
3. For deployment on vSphere with Tanzu, execute: 
      ```bash
         ./prepare-sivt-tekton.sh --exec-tkgs-day0
      ```

The pipelines can be monitored from UI at: `http://<IP of Linux/SIVT VM>:8085`        
                  
The pipelines can be monitored from CLI by:
```bash
            export KUBECONFIG=path to arcas-ci-cd-cluster.yaml
            tkn pr desc -L    
```
      
   
[Back to Main](../README.md)
   
