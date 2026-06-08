# Usage

Most commands need a configured host and target directory. If you use `gh_mirror`, the host is fixed to `github`; if you use `sh_mirror`, the host is fixed to `selfhosted`.

## Setup and diagnostics

```bash
git_mirror init
git_mirror doctor
git_mirror list-config
```

## Daily status

```bash
git_mirror status --host github
git_mirror local-changes --host github
git_mirror build-status --host github
```

`status` works from local Git data and enriches the table with GitHub Actions status when a token is available. `local-changes` is focused on uncommitted and unpushed work. `build-status` asks GitHub for recent workflow status.

## Repository maintenance

```bash
git_mirror clone-all --host github
git_mirror pull-all --host github
git_mirror update-from-main --host github
git_mirror prune-all --host github
git_mirror not-repo --host github
```

Mutating commands prompt before slow or destructive work. Pass `--dry-run` to preview where supported, and `--yes` to skip prompts in automation.

`clone-all` clones configured account repositories into the target directory. `pull-all` pulls existing local repositories. `update-from-main` updates local branches from the main branch using the project logic. `prune-all` removes local branches that no longer exist remotely. `not-repo` reports directories in the target directory that are not Git repositories.

## GitHub account data

```bash
git_mirror show-account --host github
git_mirror list-repos --host github
git_mirror sync-config --host github
```

`sync-config` updates the configured repository table so you can mark repositories as important, ignored, or tagged.

## Interactive modes

```bash
git_mirror menu        # guided prompts in the terminal
git_mirror_tui         # full-screen Textual TUI
git_mirror gui         # or git_mirror_gui: tkinter desktop GUI
```

These are alternatives to typing commands. The **menu** asks you which host and
command to run; the **TUI** is a full-screen, keyboard-driven dashboard; the
**GUI** is a windowed desktop app. All three are useful for scanning configured
repositories without remembering command names.

See [Interfaces](interfaces.md) for a full description of each, including the
TUI's Dashboard, Local Changes, Actions, and Doctor tabs.
