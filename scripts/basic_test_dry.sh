#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=scripts/smoke_common.sh
. "$(dirname "$0")/smoke_common.sh"

for entrypoint in gh_mirror gl_mirror sh_mirror; do
    run_cli "$entrypoint" show-account --help
    run_cli "$entrypoint" list-repos --help
    run_cli "$entrypoint" clone-all --help
    run_cli "$entrypoint" pull-all --help
    run_cli "$entrypoint" local-changes --help
    run_cli "$entrypoint" not-repo --help
    run_cli "$entrypoint" update-from-main --help
    run_cli "$entrypoint" prune-all --help
    run_cli "$entrypoint" sync-config --help
    run_cli "$entrypoint" build-status --help
done
