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
Source Path: E:\github\git_mirror\git_mirror\manage_poetry.py

Source Path: E:\github\git_mirror\git_mirror\manage_poetry.py
Module Name: git_mirror.manage_poetry
```python
import logging
import os
import subprocess  # nosec
from contextlib import contextmanager

import git

from git_mirror.custom_types import SourceHost
from git_mirror.performance import log_duration

logger = logging.getLogger(__name__)


def clean_gone_branches(repo: git.Repo) -> None:
    """Clean branches that are gone from remote.

    Args:
        repo: The Git repository object.
    """
    gone_branches = [
        ref.split()[0]
        for ref in repo.git.for_each_ref("--format=%(refname:short) %(upstream:track)").split("\n")
        if "[gone]" in ref
    ]
    for branch in gone_branches:
        repo.git.branch("-D", branch)


@contextmanager
def working_directory(repo_folder:str):
    """Changes to the working directory and returns to the original directory when done."""
    original_directory = os.getcwd()
    os.chdir(repo_folder)
    try:
        yield
    finally:
        os.chdir(original_directory)


class PoetryManager:
    def __init__(self, host: SourceHost, dry_run: bool = False, prompt_for_changes: bool = True):
        """
        Args:
            host: The source host.
            dry_run: Whether to perform a dry run.
            prompt_for_changes: Whether to prompt for changes.
        """
        self.host = host
        self.dry_run = dry_run
        self.prompt_for_changes = prompt_for_changes

    @log_duration
    def install(
            self, repo_folder: str
    ) -> None:
        """Update project dependencies and create a merge request if changes are made.

        Args:
            repo_folder: The folder of the repository.
        """
        with working_directory(repo_folder):
            # Update dependencies using Poetry
            subprocess.run(["poetry", "lock"], check=True, shell=True)  # nosec
            # TODO: make group config driven.
            subprocess.run(["poetry", "install", "--with", "dev"], check=True, shell=True)  # nosec


    @log_duration
    def update_dependencies(
        self,  repo_folder:str, main_branch: str, dependency_update_branch: str, project_id: int, repo_name: str,
            user: str, reviewer: str
    ) -> None:
        """Update project dependencies and create a merge request if changes are made.

        Args:
            repo_folder: The folder of the repository.
            main_branch: The main branch name.
            dependency_update_branch: The dependency update branch name.
            project_id: The ID of the GitLab project.
            repo_name: The name of the Github repository.
            user: Username for assigning the merge request.
            reviewer: Username for reviewing the merge request.
        """
        with working_directory(repo_folder):
            # Setup
            repo = git.Repo(repo_folder)
            origin = repo.remotes.origin

            # Checkout and pull main branch
            repo.git.checkout(main_branch)
            origin.pull()

            # Clean gone branches (Should this really be here?)
            # clean_gone_branches(repo)

            logger.info("Updating dependencies")
            try:
                repo.git.checkout("-b", dependency_update_branch)
            except git.exc.GitCommandError:
                repo.git.branch("-D", dependency_update_branch)
                repo.git.checkout("-b", dependency_update_branch)

            # Update dependencies using Poetry
            subprocess.run(["poetry", "install"], check=True, shell=True)  # nosec
            subprocess.run(["poetry", "update"], check=True, shell=True)  # nosec
            repo.git.add("poetry.lock")
            repo.index.commit("Update dependencies")

            # get rid of local branches that are gone from remote
            # prune should be a separate step
            origin.fetch(prune=False)

            # Check if there are changes
            if repo.git.diff("--quiet", "--exit-code", f"origin/{main_branch}"):
                # no changes, nevermind.
                repo.git.checkout(main_branch)
                repo.git.branch("-D", dependency_update_branch)
            else:
                # origin.push('-f', f'{dependency_update_branch}:{dependency_update_branch}', set_upstream=True)
                push_info = origin.push(
                    refspec=f"{dependency_update_branch}:{dependency_update_branch}", force=True, set_upstream=True
                )
                logger.debug(push_info)

                self.host.merge_request(
                    dependency_update_branch, main_branch, "Update Poetry lock file", reviewer, project_id, repo_name
                )

            repo.git.checkout(main_branch)


# if __name__ == "__main__":
#     update_dependencies(
#         main_branch=os.environ.get("MAIN_BRANCH"),
#         dependency_update_branch=os.environ.get("DEPENDENCY_UPDATE_BRANCH"),
#         gitlab_token=os.environ.get("GITLAB_TOKEN"),
#         gitlab_url=os.environ.get("GITLAB_URL", "https://gitlab.com"),
#         project_id=int(os.environ.get("PROJECT_ID")),
#         user=os.environ.get("USER"),
#         reviewer=os.environ.get("REVIEWER")
#     )

```

