# git-mirror

`git-mirror` is a developer utility for running common Git maintenance tasks across a folder of local GitHub repositories.

It is for people who keep many repositories checked out locally and want one command for things like status, pull, branch cleanup, and GitHub Actions status. It is not a repository mirroring service, backup tool, or arbitrary script runner.

Version 2.x is GitHub-focused. Public GitHub and self-hosted GitHub Enterprise are supported. GitLab support and old Python package maintenance commands were removed.

## What it does

- Clones all repositories for a configured account into a target directory.
- Pulls all local repositories in that target directory.
- Shows local dirty state, ahead or behind counts, branch age, and recent build status.
- Lists uncommitted or unpushed local changes.
- Finds directories that are not Git repositories.
- Updates local branches from the main branch.
- Prunes branches that no longer exist remotely.
- Syncs a per-repository configuration table so selected repositories can be tagged or ignored.

## What it does not do

- It does not keep two remotes continuously mirrored.
- It does not run arbitrary shell scripts across repositories.
- It does not currently support GitLab.
- It does not replace `gh`; it wraps common multi-repository chores.

## Start here

Install the package, run the guided setup, and then ask the doctor command what still needs attention:

```bash
pipx install git-mirror
git_mirror init
git_mirror doctor
git_mirror status --host github
```
