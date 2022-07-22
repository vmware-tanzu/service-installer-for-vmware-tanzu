<!--
# Copyright 2021 VMware, Inc
# SPDX-License-Identifier: BSD-2-Clause
-->
# README

Service Installer for VMware Tanzu (SIVT) enables users to install Tanzu for Kubernetes Operations on the AWS environment. This project helps build an architecture in AWS that corresponds to following reference architecture
- Non-Airgap: [Tanzu for Kubernetes Operations Reference Design](https://docs.vmware.com/en/VMware-Tanzu/services/tanzu-reference-architecture/GUID-reference-designs-tko-on-aws.html).
- Airgap: RA is yet to be published

Service Installer for VMware Tanzu provides automation of Tanzu Kubernetes Grid deployment on the following two AWS environments:

- Federal Air-gapped
- Non Air-gapped

**Note:** In this documentation set, a federal air-gapped environment refers to an internet-restricted environment that is compliant with standards such as FIPS and STIG.

## Tanzu for Kubernetes Operations Deployment on Federal Air-Gapped AWS

You can use Service Installer for VMware Tanzu for STIG hardened and FIPS compliant Tanzu for Kubernetes Operations deployment on a federal air-gapped (internet-restricted) AWS environment. Service Installer for VMware Tanzu provides Terraform automation scripts and dependent binaries in a TAR file that can be easily transferred to an air-gapped environment, which can be used to deploy Tanzu for Kubernetes Operations.

For air-gapped deployment, Service Installer for VMware Tanzu supports CloudFormation stack configuration along with Harbor installation for loading dependencies.

Service Installer for VMware Tanzu deploys:

- Tanzu Kubernetes Grid management and workload clusters
- User-managed packages such as Contour, Harbor, Prometheus, Grafana, FluentBit, and Pinniped with LDAP or OIDC identity management

For air-gapped deployment, Service Installer for VMware Tanzu supports Ubuntu and vanilla Amazon Linux 2 based cluster nodes.

For detailed information, see Tanzu Kubernetes Grid on [Federal Air-gapped AWS Deployment Guide](../docs/product/release/AWS%20-%20Federal%20Airgap/AWSFederalAirgap-DeploymentGuide.md).

## Tanzu for Kubernetes Operations Deployment on Non Air-Gapped AWS

You can use Service Installer for VMware Tanzu for STIG hardened and FIPS compliant Tanzu for Kubernetes Operations deployment on a non air-gapped (internet-connected) AWS environment. For non air-gapped deployment, Service Installer for VMware Tanzu supports VPCs creation, transit gateway, and associated networking (subnets) creation along with CloudFormation stack configuration.

Service Installer for VMware Tanzu deploys:

- Tanzu Kubernetes Grid management and workload clusters on two VPCs
- User-managed packages such as Contour, Harbor, Prometheus, Grafana, Fluent Bit, and Pinniped with LDAP or OIDC identity management
- Integration of management and workload cluster with SaaS services such as Tanzu Mission Control (TMC), Tanzu Service Mesh (TSM), and Tanzu Observability (TO)

For non air-gapped deployment, Service Installer for VMware Tanzu supports only Ubuntu based cluster nodes. Service Installer for VMware Tanzu supports both compliant and non-compliant deployments in a non air-gapped environment.

### Compliant Deployment

Compliant deployment enables users to deploy Tanzu Kubernetes Grid according to FIPS and STIG security standards. This deployment process is configured to deploy FIPS compliant Tanzu Kubernetes Grid master and worker nodes. Following is the list of compliant components used:

- FIPS compliant and STIG hardened Ubuntu (18.04) base OS for Tanzu Kubernetes Grid cluster nodes
- FIPS compliant Tanzu Kubernetes Grid (TKG) / Tanzu Kubernetes releases (TKr) binaries
- STIG/CIS hardened Tanzu Kubernetes Grid using overlays

### Non-compliant deployment

This Tanzu Kubernetes Grid deployment process makes use of vanilla Tanzu Kubernetes Grid images for installation and deploys non-FIPS and non-STIG hardened Tanzu Kubernetes Grid master and worker nodes.

For detailed information, see Tanzu Kubernetes Grid on [Non Air-gapped AWS Deployment Guide](../docs/product/release/AWS%20-%20Non%20Airgap/AWSNonAirgap-DeploymentGuide.md).
