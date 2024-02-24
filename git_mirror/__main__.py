import argparse
import logging
import logging.config
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

import git_mirror.router as router
from git_mirror import logging_config
from git_mirror.__about__ import __description__, __version__
from git_mirror.bug_report import BugReporter
from git_mirror.manage_config import ConfigManager, default_config_path
from git_mirror.menu import get_command_info
from git_mirror.safe_env import load_env
from git_mirror.version_check import display_version_check_message

# Assuming RepoManager and other necessary imports are defined elsewhere

load_env()

LOGGER = logging.getLogger(__name__)


def validate_host_token(args: argparse.Namespace) -> tuple[Optional[str], int]:
    """
    Get token from env or raise a helpful message.

    Args:
        args (argparse.Namespace): The parsed arguments.

    Returns:
        tuple[Optional[str], int]: The token and return value.
    """
    # HACK: This needs to be redone somehow.
    config_manager = ConfigManager(args.config_path)
    invalid_or_missing_host = not args.host or args.host not in ("github", "gitlab", "selfhosted")
    needs_host = args.command not in ("init", "list-config")
    if invalid_or_missing_host and needs_host:
        print(
            "Please specify a host with --host or use gh_mirror for Github, gl_mirror for Gitlab, or sh_mirror for self hosted. "
            "Specify selfhosted in config file with a host_type of github or gitlab."
        )
        return "", 1
    if not needs_host:
        return None, 0
    config_data = config_manager.load_config(args.host)
    # github or self hosted github
    selfhosted_type_is_github = args.host == "selfhosted" and config_data and config_data.host_type == "github"
    selfhosted_type_is_gitlab = args.host == "selfhosted" and config_data and config_data.host_type == "gitlab"
    # SELFHOSTED_ACCESS_TOKEN
    if selfhosted_type_is_github or selfhosted_type_is_gitlab:
        token = os.getenv("SELFHOSTED_ACCESS_TOKEN")
        if not token:
            print("Self hosted access token must be provided through SELFHOSTED_ACCESS_TOKEN environment variable.")
            return "", 1
    elif args.host == "github" or selfhosted_type_is_github:
        token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not token:
            print("GitHub access token must be provided through GITHUB_ACCESS_TOKEN environment variable.")
            return "", 1
    elif args.host == "gitlab" or selfhosted_type_is_gitlab:
        token = os.getenv("GITLAB_ACCESS_TOKEN")
        if not token:
            print("GitLab access token must be provided through GITLAB_ACCESS_TOKEN environment variable.")
            return "", 1
    elif args.command in ("init", "list-config"):
        token = None
    else:
        raise ValueError(f"Invalid host: {args.host}")
    return token, 0


def validate_parse_args(args: argparse.Namespace, first_time_init, use_github) -> tuple[str, int, int]:

    LOGGER.debug(f"Program name {sys.argv[0]}")

    group_id = 0
    domain = ""

    # Attempt to read from config if arguments are not provided
    if (
        (not args.user_name or not args.target_dir)
        and not first_time_init
        and args.command not in ("init", "list-config")
    ):
        config_manager = ConfigManager(args.config_path)
        if not args.host:
            print("Please specify a host, eg. --host github or --host gitlab.")
            return domain, group_id, 1
        config_data = config_manager.load_config(args.host)
        config_path = args.config_path
        if config_data and config_path.exists():
            if not args.user_name:
                args.user_name = config_data.user_name
            if not args.target_dir:
                args.target_dir = config_data.target_dir
            if not args.pypi_owner_name:
                args.pypi_owner_name = config_data.pypi_owner_name
            if not args.include_private:
                args.include_private = config_data.include_private
            if not args.include_forks:
                args.include_forks = config_data.include_forks
            if not use_github and not args.domain:
                domain = config_data.host_url
            if not use_github and not args.group_id:
                group_id = config_data.group_id
            if not args.global_template_dir:
                args.global_template_dir = config_data.global_template_dir
    if (
        (not args.user_name or not args.target_dir)
        and not first_time_init
        and args.command not in ("init", "list-config")
    ):
        print("user-name and target-dir are required if not specified in ~/git_mirror.toml.")
        return domain, group_id, 1
    return domain, group_id, 0


def enable_logging(args):
    # No logging above this line!
    if args.verbose > 0:
        config = logging_config.generate_config(level="DEBUG", logging_level=args.verbose)
        logging.config.dictConfig(config)
    else:
        # Essentially, quiet mode
        logging.basicConfig(level=logging.FATAL)


def main_selfhosted(argv: Optional[Sequence[str]] = None) -> int:
    return main(argv, use_gitlab=False, use_github=False, use_selfhosted=True)


def main_github(argv: Optional[Sequence[str]] = None) -> int:
    return main(argv, use_gitlab=False, use_github=True, use_selfhosted=False)


