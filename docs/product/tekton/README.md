# Tekton Pipelines for Tanzu Kubernetes Grid

Tekton is a cloud-native solution for building CI/CD system which provides the pipelines for Day-0 deployment and Day-2 operations of Tanzu Kubernetes Grid 1.5.x for a vSphere backed environment.

## Features

- Bring up of reference architecture based Tanzu Kubernetes Grid environment on vSphere
- End-to-end Tanzu Kubernetes Grid deployment and configuration of AVI controller, management, shared services, and workload clusters, plug-ins, extensions
- End-to-end bring up of vSphere with Tanzu environment with enabling of WCP, supervisor cluster, and workload cluster with plug-ins and extensions 
- Rescale and resize Day-2 operations
- Day-2 operations of Tanzu Kubernetes Grid upgrade from 1.5.x to 1.5.4 with packages and extensions
- Day-0 and Day-2 operations for Tanzu Kubernetes Grid for Internet-restricted environments


## Deploy on Internet Connected Environment
- [Prerequisites for Tekton Pipelines For Tanzu Kubernetes Grid](./prerequisites.md)
- [Prepare to Run Tekton Pipelines for Tanzu Kubernetes Grid](./preparefortektonpipelines.md)
- [Run Day-0 Tekton Pipelines for Tanzu Kubernetes Grid](./runday0.md)
- [Run Day-2 Tekton Pipelines for Tanzu Kubernetes Grid](./runday2.md)
- [Monitor Tekton Pipeline Runs, Task Runs, and Pipelines](./monitortekton.md)
- [Trigger Tekton Pipelines for Tanzu Kubernetes Grid through Git Commits](./triggerpipelinethrugitcommit.md)

## Deploy on Internet Restricted Environment
- [Run Day-0 Tekton Pipelines for Tanzu Kubernetes Grid Internet Restricted Environments](./runday0_airgapped.md)
- [Run Day-2 Tekton Pipelines for Tanzu Kubernetes Grid Internet Restricted Environments](./runday2_airgapped.md)
- [Monitor Tekton Pipeline Runs, Task Runs, and Pipelines](./monitortekton.md)
