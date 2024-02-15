import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from gitlab.v4.objects import Project

from git_mirror.manage_gitlab import GitlabRepoManager

# Assuming LOGGER is defined in the module where GitlabRepoManager is defined
LOGGER = logging.getLogger(__name__)


@pytest.fixture
def gitlab_repo_manager():
    token = "fake-token"
    base_dir = Path("/fake/path")
    user_login = "fake-user"
    include_private = True
    include_forks = False
    manager = GitlabRepoManager(token, base_dir, user_login, include_private, include_forks)
    return manager


@pytest.fixture
def mock_gitlab():
    with patch("gitlab.gitlab") as mock:
        yield mock


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
    return mock


def test_get_user_repos_includes_correct_repos(gitlab_repo_manager, mock_gitlab, mock_gitlab_repo):
    # Setup mock return values
    gitlab_repo_manager.gitlab = mock_gitlab()
    gitlab_repo_manager.gitlab.projects = MagicMock()
    mock_gitlab_repo.id = 1
    mock_gitlab_repo.namespace = {"path": "fake-user"}
    gitlab_repo_manager.gitlab.projects.list.return_value = [mock_gitlab_repo]
    gitlab_repo_manager.gitlab.projects.get.return_value = mock_gitlab_repo

    # Call the method under test
    repos = gitlab_repo_manager._get_user_repos()

    # Assertions
    assert len(repos) == 1
    assert repos[0] == mock_gitlab_repo


def test_get_user_repos_handles_gitlab_exception(gitlab_repo_manager, mock_gitlab, mock_gitlab_repo):
    # Setup to raise exception
    gitlab_repo_manager.gitlab = mock_gitlab()
    gitlab_repo_manager.gitlab.projects = MagicMock()
    gitlab_repo_manager.gitlab.projects.list.return_value = []

    mock_user = MagicMock()
    mock_gitlab.return_value.get_user.return_value = mock_user

    # Call the method under test expecting to catch the exception and return empty list
    repos = gitlab_repo_manager._get_user_repos()

    # Assertions
    assert repos == []
    # {'owned': True, 'visibility': 'private'}
    gitlab_repo_manager.gitlab.projects.list.assert_called_once_with(owned=True)


if __name__ == "__main__":
    pytest.main()
