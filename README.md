# git-mirror

Batch Git maintenance across a folder of local GitHub repositories.

`git-mirror` is for developers who keep many repositories checked out and want a single command for the boring, repetitive work: clone everything, pull everything, scan local changes, check build status, and clean up branches.

Despite the name, it is not a service for mirroring repositories between remotes. It does not keep GitHub, GitLab, or another server in sync. Version 2.x supports public GitHub and self-hosted GitHub Enterprise only; GitLab support was removed.

## Install

```bash
pipx install git-mirror
git_mirror init
git_mirror doctor
```

The setup wizard creates or validates your configuration and helps store a GitHub token in the OS keychain when possible.

## Commands

The installed command names are:

- `git_mirror`: full CLI; pass `--host github` or `--host selfhosted` for repository commands.
- `gh_mirror`: shortcut for the public GitHub host.
- `sh_mirror`: shortcut for self-hosted GitHub Enterprise.
- `git_mirror_gui`: desktop GUI.

Common commands:

```bash
git_mirror status --host github
git_mirror clone-all --host github
git_mirror pull-all --host github
git_mirror local-changes --host github
git_mirror build-status --host github
git_mirror update-from-main --host github
git_mirror prune-all --host github
git_mirror sync-config --host github
git_mirror not-repo --host github
```

Use `--dry-run` to preview supported mutating commands and `--yes` to skip confirmation prompts in automation.

## Configuration

By default, `git_mirror init` writes `~/git_mirror.toml`.

```toml
[tool.git-mirror.github]
host_type = "github"
host_url = "https://api.github.com"
user_name = "octocat"
target_dir = "C:/github"
include_private = false
include_forks = false

[tool.git-mirror.selfhosted]
host_type = "github"
host_url = "https://ghe.example.com/api/v3"
user_name = "octocat"
target_dir = "D:/enterprise-github"
include_private = true
include_forks = false
```

`selfhosted` means GitHub Enterprise using a GitHub-compatible API. Its `host_type` should still be `github`.

Tokens are resolved in this order:

1. Environment variables: `GITHUB_ACCESS_TOKEN` or `SELFHOSTED_ACCESS_TOKEN`.
2. The OS keychain.
3. A legacy plaintext `.env` file.

## Repository Selection

Run `sync-config` to populate the per-repository config table:

```bash
git_mirror sync-config --host github
```

Then tag or ignore repositories:

```toml
[tool.git-mirror.github.repos]
work-api = { tags = ["work"] }
old-demo = { ignore = true }
```

Selection flags work on repository commands:

```bash
git_mirror pull-all --host github --only work-api,docs-site
git_mirror status --host github --tag work
git_mirror pull-all --host github --exclude old-demo
git_mirror status --host github --include-ignored
```

## What It Does Not Do

- It does not mirror one remote server to another.
- It does not run arbitrary shell scripts across repositories.
- It does not currently support GitLab.
- It does not replace `gh`; it covers a narrower multi-repository workflow.

## Documentation

Full documentation is published at [git-mirror.readthedocs.io](https://git-mirror.readthedocs.io/).

The changelog is in [CHANGELOG.md](CHANGELOG.md).
