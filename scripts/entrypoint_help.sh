#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=scripts/smoke_common.sh
. "$(dirname "$0")/smoke_common.sh"

run_cli gh_mirror list-config --help
run_cli gh_mirror doctor --help
run_cli gl_mirror list-config --help
run_cli gl_mirror doctor --help
run_cli sh_mirror list-config --help
run_cli sh_mirror doctor --help
