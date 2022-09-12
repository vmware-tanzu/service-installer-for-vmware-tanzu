# Service Installer for VMware Tanzu 1.3.1 Release Notes

## What's New

- OVHcloud enhancements:
  - Bundled and pre-loaded Harbor in Service Installer for VMware Tanzu (SIVT) OVA
  - Support for NSX ALB deployment in No-Orchestrator mode in OVHcloud
- Activate proxy support for Tanzu Kubernetes Grid
- Gracefully shut down Tanzu Kubernetes Grid Service clusters to prepare for DC maintenance
- AWS - Added support to do AWS region specific deployment in an AWS account. Now, you can have multiple deployments within the same AWS account for testing purpose
- Tekton: Support for Tanzu Kubernetes Grid Service E2E deployment
- Tekton: Support for Tanzu Kubernetes Grid Day-2 Upgrade support from 1.5.x to 1.5.4 with packages and extensions

## Resolved Issues

- Scoping the AWS roles, policies, and profiles to the AWS zone instead of global. This activates multiple deployments in different zones of an AWS account.
- Service Installer for VMware Tanzu was bundling Harbor version which had a vulnerability. Updated the bundled Harbor to the latest version. 
- Control plane and workload volumes are appended with special characters.
- Service Installer for VMware Tanzu UI doesn't populate information for additional control plane and workload volumes.

## Known Issues

- Service Installer for VMware Tanzu is unable to fetch cluster images from the content library. This happens due to a known issue with Tanzu on vSphere. The subscribed content library needs to be synced manually sometimes to update with the images.
- TMC integration of management and workload clusters fails for AWS non air-gapped compliant deployment, due to a known issue in the TMC API.
- Prometheus deployment fails if SaaS is activated in non-airgapped AWS deployment.
- Harbor deployment fails both with and without SaaS in multi workload cluster configurations in non-airgap AWS deployment.
- In case you are using proxy with self-signed or custom CA certificate, SIVT fails to pull the kind image while deploying Tanzu Kubernetes Grid management cluster in a vSphere VDS environment.</br> 
   
   **Resolution:** Before initiating the deployment with SIVT, perform the following steps:
    
    1. Import the proxy certificate into the SIVT VM.
    1. Run the following commands: 
        ```
        cat proxy-cert.pem >> /etc/pki/tls/certs/ca-bundle.crt
        systemctl restart docker
        ```
- Tanzu Kubernetes Grid deployment with NSX-T networking fails with `Failed to configure vcf list index out of range`.
   
   **Resolution:** This issue occurs only when you deactivate the shared services cluster in UI or the config file and proceed with management or workload cluster deployment.
   If the shared services cluster is activated and all the configuration details are provided, then deployment proceeds.

## Download

- Download the Service Installer OVA and AWS solutions from [VMware Marketplace: Service Installer for VMware Tanzu](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true).
