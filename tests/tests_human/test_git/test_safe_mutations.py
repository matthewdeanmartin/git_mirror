"""Hardening tests for batch mutations (Phase 7)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import git as g

from git_mirror.custom_types import UpdateBranchArgs
from git_mirror.manage_github import GithubRepoManager
from git_mirror.utils.dummies import Dummy


def manager(tmp_path, dry_run=False):
    return GithubRepoManager(
        token="t",
        base_dir=tmp_path,
        user_login="octocat",
        dry_run=dry_run,
        prompt_for_changes=False,
    )


def test_pull_repo_skips_dirty_repo(tmp_path):
    mgr = manager(tmp_path)
    fake_repo = MagicMock()  # truthy .remotes with an .origin attribute
    fake_repo.is_dirty.return_value = True

    with patch("git_mirror.manage_github.g.Repo", return_value=fake_repo):
        mgr.pull_repo((tmp_path / "repo", Dummy()))

    # A dirty repo must never be pulled.
    fake_repo.remotes.origin.pull.assert_not_called()


def test_pull_repo_skips_repo_without_remote(tmp_path):
    mgr = manager(tmp_path)
    fake_repo = MagicMock()
    fake_repo.remotes = []

    with patch("git_mirror.manage_github.g.Repo", return_value=fake_repo):
        mgr.pull_repo((tmp_path / "repo", Dummy()))
    # No crash, nothing pulled (no remote).


def test_pull_repo_pulls_clean_repo(tmp_path):
    mgr = manager(tmp_path)
    fake_repo = MagicMock()  # truthy .remotes
    fake_repo.is_dirty.return_value = False

    with patch("git_mirror.manage_github.g.Repo", return_value=fake_repo):
        mgr.pull_repo((tmp_path / "repo", Dummy()))

    fake_repo.remotes.origin.pull.assert_called_once()


def test_update_skips_dirty_repo(tmp_path):
    mgr = manager(tmp_path)
    fake_repo = MagicMock()
    fake_repo.is_dirty.return_value = True

    with (
        patch("git_mirror.manage_github.g.Repo", return_value=fake_repo),
        patch.object(GithubRepoManager, "client") as mock_client,
    ):
        mock_client.return_value.get_repo.return_value.default_branch = "main"
        mgr.update_local_branches(UpdateBranchArgs(tmp_path / "repo", "repo", False, Dummy()))

    # Dirty repo: never fetch/checkout.
    fake_repo.remotes.origin.fetch.assert_not_called()


def test_update_aborts_on_conflict_and_restores_branch(tmp_path):
    mgr = manager(tmp_path)

    fake_repo = MagicMock()
    fake_repo.is_dirty.return_value = False
    fake_repo.active_branch.name = "feature"

    main_head = MagicMock()
    main_head.name = "main"
    feat_head = MagicMock()
    feat_head.name = "feature"
    fake_repo.heads = [main_head, feat_head]

    # Make the merge raise a conflict.
    fake_repo.git.merge.side_effect = g.exc.GitCommandError("merge", 1)

    with (
        patch("git_mirror.manage_github.g.Repo", return_value=fake_repo),
        patch.object(GithubRepoManager, "client") as mock_client,
        patch.object(GithubRepoManager, "abort_in_progress_merge_or_rebase") as mock_abort,
    ):
        mock_client.return_value.get_repo.return_value.default_branch = "main"
        mgr.update_local_branches(UpdateBranchArgs(tmp_path / "repo", "repo", False, Dummy()))

    # Conflict must trigger an abort...
    mock_abort.assert_called_once()
    # ...and we must end back on the original branch.
    fake_repo.git.checkout.assert_any_call("feature")


def test_update_invalid_repo_is_isolated(tmp_path):
    mgr = manager(tmp_path)
    with patch("git_mirror.manage_github.g.Repo", side_effect=g.InvalidGitRepositoryError("bad")):
        # Should return quietly, not raise, so the batch continues.
        mgr.update_local_branches(UpdateBranchArgs(tmp_path / "repo", "repo", False, Dummy()))
