# git_mirror
Keep all your git repos in sync safely. Useful for a poly-repo workflow.

Clone all your github repos and call pull on them.

## Installation

```bash
pipx install git-mirror
```

## Usage
CLI tool. Run in the directory with your pyproject.toml file.

You have forgotten to clone some repos on your secondary laptop. Run `git_mirror clone-all`.

You probably made changes and forgot to pull them. Run `git_mirror pull-all`.

You have made changes to many repos and can't remember which. Run `git_mirror local-changes`.

You have pushed changes to many repos and forgot if you deployed them to pypi or not. Run `git_mirror build-status`.

Github doesn't summarize failing builds across all repos. Run `git_mirror build-status`.

Your local folder has a bunch of stray folders that aren't even repos. Run `git_mirror not-repo`.

You care about some repos more than others, use config to focus on a subset of repos. (PENDING FEATURE)

```text
usage: __main__.py [-h] [--user-name USER_NAME] [--target-dir TARGET_DIR] [--include-forks] [--include-private] [--config-path CONFIG_PATH]
                   {clone-all,pull-all,local-changes,not-repo,build-status,sync-config,pypi-status}

GitHub Repository Management Tool

positional arguments:
  {clone-all,pull-all,local-changes,not-repo,build-status,sync-config,pypi-status}
                        The command to execute.

options:
  -h, --help            show this help message and exit
  --user-name USER_NAME
                        The GitHub username.
  --target-dir TARGET_DIR
                        The directory where repositories will be cloned or pulled.
  --include-forks       Include forked repositories.
  --include-private     Include private repositories.
  --config-path CONFIG_PATH
                        Path to the TOML config file.
```


###  Config
Interactively setup config in pyproject.toml
```bash
git_mirror init
```

## Manual Config
```toml
[tool.git-mirror]
user_name = "matthewdeanmartin"
target_dir = "e:/github/"
include_private = false
```

## TODO
- Support Gitlab
- "sync set of files", like project boilerplate
- interactive mode
- Verify it works with "cli to website" tools


## Clone All
Clone everything to target directory, unless it already exists
```bash
git_mirror clone-all
```

## Pull All
Execute pull on all repos.
```bash
git_mirror pull-all
```

## Local Changes
Show local, uncommitted, unpushed changes
```bash
git_mirror local-changes
```

## Not repo
Show what stray folders in the target folder have accumulated that aren't even repos.
```bash
git_mirror not-repo
```

## Build Status
What github actions are failing, passing.
```bash
git_mirror build-status
```

## Sync Config
Copy the list of all your repos to the config file so you can mark them for ignore or tag them.
```bash
git_mirror sync-config
```


## Prior Art

- `gita` - multi-repo git tool
