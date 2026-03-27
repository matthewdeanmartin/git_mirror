# git_mirror review

## Summary

The repo still has the shape of a useful polyrepo tool, but the center of gravity has drifted.

The original core seems to be:

- manage many repos from one place
- support GitHub, GitLab, and self-hosted Git
- provide built-in safe batch operations instead of arbitrary shell fan-out

What is in the code today is a mix of that core, Python-specific tooling, and some half-wired cross-repo templating. The biggest issues are not polish problems; there are several structural bugs in setup and host modeling that block the intended product.

## Core vs non-core

### Core

These are the features that fit the original product direction and should define the product:

- `clone-all`
- `pull-all`
- `list-repos`
- `show-account`
- `local-changes`
- `update-from-main`
- `prune-all`
- `build-status`
- `sync-config`
- a sane `init` flow
- real support for GitHub, GitLab, and self-hosted instances

### Non-core

These features are useful, but they are not central to the “safe multi-repo action runner across hosts” story:

- `pypi-status`
- `poetry-relock`
- `cross-repo-report`
- `cross-repo-sync`
- `cross-repo-init`
- bug reporting hooks via `BugReporter`

Why they feel non-core:

- `pypi-status` and `poetry-relock` are Python packaging workflows, not polyrepo fundamentals.
- cross-repo template sync is closer to boilerplate propagation than repo orchestration.
- these features add setup and mental overhead while core host support is still incomplete.

Recommendation: keep them, but explicitly demote them to later phases or a separate “automation” surface.

## Obvious bugs

### 1. First-run auto-init is broken

In `git_mirror\__main__.py:409-412`, the code detects first-time setup and assigns `argv = ["init"]`, but it never reparses args. `args.command` stays whatever was parsed before, so the promised first-run initialization path does not actually run.

This is a direct contributor to the bad setup experience.

### 2. Self-hosted config init is internally inconsistent

In `git_mirror\manage_config.py:112-150`, `ask_for_section()` uses:

- `host_type = "selfhosted"` for the section choice
- `host_name = "github" | "gitlab"` for the actual backend type

But `ConfigManager.initialize_config()` later rejects anything where `config_section.host_type not in ("github", "gitlab")` at `git_mirror\manage_config.py:228-229`.

That means self-hosted initialization is effectively broken by design.

### 3. Self-hosted GitHub is not actually supported

The CLI claims support for GitHub, GitLab, and self-hosted. The code does not currently honor that model.

- `git_mirror\router.py:126-138` routes both `gitlab` and `selfhosted` to `GitlabRepoManager`
- `git_mirror\__main__.py:67-81` distinguishes self-hosted GitHub vs self-hosted GitLab for token handling
- `git_mirror\manage_github.py:81-82` ignores `host_domain` and always constructs a normal `gh.Github(self.token)` client

So the app conceptually models self-hosted GitHub, but operationally routes self-hosted traffic as GitLab or uses public GitHub assumptions.

### 4. Self-hosted PAT validation is hardcoded to public hosts

- `git_mirror\pat_init.py:29` validates against `https://api.github.com/user`
- `git_mirror\pat_init_gitlab.py:29` validates against `https://gitlab.com/api/v4/user`

That works only for public SaaS endpoints. It does not validate tokens for self-hosted instances.

### 5. Retrying target-dir entry is buggy

In `git_mirror\manage_config.py:104-105`, when the user declines directory creation and is reprompted, the code does:

`target_dir = Path(target_dir_answer).expanduser()`

But `target_dir_answer` is the whole prompt result dict, not the `"target_dir"` string value. That path conversion is wrong and will fail.

### 6. `menu` has a broken Poetry entry

In `git_mirror\menu.py:49`, the `"Poetry "` entry maps to `"cross-repo-init"` instead of `"poetry-relock"`.

Also:

- `menu.py:60` lists a `poetry-relock` category entry
- `__main__.py` never registers a `poetry-relock` subparser
- `router.py:192-203` has a partial `poetry-relock` branch with TODO placeholders

So this feature is both exposed incorrectly and unfinished.

### 7. Unpushed commit detection is reversed

In `git_mirror\manage_git.py:167-173`, the code labels `branch..tracking_branch()` as `ahead_count` and reports unpushed commits when that count is positive. That range represents the remote being ahead of local, not local commits waiting to be pushed.

So `local-changes` can report the wrong condition.

### 8. GitLab fork detection in `not-repo` is inverted

In `git_mirror\manage_gitlab.py:403-411`, the code sets `forked = True` when `forked_from_project` exists, but then increments `is_fork` when `not forked`.

That makes the fork classification backwards.

### 9. Import surface is too eager and hurts setup/testing

`git_mirror\__init__.py:1-6` eagerly imports `GitManager`, `GithubRepoManager`, `GitlabRepoManager`, and `PyPiManager`.

