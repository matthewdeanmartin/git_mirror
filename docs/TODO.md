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
