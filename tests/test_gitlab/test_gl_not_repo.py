import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from git import InvalidGitRepositoryError, Remote, Repo
from gitlab.v4.objects import Project

from git_mirror.manage_git import extract_repo_name
from git_mirror.manage_gitlab import GitlabRepoManager

LOGGER = logging.getLogger(__name__)


@patch("git.Repo")
@patch("git_mirror.manage_git.find_git_repos")
def test_not_repo(mock_iterdir, mock_git_repo, tmp_path):
    # Mock setup
    base_dir = tmp_path
    manager = GitlabRepoManager("token", base_dir, "user_login", prompt_for_changes=False)
    manager.client = lambda: MagicMock()
    manager.user = MagicMock()

    manager.project = MagicMock()
    manager.project.id = 1
    manager.project.forked_from_project = True

    # Simulate directories in the base directory
    mock_iterdir.return_value = [base_dir / "repo1", base_dir / "not_a_repo", base_dir / "fork_repo"]

    os.makedirs(str(tmp_path / "repo1"))
    os.makedirs(str(tmp_path / "fork_repo"))
    os.makedirs(str(tmp_path / "not_a_repo"))

    # Simulate valid and invalid git repositories
    def repo_side_effect(path):
        if path.name == "not_a_repo":
            raise InvalidGitRepositoryError("Not a git repository")
        else:
            mock = MagicMock(spec=Repo)
            if path.name == "repo1":
                remote = MagicMock(spec=Remote)
                remote.config_reader.get.return_value = "https://gitlab.com/user_login/repo1.git"
                remote.id = 1
                remote.forked_from_project = False
                mock.remotes = [remote]

            elif path.name == "fork_repo":
                remote = MagicMock(spec=Remote)
                remote.id = 2
                remote.config_reader.get.return_value = "https://gitlab.com/user_login/fork_repo.git"
                remote.forked_from_project = True
                mock.remotes = [remote]

            return mock

    # what to do with side effect
    mock_git_repo.side_effect = repo_side_effect

    # Simulate user's repositories on gitlab, including a fork
    mock_user_repo = MagicMock(spec=Project)
    mock_user_repo.id = 1
    mock_user_repo.path = "repo1"
    mock_user_repo.forked_from_project = False

    mock_fork_repo = MagicMock(spec=Project)
    mock_fork_repo.id = 2
    mock_fork_repo.path = "fork_repo"
    mock_fork_repo.forked_from_project = True

    get = MagicMock()

    def get_side_effect(id):
        if id == 1:
            return mock_user_repo
        return mock_fork_repo

    get.side_effect = get_side_effect
    mgl = MagicMock()

    mgl.projects.get = get
    mgl.projects.list.return_value = [mock_user_repo, mock_fork_repo]
    manager.client = lambda: mgl
    no_remote, not_found, is_fork, not_repo = manager.not_repo()

    assert no_remote == 0
    assert not_found == 0
    assert is_fork == 1
    assert not_repo == 1


@pytest.mark.parametrize(
    "remote_url,expected_name",
    [
        ("https://gitlab.com/user/repo.git", "repo"),
        ("git@gitlab.com:user/repo.git", "repo"),
        ("https://gitlab.com/user/repo", "repo"),
        ("git@gitlab.com:user/repo", "repo"),
        ("https://gitlab.com/user/repo.git/", "repo"),  # Trailing slash
        ("git@gitlab.com:user/repo.git/", "repo"),  # Trailing slash
    ],
)
def test_extract_repo_name(remote_url, expected_name):
    repo_name = extract_repo_name(remote_url)
    assert repo_name == expected_name
