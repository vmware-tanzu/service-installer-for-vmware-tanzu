# Service Installer for VMware Tanzu 1.3.1 Release Notes

## What's New

- OVH engagement deliverables,  
  - Bundle and pre-load Harbor in SIVT ova.
  - Support NSX ALB deployment in No-Orchestrator mode in OVH Cloud.
- Enable proxy support for TKGm
- Gracefully shutdown and bring up TKGs clusters to prepare for DC maintenance.
- AWS - Added support to do aws-rigion specific deployment in an AWS account. Now we can have multiple deployments within same AWS account for testing purpose.
- Tekton: Support for Tanzu Kubernetes Grid Service E2E deployment
- Tekton: Support for Tanzu Kubernetes Grid Day-2 Upgrade support from 1.5.x to 1.5.4 with packages and extensions

## Resolved Issues
- Scoping the AWS roles/policies/profiles to the Aws-Zone than global. This should help to do multiple deployments in different zones of an AWS account.
- SIVT was bundling Harbor version which had vulnerability. Updated the Harbor to the latest version. 
- Control Plane and Workload volumes are appended with special characters.
- SIVT UI doesn't populate information for additional Control plane and workload volumes.

## Known Issues

- SIVT unable to fetch cluster images from content library. This happens due to the known-issue with Tanzu on vSphere. The subscribed content library needs to be synced manually sometimes to update with the images.
- TMC integration of management and workload clusters fails for AWS non air-gapped compliant deployment, due to a known issue in the TMC API.
- Prometheus deployment fails if SaaS is enabled in non-airgap AWS deployment.
- Harbor deployment fails both with and without SaaS in multi workload cluster configurations in non-airgap AWS deployment.
- In case you are using proxy with self-signed or custom CA certificate, SIVT fails to pull the kind image while deploying Tanzu Kubernetes Grid management cluster in a vSphere VDS environment.</br> 
   **Resolution:** Before initiating the deployment with SIVT, perform the following steps:
    1. Import the proxy certificate into the SIVT VM.
    1. Run the following commands: 
        ```
        cat proxy-cert.pem >> /etc/pki/tls/certs/ca-bundle.crt
        systemctl restart docker
        ```
- TKG deployment with NSX-t networking fails with "Failed to configure vcf list index out of range". 
   **Resolution:** This is happening only when we disable the shared service cluster in UI/config file and proceed with mgmt/workload cluster deployment.
   If the shared service cluster is enabled and all the configuration details are provided, then deployment proceeds.

## Download

- Download the Service Installer OVA and AWS solutions from [VMware Marketplace: Service Installer for VMware Tanzu](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true).
- Refer to [Service Installer for VMware Tanzu GitHub repository](https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu) for the automation code.
