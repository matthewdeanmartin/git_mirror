"""
Sends the cli commands to the right method
"""

import logging
from pathlib import Path
from typing import Optional

import git_mirror.manage_config as mc
import git_mirror.manage_git as mg
import git_mirror.manage_github as mgh
import git_mirror.manage_gitlab as mgl
from git_mirror.check_cli_deps import check_tool_availability
from git_mirror.custom_types import SourceHost
from git_mirror.manage_poetry import PoetryManager
from git_mirror.safe_env import load_env
from git_mirror.ui import console_with_theme

load_env()

# Configure logging
LOGGER = logging.getLogger(__name__)

console = console_with_theme()


def route_simple(
    command: str,
    config_path: Optional[Path] = None,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        config_path (Path): Path to the TOML config file.
    """
    if config_path is None:
        config_path = mc.default_config_path()

    if command == "init":
        config_manager = mc.ConfigManager(config_path=config_path)
        config_manager.initialize_config()
    else:
        console.print(f"Unknown command: {command}")


def route_config(
    command: str,
    config_path: Optional[Path] = None,
    dry_run: bool = False,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        config_path (Path): Path to the TOML config file.
        dry_run (bool): Flag to determine whether the operation should be a dry run.
    """
    if config_path is None:
        config_path = mc.default_config_path()

    if command == "list-config":
        config_manager = mc.ConfigManager(config_path=config_path)
        config_manager.list_config()
        print()
        check_tool_availability()
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
    config_path: Optional[Path] = None,
    domain: Optional[str] = None,
    group_id: Optional[int] = None,
    logging_level: int = 1,
    dry_run: bool = False,
    template_dir: Optional[Path] = None,
    prompt_for_changes: bool = True,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        user_name (str): The GitHub username.
        target_dir (Path): The directory where repositories will be cloned or pulled.
        token (str): The GitHub access token.
        host (str): The source host.
        include_private (bool): Flag to determine whether private repositories should be included.
        include_forks (bool): Flag to determine whether forked repositories should be included.
        config_path (Path): Path to the TOML config file.
        domain (str): The GitLab domain.
        group_id (int): The GitLab group id.
        logging_level (int): The logging level.
        dry_run (bool): Flag to determine whether the operation should be a dry run.
        template_dir (Path): The directory containing the templates to sync.
        prompt_for_changes (bool): Flag to determine whether to prompt for changes.
    """
    if config_path is None:
        config_path = mc.default_config_path()

    if command == "local-changes":
        base_path = Path(target_dir).expanduser()
        git_manager = mg.GitManager(base_path, dry_run, prompt_for_changes=prompt_for_changes)
        git_manager.check_for_uncommitted_or_unpushed_changes()
    elif host in ("github", "gitlab", "selfhosted"):
        if host == "github":
            base_path = Path(target_dir).expanduser()
            manager: SourceHost = mgh.GithubRepoManager(
                token,
                base_path,
                user_name,
                include_private=include_private,
                include_forks=include_forks,
                dry_run=dry_run,
                prompt_for_changes=prompt_for_changes,
            )
        elif host in ("gitlab", "selfhosted"):
            base_path = Path(target_dir).expanduser()
            manager = mgl.GitlabRepoManager(
                token,
                base_path,
                user_name,
                include_private=include_private,
                include_forks=include_forks,
                host_domain=domain or "https://gitlab.com",
                logging_level=logging_level,
                dry_run=dry_run,
                prompt_for_changes=prompt_for_changes,
            )
        else:
            raise ValueError(f"Unknown host: {host}")

        if command == "clone-all" and host in ("gitlab", "selfhosted") and group_id is not None and group_id != 0:
            # TODO: confusion with clone all by user name and by group id.
            # If they are both filled in, then what does the user want?
            # hack until I support cloning by github org or something.
            gl_manager = mgl.GitlabRepoManager(
                token,
                base_path,
                user_name,
                include_private=include_private,
                include_forks=include_forks,
                host_domain=domain or "https://gitlab.com",
                logging_level=logging_level,
                dry_run=dry_run,
                prompt_for_changes=prompt_for_changes,
            )
            gl_manager.clone_group(group_id)
        elif command == "clone-all":
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
        elif command == "cross-repo-report":
            if not template_dir:
                console.print("Template directory is required for cross-repo-report")
                return
            manager.cross_repo_sync_report(template_dir)
        elif command == "cross-repo-sync":
            if not template_dir:
                console.print("Template directory is required for cross-repo-sync")
                return
            manager.cross_repo_sync(template_dir)
        elif command == "cross-repo-init":
            if not template_dir:
                console.print("Template directory is required for cross-repo-init")
                return
            manager.cross_repo_init(template_dir)
        elif command == "poetry-relock":
            git_manager = mg.GitManager(base_path, dry_run, prompt_for_changes=prompt_for_changes)
            poetry_manager = PoetryManager(manager)
            for repo in git_manager.local_repos_with_file_in_root("pyproject.toml"):
                poetry_manager.update_dependencies(
                    main_branch="TODO-lookup",
                    dependency_update_branch="poetry-update",
                    reviewer="TODO-config",
                    project_id=0,  # TODO- config
                    repo_name=repo.name,  # Github only
                    user="TODO-lookup",
                )
        else:
            console.print(f"Unknown command: {command}")
    else:
        console.print(f"Unknown host: {host}")


def route_cross_repo(
    command: str,
    user_name: str,
    target_dir: Path,
    token: str,
    host: str,
    include_private: bool,
    include_forks: bool,
    domain: Optional[str] = None,
    logging_level: int = 1,
    dry_run: bool = False,
    template_dir: Optional[Path] = None,
    prompt_for_changes: bool = True,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        user_name (str): The GitHub username.
        target_dir (Path): The directory where repositories will be cloned or pulled.
        token (str): The GitHub access token.
        host (str): The source host.
        include_private (bool): Flag to determine whether private repositories should be included.
        include_forks (bool): Flag to determine whether forked repositories should be included.
        config_path (Path): Path to the TOML config file.
        domain (str): The GitLab domain.
        group_id (int): The GitLab group id.
        logging_level (int): The logging level.
        dry_run (bool): Flag to determine whether the operation should be a dry run.
        template_dir (Path): The directory containing the templates to sync.
        prompt_for_changes (bool): Flag to determine whether to prompt for changes.
    """
    if host in ("github", "gitlab", "selfhosted"):
        if host == "github":
            base_path = Path(target_dir).expanduser()
            manager: SourceHost = mgh.GithubRepoManager(
                token,
                base_path,
                user_name,
                include_private=include_private,
                include_forks=include_forks,
                dry_run=dry_run,
                prompt_for_changes=prompt_for_changes,
            )
        elif host in ("gitlab", "selfhosted"):
            base_path = Path(target_dir).expanduser()
            manager = mgl.GitlabRepoManager(
                token,
                base_path,
                user_name,
                include_private=include_private,
                include_forks=include_forks,
                host_domain=domain or "https://gitlab.com",
                logging_level=logging_level,
                dry_run=dry_run,
                prompt_for_changes=prompt_for_changes,
            )
        else:
            raise ValueError(f"Unknown host: {host}")

        if not template_dir:
            console.print("Template directory is required for cross-repo-report")
            return

        if command == "cross-repo-report":
            manager.cross_repo_sync_report(template_dir)
        elif command == "cross-repo-sync":
            if not template_dir:
                console.print("Template directory is required for cross-repo-sync")
                return
            manager.cross_repo_sync(template_dir)
        elif command == "cross-repo-init":
            if not template_dir:
                console.print("Template directory is required for cross-repo-init")
                return
            manager.cross_repo_init(template_dir)
        else:
            console.print(f"Unknown command: {command}")
    else:
        console.print(f"Unknown host: {host}")


def route_pypi(
    command: str,
    user_name: str,
    target_dir: Path,
    token: str,
    host: str,
    include_private: bool,
    include_forks: bool,
    pypi_owner_name: Optional[str] = None,
    domain: Optional[str] = None,
    logging_level: int = 1,
    dry_run: bool = False,
):
    """
    Main function to handle clone-all or pull-all operations, with an option to include forks.

    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        user_name (str): The GitHub username.
        target_dir (Path): The directory where repositories will be cloned or pulled.
        token (str): The GitHub access token.
        host (str): The source host.
        include_private (bool): Flag to determine whether private repositories should be included.
        include_forks (bool): Flag to determine whether forked repositories should be included.
        pypi_owner_name (str): The PyPI owner name to filter the results.
        domain (str): The GitLab domain.
        logging_level (int): The logging level.
        dry_run (bool): Flag to determine whether the operation should be a dry run.
    """
    if host in ("github", "gitlab", "selfhosted"):
        if host == "github":
            base_path = Path(target_dir).expanduser()
            manager: SourceHost = mgh.GithubRepoManager(
                token,
                base_path,
                user_name,
                include_private=include_private,
                include_forks=include_forks,
                dry_run=dry_run,
            )
        elif host in ("gitlab", "selfhosted"):
            base_path = Path(target_dir).expanduser()
            manager = mgl.GitlabRepoManager(
                token,
                base_path,
                user_name,
                include_private=include_private,
                include_forks=include_forks,
                host_domain=domain or "https://gitlab.com",
                logging_level=logging_level,
                dry_run=dry_run,
            )
        else:
            raise ValueError(f"Unknown host: {host}")

        if command == "pypi-status":
            manager.check_pypi_publish_status(pypi_owner_name=pypi_owner_name)
        else:
            console.print(f"Unknown command: {command}")
    else:
        console.print(f"Unknown host: {host}")
