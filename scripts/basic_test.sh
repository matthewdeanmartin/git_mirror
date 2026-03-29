#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=scripts/smoke_common.sh
. "$(dirname "$0")/smoke_common.sh"

run_smoke uv run git_mirror list-config --config-path "$CONFIG_PATH"
run_smoke uv run git_mirror list-config --config-path "$CONFIG_PATH" --host github
run_smoke uv run git_mirror list-config --config-path "$CONFIG_PATH" --host gitlab
run_smoke uv run git_mirror list-config --config-path "$CONFIG_PATH" --host selfhosted

run_smoke uv run git_mirror doctor --help
run_smoke uv run git_mirror init --help
run_smoke uv run git_mirror menu --help
run_smoke uv run git_mirror gui --help

run_smoke uv run git_mirror list-repos --help
run_smoke uv run git_mirror clone-all --help
run_smoke uv run git_mirror pull-all --help
run_smoke uv run git_mirror local-changes --help
run_smoke uv run git_mirror not-repo --help
run_smoke uv run git_mirror update-from-main --help
run_smoke uv run git_mirror prune-all --help
run_smoke uv run git_mirror sync-config --help
run_smoke uv run git_mirror build-status --help
