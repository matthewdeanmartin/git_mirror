# git_mirror
Make your local git repos look like github or gitlab.

Supports 
- clone all
- pull all
- prune unnecessary branches
- update branch from main.
- checking for unpushed changes.

Does not support running arbitrary scripts in each repo.

Goal is for tools to be built-in, to be easy.

Also supports parallel execution.

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
usage: git_mirror [-h] [-V] [--host {gitlab,github}] [--user-name USER_NAME] [--pypi-owner-name PYPI_OWNER_NAME] [--target-dir TARGET_DIR] [--include-forks] [--include-private] [--config-path CONFIG_PATH]
                  [--verbose]
                  {clone-all,pull-all,local-changes,not-repo,build-status,sync-config,pypi-status}

Clone, pull all repos from gitlab or github and other polyrepo workflows.

positional arguments:
  {clone-all,pull-all,local-changes,not-repo,build-status,sync-config,pypi-status}
                        The command to execute.

options:
  -h, --help            show this help message and exit
  -V, --version         Show program's version number and exit.
  --host {gitlab,github}
                        Source host, use gl_mirror or gh_mirror to skip this.
  --user-name USER_NAME
                        The username.
  --pypi-owner-name PYPI_OWNER_NAME
                        Pypi Owner Name.
  --target-dir TARGET_DIR
                        The directory where repositories will be cloned or pulled.
  --include-forks       Include forked repositories.
  --include-private     Include private repositories.
  --config-path CONFIG_PATH
                        Path to the TOML config file.
  --verbose             verbose output

    Examples:

        # Clone everything
        git_mirror clone-all

        # Generate config for snapshots
        git_mirror pull-all
```

## Config

Either run `git_mirror init` to interactively setup the config, or add a section to `~/git_mirror.toml`.

```toml
[tool.git-mirror.github]
user_name = "matthewdeanmartin"
pypi_owner_name = "Matthew Martin"
target_dir = "f:/github/"
include_private = false
include_forks = false

[tool.git-mirror.gitlab]
user_name = "matthewdeanmartin"
url = "http://gitlab.com"
pypi_owner_name = "Matthew Martin"
target_dir = "f:/gitlab/"
include_private = true
include_forks = false
group_id = 542

[tool.git-mirror.selfhosted]
type = "gitlab"
user_name = "mmartin"
url = "http://git.example.com"
pypi_owner_name = "Matthew Martin"
target_dir = "e:/self/"
include_private = true
include_forks = false
```




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

huge list of similar tools: https://myrepos.branchable.com/

Do git host things on the command line
- [gh](https://cli.github.com/) - github cli


## Documentation
- [TODO](https://github.com/matthewdeanmartin/git_mirror/blob/main/docs/TODO.md)