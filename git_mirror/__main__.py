# import git_mirror.hack.forwarding as argparse
import argparse
import logging
import logging.config
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

import requests_cache

import git_mirror.pat_init as pat_init
import git_mirror.pat_init_gitlab as pat_init_gitlab
import git_mirror.router as router
from git_mirror import logging_config
from git_mirror.__about__ import __description__, __version__
from git_mirror.bug_report import BugReporter
from git_mirror.manage_config import ConfigManager, default_config_path
from git_mirror.menu import ask_for_host, get_command_info
from git_mirror.safe_env import load_env
from git_mirror.ui import console_with_theme
from git_mirror.version_check import display_version_check_message

# Assuming RepoManager and other necessary imports are defined elsewhere

load_env()

LOGGER = logging.getLogger(__name__)

backend = requests_cache.SQLiteCache(use_cache_dir=True, fast_save=True)

requests_cache.install_cache("git_mirror_cache", backend=backend, expire_after=300)

console = console_with_theme()


def validate_host_token(args: argparse.Namespace) -> tuple[Optional[str], int]:
    """
    Get token from env or raise a helpful message.

    Args:
        args (argparse.Namespace): The parsed arguments.

    Returns:
        tuple[Optional[str], int]: The token and return value.
    """
    host = args.host if hasattr(args, "host") else None
    config_path = args.config_path if hasattr(args, "config_path") else default_config_path()
    # HACK: This needs to be redone somehow.
    config_manager = ConfigManager(config_path)
    invalid_or_missing_host = not host or host not in ("github", "gitlab", "selfhosted")
    needs_host = args.command not in ("init", "list-config")
    if invalid_or_missing_host and needs_host:
        host = ask_for_host(config_manager)
        if not host:
            config_manager.initialize_config()
            # console.print(
            #     "Please specify a host with --host or use gh_mirror for Github, gl_mirror for Gitlab, or sh_mirror for self hosted. "
            #     "Specify selfhosted in config file with a host_type of github or gitlab."
            # )
            return "", 1
        args.host = host
    if not needs_host:
        return None, 0
    config_data = config_manager.load_config(args.host)
    # github or self hosted github
    selfhosted_type_is_github = args.host == "selfhosted" and config_data and config_data.host_type == "github"
    selfhosted_type_is_gitlab = args.host == "selfhosted" and config_data and config_data.host_type == "gitlab"
    # SELFHOSTED_ACCESS_TOKEN
    if selfhosted_type_is_github or selfhosted_type_is_gitlab:
        token = os.getenv("SELFHOSTED_ACCESS_TOKEN")
        if selfhosted_type_is_github and not token:
            console.print("Self hosted Github access token is missing. Setup and re-run command.")
            pat_init.setup_github_pat()
            return "", 1
        if selfhosted_type_is_gitlab and not token:
            console.print(
                "Self hosted GitLab access token must be provided through SELFHOSTED_ACCESS_TOKEN environment variable."
            )
            pat_init_gitlab.setup_gitlab_pat()
            return "", 1
    elif args.host == "github" or selfhosted_type_is_github:
        token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not token:
            console.print("Github access token is missing. Setup and re-run command.")
            pat_init.setup_github_pat()
            return "", 1
    elif args.host == "gitlab" or selfhosted_type_is_gitlab:
        token = os.getenv("GITLAB_ACCESS_TOKEN")
        if not token:
            console.print("GitLab access token must be provided through GITLAB_ACCESS_TOKEN environment variable.")
            pat_init_gitlab.setup_gitlab_pat()
            return "", 1
    elif args.command in ("init", "list-config"):
        token = None
    else:
        raise ValueError(f"Invalid host: {args.host}")
    return token, 0


def validate_parse_args(args: argparse.Namespace) -> tuple[str, int, int]:

    LOGGER.debug(f"Program name {sys.argv[0]}")

    group_id = 0
    domain = ""

    # Attempt to read from config if arguments are not provided
    if (
        (not args.user_name or not args.target_dir)
        and not args.first_time_init
        and args.command not in ("init", "list-config")
    ):
        config_manager = ConfigManager(args.config_path)
        if not args.host:
            console.print("Please specify a host, eg. --host github or --host gitlab.")
            return domain, group_id, 1
        config_data = config_manager.load_config(args.host)
        config_path = args.config_path
        if config_data and config_path.exists():
            if not args.user_name:
                args.user_name = config_data.user_name
            if not args.target_dir:
                args.target_dir = config_data.target_dir
            if hasattr(args, "pypi_owner_name") and not args.pypi_owner_name:
                args.pypi_owner_name = config_data.pypi_owner_name
            if not args.include_private:
                args.include_private = config_data.include_private
            if not args.include_forks:
                args.include_forks = config_data.include_forks
            if not args.use_github and not args.domain:
                domain = config_data.host_url
            if not args.use_github and not args.group_id:
                group_id = config_data.group_id
            if hasattr(args, "global_template_dir") and not args.global_template_dir:
                args.global_template_dir = config_data.global_template_dir
    if (
        (not args.user_name or not args.target_dir)
        and not args.first_time_init
        and args.command not in ("init", "list-config")
    ):
        console.print("user-name and target-dir are required if not specified in ~/git_mirror.toml.")
        return domain, group_id, 1
    return domain, group_id, 0


