# Service Installer for VMware Tanzu Support Process

## Definitions

* **Service Installer for VMware Tanzu member** - is a person who is an active contributor and with
  write access to the `service-installer-for-vmware-tanzu` repo.
* **Critical urgent issue** - is an issue that severely impacts the use of the
  software and has no workarounds. This kind of issue should be labeled with
  [severity-1](severity-definitions.md#severity-1) label.

## Communication channel

Our team is reachable on slack channel `service-installer-assist-external`. It can be used for any querries/clarifications, etc. 

## Weekly rotation

The Service Installer for VMware Tanzu members use a weekly rotation to manage community support.
Each week, a different member is the point person for triaging the new issues
and guiding the issues to the best state to be tackled.

The point person is not expected to solve every critical(severity-1) issue or
be on-call 24x7. Instead, they will communicate expectations for the critical
urgent issues to the community and ensure the issues are in the best position
to be addressed.

The point person is not expected to be involved with normal non-critical
priority(other than severity-1) issues.

## Start of Week

The support schedule will be provided in advance to ensure everyone knows when their support
week is occurring.

The schedule will consist of members who provide a week of their expertise to
ensure new issues are labeled appropriately.

They also work closely with the community to ensure the issue is properly
detailed and includes steps for reproducing the issue, if appropriate.

Point people are responsible for ensuring they are active and managing the
issue backlog during their scheduled week.

## During the Week

The point person will monitor: 

* New issues raised will be labelled as `needs-triage`.
* While bug being investigated, it will be labelled as `investigating`. 
* If more information is required it will be labelled as `needs-more-info`.
* Issues which needs immediate attension will be labelled as `severity-1`.

### GitHub issue flow

Generally speaking, new GitHub issues will fall into one of several categories.
The point person will use the following process for each issue:

* Feature request
  * Label the issue with `feature/enhancement`.
  * Determine the area of the Service Installer for VMware Tanzu product the issue belongs to and add appropriate
    [module](https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/labels?q=module) label.
  * Remove `needs-triage` label.
* Bug
  * Label the issue with `bug`.
  * Determine the area of the SIVT product the issue belongs to and add appropriate
    [module](https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/labels?q=module) label.
  * If the issue is critical urgent, it should be labeled as `severity-1`.
  * Remove `needs-triage` label.
* User question/problem that does not fall into one of the previous categories
  * Assign the issue to yourself.
  * When you start investigating/responding, label the issue with `investigating`.
  * Add context for both the user and future support people.
  * Use the `need_more_info` label to indicate an issue is waiting for
  information from the user. If you do not get a response in 20 days then close
  the issue with an appropriate comment.
  * If you resolve the issue, add the resolution as a comment on the issue and
  close it.
  * If the issue ends up being a feature request or a bug, update the labels
  and follow the appropriate process for it.

## End of Week

The point person will ensure all GitHub issues worked on during the week are
labeled with `investigating` and `need_more_info` (if appropriate), and have
updated comments, so the next person can pick them up.
