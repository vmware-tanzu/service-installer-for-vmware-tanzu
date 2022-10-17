# Tekton Pipeline for Tanzu Kubernetes Grid

Tekton is a cloud-native solution for building CI/CD system which provides the pipelines for Day-0 deployment and Day-2 operations of Tanzu Kubernetes Grid 1.5.x for a vSphere backed environment.

## Features

- Bring up of reference architecture based Tanzu Kubernetes Grid environment on vSphere
- E2E Tanzu Kubernetes Grid deployment and configuration of AVI controller, management, shared services, and workload clusters, plug-ins, extensions
- E2E bring up of vSphere with Tanzu environment with enabling of WCP, supervisor cluster, and workload cluster with plug-ins and extensions 
- Rescale and resize Day-2 operations
- Day-2 operations of Tanzu Kubernetes Grid upgrade from 1.5.x to 1.5.4 with packages and extensions

## Prerequisites

Tekton pipeline execution requires the following:

- Linux VM with `kind` cluster of version v1.21 or later
  - **Note:** SIVT OVA can also be used as Linux VM with `kind` preloaded.
  - SIVT OVA can be downloaded from: https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true
- Service Installer Tekton Docker file:
  - Download existing Service Installer Tekton tar file using Docker login from: http://sc-dbc2131.eng.vmware.com/smuthukumar/SERVICE_INSTALLER_IMAGES/service_installer_tekton_v154b.tar

    OR
  - Generate own Docker image using existing dockerfile in repo. For more information, see the following sections.
- Private GitLab or GitHub repo

## Tekton Pipeline Execution

### Preparation Steps

1. Git preparation:
   
   1. Create a private Git (GitLab or GitHub) repository.
   2. Clone the code from https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/tree/1.3.1-1.5.4/tekton.
   3. Create a Git personal access token (PAT) and copy the token for later stages.
   4. For Tanzu Kubernetes Grid on vSphere, prepare `deployment-config.json` based on your environment and upload under `config/deployment-config.json` in the private git repo (Refer  `sample-json/sample-deployment-config.json`).
   5. For vSphere with Tanzu, prepare `deployment-config-wcp.json` and `deployment-config-ns.json` based on your environment and upload under `config/deployment-config-wcp.json` and `config/deployment-config-ns.json` respectively in the private git repo. (Refer  `sample-json/sample-deployment-config-wcp.json` and `sample-jsonsample-deployment-config-ns.json`).
   6. For Tanzu Kubernetes Grid on VCF, prepare `deployment-config.json` based on your environment and upload under `config/deployment-config.json` in private git repo (Refer  `sample-json/sample-deployment-config-vcf.json`).
   7. Refer the SIVT README.md for creation of respective JSON files.

2. Linux VM preparation:
   1. Power on and log in to the Linux/SIVT VM.
   2. Clone your private repository by using `git clone <private repo url>`.
  
3. Tekton pipeline environment preparation:  
  
   1. In your Linux/SIVT VM, browse to the location where the Git repository is cloned.
   2. You can generate own Docker image OR use a pre-existing Docker image.
      1. To use a pre-existing Docker image, open `launch.sh` and update `TARBALL_FILE_PATH` to the absolute path where the Service Installer Docker TAR file is downloaded.
         
         For example:

            - `TARBALL_FILE_PATH="/root/tekton/arcas-tekton-cicd/service_installer_tekton_v15x.tar"`
            
                or
            - `TARBALL_URL="http://mynfsserver/images/service_installer_tekton_v15x.tar"`
            
            Save the file and exit.
      2. To generate the Docker image using dockerfile, run the following command.
            ```Shell
            ./launch.sh --build_docker_image
            ```

         This will generate a Docker image named as `sivt_tekton:tkn` using the existing dockerfile.

    3. Open `cluster_resources/kind-init-config.yaml` and provide a free port for the nginx service to use.
  
        If you do not specify a port, port 80 is used by default.
        
          ```
            extraPortMappings:
            - containerPort: 80
              hostPort: <PROVIDE FREE PORT like 8085 or 8001>
          ```
  
    4. Run the following command.
        ```shell
        ./launch.sh --create-cluster
        ``` 
        
        This command creates a `kind` cluster, which is required for the Tekton pipeline.
  
    5. When prompted for the Docker login, provide the Docker login credentials.
          
        This needs to be done one time only.
  
4. Tekton dashboard preparation:

   Tekton provides a dashboard for monitoring and triggering pipelines from the UI. It is recommended to have the dashboard integrated. This step can be skipped if Tekton dashboard is not required for your environment.
   - Run the following command:
     ```shell
     ./launch.sh --deploy-dashboard
     ```
      The exposed port is `hostPort` set in step 3 of `Tekton pipeline environment preparation`.

