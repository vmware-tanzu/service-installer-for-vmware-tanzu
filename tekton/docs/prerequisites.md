# Prerequisites for Tekton Pipelines For Tanzu Kubernetes Grid

Tekton pipeline execution for Tanzu Kubernetes Grid requires the following:

- Linux machine for creating kind cluster
  - Photon OS or Service Installer for VMware Tanzu VM can also be used   
- GitLab or GitHub repository for storing infrastructure and setup configuration files 
- Docker login credentials
- Marketplace token
- Install Python-Pip dependencies
  - pip install retry
  - pip install paramkio
- Install `tkn` CLI:
  - Download `tkn` CLI from:
    curl -LO https://github.com/tektoncd/cli/releases/download/v0.29.1/tkn_0.29.1_Linux_x86_64.tar.gz
  - Untar the downloaded zip package to bin:
    sudo tar xvzf tkn_0.29.1_Linux_x86_64.tar.gz -C /usr/local/bin/ tkn
  - Verify the `tkn` CLI is installed
    tkn version


[Back to Main](../README.md)
