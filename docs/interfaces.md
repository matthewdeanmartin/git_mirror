# Interfaces

git-mirror can be driven four ways. All four are thin front ends over the same
shared core, so a clone, pull, or prune behaves identically no matter how you
start it (see [Architecture](architecture.md)). Pick whichever fits the moment.

| Interface | Command | Best for |
|-----------|---------|----------|
| CLI | `git_mirror <command>` | scripts, CI, muscle memory |
| Interactive menu | `git_mirror menu` | guided prompts without memorizing commands |
| TUI (full-screen) | `git_mirror_tui` | live, navigable terminal dashboard |
| Desktop GUI | `git_mirror_gui` | a windowed app, point-and-click |

## CLI

The default, non-interactive surface. Every capability is a subcommand; this is
what the rest of the documentation uses. See [Usage](usage.md) for the full
command list.

```bash
git_mirror status --host github
git_mirror clone-all --host github --dry-run
```

Use `--dry-run` to preview mutating commands and `--yes` to skip confirmation
prompts in automation.

## Interactive menu

```bash
git_mirror menu
```

A guided, prompt-driven flow in the terminal. It walks you through choosing a
host and a command, so you can use git-mirror without remembering the exact flag
names. Good for occasional use.

## TUI (Textual)

```bash
git_mirror_tui
```

A full-screen terminal application built with
[Textual](https://textual.textualize.io/). Textual is a regular dependency, so
the TUI is always available after installation — there is nothing extra to
install.

The TUI is organized as tabs:

- **Dashboard** — the fleet-status table: one row per local repository with its
  branch, state (clean / dirty / out of sync / error), ahead and behind counts,
  untracked-branch count, last-commit age, and latest CI conclusion. Rows are
  sorted attention-first. Toggle **Include CI status** to enrich the table with
  GitHub Actions results (this requires a token); without it, the dashboard
  works purely from local Git data.
- **Local Changes** — repositories with uncommitted work or unpushed/untracked
  branches.
- **Actions** — run the batch mutations: **Clone All**, **Pull All**, and
  **Prune**. Choose a host, toggle **Dry run**, and watch the results stream into
  the log pane.
- **Doctor** — the same configuration, token, and connectivity health report as
  `git_mirror doctor`.

Long-running operations run on background worker threads, so the interface stays
responsive while a scan or clone is in progress.

Handy keys: `r` refreshes the active data tab, `q` quits, and the tab bar (or
arrow keys) moves between tabs. The footer lists the active bindings.

## Desktop GUI (tkinter)

```bash
git_mirror gui      # or:
git_mirror_gui
```

A windowed desktop application built with tkinter. It mirrors the TUI's scope:
a fleet-status dashboard, local-changes and build-status tables, clone / pull /
update-from-main / prune actions, a non-repository scanner, plus doctor and
configuration panels (including a "sync with remote" action). It is handy for
scanning configured repositories without remembering command names.

## Which should I use?

- Automating or scripting? Use the **CLI**.
- Want a live, keyboard-driven overview in your terminal? Use the **TUI**.
- Prefer a separate window with buttons? Use the **GUI**.
- Just need to run one thing and would rather be asked questions? Use the
  **menu**.

`init` (the setup wizard) is interactive and terminal-based; run `git_mirror
init` from a shell before using the TUI or GUI for the first time.
