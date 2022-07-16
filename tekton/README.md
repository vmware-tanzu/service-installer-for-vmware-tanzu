## Tekton Pipeline for Tanzu Kubernetes Grid

Tekton is a cloud-native solution for building CI/CD systems. Service Installer for VMware Tanzu (SIVT) is bundled with Tekton capability which provides the pipelines for Day-O deployment and Day2 operations of Tanzu Kubernetes Grid 1.5.4 on a vSphere backed environment.

## Features

-  Bringup of reference architecture based Tanzu Kubernetes Grid environment on vSphere
-  E2E Tanzu Kubernetes Grid deployment and configuration of AVI controller, management, shared services, and workload clusters, plugins, extensions
-  Rescale and resize Day-2 operations
-  Upcoming support of Tanzu Kubernetes Grid Service E2E deployment*
-  Upcoming support of Tanzu Kubernetes Grid Day-2 Upgrade support from 1.5.x to 1.5.4 with packages and extensions*

## Prerequisites

Tekton pipeline execution requires the following:

- Service Installer for VMware Tanzu (SIVT) OVA. Download from Marketplace https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true
- Docker login
- Service Installer Tekton Docker tar file. service_installer_tekton_v154.tar  
- Private git repo

## Tekton Pipeline Execution

### Preparation Steps

1. Git preparation:
   
   1. Create a private Git (Gitlab/Github) repository.
   2. Clone the code from https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/tree /1.3-1.5.4/tekton.
   3. Create a Git personal access token (PAT) and copy the token for later stages.
   4. Prepare `deployment.json` based on your environment. Refer to the SIVT Readme for preparing the config file.
   5. Commit the file under `config/deployment.json` in the Git repository.

1. SIVT OVA preparation: 
   1. Deploy the downloaded SIVT OVA and power on the VM.
   2. Log in to the SIVT OVA.
   3. Clone your private repository by using `git clone <private repo url>`.
  
1. Tekton pipeline environment preparation:  
  
   1. Log in to SIVT OVA.
   2. Browse to the location where the Git repository is cloned.
   3. Open `launch.sh` and update `TARBALL_FILE_PATH` to the absolute path where the Service Installer Docker TAR file is downloaded.</br>
   For example: 
      - `TARBALL_FILE_PATH="/root/tekton/arcas-tekton-cicd/service_installer_tekton_v153.tar"`
   </br>or
      - `TARBALL_URL="http://mynfsserver/images/service_installer_tekton_v153.tar"`
   4. Save the file and exit.
   5. Open `cluster_resources/kind-init-config.yaml`.
   
      Provide a free port for the nginx service to use. If you do not specify a port, by default 80 port is used.
         ```
         extraPortMappings:
         - containerPort: 80
           hostPort: <PROVIDE FREE PORT like 8085 or 8001>
         ```
   6. Run `./launch.sh --create-cluster`. 
          
        This command creates a kind cluster which is required for the Tekton pipeline.
   7. When prompted for the Docker login, provide the docker login credentials. 
    
      This needs to be done one time only.
  
1. Tekton dashboard preparation:

   Tekton provides a dashboard for monitoring and triggering pipelines from the UI. It is recommended to have the dashboard integrated. This step can be skipped, if Tekton dashboard is not required for your environment.
   - Execute ./launch.sh --deploy-dashboard

      The exposed port is `hostPort` set in step 5 of Tekton environment preparation.

5. Service accounts and secrets preparation:
   - Open `values.yaml` in the SIVT OVA and update the respective entries.
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

### Running the Pipelines

- For triggering the Day-0 bringup of Tanzu Kubernetes Grid, run the following command.
   ```sh
   ./launch.sh  --exec-day0
   ```

### Rerunning Pipelines

- For rerunning the pipelines, run one of the following commands.

   ```sh
    kubectl create -f run/day0-bringup.yml        
   ```
   or
   ```sh
   ./launch.sh --exec-day0
   ```

### Listing Pipelines and Task Runs

- Set the kubeconfig for the cluster by exporting the cluster kind file. 

   For example:
    ```  
    export KUBECONFIG=/root/tekton/arcas-tekton-cicd/arcas-ci-cd-cluster.yaml
    ```

- List the pipeline runs:

    ```
    tkn pr ls
    NAME                      STARTED          DURATION     STATUS
    tkgm-bringup-day0-jd2mp   53 minutes ago   58 minutes   Succeeded
    tkgm-bringup-day0-jqkbz   3 hours ago      47 minutes   Succeeded      
    ```
- List the task runs:
    ```
    tkn tr ls
    NAME                                                  STARTED          DURATION     STATUS        
    tkgm-bringup-day0-jd2mp-start-mgmt-create             46 minutes ago   20 minutes   Succeeded
    tkgm-bringup-day0-jd2mp-start-avi                     54 minutes ago   8 minutes    Succeeded
    tkgm-bringup-day0-jd2mp-start-prep-workspace          54 minutes ago   11 seconds   Succeeded
    ```

### Monitoring Pipelines

- For monitoring pipelines, use the following command:
  ```
  tkn pr logs <tkgm-bringup-day0-jd2mp> --follow
  ```
- For debugging, use the following command:
  ```
  tkn pr desc <tkgm-bringup-day0-jd2mp>
  ```

### Triggering the Pipelines through Git Commits**

Tekton pipelines also support execution of pipelines based on git commit changes. 
1. Complete the preparation stages from 1 to 5. 
2. Install the polling operator.
   ```sh
   kubectl apply -f https://github.com/bigkevmcd/tekton-polling-operator/releases/download/v0.4.0/release-v0.4.0.yaml
   ```
3. Open `trigger-bringup-res.yml` under `trigger-based` directory.
4. Update the following fields: 
      - url: UPDATE FULL GIT PATH OF REPOSITORY
      - ref: BRANCH_NAME
      - frequency: 2m [time interval to check git changes. 2 minutes is set as default]
      - type: gitlab/github
 
   Save changes and exit. 
5. Open trigger-bringup-pipeline.yml
6. Update the following fields:
    - default: "UPDATE IMAGE LOCATION" to docker.io/library/service_installer_tekton:v153
    - default: "UPDATE FULL GIT PATH OF REPOSITORY" to full path of the git repository ending with .git
    - default: main to the branch in the private git repo. 
  
   Save changes and exit.
7. Execute the following command.
   ```sh 
   kubectl apply -f trigger-bringup-pipeline.yml; 
   kubectl apply -f trigger-bringup-res.yml
   ```
8. Check if the pipeline is listed by using the following command.
   ```sh
   tkn p ls
   ```
9. Perform a git commit on the branch with a commit message of "exec_bringup".

   The pipelines will be triggered automatically. 
