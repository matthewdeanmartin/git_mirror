#!/usr/bin/env bash
set -euo pipefail

# make sure this doesn't fail on TERM not set
clear || true

# shellcheck source=scripts/smoke_common.sh
. "$(dirname "$0")/smoke_common.sh"

run_cli git_mirror --help
run_cli git_mirror --version
run_cli gh_mirror --help
run_cli gh_mirror --version
run_cli gl_mirror --help
run_cli gl_mirror --version
run_cli sh_mirror --help
run_cli sh_mirror --version
