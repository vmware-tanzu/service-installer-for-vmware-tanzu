# Service Installer for VMware Tanzu 1.1

Service Installer for VMware Tanzu automates the deployment of the reference designs for Tanzu for Kubernetes Operations on the following platforms:

- Tanzu Kubernetes Grid on VMware Cloud
- Tanzu Kubernetes Grid on vSphere with NSX-T
- Tanzu Kubernetes Grid on vSphere running Virtual Distributed Switch (VDS)
- Tanzu Kubernetes Grid Service on vSphere running Virtual Distributed Switch (VDS)

Service Installer simplifies the deployment of a Kubernetes environment. It uses best practices for deploying and configuring the required Tanzu for Kubernetes Operations components, such as:
- Tanzu Kubernetes Grid
- NSX Advanced Load Balancer
- Shared services, such as Contour, Harbor, FluentBit, Prometheus, Grafana
- Integration with Tanzu Mission Controller

## Download Service Installer for VMware Tanzu
Download the latest Service Installer for VMware Tanzu OVA(v1.1-1.5.1) [here](https://marketplace.cloud.vmware.com/services/details/service-installer-for-vmware-tanzu-1?slug=true)

## Deploy Service Installer for VMware Tanzu
1. Download the Service Installer OVA from **VMware Marketplace**.
2. Deploy the Service Installer OVA on vCenter server via the **Deploy OVF Template** option and provide required computer resources and storage details.
3. Select **Appliance network as Management network** and specify NTP server as well as root password for the VM.

   After the system configuration is completed, the OVA deployment begins.

4. After the deployment is completed, power on the Service Installer for the VMware Tanzu bootstrap VM.

   You can access the Service Installer UI at `http://<Service-Installer-VM-IP>:8888/`.

   To access the Service Installer CLI, log in over SSH. Enter `ssh root@<Service-Installer-VM-IP>`.

## Documentation
<!-- - What's new in this release: [What's New](./WhatsNew.md)./-->
Instructions to run the Service Installer for VMware Tanzu for Kubernetes Operations:

- [Deploying VMware Tanzu for Kubernetes Operations on VMware Cloud on AWS Using Service Installer for VMware Tanzu](./VMware%20Cloud%20on%20AWS%20-%20VMC/TKOonVMConAWS.md).
- [Deploying VMware Tanzu for Kubernetes Operations on vSphere with NSX-T Using Service Installer for VMware Tanzu](./vSphere%20-%20Backed%20by%20NSX-T/tkoVsphereNSXT.md).
- [Deploying VMware Tanzu for Kubernetes Operations on vSphere with vSphere Distributed Switch Using Service Installer for VMware Tanzu](./vSphere%20-%20Backed%20by%20VDS/TKGm/TKOonVsphereVDStkg.md).
- [Deploying VMware Tanzu for Kubernetes Operations on vSphere with Tanzu and vSphere Distributed Switch Using Service Installer for VMware Tanzu](./vSphere%20-%20Backed%20by%20VDS/TKGs/TKOonVsphereVDStkgs.md).
