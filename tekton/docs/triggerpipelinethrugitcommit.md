# Trigger Pipelines through GitOps

CI/CD pipelines support triggering of pipelines based on git commit changes.

1. Complete the CI/CD preparation steps mentioned in [Setup CI/CD infra and pipelines](../preparefortektonpipelines.md). 
2. From the Linux/Service Installer for VMware Tanzu VM, browse to the CI/CD directory.

   ```sh
   export KUBECONFIG=path_to_arcas-ci-cd-cluster.yaml
   kubectl apply -f tekton-infra/pipeline-resources/
   ```
See [Pipeline Support Matrix](../README.md)

## Day 0 Bringup
1. From the Git repository, update `desired-state/day0-desired-state.yml` with the desired version (2.1.0). 
2. Commit and push the file with the **message "exec_bringup"**
The Day 0 Bringup pipelines are triggered automatically.

## Day 2 Upgrade
1. From the Git repository, update desired-state/day2-desired-state.yml with the desired version (2.1.0). 
2. Commit and push the file with the **message "exec_upgrade"**
The Day 0 Bringup pipelines are triggered automatically.

## Day 2 Resize
1. From the Git repository, update desired-state/day2-desired-state.yml with the desired version (2.1.0). 
2. Commit and push the file with the **message "exec_resize"**
The Day 0 Bringup pipelines are triggered automatically.

## Day 2 Scale
1. From the Git repository, update desired-state/day2-desired-state.yml with the desired version (2.1.0). 
2. Commit and push the file with the **message "exec_scale"**
The Day 0 Bringup pipelines are triggered automatically.

The pipelines can be monitored from UI at:  http://<IP of Linux/SIVT VM>:8085
The pipelines can be monitored from CLI by executing:

            export KUBECONFIG=path to arcas-ci-cd-cluster.yaml
            tkn pr desc -L    
            
[Back to Main](../README.md)

