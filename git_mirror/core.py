"""
Core orchestration API shared by the CLI (router) and the GUI.

This is the single home for batch operations over a folder of GitHub repos.
Functions here return plain data (the dataclasses below) and never render; the
CLI router and the GUI both call into this module so operation logic and host
manager construction cannot drift between the two front ends.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import git as g

from git_mirror.manage_config import ConfigData, ConfigManager, default_config_path
from git_mirror.utils.safe_env import load_env

load_env()

LOGGER = logging.getLogger(__name__)


# ── Data containers returned to the GUI ──────────────────────────────


@dataclass
class RepoStatus:
    path: Path
    dirty: bool = False
    unpushed_branches: list[str] = field(default_factory=list)
    untracked_branches: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class RepoInfo:
    name: str
    description: str
    private: bool
    fork: bool
    html_url: str = ""


@dataclass
class BuildInfo:
    repo_name: str
    conclusion: str
    status_message: str


@dataclass
class ActionResult:
    success: bool
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class DashboardRow:
    """One repo's combined local + remote state for the status dashboard."""

    name: str
    branch: str = ""
    dirty: bool = False
    ahead: int = 0
    behind: int = 0
    untracked_branches: int = 0
    has_remote: bool = True
    last_commit_age_days: int | None = None
    build: str = ""  # latest CI conclusion, if known
    error: str | None = None

    @property
    def needs_attention(self) -> bool:
        return bool(
            self.error
            or self.dirty
            or self.ahead
            or self.behind
            or not self.has_remote
            or self.build in ("failure", "cancelled", "timed_out")
        )


# ── Manager factory (single construction point for CLI + GUI) ────────


def build_manager(
    token: str,
    base_dir: Path,
    user_name: str,
    *,
    include_private: bool = False,
    include_forks: bool = False,
    host_domain: str | None = None,
    dry_run: bool = False,
    prompt_for_changes: bool = True,
    selection: RepoSelection | None = None,
):
    """Construct the GitHub repo manager.

    This is the single place that knows how to build a host manager, shared by
    the CLI router and the GUI/core data functions so the construction logic
    cannot drift.
    """
    from git_mirror import manage_github as mgh

    return mgh.GithubRepoManager(
        token,
        Path(base_dir).expanduser(),
        user_name,
        include_private=include_private,
        include_forks=include_forks,
        host_domain=host_domain or "https://api.github.com",
        dry_run=dry_run,
        prompt_for_changes=prompt_for_changes,
        selection=selection,
    )


def manager_from_config(
    token: str,
    config: ConfigData,
    *,
    dry_run: bool = False,
    prompt_for_changes: bool = True,
):
    """Build a manager directly from a ConfigData."""
    if not config.target_dir:
        raise ValueError("No target directory configured")
    return build_manager(
        token,
        config.target_dir,
        config.user_name,
        include_private=config.include_private,
        include_forks=config.include_forks,
        host_domain=config.host_url,
        dry_run=dry_run,
        prompt_for_changes=prompt_for_changes,
    )


# ── Repo selection / filtering ───────────────────────────────────────


@dataclass
class RepoSelection:
    """An effective repo filter built from config overrides + CLI flags.

    Resolution rules (applied per repo name):

    - ``only`` set -> keep only those names (still subject to ``exclude``).
    - ``tags`` set -> keep repos carrying at least one of those tags.
    - ``exclude`` set -> drop those names.
    - config ``ignore = true`` -> drop, unless ``include_ignored`` is set or the
      repo was explicitly named in ``only``.
    """

    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    only: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    exclude: set[str] = field(default_factory=set)
    include_ignored: bool = False

    def is_selected(self, repo_name: str) -> bool:
        if repo_name in self.exclude:
            return False
        explicitly_named = repo_name in self.only
        if self.only and not explicitly_named:
            return False
        if self.tags:
            repo_tags = set(self.overrides.get(repo_name, {}).get("tags", []))
            if not (repo_tags & self.tags):
                return False
        if not self.include_ignored and not explicitly_named:
            if self.overrides.get(repo_name, {}).get("ignore"):
                return False
        return True

    def filter(self, repo_names: list[str]) -> list[str]:
        return [name for name in repo_names if self.is_selected(name)]


def build_selection(
    host: str,
    config_path: Path | None = None,
    *,
    only: list[str] | None = None,
    tags: list[str] | None = None,
    exclude: list[str] | None = None,
    include_ignored: bool = False,
) -> RepoSelection:
    """Build a RepoSelection by reading config overrides and applying flags."""
    cm = ConfigManager(config_path or default_config_path())
    overrides = cm.load_repo_overrides(host)
    return RepoSelection(
        overrides=overrides,
        only=set(only or []),
        tags=set(tags or []),
        exclude=set(exclude or []),
        include_ignored=include_ignored,
    )


