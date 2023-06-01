# ubuntu_1804_STIG

Cookbook to automate STIG implementation for Ubuntu 1804

## Cookbook variables:

Comnpensating controls may exist that satisfy the STIG requirement for a security measure.  
Variables definded in [vars.yml](vars/main.yml) allow skipping package insatallation where compensating controls exist.

|Name|Default|Description|
|----|:-------:|-----------|
|`install_fips`| `yes`|Install FIPS certified kernel, openssh, openssl and strongswan modules. Requires `UBUNTU_ADVANTAGE_PASSWORD` and `UBUNTU_ADVANTAGE_PASSWORD_UPDATES` variables to be set. There are **no compensating control** from FIPS STIG requirement|
|`install_aide`| `yes`|`aide` is an open source host based file and directory integrity checker. `install_aide` can be set to `no` if any other integrity checker (e.g. Tripwire) is installed on the VM instead of being baked into the image|
|`install_chrony`| `yes`| `chrony` provides fast and accurate time synchronization. `install_chrony` can be set to `no` if any other time synching package (e.g. `timesyncd`) is used.|
|`install_protect_kernel_defaults`| `yes` | Set `sysctl` settings to support `--protect-kernel-defaults` flag in `kubelet` |
|`UBUNTU_ADVANTAGE_PASSWORD`| |Env variable in `<USERNAME>:<PASSWORD>` format required to access Ubunutu `FIPS (ppa:ubuntu-advantage/fips)` private Personal Package Archive(ppa). Required if `install_fips` is set to `yes`|
|`UBUNTU_ADVANTAGE_PASSWORD_UPDATES`| |Env variable in `<USERNAME>:<PASSWORD>` format required to access Ubunutu `FIPS Updates (ppa:ubuntu-advantage/fips-updates)` private Personal Package Archive(ppa). Required if `install_fips` is set to `yes`|


## Cloud provider specific tasks:
This repo has been tested on AWS only. 
For setting [cloud provider specific modules](tasks/V-219151.yml#L35-43) refer to https://security-certs.docs.ubuntu.com/en/fips-cloud-containers

## Exceptions

|	VID |	Title	|	Impact	|	Exception	|
|-----|--------|---------|----------|
|	V-219150	|	Ubuntu operating systems handling data requiring data at rest protections must employ cryptographic mechanisms to prevent unauthorized disclosure and modification of the information at rest.	|	moderate	|	Disk encryption is handled by the IaaS.	|
|	V-219153	|	Ubuntu operating systems handling data requiring data at rest protections must employ cryptographic mechanisms to prevent unauthorized disclosure and modification of the information at rest.	|	low	|	Integrate with Enterprise SEIM	|
|	V-219154	|	The Ubuntu operating system must have a crontab script running weekly to off-load audit events of standalone systems.	|	low	|	Integrate with Enterprise SEIM	|
|	V-219159	|	The Ubuntu operating system must deploy Endpoint Security for Linux Threat Prevention (ENSLTP).	|	moderate	|	Integrate with Enterprise Endpoint protectiom	|
|	V-219162	|	The Ubuntu operating system audit event multiplexor must be configured to off-load audit logs onto a different system or storage media from the system being audited.	|	low	|	Integrate with Enterprise SEIM	|
|	V-219163	|	The Ubuntu operating system must be configured such that Pluggable Authentication Module (PAM) prohibits the use of cached authentications after one day.	|	low	|	Access to cluster VMs is allowed only via the bastion. Cluster VMs do not support smart card authentication	|
|	V-219183	|	The Ubuntu operating system must allow the use of a temporary password for system logons with an immediate change to a permanent password.	|	moderate	|	Manually verify if a policy exists to ensure that a method exists to force temporary users to change their password upon next login	|
|	V-219185	|	The Ubuntu operating system must require users to re-authenticate for privilege escalation and changing roles.	|	moderate	|	`ubuntu` user is required for ami creation and to run cloud-init	|
|	V-219187	|	The Ubuntu operating system must set a sticky bit on all public directories to prevent unauthorized and unintended information transferred via shared system resources.	|	moderate	|	Github issue created to fix this issue. https://github.com/antrea-io/antrea/issues/2300	|
|	V-219188	|	The Ubuntu operating system must generate error messages that provide information necessary for corrective actions without revealing information that could be exploited by adversaries.	|	moderate	|	Github issue created to fix this issue. https://github.com/antrea-io/antrea/issues/2300	|
|	V-219315	|	The Ubuntu operating system, for PKI-based authentication, must validate certificates by constructing a certification path (which includes status information) to an accepted trust anchor.	|	moderate	|	Access to cluster VMs is allowed only via the bastion. Cluster VMs do not support smart card authentication	|
|	V-219316	|	The Ubuntu operating system must map the authenticated identity to the user or group account for PKI-based authentication.	|	high	|	Access to cluster VMs is allowed only via the bastion. Cluster VMs do not support smart card authentication	|
|	V-219317	|	The Ubuntu operating system must implement smart card logins for multifactor authentication for access to accounts.	|	moderate	|	Access to cluster VMs is allowed only via the bastion. Cluster VMs do not support smart card authentication	|
|	V-219320	|	The Ubuntu operating system must implement certificate status checking for multifactor authentication.	|	moderate	|	Access to cluster VMs is allowed only via the bastion. Cluster VMs do not support smart card authentication	|
|	V-219322	|	Pam_Apparmor must be configured to allow system administrators to pass information to any other Ubuntu operating system administrator or user, change security attributes, and to confine all non-privileged users from executing functions to include disabling, circumventing, or altering implemented security safeguards/countermeasures.	|	low	|	`snap.amazon-ssm-agent.amazon-ssm-agent` profile is a known issue. https://github.com/aws/amazon-ssm-agent/issues/108	|
|	V-219324	|	The Apparmor module must be configured to employ a deny-all, permit-by-exception policy to allow the execution of authorized software programs and limit the ability of non-privileged users to grant other users direct access to the contents of their home directories/folders.	|	moderate	|	Manual verification. Exception for `snap.amazon-ssm-agent.amazon-ssm-agent`	|
|	V-219327	|	The Ubuntu operating system must automatically remove or disable emergency accounts after 72 hours.	|	low	|	Manual verification. Check if emergency must terminate the account after a 72 hour time period.	|
|	V-219334	|	The Ubuntu operating system must be configured to prohibit or restrict the use of functions, ports, protocols, and/or services, as defined in the PPSM CAL and vulnerability assessments.	|	moderate	|	Network protection is provided by VPC for perimeter protection and iptables for container networks	|
|	V-219340	|	The Ubuntu operating system must configure the uncomplicated firewall to rate-limit impacted network interfaces.	|	moderate	|	Network protection is provided by VPC for perimeter protection and iptables for container networks	|
