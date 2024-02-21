# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.0] - 2024-02-15

### Added

- Github and Gitlab support

## [0.2.0] - 2024-02-16

### Added

- Gitlab support improved, start support for self-hosted

### Fixed

- Colorama was missing from installer, 0.1.0 yanked.

## [0.3.0] - 2024-02-18

### Added
- menu command for UI.
- More commands.
- Start support for running multi-repo steps in parallel.
- Double verbose outputs even more logging.

### Fixed
- `.env` file support doesn't work in all shells, now keeps going if it fails.
- User info is printed, not just logged

## [0.3.0] - 2024-02-18

### Added
- Display message if no config file or sections found.

### Fixed
- group_id config shouldn't blow up.
- 