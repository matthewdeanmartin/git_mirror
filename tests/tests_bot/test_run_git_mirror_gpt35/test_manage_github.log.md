System: You are an excellent python pytest unit test engineer. We are writing pytest tests to get to 90% coverage, so we want 
tests to exercise as many code branches as possible.

First, begin by looking for bugs. There might not be any bugs. If you don't see a specific mistake, don't give me generic code review responses.

Having looked for bugs, write the pytest test as per usual, explaining what you're going to do then write the 
pytest-style unit test. Don't forget to write code!

## Tooling
Use pytest style testing. Use unittest.mock for mocking. pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.

Do not, under any circumstances, use unittest.TestCase.

The target python version is 3.10

## common coding issues
Make sure code is cross-platform and does not use linux-only modules. Prefer pathlib.Path whenever possible. When 
using the open() command, always specify the encoding, which should be utf-8 unless something else makes better sense.

## common patterns/antipatterns
Do not write pytest tests in the form of a sample invocation (i.e. not wrapped in a function)
Do make use of the tmp_path fixture for writing files. Do not mock `open` to avoid writing files.

## Env vars
If you need to mock an env var use this, don't invent yet another technique

```
from tests.env_util import temporary_env_var

with temporary_env_var("NAME", "mock_value", "NAME2", "mock_value2"):
	assert os.environ["NAME"] == "mock_value"
	assert os.environ["NAME2"] == "mock_value2"
```

Library is named git_mirror.
User: 
Source Path: E:\github\git_mirror\git_mirror\manage_github.py

