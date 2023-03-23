# Run Day-2 Tekton Pipelines for Tanzu Kubernetes Grid

1. Update the desired state YAML file.
   
   1. Browse to the `desired-state` directory in Linux or SIVT VM.
   
   2. Update the `desired-state.yml` file as below. 
      - Set `env` as `vsphere` or `vcf`.
     
      ```
       ----
       version:
         tkgm: 1.5.4
         env: vsphere
       ```

2. Generate the SIVT Tekton Docker TAR file.
    1. [RECOMMENDED] To generate the Docker image using dockerfile, follow below steps:
       1. Update `desired-state/desired-state.yml` file with desired version
       2. Run the following command.
               ```Shell
               ./launch.sh --build_docker_image
               ```
       Running this command generates a Docker image as per the version mentioned in `desired-state/desired-state.yml` file.
          Examples:
          ```
          1.5.3 --> sivt_tekton:v153
          1.5.4 --> sivt_tekton:v154
          ```
          Note: Before running the command, install these Python dependencies: `iptools`, `paramiko`, and `retry`
   
    2. To use a pre-existing Docker tar image, open `launch.sh` and update `UPGRADE_TARBALL_FILE_PATH` to the absolute path where the Service Installer Docker TAR file is present.
         
        For example:

        - `UPGRADE_TARBALL_FILE_PATH="/root/tekton/arcas-tekton-cicd/service_installer_tekton_v15x.tar"`
            
        Save the file and exit.

       Note: Using an existing TAR file is not recommended. 
       However, for setups like Internet-restricted environments where the TAR file can't be generated, you can use an existing TAR file.```

    3. Run the following command.
     ```shell
     ./launch.sh --load-upgrade-imgs
     ```

4. To upgrade all clusters, run the following command.

    ```shell
    ./launch.sh  --exec-upgrade-all 
    ```

5. To upgrade only the management cluster, run the following command.

    ```shell
    ./launch.sh  --exec-upgrade-mgmt 
    ```
   
[Back to Main](./README.md)
