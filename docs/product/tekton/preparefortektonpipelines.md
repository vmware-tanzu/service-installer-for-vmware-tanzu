# Prepare to Run Tekton Pipelines for Tanzu Kubernetes Grid

Complete the following preparatory tasks to running Tekton pipelines for Tanzu Kubernetes Grid.

## Prepare Git Environment
   
1. Create a private Git (GitLab or GitHub) repository.
   
2. Clone the code from https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/tree/1.3.1-1.5.4/tekton.
   
3. Create a Git personal access token (PAT) and copy the token for later stages.
   
4. For Tanzu Kubernetes Grid on vSphere, prepare `deployment-config.json` based on your environment and upload under `config/deployment-config.json` in the private git repo (Refer  `sample-json/sample-deployment-config.json`).
   
5. For vSphere with Tanzu, prepare `deployment-config-wcp.json` and `deployment-config-ns.json` based on your environment and upload under `config/deployment-config-wcp.json` and `config/deployment-config-ns.json` respectively in the private git repo. (Refer  `sample-json/sample-deployment-config-wcp.json` and `sample-jsonsample-deployment-config-ns.json`).
   
6. For Tanzu Kubernetes Grid on VCF, prepare `deployment-config.json` based on your environment and upload under `config/deployment-config.json` in private git repo (Refer  `sample-json/sample-deployment-config-vcf.json`).
   
7. Refer the SIVT README.md for creation of respective JSON files.

## Prepare Linux VM 

1. Power on and log in to the Linux or SIVT VM.
   
2. Clone your private repository by using `git clone <private repo url>`.
  
## Prepare Tekton Pipeline Environment
  
1. In your Linux or SIVT VM, browse to the location where the Git repository is cloned.
   
2. Generate the SIVT Tekton Docker TAR file.
    1. [RECOMMENDED] To generate the Docker image using dockerfile, follow below steps:
       1. Update `desired-state/desired-state.yml` file with desired version
       2. Run the following command.
               ```Shell
               ./launch.sh --build_docker_image
               ```
       Note: Please login to docker using credentials manually, else may face issues related to rate limiting error
       Running this command generates a Docker image as per the version mentioned in `desired-state/desired-state.yml` file.
          Examples:
          ```
          1.5.3 --> sivt_tekton:v153
          1.5.4 --> sivt_tekton:v154
          ```
          **Note:** Before running the command, install these Python dependencies: `iptools`, `paramiko`, and `retry`
   
    2. To use a pre-existing Docker tar image, open `launch.sh` and update `TARBALL_FILE_PATH` to the absolute path where the Service Installer Docker TAR file is downloaded.
         
        For example:

        - `TARBALL_FILE_PATH="/root/tekton/arcas-tekton-cicd/service_installer_tekton_v15x.tar"`
            or
        - `TARBALL_URL="http://mynfsserver/images/service_installer_tekton_v15x.tar"`
            
        Save the file and exit.

       **Note:** Using an existing TAR file is not recommended. 
       However, for setups like Internet-restricted environments where the TAR file can't be generated, you can use an existing TAR file.```

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
          
    This step needs to be done one time only.
  
## Prepare Tekton Dashboard

Tekton provides a dashboard for monitoring and triggering pipelines from the UI. It is recommended to have the dashboard integrated. This step can be skipped if Tekton dashboard is not required for your environment.

- Run the folllowing command:
    ```shell
     ./launch.sh --deploy-dashboard
    ```
    The exposed port is `hostPort` set in step 3 of **Prepare Tekton Pipeline Environment**.

## Prepare Service Accounts and Secrets

1. Browse to the directory in Linux or SIVT VM where private git repo is cloned 

2. Open `values.yaml` in the SIVT OVA and update the respective entries.
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

[Back to Main](./README.md)
