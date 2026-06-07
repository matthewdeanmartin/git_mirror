# git_mirror

Batch git operations across a whole folder of GitHub repositories.

Point git_mirror at a folder full of GitHub repos and operate on all of them at once — see their
combined state, keep them in sync, and clean them up — safely, in parallel, without 30 terminal tabs.

(has nothing to do with keeping identical copies of repos on different remote servers, maybe I'll change the name.)

> **Version 2.0 is a breaking change: GitLab support has been removed.** git_mirror now targets
> GitHub and self-hosted GitHub Enterprise only. See `spec/refocus.md` for the rationale and roadmap.

Supports

- clone all
- pull all
- prune unnecessary branches
- update branch from main
- checking for unpushed changes
- copy template files to all repos (PENDING)

Does not support running arbitrary scripts in each repo.

Goal is for tools to be built-in, to be easy, safe.

Also supports parallel execution for some commands.

## Why not just plain git?
If you support 30 distinct repos across 3 different source control hosts, you'd need to open 30 tabs, cd to 30 repos,
run 30 git commands (pull, get latest from main, etc) and then feel that this was a good use of time.

## Note!
Version `1.0.0` removes the old Python-package-specific commands such as `pypi-status`.

## Installation

```bash
pipx install git-mirror
# Run the guided setup wizard
git_mirror init
# Inspect what is configured and what still needs fixing
git_mirror doctor
# Interactively select command for Github
gh_mirror menu
```

The setup wizard will help create or validate the right token, then tell you what is still broken if anything fails.

### Credential storage

As of 2.0, `git_mirror init` stores your PAT in the **OS keychain** by default
(via [keyring](https://pypi.org/project/keyring/)). Tokens are resolved in this
order, first hit wins:

1. An explicit environment variable (`GITHUB_ACCESS_TOKEN` / `SELFHOSTED_ACCESS_TOKEN`) — handy for CI.
2. The OS keychain.
3. A plaintext `.env` file (legacy; `git_mirror doctor` will offer to migrate it).

```bash
# Still supported, e.g. for CI:
GITHUB_ACCESS_TOKEN=PAT
SELFHOSTED_ACCESS_TOKEN=PAT
```

## Usage

CLI tool. Run in the directory with your pyproject.toml file.

You have forgotten to clone some repos on your secondary laptop. Run `git_mirror clone-all`.

You probably made changes and forgot to pull them. Run `git_mirror pull-all`.

You have made changes to many repos and can't remember which. Run `git_mirror local-changes`.

Github doesn't summarize failing builds across all repos. Run `git_mirror build-status`.

Your local folder has a bunch of stray folders that aren't even repos. Run `git_mirror not-repo`.

You care about some repos more than others. Focus on a subset with selection flags or config:

```bash
git_mirror pull-all --only repo-a,repo-b      # act on just these
git_mirror pull-all --tag work                 # act on repos tagged "work" in config
git_mirror pull-all --exclude scratch          # skip these
git_mirror pull-all --include-ignored          # also act on repos marked ignore=true
```

Tags and ignores live in the per-repo config table populated by `git_mirror sync-config`:

```toml
[tool.git-mirror.github.repos]
my-lib = { tags = ["work"] }
old-experiment = { ignore = true }
```

```text
usage: git_mirror [-h] [-V] [--menu MENU]
                  {show-account,list-repos,clone-all,pull-all,local-changes,not-repo,update-from-main,prune-all,sync-config,build-status,list-config,doctor,menu,init}
                  ...

Batch git operations across a folder of GitHub repositories. See readme for how this differs from the many other multi-repo tools.

positional arguments:
  {show-account,list-repos,clone-all,pull-all,local-changes,not-repo,update-from-main,prune-all,sync-config,build-status,list-config,doctor,menu,init}
                        Subcommands.
    show-account        Show source code host user account information.
    list-repos          List repositories.
    clone-all           Clone all repositories.
    pull-all            Pull all repositories.
    local-changes       List local changes.
    not-repo            List directories that are not repositories.
    update-from-main    Update from main branch.
    prune-all           Prune all repositories not found remotely.
    sync-config         Sync configuration with source code host.
    build-status        Show build status.
    list-config         List configuration.
    doctor              Check configuration and explain what needs fixing.
    menu                Show menu.
    init                Initialize configuration.

options:
  -h, --help            show this help message and exit
  -V, --version         Show program's version number and exit.
  --menu MENU           Choose a command via menu.

    Examples:

        # Interactively initialize configuration
        git_mirror init

        # Interactively select command
        git_mirror menu
```

## Config

Either run `git_mirror init` to go through the setup wizard, or add a section to `~/git_mirror.toml`. If something still does not work afterward, run `git_mirror doctor`.

```toml
[tool.git-mirror.github]
host_type = "github"
host_url = "https://api.github.com"
user_name = "matthewdeanmartin"
target_dir = "f:/github/"
include_private = false
include_forks = false

[tool.git-mirror.selfhosted]
host_type = "github"
host_url = "https://ghe.example.com/api/v3"
user_name = "mmartin"
target_dir = "e:/self/"
include_private = true
include_forks = false
```

`selfhosted` is for GitHub Enterprise (a GitHub-compatible API). Its `host_type` must be `github`.

## Examples

```bash
git_mirror clone-all # Clone everything to target directory, unless it already exists
git_mirror pull-all # Execute pull on all repos.
git_mirror local-changes # Show local, uncommitted, unpushed changes
git_mirror not-repo # Show what stray folders in the target folder have accumulated that aren't even repos.
git_mirror build-status # What github actions are failing, passing.
git_mirror sync-config  # Copy the list of all your repos to the config file so you can mark them for ignore or tag them.
```

## Prior Art

Do actions across multiple repos

- [gita](https://github.com/nosarthur/gita) - multi-repo git tool
- [mani](https://github.com/alajmo/mani) - Stores bash snippets in a yaml file. Rust
- [meta](https://github.com/mateodelnorte/meta) - Node based

[See also this huge list of similar tools](https://myrepos.branchable.com/)

Do git host things on the command line

- [gh](https://cli.github.com/) - github cli
- [glab](https://docs.gitlab.com/ee/editor_extensions/gitlab_cli/) - gitlab cli

## Documentation

- [TODO](https://github.com/matthewdeanmartin/git_mirror/blob/main/docs/TODO.md)
