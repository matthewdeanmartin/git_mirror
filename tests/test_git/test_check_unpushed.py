import io
from unittest.mock import patch

import git as g
import pytest

from git_mirror.manage_git import GitManager


# Helper function to initialize a git repository with an optional remote
def init_repo(tmp_path, name, with_remote=False):
    repo_path = tmp_path / name
    repo_path.mkdir()
    repo = g.Repo.init(repo_path)
    # Simulate a commit by creating a file and committing it
    (repo_path / "README.md").write_text("# Test Repository\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    if with_remote:
        # Simulate a remote by initializing a bare repository and adding it as a remote
        remote_path = tmp_path / f"{name}_remote"
        g.Repo.init(remote_path, bare=True)
        remote = repo.create_remote("origin", remote_path.as_uri())
        # Push to simulate setting up tracking information
        remote.push(refspec=f"{repo.active_branch.name}:{repo.active_branch.name}")

    return repo_path, repo


@pytest.fixture
def git_repo_manager(tmp_path):
    return GitManager(tmp_path)


def test_check_for_uncommitted_changes_no_changes(git_repo_manager, tmp_path):
    _, repo = init_repo(tmp_path, "repo1")
    # No uncommitted changes at this point

    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        git_repo_manager.check_for_uncommitted_or_unpushed_changes()
        assert "has uncommitted changes." not in mock_stdout.getvalue()


def test_check_for_uncommitted_changes_with_changes(git_repo_manager, tmp_path):
    repo_path, repo = init_repo(tmp_path, "repo2")
    # Simulate uncommitted changes
    (repo_path / "new_file.txt").write_text("Some changes")

    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        git_repo_manager.check_for_uncommitted_or_unpushed_changes()
        assert "has uncommitted changes." in mock_stdout.getvalue()


def test_check_for_unpushed_commits_no_unpushed(git_repo_manager, tmp_path):
    repo_path, _ = init_repo(tmp_path, "repo3", with_remote=True)
    # No unpushed commits, as we've just pushed the initial commit

    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        git_repo_manager.check_for_uncommitted_or_unpushed_changes()
        assert "has unpushed commits" not in mock_stdout.getvalue()


def test_check_for_unpushed_commits_with_unpushed_no_remote(git_repo_manager, tmp_path):
    repo_path, repo = init_repo(tmp_path, "repo4", with_remote=True)
    # Simulate an unpushed commit
    (repo_path / "another_file.txt").write_text("More changes")
    repo.index.add(["another_file.txt"])
    repo.index.commit("Another commit")

    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        git_repo_manager.check_for_uncommitted_or_unpushed_changes()
        # no remote! Should be checking for no remote
        assert "has unpushed commits" not in mock_stdout.getvalue()
