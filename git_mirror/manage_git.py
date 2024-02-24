"""
Pure git actions.
"""

import logging
from pathlib import Path

import git as g
from termcolor import colored

from git_mirror.safe_env import load_env

load_env()

# Configure logging
LOGGER = logging.getLogger(__name__)


def find_git_repos(base_dir: Path) -> list[Path]:
    """
    Recursively finds all Git repositories in the given base directory.

    Args:
        base_dir (Path): The base directory to search for Git repositories.

    Returns:
        List[Path]: A list of Paths representing the Git repositories found.
    """
    git_repos = []

    for path in base_dir.rglob("*"):
        if path.name == ".git" and path.is_dir():
            git_repos.append(path.parent)  # Add the parent directory of '.git'

    return git_repos


def extract_repo_name(remote_url: str) -> str:
    """
    Extracts the repository name from its remote URL.

    Args:
        remote_url (str): The remote URL of the repository.

    Returns:
        str: The repository name.

    Examples:
        >>> extract_repo_name("http://example.com/user/repo.git")
        'repo'
    """
    # This handles both SSH and HTTPS URLs and assumes the default GitHub domain.
    if remote_url.endswith(".git"):
        remote_url = remote_url[:-4]
    elif remote_url.endswith(".git/"):
        remote_url = remote_url[:-5]
    parts = remote_url.split("/")
    repo_name = parts[-1]  # Assumes the URL ends with 'username/repo_name'
    return repo_name


class GitManager:
    def __init__(
        self,
        base_dir: Path,
        dry_run: bool = False,
    ):
        """
        Initializes base directory for git operations.

        Args:
            base_dir (Path): Base directory path where repositories will be cloned.
            dry_run (bool): Flag to determine whether the operation should be a dry run.
        """
        self.base_dir = base_dir

    def local_repos_with_file_in_root(self, file_name: str) -> list[Path]:
        """
        Finds local git repositories within the base directory that have a specific file in their root.

        Args:
            file_name (str): The name of the file to search for in the root of each repository.

        Returns:
            List[Path]: A list of Paths to the repositories that contain the specified file in their root directory.
        """
        found_repos = []
        for repo_dir in self.base_dir.iterdir():
            if repo_dir.is_dir() and (repo_dir / ".git").exists():
                target_file_path = repo_dir / file_name
                if target_file_path.exists():
                    LOGGER.info(f"Found {file_name} in {repo_dir}")
                    found_repos.append(repo_dir)
        return found_repos

    def check_for_uncommitted_or_unpushed_changes(self) -> list[str]:
        """
        Checks all local repositories for uncommitted changes or commits that haven't been pushed to the remote.
        """
        messages = []
        have_uncommitted = 0
        for repo_dir in find_git_repos(self.base_dir):
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    conclusion = ""
                    if repo.is_dirty(untracked_files=True):
                        conclusion = f"{repo_dir} has uncommitted changes."
                        have_uncommitted += 1
                    else:
                        LOGGER.debug(f"{repo_dir} has no uncommitted changes.")

                    if conclusion:
                        print(colored(conclusion, "red"))

                    self._check_for_unpushed_commits(repo, repo_dir)

                except g.InvalidGitRepositoryError:
                    message = f"{repo_dir} is not a valid Git repository."
                    messages.append(message)
                    LOGGER.warning(message)
                except Exception as e:
                    message = f"Error checking {repo_dir}: {e}"
                    messages.append(message)
                    LOGGER.error(message)
        if have_uncommitted == 0:
            print(colored("All repositories are clean, no uncommitted changes.", "green"))
        return messages

    def _check_for_unpushed_commits(self, repo: g.Repo, repo_dir: Path) -> list[str]:
        """
        Checks if the repository has commits that haven't been pushed to its tracked remote branches.

        Args:
            repo (Repo): The repository object.
            repo_dir (Path): The directory of the repository.
        """
        messages = []
        for branch in repo.heads:  # branches. Mypy doesn't like the alias.
            try:
                # Compare local branch commit with remote branch commit
                if branch.tracking_branch():
                    ahead_count, _behind_count = repo.iter_commits(
                        f"{branch}..{branch.tracking_branch()}"
                    ), repo.iter_commits(f"{branch.tracking_branch()}..{branch}")
                    if sum(1 for _ in ahead_count) > 0:
                        message = f"{repo_dir} has unpushed commits on branch {branch}."
                        messages.append(message)
                    else:
                        message = f"{repo_dir} is up to date with remote on branch {branch}."
                        messages.append(message)
                else:
                    message = f"{repo_dir} branch {branch} does not track a remote."
                    messages.append(message)
            except g.GitCommandError as e:
                message = f"Error checking for unpushed commits in {repo_dir} on branch {branch}: {e}"
                LOGGER.error(message)
                messages.append(message)

        return messages
