## Purpose

This project is designed to build a Tanzu Application Platform 1.2 multicluster instances on AWS EKS that corresponds to the [Tanzu Application Platform Reference Design](https://github.com/vmware-tanzu-labs/tanzu-validated-solutions/blob/main/src/reference-designs/tap-architecture-planning.md) . 

This is a 2-steps automation with minimum inputs into config files. 

* **Step 1** to create all aws resources for tap like VPC , 4 eks clusters and associated security and Iam group , node etc
* **Step 2** to install tap profiles into eks clusters.

Specifically, this automation will build:
- an AWS VPC (internet facing)
- 4 EKS clusters named as tap-view , tap-run , tap-build,tap-iterate and associated security IAM roles and groups and nodes into aws. 
- Install Tanzu Application Platform profiles such as view,run,build,iterate on Respective eks clusters. 
- Install Tanzu Application Platform sample demo app. 

## AWS resources matrix 

 **Resource Name** | **Size/Number**  
 -----|-----
 VPC | 1
 Subnets | 2 private , 2 public
 VPC cidr | 10.0.0.0/16
 EKS clusters | 4
 Nodes per eks cluster | Nodes : 3, Node Size : t2.xlarge , Storage : 100GB disk size
## Prerequisite 

Following CLI must be set up into the jumpbox or the execution machine or terminal. 
   * terraform cli 
   * aws cli 


## Prepare the Environment

First, be sure that your AWS access credentials are available within your environment.

### Set aws env variables.
 
```bash
export AWS_ACCESS_KEY_ID=<your AWS access key>
export AWS_SECRET_ACCESS_KEY=<your AWS secret access key>
export AWS_REGION=us-east-1  # ensure the region is set correctly. this must agree with what you set in the tf files below.
```

### Prepare Terraform

* Initialize Terraform by executing `terraform init`
* Set required variables in `terraform.tfvars`
  * `availability_zones_count` Should be set to number of subnets(private/public) you want to create within vpc.
  * `vpc_cidr` Should be set cidr for vpc. 
  * `aws_region` Should be set to your AWS region
  * `subnet_cidr_bits` Should be set cidr bits for vpc.

* Execute Terraform apply by running `terraform apply`

### Add TAP configuration mandatory details 

Add the following details into  the `tap/aws/tap-scripts/var.conf` file to fulfill TAP prerequisites. Examples and default values are given in the sample below. All fields are mandatory. They can't be left blank and must be filled before executing the `tap-index.sh` script. Refer to the sample config file below. 
```

TAP_DEV_NAMESPACE="default"
os=<terminal os as m or l.  m for Mac , l for linux/ubuntu>
INSTALL_REGISTRY_HOSTNAME=registry.tanzu.vmware.com
INSTALL_BUNDLE=registry.tanzu.vmware.com/tanzu-cluster-essentials/cluster-essentials-bundle@sha256:e00f33b92d418f49b1af79f42cb13d6765f1c8c731f4528dfff8343af042dc3e
DOCKERHUB_REGISTRY_URL=index.docker.io
TAP_VERSION=1.2.0
TAP_NAMESPACE="tap-install"
tanzu_net_reg_user=<Provide tanzu net user>
tanzu_net_reg_password=<Provide tanzu net password>
tanzu_net_api_token=<Provide tanzu net token>
aws_region=<aws region where tap eks clusters created>
registry_url=<Provide user registry url>
registry_user=<Provide user registry userid>
registry_password=<Provide user registry password>
tap_run_cnrs_domain=<run cluster sub domain example like : run.ab-tap.customer0.io >
alv_domain=<app live view  sub domain example like :alv.ab-tap.customer0.io >
TAP_RUN_CLUSTER_NAME="tap-run"
TAP_GITHUB_TOKEN=< git hub token>
tap_view_app_domain=<view  cluster sub domain example like :view.ab-tap.customer0.io>
tap_git_catalog_url=<git catelog url example like : https://github.com/sendjainabhi/tap/blob/main/catalog-info.yaml>

#tap demo app properties
TAP_APP_NAME="tap-demo"
TAP_APP_GIT_URL="https://github.com/sample-accelerators/spring-petclinic"

```
## Install TAP
### Build EKS clusters 
Run following steps to build AWS resources for TAP. 

*  Run `terraform plan` from the `tap/aws/terraform` directory and review all AWS resources.

* Run `terraform apply` to build AWS resources.

### Install TAP multi clusters (Run/View/Build/Iterate)

Execute following steps to Install TAP multi clusters (Run/View/Build/Iterate)
```

#Step 1 - Add execute permission to the tap-index.sh file.
chmod +x tap/aws/tap-scripts/tap-index.sh

#Step 2 - Run tap-index.sh. 
./tap/aws/tap-scripts/tap-index.sh


```
**Note** - 

 Pick an external ip from service output from eks view and run clusters and configure DNS wildcard records in your dns server for view and run cluster
 * **Example view cluster** - *.view.customer0.io ==> <ingress external ip/cname>
 * **Example run cluster** - *.run.customer0.io ==> <ingress external ip/cname>
  * **Example iterate cluster** - *.iter.customer0.io ==> <ingress external ip/cname>
### TAP single profile(Run/View/Build/Iterate) installation 

You can install only any single TAP profile(Run/View/Build/Iterate) as well 

* **To install View profile only , execute following step** 

```

#Step 1 - Add execute permission to the tap-view.sh file.
chmod +x tap/aws/tap-scripts/tap-view.sh

#Step 2 - Run tap-view.sh. 
./tap/aws/tap-scripts/tap-view.sh


```

* **To install Run profile only , execute following step** 

```

#Step 1 - Add execute permission to the tap-run.sh file.
chmod +x tap/aws/tap-scripts/tap-run.sh

#Step 2 - Run tap-run.sh. 
./tap/aws/tap-scripts/tap-run.sh


```

* **To install build profile only , execute following step** 

```

#Step 1 - Add execute permission to the tap-build.sh file.
chmod +x tap/aws/tap-scripts/tap-build.sh

#Step 2 - Run tap-build.sh. 
./tap/aws/tap-scripts/tap-build.sh


```


* **To install iterate profile only , execute following step** 

```

#Step 1 - Add execute permission to the tap-iterate.sh file.
chmod +x tap/aws/tap-scripts/tap-iterate.sh

#Step 2 - Run tap-iterate.sh. 
./tap/aws/tap-scripts/tap-iterate.sh


```

### TAP scripts for specific tasks

If you got stuck in any specific stage and need to resume installation, you can use the following scripts. Log in to respective EKS cluster before running these scripts.

* **Install tanzu cli** - Run `./tap/aws/tap-scripts/tanzu-cli-setup.sh`

* **Install tanzu essentials** - Run `./tap/aws/tap-scripts/tanzu-essential-setup.sh`  

* **Setup TAP repository** - Run `./tap/aws/tap-scripts/tanzu-repo.sh`  

* **Install TAP run profile packages** - Run `./tap/aws/tap-scripts/tanzu-run-profile.sh`  

* **Install TAP build profile packages** - Run `./tap/aws/tap-scripts/tanzu-build-profile.sh`

* **Install TAP view profile packages** - Run `./tap/aws/tap-scripts/tanzu-view-profile.sh`

## Clean up

### Delete TAP instances from all eks clusters 

Follow below steps: 
```

1. Run chmod +x tap/aws/tap-scripts/tap-delete/tap-delete.sh
2. Run ./tap/aws/tap-scripts/tap-delete/tap-delete.sh
 
# Delete single tap cluster instance 
1. Log in to eks clusters(view/run/build/iterate) using kubeconfig where you want to delete tap.
2. Run chmod +x tap/aws/tap-scripts/tap-delete/tap-delete-single-cluster.sh
3. Run ./tap/aws/tap-scripts/tap-delete/tap-delete-single-cluster.sh

```
### Delete EKS clusters instances from eks cluster 
Run `terraform destroy` to delete all AWS resources created by terraform. In some instances, it is possible that `terraform destroy` will not be able to clean up after a failed Tanzu install. Especially in situations where the management cluster only comes partially up for some reason. In this case, you can recursively delete the VPCs that failed to get destroyed and use the tags "CreatedBy: Arcas" to find anything that was generated by terraform.