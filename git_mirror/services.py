"""
Orchestration helpers shared by CLI and GUI.

The GUI never touches the filesystem or network directly — it calls
functions here and renders the returned data.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import git as g

from git_mirror.manage_config import ConfigData, ConfigManager, default_config_path
from git_mirror.safe_env import load_env

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


# ── Service functions (called from background threads) ───────────────


def load_all_configs(config_path: Path | None = None) -> dict[str, ConfigData | None]:
    cm = ConfigManager(config_path or default_config_path())
    return cm.load_config_objects()


def run_doctor(config_path: Path | None = None, host: str | None = None) -> list[tuple[str, list[Any]]]:
    """Returns list of (host_label, checks) tuples."""
    from git_mirror.manage_config import SetupCheck, _host_label, _render_checks, _token_env_var

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


def list_repos_data(token: str, host: str, config: ConfigData) -> list[RepoInfo]:
    """Fetch repo list and return as plain data."""
    if config.host_type == "github":
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
    elif config.host_type == "gitlab":
        import gitlab

        gl = gitlab.Gitlab(config.host_url, private_token=token)
        gl.auth()
        gl_user = gl.user
        projects = gl_user.projects.list(all=True) if gl_user else []
        repos = []
        for p in projects:
            if config.include_private or p.visibility != "private":
                repos.append(
                    RepoInfo(
                        name=p.name,
                        description=getattr(p, "description", "") or "No description",
                        private=p.visibility == "private",
                        fork=bool(getattr(p, "forked_from_project", None)),
                        html_url=p.web_url,
                    )
                )
        return repos
    return []


def clone_all_repos(token: str, config: ConfigData, dry_run: bool = False) -> ActionResult:
    """Clone all repos, return results as data."""
    result = ActionResult(success=True)
    if not config.target_dir:
        return ActionResult(success=False, errors=["No target directory configured"])
    base_path = config.target_dir.expanduser()

    if config.host_type == "github":
        import git_mirror.manage_github as mgh

        mgr = mgh.GithubRepoManager(
            token, base_path, config.user_name,
            include_private=config.include_private,
            include_forks=config.include_forks,
            host_domain=config.host_url or "https://api.github.com",
            dry_run=dry_run, prompt_for_changes=False,
        )
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
    elif config.host_type == "gitlab":
        import git_mirror.manage_gitlab as mgl

        mgr_gl = mgl.GitlabRepoManager(
            token, base_path, config.user_name,
            include_private=config.include_private,
            include_forks=config.include_forks,
            host_domain=config.host_url or "https://gitlab.com",
            dry_run=dry_run, prompt_for_changes=False,
        )
        repos_gl = mgr_gl._get_user_repos()
        for repo_data_gl in repos_gl:
            name = repo_data_gl.name
            url = repo_data_gl.http_url_to_repo
            dest = base_path / name
            if dest.exists():
                result.messages.append(f"Already exists: {name}")
                continue
            if dry_run:
                result.messages.append(f"Would clone: {url}")
                continue
            try:
                g.Repo.clone_from(url, dest)
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
    if config.host_type != "github":
        return []
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
    """Read token from environment for the given config."""
    if config.host_name == "selfhosted":
        return os.getenv("SELFHOSTED_ACCESS_TOKEN")
    if config.host_type == "github":
        return os.getenv("GITHUB_ACCESS_TOKEN")
    return os.getenv("GITLAB_ACCESS_TOKEN")
