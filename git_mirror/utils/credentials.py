"""
Credential storage seam.

git_mirror historically stored Personal Access Tokens as plaintext in ``~/.env``
or ``./.env``.  This module introduces an OS-keychain-backed store (via the
``keyring`` package) while keeping the old ``.env`` / environment-variable path
working for CI and for users who have not migrated.

Resolution order for reads (first hit wins):

1. **Process environment variable** -- an explicit ``GITHUB_ACCESS_TOKEN`` /
   ``SELFHOSTED_ACCESS_TOKEN`` exported before launch.  This is what CI uses and
   it must stay predictable, so it wins.
2. **OS keychain** (``keyring``) -- the recommended storage from 2.0 onward.
3. **``.env`` file** -- legacy plaintext, loaded via ``python-dotenv``.

Writes default to the keychain.
"""

from __future__ import annotations

import logging
import os
from enum import Enum

from git_mirror.utils.ui import console_with_theme

LOGGER = logging.getLogger(__name__)

console = console_with_theme()

# keyring service name; the "username" is the host_name (github / selfhosted).
SERVICE_NAME = "git_mirror"

# host_name -> environment variable that holds its token.
ENV_VAR_BY_HOST = {
    "github": "GITHUB_ACCESS_TOKEN",
    "selfhosted": "SELFHOSTED_ACCESS_TOKEN",
}


def env_var_for_host(host_name: str) -> str:
    """Return the environment-variable name used for a host's token."""
    return ENV_VAR_BY_HOST.get(host_name, "GITHUB_ACCESS_TOKEN")


class TokenSource(str, Enum):
    """Where a token was resolved from, for diagnostics (doctor)."""

    ENV = "environment variable"
    KEYRING = "OS keychain"
    DOTENV = ".env file"
    MISSING = "not found"


def keyring():
    """Import keyring lazily; return the module or None if unusable."""
    try:
        import keyring

        return keyring
    except Exception as exc:  # pragma: no cover - import guard # pylint: disable=broad-exception-caught
        LOGGER.debug(f"keyring unavailable: {exc}")
        return None


def keyring_get(host_name: str) -> str | None:
    kr = keyring()
    if kr is None:
        return None
    try:
        return kr.get_password(SERVICE_NAME, host_name)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        LOGGER.debug(f"keyring read failed for {host_name}: {exc}")
        return None


def dotenv_get(env_var: str) -> str | None:
    """Read a value straight from the resolved .env file without mutating env."""
    try:
        from dotenv import dotenv_values, find_dotenv
        from pathlib import Path

        values: dict[str, str | None] = {}
        home_env = Path.home() / ".env"
        if home_env.is_file():
            values.update(dotenv_values(home_env))
        found = find_dotenv(usecwd=True)
        if found:
            values.update(dotenv_values(found))
        return values.get(env_var)
    except Exception as exc:  # pragma: no cover - defensive # pylint: disable=broad-exception-caught
        LOGGER.debug(f"dotenv read failed for {env_var}: {exc}")
        return None


def resolve_token(host_name: str) -> tuple[str | None, TokenSource]:
    """Resolve a token and report where it came from.

    Note: because ``safe_env.load_env`` may already have copied ``.env`` values
    into ``os.environ`` during startup, an env-var hit can originate from a
    ``.env`` file.  We disambiguate by checking the keychain *before* trusting an
    env var that also exists verbatim in ``.env``.
    """
    env_var = env_var_for_host(host_name)
    env_value = os.environ.get(env_var)
    dotenv_value = dotenv_get(env_var)

    # A real, exported env var (one that is NOT merely the dotenv value) wins.
    if env_value and env_value != dotenv_value:
        return env_value, TokenSource.ENV

    keyring_value = keyring_get(host_name)
    if keyring_value:
        return keyring_value, TokenSource.KEYRING

    # Fall back to whatever the env holds (possibly the dotenv-loaded value).
    if env_value:
        source = TokenSource.DOTENV if env_value == dotenv_value else TokenSource.ENV
        return env_value, source

    if dotenv_value:
        return dotenv_value, TokenSource.DOTENV

    return None, TokenSource.MISSING


def get_token(host_name: str) -> str | None:
    """Return the token for a host, or None."""
    token, _ = resolve_token(host_name)
    return token


def set_token(host_name: str, token: str) -> bool:
    """Store a token in the OS keychain. Returns True on success."""
    kr = keyring()
    if kr is None:
        return False
    try:
        kr.set_password(SERVICE_NAME, host_name, token)
        # Make it visible to the current process immediately.
        os.environ[env_var_for_host(host_name)] = token
        return True
    except Exception as exc:  # pylint: disable=broad-exception-caught
        LOGGER.debug(f"keyring write failed for {host_name}: {exc}")
        console.print(f"Could not save to the OS keychain: {exc}", style="danger")
        return False


def delete_token(host_name: str) -> bool:
    """Remove a token from the OS keychain. Returns True if something was removed."""
    kr = keyring()
    if kr is None:
        return False
    try:
        kr.delete_password(SERVICE_NAME, host_name)
        return True
    except Exception as exc:
        LOGGER.debug(f"keyring delete failed for {host_name}: {exc}")
        return False


def migrate_dotenv_to_keychain(host_name: str) -> bool:
    """Copy a token found in .env/env into the keychain. Returns True if moved."""
    token, source = resolve_token(host_name)
    if not token or source == TokenSource.KEYRING:
        return False
    if set_token(host_name, token):
        console.print(f"Copied {host_name} token into the OS keychain.")
        console.print(
            "The plaintext copy in your .env file is still there; remove it manually when ready.",
            style="yellow",
        )
        return True
    return False


def keyring_available() -> bool:
    """True if a usable, non-null keyring backend is configured."""
    kr = keyring()
    if kr is None:
        return False
    try:
        backend = kr.get_keyring()
        # The null backend (used in CI/tests) is not real storage.
        return type(backend).__name__ != "Keyring" or "null" not in type(backend).__module__
    except Exception:  # pragma: no cover - defensive # pylint: disable=broad-exception-caught
        return False

