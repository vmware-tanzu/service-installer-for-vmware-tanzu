**TEKTON PIPELINE FOR TKGM**

Tekton is a cloud-native solution for building CI/CD systems. SIVT is bundled with Tekton capability which provides the pipelines for DayO deployment and Day2 operations of TKGM 1.5.4 on vSphere backed environment.

**Features**

-  Bringup of Reference Architecture based TKGM environment on vSphere.
-  E2E TKGM deployment and configuration of AVI Controller, Management, SharedServices, Workload clusters, Plugins, Extensions
-  Rescale and Resize Day2 operations. 
-  Upcoming support of TKGS E2E deployment*
-  Upcoming support of TKGM DAY2 Upgrade support from 1.5.x to 1.5.4 with packages and extensions*

**Pre-requisites**

Tekton pipelines execution require the following:

- Service Installer OVA. Download from Marketplace https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true
- Docker login
- Service Installer Tekton Docker tar file. service_installer_tekton_v154.tar  
- Private git repo

**Execution**
 - 1. GIT Preparation
 ```
 1. Prepare a private git (gitlab/github) repo
 2. Clone the code from https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/tree/1.3-1.5.4/tekton
 3. Create a GIT PAT and copy the token for later stages
 4. Prepare deployment.json based on your environment. Refer SIVT Readme for preparing the config file. 
 5. Commit the file under config/deployment.json in the git repo.
 ```
 - 2. SIVT OVA Preparation 
 ```
 1. Deploy the download SIVT OVA and power on the VM
 2. Login to the SIVT OVA
 3. Clone your private repository by 
 #git clone <private repo url>
 ```
  - 3. Preparing the TEKTON pipeline environment  
  ```
  1. Login to SIVT OVA
  2. Browse to the location where the git repo is cloned. 
  3. Open launch.sh and update TARBALL_FILE_PATH to the absolute path where the Service Installer Docker tar is downloaded.
  For example: 
  - TARBALL_FILE_PATH="/root/tekton/arcas-tekton-cicd/service_installer_tekton_v153.tar" 
  or
  - TARBALL_URL="http://mynfsserver/images/service_installer_tekton_v153.tar"
  4. Save file and exit. 
  5. Open cluster_resources/kind-init-config.yaml.
  Provide a free port for the  nginx service to use. If not, by default, 80 port is used. 
  extraPortMappings:
  - containerPort: 80
    hostPort: <PROVIDE FREE PORT like 8085 or 8001>
  
  6. ./launch.sh --create-cluster #This will create a kind cluster which is required for TEKTON pipeline 
  7. When prompted for docker login, provide the docker login credentials. #This would be an one time effort
  ```
- 4. Preparing TEKTON Dashboard

TEKTON provides a helpful dashboard for monitoring and triggering pipelines from UI. It is recommended to have dashboard integrated. This step can be skipped, if TEKTON dashboard is not required for your environment
```
1. Execute ./launch.sh --deploy-dashboard
Exposed port is hostPort set in step 5 of preparing TEKTON environment
```
- 5. Service Accounts and Secrets preparation
Open values.yaml in the SIVT OVA and update the respective entries. 
```
#@data/values-schema
---
git:
  host: <giturl>
  repository: <username>/<repo_name>
  branch: <branch_name>
  username: <username>
  password: <GITPAT>
imagename: docker.io/library/service_installer_tekton:v153
imagepullpolicy: Never
```
**Running the PIPELINES**

- For triggering Day0 bringup of TKGM
```sh
./launch.sh  --exec-day0
```
**Re-running Pipelines**

From kubectl

```sh
    kubectl create -f run/day0-bringup.yml        
    #or
    ./launch.sh --exec-day0
```

**Listing Pipelines and taskruns**
```
Set the kubeconfig for the cluster, by exporting the cluster kind file. 
For example:
          export KUBECONFIG=/root/tekton/arcas-tekton-cicd/arcas-ci-cd-cluster.yaml
```

From tkn

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


**Monitoring Pipelines**


    tkn pr logs <tkgm-bringup-day0-jd2mp> --follow
    #For debugging. 
    tkn pr desc <tkgm-bringup-day0-jd2mp>


**Triggering the PIPELINES through git commits**

TEKTON pipelines also support execution of pipelines based on git commit changes. 
1. Complete the Preparation stages from 1 to 5. 
2. Install polling operator
```sh
kubectl apply -f https://github.com/bigkevmcd/tekton-polling-operator/releases/download/v0.4.0/release-v0.4.0.yaml
```
3. Open trigger-bringup-res.yml under trigger-based directory.
4. Update the fields of 
      - url: UPDATE FULL GIT PATH OF REPOSITORY
      - ref: BRANCH_NAME
      - frequency: 2m [time interval to check git changes. 2 minutes is set as default]
      - type: gitlab/github
  Save and exit. 
5. Open 
6. Update the fields of    
    - default: "UPDATE IMAGE LOCATION" to docker.io/library/service_installer_tekton:v153
    - default: "UPDATE FULL GIT PATH OF REPOSITORY" to full path of the git repository ending with .git
    - default: main to the branch in the private git repo. 
  Save and exit. 
7. Execute
```sh 
kubectl apply -f trigger-bringup-pipeline.yml; kubectl apply -f trigger-bringup-res.yml
```
8. Check if the pipeline is listed by 
```sh
tkn p ls
```
9. Perform a git commit on the branch with a commit message of "exec_bringup"
10. The pipelines will be triggered automatically. 



