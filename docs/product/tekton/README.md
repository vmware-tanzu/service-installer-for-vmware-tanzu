# TEKTON PIPELINE 

Tekton is a cloud-native solution for building CI/CD systems. It consists of Tekton Pipelines, which provides the DayO deployment and Day2 operations of TKGM 1.4.x on vSphere backed environment. 

## Features

- Bring based on Reference Architecture of TKGM on vSphere.
- E2E deployement and configuration of AVI Controller, Management, SharedServices, Workload clusters 
- Support for Day2 of upgrade from 1.4.0 to 1.4.1


## Pre-requisites

Tekton pipelines execution require the following: 

- Service Installer OVA
- Kind:Node image present locally on service installer
- Docker:dind image present locally on service installer
- Service Installer Image (Used only for Tekton pipeline. It is available in Marketplace, download and make it available in the SIVT as a docker image)
- Private git repo

## Execution

1. Update config/deployment.json based on the environment. 
2. In Service Installer VM navigate to the tekton folder '/opt/vmware/arcas/tekton' which has tekton pipeline code.

    ### 2.1 Update entries in values.yaml
    ```cat values.yaml
        #@data/values-schema
        ---
        git:
        host: <FQDN/IP OF GIT>
        repository: <GITUSER/GITREPO> #foo/master
        branch: <BRANCH>
        username: <USER WITH GIT ACCESS FOR THE REPO> #foo
        password: <GIT PAT>
        imagename: <IMAGE PATH OF SERVICE INSTALLER IMAGE> #service_installer_tekton:v141 #registry:/library/service_installer_tekton:v141
    ```
    ### 2.2 For triggering Day0 bringup
    ``` 
        #For launching Day0 bringup of TKGM
        ./launch.sh --create-cluster --deploy-dashboard --exec-day0
    ```
    ### 2.3 For triggering Day2 operation targetting management cluster
    ``` 
        #For launching Day2 upgrade opearations for Management cluster
        ./launch.sh --create-cluster --deploy-dashboard --exec-upgrade-mgmt
    ```
    ### 2.4 For triggering Day2 operation targetting all clusters
    ``` 
        #For launching Day2 upgrade opearations for Management cluster
        ./launch.sh --create-cluster --deploy-dashboard     --exec-upgrade-all To trigger upgrade of all clusters

    ```
3. Re-triggering any Pipelines
    ### From kubectl
    ``` 
        kubectl create -f run/day0-bringup.yml        
        #or 
        ./launch.sh --exec-day0
    ```
5. Listing Pipelines and taskruns
    ### From tkn
    ``` 
        #for PipelineRuns
        tkn pr ls
        NAME                      STARTED          DURATION     STATUS
        tkgm-bringup-day0-jd2mp   53 minutes ago   58 minutes   Succeeded
        tkgm-bringup-day0-jqkbz   3 hours ago      47 minutes   Succeeded      

        #for TaskRuns
        tkn tr ls
        NAME                                                  STARTED          DURATION     STATUS        
        tkgm-bringup-day0-jd2mp-start-mgmt-create             46 minutes ago   20 minutes   Succeeded
        tkgm-bringup-day0-jd2mp-start-avi                     54 minutes ago   8 minutes    Succeeded
        tkgm-bringup-day0-jd2mp-start-prep-workspace          54 minutes ago   11 seconds   Succeeded

    ```
4. Monitoring Pipelines
    ### From tkn
    ``` 
        tkn pr logs <tkgm-bringup-day0-jd2mp> --follow
        #For debugging. 
        tkn pr desc <tkgm-bringup-day0-jd2mp>
    ```