Source Path: E:\github\git_mirror\git_mirror\manage_github.py
Module Name: git_mirror.manage_github
```python
"""
Public interface with github.

This should use manage_config, manage_git, manage_pypi for things that are not github specific.
"""

import asyncio
import logging
import multiprocessing
from datetime import datetime
from pathlib import Path
from typing import Any, ContextManager, Optional, Union

import git as g
import github as gh
import github.AuthenticatedUser as ghau
import github.NamedUser as ghnu
import github.Repository as ghr
import httpx
import inquirer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from termcolor import colored

import git_mirror.manage_git as mg
from git_mirror.cross_repo_sync import TemplateSync
from git_mirror.custom_types import SourceHost, UpdateBranchArgs
from git_mirror.dummies import Dummy
from git_mirror.manage_pypi import PyPiManager, pretty_print_pypi_results
from git_mirror.performance import log_duration
from git_mirror.safe_env import load_env
from git_mirror.ui import console_with_theme

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
        prompt_for_changes: bool = True,
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
            prompt_for_changes (bool): Whether to prompt for changes.
        """
        # self.client() = gh.Github(token)
        self.token = token
        self.base_dir = base_dir
        # cache user
        self.user: Optional[Union[ghnu.NamedUser, ghau.AuthenticatedUser]] = None
        self.user_login = user_login
        self.include_private = include_private
        self.include_forks = include_forks
        self.host_domain = host_domain
        self.dry_run = dry_run
        self.prompt_for_changes = prompt_for_changes
        LOGGER.debug(
            f"GithubRepoManager initialized with user_login: {user_login}, include_private: {include_private}, include_forks: {include_forks}"
        )

    def client(self) -> gh.Github:
        return gh.Github(self.token)

    def _thread_safe_repos(self, data: list[ghr.Repository]) -> list[dict[str, Any]]:
        repos = []
        for repo in data:
            repos.append(
                {
                    "name": repo.name,
                    "description": repo.description or "No description",
                    "private": "Yes" if repo.private else "No",
                    "fork": "Yes" if repo.fork else "No",
                    "html_url": repo.html_url,
                }
            )
        return repos

    def _get_user_repos(self, ignore_users_filters: bool = False) -> list[ghr.Repository]:
        """
        Fetches the user's repositories from GitHub, optionally including private repositories and forks.

        Returns:
            list[Repository]: A list of Repository objects.
        """
        console = console_with_theme()
        if not self.user:
            self.user = self.client().get_user()

        try:
            repos = []
            for repo in self.user.get_repos():
                # ignore user's filters when checking if something local isn't a remote repo.
                if ignore_users_filters or (
                    (self.include_private or not repo.private)
                    and (self.include_forks or not repo.fork)
                    and repo.owner.login == self.user_login
                ):
                    repos.append(repo)

            return repos
        except gh.GithubException as e:
            console.print(f"Failed to fetch repositories: {e}", style="danger")
            return []

    @log_duration
    def clone_all(self, single_threaded: bool = False):
        console = console_with_theme()
        repos = self._get_user_repos()
        if self.prompt_for_changes:
            answer = inquirer.prompt(
                [
                    inquirer.Confirm(
                        "clone-all", message=f"Are you sure you want to clone {len(repos)} repositories?", default=False
                    )
                ]
            )
            if not answer["clone-all"]:
                console.print("Cloning cancelled.")
                return

        console.print(f"Cloning {len(repos)} repositories.")

        if single_threaded or len(repos) < 4:  # or features.CACHING:
            for repo in self._thread_safe_repos(repos):
                self._clone_repo((repo, Dummy()))
        else:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                manager = multiprocessing.Manager()
                lock = manager.Lock()
                results = pool.map(self._clone_repo, [(repo, lock) for repo in self._thread_safe_repos(repos)])
                for output in results:
                    if output:
                        console.print(output, end="")

    def _clone_repo(self, repo_args: tuple[dict[str, Any], ContextManager[Any]]) -> None:
        """
        Clones the given repository into the target directory.

        Args:
            repo_args (tuple[dict[str, Any], ContextManager[Any]]): A tuple containing the repository data and a lock.

        Returns:
        str: The captured print output.
        """
        console = console_with_theme()
        repo, lock = repo_args
        try:
            if not (self.base_dir / repo["name"]).exists():
                if not self.dry_run:
                    message = f"Cloning {repo['html_url']} into {self.base_dir}"
                    with lock:
                        console.print(message)
                    g.Repo.clone_from(f"{repo['html_url']}.git", self.base_dir / repo["name"])
                else:
                    message = f"Would have cloned {repo['html_url']} into {self.base_dir}"
                    with lock:
                        console.print(message)
            else:
                message = f"Repository {repo['name']} already exists locally. Skipping clone."
                with lock:
                    console.print(message)
        except g.GitCommandError as e:
            message = f"Failed to clone {repo['name']}: {e}"
            with lock:
                console.print(message, style="danger")

    @log_duration
    def pull_all(self, single_threaded: bool = False):
        console = console_with_theme()
        directories = mg.find_git_repos(self.base_dir)
        console.print(f"Pulling {len(directories)} repositories.")
        if single_threaded or len(directories) < 4:
            for repo_dir in directories:
                self.pull_repo((repo_dir, Dummy()))
        else:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                manager = multiprocessing.Manager()
                lock = manager.Lock()
                results = pool.map(self.pull_repo, ((repo_dir, lock) for repo_dir in directories))
                for output in results:
                    if output:
                        console.print(output, end="")

    @log_duration
    def pull_repo(self, args: tuple[Path, ContextManager[Any]]) -> None:
        """
        Performs a git pull operation on the repository at the given path.

        Args:
            args (tuple[Path, ContextManager[Any]]): A tuple containing the path to the repository and a lock.

        Returns:
            str: The captured print output.
        """
        console = console_with_theme()
        repo_path, lock = args
        try:
            repo = g.Repo(repo_path)
            origin = repo.remotes.origin
            if not self.dry_run:
                with lock:
                    console.print(f"Pulling latest changes in {repo_path}")
                origin.pull()
            else:
                with lock:
                    console.print(f"Would have pulled latest changes in {repo_path}")
        except Exception as e:
            with lock:
                console.print(f"Failed to pull repo at {repo_path}: {e}", style="danger")

    @log_duration
    def not_repo(self) -> tuple[int, int, int, int]:
        """
        Lists directories in the base directory that are not valid Git repositories,
        or are not owned by the user, or are forks of another repository.

        Uses both git and github because of fork checking.
        """
        console = console_with_theme()
        user_repos = {repo.name: repo for repo in self._get_user_repos(ignore_users_filters=True)}

        no_remote = 0
        not_found = 0
        is_fork = 0
        not_repo = 0
        repos = mg.find_git_repos(self.base_dir)
        console.print(f"Checking {len(repos)} repositories for stray, non-repo subfolders in {self.base_dir}.")
        for repo_dir in repos:
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    remotes = repo.remotes
                    if not remotes:
                        no_remote += 1
                        console.print(f"{repo_dir} has no remote repositories defined.")
                        continue

                    remote_url = remotes[0].config_reader.get("url")
                    repo_name = mg.extract_repo_name(remote_url)

                    if repo_name not in user_repos:
                        not_found += 1
                        console.print(f"{repo_dir} is not found in your GitHub account.")
                        continue

                    github_repo = user_repos[repo_name]
                    if github_repo.fork:
                        is_fork += 1
                        console.print(f"{repo_dir} is in your account, but is a fork of another user's repository.")
                        continue

                except g.InvalidGitRepositoryError:
                    not_repo += 1
                    console.print(f"{repo_dir} is not a valid Git repository.", style="danger")
        return no_remote, not_found, is_fork, not_repo

    @log_duration
    def list_repo_builds(self) -> list[tuple[str, str]]:
        """
        Lists the most recent GitHub Actions workflow runs for each repository of the authenticated user,
        with the status color-coded: green for success, red for failure, and yellow for cancelled.
        """
        console = console_with_theme()
        if not self.user:
            self.user = self.client().get_user()

        messages = []
        repos = self._get_user_repos()
        console.print(f"Checking {len(repos)} repositories for build statuses.")
        for repo in repos:
            console.print(f"Repository: {repo.name}")
            statuses = repo.get_workflow_runs()
            messages.extend(self._loop_actions(statuses))
        return messages

    def _loop_actions(self, statuses) -> list[tuple[str, str]]:
        console = console_with_theme()
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
                console.print(colored(status_message, "green"))
            elif conclusion == "failure":
                console.print(colored(status_message, "red"))
            elif conclusion == "cancelled":
                console.print(colored(status_message, "yellow"))
            else:
                console.print(status_message)  # Default, no color
        return messages

    @log_duration
    def check_pypi_publish_status(self, pypi_owner_name: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Checks if the repositories as Python packages are published on PyPI and compares the last change dates.
        """
        console = console_with_theme()
        results = []
        if pypi_owner_name:
            pypi_owner_name = pypi_owner_name.strip().lower()

        async def get_infos_async(package_names):
            pypi_manager = PyPiManager()
            return await pypi_manager.get_infos(package_names)

        package_names = [path.name for path in mg.find_git_repos(self.base_dir)]
        package_infos = asyncio.run(get_infos_async(package_names))

        repos = mg.find_git_repos(self.base_dir)
        console.print(f"Checking {len(repos)} repositories for PyPI publish status.")
        for repo_dir in repos:
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
        print()
        console.print(pretty_print_pypi_results(results))
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

    @log_duration
    def list_repo_names(self) -> list[str]:
        """
        Returns a list of repository names.

        Returns:
            List[str]: A list of repository names.
        """
        return [repo.full_name for repo in self._get_user_repos()]

    @log_duration
    def list_repos(self) -> Optional[Table]:
        """
        Fetches and prints beautifully formatted information about the user's GitHub repositories.
        """
        console = console_with_theme()
        try:
            user = self.client().get_user(self.user_login)
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

            console.print(table)
            return table
        except gh.GithubException as e:
            console.print(f"An error occurred: {e}", style="danger")
        return None

    @log_duration
    def print_user_summary(self) -> None:
        """
        Fetches and prints a summary of the user's GitHub account.
        """
        console = console_with_theme()
        try:
            user = self.client().get_user(self.user_login)
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

    @log_duration
    def update_all_branches(self, single_threaded: bool = False, prefer_rebase: bool = False):
        """
        Updates each local branch with the latest changes from the main/master branch on GitHub.

        Args:
            single_threaded (bool): Whether to run the operation in a single thread.
            prefer_rebase (bool): Whether to prefer rebasing instead of merging.
        """
        console = console_with_theme()
        directories = mg.find_git_repos(self.base_dir)
        console.print(f"Merging/rebasing {len(directories)} main to local repositories.")
        if single_threaded or len(directories) < 4:
            for repo_dir in directories:
                self._update_local_branches(UpdateBranchArgs(repo_dir, repo_dir.name, prefer_rebase, Dummy()))
        else:
            with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
                manager = multiprocessing.Manager()
                lock = manager.Lock()
                results = pool.map(
                    self._update_local_branches,
                    (UpdateBranchArgs(repo_dir, repo_dir.name, prefer_rebase, lock) for repo_dir in directories),
                )
                for output in results:
                    if output:
                        if output:
                            console.print(output, end="")

    # def _update_local_branches(self, repo_path: Path, github_repo_full_name: str, prefer_rebase: bool = False):
    def _update_local_branches(self, args: UpdateBranchArgs):
        """
        Updates each local branch with the latest changes from the main/master branch on GitHub.

        Args:
            args: UpdateBranchArgs
        """
        console = console_with_theme()
        repo_path, github_repo_full_name, prefer_rebase = args.repo_path, args.github_repo_full_name, args.prefer_rebase
        github_repo_full_name = self.user_login + "/" + github_repo_full_name
        repo = g.Repo(str(repo_path))
        try:
            github_repo = self.client().get_repo(github_repo_full_name)
        except gh.GithubException as e:
            console.print(f"Failed to retrieve info on GitHub repository {github_repo_full_name}: {e}", style="danger")
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

                    console.print(f"Updated branch '{branch}' with latest changes from '{default_branch}'.")
                else:
                    console.print(f"Would have updated branch '{branch}' with latest changes from '{default_branch}'.")
            except g.exc.GitCommandError as e:
                console.print(f"Failed to update branch '{branch}': {e}", style="danger")

    @log_duration
    def prune_all(self) -> None:
        """
        Prunes all local branches that have been deleted on GitHub.
        """
        console = console_with_theme()
        repos = mg.find_git_repos(self.base_dir)
        console.print(f"Ready to Pruning {len(repos)} repositories of branches no longer on remote.")
        if self.prompt_for_changes:
            answer = inquirer.prompt(
                [inquirer.Confirm("prune", message="Are you sure you want to prune all repositories?", default=False)]
            )
            if not answer["prune"]:
                console.print("Pruning cancelled.")
                return

        for repo_dir in repos:
            if repo_dir.is_dir():
                self._delete_local_branches_if_not_on_github(repo_dir, f"{self.user_login}/{repo_dir.name}")

    def _delete_local_branches_if_not_on_github(self, repo_path: Path, github_repo_full_name: str):
        """
        Loops through all local branches, checks if they exist on GitHub, and prompts the user for deletion if they don't.

        Args:
            repo_path (Path): The file system path to the local git repository.
            github_repo_full_name (str): The full name of the GitHub repository (e.g., "owner/repo").
        """
        console = console_with_theme()
        try:
            repo = g.Repo(str(repo_path))
        except g.InvalidGitRepositoryError:
            console.print(f"{repo_path} is not a valid Git repository.", style="danger")
            return
        try:
            github_repo = self.client().get_repo(github_repo_full_name)
        except gh.GithubException as e:
            console.print(f"Failed to retrieve info on GitHub repository {github_repo_full_name}: {e}", style="danger")
            return

        # Get a list of all branch names on GitHub
        remote_branches = [branch.name for branch in github_repo.get_branches()]

        # Get a list of all local branch names
        local_branches = [branch.name for branch in repo.heads]  # alias to branches

        # Determine branches that are local but not on GitHub
        branches_to_consider = [branch for branch in local_branches if branch not in remote_branches]

        if not branches_to_consider:
            console.print(f"For {github_repo_full_name}, no local branches exist that are missing on GitHub.")
            return

        # Prompt user for each branch that doesn't exist on GitHub
        for branch in branches_to_consider:
            if self.prompt_for_changes:
                question = [
                    inquirer.Confirm(
                        "delete",
                        message=f"The branch '{branch}' does not exist on GitHub. Delete locally?",
                        default=False,
                    )
                ]
                answer = inquirer.prompt(question)

                if not answer["delete"]:
                    console.print(f"Skipped deletion of branch '{branch}'.")
                    continue
            try:
                if not self.dry_run:
                    # Safely delete the branch
                    repo.git.branch("-d", branch)
                    console.print(f"Deleted branch '{branch}' locally.")
                else:
                    console.print(f"Would have deleted branch '{branch}' locally.")
            except g.exc.GitCommandError as e:
                console.print(
                    f"Could not delete branch '{branch}'. It may not be fully merged. Error: {e}", style="danger"
                )

    @log_duration
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

    @log_duration
    def cross_repo_sync_report(self, template_dir: Path) -> None:
        """
        Reports differences between the template directory and the target directories.
        """
        console = console_with_theme()
        if not template_dir or not template_dir.exists():
            console.print(f"Template directory {template_dir} does not exist.")
            return
        # right now just the easy case of all repos need to match 1 template_dir
        console.print("Reporting differences between the template directory and the target directories.")
        syncer = TemplateSync(template_dir)
        directories = mg.find_git_repos(self.base_dir)
        console.print(f"Found {len(directories)} repositories.")
        syncer.report_content_differences(directories)

    @log_duration
    def cross_repo_init(self, template_dir: Path) -> None:
        console = console_with_theme()
        if not template_dir or not template_dir.exists():
            console.print(f"Template directory {template_dir} does not exist.")
            return
        syncer = TemplateSync(template_dir, use_default=True)
        directories = mg.find_git_repos(self.base_dir)
        console.print(f"Found {len(directories)} repositories.")
        syncer.write_template_map(directories)
        console.print(f"Initialized template map for {len(directories)} repositories.")

    @log_duration
    def cross_repo_sync(self, template_dir: Path) -> None:
        console = console_with_theme()
        if not template_dir or not template_dir.exists():
            console.print(f"Template directory {template_dir} does not exist.")
            return
        syncer = TemplateSync(template_dir, use_default=True)
        directories = mg.find_git_repos(self.base_dir)
        console.print(f"Found {len(directories)} repositories.")
        if self.prompt_for_changes:
            answer = inquirer.prompt(
                [inquirer.Confirm("sync", message="Are you sure you want to sync all repositories?", default=False)]
            )
            if not answer["sync"]:
                console.print("Sync cancelled.")
                return
        syncer.sync_template(directories)
        console.print(f"Synchronized {len(directories)} repositories with the template directory.")

    @log_duration
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
        console = console_with_theme()
        repo = self.client().get_repo(repo_name)
        if not self.user:
            self.user = self.client().get_user()

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

        console.print(f"Pull request created: {pull_request.html_url}")

```

