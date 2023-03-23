# Service Installer for VMware Tanzu 2.1.1 Release Notes

## What's New

- Service Installer for VMware Tanzu (SIVT)  ova now supports Tanzu Kubernetes Grid (TKG) 2.1.1
- SIVT provides support for vSphere 8.0 for Tanzu Kubernetes Grid deployments and vSphere with Tanzu deployments.
- SIVT supports NSX Advanced Load Balancer 22.1.2 for both Tanzu Kubernetes Grid and vSphere with Tanzu deployments.
- SIVT now supports TKG 2.1.0 for non-compliant deployment on AWS and TKG 1.6.1 (FIPS) for compliant deployment.
- Tekton now supports Day 0 operations on vSphere with NSX-T and vDS environments (TKG-2.1.0).
- Enable L7 Ingress on AVI controller is now modularized and can be controller at cluster level.
- User can now select Manual IP or IP Pool as mode of configuration for CSE vApp deployment (VCD).
- User can check STATUS of current deployment using `--status`.
- Updated the names of Service Engines for Management and Workload cluster to `Mgmt-se` and `Workload-se` respectively.
- SIVT now runs the complete set of pre-checks and provides all the errors encountered together at the end.

NOTE: SIVT Azure component will still be supporting the older version of Tanzu Kubernetes Grid [support matrix](index.md/##Service Installer for VMware Tanzu Support Matrix).

## Resolved Issues

- Fixed file formatting for AKO file for workload cluster in case of Tanzu Kubernetes Grid deployments.
- Automation fails to obtain right IP if multiple AVI VMs ending with same FQDN are found in cluster.
- Failed to validate Content Library UUID - Tanzu Kubernetes Grid Service.
- Added check for validating Kube Version for Shared and Workload clusters.
- SIVT creates the NSX-T cloud with incorrect VC info when we have more than 1 vcenter configured in NSX-T Manager
- The UI shows red sign on selecting an already present namespace for vSphere with Tanzu.
- Failed to config tkgs “Authentication credentials not provided", fixed to enable AXA.
- Tanzu Mission Control integration of management and workload clusters fails for AWS non air-gapped compliant deployment, due to a known issue in the Tanzu Mission Control API.
- Verify checksum of existing files instead checking presence of those file using exists() method.
- Tanzu Kubernetes Grid deployment with NSX-T networking fails with `Failed to configure vcf list index out of range`.

## Known Issues
- There is a known product issue with Harbor(2.6.x) when deployed on a Workload cluster for vSphere with Tanzu deployments.
- There is a known TMC issue for TKGs extension deployment, Kapp running on the cluster doesn't support Tanzu packaging.
- FIPS/STIG compliant deployment for Tanzu Kubernetes Grid 2.1.1 is *not supported* in SIVT.
- The size of SIVT OVA with Harbor and Tanzu Kubernetes Grid dependency is increased to 25 GB as downloading the Kube version specific Tanzu Kubernetes Grid binary download is not supported in 'tanzu isolated-cluster plugin'.
- Service Installer for VMware Tanzu is unable to fetch cluster images from the content library. This happens due to a known issue with Tanzu on vSphere. The subscribed content library needs to be synced manually sometimes to update with the images.
- VCD API call takes time depending on environment configuration , re-trigger the SIVT command after 1 min delay  
- Creating ALB Service Engine Group assignment to Edge Gateway fails intermittently. [Terraform provider issue](https://github.com/vmware/terraform-provider-vcd/issues/923)
- Activating AVI L7 on vSphere with NSXT environments over NodePortLocal mode fails to bringup AKO pods.
- AKO POD deployment fails if cluster name has more than 25 characters, prechecks for this will be added in upcoming release.
- SIVT supposed to download Ubuntu-2004-kube-v1.22.9.ova version, right now it is downloading Ubuntu-2004-kube-v1.23.8.ova version.
  Note: If user need specific version of Ubuntu + K8S ova version, download the same from marketplace and upload it to the K8S catalog.
- There is a known issue with Harbor(2.6.1) extensions deployment on Tanzu Kubernetes Grid AWS compliant deployment.

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
  2. Go to `/opt/vmware/arcas/tools/harbor`
  3. Run the following commands:
      ```
      docker-compose stop
      find common/ -type f -exec chmod 0755 \{\} \;
      docker-compose up -d
      ```

## Download

- Download the Service Installer OVA and AWS solutions from [VMware Marketplace: Service Installer for VMware Tanzu](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true).
