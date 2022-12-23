# STIG hardened Ubuntu 18.04 NodeOS image


  - (Optional) Set local registry. If not set, This defaults to `us.gcr.io/$(gcloud config get-value project)`
    ```
    export REGISTRY=<local registry>
    ```

  - Set FIPS PPA credentials
    - `export UBUNTU_ADVANTAGE_PASSWORD=<user:password>`
    - `export UBUNTU_ADVANTAGE_PASSWORD_UPDATES=<user:password>`
## AWS
  - Set AWS environment variables
    - `export AWS_ACCESS_KEY_ID=<access_key_id>`
    - `export AWS_SECRET_ACCESS_KEY=<secret_access_key>`
  - Based on your image building environemnt
    - Online image builder
      
      - Update `aws_region`, `ami_regions`, and `subnet_id` in [aws_settings.json](aws_settings.json)
      -  
        ```
        make docker-aws
        ```
      
    - Offline image builder **(WIP)**
      - Set offline registry.
        ```
        export OFFLINE_REGISTRY=<local registry>
        ```
      - Set name of the bucket containing all the offline dependencies.
        ```
        export BUCKET_NAME=<bucket name>
        ```
      - Update `aws_region`, `ami_regions`, and `subnet_id` in [aws_settings_offline.json](aws_settings_offline.json)
      - Update  urls in `tkg_offline.json`
      - Set path to your debian repo source in [local.list](local.list). The repo should contain all deb packages required by base image-buider and stig hardening role(inclusing the fips ppa debs). This repo should be accessible by the EC2 instance created by packer as a part of AMI creation. 
      -
        ```
        make docker-aws-offline
        ```

## vSphere
  - Update [vsphere_settings.json](vsphere_settings.json) and [vsphere_credentials.json](vsphere_credentials.json)
  - metadata.json contains the version name that will be referenced in the TKG BOM file, it defaults to v1.20.5+vmware.2-fips.0
  -
    ```
    make docker-vsphere
    ```

## Azure
  - (Optional)Create imagebuilder tenant.
    - `az ad sp create-for-rbac --name imagebuilder --role owner`
  - Set Azure environment variables
    - `export AZURE_SUBSCRIPTION_ID=<azure_subscription_id>`
    - `export AZURE_TENANT_ID=<azure_tenant_id>`
    - `export AZURE_CLIENT_ID=<azure_client_id>`
    - `export AZURE_CLIENT_SECRET=<azure_client_secret>`
  - Update [azure_settings.json](azure_settings.json)
    ```
    make docker-azure
    ```

### Verify STIG hardning
  - Install [CINC](https://cinc.sh/) (OSS Chef Software)

    `curl https://omnitruck.cinc.sh/install.sh | bash`
  - Create a VM using the shiny mew AMI
  -
    ```
    git clone git@github.com:vmware/dod-compliance-and-automation.git >> ~/workspace/dod-compliance-and-automation

    cd ~/workspace/dod-compliance-and-automation/ubuntu/18.04/inspec

    inspec exec canonical-ubuntu-18.04-lts-stig-baseline  -t ssh://ubuntu@<VM_EXTERNAL_IP>  --sudo  -i <PATH_TOSSH_KEY> --reporter=cli json:/tmp/output.json
    ```