Here are function and method signatures of the dependencies

```python
#git_mirror/cross_repo_sync.py
def run()->None:
    ...

class TemplateSync:
    """    A class to synchronize template directories across multiple target directories, with detailed file comparison."""
    def __init__(self, templates_dir: Path, use_default: bool=False)->None:
        """Initializes the TemplateSync with a source template directory."""
        ...
    def read_template_map(self)->dict[str, str]:
        ...
    def write_template_map(self, target_dirs: list[Path])->None:
        ...
    def get_template_dir(self, project: str)->Path:
        ...
    def report_differences(self, target_dirs: list[Path])->None:
        """Reports detailed differences between the template directory and each target directory."""
        ...
    def _report_differences_data(self, target_dirs: list[Path])->dict[str, list[dict[str, str]]]:
        ...
    def report_content_differences(self, target_dirs: list[Path])->None:
        """Reports detailed differences between the template directory and each target directory, displaying rich diffs for files with different contents."""
        ...
    def sync_template(self, target_dirs: list[Path])->None:
        """Synchronizes the template directory with each target directory."""
        ...
    def _compare_directories(self, target_dir: Path, project_name: str='')->list[dict[str, str]]:
        """Compares the template directory with a target directory to find detailed differences."""
        ...
    def _compare_files(self, template: Path, target: Path, project_name: str='')->dict[str, str]:
        """Compares two files, insensitive to CR/LF differences, and returns the nature of the difference."""
        ...
    def apply_light_templating(self, target: Path, template: Path, project_name: str)->tuple[list[str], list[str]]:
        ...
    def _copy_template(self, target_dir: Path)->None:
        """Copies the template directory to a target directory."""
        ...
    def _display_diff(self, template: Path, target: Path, project_name: str)->None:
        """Displays a rich diff of the contents of two files."""
        ...
```

