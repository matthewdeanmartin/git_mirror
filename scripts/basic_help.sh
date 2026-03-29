#!/usr/bin/env bash
set -euo pipefail

# make sure this doesn't fail on TERM not set
clear || true

# shellcheck source=scripts/smoke_common.sh
. "$(dirname "$0")/smoke_common.sh"

run_smoke uv run git_mirror --help
run_smoke uv run git_mirror --version
run_smoke uv run gh_mirror --help
run_smoke uv run gh_mirror --version
run_smoke uv run gl_mirror --help
run_smoke uv run gl_mirror --version
run_smoke uv run sh_mirror --help
run_smoke uv run sh_mirror --version
