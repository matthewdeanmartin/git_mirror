import argparse
import logging
import logging.config
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

import git_mirror.router as router
from git_mirror import logging_config
from git_mirror.__about__ import __description__, __version__
from git_mirror.manage_config import ConfigManager, default_config_path

# Assuming RepoManager and other necessary imports are defined elsewhere

load_dotenv()  # Load environment variables from .env file if present

LOGGER = logging.getLogger(__name__)


def main_github(argv: Optional[Sequence[str]] = None) -> int:
    return main(argv, use_gitlab=False, use_github=True)


def main_gitlab(argv: Optional[Sequence[str]] = None) -> int:
    return main(argv, use_gitlab=True, use_github=False)


def main(argv: Optional[Sequence[str]] = None, use_gitlab: bool = False, use_github: bool = False) -> int:
    program = "git_mirror"
    if not (use_github or use_gitlab):
        if sys.argv[0].endswith("gl_mirror"):
            use_gitlab = True
            program = "gl_mirror"
        elif sys.argv[0].endswith("gh_mirror"):
            use_github = True
            program = "gh_mirror"

    parser = argparse.ArgumentParser(
        prog=program,
        allow_abbrev=False,
        description=__description__,
        epilog=f"""
    Examples:

        # Clone everything
        {program} clone-all
        
        # Generate config for snapshots
        {program} pull-all""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    choices = [
        "init",
        "show-account",
        "list-repos",
        "clone-all",
        "pull-all",
        "local-changes",
        "not-repo",
        "build-status",
        "sync-config",
        "list-config",
        "pypi-status",
    ]
    parser.add_argument("command", choices=choices, help="The command to execute.")
    host_choices = ["gitlab", "github"]
    if use_gitlab:
        host_choices = ["gitlab"]
        host_default = "gitlab"
    elif use_github:
        host_choices = ["github"]
        host_default = "github"
    else:
        host_default = None

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program's version number and exit.",
    )

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
    parser.add_argument("--config-path", type=Path, default=default_config_path(), help="Path to the TOML config file.")
    parser.add_argument("--verbose", action="store_true", help="verbose output")

    first_time_init = False
    if not sys.argv[1:] and not default_config_path().exists():
        print("This appears to be first time setup. Let's initialize configuration.")
        argv = ["init"]
        first_time_init = True

    args: argparse.Namespace = parser.parse_args(argv)

    # No logging above this line!
    if args.verbose:
        config = logging_config.generate_config(level="DEBUG")
        logging.config.dictConfig(config)
    else:
        # Essentially, quiet mode
        logging.basicConfig(level=logging.FATAL)

    LOGGER.debug(f"Program name {sys.argv[0]}")

    if args.host == "github":
        token = os.getenv("GITHUB_ACCESS_TOKEN")
        if not token:
            print("GitHub access token must be provided through GITHUB_ACCESS_TOKEN environment variable.")
            sys.exit(1)
    elif args.host == "gitlab":
        token = os.getenv("GITLAB_ACCESS_TOKEN")
        if not token:
            print("GitLab access token must be provided through GITLAB_ACCESS_TOKEN environment variable.")
            sys.exit(1)
    elif args.command in ("init", "list-config"):
        token = None
    else:
        print("Please specify a host.")
        sys.exit(1)

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
            return 1
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
                print(f"Using domain from config: {domain}")
            if not use_github and not args.group_id:
                group_id = config_data.group_id
                print(f"Using group id from config: {args.group_id}")

    if (
        (not args.user_name or not args.target_dir)
        and not first_time_init
        and args.command not in ("init", "list-config")
    ):
        print("user-name and target-dir are required if not specified in ~/git_mirror.toml.")
        return 1

    router.main_github(
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
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
