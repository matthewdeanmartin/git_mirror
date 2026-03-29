#!/usr/bin/env bash
set -euo pipefail

SMOKE_ROOT="${SMOKE_ROOT:-$(mktemp -d)}"
export HOME="$SMOKE_ROOT/home"
export XDG_CACHE_HOME="$SMOKE_ROOT/xdg-cache"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.uv-cache}"
export HISTFILE="$SMOKE_ROOT/bash_history"
export PYTHON_KEYRING_BACKEND="keyring.backends.null.Keyring"
export PYTEST_CURRENT_TEST="smoke"
export GITHUB_ACCESS_TOKEN="${GITHUB_ACCESS_TOKEN:-smoke-token}"
export GITLAB_ACCESS_TOKEN="${GITLAB_ACCESS_TOKEN:-smoke-token}"
export SELFHOSTED_ACCESS_TOKEN="${SELFHOSTED_ACCESS_TOKEN:-smoke-token}"

mkdir -p "$HOME" "$XDG_CACHE_HOME" "$SMOKE_ROOT/target"

CONFIG_PATH="$SMOKE_ROOT/git_mirror.toml"
TARGET_DIR="$SMOKE_ROOT/target"

cleanup() {
    rm -rf "$SMOKE_ROOT"
}

trap cleanup EXIT

run_smoke() {
    printf '==> %s\n' "$*"
    "$@"
}
