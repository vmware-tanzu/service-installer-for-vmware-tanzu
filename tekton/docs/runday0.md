# Run Day-0 Tekton Pipelines for Tanzu Kubernetes Grid

Use the following commands to initiate the day-0 pipelines for Tanzu Kubernetes Grid.

## Bringup of Tanzu Kubernetes Grid

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

2. Run the following command.

   ```shell
   ./launch.sh  --exec-day0
   ```

## Bringup of vSphere with Tanzu

1. Update desired state YAML file.
   
   1. Browse to the `desired-state` directory in Linux or SIVT VM.
     
   2. Update the `desired-state.yml` file as below.

	   ```
       ----
       version:
         tkgs: 1.5
         env: vsphere
       ```

2. Run the following command.

   ```shell
   ./launch.sh  --exec-tkgs-day0
   ```
   
[Back to Main](../README.md)
   