```python
#git_mirror/custom_types.py

class UpdateBranchArgs:
class SourceHost:
    """    Just the methods that are common among hosters.
    By convention, other methods are underscored and treated as private"""
    def clone_all(self, single_threaded: bool=False):
        ...
    def pull_all(self, single_threaded: bool=False):
        ...
    def pull_repo(self, args: tuple[Path, ContextManager[Any]])->None:
        """Performs a git pull operation on the repository at the given path.
    
        Args:
            args (tuple[Path, ContextManager[Any]]): A tuple containing the path to the repository and a lock."""
        ...
    def not_repo(self)->tuple[int, int, int, int]:
        """Lists directories in the base directory that are not valid Git repositories,
        or are not owned by the user, or are forks of another repository.
    
        Uses both git and github because of fork checking."""
        ...
    def list_repo_builds(self)->list[tuple[str, str]]:
        """Lists the most recent GitHub Actions workflow runs for each repository of the authenticated user,
        with the status color-coded: green for success, red for failure, and yellow for cancelled."""
        ...
    def check_pypi_publish_status(self, pypi_owner_name: Optional[str]=None)->list[dict[str, Any]]:
        """Checks if the repositories as Python packages are published on PyPI and compares the last change dates."""
        ...
    def list_repo_names(self)->list[str]:
        """Returns a list of repository names.
    
        Returns:
            List[str]: A list of repository names."""
        ...
    def list_repos(self)->Optional[Table]:
        """Fetches and prints beautifully formatted information about the user's GitHub repositories."""
        ...
    def print_user_summary(self)->None:
        """Fetches and prints a summary of the user's GitHub account."""
        ...
    def update_all_branches(self, single_threaded: bool=False, prefer_rebase: bool=False):
        """Updates each local branch with the latest changes from the main/master branch on Source Host."""
        ...
    def prune_all(self):
        """Loops through all local branches, checks if they exist on GitHub, and prompts the user for deletion if they don't."""
        ...
    def version_info(self)->dict[str, Any]:
        """Return API version information."""
        ...
    def cross_repo_sync_report(self, template_dir: Path):
        """Compares the template directory to the target directories and reports differences."""
        ...
    def cross_repo_init(self, template_dir: Path):
        ...
    def cross_repo_sync(self, template_dir: Path):
        ...
    def merge_request(self, source_branch: str, target_branch: str, title: str, reviewer: str, project_id: int, repo_name: str):
        ...
```