def main_gitlab(argv: Optional[Sequence[str]] = None) -> int:
    return main(argv, use_gitlab=True, use_github=False, use_selfhosted=False)


def main(
    argv: Optional[Sequence[str]] = None,
    use_gitlab: bool = False,
    use_github: bool = False,
    use_selfhosted: bool = False,
) -> int:
    program = "git_mirror"
    if not (use_github or use_gitlab or use_selfhosted):
        if sys.argv[0].endswith("gl_mirror"):
            use_gitlab = True
            program = "gl_mirror"
        elif sys.argv[0].endswith("gh_mirror"):
            use_github = True
            program = "gh_mirror"
        elif sys.argv[0].endswith("sh_mirror"):
            use_selfhosted = True
            program = "sh_mirror"

    parser = argparse.ArgumentParser(
        prog=program,
        allow_abbrev=False,
        description=__description__,
        epilog=f"""
    Examples:

        # Interactively initialize configuration
        {program} init
        
        # Interactively select command
        {program} menu""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    choices = [
        # UI
        "menu",
        "init",
        # Diagnostics
        "show-account",
        "list-repos",
        # Repo Actions/Report
        "clone-all",
        "pull-all",
        "local-changes",
        "not-repo",
        # Branch commands
        "update-from-main",
        "prune-all",
        # Build
        "build-status",
        # Config
        "sync-config",
        "list-config",
        # Pypi
        "pypi-status",
        # Template/Cross Repo Sync
        "cross-repo-report",
        "cross-repo-sync",
        "cross-repo-init",
    ]
    parser.add_argument("command", choices=choices, help="The command to execute.")
    host_choices = ["gitlab", "github"]
    if use_gitlab:
        host_choices = ["gitlab"]
        host_default = "gitlab"
    elif use_github:
        host_choices = ["github"]
        host_default = "github"
    elif use_selfhosted:
        host_choices = ["selfhosted"]
        host_default = "selfhosted"
    else:
        host_default = None

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit.",
    )

    parser.add_argument("--menu", help="Choose a command via menu.")

    parser.add_argument(
        "--host",
        choices=host_choices,
        default=host_default,
        help="Source host, use gl_mirror or gh_mirror to skip this.",
    )
    parser.add_argument("--user-name", help="The username.")
    if not use_github:
        parser.add_argument("--group-id", help="The gitlab group id.")
        parser.add_argument("--domain", help="The gitlab (compatible) domain.")
    parser.add_argument("--pypi-owner-name", help="Pypi Owner Name.")
    parser.add_argument("--target-dir", type=Path, help="The directory where repositories will be cloned or pulled.")
    parser.add_argument("--include-forks", action="store_true", help="Include forked repositories.")
    parser.add_argument("--include-private", action="store_true", help="Include private repositories.")
    parser.add_argument("--dry-run", action="store_true", help="Don't change anything.")
    parser.add_argument("--config-path", type=Path, default=default_config_path(), help="Path to the TOML config file.")
    parser.add_argument("--global-template-dir", type=Path, help="Templates for syncing files across repos.")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Verbose output, repeat for more verbose")

    # UX - help user who doesn't enter any specific command and is likely just starting out
    first_time_init = False
    if not sys.argv[1:] and not default_config_path().exists():
        print("This appears to be first time setup. Let's initialize configuration.")
        argv = ["init"]
        first_time_init = True

    # TODO: UX - help user who hasn't set a host or token.

    args: argparse.Namespace = parser.parse_args(argv)

    enable_logging(args)

    # Can't run any commands except init without a host and token
    token, return_value = validate_host_token(args)
    if return_value != 0:
        return return_value

    if args.command == "menu":
        get_command_info(args)

    # modify args
    domain, group_id, return_value = validate_parse_args(args, first_time_init, use_github)
    if return_value != 0:
        return return_value

    if os.environ.get("GITHUB_ACCESS_TOKEN") and "PYTEST_CURRENT_TEST" not in os.environ:
        # TODO: make this lazy.
        reporter = BugReporter(os.environ.get("GITHUB_ACCESS_TOKEN", ""), "matthewdeanmartin/git_mirror")
        sys.excepthook = reporter.handle_exception_and_report

    router.route_to_command(
        command=args.command,
        user_name=args.user_name,
        target_dir=args.target_dir,
        token=token or "",
        host=args.host,
        include_private=args.include_private,
        include_forks=args.include_forks,
        config_path=args.config_path,
        pypi_owner_name=args.pypi_owner_name,
        domain=domain,
        group_id=group_id,
        logging_level=args.verbose,
        dry_run=args.dry_run,
        template_dir=args.global_template_dir,
    )
    display_version_check_message()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
