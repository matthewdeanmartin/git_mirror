import getpass
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import find_dotenv, load_dotenv, set_key

from git_mirror.safe_env import env_info
from git_mirror.ui import console_with_theme

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
    console.print("Checking environment...")
    env_info()
    console.print()
    dotenv_path = Path(find_dotenv())
    load_dotenv(dotenv_path)
    existing_pat = os.getenv(env_var)

    if existing_pat and check_pat_validity(existing_pat, api_url=api_url):
        console.print(f"Existing {host_label} PAT is valid.")
        return existing_pat

    console.print(f"No valid {host_label} PAT found.")
    console.print(docs_url)
    console.print("Next we will create a local or global .env file to store the PAT.")
    new_pat = getpass.getpass(f"Enter your new {host_label} PAT: ")

    if not check_pat_validity(new_pat, api_url=api_url):
        console.print("The provided PAT is invalid.")
        return None

    choice = (
        input("Do you want to save the PAT globally or locally? [G/L]. If you don't know select globally. ")
        .strip()
        .lower()
    )

    if not _save_pat(choice, env_var, new_pat):
        return None
    return new_pat


if __name__ == "__main__":
    setup_github_pat()
