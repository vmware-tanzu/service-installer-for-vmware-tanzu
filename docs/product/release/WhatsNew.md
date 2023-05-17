# Service Installer for VMware Tanzu 2.2.0 Release Notes

## What's New

- Service Installer for VMware Tanzu (SIVT) ova now supports Tanzu Kubernetes Grid (TKG) 2.2.0
- SIVT now supports Essentials along with Enterprise license for NSX ALB for TKGm and TKGs VDS platforms
- Code refactored to remove TMC CLI for TMC related operations, SIVT now uses TMC APIs
  - TMC API code changes are ported to VMC along with other code enhancements
  - TMC API: Worker node count passed as control plane node count to API payload for shared and workload cluster
- SIVT now supports version control for deployment JSON file generated from User Interface.
- SIVT now supports TKG 2.1.1 for non-compliant deployment on AWS and TKG 1.6.1 (FIPS) for compliant deployment

NOTE: SIVT Azure will be supporting the older version of Tanzu Kubernetes Grid [support matrix](index.md/##Service Installer for VMware Tanzu Support Matrix).

## Resolved Issues
- Backend Check for Kubernetes OVA version of Shared and Workload clusters in JSON files is missing
- Fluent-bit extension failing for TKGs proxy
- UI: VDS Configure options has a bug on Custom repo page leading to AVI not getting loaded.
- Inconsistent naming of networks / port groups in docs
- Activating AVI L7 on vSphere with NSXT environments over NodePortLocal mode fails to bring-up AKO pods.
- Implement pre-check to handle 'AKO POD deployment failure if cluster name has more than 25 characters'

## Known Issues
- TO and TSM integration fails with the latest version of kubernetes 1.25.x for TKGm 2.2.0 deployment
- There is a known product issue with Harbor(2.6.x) when deployed on a Workload cluster for vSphere with Tanzu deployments.
- There is a known issue for fluent-bit extensions deployment when grafana and prometheus is not selected alongside fluent-bit for vsphere TKG multi cloud.
- There is a known TMC issue for TKGs extension deployment, Kapp running on the cluster doesn't support Tanzu packaging.
- FIPS/STIG compliant deployment for Tanzu Kubernetes Grid 2.1.1 onwards is *not supported* in SIVT.
- The size of SIVT OVA with Harbor and Tanzu Kubernetes Grid dependency is increased to 25 GB as downloading the Kube version specific Tanzu Kubernetes Grid binary download is not supported in 'tanzu isolated-cluster plugin'.
- Service Installer for VMware Tanzu is unable to fetch cluster images from the content library. This happens due to a known issue with Tanzu on vSphere. The subscribed content library needs to be synced manually sometimes to update with the images.
- VCD API call takes time depending on environment configuration , re-trigger the SIVT command after 1 min delay
- Creating ALB Service Engine Group assignment to Edge Gateway fails intermittently. [Terraform provider issue](https://github.com/vmware/terraform-provider-vcd/issues/923)
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
