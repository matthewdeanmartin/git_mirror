from __future__ import annotations

import getpass
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from dotenv import find_dotenv, load_dotenv, set_key

from git_mirror.safe_env import env_info
from git_mirror.ui import console_with_theme

LOGGER = logging.getLogger(__name__)

DEFAULT_GITLAB_URL = "https://gitlab.com"

console = console_with_theme()


def api_url(host_url: str = DEFAULT_GITLAB_URL) -> str:
    """Normalize a GitLab host URL into its API base URL."""
    raw_url = host_url.strip()
    if "://" not in raw_url:
        raw_url = f"https://{raw_url}"
    parsed = urlparse(raw_url.rstrip("/"))
    path = parsed.path.rstrip("/")
    if not path:
        path = "/api/v4"
    elif not path.startswith("/api/"):
        path = f"{path}/api/v4"
    return urlunparse(parsed._replace(path=path, params="", query="", fragment=""))


def get_authenticated_user(token: str, host_url: str = DEFAULT_GITLAB_URL) -> dict[str, Any] | None:
    """Return the authenticated GitLab user payload if the token is valid."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{api_url(host_url).rstrip('/')}/user", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except httpx.RequestError as e:
        console.print(f"An error occurred while checking PAT validity: {e}", style="danger")
        return None


def check_pat_validity(token: str, host_url: str = DEFAULT_GITLAB_URL) -> bool:
    """
    Check if the GitLab Personal Access Token (PAT) is still valid.

    Args:
        token (str): The GitLab Personal Access Token.
        host_url (str): The GitLab host base URL.

    Returns:
        bool: True if the token is valid, False otherwise.
    """
    return get_authenticated_user(token, host_url=host_url) is not None


def _save_pat(choice: str, env_var: str, new_pat: str) -> bool:
    if choice == "g":
        home_path = Path.home() / ".env"
        set_key(home_path, env_var, new_pat)
        console.print(f"PAT saved globally in {home_path}")
    elif choice == "l":
        local_path = Path(".env")
        set_key(local_path, env_var, new_pat)
        console.print(f"PAT saved locally in {local_path}")
    else:
        console.print("Invalid option selected. PAT setup aborted.")
        return False

    os.environ[env_var] = new_pat
    return True


def setup_gitlab_pat(
    env_var: str = "GITLAB_ACCESS_TOKEN",
    host_url: str = DEFAULT_GITLAB_URL,
    host_label: str = "GitLab",
    docs_url: str = "https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html",
) -> str | None:
    """
    Setup the GitLab Personal Access Token (PAT) either globally or locally.

    Returns the valid token when setup succeeds so callers can continue without requiring
    the user to restart the command.
    """
    console.print("Checking environment...")
    env_info()
    console.print()
    dotenv_path = Path(find_dotenv())
    load_dotenv(dotenv_path)
    existing_pat = os.getenv(env_var)

    if existing_pat and check_pat_validity(existing_pat, host_url=host_url):
        console.print(f"Existing {host_label} PAT is valid.")
        return existing_pat

    console.print(f"No valid {host_label} PAT found.")
    console.print(docs_url)
    console.print("Next we will create a local or global .env file to store the PAT.")
    new_pat = getpass.getpass(f"Enter your new {host_label} PAT: ")

    if not check_pat_validity(new_pat, host_url=host_url):
        console.print("The provided PAT is invalid.")
        return None

    choice = (
        input("Do you want to save the PAT globally or locally? [G/L]. If you don't know, select globally. ")
        .strip()
        .lower()
    )

    if not _save_pat(choice, env_var, new_pat):
        return None
    return new_pat


if __name__ == "__main__":
    setup_gitlab_pat()
