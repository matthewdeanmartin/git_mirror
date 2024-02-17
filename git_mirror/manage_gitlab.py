"""
Interface with gitlab.

This should use manage_config, manage_git, manage_pypi for things that are not gitlab specific.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union, cast

import git as g
import gitlab
from dotenv import load_dotenv
from gitlab.base import RESTObject, RESTObjectList
from gitlab.v4.objects import Project
from rich.console import Console
from rich.table import Table
from termcolor import colored

from git_mirror.manage_git import extract_repo_name
from git_mirror.manage_pypi import PyPiManager
from git_mirror.types import SourceHost

load_dotenv()  # Load environment variables from a .env file, if present

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
        """
        self.gitlab = gitlab.Gitlab(host_domain, private_token=token)
        self.base_dir = base_dir
        self.user_login = user_login
        self.include_private = include_private
        self.include_forks = include_forks
        self.user: Optional[RESTObject] = None

    def _get_user_repos(self) -> list[Project]:
        """
        Fetches the user's repositories from GitLab, optionally including private repositories and forks.

        Returns:
            List[gitlab.v4.objects.Project]: A list of Project objects.
        """
        if not self.user:
            self.user = self.gitlab.users.list(username=self.user_login)[0]  # type: ignore

        try:
            kwargs: dict[str, Union[bool, str]] = {"owned": True}
            if not self.include_private:
                kwargs["visibility"] = "public"
            projects = self.gitlab.projects.list(**kwargs)
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
            LOGGER.error(f"Failed to fetch repositories: {e}")
            return []

    def clone_all(self):
        """
        Clones all repositories for a user.
        """
        repos = self._get_user_repos()
        print(f"Cloning {len(repos)} repositories.")
        for repo in repos:
            self._clone_repo(repo)

    def clone_group(self, group_id: int):
        """
        Clones all repositories for a user or all repositories within a group.

        Args:
            group_id (int): The ID of the group to clone repositories from.
        """
        self._clone_group_repos(group_id)

    def _clone_group_repos(self, group_id: int) -> None:
        """
        Clones all repositories within a specified group, including subgroups.

        Args:
            group_id (int): The ID of the group.
        """
        groups_to_process = [group_id]

        while groups_to_process:
            current_group_id = groups_to_process.pop(0)
            group = self._get_group_by_id(current_group_id)
            # subgroups = self._get_subgroups(group)
            repos = self._get_repos(group)

            for repo in repos:
                self._clone_repo(repo, extra_path=group.full_path)

            # for subgroup in subgroups:
            #     groups_to_process.append(subgroup.id)

    def _clone_repo(self, project, extra_path: str = "") -> None:
        """
        Clones the given project into the target directory, respecting group/subgroup structure.

        Args:
            project: The project to clone.
            extra_path (str): Additional path components for group/subgroup structure.
        """
        try:
            repo_path = self.base_dir / extra_path / project.path
            if not repo_path.exists():
                LOGGER.info(f"Cloning {project.web_url} into {repo_path}")
                repo_path.parent.mkdir(parents=True, exist_ok=True)
                g.Repo.clone_from(project.http_url_to_repo, repo_path)
            else:
                LOGGER.info(f"Project {project.path} already exists locally. Skipping clone.")
        except g.GitCommandError as e:
            LOGGER.error(f"Failed to clone {project.path}: {e}")

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
            LOGGER.error(f"Failed to get group with ID {group_id}: {e}")
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
            LOGGER.error(f"Failed to list subgroups for group {group.id}: {e}")
            return []

    def _get_repos(self, group):
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
            return projects
        except gitlab.exceptions.GitlabListError as e:
            LOGGER.error(f"Failed to list projects for group {group.id}: {e}")
            return []

    #
    # def _clone_repo(self, project: Project) -> None:
    #     """
    #     Clones the given GitLab project into the target directory.
    #
    #     Args:
    #         project (Project): The GitLab project to clone.
    #     """
    #     try:
    #         repo_path = self.base_dir / project.path
    #         if not repo_path.exists():
    #             LOGGER.info(f"Cloning {project.web_url} into {repo_path}")
    #             g.Repo.clone_from(project.http_url_to_repo, repo_path)
    #         else:
    #             LOGGER.info(f"Project {project.path} already exists locally. Skipping clone.")
    #     except g.GitCommandError as e:
    #         LOGGER.error(f"Failed to clone {project.path}: {e}")

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

        Returns:
            tuple: Counts of no_remote, not_found, is_fork, not_repo scenarios.
        """
        kwargs: dict[str, Union[str, bool]] = {"owned": True}
        if not self.include_private:
            kwargs["visibility"] = "public"
        user_projects = {
            project.path: self.gitlab.projects.get(id=project.id) for project in self.gitlab.projects.list(**kwargs)
        }

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

                    if repo_name not in user_projects:
                        not_found += 1
                        LOGGER.info(f"{repo_dir} is not found in your GitLab account.")
                        continue

                    gitlab_project = user_projects[repo_name]
                    if hasattr(gitlab_project, "forked_from_project") and gitlab_project.forked_from_project:
                        forked = True
                    else:
                        forked = False
                    if not forked:
                        is_fork += 1
                        LOGGER.info(f"{repo_dir} is a fork of another repository.")
                        continue

                except g.InvalidGitRepositoryError:
                    not_repo += 1
                    LOGGER.info(f"{repo_dir} is not a valid Git repository.")
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
        pypi_manager = PyPiManager(pypi_owner_name)
        found = 0
        for repo_dir in self.base_dir.iterdir():
            LOGGER.debug(f"Checking {repo_dir}")
            if repo_dir.is_dir():
                try:
                    repo = g.Repo(repo_dir)
                    package_name = repo_dir.name  # Assuming the repo name is the package name

                    pypi_data, status_code = pypi_manager.get_info(package_name)
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
                    LOGGER.warning(f"{repo_dir} is not a valid Git repository.")
                except Exception as e:
                    LOGGER.error(f"Error checking {repo_dir}: {e}")
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
        Fetches and prints beautifully formatted information about the user's GitHub repositories.
        """
        try:
            table = Table(title="Gitlab Repositories")

            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Description", style="magenta")
            table.add_column("URL", style="green")
            table.add_column("Private", style="red")
            table.add_column("Fork", style="blue")

            kwargs: dict[str, Union[bool, str]] = {"owned": True}
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
        Fetches and prints a summary of the user's GitHub account.
        """
        print("not implemented yet")
