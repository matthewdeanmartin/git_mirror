import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import github as gh
import pytest

from git_mirror.manage_github import GithubRepoManager

# Assuming LOGGER is defined in the module where GithubRepoManager is defined
LOGGER = logging.getLogger(__name__)


@pytest.fixture
def github_repo_manager():
    token = "fake-token"
    base_dir = Path("/fake/path")
    user_login = "fake-user"
    include_private = True
    include_forks = False
    manager = GithubRepoManager(token, base_dir, user_login, include_private, include_forks, prompt_for_changes=False)
    return manager


@pytest.fixture
def mock_github():
    with patch("github.Github") as mock:
        # Mock get_user to return a mock user object
        mock_user = MagicMock()
        mock.return_value.get_user.return_value = mock_user
        yield mock


@pytest.fixture
def mock_github_repo():
    mock = MagicMock(spec=gh.Repository)
    mock.private = False
    mock.fork = False
    # Set up the nested owner.login attribute
    owner_mock = MagicMock()
    owner_mock.login = "fake-user"
    mock.owner = owner_mock
    return mock


def test_get_user_repos_includes_correct_repos(github_repo_manager, mock_github, mock_github_repo):
    # Setup mock return values
    github_repo_manager.github = mock_github()
    mock_user = mock_github.return_value.get_user()
    mock_user.get_repos.return_value = [mock_github_repo]

    # Call the method under test
    repos = github_repo_manager._get_user_repos()

    # Assertions
    assert len(repos) == 1
    assert repos[0] == mock_github_repo
    mock_user.get_repos.assert_called_once()


def test_get_user_repos_handles_github_exception(github_repo_manager, mock_github):
    # Setup to raise exception
    github_repo_manager.github = mock_github()
    mock_user = MagicMock()
    mock_user.get_repos.side_effect = gh.GithubException(status=404, data={}, headers={})
    mock_github.return_value.get_user.return_value = mock_user

    # Call the method under test expecting to catch the exception and return empty list
    repos = github_repo_manager._get_user_repos()

    # Assertions
    assert repos == []
    mock_user.get_repos.assert_called_once_with()


if __name__ == "__main__":
    pytest.main()