```python
#git_mirror/dummies.py

class Dummy:
    def __enter__(self):
        ...
    def __exit__(self, exc_type, exc_val, exc_tb):
        ...
```

```python
#git_mirror/manage_git.py
def find_git_repos(base_dir: Path)->list[Path]:
    """Recursively finds all Git repositories in the given base directory using two methods:
    First, it uses `os.walk`, and then it uses `pathlib.Path.rglob` to ensure no repositories are missed.
    
    Args:
        base_dir (Path): The base directory to search for Git repositories.
    
    Returns:
        List[Path]: A list of Paths representing the Git repositories found."""
    ...
def extract_repo_name(remote_url: str)->str:
    """Extracts the repository name from its remote URL.
    
    Args:
        remote_url (str): The remote URL of the repository.
    
    Returns:
        str: The repository name.
    
    Examples:
        >>> extract_repo_name("http://example.com/user/repo.git")
        'repo'"""
    ...

class GitManager:
    def __init__(self, base_dir: Path, dry_run: bool=False, prompt_for_changes: bool=True):
        """Initializes base directory for git operations.
    
        Args:
            base_dir (Path): Base directory path where repositories will be cloned.
            dry_run (bool): Flag to determine whether the operation should be a dry run.
            prompt_for_changes (bool): Flag to determine whether the operation should prompt for changes."""
        ...
    def local_repos_with_file_in_root(self, file_name: str)->list[Path]:
        """Finds local git repositories within the base directory that have a specific file in their root.
    
        Args:
            file_name (str): The name of the file to search for in the root of each repository.
    
        Returns:
            List[Path]: A list of Paths to the repositories that contain the specified file in their root directory."""
        ...
    def check_for_uncommitted_or_unpushed_changes(self, single_threaded: bool=False)->int:
        """Checks all local repositories for uncommitted changes or commits that haven't been pushed to the remote."""
        ...
    def check_single_repo(self, repo_dir: Path)->int:
        ...
    def _check_for_unpushed_commits(self, repo: g.Repo, repo_dir: Path)->int:
        """Checks if the repository has commits that haven't been pushed to its tracked remote branches.
    
        Args:
            repo (Repo): The repository object.
            repo_dir (Path): The directory of the repository."""
        ...
```

