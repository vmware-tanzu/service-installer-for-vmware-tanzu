# CI/CD Pipelines for Service Installer for VMware Tanzu

CI/CD pipeline execution for Service Installer for VMware Tanzu is built upon Tekton framework. Tekton is a cloud-native solution for building CI/CD system which provides the pipelines for Day 0 deployment and Day 2  operations of Tanzu Kubernetes Grid 2.1.0.

## Features

- Bring up of Tanzu Kubernetes Grid based on Reference Architecture deployments.
- End-to-end Tanzu Kubernetes Grid deployment and configuration of AVI controller, management, shared services, and workload clusters, plug-ins, extensions
- End-to-end bring up of vSphere with Tanzu environment with enabling of WCP, supervisor cluster, and workload cluster with plug-ins and extensions 
- Day 2 operations support of Resize and Rescale
- Day 0 deployment and Day 2 operations for Tanzu Kubernetes Grid through Gitops


## Pipeline Support Matrix
### Day 0 Support Matrix
| Platform | vSphere with vDS            | vSphere with NSX-T |
|----------|-----------------------------|--------------------|
| Internet | TKG 2.1.0                   | TKG 2.1.0          |
| Internet | TKGs with vSphere >= 7.0 u2 | NA                 |
| Airgap   | Not supported               | Not supported      |

### Day 2 Support Matrix
|Sl.No  | Day2 Operations | Status              |
|-------|-----------------|---------------------|
| 1     | Rescale         | Supported           |
| 2     | Resize          | Supported           |

## ReadMe for Preparing CI/CD Pipelines 
1. [Prerequisites for CI/CD Pipelines For Tanzu Kubernetes Grid](./docs/prerequisites.md)
2. [Setup CI/CD infra and pipelines](./docs/preparefortektonpipelines.md)

## Executing Pipelines 
- [Run Day 0 Deployment Pipelines for Tanzu Kubernetes Grid](./docs/runday0.md)
- [Run Day 2 Operations Pipelines for Tanzu Kubernetes Grid](./docs/runday2.md)
- [Trigger Pipelines for Tanzu Kubernetes Grid through GitOps](./docs/triggerpipelinethrugitcommit.md)

## Monitoring Pipelines 
- [Monitor Pipeline Runs, Task Runs, and Pipelines](./docs/monitortekton.md)
