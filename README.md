# git_mirror

Make all your local git repos look like Github or Gitlab.

(has nothing to do with keeping identical copies of repos on different remote servers, maybe I'll change the name.)

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
Upcoming 0.3.4 to 1.0.0 will break backwards as I switch to (sub-)subcommands.

## Installation

```bash
pipx install git-mirror
# Interactively initialize configuration
git_mirror init
# Interactively select command for Github
gh_mirror menu
```

Requires .env file with Github or Gitlab token.

```bash
GITHUB_ACCESS_TOKEN=PAT
GITLAB_ACCESS_TOKEN=PAT
SELFHOSTED_ACCESS_TOKEN=PAT
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
usage: git_mirror [-h] [-V] [--menu MENU]
                  {show-account,list-repos,clone-all,pull-all,local-changes,not-repo,update-from-main,prune-all,sync-config,build-status,list-config,pypi-status,cross-repo-report,cross-repo-sync,cross-repo-init,menu,init}
                  ...

Make your local git repos look like github or gitlab. See readme for how this differs from the many other multi-repo tools.

positional arguments:
  {show-account,list-repos,clone-all,pull-all,local-changes,not-repo,update-from-main,prune-all,sync-config,build-status,list-config,pypi-status,cross-repo-report,cross-repo-sync,cross-repo-init,menu,init}
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
    pypi-status         Show pypi deployment status.
    cross-repo-report   Show cross repo sync report.
    cross-repo-sync     Sync files across repos.
    cross-repo-init     Initialize cross repo sync.
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

[See also this huge list of similar tools](https://myrepos.branchable.com/)

Do git host things on the command line

- [gh](https://cli.github.com/) - github cli
- [glab](https://docs.gitlab.com/ee/editor_extensions/gitlab_cli/) - gitlab cli

## Documentation

- [TODO](https://github.com/matthewdeanmartin/git_mirror/blob/main/docs/TODO.md)