```python
#git_mirror/manage_pypi.py
def pretty_print_pypi_results(results: list[dict[str, Any]])->Table:
    """Pretty prints the results of the PyPI audit using the rich library.
    
    Args:
        results (List[dict[str, Any]]): A list of dictionaries containing the audit results."""
    ...

class PyPiManager:
    def __init__(self, pypi_owner_name: Optional[str]=None):
        ...
    def _get_latest_pypi_release_date(self, pypi_data: dict)->datetime:
        """Parses the PyPI package data to find the release date of the latest version.
    
        Args:
            pypi_data (dict): The package data from PyPI.
    
        Returns:
            datetime: The release date of the latest version on PyPI.
    
        Examples:
            >>> data ={"info": {"version": "0.1.0"}, "releases": {"0.1.0": [{"upload_time": "2021-09-10T18:48:49"}]}}
            >>> PyPiManager._get_latest_pypi_release_date(data)
            datetime.datetime(2021, 9, 10, 18, 48, 49)"""
        ...
```

```python
#git_mirror/performance.py
def log_duration(func: Callable)->Callable:
    """A decorator that logs the execution time of the wrapped function.
    
    Args:
        func (Callable): The function to wrap.
    
    Returns:
        Callable: The wrapper function."""
    ...
def wrapper(*args: Any, **kwargs: Any)->Any:
    ...

```

