# Architecture

git-mirror has four front ends — a CLI, an interactive menu, a Textual TUI, and a
tkinter GUI — but only **one** implementation of each batch operation. This page
explains the layering, which matters if you are contributing or wondering why all
four interfaces behave identically.

## One core, many front ends

```
        CLI (router)   menu   TUI (tui/app.py)   GUI (gui/app.py)
              \          \          |               /
               \          \         |              /
                +----------------------------------+
                |          git_mirror.core         |   <- the only place
                |   (batch operations, plain data) |      batch logic lives
                +----------------------------------+
                                  |
                +----------------------------------+
                |   manage_github / manage_git     |   <- host + git managers
                +----------------------------------+
```

`git_mirror/core.py` is the single, interface-agnostic home for "do a batch git
operation over a folder of repositories." Every front end calls into it and
renders the **plain data** it returns. The front ends never re-implement an
operation and never build a host manager themselves.

### What core returns

Core functions return dataclasses, not formatted text:

- `RepoStatus` — one repository's uncommitted / unpushed / untracked state.
- `DashboardRow` — combined local + remote state for the status dashboard
  (branch, dirty, ahead, behind, untracked count, last-commit age, CI build,
  error), with a `needs_attention` property.
- `RepoInfo` — a remote repository listing entry.
- `BuildInfo` — one repository's latest CI conclusion.
- `ActionResult` — the outcome of a mutation, with `messages` and `errors`.

### Key core functions

- Read/scan: `load_all_configs`, `run_doctor`, `scan_local_changes`,
  `repo_dashboard`, `list_repos_data`, `get_build_statuses`, `find_non_repos`.
- Mutations: `clone_all_repos`, `pull_all_repos`, `update_from_main_repos`,
  `prune_all_repos`.
- Plumbing shared by all callers: `build_manager` / `manager_from_config`
  (the single place a host manager is constructed), `build_selection` (repository
  filtering), and `get_token_for_host` (credential resolution).

Because there is exactly one `manager_from_config`, manager construction cannot
drift between the CLI and the GUI/TUI.

## Shared status classification

Turning a repository's state into "good / warning / bad" so it can be coloured is
a *decision*, and that decision lives in core too:

- `core.dashboard_state(row)` → `("ok" | "warn" | "error", label)`
- `core.build_state(conclusion)` → `("ok" | "warn" | "error" | "dim", label)`

Each front end maps the returned tag to its own colours — the CLI via
`utils/ui.rich_markup` (Rich), the GUI via tkinter tags, the TUI via its
`TAG_COLOR` table. One decision, several colour tables, **no duplicated logic**.

## Keeping background work off the UI thread

The interactive interfaces run slow operations off the main thread so the UI
stays responsive:

- The **GUI** uses a `BackgroundRunner` that runs a function in a daemon thread
  and posts the result back via `root.after(...)`.
- The **TUI** uses Textual workers (`@work(thread=True)`) and posts results back
  via `app.call_from_thread(...)`.

Both simply call a core function on the worker and render the returned dataclass.

## Front-end responsibilities

A front end is responsible for **input and rendering only**:

1. gather inputs (host, flags, dry-run, selection),
2. call the matching `core` function,
3. render the returned data (table, log, widget),
4. classify state via `core.dashboard_state` / `core.build_state` and map the tag
   to a colour.

If you find yourself building a `GithubRepoManager`, resolving a token, or
re-deriving status colours inside a front end, that logic belongs in `core`
instead.

## Module map

- `git_mirror/core.py` — shared batch operations and classification.
- `git_mirror/router.py` — thin CLI adapter; parses, calls core, renders Rich.
- `git_mirror/menu.py` — interactive `inquirer` menu.
- `git_mirror/tui/app.py` — Textual TUI.
- `git_mirror/gui/app.py` — tkinter GUI.
- `git_mirror/manage_github.py`, `git_mirror/manage_git.py` — the host and Git
  managers core delegates to.
- `git_mirror/manage_config.py` — config file load/save, doctor checks, setup.
- `git_mirror/utils/` — repository-agnostic plumbing (credentials, console/theme,
  environment, logging, bug reporting, dependency checks).
