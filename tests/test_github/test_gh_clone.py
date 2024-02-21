from unittest.mock import MagicMock, patch

import github as gh
import pytest
from git.exc import GitCommandError
from github import Repository as ghRepository  # Assuming this import based on context

from git_mirror.manage_github import GithubRepoManager


@pytest.fixture
def mock_github_repo():
    mock = MagicMock(spec=gh.Repository)
    mock.private = False
    mock.fork = False
    # Set up the nested owner.login attribute
    owner_mock = MagicMock()
    owner_mock.login = "fake-user"
    mock.owner = owner_mock
    mock.name = "name"
    return mock


@pytest.fixture
def github_repo_manager(tmp_path):
    token = "fake-token"
    base_dir = tmp_path  # Use pytest's tmp_path fixture to avoid real filesystem writes
    user_login = "fake-user"
    manager = GithubRepoManager(token, base_dir, user_login)
    return manager


@pytest.fixture
def mock_repo():
    mock = MagicMock(spec=ghRepository)
    mock.name = "test_repo"
    mock.html_url = "https://github.com/fake-user/test_repo"
    return mock


@patch("git.Repo.clone_from")
@patch("git_mirror.manage_github.GithubRepoManager._get_user_repos")
def test_clone_all(mock_get_user_repos, mock_clone_from, github_repo_manager, mock_repo):
    # Setup
    mock_get_user_repos.return_value = [mock_repo]

    # Execute
    github_repo_manager.clone_all()

    # Assert
    mock_clone_from.assert_called_once_with(f"{mock_repo.html_url}.git", github_repo_manager.base_dir / mock_repo.name)


@patch("git.Repo.clone_from")
def test_clone_repo_already_exists(mock_clone_from, github_repo_manager, mock_github_repo, tmp_path):
    # Setup: Create a directory with the same name as the repo to simulate its existence
    (tmp_path / mock_github_repo.name).mkdir()
    (tmp_path / mock_github_repo.name / ".git").mkdir()

    # Execute
    github_repo_manager._clone_repo(mock_github_repo)

    # Assert
    mock_clone_from.assert_not_called()


@patch("git.Repo.clone_from")
def test_clone_repo_clone_success(mock_clone_from, github_repo_manager, mock_repo):
    # Execute
    github_repo_manager._clone_repo(mock_repo)

    # Assert
    mock_clone_from.assert_called_once_with(f"{mock_repo.html_url}.git", github_repo_manager.base_dir / mock_repo.name)


@patch("git.Repo.clone_from", side_effect=GitCommandError("clone", "error"))
def test_clone_repo_clone_failure(mock_clone_from, github_repo_manager, mock_repo):
    # Execute
    github_repo_manager._clone_repo(mock_repo)

    # Assert
    mock_clone_from.assert_called_once()
    # Optionally, assert on logging if desired, but requires additional setup to capture log output


if __name__ == "__main__":
    pytest.main()