```python
#git_mirror/safe_env.py
def load_env()->None:
    ...
def env_info()->None:
    ...

```

```python
#git_mirror/ui.py
def console_with_theme()->Console:
    """Factory to allow for app theming."""
    ...

```
Please write some unit tests for E:\github\git_mirror\git_mirror\manage_github.py. If you can't think of anymore unit tests, write "No more unit tests".
Assistant: To test the `GitRepoManager` class, we can write the following unit tests:

1. Test the initialization of `GitRepoManager`:
   - Mock the `logging.getLogger` function to ensure that the `LOGGER` attribute is set correctly.
   - Check if the attributes are set correctly when initializing `GitRepoManager`.

2. Test the `client` method:
   - Mock the `gh.Github` class and ensure the method returns an instance of `gh.Github`.

3. Test the `_thread_safe_repos` method:
   - Mock a list of `ghr.Repository` objects and ensure that the method transforms them into the expected format.

4. Test the `_get_user_repos` method:
   - Mock `client.get_user()`, `user.get_repos()`, and test the filtering logic based on private and forked repositories.

5. Test the `clone_all` method:
   - Mock the console output to check if correct messages are printed based on the logic in the method.
   - Test the case where `prompt_for_changes` is False and no repositories are cloned.

6. Test the `_clone_repo` method:
   - Mock the `g.Repo.clone_from` method to check if the correct messages are printed based on different conditions.

