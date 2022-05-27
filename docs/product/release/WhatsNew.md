# Service Installer for VMware Tanzu 1.2 Release Notes

## <a id="new"></a> What's New

- Support for Tanzu Kubernetes Grid 1.5.3 and Day 0 support in Tekton-based pipelines.
- Ability to cleanup the steps performed by Service Installer for VMware Tanzu and start from scratch.
- Support for the following extensions:
    - Fluent Bit with Kafka, HTTP ,and Syslog endpoints.
    - Pinniped with OIDC and LDAP identity management.
    - Velero.
- The Service Installer user interface includes the following pre-checks:
    - Name resolution check for NSX Advanced Load Balancer.
    - Ping check for vSphere with Tanzu management cluster IPs and NSX Load Balancer IPs.
- Support for deployments in an Internet-restricted environment.
- Support for single network topology.
- Support for minimum user privilege.

## Service Installer for VMware Tanzu Deployment JSON Files
This release adds new fields to the JSON files. The new fields correspond to new extensions that are supported in this release.

To update your JSON files, see the sample JSON files included with this release or generate a new file from Service Installer user interface.

The following separate JSON files for each platform are available:

  - [VMware Cloud on AWS](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/1.2/service-installer/GUID-VMware%20Cloud%20on%20AWS%20-%20VMC-TKOonVMConAWS.html#sample-input-file-7)
  - [vSphere - Backed by NSX-T](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/1.2/service-installer/GUID-vSphere%20-%20Backed%20by%20NSX-T-tkoVsphereNSXT.html#sample-input-file-4)
  - [vSphere - Backed by VDS and Tanzu Kubernetes Grid](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/1.1/service-installer/GUID-vSphere%20-%20Backed%20by%20VDS-TKGm-TKOonVsphereVDStkg.html#sample-input-file-5)
  - [vSphere - Backed by VDS and Tanzu Kubernetes Grid Service](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/1.1/service-installer/GUID-vSphere%20-%20Backed%20by%20VDS-TKGs-TKOonVsphereVDStkgs.html#sample-input-file-4)

## <a id="resolved-issues"></a> Resolved Issues
- <a id="MAPBUA-570"> </a> Resource pool creation fails if resource pool with same name exists in parent resource pool.
- <a id="MAPBUA-569"> </a> Tanzu Kubernetes Grid Service issue while listing clusters for same cluster names across different datacenter.
- <a id="MAPBUA-597"> </a> Issue with Signed certificates for NSX Advanced Load Balancer in Tanzu Kubernetes Grid Service deployment.
- <a id="MAPBUA-606"> </a> Configure vSphere `kubectl` plugin before fetching TKr version.
- <a id="MAPBUA-611"> </a> UI tooltip for workload cluster points to wrong pod and service CIDR.
- <a id="MAPBUA-618"> </a> Add System message of day in Service Installer for VMware Tanzu VM.
- <a id="MAPBUA-627"> </a> Space in datacenter and cluster name govc command id failing to create resources.
- <a id="MAPBUA-667"> </a> Folders are listed along with clusters in UI cluster dropdown.
- <a id="MAPBUA-736"> </a> Comma separated NTP values validation fails.
- <a id="MAPBUA-690"> </a> Include Network troubleshooting binaries in Service Installer for VMware Tanzu OVA.

## Known Issues
- <a id="TKG-11079"> </a> Contour package installation failure in workload cluster.
- <a id="GCM-6212"> </a> Workload clusters integration with TSM is failing for vSphere with Tanzu
- Deployment on Proxy environment is not supported. This will be addressed in next release.
- Complex passwords for proxy server won't work. Passwords can contain only alphanumeric characters.

## Download
- Download the latest Service Installer OVA from [VMware Marketplace: Service Installer for VMware Tanzu](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true).
