"""
Sends the cli commands to the right method
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

CONSOLE = None


def get_console():
    global CONSOLE
    if CONSOLE is None:
        from git_mirror.utils.ui import console_with_theme

        CONSOLE = console_with_theme()
    return CONSOLE


def render_dashboard(rows) -> None:
    """Render the fleet status dashboard as a single Rich table."""
    from rich.table import Table

    from git_mirror import core
    from git_mirror.utils.ui import rich_markup as _rich

    console = get_console()
    if not rows:
        console.print("No repositories found in the target directory.")
        return

    table = Table(title="Repository Status", show_lines=False)
    table.add_column("Repo", no_wrap=True)
    table.add_column("Branch", no_wrap=True)
    table.add_column("State")
    table.add_column("Ahead", justify="right")
    table.add_column("Behind", justify="right")
    table.add_column("Last commit", justify="right")
    table.add_column("Build")

    attention = 0
    for row in rows:
        if row.needs_attention:
            attention += 1

        state_tag, state_label = core.dashboard_state(row)
        state = _rich(state_tag, state_label)

        ahead = f"[yellow]{row.ahead}[/yellow]" if row.ahead else "0"
        behind = f"[yellow]{row.behind}[/yellow]" if row.behind else "0"
        age = "-" if row.last_commit_age_days is None else f"{row.last_commit_age_days}d"

        if row.build:
            build_tag, build_label = core.build_state(row.build)
            build = _rich(build_tag, build_label)
        else:
            build = "-"

        table.add_row(row.name, row.branch or "-", state, ahead, behind, age, build)

    console.print(table)
    console.print(f"{attention} of {len(rows)} repositories need attention.")


def route_simple(
    command: str,
    config_path: Path | None = None,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        config_path (Path): Path to the TOML config file.
    """
    from git_mirror import manage_config as mc

    console = get_console()
    if config_path is None:
        config_path = mc.default_config_path()

    if command == "init":
        config_manager = mc.ConfigManager(config_path=config_path)
        config_manager.initialize_config()
    else:
        console.print(f"Unknown command: {command}")


def route_config(
    command: str,
    config_path: Path | None = None,
    host: str | None = None,
    dry_run: bool = False,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        config_path (Path): Path to the TOML config file.
        host (str | None): Optional host to inspect.
        dry_run (bool): Flag to determine whether the operation should be a dry run.
    """
    from git_mirror import manage_config as mc

    console = get_console()
    if config_path is None:
        config_path = mc.default_config_path()

    if command == "list-config":
        from git_mirror.utils.check_cli_deps import check_tool_availability

        config_manager = mc.ConfigManager(config_path=config_path)
        config_manager.list_config()
        print()
        check_tool_availability()
    elif command == "doctor":
        config_manager = mc.ConfigManager(config_path=config_path)
        config_manager.doctor(host=host)
    else:
        console.print(f"Unknown command: {command}")


def route_repos(
    command: str,
    user_name: str,
    target_dir: Path,
    token: str,
    host: str,
    include_private: bool,
    include_forks: bool,
    config_path: Path | None = None,
    domain: str | None = None,
    logging_level: int = 1,
    dry_run: bool = False,
    template_dir: Path | None = None,
    prompt_for_changes: bool = True,
    only: list[str] | None = None,
    tags: list[str] | None = None,
    exclude: list[str] | None = None,
    include_ignored: bool = False,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        user_name (str): The GitHub username.
        target_dir (Path): The directory where repositories will be cloned or pulled.
        token (str): The GitHub access token.
        host (str): The source host (github or selfhosted GitHub Enterprise).
        include_private (bool): Flag to determine whether private repositories should be included.
        include_forks (bool): Flag to determine whether forked repositories should be included.
        config_path (Path): Path to the TOML config file.
        domain (str): The GitHub Enterprise API base URL.
        logging_level (int): The logging level.
        dry_run (bool): Flag to determine whether the operation should be a dry run.
        template_dir (Path): The directory containing the templates to sync.
        prompt_for_changes (bool): Flag to determine whether to prompt for changes.
        only (list[str]): Act only on these repo names.
        tags (list[str]): Act only on repos carrying any of these tags.
        exclude (list[str]): Skip these repo names.
        include_ignored (bool): Include repos marked ignore = true in config.
    """
    from git_mirror import core
    from git_mirror import manage_config as mc

    console = get_console()
    if config_path is None:
        config_path = mc.default_config_path()

    selection = core.build_selection(
        host,
        config_path=config_path,
        only=only,
        tags=tags,
        exclude=exclude,
        include_ignored=include_ignored,
    )

    if command == "status":
        config_manager = mc.ConfigManager(config_path=config_path)
        config_data = config_manager.load_config(host) if host else None
        base_path = Path(target_dir).expanduser()
        rows = core.repo_dashboard(
            base_path,
            selection=selection,
            token=token or None,
            config=config_data,
        )
        render_dashboard(rows)
    elif command == "local-changes":
        from git_mirror import manage_git as mg

        base_path = Path(target_dir).expanduser()
        git_manager = mg.GitManager(
            base_path, dry_run, prompt_for_changes=prompt_for_changes, selection=selection
        )
        git_manager.check_for_uncommitted_or_unpushed_changes()
    elif host in ("github", "selfhosted"):
        resolved_domain = domain
        if host == "selfhosted":
            config_manager = mc.ConfigManager(config_path=config_path)
            config_data = config_manager.load_config("selfhosted")
            if not config_data:
                console.print("No self-hosted configuration found. Run `git_mirror init` first.")
                return
            resolved_domain = resolved_domain or config_data.host_url

        manager: Any = core.build_manager(
            token,
            target_dir,
            user_name,
            include_private=include_private,
            include_forks=include_forks,
            host_domain=resolved_domain,
            dry_run=dry_run,
            prompt_for_changes=prompt_for_changes,
            selection=selection,
        )

        if command == "clone-all":
            manager.clone_all()
        elif command == "pull-all":
            manager.pull_all()
        elif command == "not-repo":
            manager.not_repo()
        elif command == "build-status":
            manager.list_repo_builds()
        elif command == "list-repos":
            manager.list_repos()
        elif command == "update-from-main":
            manager.update_all_branches()
        elif command == "prune-all":
            manager.prune_all()
        elif command == "show-account":
            manager.print_user_summary()
        elif command == "sync-config":
            config_manager = mc.ConfigManager(config_path=config_path)
            config_manager.load_and_sync_config(host, manager.list_repo_names())
        else:
            console.print(f"Unknown command: {command}")
    else:
        console.print(f"Unknown host: {host}")
