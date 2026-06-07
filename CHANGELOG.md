# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added Read the Docs and MkDocs documentation.
- Added changelog-driven draft release and PyPI publishing workflows.

### Changed

- Rewrote the README to describe the current GitHub-focused scope honestly.

## [2.0.0] - 2026-06-07

### Added

- Added GitHub Enterprise support through the self-hosted GitHub configuration path.
- Added OS keychain credential storage with environment variable and legacy `.env` fallback.
- Added the combined `status` dashboard for local repository state and optional GitHub Actions status.
- Added per-repository tags and ignore flags for selecting subsets of repositories.
- Added the desktop GUI entry point.

### Changed

- Re-focused the CLI on safe GitHub repository maintenance across many local checkouts.
- Reworked setup around `git_mirror init` and `git_mirror doctor`.

### Removed

- Removed GitLab support.
- Removed old Python package maintenance commands from the active CLI.

## [1.0.0] - 2026-03-27

### Changed

- Re-focused the CLI around safe git operations across many repositories.
- Reworked `init` into a more guided setup flow and added `doctor` for actionable configuration diagnostics.

### Removed

- Removed `pypi-status` and `poetry-relock` from the command surface.
- Removed the mutating `cross-repo-sync` command from the active CLI and archived its implementation under `dead_code`.
- Removed the remaining `cross-repo-report` and `cross-repo-init` commands from the active CLI and archived their code under `dead_code`.

## [0.3.8] - 2024-05-15

### Fixed

- termcolor missing from installer.

## [0.3.3] - 2024-02-24

### Added

- Started cross-repo sync feature. Beta quality
- Started poetry dependency lock. Command not surfaced yet.

### Fixed

- more unit tests, found bugs in the config UI

## [0.3.2] - 2024-02-21

### Added

- `--dry-run` to simulate read-write events.
- If github token available, and an crash happens, it offers to report the bug with an Issue

### Fixed

- menu now has exit, loop to main menu and better control-c handling

## [0.3.1] - 2024-02-20

### Added

- Display message if no config file or sections found.

### Fixed

- group_id config shouldn't blow up.
- Gitlab and self hosted works better

## [0.3.0] - 2024-02-18

### Added

- menu command for UI.
- More commands.
- Start support for running multi-repo steps in parallel.
- Double verbose outputs even more logging.

### Fixed

- `.env` file support doesn't work in all shells, now keeps going if it fails.
- User info is printed, not just logged

## [0.2.0] - 2024-02-16

### Added

- Gitlab support improved, start support for self-hosted

### Fixed

- Colorama was missing from installer, 0.1.0 yanked.

## [0.1.0] - 2024-02-15

### Added

- Github and Gitlab support

