# Service Installer for VMware Tanzu 1.4

Service Installer for VMware Tanzu automates the deployment of the reference designs for Tanzu for Kubernetes Operations on the following platforms:

- Tanzu Kubernetes Grid on VMware Cloud
- Tanzu Kubernetes Grid on vSphere with NSX-T
- Tanzu Kubernetes Grid on vSphere running vSphere Distributed Switch (VDS)
- vSphere with Tanzu running vSphere Distributed Switch (VDS)
- Tanzu Kubernetes Grid on AWS (air-gapped and Internet-connected)
- Tanzu Kubernetes Grid on Azure

Service Installer simplifies the deployment of a Kubernetes environment. It uses best practices for deploying and configuring the required Tanzu for Kubernetes Operations components, such as:

- Tanzu Kubernetes Grid
- NSX Advanced Load Balancer
- Shared services such as Contour, Harbor, Fluent Bit, Prometheus, Grafana
- Integration with Tanzu Mission Control, Tanzu Observability, and Tanzu Service Mesh

## Release Notes
See the [Release Notes](WhatsNew.md) for a summary of what's new in this release.

## Download Service Installer for VMware Tanzu
For the download location, see [Release Notes](WhatsNew.md).

## Deploy Service Installer for VMware Tanzu

1. Download the Service Installer OVA.
1. Log in to vSphere Client. 
1. Start the **Deploy OVF Template** wizard and provide the required details.
   - Select the **Local file** option to upload the Service Installer OVA. 
   - Provide the required computer resources and storage details.
   - Under **Select networks**, for **Appliance Network**, select the management port group.
   - Specify the NTP server and the root password for the VM. 

   For more information about deploying an OVA, see [Deploy an OVF or OVA Template](https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.vsphere.vm_admin.doc/GUID-17BEDA21-43F6-41F4-8FB2-E01D275FE9B4.html).
   
   After the system configuration completes, the OVA deployment begins.

1. After the deployment is completed, power on the Service Installer for the VMware Tanzu bootstrap VM.

   You can access the Service Installer UI at `http://<Service-Installer-VM-IP>:8888/`.

   To access the Service Installer CLI, log in over SSH. Enter `ssh root@<Service-Installer-VM-IP>`.

## Documentation
<!-- - What's new in this release: [What's New](./WhatsNew.md)./-->
Instructions to run the Service Installer for VMware Tanzu for Kubernetes Operations:

- [Deploying VMware Tanzu for Kubernetes Operations on VMware Cloud on AWS Using Service Installer for VMware Tanzu](./VMware%20Cloud%20on%20AWS%20-%20VMC/TKOonVMConAWS.md).
- [Deploying VMware Tanzu for Kubernetes Operations on vSphere with NSX-T Using Service Installer for VMware Tanzu](./vSphere%20-%20Backed%20by%20NSX-T/tkoVsphereNSXT.md).
- [Deploying VMware Tanzu for Kubernetes Operations on vSphere with vSphere Distributed Switch Using Service Installer for VMware Tanzu](./vSphere%20-%20Backed%20by%20VDS/TKGm/TKOonVsphereVDStkg.md).
- [Deploying VMware Tanzu for Kubernetes Operations on vSphere with Tanzu and vSphere Distributed Switch Using Service Installer for VMware Tanzu](./vSphere%20-%20Backed%20by%20VDS/TKGs/TKOonVsphereVDStkgs.md).
