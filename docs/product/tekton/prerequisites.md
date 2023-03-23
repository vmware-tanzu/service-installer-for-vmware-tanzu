# Prerequisites for Tekton Pipelines For Tanzu Kubernetes Grid

Tekton pipeline execution for Tanzu Kubernetes Grid requires the following:

- Linux VM with `kind` cluster of version v1.21 or later
  - **Note:** SIVT OVA can also be used as Linux VM with `kind` preloaded.
  - SIVT OVA can be downloaded from: https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true
- Service Installer Tekton Docker file:
  - Generate your own Docker image using the existing dockerfile in the repository. For more information, see the [Prepare Tekton Pipeline Environment](./preparefortektonpipelines.md)
- Private GitLab or GitHub repository

[Back to Main](./README.md)
