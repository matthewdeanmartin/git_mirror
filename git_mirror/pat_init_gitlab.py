import getpass
import logging
import os
from pathlib import Path

import httpx
from dotenv import find_dotenv, load_dotenv, set_key

LOGGER = logging.getLogger(__name__)


def check_pat_validity(token: str) -> bool:
    """
    Check if the GitLab Personal Access Token (PAT) is still valid.

    Args:
        token (str): The GitLab Personal Access Token.

    Returns:
        bool: True if the token is valid, False otherwise.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get("https://gitlab.com/api/v4/user", headers=headers)
        return response.status_code == 200
    except httpx.RequestError as e:
        print(f"An error occurred while checking PAT validity: {e}")
        return False


def setup_gitlab_pat() -> None:
    """
    Setup the GitLab Personal Access Token (PAT) either globally or locally.
    Checks if it exists and is valid, then asks the user for their preference
    on storing the PAT.
    """
    # Attempt to load existing .env and check for existing PAT
    dotenv_path = Path(find_dotenv())
    load_dotenv(dotenv_path)
    existing_pat = os.getenv("GITLAB_ACCESS_TOKEN")

    # Check validity of an existing PAT
    if existing_pat and check_pat_validity(existing_pat):
        print("Existing PAT is valid.")
        return
    else:
        print("No valid PAT found.")

    print("https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html")
    # Ask for new PAT
    new_pat = getpass.getpass("Enter your new GitLab PAT: ")

    # Validate the new PAT
    if not check_pat_validity(new_pat):
        print("The provided PAT is invalid.")
        return

    # Ask user for global or local setup
    choice = (
        input("Do you want to save the PAT globally or locally? [G/L]. If you don't know, select globally. ")
        .strip()
        .lower()
    )

    if choice == "g":
        home_path = Path.home() / ".env"
        set_key(home_path, "GITLAB_ACCESS_TOKEN", new_pat)
        print(f"PAT saved globally in {home_path}")
    elif choice == "l":
        local_path = Path(".env")
        set_key(local_path, "GITLAB_ACCESS_TOKEN", new_pat)
        print(f"PAT saved locally in {local_path}")
    else:
        print("Invalid option selected. PAT setup aborted.")


if __name__ == "__main__":
    setup_gitlab_pat()
