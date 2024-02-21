## Non-pypi version audit
- depends on git - min version too low to care about?
- github API - has version endpoint
- gitlab API (v3)

## Performance
- Many steps are slow/not parallel, provide no UI when waiting.

## Host support

- Private Gitlab
  - Need to disambiguate the gitlabs (currently, just "selfhosted")
- Private Github
  - Need to load url from config.

## TODO

- "sync set of files", like project boilerplate
- Verify it works with "cli to website" tools

## Config

- Add tag filtering to app so that action only applied to tag
- Implement "do_not_clone" attribute to skip them.
- Implement "remove_local" - skip and delete

## Plugins?

- hook for new specific command
- hook for new host
