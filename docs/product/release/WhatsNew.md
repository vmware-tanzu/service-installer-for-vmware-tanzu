# Service Installer for VMware Tanzu 2.1.0 Release Notes

## What's New

- SIVT ova now supports Tanzu Kubernetes Grid 2.1.0
- Workload cluster creation with AVI_LABELS to place the workload control plane VIP on respective SE group
- Integrate Tanzu Kubernetes Grid specific-version download script in SIVT VM
- For the DVS mode, for all the networks it shows "SEGMENT NAME", this needs to be changed to "Portgroup name"
- AVI 21.1.4 support for TKGs and TKGm.

NOTE: SIVT AWS, Azure components will still be supporting the older version of Tanzu Kubernetes Grid [support matrix](index.md/##Service Installer for VMware Tanzu Support Matrix).
      Tanzu Kubernetes Grid 2.1.0 support for these components will be added in future releases.

## Resolved Issues

- Post validation of 'AVI controller', next button user action is not proceeding further
- Harbor version installed on shared-services cluster is not the latest version
- Ping check for NSX-T workload segment gateway fails

## Known Issues 
- There is a known product issue in TMC/TKG due to which when TMC is enabled, Prometheus, Grafana and Harbor deployments are having issues. 
- FIPS/STIG compliant deployment for Tanzu Kubernetes Grid 2.1.0 is *not supported* in SIVT.
- The size of SIVT OVA with Harbor and Tanzu Kubernetes Grid dependency is increased to 25 GB as downloading the Kube version specific Tanzu Kubernetes Grid binary download is not supported in 'tanzu isolated-cluster plugin'.
- Service Installer for VMware Tanzu is unable to fetch cluster images from the content library. This happens due to a known issue with Tanzu on vSphere. The subscribed content library needs to be synced manually sometimes to update with the images.
- Tanzu Mission Control integration of management and workload clusters fails for AWS non air-gapped compliant deployment, due to a known issue in the Tanzu Mission Control API.
- Prometheus deployment fails if SaaS is activated in non-airgapped AWS deployment.
- VCD API call takes time depending on environment configuration , re-trigger the SIVT command after 1 min delay  
- Creating ALB Service Engine Group assignment to Edge Gateway fails intermittently. [Terraform provider issue](https://github.com/vmware/terraform-provider-vcd/issues/923)
- Activating AVI L7 on vSphere with NSXT environments over NodePortLocal mode fails to bringup AKO pods.
- SIVT supposed to download Ubuntu-2004-kube-v1.22.9.ova version, right now it is downloading Ubuntu-2004-kube-v1.23.8.ova version.
  Note: If user need specific version of Ubuntu + K8S ova version, download the same from marketplace and upload it to the K8S catalog.
- Harbor deployment fails both with and without SaaS in multi workload cluster configurations in non-airgapped AWS deployment.
- In case you are using proxy with self-signed or custom CA certificate, SIVT fails to pull the `kind` image while deploying Tanzu Kubernetes Grid management cluster in a vSphere VDS environment.</br>
  **Resolution:** Before initiating the deployment with SIVT, perform the following steps:

  1. Import the proxy certificate into the SIVT VM.
  1. Run the following commands:
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
