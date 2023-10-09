# Setup CI/CD infra and pipelines


### 1. Prepare Git Environment
   

1.  Create a Git (GitLab or GitHub) repository with environment directory structure.
      - Reference directory structure can be cloned from  https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/tree/2.1.1/tekton/sample_user_lab_details
2. Create a Git personal access token (GITPAT) for the created repository.
3. Update `values.yaml` file with the required fields. 
    ```bash
        #@data/values
        ---
        git:
            host: <GITURL> #github.com 
            repository: <REPOUSER>/<REPONAME> #user/myrepo
            branch: <BRANCH_NAME> 
            username: <GITUSERNAME>
            password: <GIT_PAT>
        refreshToken: <MARKET PLACE TOKEN>
    ```
   
### 2. Prepare Linux VM 

1. Power on and log in to the Linux console/VM.   
2. Create a directory for CI/CD setup. 
3. Clone or copy contents from  https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/tree/2.1.1/tekton to the CI/CD directory. 
3. Update `values.yaml` file with the required fields.
  
### 3. Prepare CI/CD Pipeline Environment
  
1. In your Linux or Service Installer for VMware Tanzu VM, browse to the location where the CI/CD directory is located.   
2. Execute:
    ```bash
        ./prepare-sivt-tekton.sh --setup  #Provide docker login credentials when prompted. This would be a one-time requirement. 
    ```

The CI/CD bringup will be completed within 5-6 minutes. 

You can now proceed to execute the pipelines. 

[Back to Main](../README.md)
