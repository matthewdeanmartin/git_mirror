"""
Public interface with github.

This should use manage_config, manage_git, manage_pypi for things that are not github specific.
"""

import asyncio
import logging
import multiprocessing
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Optional, Union

import git as g
import github as gh
import github.AuthenticatedUser as ghau
import github.NamedUser as ghnu
import github.Repository as ghr
import httpx
import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from termcolor import colored

import git_mirror.manage_git as mg
from git_mirror.cross_repo_sync import TemplateSync
from git_mirror.custom_types import SourceHost, UpdateBranchArgs
from git_mirror.manage_pypi import PyPiManager, pretty_print_pypi_results
from git_mirror.safe_env import load_env

load_env()

# Configure logging
LOGGER = logging.getLogger(__name__)


class GithubRepoManager(SourceHost):
    def __init__(
        self,
        token: str,
        base_dir: Path,
        user_login: str,
        include_private: bool = True,
        include_forks: bool = False,
        host_domain: str = "https://github.com",
        dry_run: bool = False,
    ):
        """
        Initializes the RepoManager with a GitHub token and a base directory for cloning repositories.

        Args:
            token (str): GitHub personal access token.
            base_dir (Path): Base directory path where repositories will be cloned.
            user_login (str): The GitHub username.
            include_private (bool): Whether to include private repositories.
            include_forks (bool): Whether to include forked repositories.
            host_domain (str): The domain of the GitHub instance.
            dry_run (bool): Whether to perform a dry run.
        """
        self.github = gh.Github(token)
        self.base_dir = base_dir
        # cache user
        self.user: Optional[Union[ghnu.NamedUser, ghau.AuthenticatedUser]] = None
        self.user_login = user_login
        self.include_private = include_private
        self.include_forks = include_forks
        self.host_domain = host_domain
        self.dry_run = dry_run
        LOGGER.debug(
            f"GithubRepoManager initialized with user_login: {user_login}, include_private: {include_private}, include_forks: {include_forks}"
        )

    def _get_user_repos(
        self,
    ) -> list[ghr.Repository]:
        """
        Fetches the user's repositories from GitHub, optionally including private repositories and forks.

        Returns:
            list[Repository]: A list of Repository objects.
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

    def clone_all(self, single_threaded: bool = False):
        repos = self._get_user_repos()
        print(f"Cloning {len(repos)} repositories.")
        if single_threaded or len(repos) < 4:
            for repo in repos:
                print(self._clone_repo(repo))
        else:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                results = pool.map(self._clone_repo, repos)
                for output in results:
                    if output:
                        print(output, end="")

    def _clone_repo(self, repo: ghr.Repository) -> str:
        """
        Clones the given repository into the target directory.

        Args:
            repo (Repository): The repository to clone.

        Returns:
        str: The captured print output.
        """
        # Redirect stdout to capture print output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            if not (self.base_dir / repo.name).exists():
                if not self.dry_run:
                    message = f"Cloning {repo.html_url} into {self.base_dir}"
                    print(message)
                    g.Repo.clone_from(f"{repo.html_url}.git", self.base_dir / repo.name)
                else:
                    message = f"Would have cloned {repo.html_url} into {self.base_dir}"
                    print(message)
            else:
                message = f"Repository {repo.name} already exists locally. Skipping clone."
                print(message)
        except g.GitCommandError as e:
            message = f"Failed to clone {repo.name}: {e}"
            print(message)
        finally:
            # Restore stdout
            sys.stdout = old_stdout
        return captured_output.getvalue()

    def pull_all(self, single_threaded: bool = False):
        directories = mg.find_git_repos(self.base_dir)
        print(f"Pulling {len(directories)} repositories.")
        if single_threaded or len(directories) < 4:
            for repo_dir in directories:
                self.pull_repo(repo_dir)
        else:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                results = pool.map(self.pull_repo, (print(repo_dir) or repo_dir for repo_dir in directories))
                for output in results:
                    if output:
                        print(output, end="")

    def pull_repo(self, repo_path: Path) -> str:
        """
        Performs a git pull operation on the repository at the given path.

        Args:
            repo_path (Path): The path to the repository.

        Returns:
            str: The captured print output.
        """
        # Redirect stdout to capture print output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            repo = g.Repo(repo_path)
            origin = repo.remotes.origin
            if not self.dry_run:
                print(f"Pulling latest changes in {repo_path}")
                origin.pull()
            else:
                print(f"Would have pulled latest changes in {repo_path}")
        except Exception as e:
            print(f"Failed to pull repo at {repo_path}: {e}")
        finally:
            # Restore stdout
            sys.stdout = old_stdout
        return captured_output.getvalue()

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
        for repo_dir in mg.find_git_repos(self.base_dir):
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    remotes = repo.remotes
                    if not remotes:
                        no_remote += 1
                        print(f"{repo_dir} has no remote repositories defined.")
                        continue

                    remote_url = remotes[0].config_reader.get("url")
                    repo_name = mg.extract_repo_name(remote_url)

                    if repo_name not in user_repos:
                        not_found += 1
                        print(f"{repo_dir} is not found in your GitHub account.")
                        continue

                    github_repo = user_repos[repo_name]
                    if github_repo.fork:
                        is_fork += 1
                        print(f"{repo_dir} is a fork of another repository.")
                        continue

                except g.InvalidGitRepositoryError:
                    not_repo += 1
                    print(f"{repo_dir} is not a valid Git repository.")
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

        async def get_infos_async(package_names):
            pypi_manager = PyPiManager()
            return await pypi_manager.get_infos(package_names)

        package_names = [path.name for path in mg.find_git_repos(self.base_dir)]
        package_infos = asyncio.run(get_infos_async(package_names))

        for repo_dir in mg.find_git_repos(self.base_dir):
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    package_name = repo_dir.name  # Assuming the repo name is the package name

                    pypi_data, status_code = package_infos[package_name]
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

    def update_all_branches(self, single_threaded: bool = False, prefer_rebase: bool = False):
        """
        Updates each local branch with the latest changes from the main/master branch on GitHub.

        Args:
            single_threaded (bool): Whether to run the operation in a single thread.
            prefer_rebase (bool): Whether to prefer rebasing instead of merging.
        """
        directories = mg.find_git_repos(self.base_dir)
        print(f"Merging/rebasing {len(directories)} main to local repositories.")
        if single_threaded or len(directories) < 4:
            for repo_dir in directories:
                self._update_local_branches(UpdateBranchArgs(repo_dir, repo_dir.name, prefer_rebase))
        else:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                results = pool.map(
                    self._update_local_branches,
                    (UpdateBranchArgs(repo_dir, repo_dir.name, prefer_rebase) for repo_dir in directories),
                )
                for output in results:
                    if output:
                        if output:
                            print(output, end="")

    # def _update_local_branches(self, repo_path: Path, github_repo_full_name: str, prefer_rebase: bool = False):
    def _update_local_branches(self, args: UpdateBranchArgs):
        """
        Updates each local branch with the latest changes from the main/master branch on GitHub.

        Args:
            args: UpdateBranchArgs
        """
        repo_path, github_repo_full_name, prefer_rebase = args.repo_path, args.github_repo_full_name, args.prefer_rebase
        github_repo_full_name = self.user_login + "/" + github_repo_full_name
        repo = g.Repo(str(repo_path))
        try:
            github_repo = self.github.get_repo(github_repo_full_name)
        except gh.GithubException as e:
            print(f"Failed to retrieve info on GitHub repository {github_repo_full_name}: {e}")
            return
        # Get the default branch name from GitHub
        default_branch = github_repo.default_branch

        # Fetch all changes from remote
        origin = repo.remotes.origin
        if not self.dry_run:
            origin.fetch()

        # Update each local branch
        for branch in repo.heads:  # branches, but mypy doesn't like the alias
            try:
                if branch.name == default_branch:
                    continue
                if not self.dry_run:
                    # Checkout the branch
                    repo.git.checkout(branch)
                    # Ensure the branch is up to date with its upstream
                    repo.git.pull()

                    if prefer_rebase:
                        # Perform rebase
                        repo.git.rebase(f"origin/{default_branch}")
                    else:
                        # Perform merge
                        repo.git.merge(f"origin/{default_branch}")

                    print(f"Updated branch '{branch}' with latest changes from '{default_branch}'.")
                else:
                    print(f"Would have updated branch '{branch}' with latest changes from '{default_branch}'.")
            except g.exc.GitCommandError as e:
                print(f"Failed to update branch '{branch}': {e}")

    def prune_all(self) -> None:
        for repo_dir in mg.find_git_repos(self.base_dir):
            if repo_dir.is_dir():
                self._delete_local_branches_if_not_on_github(repo_dir, f"{self.user_login}/{repo_dir.name}")

    def _delete_local_branches_if_not_on_github(self, repo_path: Path, github_repo_full_name: str):
        """
        Loops through all local branches, checks if they exist on GitHub, and prompts the user for deletion if they don't.

        Args:
            repo_path (Path): The file system path to the local git repository.
            github_repo_full_name (str): The full name of the GitHub repository (e.g., "owner/repo").
        """
        # Initialize GitHub client and GitPython Repo
        try:
            repo = g.Repo(str(repo_path))
        except g.InvalidGitRepositoryError:
            print(f"{repo_path} is not a valid Git repository.")
            return
        try:
            github_repo = self.github.get_repo(github_repo_full_name)
        except gh.GithubException as e:
            print(f"Failed to retrieve info on GitHub repository {github_repo_full_name}: {e}")
            return

        # Get a list of all branch names on GitHub
        remote_branches = [branch.name for branch in github_repo.get_branches()]

        # Get a list of all local branch names
        local_branches = [branch.name for branch in repo.heads]  # alias to branches

        # Determine branches that are local but not on GitHub
        branches_to_consider = [branch for branch in local_branches if branch not in remote_branches]

        if not branches_to_consider:
            print(f"For {github_repo_full_name}, no local branches exist that are missing on GitHub.")
            return

        # Prompt user for each branch that doesn't exist on GitHub
        for branch in branches_to_consider:
            question = [
                inquirer.Confirm(
                    "delete", message=f"The branch '{branch}' does not exist on GitHub. Delete locally?", default=False
                )
            ]
            answer = inquirer.prompt(question)

            if answer["delete"]:
                try:
                    if not self.dry_run:
                        # Safely delete the branch
                        repo.git.branch("-d", branch)
                        print(f"Deleted branch '{branch}' locally.")
                    else:
                        print(f"Would have deleted branch '{branch}' locally.")
                except g.exc.GitCommandError as e:
                    print(f"Could not delete branch '{branch}'. It may not be fully merged. Error: {e}")
            else:
                print(f"Skipped deletion of branch '{branch}'.")

    def version_info(self) -> dict[str, Any]:
        """
        Return API version information.
        """
        # pygithub doesn't support this endpoint?
        response = httpx.get(f"{self.host_domain}/versions")
        response.raise_for_status()  # Raises an exception for 4XX/5XX responses
        data = response.json()
        versions_supported = data["info"]["version"]
        return {"version": versions_supported}

    def cross_repo_sync_report(self, template_dir: Path) -> None:
        """
        Reports differences between the template directory and the target directories.
        """
        if not template_dir or not template_dir.exists():
            print(f"Template directory {template_dir} does not exist.")
            return
        # right now just the easy case of all repos need to match 1 template_dir
        print("Reporting differences between the template directory and the target directories.")
        syncer = TemplateSync(template_dir)
        directories = mg.find_git_repos(self.base_dir)
        print(f"Found {len(directories)} repositories.")
        syncer.report_content_differences(directories)

    def cross_repo_init(self, template_dir: Path):
        if not template_dir or not template_dir.exists():
            print(f"Template directory {template_dir} does not exist.")
            return
        syncer = TemplateSync(template_dir, use_default=True)
        directories = mg.find_git_repos(self.base_dir)
        print(f"Found {len(directories)} repositories.")
        syncer.write_template_map(directories)
        print(f"Initialized template map for {len(directories)} repositories.")

    def cross_repo_sync(self, template_dir: Path):
        if not template_dir or not template_dir.exists():
            print(f"Template directory {template_dir} does not exist.")
            return
        syncer = TemplateSync(template_dir, use_default=True)
        directories = mg.find_git_repos(self.base_dir)
        print(f"Found {len(directories)} repositories.")
        syncer.sync_template(directories)
        print(f"Synchronized {len(directories)} repositories with the template directory.")

    def merge_request(
        self, source_branch: str, target_branch: str, title: str, reviewer: str, project_id: int, repo_name: str
    ) -> None:
        """
        Create a pull request on GitHub and assign a reviewer.

        Args:
            source_branch: The name of the source branch for the pull request.
            target_branch: The name of the target branch for the pull request.
            title: The title of the pull request.
            reviewer: GitHub username of the reviewer.
            project_id: The ID of the GitLab project (unused here).
            repo_name: The name of the repository, e.g., "user/repo".

        Returns:
            None
        """
        repo = self.github.get_repo(repo_name)
        if not self.user:
            self.user = self.github.get_user()

        # Create pull request
        pull_request = repo.create_pull(
            title=title,
            body=title,  # Customize the body message as needed
            head=source_branch,
            base=target_branch,
            maintainer_can_modify=True,  # Allows maintainer to modify the PR if needed
        )

        # Assign user and request a review
        pull_request.assignees.append(self.user)  # type: ignore
        pull_request.create_review_request(reviewers=[reviewer])

        print(f"Pull request created: {pull_request.html_url}")