# ── Service functions (called from background threads) ───────────────


def load_all_configs(config_path: Path | None = None) -> dict[str, ConfigData | None]:
    cm = ConfigManager(config_path or default_config_path())
    return cm.load_config_objects()


def run_doctor(config_path: Path | None = None, host: str | None = None) -> list[tuple[str, list[Any]]]:
    """Returns list of (host_label, checks) tuples."""
    from git_mirror.manage_config import SetupCheck, _host_label

    cm = ConfigManager(config_path or default_config_path())
    results: list[tuple[str, list[Any]]] = []
    configs = cm.load_config_objects()
    hosts = [host] if host else [name for name, data in configs.items() if data]
    for h in hosts:
        config = cm.load_config(h)
        if not config:
            results.append((h, [SetupCheck(h, False, "No configuration found", "Run init")]))
            continue
        checks = cm._run_checks(config)
        results.append((_host_label(config), checks))
    return results


def scan_local_changes(target_dir: Path) -> list[RepoStatus]:
    """Scan repos for uncommitted/unpushed changes without printing."""
    from git_mirror.manage_git import find_git_repos

    repos = find_git_repos(target_dir)
    statuses: list[RepoStatus] = []
    for repo_dir in sorted(repos):
        status = RepoStatus(path=repo_dir)
        try:
            repo = g.Repo(repo_dir)
            if repo.is_dirty(untracked_files=True):
                status.dirty = True
            for branch in repo.heads:
                try:
                    if branch.tracking_branch():
                        local_ahead = list(repo.iter_commits(f"{branch.tracking_branch()}..{branch}"))
                        if len(local_ahead) > 0:
                            status.unpushed_branches.append(branch.name)
                    else:
                        status.untracked_branches.append(branch.name)
                except g.GitCommandError:
                    pass
        except g.InvalidGitRepositoryError:
            status.error = "Invalid git repository"
        except Exception as e:
            status.error = str(e)
        statuses.append(status)
    return statuses


def _dashboard_row_for(repo_dir: Path) -> DashboardRow:
    """Compute the local state of a single repo (safe to run in a thread)."""
    from datetime import datetime, timezone

    row = DashboardRow(name=repo_dir.name)
    try:
        repo = g.Repo(repo_dir)
        if repo.is_dirty(untracked_files=True):
            row.dirty = True
        row.has_remote = bool(repo.remotes)
        try:
            row.branch = repo.active_branch.name
        except (TypeError, ValueError):
            row.branch = "(detached)"
        for branch in repo.heads:
            tracking = branch.tracking_branch()
            if tracking is None:
                row.untracked_branches += 1
                continue
            if branch.name == row.branch:
                row.ahead = sum(1 for _ in repo.iter_commits(f"{tracking}..{branch}"))
                row.behind = sum(1 for _ in repo.iter_commits(f"{branch}..{tracking}"))
        try:
            last = repo.head.commit.committed_datetime
            now = datetime.now(timezone.utc)
            row.last_commit_age_days = max(0, (now - last).days)
        except Exception:
            row.last_commit_age_days = None
    except g.InvalidGitRepositoryError:
        row.error = "Invalid git repository"
    except Exception as e:  # pragma: no cover - defensive per-repo isolation
        row.error = str(e)
    return row


def repo_dashboard(
    target_dir: Path,
    *,
    selection: RepoSelection | None = None,
    token: str | None = None,
    config: ConfigData | None = None,
) -> list[DashboardRow]:
    """Build the combined fleet status, one row per local repo.

    Local git state is gathered in parallel.  If ``token`` and ``config`` are
    given, the latest GitHub Actions conclusion is merged in per repo.  Rows are
    sorted attention-first, then by name.
    """
    import multiprocessing.dummy as mp_threads

    from git_mirror.manage_git import find_git_repos

    repos = sorted(find_git_repos(target_dir))
    if selection is not None:
        repos = [r for r in repos if selection.is_selected(Path(r).name)]

    if not repos:
        return []

    pool_size = min(len(repos), 8)
    with mp_threads.Pool(pool_size) as pool:
        rows = pool.map(_dashboard_row_for, repos)

    if token and config:
        try:
            builds = {b.repo_name: b.conclusion for b in get_build_statuses(token, config)}
            for row in rows:
                if row.name in builds:
                    row.build = builds[row.name]
        except Exception as e:  # pragma: no cover - network optional
            LOGGER.debug(f"Could not fetch build statuses for dashboard: {e}")

    rows.sort(key=lambda r: (not r.needs_attention, r.name.lower()))
    return rows


