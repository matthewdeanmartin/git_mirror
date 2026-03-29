#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=scripts/smoke_common.sh
. "$(dirname "$0")/smoke_common.sh"

for entrypoint in gh_mirror gl_mirror sh_mirror; do
    run_smoke uv run "$entrypoint" show-account --help
    run_smoke uv run "$entrypoint" list-repos --help
    run_smoke uv run "$entrypoint" clone-all --help
    run_smoke uv run "$entrypoint" pull-all --help
    run_smoke uv run "$entrypoint" local-changes --help
    run_smoke uv run "$entrypoint" not-repo --help
    run_smoke uv run "$entrypoint" update-from-main --help
    run_smoke uv run "$entrypoint" prune-all --help
    run_smoke uv run "$entrypoint" sync-config --help
    run_smoke uv run "$entrypoint" build-status --help
done
