# Support for Service Installer for VMware Tanzu

This document is a practical guide to help understand the scope of VMware Support for customers using Service Installer for VMware Tanzu. This document is intended to provide a basic outline and cover some common concrete examples of services that are in and out of the scope of support provided by VMware. This is not a legal document, see the disclaimer at the bottom. For official documents, see [VMware Terms of Service](https://www.vmware.com/download/eula.html).

## Introduction

Service Installer for VMware Tanzu ( **SIVT** ) automates the deployment of the reference designs for Tanzu for Kubernetes Operations on various platforms.The purpose of this document is to provide clarity on what is and is not in scope of support for Service Installer for VMware Tanzu.

## In Scope

The following items are examples of tasks which are covered by VMware Support for SIVT.

| **Tasks** | **In Scope** |
| --- | --- |
| Debugging failures when deploying SIVT OVA | Yes |
| Bug reporting | Yes |
| Bug fix | Yes [1] |
| Enhancements requests | Yes [1] |
| Debugging failures when deploying VMware Tanzu products using SIVT product | Yes [2] |
| SIVT API, CLI and GUI support | Yes [3] |
| SIVT and Tekton integration | Yes [4] |
| SIVT and Harbor Integration | Yes [5] |

[1]  Bug fixes and enhancement requests are prioritized by VMware Engineering with input from VMware Support and our customers. There is no guarantee of an immediate fix and VMware Support retains the right to close out support tickets if a fix is not immediate.

[2]  For the exact list and versions of the product, see [Service Installer for VMware Tanzu Support matrix](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/2.1.0/service-installer/GUID-index.html#service-installer-for-vmware-tanzu-support-matrix-3).

[3] The API, CLI and GUI are supported however VMware support can not assist with writing or debugging custom code that leverages these components. Also, writing or troubleshooting custom wrappers modifications or automation are out of scope of support.

[4] Tekton use is only supported when using SIVT to deploy the documented products. Any custom applications or use of Tekton for user applications is outside the scope of support. Only VMware shipped SIVT pipelines are supported.

[5] Harbor usage is supported strictly when using to deploy the products mentioned in [Service Installer for VMware Tanzu Support matrix](https://docs.vmware.com/en/Service-Installer-for-VMware-Tanzu/2.1.0/service-installer/GUID-index.html#service-installer-for-vmware-tanzu-support-matrix-3). The Harbor instance of SIVT should not be used for external applications or as a standalone Harbor deployment to be used outside of SIVT.

## Out of Scope

The following items are examples of tasks which are not covered by VMware Support.

| **Tasks** | **In Scope** |
| --- | --- |
| Debugging custom code | No [1] |
| Modified code, scripts, pipelines and utilities shipped with SIVT | No [2] |
| Experimental features | No [3] |
| Assistance with Load/performance/stress testing of SIVT API and products deployed via SIVT | No |
| Customization using YTT overlays and debugging failures using customized overlays | No [4] |
| Modified terraform files shipped with SIVT | No [2] |
| Modified ansible configuration shipped with SIVT | No [2] |
| Modified Tekton resources (pipelies, tasks, and so on) | No [2] |
| Forks, development or customer built SIVT OVA and components using SIVT Github repository | No [5] |

[1] VMware Support cannot assist with reviewing customer or third-party application code or troubleshooting issues related to it. VMware can provide assistance through your solution engineer or account team representatives.

[2] Any modification to the code, scripts, terraform files, Tekton resources (pipelines, tasks etc), ansible templates/configurations or utilities shipped with SIVT will result in an unsupported deployment. VMware support recommends submitting enhancement requests if a particular functionality is needed.

[3] VMware Support provides assistance for beta/experiment features that are shipped in a generally available product. The goal in this case is to find and report bugs so that the feature works correctly when it is generally available. A fix for any bugs uncovered may not be available until the feature is generally available. Production and Severity 1 support are not available for beta/experimental features.

[4] VMware support cannot assist with any customization done to SIVT created deployments via ytt overlays. Any failures caused by these customized overlays are out of scope of support as SIVT currently does not support using overlays.

[5] Building SIVT OVA or any other components from the SIVT Github repository is out of scope of support. Any forks or branches that modify the SIVT code need to be merged and shipped as part of the official VMware product.
