"""
Pure git actions.
"""

import logging
import multiprocessing
import os
from pathlib import Path

import git as g

from git_mirror.performance import log_duration
from git_mirror.safe_env import load_env
from git_mirror.ui import console_with_theme

load_env()

# Configure logging
LOGGER = logging.getLogger(__name__)


def find_git_repos(base_dir: Path) -> list[Path]:
    """
    Recursively finds all Git repositories in the given base directory using two methods:
    First, it uses `os.walk`, and then it uses `pathlib.Path.rglob` to ensure no repositories are missed.

    Args:
        base_dir (Path): The base directory to search for Git repositories.

    Returns:
        List[Path]: A list of Paths representing the Git repositories found.
    """
    git_repos_set = set()

    # Rlgob is 2x slower
    for root, dirs, _ in os.walk(base_dir):
        if ".git" in dirs:
            git_repos_set.add(Path(root))

    git_repos = list(git_repos_set)
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
        prompt_for_changes: bool = True,
    ):
        """
        Initializes base directory for git operations.

        Args:
            base_dir (Path): Base directory path where repositories will be cloned.
            dry_run (bool): Flag to determine whether the operation should be a dry run.
            prompt_for_changes (bool): Flag to determine whether the operation should prompt for changes.
        """
        self.base_dir = base_dir
        self.dry_run = dry_run
        self.prompt_for_changes = prompt_for_changes

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

    @log_duration
    def check_for_uncommitted_or_unpushed_changes(self, single_threaded: bool = False) -> int:
        """
        Checks all local repositories for uncommitted changes or commits that haven't been pushed to the remote.
        """
        console = console_with_theme()
        repos = list(find_git_repos(self.base_dir))
        console.print(f"Checking {len(repos)} repositories for uncommitted changes and unpushed commits.")
        have_uncommitted = 0
        if single_threaded or len(repos) < 2:
            for repo_dir in repos:
                have_uncommitted += self.check_single_repo(repo_dir)
        else:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                # TODO: may need to figure out how to add a lock for print()
                # manager = multiprocessing.Manager()
                # lock = manager.Lock()
                results = pool.starmap(self.check_single_repo, [(repo_dir,) for repo_dir in repos])
                have_uncommitted = sum(results)
        if have_uncommitted == 0:
            console.print("All repositories are clean, no uncommitted changes.")
        return have_uncommitted

    def check_single_repo(self, repo_dir: Path) -> int:
        console = console_with_theme()
        have_uncommitted = 0
        if repo_dir.is_dir():
            try:
                repo = g.Repo(repo_dir)
                conclusion = ""
                if repo.is_dirty(untracked_files=True):
                    conclusion = f"{repo_dir} has uncommitted changes."
                    have_uncommitted = 1
                else:
                    LOGGER.debug(f"{repo_dir} has no uncommitted changes.")

                if conclusion:
                    console.print(conclusion)

                self._check_for_unpushed_commits(repo, repo_dir)

            except g.InvalidGitRepositoryError:
                console.print(f"{repo_dir} is not a valid Git repository.")
            except Exception as e:
                console.print(f"Error checking {repo_dir}: {e}", style="danger")
        return have_uncommitted

    def _check_for_unpushed_commits(self, repo: g.Repo, repo_dir: Path) -> int:
        """
        Checks if the repository has commits that haven't been pushed to its tracked remote branches.

        Args:
            repo (Repo): The repository object.
            repo_dir (Path): The directory of the repository.
        """
        console = console_with_theme()
        branches_checked = 0
        for branch in repo.heads:  # branches. Mypy doesn't like the alias.
            branches_checked += 1
            try:
                # Compare local branch commit with remote branch commit
                if branch.tracking_branch():
                    ahead_count, _behind_count = repo.iter_commits(
                        f"{branch}..{branch.tracking_branch()}"
                    ), repo.iter_commits(f"{branch.tracking_branch()}..{branch}")
                    if sum(1 for _ in ahead_count) > 0:
                        console.print(f"{repo_dir} has unpushed commits on branch {branch}.")
                    else:
                        LOGGER.info(f"{repo_dir} is up to date with remote on branch {branch}.")
                else:
                    console.print(f"{repo_dir} branch {branch} does not track a remote.")
            except g.GitCommandError as e:
                message = f"Error checking for unpushed commits in {repo_dir} on branch {branch}: {e}"
                console.print(message, style="danger")
        return branches_checked
