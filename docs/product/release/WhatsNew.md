# Service Installer for VMware Tanzu 1.3 Release Notes

## What's New

### AWS Automation Enhancements and Compliance Support

- Support for Tanzu Kubernetes Grid (TKG) 1.5.3 deployment on federal air-gapped AWS with STIG hardening and FIPS compliance
- Support for Tanzu Kubernetes Grid (TKG) 1.5.3 deployment on internet-connected AWS (compliant and non-compliant)
- Ability to deploy management and workload clusters
- Support for deploying the following extensions:

  - Harbor
  - Prometheus
  - Grafana
  - Fluent Bit
  - Contour
  - Cert-Manager
  - Pinniped with OIDC and LDAP identity management
- Support for Tanzu Kubernetes Grid deployment with Ubuntu 18.04 (Ubuntu OS image is STIG hardened/FIPS compliant + TKG FIPS enabled) for airgap deployment
- Support for Tanzu Kubernetes Grid deployment with Amazon Linux 2 (AL2 vanilla OS image + TKG FIPS enabled) for airgap deployment
- Support for Tanzu Kubernetes Grid deployment with Ubuntu 18.04 (compliant and non-compliant)
- Clean up feature - Ability to destroy the deployments performed by Service Installer for VMware Tanzu (SIVT) and start from scratch
- GP2 volume support for Amazon Linux 2 and Ubuntu 18.04 for airgap deployment
- Enhanced pre-checks for the user inputs and graceful handling of failures
- Enhanced pre-checks to validate VPC endpoints needed for airgapped deployment.
- User-friendly error messages and debug messages
- Make targets are modularised into independently deployable components
- Tarballs containing all the dependencies are made available to enable users to easily transfer all the required binaries to airgap environment
  - `service-installer-for-AWS-Tanzu-1.3.tar.gz` - Tarball containing all the automation scripts and deployment dependencies for non-airgap compliant and non-compliant deployments.
  - `service-installer-for-AWS-Tanzu-with-Dependency-1.3.tar.gz` - Tarball containing all the Tanzu Kubernetes Grid / Tanzu Kubernetes releases (TKR) FIPS binaries, Harbor, deployment dependencies, and automation scripts, to address following deployment usecases for airgap deployment
      - Automated Federal compliant deployment
      - Manual deployment (in case user wants to deploy by following the reference architecture and deployment guide)

### vSphere Enhancements

- Support for Tanzu Kubernetes Grid 1.5.4 along with AVI 21.1.4
- Support for customisation of Tanzu Kubernetes Grid Service configuration
  - CNI - User can use either Antrea or Calico
  - Support for Trusted CA certificate
- Support for bring your own certificate (BYOC) / user certificate for Tanzu Kubernetes Grid proxy based deployments
- Additional volume support for Tanzu Kubernetes Grid Service
- Additional customisations for user-managed packages by exposing the YAML
- Auto-completion of `arcas` commands feature
- Implemented k alias names for `kubectl`
- Service Installer for VMware Tanzu UI allows to skip shared services cluster and workload cluster deployments
- Support for updated packages for Photon 3.0 operating system

### Tekton Enhancements

- Bringup of reference architecture based Tanzu Kubernetes Grid environment on vSphere TKGM 1.5.3 and 1.5.4
- E2E Tanzu Kubernetes Grid deployment and configuration of AVI controller, management, shared services, and workload clusters, plugins, extensions
- Rescale and resize Day-2 operations
- Upcoming support of Tanzu Kubernetes Grid Service E2E deployment*
- Upcoming support of Tanzu Kubernetes Grid Day-2 Upgrade support from 1.5.x to 1.5.4 with packages and extensions*

## Resolved Issues

- Datacenter, cluster, and datastores now support sub-folder structure.
- Tanzu Service Mesh (TSM) and Tanzu Observability (TO) node size restrictions are made liberal now.
- Work around steps for Contour issue on shared services cluster
- WCP enablement fails with DNS compliant errors
- Shared services and workload cluster deployment failure in VMC on AWS environment when no parent resource pool is selected in the SIVT UI
- Allow user to retain installed OVA and susbcribed content lib after SIVT cleanup is used
- Arcas with TMC integration of vSphere supervisor cluster fails workload cluster creation: could not find VMClass for nodepool
- Add pre-check for valid avi-password-base64 and avi-backup-passphrase-base64 values


## Known Issues

- Tanzu Kubernetes Grid Service proxy deployment is not supported in this release.
- TKGm Management cluster creation with proxy is failing with unable to update no_proxy config on kube-api server. This is not a SIVT issue.
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

## Download

- Download the Service Installer OVA and AWS solutions from [VMware Marketplace: Service Installer for VMware Tanzu](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true).