5. Service accounts and secrets preparation:
   - Browse to the directory in Linux/SIVT VM where private git repo is cloned 
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
      imagename: docker.io/library/service_installer_tekton:v154b
      imagepullpolicy: Never
      refreshToken: <MARKETPLACE REFRESH TOKEN>
      ```

### Running the Day-0 Pipelines

#### Day-0 bringup of Tanzu Kubernetes Grid

1. Update the desired state YAML file:
   - Browse to the `desired-state` directory in Linux/SIVT VM and update `desired-state.yml` file as below:
   - Update env as `vsphere` or `vcf`
     ```
     ----
     version:
       tkgm: 1.5.4
       env: vsphere
     ```
2. Run the following command:
   ```shell
   ./launch.sh  --exec-day0
   ```

#### Day-0 bringup of vSphere with Tanzu

1. Update desired state YAML file:
   - Browse to the `desired-state` directory in Linux/SIVT VM and update `desired-state.yml` file as below:
     ```
     ----
     version:
       tkgs: 1.5
       env: vsphere
     ```
2. Run the following command:
   ```shell
   ./launch.sh  --exec-tkgs-day0
   ```
### Running the Day-2 Pipelines

1. Update the desired state YAML file:
    - Browse to the `desired-state` directory in Linux/SIVT VM and update `desired-state.yml` file as below:
    - Update env as `vsphere` or `vcf`
      ```
      ----
      version:
        tkgm: 1.5.4
        env: vsphere
      ```
2. If the targeted Docker image for upgrade is already available in the `kind` cluster, skip this step. Else, do the below steps:
   - Open `launch.sh` and update the `UPGRADE_TARBALL_FILE_PATH` variable to the absolute path where the Service Installer Docker TAR file is downloaded.
     For example: 
      - `UPGRADE_TARBALL_FILE_PATH="/root/tekton/arcas-tekton-cicd/service_installer_tekton_v15x.tar"`
   - Run the following command:
     ```shell
     ./launch.sh --load-upgrade-imgs
     ```
3. To upgrade all clusters, run:
    ```shell
    ./launch.sh  --exec-upgrade-all 
    ```
4. To upgrade only the management cluster, run:
    ```shell
    ./launch.sh  --exec-upgrade-mgmt 
    ```

### Listing Pipelines and Task Runs

- Set the kubeconfig for the cluster by exporting the cluster kind file. 

   For example:
    ```  
    export KUBECONFIG=/root/tekton/arcas-tekton-cicd/arcas-ci-cd-cluster.yaml
    ```

- List the pipeline runs:
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
- List the task runs:
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


### Monitoring Pipelines

- For monitoring pipelines, use the following command:
  - Tanzu Kubernetes Grid:
    ```
    tkn pr logs <tkgm-bringup-day0-jd2mp> --follow
    ```
  - TKGs:
    ```
    tkn pr logs <tkgs-bringup-day0-z5qf4> --follow
    ```
- For debugging, use the following command:
  - Tanzu Kubernetes Grid:
    ```
    tkn pr desc <tkgm-bringup-day0-jd2mp>
    ```
  - vSphere with Tanzu:
    ```
    tkn pr desc <tkgs-bringup-day0-z5qf4>
    ```

### Triggering the Pipelines through Git Commits**

Tekton pipelines also support execution of pipelines based on git commit changes. 
1. Complete the preparation stages from 1 to 5. 
2. Install the polling operator.
   ```sh
   kubectl apply -f https://github.com/bigkevmcd/tekton-polling-operator/releases/download/v0.4.0/release-v0.4.0.yaml
   ```
3. Browse to Linux/SIVT VM directory to open `trigger-bringup-res.yml` under the `trigger-based` directory.
4. Update the following fields: 
      - url: UPDATE FULL GIT PATH OF REPOSITORY
      - ref: BRANCH_NAME
      - frequency: 2m [time interval to check git changes. 2 minutes is set as default]
      - type: gitlab/github
 
   Save changes and exit. 
5. Open `trigger-bringup-pipeline.yml`.
6. Update the following fields:
    - default: "UPDATE IMAGE LOCATION" to docker.io/library/service_installer_tekton:v153
    - default: "UPDATE FULL GIT PATH OF REPOSITORY" to full path of the git repository ending with .git
    - default: main to the branch in the private git repo. 
  
   Save changes and exit.
7. Run the following command.
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
