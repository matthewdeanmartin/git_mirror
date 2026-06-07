# Configuration

Run the guided setup first:

```bash
git_mirror init
```

By default, configuration is written to `~/git_mirror.toml`. Use `--config-path` to point at a different file.

## GitHub

```toml
[tool.git-mirror.github]
host_type = "github"
host_url = "https://api.github.com"
user_name = "octocat"
target_dir = "C:/github"
include_private = false
include_forks = false
```

## GitHub Enterprise

Self-hosted GitHub Enterprise uses the same GitHub API support with a different host URL:

```toml
[tool.git-mirror.selfhosted]
host_type = "github"
host_url = "https://ghe.example.com/api/v3"
user_name = "octocat"
target_dir = "D:/enterprise-github"
include_private = true
include_forks = false
```

## Credentials

`git_mirror init` stores personal access tokens in the operating system keychain when possible. Tokens are resolved in this order:

1. Environment variables: `GITHUB_ACCESS_TOKEN` or `SELFHOSTED_ACCESS_TOKEN`.
2. The OS keychain.
3. A legacy plaintext `.env` file.

Run `git_mirror doctor` after setup to validate the configured target directory, token, and account.

## Repository selection

Run `sync-config` to populate a per-repository table:

```bash
git_mirror sync-config --host github
```

Then mark repositories:

```toml
[tool.git-mirror.github.repos]
work-api = { tags = ["work"] }
old-demo = { ignore = true }
```

Repository commands accept selection flags:

```bash
git_mirror pull-all --host github --only work-api,docs-site
git_mirror status --host github --tag work
git_mirror pull-all --host github --exclude old-demo
git_mirror status --host github --include-ignored
```