7. Test the `pull_all` method:
   - Mock the console output and pool.map calls to ensure correct behavior.

8. Test the `_update_local_branches` method:
   - Mock `git.Repo` instantiation and `repo.git.checkout` methods to test the branch update logic.

9. Test the `prune_all` method:
   - Mock the console output to ensure correct messages are printed based on different conditions.

10. Test the `version_info` method:
    - Mock the `httpx.get` method to test the API call and return values based on different scenarios.

11. Test the `cross_repo_sync` method:
    - Mock the `TemplateSync` class and ensure that the synchronization logic behaves as expected.

12. Test the `merge_request` method:
    - Mock the creation of a pull request and assignment of a reviewer, ensuring the correct URL is returned.

Here is an example of how the unit tests could look like:

```python
import pytest
from git_mirror.manage_github import GitRepoManager
from unittest.mock import Mock

@pytest.fixture
def mock_github():
    return Mock()

def test_GitRepoManager_initialization(mock_github):
    manager = GitRepoManager(
        token="dummy_token",
        base_dir="/path/to/base/dir",
        user_login="test_user",
        include_private=True,
        include_forks=False,
        host_domain="https://github.com",
        dry_run=False,
        prompt_for_changes=True
    )
    assert manager.token == "dummy_token"
    assert manager.base_dir == "/path/to/base/dir"
    assert manager.user_login == "test_user"
    assert manager.include_private == True
    assert manager.include_forks == False
    assert manager.host_domain == "https://github.com"
    assert manager.dry_run == False
    assert manager.prompt_for_changes == True
    mock_github.assert_called_once_with("dummy_token")
```

This example tests the initialization of the `GitRepoManager` class and mocks the `gh.Github` class constructor to ensure it's called with the correct token.

If you need more unit tests, please let me know!
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ```python
import pytest
from git_mirror.manage_github import GitRepoManager
from unittest.mock import Mock, patch
from pathlib import Path

@pytest.fixture
def mock_repo():
    return GitRepoManager(
        token="dummy_token",
        base_dir=Path("/path/to/base/dir"),
        user_login="test_user",
        include_private=True,
        include_forks=False,
        host_domain="https://github.com",
        dry_run=False,
        prompt_for_changes=True
    )

def test_client_method(mock_repo):
    mock_gh = Mock()
    with patch('git_mirror.manage_github.gh.Github', return_value=mock_gh) as mock_github:
        client = mock_repo.client()
    mock_github.assert_called_once_with("dummy_token")
    assert client == mock_gh
```

In this test, we are testing the `client` method of the `GitRepoManager` class. We are mocking the `gh.Github` class and using a patch decorator to mock the class instantiation. Then, we are checking if the `client` method returns the expected Github object.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ```python
import pytest
from git_mirror.manage_github import GitRepoManager
from unittest.mock import Mock, patch
from pathlib import Path

@pytest.fixture
def mock_repo():
    return GitRepoManager(
        token="dummy_token",
        base_dir=Path("/path/to/base/dir"),
        user_login="test_user",
        include_private=True,
        include_forks=False,
        host_domain="https://github.com",
        dry_run=False,
        prompt_for_changes=True
    )

def test_thread_safe_repos_method(mock_repo):
    mock_repo_data = [
        Mock(name="Repo1", description="Description1", private=False, fork=True, html_url="https://github.com/Repo1"),
        Mock(name="Repo2", description=None, private=True, fork=False, html_url="https://github.com/Repo2"),
    ]
    expected_output = [
        {
            "name": "Repo1",
            "description": "Description1",
            "private": "No",
            "fork": "Yes",
            "html_url": "https://github.com/Repo1"
        },
        {
            "name": "Repo2",
            "description": "No description",
            "private": "Yes",
            "fork": "No",
            "html_url": "https://github.com/Repo2"
        }
    ]
    
    repos = mock_repo._thread_safe_repos(mock_repo_data)
    
    assert repos == expected_output
```

In this test, we are testing the `_thread_safe_repos` method of the `GitRepoManager` class. We are providing mock data for repositories and checking if the method transforms the data into the expected format.