def enable_logging(args):
    # No logging above this line!
    if hasattr(args, "verbose") and args.verbose > 0:
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


def handle_repos(args: argparse.Namespace) -> None:
    token, return_value = validate_host_token(args)
    # modify args
    domain, group_id, return_value = validate_parse_args(args)
    if return_value != 0:
        sys.exit(return_value)
    router.route_repos(
        command=args.command,
        user_name=args.user_name,
        target_dir=args.target_dir,
        token=token or "",
        host=args.host,
        include_private=args.include_private,
        include_forks=args.include_forks,
        config_path=args.config_path,
        domain=domain,
        group_id=group_id,
        logging_level=args.verbose,
        dry_run=args.dry_run,
        prompt_for_changes=not args.yes,
    )


def handle_config(args: argparse.Namespace) -> None:
    router.route_config(
        command=args.command,
        config_path=args.config_path,
        dry_run=args.dry_run,
    )


def handle_pypi(args: argparse.Namespace) -> None:
    token, return_value = validate_host_token(args)
    # modify args
    domain, group_id, return_value = validate_parse_args(args)
    if return_value != 0:
        sys.exit(return_value)
    router.route_pypi(
        command=args.command,
        user_name=args.user_name,
        target_dir=args.target_dir,
        token=token or "",
        host=args.host,
        include_private=args.include_private,
        include_forks=args.include_forks,
        domain=domain,
        logging_level=args.verbose,
        dry_run=args.dry_run,
    )


def handle_cross_repo_sync(args: argparse.Namespace) -> None:
    token, return_value = validate_host_token(args)
    # modify args
    domain, group_id, return_value = validate_parse_args(args)
    if return_value != 0:
        sys.exit(return_value)
    router.route_cross_repo(
        command=args.command,
        user_name=args.user_name,
        target_dir=args.target_dir,
        token=token or "",
        host=args.host,
        include_private=args.include_private,
        include_forks=args.include_forks,
        domain=domain,
        logging_level=args.verbose,
        dry_run=args.dry_run,
        template_dir=args.global_template_dir,
        prompt_for_changes=not args.yes,
    )


def handle_simple(args: argparse.Namespace) -> None:
    router.route_simple(
        command=args.command,
        config_path=args.config_path,
    )


def pypi_specific_args(parser):
    parser.add_argument("--pypi-owner-name", help="Pypi Owner Name.")


def config_specific_args(parser):
    pass
    # config path is global
    # parser.add_argument("--config-path", type=Path, default=default_config_path(), help="Path to the TOML config file.")


