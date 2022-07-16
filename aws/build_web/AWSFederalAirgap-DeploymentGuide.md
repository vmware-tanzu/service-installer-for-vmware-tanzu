# Federal AWS SIVT Automation
The Federal AWS Service Installer for VMware Tanzu (SIVT) Automation enables users to install TKG in an Airgap AWS environment(internet restricted) with the help of easily transportable binaries/TAR balls and terraform automation scripts. The Platform deployed should be STIG hardened and FIPS compliant. The automation deploys following Tanzu components
  - Management cluster
  - Workload cluster
  - User managed packages i.e. Harbor, Prometheus, Grafana, Fluent-bit and contour

This document describes the steps that needs to be followed to deploy TKG on Airgap AWS environment using SIVT automation.

**NOTE:** The repository uses submodules hence, make sure you clone the submodules using the command `git clone git@gitlab.eng.vmware.com:core-build/sivt-aws-federal.git --recurse`

## Prerequisites

Before deploying Tanzu Kubernetes Grid on AWS using Service Installer for VMware Tanzu, ensure the following are setup. 

1. A pre-existing AirGapped Virtual Private Network(VPC) in AWS. This AWS VPC should have VPC endpoints of type interface unless otherwise specified, enabled to allow access within the vpc to the following AWS services
    - sts
    - ssm
    - ec2
    - ec2messages
    - elasticloadbalancing
    - secretsmanager
    - ssmmessages
    - cloudformation
    - s3 (gateway type)

2. An RSA SSH key pair created in the AWS region where TKG needs to be deployed.

3. An S3 Bucket that is in the same AWS region as airgapped VPC, with all of the TKG dependencies required for the install. Follow steps to complete this task
    - Download the Tarball which contains all the TKG/TKR binaries from [buildweb](https://buildweb.eng.vmware.com/) <br/>
        **Note:** Below two files needs to be downloaded from above link based on your requirements
        - `tkg_tkr_1_5_3.tar` contains all the TKG/TKR binaries - For manual deployment
        - `tkg_sivt_aws_federal_1_5_3.tar` contains TKG/TKR binaries, harbor, deployment dependencies as well as automation source code - To deploy using automation
    - Copy the data over to your internet restricted environment on the portable media. Finally run the following commands to copy the dependecny to S3 bucket,
      ```sh
      export BUCKET_NAME=MY-BUCKET
      export DEPS_DIR=MY-DEPENDENCY-DIRECTORY
      make upload-deps
      ```
4. Create a bucket policy on your aws s3 bucket that allows access from within VPC via a VPC endpoint. The policy should look like the below,
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Access-to-specific-VPCE-only",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::<YOUR BUCKET NAME>/*",
                "Condition": {
                    "StringEquals": {
                        "aws:sourceVpce": "<YOUR VPC ENDPOINT ID>"
                    }
                }
            }
        ]
    }
    ```
5. A bastion VM with SSH access to the airgapped env that has,
    - Docker
    - yq
    - awscli
    - jq
    - make(build-essentials)
    - terraform
    - kind
    - goss
    - CAPI Image builder
    - docker-compose
    - Ubuntu OS apt-get repo
    - crashd

6. Account used for deployment must have access to create CloudFormation, security groups, EC2 instances, bucket policies, and AMIs as well as create, get, and list access to the TKG dependenices bucket (S3 bucket) mentioned above.

7. Bash shell support must be enabled as the shell scripts in the code use /bin/bash.


### Deployment Steps
1. Copy the contents of the portable media created using tarball, to the bastion VM.

2. Copy dependencies to the AWS S3 bucket by executing the below commands inside the the Federal SIVT AWS git repo.
    ```sh
      export BUCKET_NAME=<S3 Bucket in airgapped env>
      export DEPS_DIR=<Directory where dependencies are located>
      make upload-deps
    ```

3. Export the following environment variables:
    ```sh
      export BUCKET_NAME=<AWS S3 bucket name containing dependencies>
      export VPC_ID=<AirGapped VPC ID>
      export SUBNET_ID=<Private Subnet ID where TKGm will be installed>
      export SSH_KEY_NAME=<AWS RSA SSH key>
      export AWS_AZ_ZONE=<AWS AZ_ZONE>
      export AWS_SESSION_TOKEN=<AWS session token>
      export AWS_ACCESS_KEY_ID=<AWS Access Key ID>
      export AWS_SECRET_ACCESS_KEY=<AWS Secret Access Key>
      export AWS_DEFAULT_REGION=<AWS Region where TKGm will be installed>
      export TKR_VERSION=<Tanzu Kubernetes Release Version>
      export TKG_VERSION=<Tanzu Kubernetes Grid Version>
      export FIPS_ENABLED=<true or false> #This variable should be set to **true**
    ```
    |TKG Version|TKR Version|FIPS ENABLED|
    |-----------|-----------|------------|
    |v1.5.3|v1.22.8|true|

    **NOTE:**
    If you do not want to use default Harbor Admin Password, export the password using below command:

    ```sh
    export TF_VAR_harbor_pwd=<Custom Password for Harbor>
    ```

4. This step is needed if you plan to use existing image registry. Refer [Using an Existing Registry](#using-an-existing-registry) section for detailed steps.

5. Script sets below values for harbor, prometheus and grafana extensions

    ```sh
      HARBOR_HOSTNAME="harbor.system.tanzu"
      PROMETHEUS_HOSTNAME="prometheus.system.tanzu"
      GRAFANA_HOSTNAME="grafana.system.tanzu"
      HARBOR_PASSWORD="harbor123"
    ```
    Use below commands if you want to overwrite these values

    ```sh
        export TF_VAR_harbor_host_name=<Hostname for Harbor>
        export TF_VAR_prometheus_host_name=<Hostname for Prometheus>
        export TF_VAR_grafana_host_name=<Hostname for Grafana>
        export TF_VAR_harbor_extension_password=<Password for Harbor>
    ```
## Install TKG extensions
By default script will not install any of the TKG extensions. Set following variables to install TKG extensions like cert-manager, contour, fluent-bit, grafana, prometheus and Harbor.
```sh
    export HARBOR_DEPLOYMENT=true
    export PROMETHEUS_DEPLOYMENT=true
    export GRAFANA_DEPLOYMENT=true
    export FLUENT_BIT_DEPLOYMENT=true
    export CONTOUR_DEPLOYMENT=true
    export CERT_MANAGER_DEPLOYMENT=true
