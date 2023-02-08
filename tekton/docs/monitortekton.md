# Monitor Tekton Pipeline Runs, Task Runs, and Pipelines

Use the following commands to monitor Tekton pipeline runs, task runs, and pipelines for Tanzu Kubernetes Grid.

## List Pipeline Runs and Task Runs

1. Set the kubeconfig for the cluster by exporting the cluster kind file. 

   For example:
    ```  
    export KUBECONFIG=/root/tekton/arcas-tekton-cicd/arcas-ci-cd-cluster.yaml
    ```

2. List the pipeline runs.
   - For Tanzu Kubernetes Grid:
      ```
      tkn pr ls
      NAME                      STARTED          DURATION     STATUS
      tkgm-bringup-day0-jd2mp   53 minutes ago   58 minutes   Succeeded
      tkgm-bringup-day0-jqkbz   3 hours ago      47 minutes   Succeeded      
      ```
    
   - For vSphere with Tanzu:
 
      ```
       tkn pr ls  
       NAME                      STARTED      DURATION   STATUS 
       tkgs-bringup-day0-z5qf4   1 hour ago   1 hour     Succeeded
       ```

3. List the task runs.

   - For Tanzu Kubernetes Grid:

         ```
         tkn tr ls
         NAME                                                  STARTED          DURATION     STATUS        
         tkgm-bringup-day0-jd2mp-start-mgmt-create             46 minutes ago   20 minutes   Succeeded
         tkgm-bringup-day0-jd2mp-start-avi                     54 minutes ago   8 minutes    Succeeded
         tkgm-bringup-day0-jd2mp-start-prep-workspace          54 minutes ago   11 seconds   Succeeded
        ```

   - For vSphere with Tanzu:

       ```
       tkn tr ls
       NAME                                                  STARTED          DURATION     STATUS
       tkgs-bringup-day0-z5qf4-gitcommit                     13 minutes ago   11 seconds   Succeeded
       tkgs-bringup-day0-z5qf4-start-extns-deploy            26 minutes ago   13 minutes   Succeeded
       tkgs-bringup-day0-z5qf4-start-wld-setup               53 minutes ago   27 minutes   Succeeded
       tkgs-bringup-day0-z5qf4-start-wld-ns-setup            54 minutes ago   30 seconds   Succeeded
       tkgs-bringup-day0-z5qf4-start-enable-wcp              1 hour ago       31 minutes   Succeeded
       tkgs-bringup-day0-z5qf4-start-avi-wcp-configuration   1 hour ago       1 minute     Succeeded
       tkgs-bringup-day0-z5qf4-start-avi                     1 hour ago       11 minutes   Succeeded
       tkgs-bringup-day0-z5qf4-start-prep-workspace          1 hour ago       11 seconds   Succeeded
       ```

## Monitor Pipelines

- For monitoring pipelines, use the following commands.
  
  - Tanzu Kubernetes Grid:
  
  ```
    tkn pr logs <tkgm-bringup-day0-jd2mp> --follow
    ```
  
  - vSphere with Tanzu:
  
    ```
    tkn pr logs <tkgs-bringup-day0-z5qf4> --follow
    ```

- For debugging, use the following commands.

  - Tanzu Kubernetes Grid:

    ```
    tkn pr desc <tkgm-bringup-day0-jd2mp>
    ```

  - vSphere with Tanzu:

    ```
    tkn pr desc <tkgs-bringup-day0-z5qf4>
    ```	

[Back to Main](../README.md)