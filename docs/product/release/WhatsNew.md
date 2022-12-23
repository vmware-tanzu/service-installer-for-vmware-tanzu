# Service Installer for VMware Tanzu 1.4.1 Release Notes

## What's New

- Tanzu Kubernetes Grid Federal air-gapped deployment on vSphere. Service Installer for VMware Tanzu now supports following flavours of deployments.
  1. vSphere + Internet connected + Compliant deployment
  2. vSphere + Internet connected + non-compliant deployment
  3. vSphere + air-gapped + compliant deployment
  4. vSphere + air-gapped + non-compliant deployment
- Non-orchestrated Tanzu Kubernetes Grid deployment on vSphere VDS.
- Users can choose AVI for L7 ingress applications. Contour is used by default. For NSX Nodeport mode is supported.
- Tanzu for Kubernetes Operations deployment on VMware Cloud Director (VCD) (CSE + packages) in Internet-connected environments.
  - VCD terraform modules are used for development
  - Both brownfield and greenfield deployments are supported
- Service Installer for VMware Tanzu comes with pre-bundled Harbor and STIG/FIPS compliant Tanzu Kubernetes Grid dependencies are loaded in the background during the SIVT bootup.
- Migrated SIVT build system from StudioVA to Capiva and addressed following issues, 
  - Reduces SIVT OVA sizes. Regular ova from 3GB to 2GB and SIVT harbor ova from 30GB to 19GB. 
  - Resolves build issues such as: no-space error, 2x size issues, etc. 
  - Enhanced the integrated Harbor solution. Removed dependency on Tanzu Kubernetes Grid tar download. 
- Tekton enhancements: 
  - Tanzu Kubernetes Grid deployment on Federal Air-gapped environments (Day 0/Day 2)
  - Air-gapped: Bring up Tekton Triggers and Polling Intervals

## Resolved Issues

- Post validation of 'AVI controller', next button user action is not proceeding further 
- SIVT is not deploying latest Harbor package as part of the deployment
- Add pre-check to see if Tanzu, NSX and vCenter licenses are valid
- Parameterise the data-values for Contour and Fluent-bit
- Improvise the error message if expired/insufficient permission 'MarketPlace refresh token' is used
- Implement pre-check to control the date and time on ESXi nodes and vCenter
- SIVT giving standard package repository error for TKGs deployment

## Known Issues

- Service Installer for VMware Tanzu is unable to fetch cluster images from the content library. This happens due to a known issue with Tanzu on vSphere. The subscribed content library needs to be synced manually sometimes to update with the images.
- TMC integration of management and workload clusters fails for AWS non air-gapped compliant deployment, due to a known issue in the TMC API.
- Prometheus deployment fails if SaaS is activated in non-airgapped AWS deployment.
- Vcd Api call takes time depending on environment configuration , please re-trigger  the SIVT command after 1 min delay  
- Creating ALB Service Engine Group assignment to Edge Gateway fails intermittently. [Terraform provider issue](https://github.com/vmware/terraform-provider-vcd/issues/923)
- Activating AVI L7 on vSphere with NSXT environments over NodePortLocal mode fails to bringup AKO pods. [MAPBUA-1546](https://jira.eng.vmware.com/browse/MAPBUA-1546)
- SIVT is supposed to download `Ubuntu-2004-kube-v1.22.9.ova`. Currently, it is downloading `Ubuntu-2004-kube-v1.23.8.ova`.
  **Note:** If user needs a specific version of Ubuntu + K8S ova, download it from marketplace and upload it to the K8S catalog.
- Harbor deployment fails both with and without SaaS in multi workload cluster configurations in non-airgapped AWS deployment.
- In case you are using proxy with self-signed or custom CA certificate, SIVT fails to pull the `kind` image while deploying Tanzu Kubernetes Grid management cluster in a vSphere VDS environment.</br>
  **Resolution:** Before initiating the deployment with SIVT, perform the following steps:

  1. Import the proxy certificate into the SIVT VM.
  2. Run the following commands:
      ```
      cat proxy-cert.pem >> /etc/pki/tls/certs/ca-bundle.crt
      systemctl restart docker
      ```
- In case you are using SIVT OVA with embedded Harbor, if Docker restarts or SIVT VM reboots, it may result in embedded Harbor failure. 

  **Resolution:** Perform the following steps:

  1. SSH to the SIVT VM.
  2. Go to the `/opt/vmware/arcas/tools/harbor`
  3. Run the following commands:
      ```
      docker-compose stop
      find common/ -type f -exec chmod 0755 \{\} \;
      docker-compose up -d
      ```
- Tanzu Kubernetes Grid deployment with NSX-T networking fails with `Failed to configure vcf list index out of range`.

  **Resolution:** This issue occurs only when you deactivate the shared services cluster in UI or the config file and proceed with management or workload cluster deployment.
  If the shared services cluster is activated and all the configuration details are provided, then deployment proceeds.

## Download

- Download the Service Installer OVA and AWS solutions from [VMware Marketplace: Service Installer for VMware Tanzu](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true).
