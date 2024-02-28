import getpass
import logging
import os
from pathlib import Path

import httpx
from dotenv import find_dotenv, load_dotenv, set_key

from git_mirror.safe_env import env_info
from git_mirror.ui import console_with_theme

LOGGER = logging.getLogger(__name__)

console = console_with_theme()


def check_pat_validity(token: str) -> bool:
    """
    Check if the GitHub Personal Access Token (PAT) is still valid.

    Args:
        token (str): The GitHub Personal Access Token.

    Returns:
        bool: True if the token is valid, False otherwise.
    """
    headers = {"Authorization": f"token {token}"}
    try:
        response = httpx.get("https://api.github.com/user", headers=headers)
        return response.status_code == 200
    except httpx.RequestError as e:
        console.print(f"An error occurred while checking PAT validity: {e}", style="danger")
        return False


def setup_github_pat() -> None:
    """
    Setup the GitHub Personal Access Token (PAT) either globally or locally.
    Checks if it exists and is valid, then asks the user for their preference
    on storing the PAT.
    """
    console.print("Checking environment...")
    env_info()
    console.print()
    # Attempt to load existing .env and check for existing PAT
    dotenv_path = Path(find_dotenv())
    load_dotenv(dotenv_path)
    existing_pat = os.getenv("GITHUB_ACCESS_TOKEN")

    # Check validity of an existing PAT
    if existing_pat and check_pat_validity(existing_pat):
        console.print("Existing PAT is valid.")
        return
    else:
        console.print("No valid PAT found.")

    console.print(
        "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens"
    )

    console.print("Next we will create a local or global .env file to store the PAT.")
    # Ask for new PAT
    new_pat = getpass.getpass("Enter your new GitHub PAT: ")

    # Validate the new PAT
    if not check_pat_validity(new_pat):
        console.print("The provided PAT is invalid.")
        return

    # Ask user for global or local setup
    choice = (
        input("Do you want to save the PAT globally or locally? [G/L]. If you don't know select globally. ")
        .strip()
        .lower()
    )

    if choice == "g":
        home_path = Path.home() / ".env"
        set_key(home_path, "GITHUB_ACCESS_TOKEN", new_pat)
        console.print(f"PAT saved globally in {home_path}")
    elif choice == "l":
        local_path = Path(".env")
        set_key(local_path, "GITHUB_ACCESS_TOKEN", new_pat)
        console.print(f"PAT saved locally in {local_path}")
    else:
        console.print("Invalid option selected. PAT setup aborted.")


if __name__ == "__main__":
    setup_github_pat()
