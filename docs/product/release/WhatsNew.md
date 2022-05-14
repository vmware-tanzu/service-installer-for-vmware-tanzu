## What's New

- Support for TKG 1.5.3, including Day 0 support in Tekton-based pipelines
- Cleanup feature - Ability to cleanup the steps performed by SIVT and start from scratch
- Support for below extensions
    - Fluent Bit with Kafka, HTTP and Syslog endpoints
    - Pinniped with OIDC and LDAP identity management
    - Velero
- Below Features added in SIVT user interface to enhance prechecks
    - Name resolution check for NSX ALB Load balancer
    - Ping check for vSphere with Tanzu management cluster IPs and NSX Load Balancer IPs
- Deployments on internet restricted environment is now supported with SIVT
- Additional improvements based on feedback from TKGm TSLs 
    - Support for single network topology
    - Support for minimum user privilege


## Service Installer for VMware Tanzu Deployment JSON files 

**Note: New fields corresponding to new extensions support are added to JSON files in this release. Please refer sample JSON files or generate file from SIVT user interface to update your JSON files**

All these JSON files for different platforms are available at,
- In Documentation
    - [VMware Cloud on AWS - VMC](./VMware%20Cloud%20on%20AWS%20-%20VMC/TKOonVMConAWS.md#sample-input-file) 
    - [vSphere - Backed by NSX-T](./vSphere%20-%20Backed%20by%20NSX-T/tkoVsphereNSXT.md#sample-input-file) 
    - [vSphere - Backed by VDS-TKGm](./vSphere%20-%20Backed%20by%20VDS/TKGm/TKOonVsphereVDStkg.md#sample-input-file) 
    - [vSphere - Backed by VDS-TKGs](./vSphere%20-%20Backed%20by%20VDS/TKGs/TKOonVsphereVDStkgs.md#sample-input-file)

## Fixed Issues
- [MAPBUA-570](https://jira.eng.vmware.com/browse/MAPBUA-570) TKG_TSL_Feedback: Resource pool creation fails if resource pool with same name exists in parent resuorce pool
- [MAPBUA-569](https://jira.eng.vmware.com/browse/MAPBUA-569)	TKG_TSL_Feedback: TKGs issue while listing clusters for same cluster names across different datacenter
- [MAPBUA-597](https://jira.eng.vmware.com/browse/MAPBUA-597)	TKG_TSL_Feedback: Issue with Signed certificates for NSX ALB in TKGS deployment
- [MAPBUA-606](https://jira.eng.vmware.com/browse/MAPBUA-606)	TKG_TSL_Feedback: Configure vSphere kubectl plugin before fetching tkr version
- [MAPBUA-611](https://jira.eng.vmware.com/browse/MAPBUA-611)	TKG_TSL_feedback: UI tooltip for workload cluster points to wrong pod and service CIDR
- [MAPBUA-618](https://jira.eng.vmware.com/browse/MAPBUA-618)	TKG_TSL_Feedback: Add System message of day in SIVT VM
- [MAPBUA-627](https://jira.eng.vmware.com/browse/MAPBUA-627)	TKG_TSL_Feedback: Space in Datacenter and cluster name govc command id failing to create resources
- [MAPBUA-667](https://jira.eng.vmware.com/browse/MAPBUA-667)	TKG_TLS_feedback: Folders are being listed along with clusters in UI cluster dropdown
- [MAPBUA-736](https://jira.eng.vmware.com/browse/MAPBUA-736)	TKG_TLS_Feedback: Comma separated NTP values validation fails
- [MAPBUA-690](https://jira.eng.vmware.com/browse/MAPBUA-690)	TKG_TSL_Feedback: Include Network troubleshooting binaries in SIVT OVA

## Important Links
- Download latest Arcas OVA from [here](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true)

## Known Issues
- [TKG-11079](https://jira.eng.vmware.com/browse/TKG-11079) - Contour package installation failure in workload cluster
- [GCM-6212](https://jira.eng.vmware.com/browse/GCM-6212) - Workload clusters integration with TSM is failing for vSphere with Tanzu
- Deployment on Proxy environment is not supported. This will be addressed in next release.
- Complex passwords for proxy server won't work. Passwords can contain only alphanumeric characters.
