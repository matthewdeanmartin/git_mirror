from __future__ import annotations

import getpass
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import find_dotenv, load_dotenv, set_key

from git_mirror.utils.safe_env import env_info
from git_mirror.utils.ui import console_with_theme

LOGGER = logging.getLogger(__name__)

DEFAULT_GITHUB_API_URL = "https://api.github.com"

console = console_with_theme()


def get_authenticated_user(token: str, api_url: str = DEFAULT_GITHUB_API_URL) -> dict[str, Any] | None:
    """Return the authenticated GitHub user payload if the token is valid."""
    headers = {"Authorization": f"token {token}"}
    try:
        response = httpx.get(f"{api_url.rstrip('/')}/user", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except httpx.RequestError as e:
        console.print(f"An error occurred while checking PAT validity: {e}", style="danger")
        return None


def check_pat_validity(token: str, api_url: str = DEFAULT_GITHUB_API_URL) -> bool:
    """
    Check if the GitHub Personal Access Token (PAT) is still valid.

    Args:
        token (str): The GitHub Personal Access Token.
        api_url (str): The GitHub API base URL.

    Returns:
        bool: True if the token is valid, False otherwise.
    """
    return get_authenticated_user(token, api_url=api_url) is not None


def host_name_for_env_var(env_var: str) -> str:
    return "selfhosted" if env_var == "SELFHOSTED_ACCESS_TOKEN" else "github"


def save_pat(choice: str, env_var: str, new_pat: str) -> bool:
    if choice == "k":
        from git_mirror.utils import credentials

        host_name = host_name_for_env_var(env_var)
        if credentials.set_token(host_name, new_pat):
            console.print("PAT saved to the OS keychain.")
        else:
            console.print(
                "Could not save to the OS keychain; falling back to a global .env file.",
                style="danger",
            )
            home_path = Path.home() / ".env"
            set_key(home_path, env_var, new_pat)
            console.print(f"PAT saved globally in {home_path}")
    elif choice == "g":
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


def setup_github_pat(
    env_var: str = "GITHUB_ACCESS_TOKEN",
    api_url: str = DEFAULT_GITHUB_API_URL,
    host_label: str = "GitHub",
    docs_url: str = "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens",
) -> str | None:
    """
    Setup the GitHub Personal Access Token (PAT) either globally or locally.

    Returns the valid token when setup succeeds so callers can continue without requiring
    the user to restart the command.
    """
    from git_mirror.utils import credentials

    console.print("Checking environment...")
    env_info()
    console.print()
    dotenv_path = Path(find_dotenv())
    load_dotenv(dotenv_path)
    host_name = host_name_for_env_var(env_var)
    existing_pat = credentials.get_token(host_name)

    if existing_pat and check_pat_validity(existing_pat, api_url=api_url):
        console.print(f"Existing {host_label} PAT is valid.")
        return existing_pat

    console.print(f"No valid {host_label} PAT found.")
    console.print(docs_url)
    console.print("Next we will store the PAT. The OS keychain is recommended.")
    new_pat = getpass.getpass(f"Enter your new {host_label} PAT: ")

    if not check_pat_validity(new_pat, api_url=api_url):
        console.print("The provided PAT is invalid.")
        return None

    choice = (
        input(
            "Where do you want to save the PAT? "
            "[K]eychain (recommended), [G]lobal .env, [L]ocal .env. "
            "If you don't know, select keychain. "
        )
        .strip()
        .lower()
    ) or "k"

    if not save_pat(choice, env_var, new_pat):
        return None
    return new_pat


if __name__ == "__main__":
    setup_github_pat()
