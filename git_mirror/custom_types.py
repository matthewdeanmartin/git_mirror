"""
Mypy types.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol

from rich.table import Table


@dataclass
class UpdateBranchArgs:
    repo_path: Path
    github_repo_full_name: str
    prefer_rebase: bool


class SourceHost(Protocol):
    """Just the methods that are common among hosters.
    By convention, other methods are underscored and treated as private
    """

    def clone_all(self, single_threaded: bool = False):
        pass

    def pull_all(self, single_threaded: bool = False):
        pass

    def pull_repo(self, repo_path: Path) -> str:
        """
        Performs a git pull operation on the repository at the given path.

        Args:
            repo_path (Path): The path to the repository.
        """

    def not_repo(self) -> tuple[int, int, int, int]:
        """
        Lists directories in the base directory that are not valid Git repositories,
        or are not owned by the user, or are forks of another repository.

        Uses both git and github because of fork checking.
        """

    def list_repo_builds(self) -> list[tuple[str, str]]:
        """
        Lists the most recent GitHub Actions workflow runs for each repository of the authenticated user,
        with the status color-coded: green for success, red for failure, and yellow for cancelled.
        """

    def check_pypi_publish_status(self, pypi_owner_name: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Checks if the repositories as Python packages are published on PyPI and compares the last change dates.
        """

    def list_repo_names(self) -> list[str]:
        """
        Returns a list of repository names.

        Returns:
            List[str]: A list of repository names.
        """

    def list_repos(self) -> Optional[Table]:
        """
        Fetches and prints beautifully formatted information about the user's GitHub repositories.
        """

    def print_user_summary(self) -> None:
        """
        Fetches and prints a summary of the user's GitHub account.
        """

    def update_all_branches(self, single_threaded: bool = False, prefer_rebase: bool = False):
        """
        Updates each local branch with the latest changes from the main/master branch on Source Host.
        """

    def prune_all(self):
        """
        Loops through all local branches, checks if they exist on GitHub, and prompts the user for deletion if they don't.
        """

    def version_info(self) -> dict[str, Any]:
        """
        Return API version information.
        """

    def cross_repo_sync_report(self, template_dir: Path):
        """
        Compares the template directory to the target directories and reports differences.
        """

    def cross_repo_init(self, template_dir: Path):
        pass

    def cross_repo_sync(self, template_dir: Path):
        pass

    def merge_request(
        self, source_branch: str, target_branch: str, title: str, reviewer: str, project_id: int, repo_name: str
    ):
        pass
