"""
Pure git actions.
"""

import logging
from pathlib import Path

import git as g
from dotenv import load_dotenv
from termcolor import colored

load_dotenv()  # Load environment variables from a .env file, if present

# Configure logging
LOGGER = logging.getLogger(__name__)


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
    ):
        """
        Initializes base directory for git operations.

        Args:
            base_dir (Path): Base directory path where repositories will be cloned.
        """
        self.base_dir = base_dir

    def check_for_uncommitted_or_unpushed_changes(self) -> list[str]:
        """
        Checks all local repositories for uncommitted changes or commits that haven't been pushed to the remote.
        """
        messages = []
        for repo_dir in self.base_dir.iterdir():
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    conclusion = ""
                    if repo.is_dirty(untracked_files=True):
                        conclusion = f"{repo_dir} has uncommitted changes."
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
