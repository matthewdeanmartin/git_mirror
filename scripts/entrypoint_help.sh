#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=scripts/smoke_common.sh
. "$(dirname "$0")/smoke_common.sh"

run_smoke uv run gh_mirror list-config --help
run_smoke uv run gh_mirror doctor --help
run_smoke uv run gl_mirror list-config --help
run_smoke uv run gl_mirror doctor --help
run_smoke uv run sh_mirror list-config --help
run_smoke uv run sh_mirror doctor --help
