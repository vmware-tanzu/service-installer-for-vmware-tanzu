# Service Installer for VMware Tanzu 1.1 Release Notes

## <a id="new"></a> What's New

- Automates the deployment and configuration of NSX Advanced Load Balancer in a Tanzu Kubernetes Grid Service deployment on vSphere with NSX Advanced Load Balancer.
- Supports Tanzu Kubernetes Grid 1.5.1.
- Integrates the following Tanzu SaaS components on Tanzu Kubernetes Grid Service:

    - Tanzu Mission Control
    - Tanzu Observability
    - Tanzu Service Manager
- Integrates the following extensions on Tanzu Kubernetes Grid Service:

    - Prometheus
    - Grafana
- Ability to upload an input JSON file for Tanzu Kubernetes Grid Service.Adds verbose option to SIVT CLI.
- Ability to Download Service Installer for VMware Tanzu log bundle.
- Uses Tanzu Mission Control CLI to deploy shared service and workload clusters on Tanzu for Kubernetes Grid 1.5.1.
- Attach Tanzu Kubernetes Grid 1.5.1 management Cluster to Tanzu Mission Control.
- Custom sizing of CPU and memory storage for all clusters.
- Supports Avi controller 20.1.7.Supports Avi high availability.
- Reduces Avi controller footprint.
- Supports user owned certificate and default generation of certificate for Avi controller.
- Separates namespace and cluster creation for Tanzu Kubernetes Grid Service.
- Supports NTP for workload networks.
- Supports multiple workload networks.
- Ability to change the Service Installer password at the time of deployment.
- Uses standard input file naming convention.
- Supports Tekton pipeline for Tanzu Kubernetes Grid 1.4.x.

  - Reference Architecture based Day 0 deployment of Tanzu Kubernetes Grid on vSphere.
  - Day 2 operation of upgrading Tanzu Kubernetes Grid clusters from 1.4.0 to 1.4.1.

## <a id="json-files"></a> Service Installer for VMware Tanzu Deployment JSON files
This release introduces changes to the deployment JSON files that are generated from the Service Installer user interface.

**Note: If you are directly using the old JSON files, it will not work.**

The JSON files for each platform are available at,

- [VMware Cloud on AWS](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/1.1/service-installer/GUID-VMware%20Cloud%20on%20AWS%20-%20VMC-TKOonVMConAWS.html#sample-input-file-7)
- [vSphere - Backed by NSX-T](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/1.1/service-installer/GUID-vSphere%20-%20Backed%20by%20NSX-T-tkoVsphereNSXT.html#sample-input-file-4)
- [vSphere - Backed by VDS and Tanzu Kubernetes Grid](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/1.1/service-installer/GUID-vSphere%20-%20Backed%20by%20VDS-TKGm-TKOonVsphereVDStkg.html#sample-input-file-5)
- [vSphere - Backed by VDS and Tanzu Kubernetes Grid Service](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/1.1/service-installer/GUID-vSphere%20-%20Backed%20by%20VDS-TKGs-TKOonVsphereVDStkgs.html#sample-input-file-4)

## <a id="resolved-issues"></a> Resolved Issues
- <a id="MAPBUA-355"></a> Update documentation for Harbor setup to explain how to get a certificate ahead of time.
- <a id="MAPBUA-356"></a>	Single network for all the segments.
- <a id="MAPBUA-357"></a>	Good to have a production example network and a developer example network.
- <a id="MAPBUA-358"></a>	Annotate networking diagram with sample values for CIDR ranges.
- <a id="MAPBUA-359"></a>	Log location information was missing. Documentation needs to clearly have log location details.
- <a id="MAPBUA-360"></a> Update the documentation to clarify 'Sizing for cluster'.
- <a id="MAPBUA-361"></a> Cluster selection is too restrictive for Tanzu Mission Control/Tanzu Observability. Need to have the option to select a smaller size. Need horizontal scaling instead of vertical scaling.
- <a id="MAPBUA-362"></a> The Service Installer OVA should come bundled with 'kind CLI, k9s, k alias, kubectx, kube-ps1, fzf'. These are great aids when working on console.
- <a id="MAPBUA-364"></a> Good to resize the Avi controller to the "lightweight" config. 4 vcpu, 12 GB ram.
- <a id="MAPBUA-366"></a> Logging improvements.

## <a id="known-issues"></a> Known Issues
- Bring your own certificate feature for AVI controller does not work as expected.
- Tanzu Service Mesh is not supported on 1.5.1. Integrating workload clusters in VMware Cloud environment with Tanzu Service Mesh fails.
- Complex passwords for proxy server won't work. Passwords can contain only alphanumeric characters.
  This is due to bug in Tanzu Kubernetes Grid.
- Custom image repository is not supported in Tanzu Kubernetes Grid 1.5.1.
- Resource pool creation fails if a resource pool with same name exists in the parent resource pool.
- Tanzu Kubernetes Grid Service issue while listing clusters for same cluster names across different datacenter.

## <a id="download"></a> Download
- Download the latest Service Installer OVA from [VMware Marketplace: Service Installer for VMware Tanzu](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true).