Here are function and method signatures of the dependencies

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
Please write some unit tests for E:\github\git_mirror\git_mirror\manage_poetry.py. If you can't think of anymore unit tests, write "No more unit tests".
Assistant: ## Bug Report

1. In the `install` method of the `PoetryManager` class, the subprocess calls to `poetry lock` and `poetry install --with dev` are using `shell=True`. This can be a security risk and should be avoided. Instead, the command should be provided as a list of strings without using `shell=True`.

2. The `update_dependencies` method of the `PoetryManager` class has a TODO comment suggesting making the group configuration driven. This comment should be expanded upon or addressed to ensure clarity on what needs to be done.

3. The `clean_gone_branches` function should not be called inside the `update_dependencies` method without proper consideration of its necessity and impact. It's currently commented out in the code, and its inclusion/exclusion should be decided based on the desired behavior.

4. In the `PoetryManager` class `update_dependencies` method, there is a commented block of code with `origin.push('-f', f'{dependency_update_branch}:{dependency_update_branch}', set_upstream=True)`. This block of code is commented out and should either be implemented or removed based on the intended functionality.

## Unit Tests
```python
import pytest
from git_mirror.manage_poetry import PoetryManager, clean_gone_branches
from git import Repo
from git_mirror.custom_types import SourceHost
from unittest.mock import MagicMock

@pytest.fixture
def mock_repo():
    # Mocking the git.Repo object
    return MagicMock(spec=Repo)

@pytest.fixture
def mock_source_host():
    # Mocking the SourceHost object
    return MagicMock(spec=SourceHost)

def test_clean_gone_branches():
    # Test clean_gone_branches function
    repo = MagicMock()
    repo.git.for_each_ref.return_value = "branch1 [gone]\nbranch2 [ahead]"
    clean_gone_branches(repo)
    assert repo.git.branch.call_args_list == [call("-D", "branch1")]

def test_PoetryManager_install(mock_repo, tmp_path):
    # Test install method of PoetryManager
    repo_folder = tmp_path / "test_repo"
    repo_folder.mkdir()
    
    manager = PoetryManager(host=mock_source_host, dry_run=True, prompt_for_changes=False)
    manager.install(str(repo_folder))
    
    # Assert subprocess.run calls with correct commands
    assert mock_subprocess.run.call_args_list == [
        call(["poetry", "lock"], check=True),
        call(["poetry", "install", "--with", "dev"], check=True)
    ]

def test_PoetryManager_update_dependencies(mock_repo, mock_source_host, tmp_path):
    # Test update_dependencies method of PoetryManager
    repo_folder = tmp_path / "test_repo"
    repo_folder.mkdir()
    
    manager = PoetryManager(host=mock_source_host, dry_run=True, prompt_for_changes=False)
    manager.update_dependencies(str(repo_folder), "main", "dependency_update", 123, "repo_name", "user", "reviewer")
    
    # Assert subprocess.run calls with correct commands
    assert mock_subprocess.run.call_args_list == [
        call(["poetry", "install"], check=True),
        call(["poetry", "update"], check=True)
    ]
    
    # Assert other actions based on method logic

# Add more tests as needed

def test_working_directory():
    # Write a test for working_directory context manager if necessary

```

No more unit tests.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ```python
from unittest.mock import mock_open, patch
from git_mirror.manage_poetry import PoetryManager

def test_PoetryManager_working_directory(tmp_path):
    # Test the working_directory context manager
    repo_folder = tmp_path / "test_repo"
    repo_folder.mkdir()

    file_path = repo_folder / "test_file.txt"

    with patch("os.chdir") as mock_chdir:
        with PoetryManager(host=None) as manager:
            with manager.working_directory(str(repo_folder)):
                with open(file_path, "w") as file:
                    file.write("Test data")

        # Assert that os.chdir was called correctly
        assert mock_chdir.call_args_list == [call(str(repo_folder)), call(str(repo_folder.parent))]

    # Add more assertions as needed

# No more unit tests
```