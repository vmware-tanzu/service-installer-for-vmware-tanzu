# Contributing

## Table of Contents

* [Contributing](#contributing)
* [Communication](#communication)
* [Propose a Change](#propose-a-change)
* [Contribute a Change](#contribute-a-change)
  * [Commit Messages](#commit-messages)
* [Pull Request Process](#pull-request-process)
  * [Creating a Pull Request](#creating-a-pull-request)
  * [Getting your Pull Request Reviewed, Approved, and Merged](#getting-your-pull-request-reviewed-approved-and-merged)
  * [Merging a Pull Request](#merging-a-pull-request)
* [Contribution Flow](#contribution-flow)
  * [Staying In Sync With Upstream](#staying-in-sync-with-upstream)
  * [Updating pull requests](#updating-pull-requests)  
* [Developer Certificate of Origin](#developer-certificate-of-origin)

--------------

We’d love to accept your patches and contributions to this project. You'll need
to follow these guidelines in order to make a contribution. Most contributions are submitted as Pull Requests (PRs).

## Communication

Communicate with other members of the community through the following channels:
* Slack - Use the 'service-installer-assist-external' Slack channel.
* Github issue - Use the Github Issues area for asynchronous communication.

## Propose a Change

If you'd like to propose a change or report a bug, begin by searching through
open issues in Github to see if anyone has already submitted a  similar issue.
If there's a similar issue, provide additional information in a comment on that
issue instead of raising a new issue.

If the issue hasn't been proposed or reported, submit a new issue, filling in
the supplied template with as much detail as you can. Submitting an issue in
Github gives the project maintainers and community members an opportunity to
provide high-level feedback early and possibly avoid unnecessary effort. This is
particularly important if the proposal will involve significant effort to
implement.

## Contribute a Change

Pull requests (PRs) are welcome for all changes, whether they are for improving
documentation, fixing a bug, adding or enhancing a feature, or merely correcting
a typo.

If your PR will change the behavior or functionality of the SIVT software, you'll need to build and test your changes before
submitting your PR.

When adding new functionality or fixing bugs, add appropriate test coverage
where possible. Different parts of the code base have different testing strategies and patterns, some of which may be in flux at any time. Consider
commenting on the issue to seek input or opening a draft PR to seek
feedback on testing approaches for a particular change.

### Commit Messages

* Each commit message should include a one-line (maximum 72 chars) title that summarizes the change.
* Unless the change is so small that it can be adequately explained in the title, the commit message should also include a body with more detailed explanatory text, wrapped to 72 characters.
* It is critical to separate the commit message summary from the body with a blank line.
* Write commit messages using the imperative: "Implement feature" and not "Implemented feature".

## Pull Request Process

### Creating a Pull Request

* Before submitting a pull request, be sure to verify the changes on your local system.  
* When you can, make small commits and pull requests rather than large ones. Small changes are easier to digest and get reviewed faster.  
* If you find that your change is getting large, break up your PR into small, logical commits.
* Consider breaking up large PRs into smaller PRs, if the PRS are independent of each other.
* Write clear, understandable commit messages. See [Commit
 Messages](#commit-messages) section for guidelines.
 * Bulleted points are fine. Use a hyphen or asterisk for the bullet, followed by a single space.
 * Use the pull request template to provide a complete description of the change.
The template captures important information that streamlines the review
process, ensures your changes are documented in release notes, and updates
related issues. Your pull request description and any discussion that follows
is a contribution in itself that helps the community and future contributors
understand the project better.
 * Pull requests *should* reference an existing issue and include either a `Fixes #NNNN`
or `Updates #NNNN` comment. A `Fixes` comment closes the associated
issue, and an `Updates` comment links the PR to it.

### Getting your Pull Request Reviewed, Approved, and Merged

Before a PR can be merged, the following steps must take place:

* At least two reviewers have signed off on it and all the review comments are resolved.
* The `ok-to-merge` label has been applied.
* A [CODEOWNER](https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu/blob/main/CODEOWNERS.md) has approved all changed files.

While the sequence of these steps may vary, open PRs typically undergo the following steps:

1. A review is automatically requested from CODEOWNERS.
2. An assignee is added to pull request to ensure it gets proper attention throughout the process.
   In most cases. one of the CODEOWNERS will assign themselves to the PR, but they may choose to delegate it to someone else.
3. Triage evaluates the pull request to ensure that it is generally aligned with product goals and does not conflict with current milestones. If this is the case, triage adds the `ok-to-merge` label. If not, they may add a `do-not-merge/*` label and an explanatory comment.
4. The assignee may request others to do an initial review. Anyone else may also review.
5. Reviewers leave feedback.
6. The contributor updates the PR to address all feedback.
7. The requested reviewer approves the PR.
8. The assignee approves the PR.
9. The assignee merges the PR or, if necessary, requests another member to merge it.

During the review process, reviewers and contributors are encouraged to communicate with each other directly.

Throughout the process, and until the PR is merged, the following should be transparent to the contributor:

* Has the pull request been assigned to anyone yet?
* Has the pull request been labeled with `ok-to-merge` or `do-not-merge`?
* Has someone been requested to review the pull request?
* Has the PR been approved by a reviewer?
* Has the PR been approved by the approver?

If any of these statuses is unclear, and there has been no new activity for 2-3 days,
the contributor is encouraged to seek further information by commenting and
mentioning the assignee or the review has been unresponsive.

### Merging a Pull Request

When merging PRs, maintainers should use the the [Squash and merge](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-request-merges#squash-and-merge-your-pull-request-commits) option.
This option is preferable for two reasons:
First, it causes GitHub to insert the pull request number in the commit subject
which makes it easier to track which commit includes the PR changes.
Second, it creates a one-to-one correspondence between pull requests and commits, which makes it easier to manage reverting changes.

At the discretion of a maintainer, PRs with multiple commits can be merged
with the [Rebase and merge](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-request-merges#rebase-and-merge-your-pull-request-commits)
option. Merging pull requests with multiple commits can make sense in cases
where a change involves code generation or mechanical changes that can be
cleanly separated from semantic changes. The maintainer should review commit
messages for each commit and make sure that each commit builds and passes
tests.

## Contribution Flow

This is a rough outline of what a contributor's workflow looks like:

- Create a topic branch from where you want to base your work
- Make commits of logical units
- Make sure your commit messages are in the proper format (see below)
- Push your changes to a topic branch in your fork of the repository
- Submit a pull request

Example:

``` shell
git remote add upstream https://github.com/vmware-tanzu/service-installer-for-vmware-tanzu.git
git checkout -b my-new-feature main
git commit -a
git push origin my-new-feature
```

### Staying In Sync With Upstream

When your branch gets out of sync with the vmware-tanzu/main branch, use the following to update:

``` shell
git checkout my-new-feature
git fetch -a
git pull --rebase upstream main
git push --force-with-lease origin my-new-feature
```

### Updating pull requests

If your PR fails to pass CI or needs changes based on code review, you'll most likely want to squash these changes into
existing commits.

If your pull request contains a single commit or your changes are related to the most recent commit, you can simply
amend the commit.

``` shell
git add .
git commit --amend
git push --force-with-lease origin my-new-feature
```

If you need to squash changes into an earlier commit, you can use:

``` shell
git add .
git commit --fixup <commit>
git rebase -i --autosquash main
git push --force-with-lease origin my-new-feature
```

Be sure to add a comment to the PR indicating your new changes are ready to review, as GitHub does not generate a
notification when you git push.

## Developer Certificate of Origin 

The service-installer-for-vmware-tanzu project team welcomes contributions from the community. 
Before you start working with service-installer-for-vmware-tanzu, please read our Developer Certificate of Origin (https://cla.vmware.com/dco).
All contributions to this repository must be signed as described on that page. Your signature certifies that you 
wrote the patch or have the right to pass it on as an open-source patch.
