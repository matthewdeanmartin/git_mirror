"""
Interface with gitlab.

This should use manage_config, manage_git, manage_pypi for things that are not gitlab specific.
"""

import asyncio
import logging
import multiprocessing
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Optional, Union, cast

import git as g
import gitlab
import inquirer
from gitlab.base import RESTObject, RESTObjectList
from gitlab.v4.objects import Project
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from termcolor import colored

import git_mirror.manage_git as mg
from git_mirror.cross_repo_sync import TemplateSync
from git_mirror.custom_types import SourceHost, UpdateBranchArgs
from git_mirror.manage_pypi import PyPiManager
from git_mirror.safe_env import load_env

load_env()


# Configure logging
LOGGER = logging.getLogger(__name__)


class GitlabRepoManager(SourceHost):
    def __init__(
        self,
        token: str,
        base_dir: Path,
        user_login: str,
        include_private: bool = True,
        include_forks: bool = False,
        host_domain: str = "https://gitlab.com",
        group_id: Optional[int] = None,
        logging_level: int = 1,
        dry_run: bool = False,
    ):
        """
        Initializes the RepoManager with a GitLab token and a base directory for cloning repositories.

        Args:
            token (str): GitLab personal access token.
            base_dir (Path): Base directory path where repositories will be cloned.
            user_login (str): The GitLab username.
            include_private (bool): Whether to include private repositories.
            include_forks (bool): Whether to include forked repositories.
            host_domain (str): The GitLab host domain.
            group_id (int): The ID of the group to clone repositories from.
            logging_level (int): The logging level.
            dry_run (bool): Whether the operation should be a dry run.
        """
        self.gitlab = gitlab.Gitlab(host_domain, private_token=token)
        if logging_level >= 2:
            self.gitlab.enable_debug()
        self.base_dir = base_dir
        self.user_login = user_login
        self.include_private = include_private
        self.include_forks = include_forks
        self.user: Optional[RESTObject] = None
        self.group_id = group_id
        self.verbose_logging = logging_level
        self.dry_run = dry_run

    def _get_user_repos(self) -> list[Project]:
        """
        Fetches the user's repositories from GitLab, optionally including private repositories and forks.

        Returns:
            List[gitlab.v4.objects.Project]: A list of Project objects.
        """
        if not self.user:
            self.user = self.gitlab.users.list(username=self.user_login, get_all=True)[0]  # type: ignore

        try:
            kwargs: dict[str, Union[bool, str]] = {"owned": True}
            if not self.include_private:
                kwargs["visibility"] = "public"
            projects = self.gitlab.projects.list(**kwargs, get_all=True)
            projects = [self.gitlab.projects.get(id=project.id) for project in projects]

            filtered_projects = []
            for project in projects:

                if hasattr(project, "forked_from_project") and project.forked_from_project:
                    forked = True
                else:
                    forked = False
                if (self.include_forks or not forked) and project.namespace["path"] == self.user_login:
                    filtered_projects.append(project)

            return filtered_projects  # type: ignore
        except gitlab.exceptions.GitlabError as e:
            print(f"Failed to fetch repositories: {e}")
            return []

    def clone_all(self, single_threaded: bool = False):
        """
        Clones all repositories for a user.
        """
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

    def clone_group(self, group_id: int):
        """
        Clones all repositories for a user or all repositories within a group.

        Args:
            group_id (int): The ID of the group to clone repositories from.
        """
        if group_id == 0:
            raise ValueError("Group ID cannot be 0.")
        print(f"Cloning all repositories for group with ID {group_id}")
        self._clone_group_repos(group_id)

    def _clone_group_repos(self, group_id: int) -> None:
        """
        Clones all repositories within a specified group, including subgroups.

        Args:
            group_id (int): The ID of the group.
        """
        if group_id == 0:
            raise ValueError("Group ID cannot be 0.")

        groups_to_process = [group_id]

        while groups_to_process:
            current_group_id = groups_to_process.pop(0)
            group = self._get_group_by_id(current_group_id)
            # subgroups = self._get_subgroups(group)
            if not group:
                print(f"Group with ID {current_group_id} not found. Skipping.")
            repos = self._get_repos(group)

            for repo in repos:
                print(".", end="")
                self._clone_repo(repo, extra_path=group.full_path)

            # for subgroup in subgroups:
            #     groups_to_process.append(subgroup.id)

    def _clone_repo(self, project, extra_path: str = "") -> str:
        """
        Clones the given project into the target directory, respecting group/subgroup structure.

        Args:
            project: The project to clone.
            extra_path (str): Additional path components for group/subgroup structure.
        """
        # Redirect stdout to capture print output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            repo_path = self.base_dir / extra_path / project.path
            if not repo_path.exists():
                if self.dry_run:
                    print(f"Would clone {project.web_url} into {repo_path}")
                else:
                    print(f"Cloning {project.web_url} into {repo_path}")
                    repo_path.parent.mkdir(parents=True, exist_ok=True)
                    g.Repo.clone_from(project.http_url_to_repo, repo_path)
            else:
                print(f"Project {project.path} already exists locally. Skipping clone.")
        except g.GitCommandError as e:
            print(f"Failed to clone {project.path}: {e}")
        finally:
            # Restore stdout
            sys.stdout = old_stdout
        return captured_output.getvalue()

    def _get_group_by_id(self, group_id: int):
        """
        Fetches a GitLab group by its ID using the python-gitlab library.

        Args:
            group_id (int): The ID of the group to fetch.

        Returns:
            gitlab.v4.objects.Group: The GitLab Group object.
        """
        try:
            # Fetch the group by ID
            group = self.gitlab.groups.get(group_id)
            return group
        except gitlab.exceptions.GitlabGetError as e:
            print(f"Failed to get group with ID {group_id}: {e}")
            return None

    def _get_subgroups(self, group):
        """
        Fetches all subgroups for a given GitLab group.

        Args:
            group (gitlab.v4.objects.Group): The GitLab Group object.

        Returns:
            List[gitlab.v4.objects.Group]: A list of GitLab Subgroup objects.
        """
        try:
            subgroups = group.projects.list(all=True, include_subgroups=True)
            return subgroups
        except gitlab.exceptions.GitlabListError as e:
            print(f"Failed to list subgroups for group {group.id}: {e}")
            return []

    def _get_repos(self, group: gitlab.v4.objects.Group) -> list[gitlab.v4.objects.Project]:
        """
        Fetches all repositories (projects) for a given GitLab group, including those in its subgroups.

        Args:
            group (gitlab.v4.objects.Group): The GitLab Group object.

        Returns:
            List[gitlab.v4.objects.Project]: A list of GitLab Project objects.
        """
        try:
            # Retrieve all projects for the group, including those in subgroups
            projects = group.projects.list(include_subgroups=True, all=True)
            return projects  # type: ignore
        except gitlab.exceptions.GitlabListError as e:
            print(f"Failed to list projects for group {group.id}: {e}")
            return []

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
        """
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

        Returns:
            tuple: Counts of no_remote, not_found, is_fork, not_repo scenarios.
        """
        kwargs: dict[str, Union[str, bool]] = {"owned": True, "get_all": True}
        if not self.include_private:
            kwargs["visibility"] = "public"
        user_projects = {
            project.path: self.gitlab.projects.get(id=project.id) for project in self.gitlab.projects.list(**kwargs)
        }

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

                    if repo_name not in user_projects:
                        not_found += 1
                        print(f"{repo_dir} is not found in your GitLab account.")
                        continue

                    gitlab_project = user_projects[repo_name]
                    if hasattr(gitlab_project, "forked_from_project") and gitlab_project.forked_from_project:
                        forked = True
                    else:
                        forked = False
                    if not forked:
                        is_fork += 1
                        print(f"{repo_dir} is a fork of another repository.")
                        continue

                except g.InvalidGitRepositoryError:
                    not_repo += 1
                    print(f"{repo_dir} is not a valid Git repository.")
        return no_remote, not_found, is_fork, not_repo

    def list_repo_builds(self) -> list[tuple[str, str]]:
        """
        Lists the most recent GitLab CI/CD pipeline runs for each project of the authenticated user,
        with the status color-coded: green for success, red for failure, and yellow for canceled.
        """
        messages = []
        for project in self._get_user_repos():
            print(f"Project: {project.name}")
            pipelines = cast(
                RESTObjectList, project.pipelines.list(order_by="updated_at", sort="desc", per_page=1, iterator=True)
            )  # Get the most recent pipeline
            messages.extend(self._loop_pipelines(pipelines))
        return messages

    def _loop_pipelines(self, pipelines: RESTObjectList, count: int = 1) -> list[tuple[str, str]]:
        messages = []
        seen = 0
        for pipeline in pipelines:
            seen += 1
            if seen > count:
                break
            status_message = f"Date: {pipeline.updated_at} - Pipeline #{pipeline.id} - Status: {pipeline.status} - URL: {pipeline.web_url}"
            status = pipeline.status.lower()
            messages.append((status, status_message))

            if status in ["passed", "success"]:
                print(colored(status_message, "green"))
            elif status in ["failed"]:
                print(colored(status_message, "red"))
            elif status in ["canceled", "cancelled"]:  # Checking both spellings to be safe
                print(colored(status_message, "yellow"))
            else:
                raise ValueError(f"Unknown status: {status}")
        return messages

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

    def check_pypi_publish_status(self, pypi_owner_name: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Checks if the repositories as Python packages are published on PyPI and compares the last change dates.
        """
        print("Checking if your gitlab repos have been published to pypi.")
        results = []

        async def get_infos_async(package_names):
            pypi_manager = PyPiManager()
            return await pypi_manager.get_infos(package_names)

        package_names = [path.name for path in mg.find_git_repos(self.base_dir)]
        package_infos = asyncio.run(get_infos_async(package_names))

        found = 0
        for repo_dir in mg.find_git_repos(self.base_dir):
            LOGGER.debug(f"Checking {repo_dir}")
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    package_name = repo_dir.name  # Assuming the repo name is the package name

                    pypi_data, status_code = package_infos[package_name]
                    if status_code == 200:
                        pypi_owner = pypi_data.get("info", {}).get("author", "").strip().lower()
                        any_owner_is_fine = pypi_owner_name is None
                        i_am_owner = pypi_owner_name == pypi_owner if pypi_owner_name else True

                        if any_owner_is_fine or i_am_owner:
                            pypi_release_date = PyPiManager._get_latest_pypi_release_date(pypi_data)
                            repo_last_commit_date = self._get_latest_commit_date(repo)
                            days_difference = (pypi_release_date - repo_last_commit_date).days
                            found += 1
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
                    # else:
                    #     LOGGER.debug(f"{package_name} is not a pypi package name.")
                except g.InvalidGitRepositoryError:
                    print(f"{repo_dir} is not a valid Git repository.")
                except Exception as e:
                    print(f"Error checking {repo_dir}: {e}")
        if found == 0:
            print(
                "None of your repositories are published on PyPI under the project name and "
                f"owner name of {pypi_owner_name}."
            )
        return results

    def list_repo_names(self) -> list[str]:
        """
        Returns a list of repository names.

        Returns:
            List[str]: A list of repository names.
        """
        return [project.name for project in self._get_user_repos()]

    def list_repos(self) -> Optional[Table]:
        """
        Fetches and prints beautifully formatted information about the user's Gitlab repositories.
        """
        try:
            table = Table(title="Gitlab Repositories")

            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description", style="magenta")
            table.add_column("URL", style="green")
            table.add_column("Private", style="red")
            table.add_column("Fork", style="blue")

            kwargs: dict[str, Union[bool, str]] = {"owned": True, "get_all": True}
            if not self.include_private:
                kwargs["visibility"] = "public"
            projects = self.gitlab.projects.list(**kwargs)
            projects = [self.gitlab.projects.get(id=project.id) for project in projects]

            for project in projects:

                if hasattr(project, "forked_from_project") and project.forked_from_project:
                    forked = True
                else:
                    forked = False

                if (self.include_private or project.visibility == "public") and (self.include_forks or not forked):
                    table.add_row(
                        project.name,
                        project.description or "No description",
                        project.web_url,
                        project.visibility,
                        "Yes" if forked else "No",
                    )

            console = Console()
            console.print(table)
            return table
        except gitlab.exceptions.GitlabError as e:
            print(f"An error occurred: {e}")
        return None

    def print_user_summary(self) -> None:
        """
        Fetches and prints a summary of the user's Gitlab account.
        """
        try:
            # double assign to make mypy happy
            self.user = self.load_user()
            print(self.user)

            summary = Text.assemble(
                ("Username: ", "bold cyan"),
                f"{self.user.username}\n",
                ("Name: ", "bold cyan"),
                f"{self.user.name}\n",
                ("Bio: ", "bold cyan"),
                f"{self.user.bio or 'No bio available'}\n",
                ("Public Email: ", "bold cyan"),
                f"{self.user.public_email or 'N/A'}\n",
                # I don't think Gitlab has following, followers.
                ("Location: ", "bold cyan"),
                f"{self.user.location or 'Not specified'}\n",
                ("Company: ", "bold cyan"),
                f"{self.user.organization or 'Not specified'}",
            )
            console = Console()
            console.print(Panel(summary, title="GitLab User Summary", subtitle=self.user.username))
        except Exception as e:
            print("Failed to fetch GitLab user info: %s", str(e))

    def load_user(self) -> RESTObject:
        if not self.user:
            list_info = self.gitlab.users.list(username=self.user_login, get_all=True)[0]  # type: ignore
            self.user = self.gitlab.users.get(list_info.id)
        # to make mypy happy
        return self.user

    def update_all_branches(self, single_threaded: bool = False, prefer_rebase: bool = False):
        """
        Updates each local branch with the latest changes from the main/master branch on Gitlab.

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
                        print(output, end="")

    def _update_local_branches(self, args: UpdateBranchArgs):
        """
        Updates each local branch with the latest changes from the main/master branch on Gitlab.

        Args:
            args: UpdateBranchArgs
        """
        repo_path, project_name, prefer_rebase = args.repo_path, args.github_repo_full_name, args.prefer_rebase
        repo = g.Repo(str(repo_path))

        # Search for the project using the namespace and project name
        projects = self.gitlab.projects.list(search=project_name, owned=True)[0]  # type: ignore
        # for project in projects:
        #     if project.path_with_namespace == f"{self.user_login}/{project_name}":
        #         return project.default_branch

        # Get the default branch name from Gitlab
        default_branch = projects.default_branch

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
                if not self.dry_run:
                    print(f"Updated branch '{branch}' with latest changes from '{default_branch}'.")
                else:
                    print(f"Would have updated branch '{branch}' with latest changes from '{default_branch}'.")
            except g.exc.GitCommandError as e:
                print(f"Failed to update branch '{branch}': {e}")

    def prune_all(self):
        for repo_dir in mg.find_git_repos(self.base_dir):
            if repo_dir.is_dir():
                self._delete_local_branches_if_not_on_host(repo_dir, f"{self.user_login}/{repo_dir.name}")

    def _delete_local_branches_if_not_on_host(self, repo_path: Path, project_name: str):
        """
        Loops through all local branches, checks if they exist on Gitlab, and prompts the user for deletion if they don't.

        Args:
            repo_path (Path): The file system path to the local git repository.
            project_name (str): The name of the project on Gitlab.
        """
        try:
            repo = g.Repo(str(repo_path))
        except g.InvalidGitRepositoryError:
            print(f"{repo_path} is not a valid Git repository.")
            return
        project = self.gitlab.projects.list(search=project_name, owned=True)[0]  # type: ignore

        # Get a list of all branch names on Gitlab
        remote_branches = [branch.name for branch in project.get_branches()]

        # Get a list of all local branch names
        local_branches = [branch.name for branch in repo.heads]  # alias to branches

        # Determine branches that are local but not on Gitlab
        branches_to_consider = [branch for branch in local_branches if branch not in remote_branches]

        if not branches_to_consider:
            print("No local branches exist that are missing on Gitlab.")
            return

        # Prompt user for each branch that doesn't exist on Gitlab
        for branch in branches_to_consider:
            question = [
                inquirer.Confirm(
                    "delete", message=f"The branch '{branch}' does not exist on Gitlab. Delete locally?", default=False
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
        version, revision = self.gitlab.version()
        return {"version": version, "revision": revision}

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
    ):
        if not self.user:
            self.user = self.load_user()
        project = self.gitlab.projects.get(project_id)
        reviewer_object = self.gitlab.users.list(username=reviewer, get_all=True)[0]  # type: ignore
        mr = project.mergerequests.create(
            {
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "remove_source_branch": True,
                "assignee_ids": [self.user.id],
                "reviewer_ids": [reviewer_object.id],
            }
        )
        mr.merge(merge_when_pipeline_succeeds=True, should_remove_source_branch=True, squash=True)
