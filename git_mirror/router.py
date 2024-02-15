"""
Sends the cli commands to the right method
"""

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

import git_mirror.manage_config as mc
import git_mirror.manage_git as mg
import git_mirror.manage_github as mgh
import git_mirror.manage_gitlab as mgl
from git_mirror.types import SourceHost

load_dotenv()  # Load environment variables from a .env file, if present

# Configure logging
LOGGER = logging.getLogger(__name__)


def main_github(
    command: str,
    user_name: str,
    target_dir: Path,
    token: str,
    host: str,
    include_private: bool,
    include_forks: bool,
    config_path: Optional[Path] = None,
    pypi_owner_name: Optional[str] = None,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        user_name (str): The GitHub username.
        target_dir (Path): The directory where repositories will be cloned or pulled.
        token (str): The GitHub access token.
        host (str): The source host.
        include_private (bool): Flag to determine whether private repositories should be included.
        include_forks (bool): Flag to determine whether forked repositories should be included.
        config_path (Path): Path to the TOML config file.
        pypi_owner_name (str): The PyPI owner name to filter the results.
    """
    if config_path is None:
        config_path = Path(os.getcwd()) / "pyproject.toml"

    base_path = Path(target_dir).expanduser()

    if host == "github":
        manager: SourceHost = mgh.GithubRepoManager(
            token, base_path, user_name, include_private=include_private, include_forks=include_forks
        )
    elif host == "gitlab":
        manager = mgl.GitlabRepoManager(
            token, base_path, user_name, include_private=include_private, include_forks=include_forks
        )
    else:
        raise ValueError(f"Unknown host: {host}")

    if command == "clone-all":
        manager.clone_all()
    elif command == "pull-all":
        manager.pull_all()
    elif command == "not-repo":
        manager.not_repo()
    elif command == "build-status":
        manager.list_repo_builds()
    elif command == "local-changes":
        git_manager = mg.GitManager(base_path)
        git_manager.check_for_uncommitted_or_unpushed_changes()
    elif command == "sync-config":
        config_manager = mc.ConfigManager(manager.list_repo_names(), host)
        config_manager.load_and_sync_config(toml_path=config_path)
    elif command == "pypi-status":
        manager.check_pypi_publish_status(pypi_owner_name=pypi_owner_name)
    else:
        LOGGER.error(f"Unknown command: {command}")
