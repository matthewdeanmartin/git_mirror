## Top Top Priority
- Rename to gittyup
- Change selfhosted to self-hosted-gitlab
- Maybe shows some minimal output before running a command (config)
- Support flat directory structure for gitlab
- Support repo to folder map?

## Top priority
- PAT token init help
- platform dirs for config files
- subcommands (remove the dash in current commands, restrict args to relevant command)
- show config to show where config files are
- display config to also show tool versions and API versions
- check tool versions on init (assume that runs mostly just after instal)

## DX
- always output some sort of command, unless `--quiet`
- support a `-y` flag for auto yes
- subcommands so args don't look like they apply to everything

## Cross platform support
- platform dirs for data files

## New commands

- cross-repo-* sync etc. based on 2nd config
- merge-each (to prod-in-flight branch)
- push-release-tag-to-all (e.g. for big bang release)
- poetry re-lock/update
- rebuild-all (with time delay?)

## Status command

- missing ahead/behind count

## Non-pypi version audit

- depends on git - min version too low to care about?
- github API - has version endpoint
- gitlab API (v3)

## Performance

- Many steps are slow/not parallel
- Needs to provide UI when waiting/stop waiting for all to finish before showing results
- we need cache

## Host support

- Private Gitlab
  - Need to disambiguate the gitlabs (currently, just "selfhosted")
- Private Github
  - Need to load url from config.

## UI

- everything `rich` or at least more consistent.

## TODO

- "sync set of files", like project boilerplate
- Verify it works with "cli to website" tools

## Config

- platform dirs and rename config file to `.git_mirror.toml`
- Add tag filtering to app so that action only applied to tag
- Implement "do_not_clone" attribute to skip them.
- Implement "remove_local" - skip and delete

## Plugins?

- hook for new specific command
- hook for new host

## Safety features

- `--dry-run` - get previous of git commands and other actions
- `--one-repo` - reduce blast radius for testing current setup.
- add confirmation to more commands if more than 1 repo at stake