def list_repos_data(token: str, host: str, config: ConfigData) -> list[RepoInfo]:
    """Fetch repo list and return as plain data."""
    import github as gh

    if config.host_url and config.host_url != "https://api.github.com":
        client = gh.Github(base_url=config.host_url, login_or_token=token)
    else:
        client = gh.Github(token)
    gh_user = client.get_user()
    repos = []
    for repo in gh_user.get_repos():
        if (
            (config.include_private or not repo.private)
            and (config.include_forks or not repo.fork)
            and repo.owner.login == config.user_name
        ):
            repos.append(
                RepoInfo(
                    name=repo.name,
                    description=repo.description or "No description",
                    private=repo.private,
                    fork=repo.fork,
                    html_url=repo.html_url,
                )
            )
    return repos


def clone_all_repos(token: str, config: ConfigData, dry_run: bool = False) -> ActionResult:
    """Clone all repos, return results as data."""
    result = ActionResult(success=True)
    if not config.target_dir:
        return ActionResult(success=False, errors=["No target directory configured"])
    base_path = config.target_dir.expanduser()

    mgr = manager_from_config(token, config, dry_run=dry_run, prompt_for_changes=False)
    repos = mgr._get_user_repos()
    for repo_data in mgr._thread_safe_repos(repos):
        name = repo_data["name"]
        url = repo_data["html_url"]
        dest = base_path / name
        if dest.exists():
            result.messages.append(f"Already exists: {name}")
            continue
        if dry_run:
            result.messages.append(f"Would clone: {url}")
            continue
        try:
            g.Repo.clone_from(f"{url}.git", dest)
            result.messages.append(f"Cloned: {name}")
        except g.GitCommandError as e:
            result.errors.append(f"Failed to clone {name}: {e}")

    if result.errors:
        result.success = False
    return result


def pull_all_repos(target_dir: Path, dry_run: bool = False) -> ActionResult:
    """Pull all repos in target dir."""
    from git_mirror.manage_git import find_git_repos

    result = ActionResult(success=True)
    repos = find_git_repos(target_dir)
    for repo_dir in sorted(repos):
        try:
            repo = g.Repo(repo_dir)
            if repo.remotes:
                if dry_run:
                    result.messages.append(f"Would pull: {repo_dir.name}")
                else:
                    repo.remotes.origin.pull()
                    result.messages.append(f"Pulled: {repo_dir.name}")
            else:
                result.messages.append(f"No remote: {repo_dir.name}")
        except Exception as e:
            result.errors.append(f"Failed to pull {repo_dir.name}: {e}")
    if result.errors:
        result.success = False
    return result


def find_non_repos(target_dir: Path) -> list[tuple[str, str]]:
    """Find directories that aren't repos. Returns (path, reason) tuples."""
    results: list[tuple[str, str]] = []
    if not target_dir.exists():
        return results
    for item in sorted(target_dir.iterdir()):
        if item.is_dir() and not (item / ".git").exists():
            if item.name.startswith("."):
                continue
            results.append((str(item), "Not a git repository"))
    return results


def get_build_statuses(token: str, config: ConfigData) -> list[BuildInfo]:
    """Get build statuses as data."""
    import github as gh

    if config.host_url and config.host_url != "https://api.github.com":
        client = gh.Github(base_url=config.host_url, login_or_token=token)
    else:
        client = gh.Github(token)
    user = client.get_user()
    builds: list[BuildInfo] = []
    for repo in user.get_repos():
        if repo.owner.login != config.user_name:
            continue
        if not config.include_private and repo.private:
            continue
        if not config.include_forks and repo.fork:
            continue
        runs = repo.get_workflow_runs()
        for i, run in enumerate(runs):
            if i >= 1:
                break
            builds.append(
                BuildInfo(
                    repo_name=repo.name,
                    conclusion=(run.conclusion or "").lower(),
                    status_message=f"{run.created_at} - {run.display_title} - {run.conclusion or 'pending'} - {run.status}",
                )
            )
    return builds


def get_token_for_host(config: ConfigData) -> str | None:
    """Read the token for the given config (keychain, env, or .env)."""
    from git_mirror.utils import credentials

    return credentials.get_token(config.host_name)
