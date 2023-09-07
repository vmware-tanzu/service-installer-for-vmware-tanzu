# Service Installer for VMware Tanzu 2.3.0

Service Installer for VMware Tanzu (informally known as SIVT) automates the deployment of the reference designs for Tanzu on the following platforms:

- Tanzu Kubernetes Grid on vSphere backed by VDS (Internet-connected, air-gapped, proxy-based, and no-orchestration)
- vSphere with Tanzu backed by VDS (Internet-connected and proxy-based)
- Tanzu Kubernetes Grid on vSphere backed by NSX-T (Internet-connected, air-gapped, and proxy-based)
- Tanzu Kubernetes Grid on VMware Cloud on AWS (VMC)
- Tanzu Kubernetes Grid on AWS (Internet-connected, air-gapped)
- Tanzu Kubernetes Grid on Azure
- Tanzu Kubernetes Grid on VMware Cloud Director (VCD) (Internet-connected, Greenfield, Brownfield)

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
2. Log in to vSphere Client.
3. Start the **Deploy OVF Template** wizard and provide the required details.
   - Select the **Local file** option to upload the Service Installer OVA.
   - Provide the required computer resources and storage details.
   - Under **Select networks**, for **Appliance Network**, select the management port group.
   - Specify the NTP server and the root password for the VM.

   For more information about deploying an OVA, see [Deploy an OVF or OVA Template](https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.vsphere.vm_admin.doc/GUID-17BEDA21-43F6-41F4-8FB2-E01D275FE9B4.html).

   After the system configuration completes, the OVA deployment begins.

4. After the deployment is completed, power on the Service Installer for the VMware Tanzu bootstrap VM.

   You can access the Service Installer UI at `http://<Service-Installer-VM-IP>:8888/`.

   To access the Service Installer CLI, log in over SSH. Enter `ssh root@<Service-Installer-VM-IP>`.


## Service Installer for VMware Tanzu Support Matrix


### Tanzu Kubernetes Grid Support Matrix

| Platform     | vSphere Compliant | vSphere Non-Compliant                                         | VMC on AWS                                                   | AWS Compliant                                  | AWS Non-Compliant            | Azure                        |
|--------------|-------------------|---------------------------------------------------------------|--------------------------------------------------------------|------------------------------------------------|------------------------------|------------------------------|
| Internet     | NA                | TKG 2.3.0, <br> Ubuntu 20.04,<br>Photon 3,<br> NSX ALB 22.1.2 | TKG 2.3.0, <br> Ubuntu 20.04,<br>Photon 3,<br>NSX ALB 22.1.2 | TKG 1.6.1, <br>Ubuntu 18.04                    | TKG 2.1.1, <br> Ubuntu 18.04 | TKG 1.6.0, <br> Ubuntu 20.04 |
| Air-gapped   | NA                | TKG 2.3.0, <br>Ubuntu 20.04,<br> Photon 3,<br> NSX ALB 22.1.2 | NA                                                           | TKG 1.6.1,<br> Ubuntu 18.04,<br>Amazon Linux 2 | NA                           | TKG 1.6.0, <br> Ubuntu 20.04 |
| Proxy        | NA                | TKG 2.3.0,<br> Ubuntu 20.04,<br> Photon 3,<br> NSX ALB 22.1.2 | NA                                                           | NA                                             | NA                           | TKG 1.6.0, <br>Ubuntu 20.04  |


### vSphere with Tanzu Support Matrix

| Platform | vSphere Compliant | vSphere Non-Compliant |
|----------|-------------------|-----------------------|
| Internet | NA                | >= vSphere 7.0 u2     |
| Proxy    | NA                | >= vSphere 7.0 u2     |

### VMware Cloud Director support Matrix

| Platform | Usecase    | VCD and CSE version     |
|----------|------------|-------------------------|
| VCD      | Greenfield | VCD >= 10.4 & CSE = 4.0 |
| VCD      | Brownfield | VCD >= 10.4 & CSE = 4.0 |

### Tekton Support Matrix

#### Day 0 Support Matrix
| Platform | vSphere with vDS            | vSphere with NSX-T |
|----------|-----------------------------|--------------------|
| Internet | TKG 2.1.0                   | TKG 2.1.0          |
| Internet | TKGs with vSphere >= 7.0 u2 | NA                 |
| Airgap   | Not supported               | Not supported      |

#### Day 2 Support Matrix
|Sl.No  | Day2 Operations | Status              |
|-------|-----------------|---------------------|
| 1     | Rescale         | Supported           |
| 2     | Resize          | Supported           |