def cross_repo_specific_args(parser):
    parser.add_argument("--global-template-dir", type=Path, help="Templates for syncing files across repos.")


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
    # parser.add_argument("command", choices=choices, help="The command to execute.")

    # start global args
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit.",
    )

    # this has to be here. This is how we intercept the command before main argparsing happens.
    parser.add_argument("--menu", help="Choose a command via menu.")

    subparsers = parser.add_subparsers(help="Subcommands.", dest="command")

    repos_commands = {
        # Account
        "show-account": "Show source code host user account information.",
        # Repos
        "list-repos": "List repositories.",
        "clone-all": "Clone all repositories.",
        "pull-all": "Pull all repositories.",
        "local-changes": "List local changes.",
        "not-repo": "List directories that are not repositories.",
        # Branch commands
        "update-from-main": "Update from main branch.",
        "prune-all": "Prune all repositories not found remotely.",
        # config
        "sync-config": "Sync configuration with source code host.",
        # CI
        "build-status": "Show build status.",
    }

    for command, help_text in repos_commands.items():
        # Repos command
        repos_parser = subparsers.add_parser(command, help=help_text)
        # repos specific args
        host_specific_args(repos_parser, use_github, use_gitlab, use_selfhosted)
        global_args(repos_parser)
        # router to handler
        repos_parser.set_defaults(func=handle_repos)

    config_commands = {
        "list-config": "List configuration.",
    }

    for command, help_text in config_commands.items():
        # Repos command
        config_parser = subparsers.add_parser(command, help=help_text)
        # repos specific args
        config_specific_args(config_parser)
        global_args(config_parser)
        # router to handler
        config_parser.set_defaults(func=handle_config)

    pypi_commands = {
        "pypi-status": "Show pypi deployment status.",
    }

    for command, help_text in pypi_commands.items():
        pypi_parser = subparsers.add_parser(command, help=help_text)
        # specific args
        host_specific_args(pypi_parser, use_github, use_gitlab, use_selfhosted)
        pypi_specific_args(pypi_parser)
        global_args(pypi_parser)
        # router to handler
        pypi_parser.set_defaults(func=handle_pypi)

    template_commands = {
        "cross-repo-report": "Show cross repo sync report.",
        "cross-repo-sync": "Sync files across repos.",
        "cross-repo-init": "Initialize cross repo sync.",
    }

    for command, help_text in template_commands.items():
        template_parser = subparsers.add_parser(command, help=help_text)
        # specific args
        host_specific_args(template_parser, use_github, use_gitlab, use_selfhosted)
        cross_repo_specific_args(template_parser)
        global_args(template_parser)
        # router to handler
        template_parser.set_defaults(func=handle_cross_repo_sync)

    simple_commands = {
        "menu": "Show menu.",
        "init": "Initialize configuration.",
    }

    for command, help_text in simple_commands.items():
        simple_parser = subparsers.add_parser(command, help=help_text)
        global_args(simple_parser)
        # router to handler
        if command != "menu":
            simple_parser.set_defaults(func=handle_simple)

    # TODO: UX - help user who hasn't set a host or token.

    args: argparse.Namespace = parser.parse_args(argv)
    if args.command == "menu":
        selection = get_command_info(args)
        if selection:
            if sys.argv:
                original_arv = list(sys.argv)
            elif argv:
                original_arv = list(argv)
            else:
                original_arv = []
            new_command = [selection] + original_arv[2:]
            args = parser.parse_args(new_command)

    args.use_github = use_github
    # UX - help user who doesn't enter any specific command and is likely just starting out
    args.first_time_init = False
    if not sys.argv[1:] and not default_config_path().exists():
        console.print("This appears to be first time setup. Let's initialize configuration.")
        argv = ["init"]
        args.first_time_init = True

    enable_logging(args)
    LOGGER.debug(f"Cache store at {backend.db_path}")

    if use_github:
        args.host = "github"
    elif use_gitlab:
        args.host = "gitlab"
    elif use_selfhosted:
        args.host = "selfhosted"
    # Can't run any commands except init without a host and token
    token, return_value = validate_host_token(args)
    if return_value != 0:
        return return_value

    if os.environ.get("GITHUB_ACCESS_TOKEN") and "PYTEST_CURRENT_TEST" not in os.environ:
        reporter = BugReporter(os.environ.get("GITHUB_ACCESS_TOKEN", ""), "matthewdeanmartin/git_mirror")
        reporter.register_global_handler()

    if hasattr(args, "func"):
        args.func(args)

    # this happens if no command or after any command finishes
    display_version_check_message()
    return 0


def global_args(parser):
    parser.add_argument(
        "--config-path",
        type=Path,
        default=default_config_path(),
        # shared=True,
        action="store",
        help="Path to the TOML config file.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose output, repeat for more verbose",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't change anything.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Don't prompt before slow actions or writes.",
    )


def host_specific_args(parser: argparse.ArgumentParser, use_github: bool, use_gitlab: bool, use_selfhosted: bool):
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
        "--host",
        choices=host_choices,
        default=host_default,
        help="Source host, use gl_mirror or gh_mirror to skip this.",
    )
    parser.add_argument("--user-name", help="The username.")
    if not use_github:
        parser.add_argument("--group-id", help="The gitlab group id.")
        parser.add_argument("--domain", help="The gitlab (compatible) domain.")
    parser.add_argument("--target-dir", type=Path, help="The directory where repositories will be cloned or pulled.")
    parser.add_argument("--include-forks", action="store_true", help="Include forked repositories.")
    parser.add_argument("--include-private", action="store_true", help="Include private repositories.")


if __name__ == "__main__":
    # sys.exit(main(["list-repos","--host=selfhosted","--verbose"], use_selfhosted=True))
    sys.exit(main(sys.argv[1:]))
