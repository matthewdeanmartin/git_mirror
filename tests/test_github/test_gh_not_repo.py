import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from git import InvalidGitRepositoryError, Remote, Repo
from github.Repository import Repository as ghRepository

from git_mirror.manage_git import extract_repo_name
from git_mirror.manage_github import GithubRepoManager

LOGGER = logging.getLogger(__name__)


@patch("git.Repo")
@patch("pathlib.Path.iterdir")
def test_not_repo(mock_iterdir, mock_git_repo, tmp_path):
    # Mock setup
    base_dir = tmp_path
    manager = GithubRepoManager("token", base_dir, "user_login", include_private=True, include_forks=True)
    manager.user = MagicMock()
    mock_get_repos = MagicMock()
    manager.user.get_repos = mock_get_repos

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
                remote.config_reader.get.return_value = "https://github.com/user_login/repo1.git"
                mock.remotes = [remote]

            elif path.name == "fork_repo":
                remote = MagicMock(spec=Remote)
                remote.config_reader.get.return_value = "https://github.com/user_login/fork_repo.git"
                mock.remotes = [remote]

            return mock

    mock_git_repo.side_effect = repo_side_effect

    # Simulate user's repositories on GitHub, including a fork
    mock_user_repo = MagicMock(spec=ghRepository)
    mock_user_repo.private = False
    mock_user_repo.name = "repo1"
    mock_user_repo.fork = False
    mock_user_repo.owner.login = "user_login"

    mock_fork_repo = MagicMock(spec=ghRepository)
    mock_user_repo.private = False
    mock_fork_repo.name = "fork_repo"
    mock_fork_repo.fork = True
    mock_fork_repo.owner.login = "user_login"

    mock_get_repos.return_value = [mock_user_repo, mock_fork_repo]

    no_remote, not_found, is_fork, not_repo = manager.not_repo()

    assert no_remote == 0
    assert not_found == 0
    assert is_fork == 1  # Including fork
    assert not_repo == 1  # 1 really is a bad repo.


@pytest.mark.parametrize(
    "remote_url,expected_name",
    [
        ("https://github.com/user/repo.git", "repo"),
        ("git@github.com:user/repo.git", "repo"),
        ("https://github.com/user/repo", "repo"),
        ("git@github.com:user/repo", "repo"),
        ("https://github.com/user/repo.git/", "repo"),  # Trailing slash
        ("git@github.com:user/repo.git/", "repo"),  # Trailing slash
    ],
)
def test_extract_repo_name(remote_url, expected_name):
    repo_name = extract_repo_name(remote_url)
    assert repo_name == expected_name