```
  Installer will resolve the pre-requistes for extension deployments. Example: grafana needs cert-manager, contour and prometheus. So scripts will install cert-manager, contour and prometheus prior to Grafana installation if GRAFANA_DEPLOYMENT is set to **true**.

### Install TKG

For installing TKG, use one of the below commands inside the installer repo

  - Run `make all` command for End-to-End deployment
      ```sh 
        make all
      ```
  - If few of the steps in deployments needs manual intevention like CloudFormation for roles/policies, Harbor installation, then choose to run the below commands in the given order _for ubuntu based STIG compliant deployment_. Skip the step which is performed manually. 
  **Note:** The detailed description of individual steps described in [table](#make-targets)

      ```sh
        make verify-all-inputs 
        make cf
        make install-harbor 
        make check-for-ca-download
        make setup-docker
        make tkg-bootstrap-ami-offline 
        make stig-ami-offline 
        make install
      ```
  - If few of the steps in deployments needs manual intevention like CloudFormation for roles/policies, Harbor installation, then choose to run the below commands in the given order _for Amazon Linux 2 based deployment_. Skip the step which is performed manually. 
  **Note:** The detailed description of individual steps described in [table](#make-targets)

      ```sh
        make verify-all-inputs 
        make cf 
        make install-harbor 
        make check-for-ca-download 
        make setup-docker 
        make al2-bootstrap-ami-offline 
        make al2-node-ami-offline 
        make install-tkg-on-al2
      ```

## Make Targets
  |CLI Parameter| Description|Prerequisites|
  |--------|--------|--------|
  |all|End to End TKG deployment|NA|
  |verify-all-inputs|check all the inputs mentioned in [Deployment Steps](#deployment-steps) are set. Script mainly checks for mandatory variables|NA|
  |cf|Make Cloud Formation if it doesn't exist|NA|
  |install-harbor|Deploy harbor on a new EC2 instance via terraform|Make sure IAM profile names "tkg-s3-viewer" is created before this steps|
  |check-for-ca-download|check if harbor CA certificate is downloaded|Harbor must be up and running and REGISTRY_CA_FILENAME varaible is set|
  |setup-docker|setup local docker with downloaded harbor CA certificate| Make sure below steps are done 1. Harbor must be up and running 2. Harbor CA certificate must be downloaded. 3. REGISTRY_CA_FILENAME and REGISTRY variables are set.|
  |tkg-bootstrap-ami-offline|Build ubuntu based bootstrap ami| Make sure Prerequisites of `check-for-ca-download` and `setup-docker` are intact|
  |stig-ami-offline|build ubuntu based STIG compliant node ami| Make sure Prerequisites of `check-for-ca-download` and `setup-docker` are intact|
  |install|Deploy bootstrap on EC2 instance and deploy management and workload clusters on top of node ami| Make sure AMIs and harbor are available, REGISTRY varaible is set with harbor hostname and IAM profile names "tkg-bootstrap" is created |
  |al2-node-ami-offline|build amazon linux2 ami's for TKG clusters|Make sure Prerequisites of `check-for-ca-download` and `setup-docker` are intact|
  |al2-bootstrap-ami-offline|build amazon linux2 ami's for bootstrap|Make sure Prerequisites of `check-for-ca-download` and `setup-docker` are intact|
  |all-al2-offline-ami|build amazon linux2 ami's for bootstrap and TKG clusters|Make sure Prerequisites of `check-for-ca-download` and `setup-docker` are intact|
  |install-tkg-on-al2|install tkg on AWS, considering Amazon Linux 2 as base OS for Bootstrap and TKG clusters|Make sure AMIs and harbor are available, REGISTRY varaible is set with harbor hostname and IAM profile names "tkg-bootstrap" is created|

**Note:** 
  1. Prerequisites mentioned in above table must be taken care only if you are not using `make all` or if you are not following step by step process.
  2. For more information on IAM profiles and their corresponding roles and policies, please refer [1clickiamtemplate](https://gitlab.eng.vmware.com/core-build/sivt-aws-federal/-/blob/main/1clickiamtemplate) file. 

  - For a list of all commands run

    ```sh
      make
    ```

## Customizing Harbor
By default Harbor is installed on an Amazon 2 ami as it needs the amazon CLI to pull down dependencies from the TKG dependencies bucket as well as the ability to install docker within an airgapped env.

  - The below env vars can be set to change harbors default behavior:
      ```sh
        export TF_VAR_create_certs = <Default is true>
      ```

  - If TF_VAR_create_certs is true (which is the default), below variables must be set
      ```sh
        export TF_VAR_cert_l=#Default Minneapolis| L in the certs cn(Location)
        export TF_VAR_cert_st=#Default Minnesota|ST in the certs CN(State)
        export TF_VAR_cert_o=#Default VmWare|O in the certs CN(Organization)
        export TF_VAR_cert_ou=#Default VmWare R&D|OU in the certs CN(Organizational Unit)
      ```

  - Else if TF_VAR_create_certs is false, below variables must be set
      ```sh
        export TF_VAR_cert_path=#Path to certificate on harbor ami
        export TF_VAR_cert_key_path=#Path to private key on harbor ami
        export TF_VAR_cert_ca_path=#Path to ca certificate on harbor ami
      ```

## Customizing AMIs

This section describes the process of customizing the Ubuntu AMIs created in the deployment. The AMIs are created using the VPC ID and subnet ID of your airgapped VPC.

  - **FIPS** 
  To disable FIPS set `install_fips` to `no` in [STIG roles' main.yml](https://gitlab.eng.vmware.com/core-build/canonical-ubuntu-18.04-lts-stig-hardening/-/blob/master/vars/main.yml)

  - **Adding CA certificate in the trust store**
  To add CA certificate(s) to the AMI, copy the CA(s) in `PEM` format to [STIG roles' files/ca folder](https://gitlab.eng.vmware.com/core-build/canonical-ubuntu-18.04-lts-stig-hardening/-/tree/master/files/ca)

## Customizing TKG

All configurable options and their defaults can bee seen in
[terraform/startup.sh](https://gitlab.eng.vmware.com/core-build/sivt-aws-federal/-/tree/main/terraform). The variables should be edited in this file for them to take affect, as terraform is not configured to take all of them as inputs.

See the [variables](#variables) section for a description of all variables.

## Accessing your Harbor Instance
  - Once terrafrom finishes applying if you set up VPC peering with another VPC, you should be able to ssh into your harbor instance. To do this simply modify the security group, on an EC2 instance within the non airgapped VPC in the peering connection, to allow it to ssh over to the bootstrap.
  - On the bootstrap instance you can run `sudo tail -f /var/log/cloud-init-output.log` to track the progress of your harbor installation and subsequent loading of TKG images.

## Accessing your TKG Cluster
  - See [accessing your harbor instance](#Accessing-your-Harbor-Instance) for setting up VPC peering that will allow ssh access to your harbor instance and bootstrap instance.

  - You can run below command on bootstrap instance to track the progress of TKG install 
      ```
        sudo tail -f /var/log/cloud-init-output.log
      ```
  - Once you see a message about the security group of your bootstrap being modified, the script has finished. You can now run `kubectl get pods -A` to see all the pods running on your management cluster. Additionally if you run `kubectl get nodes`, grab an IP of one of the cluster nodes and you can SSH to it from the bootstrap node using the ssh_key you provided to terraform.


## Updating the harbor admin password

The default harbor admin password is in `air-gapped/airgapped.env` on the bootstrap host under HARBOR_ADMIN_PWD. This was set as a terraform variable.

To update run the below place the old password where it says \<OLDPASSWORD HERE \>and your new password where it says \<NEW PASSWORD HERE\>:

```sh
source $HOME/air-gapped/airgapped.env
curl -XPUT -H 'Content-Type: application/json' -u admin:$HARBOR_ADMIN_PWD "https://$DNS_NAME/api/v2.0/users/1/password" --cacert /etc/docker/certs.d/$DNS_NAME/ca.crt -d '{
  "new_password": "<NEW PASSWORD HERE>",
  "old_password": "<OLD PASSWORD HERE>"
}'
```


## Cleanup the deployment
  - Deleting the TKG cluster: To delete the tkg cluster run the following on the bootstrap node:

    ```sh
        sudo su
        cd air-gapped
        ./delete-airgapped.sh
    ```

  - Deleting the TKG Bootstrap: Before deleting the bootstrap server make sure that the TKG Managements Clusters kubeconfig is saved somewhere or delete it [via the above section](#Deleteing-the-TKG-cluster).
    ```sh
        make destroy
    ```

  - Deleting the Harbor Server: To delete the harbor server run the following. Before doing so, ensure no TKG clusters are using the images hosted on it.

    ```sh
        make destroy-harbor
    ```
  
  - Use below command to delete both TKG bootstrap and harbor server at once

    ```sh
      make destroy-all
    ```

  **NOTE:** AMIs and load balancers created as part of deployment must be deleted manually. 

## Variables

|Name|Default|Description
|---|---|---|
|AMI_ID|tkg_ami_id variable from terraform|The AMI ID to deploy |
|REGISTRY_CA_FILENAME|ca.crt|The name of the ca file for the private registry|
|AWS_NODE_AZ|pulls in az_zone from terraform|The first aws availability zone to deploy to|
|CLUSTER_NAME|airgapped-mgmnt|The name of the tkg management cluster to deploy|
|AWS_SSH_KEY_NAME|Pulls from tfvars| The ssh key to use for tkg cluster must be RSA if STIG|
|AWS_REGION|Pulls from tfvars| The aws region to deploy tkg in|
|REGISTRY|Registry DNS name of the harbor instance|The DNS name of the docker registry only modify if user provided registry|
|REGISTRY_IP|IP of the harbor instance| IP Address of docker registry only modify if user provided registry|
|TKG_CUSTOM_IMAGE_REPOSITORY|$REGISTRY/tkg| The full docker registry project path to use for tkg images|
|CLUSTER_PLAN|dev|The cluster plan for tkg|
|ENABLE_AUDIT_LOGGING|true|Whether or not auditing is enabled on k8s|
|TKG_CUSTOM_COMPATABILITY_PATH|fips/tkg-compatability|The compatability path to use set to "" if non fips deploy|
|COMPLIANCE|stig|The compliance standard to follow set to stig, cis, or none|
|ENABLE_SERVING_CERTS|false|Whether or not to enable serving certificates on kubernetes|
|PROTECT_KERNEL_DEFAULTS|true|Whether or not to set --protect-kernel-defaults on kubelet only set to true with amis that allow it|
|AWS_VPC_ID|VPC ID of bootstrap|The VPC ID to deploy tkg into|
|AWS_PRIVATE_SUBNET_ID|When cluster plan is dev set to Subnet ID of bootstrap|USED for cluster plan dev. The private subnet id to deploy tkg into|
|AWS_NODE_AZ_1|unset|Required For Prod clusters set node availability zone 1|
|AWS_NODE_AZ_2|unset|Required For Prod clusters set node availability zone 2|
|AWS_PRIVATE_SUBNET_ID_1|unset|Required For Prod clusters private subnet 1|
|AWS_PRIVATE_SUBNET_ID_2|unset|Required For Prod clusters private subnet 2|
|CONTROL_PLANE_MACHINE_TYPE|unset|Required For Prod clusters. The aws machine type for control plane nodes in k8s|
|NODE_MACHINE_TYPE|unset|Required For Prod clusters. The aws machine type to use for worker nodes in k8s|
|SERVICE_CIDR|unset|Required For Prod clusters set kubernetes services cidr|
|CLUSTER_CIDR|unset|Required For Prod clusters set cluster cidr|
|HARBOR_HOSTNAME|harbor.system.tanzu|Hostname for harbor extension|
|PROMETHEUS_HOSTNAME|prometheus.system.tanzu|Hostname for prometheus extension|
|GRAFANA_HOSTNAME|grafana.system.tanzu| Hostname for grafana extension|
|HARBOR_PASSWORD|harbor123| Password for harbor extension|


## Using an Existing Registry

#### Prerequisites
Using an existing registry is possible as long as you follow the steps documented below.

1. Create a project within your registry called tkg so that images can be pushed to <REGISTRY NAME>/tkg
2. Make the tkg project publicly readable within the AirGapped environment. I.E. no authorization needed
3. Install the following onto your bootstrap machine
    - docker
    - aws
4. Run the following to upload your images to your registry needed for tkg. You will need about 15 GB of space on your bootstrap machine. It will also place your CA in locations needed to build them into your AMIs

    ```sh
      export REGISTRY=<Registry name>
      export REGISTRY_CA_PATH=<Full Path to ca file>
      export BUCKET_NAME=<S3 Bucket in airgapped env>
      export TKG_VERSION=<TKG Version>
      export TKR_VERSION=<TKR Version>
      export IMGPKG_USERNAME=<Registry Username>
      export IMGPKG_PASSWORD=<Registry Password>
      make upload-images
    ```

5. On your bastion VM where you will run 1click.sh you need to place any addtional certificate authorities into the below directories so they will be added to your amis:
    - `ami/tkg-bootstrap/roles/bootstrap/files/ca/` 
    - `ami/stig/roles/canonical-ubuntu-18.04-lts-stig-hardening/files/ca`

6. Additional Environment Variables:
    When using an existing registry the following variabled needs to be exported in additiion to the variables mentioned in [Required Environment Variables](#required-environment-variables) section.
    ```sh
      export REGISTRY=<DNS Name of your image registry>
      export USE_EXISTING_REGISTRY=true
      export REGISTRY_CA_FILENAME=<Name of your ca file>
    ```
    **Note: The name of your ca file is the filename only and not the filepath**

## Troubleshooting Tips
Here are some handy tips to get started with troubleshooting if your cluster will not come up.

  - Export your KUBECONFIG to the one provided for your bootstrap kind cluster when TKG starts.
    ```sh
      export KUBECONFIG=~/.kube-tkg/tmp/config_<UID>
    ```

  - You can use below commands for debugging prupose
    ```
      kubectl get events -A --sort-by='.metadata.creationTimestamp'

      kubectl get clusters -n tkg-system -o yaml
      kubectl get machinedeployments -n tkg-system -o yaml
      kubectl get awsclusters -n tkg-system -o yaml
      kubectl get kcp -n tkg-system -o yaml
      kubectl get machines -n tkg-system -o yaml
    ```

If you are extremely confident in a change you need to make to a yaml above, try running `kubectl edit <apiobject> -n tkg-system <object name>`. This will open up a vi session and allow you to edit the file. If you edit this you may want to ensure if it has an OwnerReferences section in the yaml, that it does not have something controlling it that will revert back your change.

