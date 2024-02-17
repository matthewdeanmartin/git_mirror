"""
Public interface with github.

This should use manage_config, manage_git, manage_pypi for things that are not github specific.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

import git as g
import github as gh
import github.AuthenticatedUser as ghau
import github.NamedUser as ghnu
import github.Repository as ghr
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from termcolor import colored

from git_mirror.manage_git import extract_repo_name
from git_mirror.manage_pypi import PyPiManager, pretty_print_pypi_results
from git_mirror.types import SourceHost

load_dotenv()  # Load environment variables from a .env file, if present

# Configure logging
LOGGER = logging.getLogger(__name__)


class GithubRepoManager(SourceHost):
    def __init__(
        self, token: str, base_dir: Path, user_login: str, include_private: bool = True, include_forks: bool = False
    ):
        """
        Initializes the RepoManager with a GitHub token and a base directory for cloning repositories.

        Args:
            token (str): GitHub personal access token.
            base_dir (Path): Base directory path where repositories will be cloned.
            user_login (str): The GitHub username.
            include_private (bool): Whether to include private repositories.
            include_forks (bool): Whether to include forked repositories.
        """
        self.github = gh.Github(token)
        self.base_dir = base_dir
        # cache user
        self.user: Optional[Union[ghnu.NamedUser, ghau.AuthenticatedUser]] = None
        self.user_login = user_login
        self.include_private = include_private
        self.include_forks = include_forks
        LOGGER.debug(
            f"GithubRepoManager initialized with user_login: {user_login}, include_private: {include_private}, include_forks: {include_forks}"
        )

    def _get_user_repos(
        self,
    ) -> list[ghr.Repository]:
        """
        Fetches the user's repositories from GitHub, optionally including private repositories and forks.

        Returns:
            List[Repository]: A list of Repository objects.
        """
        if not self.user:
            self.user = self.github.get_user()

        try:
            repos = []
            for repo in self.user.get_repos():
                if (
                    (self.include_private or not repo.private)
                    and (self.include_forks or not repo.fork)
                    and repo.owner.login == self.user_login
                ):
                    repos.append(repo)

            return repos
        except gh.GithubException as e:
            LOGGER.error(f"Failed to fetch repositories: {e}")
            return []

    def clone_all(self):
        repos = self._get_user_repos()
        for repo in repos:
            self._clone_repo(repo)

    def _clone_repo(self, repo: ghr.Repository) -> None:
        """
        Clones the given repository into the target directory.

        Args:
            repo (Repository): The repository to clone.
        """
        try:
            if not (self.base_dir / repo.name).exists():
                LOGGER.info(f"Cloning {repo.html_url} into {self.base_dir}")
                g.Repo.clone_from(f"{repo.html_url}.git", self.base_dir / repo.name)
            else:
                LOGGER.info(f"Repository {repo.name} already exists locally. Skipping clone.")
        except g.GitCommandError as e:
            LOGGER.error(f"Failed to clone {repo.name}: {e}")

    def pull_all(self):
        for repo_dir in self.base_dir.iterdir():
            if repo_dir.is_dir():
                self.pull_repo(repo_dir)

    def pull_repo(self, repo_path: Path) -> None:
        """
        Performs a git pull operation on the repository at the given path.

        Args:
            repo_path (Path): The path to the repository.
        """
        try:
            repo = g.Repo(repo_path)
            origin = repo.remotes.origin
            LOGGER.info(f"Pulling latest changes in {repo_path}")
            origin.pull()
        except Exception as e:
            LOGGER.error(f"Failed to pull repo at {repo_path}: {e}")

    def not_repo(self) -> tuple[int, int, int, int]:
        """
        Lists directories in the base directory that are not valid Git repositories,
        or are not owned by the user, or are forks of another repository.

        Uses both git and github because of fork checking.
        """
        user_repos = {repo.name: repo for repo in self._get_user_repos()}

        no_remote = 0
        not_found = 0
        is_fork = 0
        not_repo = 0
        for repo_dir in self.base_dir.iterdir():
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    remotes = repo.remotes
                    if not remotes:
                        no_remote += 1
                        LOGGER.info(f"{repo_dir} has no remote repositories defined.")
                        continue

                    remote_url = remotes[0].config_reader.get("url")
                    repo_name = extract_repo_name(remote_url)

                    if repo_name not in user_repos:
                        not_found += 1
                        LOGGER.info(f"{repo_dir} is not found in your GitHub account.")
                        continue

                    github_repo = user_repos[repo_name]
                    if github_repo.fork:
                        is_fork += 1
                        LOGGER.info(f"{repo_dir} is a fork of another repository.")
                        continue

                except g.InvalidGitRepositoryError:
                    not_repo += 1
                    LOGGER.info(f"{repo_dir} is not a valid Git repository.")
        return no_remote, not_found, is_fork, not_repo

    def list_repo_builds(self) -> list[tuple[str, str]]:
        """
        Lists the most recent GitHub Actions workflow runs for each repository of the authenticated user,
        with the status color-coded: green for success, red for failure, and yellow for cancelled.
        """
        if not self.user:
            self.user = self.github.get_user()

        messages = []
        for repo in self._get_user_repos():
            print(f"Repository: {repo.name}")
            statuses = repo.get_workflow_runs()
            messages.extend(self._loop_actions(statuses))
        return messages

    def _loop_actions(self, statuses) -> list[tuple[str, str]]:
        actions_per_repo = 1
        status_count = 0
        messages = []
        for action in statuses:
            if status_count >= actions_per_repo:
                break
            status_count += 1

            status_message = f"Date: {action.created_at} - {action.display_title} - Conclusion - {action.conclusion}  Status: {action.status} - URL: {action.html_url}"
            conclusion = (action.conclusion or "").lower()
            messages.append((conclusion, status_message))
            if conclusion == "success":
                print(colored(status_message, "green"))
            elif conclusion == "failure":
                print(colored(status_message, "red"))
            elif conclusion == "cancelled":
                print(colored(status_message, "yellow"))
            else:
                print(status_message)  # Default, no color
        return messages

    def check_pypi_publish_status(self, pypi_owner_name: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Checks if the repositories as Python packages are published on PyPI and compares the last change dates.
        """
        results = []
        if pypi_owner_name:
            pypi_owner_name = pypi_owner_name.strip().lower()
        pypi_manager = PyPiManager()
        for repo_dir in self.base_dir.iterdir():
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    package_name = repo_dir.name  # Assuming the repo name is the package name

                    pypi_data, status_code = pypi_manager.get_info(package_name)
                    any_owner_is_fine = pypi_owner_name is None
                    i_am_owner = pypi_owner_name == pypi_data.get("info", {}).get("author", "").strip().lower()

                    if status_code == 200 and (any_owner_is_fine or i_am_owner):
                        pypi_release_date = PyPiManager._get_latest_pypi_release_date(pypi_data)

                        repo_last_commit_date = self._get_latest_commit_date(repo)
                        days_difference = (pypi_release_date - repo_last_commit_date).days

                        results.append(
                            {
                                "Package": package_name,
                                "On PyPI": "Yes",
                                "Pypi Owner": pypi_data.get("info", {}).get("author"),
                                "Repo last change date": repo_last_commit_date.date(),
                                "PyPI last change date": pypi_release_date.date(),
                                "Days difference": days_difference,
                            }
                        )
                except g.InvalidGitRepositoryError:
                    LOGGER.warning(f"{repo_dir} is not a valid Git repository.")
                except Exception as e:
                    LOGGER.error(f"Error checking {repo_dir}: {e}")
        print(pretty_print_pypi_results(results))
        return results

    @classmethod
    def _get_latest_commit_date(self, repo: g.Repo) -> datetime:
        """
        Gets the date of the latest commit in the repository.

        Args:
            repo (Repo): The repository object.

        Returns:
            datetime: The datetime of the latest commit.
        """
        last_commit = next(repo.iter_commits())
        return datetime.fromtimestamp(last_commit.committed_date)

    def list_repo_names(self) -> list[str]:
        """
        Returns a list of repository names.

        Returns:
            List[str]: A list of repository names.
        """
        return [repo.full_name for repo in self._get_user_repos()]

    def list_repos(self) -> Optional[Table]:
        """
        Fetches and prints beautifully formatted information about the user's GitHub repositories.
        """
        try:
            user = self.github.get_user(self.user_login)
            repos = user.get_repos()
            table = Table(title="GitHub Repositories")

            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description", style="magenta")
            # table.add_column("URL", style="green")
            table.add_column("Private", style="red")
            table.add_column("Fork", style="blue")

            for repo in repos:
                if (self.include_private or not repo.private) and (self.include_forks or not repo.fork):
                    table.add_row(
                        repo.name,
                        repo.description or "No description",
                        # repo.html_url, # doesn't fit
                        "Yes" if repo.private else "No",
                        "Yes" if repo.fork else "No",
                    )

            console = Console()
            console.print(table)
            return table
        except gh.GithubException as e:
            print(f"An error occurred: {e}")
        return None

    def print_user_summary(self) -> None:
        """
        Fetches and prints a summary of the user's GitHub account.
        """
        console = Console()
        try:
            user = self.github.get_user(self.user_login)
            summary = Text.assemble(
                ("Username: ", "bold cyan"),
                f"{user.login}\n",
                ("Name: ", "bold cyan"),
                f"{user.name}\n",
                ("Bio: ", "bold cyan"),
                f"{user.bio or 'No bio available'}\n",
                ("Public Repositories: ", "bold cyan"),
                f"{user.public_repos}\n",
                ("Followers: ", "bold cyan"),
                f"{user.followers}\n",
                ("Following: ", "bold cyan"),
                f"{user.following}\n",
                ("Location: ", "bold cyan"),
                f"{user.location or 'Not specified'}\n",
                ("Company: ", "bold cyan"),
                f"{user.company or 'Not specified'}",
            )
            console.print(Panel(summary, title="GitHub User Summary", subtitle=user.login))
        except gh.GithubException as e:
            console.print(f"An error occurred: {e}", style="bold red")
