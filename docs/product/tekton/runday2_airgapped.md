# Prepare to Run Day-2 Tekton Pipelines for Tanzu Kubernetes Grid in Internet-Restricted Environment

Complete the following preparatory tasks for upgrading Tanzu Kubernetes Grid in Internet-restricted environments.

## Prerequisites

- Refer to the `Prerequisites for Tekton Infrastructure` section of [Prepare to Run Day-0 Tekton Piplines for TKG in Internet-Restricted Environment](./docs/runday0_airgapped.md).
- Refer to the `Prepare Internet-Restricted Environment` section of [Prepare to Run Day-0 Tekton Pipelines for TKG in Internet-Restricted Environment](./docs/runday0_airgapped.md).

## Step 1: Download Tanzu Images of Targeted Upgrade TKG Version on Jumbox Host

- Refer to the below link to copy Tanzu images to Harbor:
  https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/1.6/vmware-tanzu-kubernetes-grid-16/GUID-mgmt-clusters-image-copy-airgapped.html

- **Note:** Download Tanzu images for the targeted upgrade Tanzu Kubernetes Grid version.

## Step 2: Prepare Tekton Docker Image of Targeted Upgrade TKG Version on Jumpbox Host

- Refer `Step 2: Prepare Tekton Docker Image on Jumpbox Host` of of [Prepare to Run Day-0 Tekton Pipelines for TKG in Internet-Restricted Environment](./docs/runday0_airgapped.md).

- **Note:** Create Docker image for the targeted upgrade Tanzu Kubernetes Grid version.
  
## Step 3: Update User Input Files in Existing Git Repo

1. Update already created `deployment-config.json` of day0  and upload under `config/deployment-config.json` in the private git repo (Refer to `sample-json/sample-deployment-config.json`).
   Update parameter `tkgCustomImageRepository` to Harbor project from where Tanzu images are to be pulled.

2. Update the desired state YAML file.
   1. Browse to the `desired-state` directory in Linux or SIVT VM.
   2. Update the `desired-state.yml` file as below.
      - Set `env` as `vsphere`.

      ```
       ----
       version:
         tkgm: 1.5.4
         env: vsphere
       ```

3. Update `values.yaml` file to Tekton Docker image of the desired version.

## Step 4: Run Day-2 Tekton Pipelines for Tanzu Kubernetes Grid

1. Run the following command to upgrade all clusters including the management cluster.

   ```shell
   ./launch.sh  --exec-upgrade-all 
   ```

1. Run the following command to upgrade only the management cluster.

    ```shell
    ./launch.sh  --exec-upgrade-mgmt
    ```

3. Refer below section to monitor the pipelines.
   - [Monitor Tekton Pipeline Runs, Task Runs, and Pipelines](./docs/monitortekton.md)

[Back to Main](./README.md)