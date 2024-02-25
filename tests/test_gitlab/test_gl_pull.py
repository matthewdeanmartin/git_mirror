import logging
from unittest.mock import ANY, patch

import pytest
from git import GitCommandError

from git_mirror.dummies import Dummy
from git_mirror.manage_gitlab import GitlabRepoManager

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def gitlab_repo_manager(tmp_path):
    token = "fake-token"
    base_dir = tmp_path  # Use pytest's tmp_path fixture for a temporary filesystem
    user_login = "fake-user"
    manager = GitlabRepoManager(token, base_dir, user_login)
    return manager


def create_fake_repo(tmp_path, repo_name):
    """Helper function to create a fake repo directory."""
    (tmp_path / repo_name).mkdir()
    (tmp_path / repo_name / ".git").mkdir()


@patch("git.Repo")
def test_pull_repo_success(mock_repo_class, gitlab_repo_manager, tmp_path):
    repo_name = "test_repo"
    repo_path = tmp_path / repo_name
    create_fake_repo(tmp_path, repo_name)

    gitlab_repo_manager.pull_repo((repo_path, Dummy()))

    mock_repo_class.assert_called_once_with(repo_path)
    mock_repo_class.return_value.remotes.origin.pull.assert_called_once()


@patch("git.Repo")
def test_pull_repo_failure(mock_repo_class, gitlab_repo_manager, tmp_path):
    repo_name = "test_repo"
    repo_path = tmp_path / repo_name
    create_fake_repo(tmp_path, repo_name)

    # Simulate a GitCommandError on pull
    mock_repo_class.return_value.remotes.origin.pull.side_effect = GitCommandError("pull", "error")

    gitlab_repo_manager.pull_repo((repo_path, Dummy()))

    mock_repo_class.assert_called_once_with(repo_path)
    mock_repo_class.return_value.remotes.origin.pull.assert_called_once()


@patch("git_mirror.manage_gitlab.GitlabRepoManager.pull_repo")
def test_pull_all(mock_pull_repo, gitlab_repo_manager, tmp_path):
    # Create fake repositories in the base directory
    repo_names = ["repo1", "repo2"]
    for name in repo_names:
        create_fake_repo(tmp_path, name)

    gitlab_repo_manager.pull_all()

    # Verify pull_repo is called for each repository
    assert mock_pull_repo.call_count == len(repo_names)
    for name in repo_names:
        mock_pull_repo.assert_any_call((tmp_path / name, ANY))
