## What's New

- Support for TKG 1.5.3 Federal Airgap deployment with STIG/FIPS compliant 
- Ability to deploy management and workload clusters
- Support for below extension deployments
	- Harbor
	- Prometheus
	- Grafana
	- Fluent-bit
	- Contour
	- Cert Manager
- Tarballs containing all the dependencies are made available to enable users to easily transfer all the required binaries to airgap environment
	- `tkg_tkr_1_5_3.tar` - Tarball containing all the TKG/TKR FIPS binaries - _To address manual installation usecase_ 
	- `tkg_sivt_aws_federal_1_5_3.tar` - Tarball containing all the TKG/TKR FIPS binaries, harbor, deployment dependencies as well as automation scripts
- Support for TKG deployment with Ubuntu 18.0.4 (Ubuntu OS image is STIG/FIPS compliant + TKG FIPS enabled)
- Support for TKG deployment with 'Amazon Linux 2' (AL2 vanilla OS image + TKG FIPS enabled) 
- Cleanup feature - Ability to destroy the deployments performed by SIVT and start from scratch.
- GP2 volume support for Amazon Linux 2 and GP3 volume support for Ubuntu 18.0.4 
- Enhanced pre-checks for the user inputs and handle failures gracefully
- Support user-friendly error messages and debug messages
- Parameterizations to do deployment of extensions and clusters
- Make targets are modularised into independently deployable components

## Important Links
- Download dependency tarballs from https://buildweb.eng.vmware.com/
- Refer [git repository](https://gitlab.eng.vmware.com/core-build/sivt-aws-federal/) for automation code

## Known Issue
- TKG deployment with ubuntu OS image having FIPS_ENABLED flag set to FALSE is not supported. 
- TKG deployment with 'Amazon Linux 2' OS image having FIPS_ENABLED flag set to FALSE is not supported.
