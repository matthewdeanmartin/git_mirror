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

`status` works from local Git data and enriches the table with GitHub Actions status when a token is available.

## Repository maintenance

```bash
git_mirror clone-all --host github
git_mirror pull-all --host github
git_mirror update-from-main --host github
git_mirror prune-all --host github
git_mirror not-repo --host github
```

Mutating commands prompt before slow or destructive work. Pass `--dry-run` to preview where supported, and `--yes` to skip prompts in automation.

## GitHub account data

```bash
git_mirror show-account --host github
git_mirror list-repos --host github
git_mirror sync-config --host github
```

`sync-config` updates the configured repository table so you can mark repositories as important, ignored, or tagged.

## Interactive modes

```bash
git_mirror menu
git_mirror gui
git_mirror_gui
```

The GUI is useful for scanning configured repositories without remembering the command names.
