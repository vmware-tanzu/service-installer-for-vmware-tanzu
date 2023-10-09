# Deploying VMware Tanzu for Kubernetes Operations on vSphere with vSphere Distributed Switch Using Service Installer for VMware Tanzu

This document provides the steps for deploying VMware Tanzu for Kubernetes Operations (informally known as TKO) on vSphere with vSphere Distributed Switch using Service Installer for VMware Tanzu.

This deployment uses Tanzu Kubernetes Grid and references the design provided in [VMware Tanzu for Kubernetes Operations on vSphere Reference Design](https://docs.vmware.com/en/VMware-Tanzu/services/tanzu-reference-architecture/GUID-reference-designs-tko-on-vsphere.html).

## Network Design
The following diagram represents the network design required for installing and running Service Installer for VMware Tanzu on vSphere with vSphere Distributed Switch.

![Network design for TKO deployment on vSphere with VDS](./images/vSphere_Network_design.png)

## Prerequisites
Before you deploy Tanzu for Kubernetes Operations using Service Installer for VMware Tanzu, you must configure the following options:

-  You have created the following port groups:
    -   Management  Cluster Network/NSX ALB Management Network: You will connect the VMware NSX Advanced Load Balancer Controller and an interface of NSX Advanced Load Balancer Service Engines (SEs) to this port group.
    -   Tanzu Kubernetes Grid Management Network: The bootstrap VM, Tanzu Kubernetes Grid management cluster nodes, Tanzu Kubernetes Grid shared services cluster, and an interface of NSX Advanced Load Balancer SEs part of SE Group 01 will be connected to this port group.
    -   Tanzu Kubernetes Grid Management Data Network: All Kubernetes load balancer services are exposed to the external network through this network. Only Tanzu Kubernetes Grid shared services clusters use this network. An interface of NSX Advanced Load Balancer SEs part of SE Group 01 will be connected to this port groups.

        IPAM of this network is handled by NSX Advanced Load Balancer and IP addresses are assigned to both VIPs and SEs.

    -   Tanzu Kubernetes Grid Workload Cluster Network: Tanzu Kubernetes Grid workload cluster nodes and an interface of NSX Advanced Load Balancer SEs part of SE Group 02 are connected to this port group.

    -   Tanzu Kubernetes Grid Workload Data Network: All Kubernetes load balancer services are exposed to the external network through this network. Multiple workload clusters can make use of this group.

        NSX Advanced Load Balancer handles the IPAM of this network. The IP addresses are assigned to both VIPs and SEs.

- DHCP service is available on the following networks. The networks must have external access to the Internet.

    -   Management Cluster Network
    -   Tanzu Kubernetes Grid workload clusters port group

  IP addresses are assigned to Tanzu Kubernetes Grid nodes and SEs. DHCP must provide the default Gateway and NTP server details.

- Reserve a block of IP addresses for SEs and VIPs on the networks. IPAM is handled by NSX Advanced Load Balancer.

    -   Tanzu Kubernetes Grid management data/VIP
    -   Tanzu Kubernetes Grid workload data/VIP
    -   Management/NSX Advanced Load Balancer management

- To allow Service Installer to automatically download the required images, such as NSX Advanced Load Balancer Controller and Kubernetes base images, from VMware Marketplace.

    - A Cloud Services Portal (CSP) API token is required to pull all required images from VMware Marketplace. To generate an API token, login in to the CSP portal and select your organization. Go to **Marketplace Service > My Account > API Tokens > Generate a Token**.
    - If Marketplace is not available in your environment or if you are working in an air-gapped environment,

        1. Download and import required Photon/Ubuntu Kubernetes base OVAs to vCenter.

           To download the images, go to [VMware Tanzu Kubernetes Grid Download Product](https://customerconnect.vmware.com/downloads/details?downloadGroup=TKG-160&productId=1098).

        2. Convert the imported images to templates.
        <br>**Note:** Templates must be located under the same cluster where deployment is performed.</br>
        3. Upload the NSX Advanced Load Balancer Controller and Kubernetes OVA:

            1. Create a content library and upload NSX Advanced Load Balancer Controller OVA (22.1.4).
            1. Download the NSX Advanced Load Balancer OVA from [MarketPlace](https://marketplace.cloud.vmware.com/services/details/nsx-advanced-load-balancer-1?slug=true).

        1. A centralized image repository with the required images to deploy the Tanzu Kubernetes clusters in an Internet restricted environments.

           For instructions to set up an Harbor image registry and publish required images, see [Pre-bundled Harbor with Tanzu Kubernetes Grid Dependencies](#airgap)

- (Optional) If you use a custom certificate for deploying Harbor on shared services cluster, import the certificate and private key to the Service Installer VM. The certificate and private key must be in PEM format.

- DNS Name resolution for NSX Advanced Load Balancer Controller.

- You have installed Service Installer for VMware Tanzu.

  For information on how to download and deploy Service Installer for VMware Tanzu, see [Service Installer for VMware Tanzu](../../index.md).

## Ports for Tanzu for Kubernetes Operations Deployment

Source                               | Destination                         | Protocol & Port |
------------------------------------ | ----------------------------------- | --------------- |
TKG Management and Workload Networks | DNS & NTP                           | UDP: 53 and 123 |
TKG Management and Workload Networks | DHCP Server                         | UDP: 67, 68     |
TKG Management and Workload Networks | vCenter Server                      | TCP: 443        |
TKG Management and Workload Networks | Any                                 | TCP: 443        |
TKG Management Cluster Network       | TKG Cluster VIP Network             | TCP: 6443       |
TKG Workload Cluster Network         | TKG Cluster VIP Network             | TCP: 6443       |
TKG Management and Workload Networks | NSX Advanced Load Balancer Controllers                     | TCP: 443        |
NSX Advanced Load Balancer Controllers                      | vCenter and ESXi Hosts              | TCP: 443        |
Admin System                         | Service Instaler VM                 | SSH: 22         |
Service installer VM                 | any                                 | TCP: 443        |
Service installer VM                 | TKG Management and Workload Network | TCP: 6443       |
Service installer VM                 | vCenter                             | TCP: 443        |
Service installer VM                 | NSX Advanced Load Balancer Controller                      | TCP: 443        |
Service installer VM                 | SIVT backend server connections                      | TCP: 5000        |

## SIVT Authentication and Authorization

Service Installer for VMware Tanzu now supports Authentication and Authorization

- Now all the SIVT api requires authentication 
- In SIVT UI a login page has been introduced, the user has to provide the vCenter username, password, and vCenter Ip address or FQDN to login to the SIVT
- For assessing SIVT api x-access-tokens and Server must be passed as a header arguments. Where values for Server header is vCenter fqdn or ip and x-access-tokens is token generated by hitting login api 
- A login API that generates the token by entering the vCenter credentials has been exposed. It will be valid for 240 minutes. 
- Running arcas cli, the user will be prompted with the vCenter server name, vCenter username,and password. Once successfully validated, the user will allowed to run arcas commands.

## Considerations
Consider the following when deploying VMware Tanzu for Kubernetes Operations using Service Installer for VMware Tanzu.

- If you set HTTP proxy, you must also set HTTPS proxy and vice-versa.
    - NSX Advanced Load Balancer Controller must be able to communicate with vCenter directly without a proxy.
    - Avi Kubernetes Operator (AKO) must be able to communicate with NSX Advanced Load Balancer Controller directly without proxy.
    - For the no-proxy section in the JSON file, in addition to the values you specify, Service Installer appends:

        - localhost and 127.0.0.1 on the Service Installer bootstrap VM.
        - localhost, 127.0.0.1, values for CLUSTER_CIDR and SERVICE_CIDR, svc, and svc.cluster.local  for Tanzu Kubernetes Grid management and workload clusters.

        >**Note** While adding domain's under No proxy sections, specify domain name itself e.g. **domain.com**, instead of prefixing it with special character like **.domain.com**

    - If the Kubernetes clusters or Service Installer VMs need to communicate with external services and infrastructure endpoints in your Tanzu Kubernetes Grid environment, ensure that those endpoints are reachable by your proxies or add them to TKG_NO_PROXY. Depending on your environment configuration, this may include, but is not limited to, your OIDC or LDAP server, Harbor, NSX-T, and NSX Advanced Load Balancer for deployments on vSphere.

      For vSphere, you manually add the CIDR of the TKG_MGMT network, which includes the IP address of your control plane endpoint, to TKG_NO_PROXY. If you set VSPHERE_CONTROL_PLANE_ENDPOINT to an FQDN, add both the FQDN and VSPHERE_NETWORK to TKG_NO_PROXY.

- Tanzu Mission Control is required to enable Tanzu Service Mesh and Tanzu Observability.
- Since Tanzu Observability also provides observability services, if Tanzu Observability is enabled, Prometheus and Grafana are not supported.
- In an Internet-restricted environment, provide custom repository details. The registry must not implement user authentication. For example, if you use a Harbor registry, the project must be public and not private.
- AVI deployment with `essentials` and `enterprise` license tier type is supported. The details of the feature supported by essential and enterprise can be found [here](https://avinetworks.com/docs/latest/nsx-alb-license-editions/).
- AVI Essentials deployment does not support AVI L7 ingress controller on workload/shared cluster.

## <a id=deploy-tko></a> Deploy Tanzu for Kubernetes Operations

1. Log in to the Service Installer for VMware Tanzu VM over SSH.

   Enter `ssh root@Service-Installer-IP`.

2. Configure and verify NTP.

   To configure and verify NTP on a Photon OS, see VMware [KB-76088](https://kb.vmware.com/s/article/76088).

3. Import a certificate and private key to the Service Installer for VMware Tanzu bootstrap VM using a copy utility such as SCP or WinSCP (for Windows).

   >**Note** Service Installer uses the certificate for NSX Advanced Load Balancer, Harbor, Prometheus, and Grafana. Ensure that the certificate and private key are in PEM format and are not encrypted as **encrypted certificate files are not supported.** Alternatively, if you do not upload a certificate, Service Installer generates a self-signed certificate.

4. Log in to Service Installer at http://\<_service-installer-ip-address_>\:8888.

5. Under **VMware vSphere with DVS**, click **Deploy Tanzu Kubernetes Grid**.

6. Under **Configure and Generate JSON**, click **Proceed**.

>**Note** To make use of an existing JSON file, click **Proceed** under **Upload and Re-configure JSON**.

7. Enter the required details to generate the input file. For reference, see the [sample JSON file](#sample-input-file).

8. Execute the following command to initiate the deployment.

   ```
   arcas --env vsphere --file /path/to/vsphere_data.json --avi_configuration --tkg_mgmt_configuration --shared_service_configuration --workload_preconfig --workload_deploy --deploy_extensions
   ```
9. Use the following command for end-to-end deployment cleanup.
   ```
   arcas --env vsphere --file /path/to/vsphere_data.json --cleanup all
   ```
   For more information about Selective cleanup, see [Selective cleanup options](../TKGm/TkgmCleanup.md).

   >**Note** If you interrupt the deployment process (i.e. using a `ctrl-c`), you need to restart Service Installer to properly refresh the service. You can do this with `systemctl restart arcas`.

   The following table describes the parameters.

   Python CLI Command Parameter         | Description                                                  |
      ------------------------------------ | ------------------------------------------------------------ |
   --avi_configuration                  | Creates the resource pool and folders for NSX Advanced Load Balancer Controller <br> Deploys AVI Control Plane, generates & replaces certs and performs initial configuration (DNS,NTP)       |
   --tkg_mgmt_configuration             | Configures required networks in AVI, creates cloud, SE group, IPAM profile, and maps IPAM & SE group with Cloud  <br> Creates resource pool and folders for Tanzu Kubernetes Grid management Cluster  <br>  Deploys Tanzu Kubernetes Grid management cluster  <br> Registers Tanzu Kubernetes Grid Mgmt cluster with TMC                          |
   --shared_service_configuration       | Deploys Shared Service cluster (makes use of Tanzu or TMC CLI) <br> Adds required tags to the cluster <br> Deploys Certmanager, Contour, and Harbor|
   --workload_preconfig                 | Configures required network configuration in AVI, creates a new SE Group for Workload Clusters <br> Creates a new AKO config for workload clusters|
   --workload_deploy                    | Deploys a workload cluster (makes use of Tanzu or TMC CLI) <br> Adds required tags to the cluster |
   --deploy_extensions                  | Deploy extensions (Prometheus, Grafana)                      |
   --cleanup                           | cleanup the deployment performed by SIVT. <br> Provides end-to-end and selective cleanup. <br>It accepts parameter values. For more information about cleanup values, see [cleanup options](../TKGm/TkgmCleanup.md). |
   --verbose                            | Enable verbose logging.          |
   | --skip_precheck                   | This option skips all the pre-flight checks.
   | --get_harbor_preloading_status   | This shows the status of TKG dependency loading to Harbor which is pre-bundled with SIVT.
   | --status                         | This option enables users to check for status of current deployment

10. Do the following to integrate with SaaS services such as Tanzu Mission Control, Tanzu Service Mesh, and Tanzu Observability. In the JSON file:

    - to activate or deactivate Tanzu Mission Control and to use the Tanzu Mission Control CLI and API enter `"tmcAvailability": "true/false"`.
    - to activate or deactivate Tanzu Service Mesh, enter `"tkgWorkloadTsmIntegration": "true/false"`.
    - to activate or deactivate Tanzu Observability, enter `"tanzuObservabilityAvailability": "true/false"`.

11. If you are using a proxy, configure the proxy details in the proxy field corresponding to the cluster.

    For example, to activate or deactivate proxy on the management cluster, use `tkgMgmt: {"enable-proxy": "true"}` in the JSON file.

12. Activate or deactivate Tanzu Kubernetes Grid extensions. For example,
    - to activate or deactivate Prometheus and Grafana, enter `"enableExtensions": "true/false"`.
    - to activate or deactivate Harbor, enter `"enableHarborExtension": "true/false"`.

>**Note**
>- Tanzu Mission Control is required to activate Tanzu Service Mesh and Tanzu Observability.
>- If Tanzu Observability is activated, Prometheus and Grafana are not supported.
>- When Tanzu Mission Control is activated only Photon is supported.

## Pinniped Configuration Guide
In the Identity Management section of SIVT UI, you will find option to enable the service.
For more details on preparing an external identity management, please refer to [this](https://docs.vmware.com/en/VMware-Tanzu-for-Kubernetes-Operations/2.3/tko-reference-architecture/GUID-deployment-guides-pinniped-with-tkg.html).


- If you choose to use OIDC, provide details of your OIDC provider account, for example, Okta.
      - **Issuer URL:** The IP or DNS address of your OIDC server.
         >- This maps to `oidcIssuerUrl` in JSON file and `OIDC_IDENTITY_PROVIDER_ISSUER_URL` in Management CLuster Yaml file.
      - **Client ID:** The client_id value that you obtain from your OIDC provider. For example, if your provider is Okta, log in to Okta, create a Web application, and select the Client Credentials options in order to get a client_id and secret.
         >- This maps to `oidcClientId` in JSON file and `OIDC_IDENTITY_PROVIDER_CLIENT_ID` in Management CLuster Yaml file.
      - **Client Secret:** The secret value that you obtain from your OIDC provider.
         >- This maps to `oidcClientSecret` in JSON file and `OIDC_IDENTITY_PROVIDER_CLIENT_SECRET` in Management CLuster Yaml file.
      - **Scopes:** A comma separated list of additional scopes to request in the token response. For example, openid,groups,email.
         >- This maps to `oidcScopes` in JSON file and `OIDC_IDENTITY_PROVIDER_SCOPES` in Management CLuster Yaml file.
      - **Username Claim:** The name of your username claim. This is used to set a user’s username in the JSON Web Token (JWT) claim. Depending on your provider, enter claims such as user_name, email, or code.
         >- This maps to `oidcUsernameClaim` in JSON file and `OIDC_IDENTITY_PROVIDER_USERNAME_CLAIM` in Management CLuster Yaml file.
      - **Groups Claim:** The name of your groups claim. This is used to set a user’s group in the JWT claim. For example, groups.
         >- This maps to `oidcGroupsClaim` in JSON file and `OIDC_IDENTITY_PROVIDER_GROUPS_CLAIM` in Management CLuster Yaml file.

  - If you choose to use LDAPS, provide details of your company’s LDAPS server. All settings except for LDAPS Endpoint are optional.
        - **LDAPS Endpoint:** The IP or DNS address of your LDAPS server. Provide the address and port of the LDAP server, in the form host:port.
         >  - This maps to `ldapEndpointIp` and `ldapEndpointPort` in JSON file and `LDAP_HOST` in Management CLuster Yaml file.
        - **Bind DN:** The DN for an application service account. The connector uses these credentials to search for users and groups. Not required if the LDAP server provides access for anonymous authentication.
         >  - This maps to `ldapBindDN` in JSON file and `LDAP_BIND_DN` in Management CLuster Yaml file.
        - **Bind Password:** The password for an application service account, if Bind DN is set.
         >  - This maps to `ldapBindPWBase64` in JSON file and `LDAP_BIND_PASSWORD` in Management CLuster Yaml file.
        - **User Search Base DN:** The point from which to start the LDAP search. For example, OU=Users,OU=domain,DC=io.
         >  - This maps to `ldapUserSearchBaseDN` in JSON file and `LDAP_USER_SEARCH_BASE_DN` in Management CLuster Yaml file.
        - **User Search Filter:** An optional filter to be used by the LDAP search.
         >  - This maps to `ldapUserSearchFilter` in JSON file and `LDAP_USER_SEARCH_FILTER` in Management CLuster Yaml file.
        - **User Search Username:** The LDAP attribute that contains the user ID. For example, uid, sAMAccountName.
         >  - This maps to `ldapUserSearchUsername` in JSON file and `LDAP_USER_SEARCH_USERNAME` in Management CLuster Yaml file.
        - **Group Search Base DN:** The point from which to start the LDAP search. For example, OU=Groups,OU=domain,DC=io.
         >  - This maps to `ldapGroupSearchBaseDN` in JSON file and `LDAP_GROUP_SEARCH_BASE_DN` in Management CLuster Yaml file.
        - **Group Search Filter:** An optional filter to be used by the LDAP search.
         >  - This maps to `ldapGroupSearchFilter` in JSON file and `LDAP_GROUP_SEARCH_FILTER` in Management CLuster Yaml file.
        - **Group Search Name Attribute:** The LDAP attribute that holds the name of the group. For example, cn.
         >  - This maps to `ldapGroupSearchNameAttr` in JSON file and `LDAP_GROUP_SEARCH_NAME_ATTRIBUTE` in Management CLuster Yaml file.
        - **Group Search User Attribute:** The attribute of the user record that is used as the value of the membership attribute of the group record. For example, distinguishedName, dn.
         >  - This maps to `ldapGroupSearchUserAttr` in JSON file and `LDAP_GROUP_SEARCH_USER_ATTRIBUTE` in Management CLuster Yaml file.
        - **Group Search Group Attribute:** The attribute of the group record that holds the user/member information. For example, member.
         >  - This maps to `ldapGroupSearchGroupAttr` in JSON file and `LDAP_GROUP_SEARCH_GROUP_ATTRIBUTE` in Management CLuster Yaml file.
        - **Root CA:** Paste the contents of the LDAPS server CA certificate into the Root CA text box.
         >  - This maps to `ldapRootCAData` in JSON file and `LDAP_ROOT_CA_DATA_B64` in Management CLuster Yaml file.

## Air-gapped: Pre-bundled Harbor with Tanzu Kubernetes Grid Dependencies

- If a pre-bundled harbor with all the necessary binaries is already present in the environment, follow below steps:
    - This harbor details must be provided under `Custom Repository` section of UI while generating deployment JSON file.
    - Make sure binaries uploaded to harbor are corresponding to the specific version of Tanzu being deployed.
    - SIVT OVA without harbor (`service-installer-for-VMware-Tanzu.ova`) can be used for performing the deployment as environment already has pre-bundled harbor.
    - SIVT 2.4.0 is bundled with Tanzu CLI 0.90.1. Perform the following steps to configure SIVT to consume the pre-bundled harbor:
      - Set the plugin source using:
        ```
        tanzu plugin source update default --uri <harbor-fqdn>:<port>/tanzu/tanzu-cli/plugins/plugin-inventory:latest
        OR
        tanzu plugin source update default --uri <harbor-fqdn>:<port>/<path-to-plugin-inventory>
        ```
      - Skip verification for this plugin source:
        ```
        export TANZU_CLI_PLUGIN_DISCOVERY_IMAGE_SIGNATURE_VERIFICATION_SKIP_LIST=<harbor-fqdn>:<port>/<path-to-plugin-inventory>
        ```
- If a pre-bundled harbor not present in the environment, follow below steps:
    - User must download Service Installer for VMware Tanzu OVA (`service-installer-for-VMware-Tanzu-with-Harbor.ova`) file from Marketplace. This OVA comes bundled with Tanzu Kubernetes Grid 2.2.0 dependencies which are not compliant.
    - While deploying OVA make sure to configure static network details by providing all the values prompted under "Networking Properties".

      >**Note** Domain Name provided is used as fqdn for harbor. Make sure to create a DNS record for the FQDN and the static Management IP that you provide.
    - Once OVA is deployed and powered on, all the images are uploaded to `tanzu` in the embedded harbor of SIVT. This will take ~ 20 minutes to complete.
    - To access harbor, log in to Harbor at `https://<sivt-ip>:9443`
        - Credential -> user:admin password:`<sivt password>`
    - Verify that all binaries are uploaded to Harbor with the mentioned repo name `tanzu`.
    - You can also verify the upload status using following arcas command
      ```
      arcas --get_harbor_preloading_status --repo_name tanzu
      ```
    - This harbor details must be provided under `Custom Repository` section of UI while generating deployment JSON file. Use below URL format for custom repository
      ```
      https://<harbor-fqdn>:9443/tanzu
      ```
    - The plugins are available at: `https://<sivt-ip>:9443/tanzu/tanzu-cli/plugins/plugin-inventory:latest`.


## Update a Running Extension Deployment

To make changes to the configuration of a running package after deployment, update your deployed package:

1. Obtain the installed package version and namespace details using the following command.
   ```
   tanzu package available list -A
   ```

2. Update the package configuration `<package-name>-data-values.yaml` file. Yaml files for the extensions deployed using SIVT are available under `/opt/vmware/arcas/tanzu-clusters/<cluster-name>` in the SIVT VM.

3. Update the installed package using the following command.

   ```
   tanzu package installed update <package-name> --version <installed-package-version> --values-file <path-to-yaml-file-in-SIVT> --namespace <package-namespace>
   ```

**Refer to the following example for Grafana update:**

**Step 1:** List the installed package version and namespace details.
   ```
   # tanzu package available list -A
   / Retrieving installed packages...
   NAME            PACKAGE-NAME                     PACKAGE-VERSION          STATUS               NAMESPACE
   cert-manager    cert-manager.tanzu.vmware.com    1.1.0+vmware.1-tkg.2     Reconcile succeeded  my-packages
   contour         contour.tanzu.vmware.com         1.17.1+vmware.1-tkg.1    Reconcile succeeded  my-packages
   grafana         grafana.tanzu.vmware.com         7.5.7+vmware.1-tkg.1     Reconcile succeeded  tkg-system
   prometheus      prometheus.tanzu.vmware.com      2.27.0+vmware.1-tkg.1    Reconcile succeeded  tkg-system
   antrea          antrea.tanzu.vmware.com                                   Reconcile succeeded  tkg-system
   [...]
   ```

**Step 2:** Update the Grafana configuration in the `grafana-data-values.yaml` file available under `/opt/vmware/arcas/tanzu-clusters/<cluster-name>/grafana-data-values.yaml`.

**Step 3:** Update the installed package.
   ```
   tanzu package installed update grafana --version 7.5.7+vmware.1-tkg.1 --values-file /opt/vmware/arcas/tanzu-clusters/testCluster/grafana-data-values.yaml --namespace my-packages
   ```
Expected Output:
   ```
   | Updating package 'grafana'
   - Getting package install for 'grafana'
   | Updating secret 'grafana-my-packages-values'
   | Updating package install for 'grafana'

   Updated package install 'grafana' in namespace 'my-packages'
   ```

For information about updating, see [Update a Package](https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/2.3/using-tkg/workload-packages-ref.html).

## <a id="sample-input-file"> </a> Sample Input File
The Service Installer user interface generates the JSON file based on your inputs and saves it to **/opt/vmware/arcas/src/** in Service Installer VM. Files are named based on the environment:

- vSphere DVS Internet environment: vsphere-dvs-tkgm.json
- vSphere DVS Proxy environment: vsphere-dvs-tkgm-proxy.json
- vSphere DVS air-gapped environment: vsphere-dvs-tkgm-airgapped.json


Following is an example of the JSON file.

>**Note** The sample JSON file is also available in Service Installer VM at the following location: **/opt/vmware/arcas/src/vsphere/vsphere-dvs-tkgm.json.sample**.

```json
{
   "envSpec":{
      "vcenterDetails":{
         "vcenterAddress":"vcenter.xx.xx",
         "vcenterSsoUser":"administrator@vsphere.local",
         "vcenterSsoPasswordBase64":"cGFzc3dvcmQ=",
         "vcenterDatacenter":"Datacenter-1",
         "vcenterCluster":"Cluster-1",
         "vcenterDatastore":"Datastore-1",
         "contentLibraryName":"TanzuAutomation-Lib",
         "aviOvaName":"avi-controller",
         "resourcePoolName":""
      },
      "envType":"tkgm",
      "marketplaceSpec":{
         "refreshToken":"t9TfXXXXJuMCq3"
      },
      "ceipParticipation":  "true",
      "customRepositorySpec":{
         "tkgCustomImageRepository":"https://harbor-local.xx.xx/tkg151",
         "tkgCustomImageRepositoryPublicCaCert":"false"
      },
      "saasEndpoints":{
         "tmcDetails":{
            "tmcAvailability":"false",
            "tmcRefreshToken":"t9TfXXXXJuMCq3",
            "tmcInstanceURL":"https://xxxx.tmc.com"
         },
         "tanzuObservabilityDetails":{
            "tanzuObservabilityAvailability":"false",
            "tanzuObservabilityUrl":"https://surf.wavefront.com",
            "tanzuObservabilityRefreshToken":"6777a3a8-XXXX-XXXX-XXXXX-797b20638660"
         }
      },
      "infraComponents":{
         "dnsServersIp":"x.x.x.x",
         "ntpServers":"x.x.x.x",
         "searchDomains":".xx.xx"
      },
      "proxySpec":{
         "arcasVm":{
            "enableProxy":"false",
            "httpProxy":"http://<fqdn/ip>:<port>",
            "httpsProxy":"https://<fqdn/ip>:<port>",
            "noProxy":"vcenter.xx.xx,172.x.x.x"
         },
         "tkgMgmt":{
            "enableProxy":"false",
            "httpProxy":"http://<fqdn/ip>:<port>",
            "httpsProxy":"https://<fqdn/ip>:<port>",
            "noProxy":""
         },
         "tkgSharedservice":{
            "enableProxy":"false",
            "httpProxy":"http://<fqdn/ip>:<port>",
            "httpsProxy":"https://<fqdn/ip>:<port>",
            "noProxy":"vcenter.xx.xx,172.x.x.x"
         },
         "tkgWorkload":{
            "enableProxy":"false",
            "httpProxy":"http://<fqdn/ip>:<port>",
            "httpsProxy":"https://<fqdn/ip>:<port>",
            "noProxy":"vcenter.xx.xx,172.x.x.x"
         }
      }
   },
   "tkgComponentSpec":{
      "aviMgmtNetwork":{
         "aviMgmtNetworkName":"nsx_alb_management_pg",
         "aviMgmtNetworkGatewayCidr":"11.12.1.14/24",
         "aviMgmtServiceIpStartRange":"11.12.1.14",
         "aviMgmtServiceIpEndRange":"11.12.1.28"
      },
      "tkgClusterVipNetwork":{
         "tkgClusterVipNetworkName":"tkg_cluster_vip_pg",
         "tkgClusterVipNetworkGatewayCidr":"11.12.2.14",
         "tkgClusterVipIpStartRange":"11.12.2.14",
         "tkgClusterVipIpEndRange":"11.12.2.28"
      },
      "aviComponents":{
         "aviPasswordBase64":"cGFzc3dvcmQ=",
         "aviBackupPassphraseBase64":"cGFzc3dvcmQ=",
         "enableAviHa":"true",
         "modeOfDeployment": "orchestrated",
         "typeOfLicense": "enterprise",
         "aviController01Ip":"11.12.1.18",
         "aviController01Fqdn":"avi.xx.xx",
         "aviController02Ip":"11.12.1.15",
         "aviController02Fqdn":"avi2.xx.xx",
         "aviController03Ip":"11.12.1.16",
         "aviController03Fqdn":"avi3.xx.xx",
         "aviClusterIp":"11.12.1.17",
         "aviClusterFqdn":"avi4.xx.xx",
         "aviSize":"essentials",
         "aviCertPath":"",
         "aviCertKeyPath":""
      },
      "identityManagementSpec":{
         "identityManagementType":"",
         "oidcSpec":{
            "oidcIssuerUrl":"",
            "oidcClientId":"",
            "oidcClientSecret":"",
            "oidcScopes":"",
            "oidcUsernameClaim":"",
            "oidcGroupsClaim":""
         },
         "ldapSpec":{
            "ldapEndpointIp":"",
            "ldapEndpointPort":"",
            "ldapBindPWBase64":"",
            "ldapBindDN":"",
            "ldapUserSearchBaseDN":"",
            "ldapUserSearchFilter":"",
            "ldapUserSearchUsername":"",
            "ldapGroupSearchBaseDN":"",
            "ldapGroupSearchFilter":"",
            "ldapGroupSearchUserAttr":"",
            "ldapGroupSearchGroupAttr":"",
            "ldapGroupSearchNameAttr":"",
            "ldapRootCAData":""
         }
      },
      "tkgMgmtComponents":{
         "tkgMgmtNetworkName":"tkg_mgmt_pg",
         "tkgMgmtGatewayCidr":"11.12.3.14/24",
         "tkgMgmtClusterName":"Mgmt-cluster",
         "tkgMgmtSize":"custom",
         "tkgMgmtCpuSize":"2",
         "tkgMgmtMemorySize":"16",
         "tkgMgmtStorageSize":"290",
         "tkgMgmtDeploymentType":"prod",
         "tkgMgmtClusterCidr":"100.96.0.0/11",
         "tkgMgmtServiceCidr":"100.64.0.0/13",
         "tkgMgmtBaseOs":"photon",
         "tkgMgmtRbacUserRoleSpec":{
            "clusterAdminUsers":"",
            "adminUsers":"",
            "editUsers":"",
            "viewUsers":""
         },
         "tkgMgmtClusterGroupName":"",
         "tkgSharedserviceClusterName":"shared-cluster",
         "tkgSharedserviceSize":"custom",
         "tkgSharedserviceCpuSize":"2",
         "tkgSharedserviceMemorySize":"16",
         "tkgSharedserviceStorageSize":"290",
         "tkgSharedserviceDeploymentType":"prod",
         "tkgSharedserviceWorkerMachineCount":"3",
         "tkgSharedserviceClusterCidr":"100.96.0.0/11",
         "tkgSharedserviceServiceCidr":"100.64.0.0/13",
         "tkgSharedserviceBaseOs":"photon",
         "tkgSharedserviceKubeVersion":"v1.22.5",
         "tkgSharedserviceEnableAviL7": "false",
         "tkgSharedserviceRbacUserRoleSpec":{
            "clusterAdminUsers":"",
            "adminUsers":"",
            "editUsers":"",
            "viewUsers":""
         },
         "tkgSharedserviceClusterGroupName":"",
         "tkgSharedserviceEnableDataProtection":"false",
         "tkgSharedClusterCredential":"",
         "tkgSharedClusterBackupLocation":"",
         "tkgSharedClusterVeleroDataProtection":{
            "enableVelero":"true",
            "username": "admin",
            "passwordBase64": "cGFzc3dvcmQ=",
            "bucketName": "shared-backup",
            "backupRegion": "minio",
            "backupS3Url": "http://<minio-server>:9000",
            "backupPublicUrl": "http://<minio-server>:9000"
         }
      }
   },
   "tkgMgmtDataNetwork":{
      "tkgMgmtDataNetworkName":"tkg_mgmt_vip_pg",
      "tkgMgmtDataNetworkGatewayCidr":"11.12.4.14/24",
      "tkgMgmtAviServiceIpStartRange":"11.12.4.14",
      "tkgMgmtAviServiceIpEndRange":"11.12.4.28"
   },
   "tkgWorkloadDataNetwork":{
      "tkgWorkloadDataNetworkName":"tkg_workload_vip_pg",
      "tkgWorkloadDataNetworkGatewayCidr":"11.12.5.14/24",
      "tkgWorkloadAviServiceIpStartRange":"11.12.5.14",
      "tkgWorkloadAviServiceIpEndRange":"11.12.5.28"
   },
   "tkgWorkloadComponents":{
      "tkgWorkloadNetworkName":"tkg_workload_pg",
      "tkgWorkloadGatewayCidr":"11.12.6.14/24",
      "tkgWorkloadClusterName":"tkg-workload-rk1901",
      "tkgWorkloadSize":"custom",
      "tkgWorkloadCpuSize":"2",
      "tkgWorkloadMemorySize":"16",
      "tkgWorkloadStorageSize":"290",
      "tkgWorkloadDeploymentType":"prod",
      "tkgWorkloadWorkerMachineCount":"3",
      "tkgWorkloadClusterCidr":"100.96.0.0/11",
      "tkgWorkloadServiceCidr":"100.64.0.0/13",
      "tkgWorkloadBaseOs":"photon",
      "tkgWorkloadKubeVersion":"v1.21.8",
      "tkgWorkloadEnableAviL7": "false",
      "tkgWorkloadRbacUserRoleSpec":{
         "clusterAdminUsers":"",
         "adminUsers":"",
         "editUsers":"",
         "viewUsers":""
      },
      "tkgWorkloadTsmIntegration":"false",
      "namespaceExclusions":{
         "exactName":"",
         "startsWith":""
      },
      "tkgWorkloadClusterGroupName":"",
      "tkgWorkloadEnableDataProtection":"false",
      "tkgWorkloadClusterCredential":"",
      "tkgWorkloadClusterBackupLocation":"",
      "tkgWorkloadClusterVeleroDataProtection":{
         "enableVelero":"true",
         "username": "admin",
         "passwordBase64": "cGFzc3dvcmQ=",
         "bucketName": "workload-backup",
         "backupS3Url": "http://<minio-server>:9000",
         "backupPublicUrl": "http://<minio-server>:9000"
      }
   },
   "harborSpec":{
      "enableHarborExtension":"true",
      "harborFqdn":"harbor.xx.tk",
      "harborPasswordBase64":"cGFzc3dvcmQ=",
      "harborCertPath":"/root/cert.pem",
      "harborCertKeyPath":"/root/key.pem"
   },
   "tanzuExtensions":{
      "enableExtensions":"true",
      "tkgClustersName":"tkg-workload-rk1901",
      "logging":{
         "syslogEndpoint":{
            "enableSyslogEndpoint":"false",
            "syslogEndpointAddress":"",
            "syslogEndpointPort":"",
            "syslogEndpointMode":"",
            "syslogEndpointFormat":""
         },
         "httpEndpoint":{
            "enableHttpEndpoint":"false",
            "httpEndpointAddress":"",
            "httpEndpointPort":"",
            "httpEndpointUri":"",
            "httpEndpointHeaderKeyValue":"Authorization Bearer Axxxxxxxxx"
         },
         "kafkaEndpoint":{
            "enableKafkaEndpoint":"false",
            "kafkaBrokerServiceName":"",
            "kafkaTopicName":""
         }
      },
      "monitoring":{
         "enableLoggingExtension":"true",
         "prometheusFqdn":"promethus.xx.vmw",
         "prometheusCertPath":"/root/cert.pem",
         "prometheusCertKeyPath":"/root/key.pem",
         "grafanaFqdn":"grafana.xx.vmw",
         "grafanaCertPath":"/root/cert.pem",
         "grafanaCertKeyPath":"/root/key.pem",
         "grafanaPasswordBase64":"cGFzc3dvcmQ="
      }
   }
}
```
