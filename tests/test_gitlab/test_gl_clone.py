from unittest.mock import MagicMock, patch

import pytest
from git.exc import GitCommandError
from gitlab.v4.objects import Project

from git_mirror.dummies import Dummy
from git_mirror.manage_gitlab import GitlabRepoManager


@pytest.fixture
def mock_gitlab_repo():
    mock = MagicMock(spec=Project)
    mock.private = False
    # Set up the nested owner.login attribute
    owner_mock = MagicMock()
    owner_mock.login = "fake-user"
    mock.owner = owner_mock
    mock.namespace = {"path": "fake-user"}
    mock.forked_from_project = False
    mock.http_url_to_repo = "http://example.com"
    mock.web_url = "http://example.com"
    mock.path = "fake-user"
    mock.html_url = "http://example.com"
    mock.id = "1"
    return mock


@pytest.fixture
def gitlab_repo_manager(tmp_path):
    token = "fake-token"
    base_dir = tmp_path  # Use pytest's tmp_path fixture to avoid real filesystem writes
    user_login = "fake-user"
    manager = GitlabRepoManager(token, base_dir, user_login, prompt_for_changes=False)
    return manager


@pytest.fixture
def mock_repo():
    mock = MagicMock(spec=Project)
    mock.name = "test_repo"
    mock.path = "fake-user/test_repo"
    mock.web_url = "https://gitlab.com/fake-user/test_repo"
    return mock


@patch("git.Repo.clone_from")
@patch("git_mirror.manage_gitlab.GitlabRepoManager._get_user_repos")
def test_clone_all(mock_get_user_repos, mock_clone_from, gitlab_repo_manager, mock_gitlab_repo):
    # Setup
    mock_get_user_repos.return_value = [mock_gitlab_repo]

    # Execute
    gitlab_repo_manager.clone_all()

    # Assert
    mock_clone_from.assert_called_once_with(
        f"{mock_gitlab_repo.html_url}", gitlab_repo_manager.base_dir / mock_gitlab_repo.path
    )


@patch("git.Repo.clone_from")
def test_clone_repo_already_exists(mock_clone_from, gitlab_repo_manager, mock_gitlab_repo, tmp_path):
    # Setup: Create a directory with the same name as the repo to simulate its existence
    (tmp_path / mock_gitlab_repo.path).mkdir()
    (tmp_path / mock_gitlab_repo.path / ".git").mkdir()

    # Execute

    mock_gitlab_repo = gitlab_repo_manager._thread_safe_repos([mock_gitlab_repo])[0]
    gitlab_repo_manager._clone_repo((mock_gitlab_repo, Dummy()))

    # Assert
    mock_clone_from.assert_not_called()


@patch("git.Repo.clone_from")
def test_clone_repo_clone_success(mock_clone_from, gitlab_repo_manager, mock_gitlab_repo):
    # Execute
    mock_gitlab_repo = gitlab_repo_manager._thread_safe_repos([mock_gitlab_repo])[0]
    gitlab_repo_manager._clone_repo((mock_gitlab_repo, Dummy()))

    # Assert
    mock_clone_from.assert_called_once_with(
        f"{mock_gitlab_repo['http_url_to_repo']}", gitlab_repo_manager.base_dir / mock_gitlab_repo["path"]
    )


@patch("git.Repo.clone_from", side_effect=GitCommandError("clone", "error"))
def test_clone_repo_clone_failure(mock_clone_from, gitlab_repo_manager, mock_gitlab_repo):
    # Execute
    mock_gitlab_repo = gitlab_repo_manager._thread_safe_repos([mock_gitlab_repo])[0]
    gitlab_repo_manager._clone_repo((mock_gitlab_repo, Dummy()))

    # Assert
    mock_clone_from.assert_called_once()
    # Optionally, assert on logging if desired, but requires additional setup to capture log output


if __name__ == "__main__":
    pytest.main()
