from pathlib import Path
from unittest.mock import MagicMock, patch

from git_mirror import core
from git_mirror.core import BuildInfo, DashboardRow, RepoSelection


def test_dashboard_row_needs_attention():
    assert DashboardRow(name="x").needs_attention is False
    assert DashboardRow(name="x", dirty=True).needs_attention is True
    assert DashboardRow(name="x", ahead=1).needs_attention is True
    assert DashboardRow(name="x", behind=2).needs_attention is True
    assert DashboardRow(name="x", has_remote=False).needs_attention is True
    assert DashboardRow(name="x", build="failure").needs_attention is True
    assert DashboardRow(name="x", build="success").needs_attention is False
    assert DashboardRow(name="x", error="boom").needs_attention is True


def test_repo_dashboard_empty(tmp_path):
    with patch("git_mirror.manage_git.find_git_repos", return_value=[]):
        assert core.repo_dashboard(tmp_path) == []


def test_repo_dashboard_sorts_attention_first(tmp_path):
    repos = [tmp_path / "clean", tmp_path / "dirty", tmp_path / "another"]

    def fake_row(p):
        name = Path(p).name
        return DashboardRow(name=name, dirty=(name == "dirty"))

    with (
        patch("git_mirror.manage_git.find_git_repos", return_value=repos),
        patch("git_mirror.core.dashboard_row_for", side_effect=fake_row),
    ):
        rows = core.repo_dashboard(tmp_path)

    # "dirty" needs attention -> first; rest alphabetical.
    assert [r.name for r in rows] == ["dirty", "another", "clean"]


def test_repo_dashboard_respects_selection(tmp_path):
    repos = [tmp_path / "keep", tmp_path / "skip"]
    selection = RepoSelection(only={"keep"})

    with (
        patch("git_mirror.manage_git.find_git_repos", return_value=repos),
        patch("git_mirror.core.dashboard_row_for", side_effect=lambda p: DashboardRow(name=Path(p).name)),
    ):
        rows = core.repo_dashboard(tmp_path, selection=selection)

    assert [r.name for r in rows] == ["keep"]


def test_repo_dashboard_merges_builds(tmp_path):
    repos = [tmp_path / "repo1"]
    config = MagicMock(host_type="github")

    with (
        patch("git_mirror.manage_git.find_git_repos", return_value=repos),
        patch("git_mirror.core.dashboard_row_for", side_effect=lambda p: DashboardRow(name=Path(p).name)),
        patch(
            "git_mirror.core.get_build_statuses",
            return_value=[BuildInfo(repo_name="repo1", conclusion="failure", status_message="x")],
        ),
    ):
        rows = core.repo_dashboard(tmp_path, token="t", config=config)

    assert rows[0].build == "failure"
    assert rows[0].needs_attention is True


def test_repo_dashboard_build_fetch_failure_is_isolated(tmp_path):
    repos = [tmp_path / "repo1"]
    config = MagicMock(host_type="github")

    with (
        patch("git_mirror.manage_git.find_git_repos", return_value=repos),
        patch("git_mirror.core.dashboard_row_for", side_effect=lambda p: DashboardRow(name=Path(p).name)),
        patch("git_mirror.core.get_build_statuses", side_effect=RuntimeError("network down")),
    ):
        rows = core.repo_dashboard(tmp_path, token="t", config=config)

    # The row still comes back; build column just stays empty.
    assert rows[0].name == "repo1"
    assert rows[0].build == ""