In practice, that means importing lightweight modules can fail early if heavy runtime deps are missing. In this checkout, `python -m pytest -q` failed during collection with missing `git` and `rich` imports before meaningful tests even ran.

This is partly an environment/bootstrap problem, but the eager package imports make it worse than it needs to be.

## Feature gaps

### 1. No real host abstraction parity

The app has three entrypoints and a `SourceHost` concept, but host support is not actually symmetric.

Missing or incomplete:

- self-hosted GitHub support
- multiple self-hosted instances
- consistent auth/bootstrap per host
- consistent behavior across GitHub and GitLab managers

### 2. No GitHub org support

The tool is supposed to be useful across many repos. Today it is mostly centered on user-owned repos.

There is even a note in `git_mirror\router.py:143-145` that GitHub org support is effectively still a hack-sized gap. For a real polyrepo tool, org/group support is core.

### 3. No repo selection model beyond “all”

The README mentions wanting to focus on subsets of repos, but that is still marked pending. There is no mature concept of:

- include/exclude lists
- tags
- groups of repos
- run against “important” repos only

Without this, the tool is closer to “all repos for one account” than a practical orchestration tool.

### 4. Setup is fragmented instead of unified

Setup is split across:

- `init`
- token prompts
- `.env` loading from current dir or home dir
- config file management
- host selection prompts

There is no clean “health check” or “doctor” command to say:

- config path used
- host configured
- token found
- token valid
- target dir exists
- API reachable

### 5. Non-core features are stealing surface area from core workflows

Cross-repo template sync and Poetry/PyPI workflows are implemented deeply enough to add commands, routes, and menu complexity, while core polyrepo gaps remain open.

That is product drift, not just backlog growth.

### 6. Command surface is inconsistent

There are features present in one layer but not another:

- router branch exists but parser command does not
- menu references commands not wired in CLI
- README claims support not borne out by routing

That makes the tool feel unreliable even before execution starts.

## Setup and init review

The current setup UX is bad for structural reasons:

- first-run auto-init is broken
- self-hosted modeling is inconsistent
- PAT validation is host-specific in name only
- config and env behavior are distributed across too many modules
- there is no single success path that ends with a verified working configuration

The right model is probably:

1. choose host type
2. choose host instance
3. validate token against that exact host
4. choose target dir
5. verify repo listing works
6. save config
7. print a short “you are ready” summary

Right now the code does not reliably deliver that flow.

## Phased plan

### Phase 0: product reset

Goal: decide what this tool is before more code is added.

Keep as core:

- clone
- pull
- list
- local status
- build status
- branch maintenance
- config sync
- host support

Move out of the critical path:

- PyPI features
- Poetry relock
- cross-repo template sync
- bug reporting extras

This phase should end with a smaller, explicit product statement in the README and CLI help.

### Phase 1: fix setup and host modeling

Goal: make install and init actually work.

Work:

- fix first-run auto-init in `__main__.py`
- repair self-hosted config modeling in `manage_config.py`
- make self-hosted GitHub and self-hosted GitLab explicit, not overloaded
- validate PATs against the configured host, not hardcoded public URLs
- add a single `doctor` or `health` command
- stop eager package imports in `git_mirror\__init__.py`

This is the most important phase.

### Phase 2: restore core polyrepo behavior

Goal: make the tool good at safe multi-repo actions.

Work:

- fix unpushed commit detection
- fix GitLab fork detection
- unify command registration, menu entries, router branches, and README
- make dry-run behavior consistent
- improve error messages for missing config, missing tokens, and bad hosts

This phase should make the existing commands trustworthy.

### Phase 3: add real repo targeting

Goal: make the tool practical for larger repo sets.

Work:

- support GitHub orgs
- improve GitLab group support
- add repo tagging / filters / subsets
- support running commands against configured groups instead of only “everything”

This is the phase where it becomes a real polyrepo tool instead of a personal account helper.

### Phase 4: host parity and operational polish

Goal: make GitHub, GitLab, and self-hosted feel equally supported.

Work:

- support multiple self-hosted instances
- normalize feature parity between managers
- add consistent build-status behavior
- add better logging and diagnostics
- clean up interactive prompts and confirmations

### Phase 5: optional automation features

Goal: reintroduce non-core value without polluting the core product.

Candidates:

- cross-repo template sync
- `pypi-status`
- `poetry-relock`
- PR/MR automation

These should come back only after Phase 1-4 are solid, and ideally live behind a clearly separate “automation” or “language-specific” surface.

## Recommendation

If the project is going to get back on track, the right move is not “add more features.” It is:

- narrow the definition of core
- repair setup and host abstraction
- make the existing core commands reliable
- only then add advanced automation back on top

Right now the biggest problem is not lack of ideas. It is that the foundation still does not match the product promise.
