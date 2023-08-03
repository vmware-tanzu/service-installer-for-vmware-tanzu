# Service Installer for VMware Tanzu 2.3.0 Release Notes

## What's New

- Service Installer for VMware Tanzu (SIVT) now supports v1alpha3 and v1beta1 APIs on vSphere 8.0 for TKG Service deployments.
- SIVT ova now supports Tanzu Kubernetes Grid (TKG) 2.3.0 Halifax release.
- SIVT now officially supports 3 network topology as per the Reference Architecture.
- SIVT now supports Selective Cleanup along with the end-to-end cleanup, which lets users selectively clear parts of the deployments.
- SIVT now supports TKG 2.1.1 for non-compliant deployment on AWS and TKG 1.6.1 (FIPS) for compliant deployment

NOTE: SIVT Azure will be supporting the older version of Tanzu Kubernetes Grid [support matrix](index.md/##Service Installer for VMware Tanzu Support Matrix).

## Resolved Issues
- SIVT does not set the default datastore for the second workload Service Engine group, instead sets this to Any.
- The configuration yaml files for Workload clusters in vSphere with Tanzu deployments are not located at path: `/opt/vmware/arcas/tanzu-clusters/<clustername>/tkgs_workload.yaml`.
- SIVT uses the AVI controller sizes which is not as per the NSX ALB official documentation.
- An alert has been added to update license after using the NSX ALB Enterprise License for deployments in SIVT.
- Improved SIVT logs to track the API response time from NSX ALB while polling for NSX ALB status.

## Known Issues
- Integration of TMC with vSphere 8.0 is not supported with SIVT due to limited support for cluster classes.
- Deletion of workload cluster takes around ~40 minutes if the extensions are already cleaned up.
- Addition of control plane volume for v1beta1 clusters on vSphere with Tanzu is not supported.
- TSM integration fails with the latest version of kubernetes 1.26.x for TKGm 2.3.0 deployment.
- `ERROR: Workload cluster not in Running state`, while deploying extensions for v1beta1 clusters on vSphere with Tanzu appears due to limitation in checking live cluster status via `kubectl get clusters`. You must wait till the cluster is in Running state and then proceed to next steps.
- Deployment of extensions fails for v1beta1 clusters on vSphere with Tanzu, because of internal use of `tanzu cluster list`, which replaces BOM files with TKG 1.6.1. For more information about deploying extensions, see [this](https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/2.1/using-tkg-21/workload-packages-ref.html).
- FIPS/STIG compliant deployment for Tanzu Kubernetes Grid 2.1.1 onwards is *not supported* in SIVT.
- The size of SIVT OVA with Harbor and Tanzu Kubernetes Grid dependency is increased to 25 GB as downloading the Kube version specific Tanzu Kubernetes Grid binary download is not supported in 'tanzu isolated-cluster plugin'.
- Service Installer for VMware Tanzu is unable to fetch cluster images from the content library. This happens due to a known issue with Tanzu on vSphere. The subscribed content library needs to be synced manually sometimes to update with the images.
- Creating ALB Service Engine Group assignment to Edge Gateway fails intermittently. [Terraform provider issue](https://github.com/vmware/terraform-provider-vcd/issues/923)
- There is a known issue with Harbor(2.6.1) extensions deployment on Tanzu Kubernetes Grid AWS compliant deployment.

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
  2. Go to `/opt/vmware/arcas/tools/harbor`
  3. Run the following commands:
      ```
      docker-compose stop
      find common/ -type f -exec chmod 0755 \{\} \;
      docker-compose up -d
      ```

## Download

- Download the Service Installer OVA and AWS solutions from [VMware Marketplace: Service Installer for VMware Tanzu](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true).
