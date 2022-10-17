# Service Installer for VMware Tanzu 1.4 Release Notes

## What's New

- Support for Tanzu Kubernetes Grid 1.6.0.
- Support for configuring NSX-T Cloud for all VDS with NSX-T networking based environments.
- Ability to skip all the pre-flight checks with `--skip_precheck` flag on CLI.
- Swagger integration with Service Installer so users can access all the workflow APIs here: `http://<SIVT_IP>:5000/swagger`
- Standalone Velero can be deployed using Service Installer for backup and restore tasks. This does not require TMC integration.
- Custom certificates for Tanzu Kubernetes Grid can now be imported through Service Installer.
- Support for proxy-based deployments on Tanzu with VMware VDS environments. 
- Support for providing configured subscribed content library for Tanzu on VMware deployments through Service Installer UI.
- Harbor enhancements: 
   - Removed dependency on DHCP for Service Installer build with Harbor. DHCP is no longer a mandatory requirement.
- Tekton enhancements: 
   - Support for vSphere with NSX-T based deployments.
   - Support for Tekton Service Installer Docker image creation
   - Support for re-entrant and resiliency of Tekton pipeline
- Precheck enhancements:
   - Check and filter out storage policies with encryption as those policies are not valid for deploying Tanzu on VMware DVS.
   - Check if all the default gateways are pingable or not.
   - Check for MTU size
   - Check for HA and DRS activation status on vCenter.

## Resolved Issues

- Service Installer by default goes into non-orchestrated workflow for build with harbor integrated.
- Service Installer UI is unable to update proxy details on Tanzu with VMware deployments.
- Service Installer fails to deploy workload cluster with TMC integration on proxy configured environments.
- For Tanzu on VMware DVS deployments using TMC, control plane nodes were getting configured with worker node VM class.
- Standard package repository installation fails on Tanzu on VMware DVS configured with proxy-based deployments.
- Validated Key Cloak as an OICD provider for Pinniped configuration on Tanzu Kubernetes Grid clusters.


## Known Issues

- Service Installer for VMware Tanzu is unable to fetch cluster images from the content library. This happens due to a known issue with Tanzu on vSphere. The subscribed content library needs to be synced manually sometimes to update with the images.
- TMC integration of management and workload clusters fails for AWS non air-gapped compliant deployment, due to a known issue in the TMC API.
- Prometheus deployment fails if SaaS is activated in non-airgapped AWS deployment.
- Harbor deployment fails both with and without SaaS in multi workload cluster configurations in non-airgapped AWS deployment.
- In case you are using proxy with self-signed or custom CA certificate, SIVT fails to pull the `kind` image while deploying Tanzu Kubernetes Grid management cluster in a vSphere VDS environment.</br> 
   
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
