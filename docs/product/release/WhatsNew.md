## What's New

- Tanzu Kubernetes Grid Service deployment on vSphere with NSX Advanced Load Balancer. Currently the following tasks are automated:
    - Deploy and configure NSX ALB
- Tanzu 1.5.1 support
- Integration of SaaS service on TKGS
    - Tanzu Mission Control (TMC)
    - Tanzu Observability (TO)
    - Tanzu Service Manager (TSM)
- Integration of extensions on TKGS
    - Prometheus
    - Grafana
- Ability to upload an input JSON file for TKGs
- Added verbose option to SIVT CLI
- Service Installer for VMware Tanzu log bundle download mechanism
- Use of TMC CLI to deploy shared service and workload clusters on Tanzu 1.5.1
- Attach TMC to management cluster for Tanzu 1.5.1
- Custom sizing of CPU and memory storage sizing for all clusters
- Support for 20.1.7 Avi controller version
- Support for Avi high availability
- Reducing Avi controller foot print
- Support for user own certificate for Avi controller along with default generation of certificate
- Namespace and cluster creation for TKGS are separated
- Support for NTP for workload networks
- Support for multiple workload networks
- Added feature to change Arcas password at the time of deployment
- Standard input file naming convention
- Support for Tekton pipeline TKGm 1.4.x
    - Reference Architecture based Day0 deployment of TKGm on vSphere
    - Day2 operation of upgrading TKGm clusters from 1.4.0 to 1.4.1

## Service Installer for VMware Tanzu Deployment JSON files 
In this release, we have made changes to the deployment JSON files which get generated from the user interface of Service Installer for VMware Tanzu. 

**Note: If you are directly using the old JSON files, it will not work.**

All these JSON files for different platforms are available at,
- In Documentation
    - [VMware Cloud on AWS - VMC](./VMware%20Cloud%20on%20AWS%20-%20VMC/TKOonVMConAWS.md#sample-input-file) 
    - [vSphere - Backed by NSX-T](./vSphere%20-%20Backed%20by%20NSX-T/tkoVsphereNSXT.md#sample-input-file) 
    - [vSphere - Backed by VDS-TKGm](./vSphere%20-%20Backed%20by%20VDS/TKGm/TKOonVsphereVDStkg.md#sample-input-file) 
    - [vSphere - Backed by VDS-TKGs](./vSphere%20-%20Backed%20by%20VDS/TKGs/TKOonVsphereVDStkgs.md#sample-input-file)

## Fixed Issues
- [MAPBUA-355](https://jira.eng.vmware.com/browse/MAPBUA-355) TKG_TSL_Feedback: Update documentation for Harbor setup to explain how to get a certificate ahead of time.
- [MAPBUA-356](https://jira.eng.vmware.com/browse/MAPBUA-356)	TKG_TSL_Feedback: Single network for all the segments
- [MAPBUA-357](https://jira.eng.vmware.com/browse/MAPBUA-357)	TKG_TSL_Feedback: Good to have Prod example network and Developer Example network
- [MAPBUA-358](https://jira.eng.vmware.com/browse/MAPBUA-358)	TKG_TSL_Feedback: Annotate Networking diagram with sample values for CIDR ranges
- [MAPBUA-359](https://jira.eng.vmware.com/browse/MAPBUA-359)	TKG_TSL_feedback: Log location information was missing. Documentation needs to clearly have log location details
- [MAPBUA-360](https://jira.eng.vmware.com/browse/MAPBUA-360)	TKG_TSL_Feedback: Update the documentation to clarify 'Sizing for cluster'.
- [MAPBUA-361](https://jira.eng.vmware.com/browse/MAPBUA-361)	TKG_TSL_Feedback: Cluster selection is too restrictive for TMC/TO. Need to have the option to select a smaller size. Need horizontal scaling instead of vertical scaling.
- [MAPBUA-362](https://jira.eng.vmware.com/browse/MAPBUA-362)	TKG_TLS_feedback: ARCAS OVA should come bundled with 'kind CLI, k9s, k alias, kubectx, kube-ps1, fzf. These are great aids when working on console'
- [MAPBUA-364](https://jira.eng.vmware.com/browse/MAPBUA-364)	TKG_TLS_Feedback: Good to resize the Avi controller to the "lightweight" config. 4 vcpu, 12 GB ram
- [MAPBUA-366](https://jira.eng.vmware.com/browse/MAPBUA-366)	TKG_TSL_Feedback: Logging improvements

## Important Links
- Download latest Arcas OVA from [here](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true)

## Known Issues
- Bring your own certificate feature for AVI controller is not working as expected. We will address this in patch release.
- TSM is officially not supported on 1.5.1. Integrating workload clusters in VMware Cloud environment with TSM fails.
- Complex passwords for proxy server won't work. Passwords can contain only alphanumeric characters.
- This is due to bug in TKG product. Custom Image repository is not supported in TKG 1.5.1
- Resource pool creation fails if resource pool with same name exists in parent resporce pool
- TKGs issue while listing clusters for same cluster names across different datacenter
