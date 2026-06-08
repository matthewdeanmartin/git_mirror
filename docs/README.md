# git-mirror

**Point git-mirror at a folder full of GitHub repositories and operate on all of
them at once** — see their combined state, keep them in sync, and clean them up,
safely and in parallel, without juggling thirty terminal tabs.

`git-mirror` is for developers who keep many repositories checked out locally and
want one command for routine maintenance: clone every repository for an account,
pull existing checkouts, inspect uncommitted and unpushed work, check GitHub
Actions status, update branches from `main`, and prune branches that no longer
exist on the remote.

Despite the name, it is **not** a remote-to-remote mirroring service. It does not
keep two servers in sync. Version 2.x supports **public GitHub** and
**self-hosted GitHub Enterprise** only.

## Quick start

```bash
pipx install git-mirror
git_mirror init      # guided setup; stores your token in the OS keychain
git_mirror doctor    # validate config, target directory, and token
git_mirror status --host github
```

`init` creates or validates your configuration and stores a GitHub token in the
operating system keychain when possible. `doctor` reports missing config values,
missing target directories, and token problems before you run any repository
command.

## What you get

- **A fleet dashboard** — `git_mirror status` shows every repository's branch,
  dirty state, ahead/behind counts, last-commit age, and latest CI conclusion in
  one table, sorted so the repositories that need attention come first.
- **Safe batch mutations** — clone, pull, update-from-main, and prune across the
  whole folder, with `--dry-run` previews and confirmation prompts.
- **Repository selection** — focus commands on a subset with `--only`, `--tag`,
  and `--exclude`, driven by a per-repository table in your config.
- **Four ways to drive it** — a scriptable CLI, an interactive terminal menu, a
  full-screen Textual TUI, and a tkinter desktop GUI. See
  [Interfaces](interfaces.md).

## Where to go next

- [Installation](installation.md) — install methods and the installed commands.
- [Configuration](configuration.md) — config file, credentials, and repository
  selection.
- [Usage](usage.md) — the command surface, grouped by task.
- [Interfaces](interfaces.md) — CLI, menu, TUI, and GUI.
- [Architecture](architecture.md) — how the one shared core keeps every
  interface consistent.
