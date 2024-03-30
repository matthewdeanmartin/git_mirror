System: You are an excellent python pytest unit test engineer. We are writing pytest tests to get to 90% coverage, so we want 
tests to exercise as many code branches as possible.

First, begin by looking for bugs. There might not be any bugs. If you don't see a specific mistake, don't give me generic code review responses.

Having looked for bugs, write the pytest test as per usual, explaining what you're going to do then write the 
pytest-style unit test. Don't forget to write code!

## Tooling
Use pytest style testing. Use unittest.mock for mocking. pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.

Do not, under any circumstances, use unittest.TestCase.

The target python version is 3.10

## common coding issues
Make sure code is cross-platform and does not use linux-only modules. Prefer pathlib.Path whenever possible. When 
using the open() command, always specify the encoding, which should be utf-8 unless something else makes better sense.

## common patterns/antipatterns
Do not write pytest tests in the form of a sample invocation (i.e. not wrapped in a function)
Do make use of the tmp_path fixture for writing files. Do not mock `open` to avoid writing files.

## Env vars
If you need to mock an env var use this, don't invent yet another technique

```
from tests.env_util import temporary_env_var

with temporary_env_var("NAME", "mock_value", "NAME2", "mock_value2"):
	assert os.environ["NAME"] == "mock_value"
	assert os.environ["NAME2"] == "mock_value2"
```

Library is named git_mirror.
User: 
Source Path: E:\github\git_mirror\git_mirror\__main__.py

Source Path: E:\github\git_mirror\git_mirror\__main__.py
Module Name: git_mirror.__main__
```python
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
from git_mirror.menu import get_command_info, ask_for_host
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


```

Here are function and method signatures of the dependencies

```python
#git_mirror/bug_report.py

class BugReporter:
    def __init__(self, token: str, repository_name: str)->None:
        """Initializes the bug reporter with the GitHub API token and repository name.
    
        Args:
            token (str): The GitHub API token.
            repository_name (str): The full name of the repository (e.g., "user/repo")."""
        ...
    def mask_secrets(self, text: str)->str:
        """Masks any secrets in the given text with asterisks.
    
        Args:
            text (str): The text to mask.
    
        Returns:
            str: The masked text."""
        ...
    def report_issue(self, issue_title: str, issue_body: str)->Optional[Issue]:
        """Creates an issue in the specified GitHub repository.
    
        Args:
            issue_title (str): The title of the issue to be created.
            issue_body (str): The body text of the issue, providing details."""
        ...
    def find_existing_issue_by_title_and_creator(self, title: str)->Optional[Issue]:
        """Searches for an existing issue by title and the issue creator.
    
        Args:
            title (str): The title of the issue to search for.
    
        Returns:
            Optional[Issue]: The found issue if any; otherwise, None."""
        ...
    def handle_exception_and_report(self, exc_type, exc_value, exc_traceback)->None:
        """Captures the current exception, checks for existing reports, asks the user for permission
        to report it as a bug, and creates an issue on GitHub if permission is granted and no
        existing report is found."""
        ...
    def register_global_handler(self)->None:
        """Registers the global exception handler to capture unhandled exceptions and report them as bugs."""
        ...
```

```python
#git_mirror/manage_config.py
def default_config_path()->Path:
    """This is only for defaults, if provided by user, let it throw."""
    ...
def read_config(config_path: Path, key: str)->Optional[str]:
    """Reads a specific key from the TOML configuration file.
    
    Args:
        config_path (Path): Path to the TOML config file.
        key (str): Key to read from the config.
    
    Returns:
        Optional[str]: The value for the specified key if found, else None."""
    ...
def ask_for_section(already_configured: list[str])->Optional[ConfigData]:
    ...
def display_config(config: ConfigData):
    """Displays the configuration data beautifully using Rich.
    
    Args:
        config (ConfigData): The configuration data to display."""
    ...
def already(gm)->list[str]:
    ...

class ConfigData:
class ConfigManager:
    def __init__(self, config_path: Optional[Path]=None):
        ...
    def load_config_objects(self)->dict[str, ConfigData]:
        ...
    def list_config(self)->None:
        ...
    def initialize_config(self)->list[str]:
        ...
    def load_config(self, host: str)->Optional[ConfigData]:
        """Loads the configuration for the specified host from the TOML file.
        Args:
            host (str): The host name (github, gitlab, selfhosted).
    
        Returns:
            Optional[ConfigData]: The configuration data if found, else None."""
        ...
    def _write_repos_to_toml(self, repos: list[str], existing_config: dict[str, Any])->None:
        """Writes GitHub repository names to a TOML config file with specified attributes.
    
        Args:
            repos (List[str]): List of repository names.
            existing_config (Dict[str, Any]): Existing configuration to merge with."""
        ...
    def load_and_sync_config(self, host: str, repos: list[str])->dict[str, Any]:
        """Loads the TOML configuration, syncs it with the current list of GitHub repositories,
        and updates the TOML file.
    
        Returns:
            dict[str, Any]: The updated configuration."""
        ...
    def load_if_exists(self)->tuple[TOMLDocument, dict[str, Any]]:
        ...
```

```python
#git_mirror/menu.py
def get_command_info(args: argparse.Namespace)->Optional[str]:
    ...
def handle_control_c(answer: Any)->None:
    """Handle control-C exit.
    
    Args:
        answer (Any): The answer from the user."""
    ...
def ask_for_host(config_manager: ConfigManager)->str:
    """Main function to run the UI that queries configuration statuses and asks the user for further actions."""
    ...

class CommandInfo:
```

```python
#git_mirror/pat_init.py
def check_pat_validity(token: str)->bool:
    """Check if the GitHub Personal Access Token (PAT) is still valid.
    
    Args:
        token (str): The GitHub Personal Access Token.
    
    Returns:
        bool: True if the token is valid, False otherwise."""
    ...
def setup_github_pat()->None:
    """Setup the GitHub Personal Access Token (PAT) either globally or locally.
    Checks if it exists and is valid, then asks the user for their preference
    on storing the PAT."""
    ...

```

```python
#git_mirror/pat_init_gitlab.py
def check_pat_validity(token: str)->bool:
    """Check if the GitLab Personal Access Token (PAT) is still valid.
    
    Args:
        token (str): The GitLab Personal Access Token.
    
    Returns:
        bool: True if the token is valid, False otherwise."""
    ...
def setup_gitlab_pat()->None:
    """Setup the GitLab Personal Access Token (PAT) either globally or locally.
    Checks if it exists and is valid, then asks the user for their preference
    on storing the PAT."""
    ...

```

```python
#git_mirror/router.py
def route_simple(command: str, config_path: Optional[Path]=None):
    """Main function to handle clone-all or pull-all operations, with an option to include forks.
    
    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        config_path (Path): Path to the TOML config file."""
    ...
def route_config(command: str, config_path: Optional[Path]=None, dry_run: bool=False):
    """Main function to handle clone-all or pull-all operations, with an option to include forks.
    
    Args:
        command (str): The command to execute ('clone-all' or 'pull-all').
        config_path (Path): Path to the TOML config file.
        dry_run (bool): Flag to determine whether the operation should be a dry run."""
    ...
def route_repos(command: str, user_name: str, target_dir: Path, token: str, host: str, include_private: bool, include_forks: bool, config_path: Optional[Path]=None, domain: Optional[str]=None, group_id: Optional[int]=None, logging_level: int=1, dry_run: bool=False, template_dir: Optional[Path]=None, prompt_for_changes: bool=True):
    """Main function to handle clone-all or pull-all operations, with an option to include forks.
    
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
        prompt_for_changes (bool): Flag to determine whether to prompt for changes."""
    ...
def route_cross_repo(command: str, user_name: str, target_dir: Path, token: str, host: str, include_private: bool, include_forks: bool, domain: Optional[str]=None, logging_level: int=1, dry_run: bool=False, template_dir: Optional[Path]=None, prompt_for_changes: bool=True):
    """Main function to handle clone-all or pull-all operations, with an option to include forks.
    
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
        prompt_for_changes (bool): Flag to determine whether to prompt for changes."""
    ...
def route_pypi(command: str, user_name: str, target_dir: Path, token: str, host: str, include_private: bool, include_forks: bool, pypi_owner_name: Optional[str]=None, domain: Optional[str]=None, logging_level: int=1, dry_run: bool=False):
    """Main function to handle clone-all or pull-all operations, with an option to include forks.
    
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
        dry_run (bool): Flag to determine whether the operation should be a dry run."""
    ...

```

```python
#git_mirror/safe_env.py
def load_env()->None:
    ...
def env_info()->None:
    ...

```

```python
#git_mirror/ui.py
def console_with_theme()->Console:
    """Factory to allow for app theming."""
    ...

```

```python
#git_mirror/version_check.py
def call_pypi_with_version_check(package_name: str, current_version: str)->tuple[bool, Version]:
    """Synchronously checks if the latest version of the package on PyPI is greater than the current version.
    
    Args:
        package_name (str): The name of the package to check.
        current_version (str): The current version of the package.
    
    Returns:
        bool: True if the latest version on PyPI is greater than the current version, False otherwise."""
    ...
def display_version_check_message()->None:
    ...

```
Please write some unit tests for E:\github\git_mirror\git_mirror\__main__.py. If you can't think of anymore unit tests, write "No more unit tests".
Assistant: I'll start by reviewing the code in `__main__.py` for any potential bugs or improvements before writing pytest unit tests.

1. `validate_host_token` function seems to have a potential bug related to the self-hosted type for GitLab. If `args.host` is `"selfhosted"` and `config_data` is None, then `selfhosted_type_is_github` and `selfhosted_type_is_gitlab` will be incorrectly set to `True`, causing issues in the subsequent logic.

2. The `main` function has a potential bug in the logic to determine the `program` based on the input argument values of `use_gitlab`, `use_github`, and `use_selfhosted`. The fallback logic to determine the `program` using `sys.argv[0]` may lead to unexpected behavior if the conditions for `use_gitlab`, `use_github`, and `use_selfhosted` are not met.

3. In the `main` function, the `select` command input could be improved by checking if the user input is in the available choices before parsing it to avoid unexpected behavior.

Now, I'll proceed to write pytest unit tests for `__main__.py`.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: Let's start by writing a pytest unit test to cover the `validate_host_token` function in `__main__.py`. We will mock necessary dependencies and test the different branches of logic based on the input arguments.

```python
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from git_mirror.__main__ import validate_host_token


def test_validate_host_token():
    with patch('git_mirror.__main__.ConfigManager') as mock_config_manager:
        mock_args = MagicMock()
        mock_args.host = "selfhosted"
        mock_args.command = "some_command"  # Not 'init' or 'list-config'
        
        # Case 1: host is "selfhosted", config_data is None
        mock_config_manager.return_value.load_config.return_value = None
        with patch('git_mirror.__main__.ask_for_host') as mock_ask_for_host:
            mock_ask_for_host.return_value = "github"
            token, return_value = validate_host_token(mock_args)
            assert token == ""
            assert return_value == 1

        # Case 2: host is "selfhosted", config_data is present for github
        mock_config_manager.return_value.load_config.return_value = {'host_type': 'github'}
        with patch('git_mirror.__main__.os.getenv') as mock_getenv, \
             patch('git_mirror.__main__.pat_init.setup_github_pat') as mock_setup_github_pat:
            mock_getenv.return_value = None
            token, return_value = validate_host_token(mock_args)
            assert token == ""
            assert return_value == 1
            mock_setup_github_pat.assert_called_once()

        # Case 3: host is "github"
        mock_args.host = "github"
        with patch('git_mirror.__main__.os.getenv') as mock_getenv, \
             patch('git_mirror.__main__.pat_init.setup_github_pat') as mock_setup_github_pat:
            mock_getenv.return_value = "mock_token"
            token, return_value = validate_host_token(mock_args)
            assert token == "mock_token"
            assert return_value == 0
            mock_setup_github_pat.assert_not_called()


if __name__ == "__main__":
    pytest.main()
```

This test mocks the dependencies and covers different scenarios for the `validate_host_token` function. We are testing the logic when the host is "selfhosted" and "github", as well as handling scenarios where config data is not present or tokens need to be setup.

Next unit test, or "No more unit tests"?
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: Next, I will write a pytest unit test to cover the `validate_parse_args` function in `__main__.py`. This test will focus on verifying the behavior of the function when arguments are not provided, and it needs to read from the config file.

```python
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from git_mirror.__main__ import validate_parse_args


def test_validate_parse_args(tmp_path):
    config_path = tmp_path / "test_config.toml"
    mock_args = MagicMock()
    mock_args.user_name = None
    mock_args.target_dir = None
    mock_args.first_time_init = False
    mock_args.command = "some_command"  # Not 'init' or 'list-config'

    # Case 1: Arguments not provided and config data exists
    with patch('git_mirror.__main__.ConfigManager') as mock_config_manager:
        mock_config_manager.return_value.load_config.return_value = {
            'user_name': 'test_user',
            'target_dir': Path('/test/directory'),
            'pypi_owner_name': 'owner',
            'include_private': True,
            'include_forks': False,
            'host_url': 'some_url',
            'group_id': 123,
            'global_template_dir': Path('/template/directory')
        }
        mock_args.config_path = config_path
        with patch('git_mirror.__main__.console.print'):
            domain, group_id, return_value = validate_parse_args(mock_args)
            assert domain == 'some_url'
            assert group_id == 123
            assert return_value == 0

    # Case 2: Arguments not provided and config data does not exist
    with patch('git_mirror.__main__.ConfigManager') as mock_config_manager:
        mock_config_manager.return_value.load_config.return_value = None
        mock_args.config_path = config_path
        with patch('git_mirror.__main__.console.print'):
            domain, group_id, return_value = validate_parse_args(mock_args)
            assert domain == ''
            assert group_id == 0
            assert return_value == 1


if __name__ == "__main__":
    pytest.main()
```

This test covers different scenarios for the `validate_parse_args` function by mocking the dependencies and checking the behavior when arguments are not provided but need to be read from the config file.

Would you like to see the next unit test, or should I stop here with "No more unit tests"?
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: Certainly! For the next unit test, I will cover the `main` function from `__main__.py`. This test will focus on testing the logic of determining the program based on the input arguments and handling the case when the user input command is in the available choices.

```python
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from git_mirror.__main__ import main


def test_main():
    with patch('git_mirror.__main__.argparse.ArgumentParser') as mock_arg_parser:
        mock_args = MagicMock()
        mock_args.command = "some_command"
        mock_args.verbose = 1
        
        with patch('git_mirror.__main__.sys.argv', new=['gl_mirror']):
            with patch('git_mirror.__main__.ask_for_host') as mock_ask_for_host:
                mock_ask_for_host.return_value = "github"
                with patch('git_mirror.__main__.console.print') as mock_console_print:
                    mock_arg_parser.return_value.parse_args.return_value = mock_args
                    exit_value = main()
                    assert exit_value == 0
                    mock_console_print.assert_called_once_with("This appears to be first time setup. Let's initialize configuration.")

        with patch('git_mirror.__main__.os.getenv', return_value="mock_token"):
            mock_args.host = "github"
            with patch('git_mirror.__main__.ask_for_host') as mock_ask_for_host, \
                 patch('git_mirror.__main__.validate_host_token') as mock_validate_host_token, \
                 patch('git_mirror.__main__.BugReporter'):
                mock_validate_host_token.return_value = "mock_token", 0
                mock_args.first_time_init = False
                exit_value = main()
                assert exit_value == 0


if __name__ == "__main__":
    pytest.main()
```

This test simulates different scenarios for the `main` function in `__main__.py`, including determining the program based on the input arguments and handling user input commands.

Next unit test, or should I conclude with "No more unit tests"?
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: Let's proceed with writing a pytest unit test for the `handle_repos` function in `__main__.py`. This test will focus on verifying the correct routing of repositories based on the provided arguments and mocked dependencies.

```python
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from git_mirror.__main__ import handle_repos


def test_handle_repos(tmp_path):
    # Mock arguments and dependencies
    mock_args = MagicMock()
    mock_args.host = "github"
    mock_args.command = "list-repos"
    mock_args.user_name = "test_user"
    mock_args.target_dir = Path("/test/directory")
    mock_args.include_private = True
    mock_args.include_forks = False
    mock_args.config_path = tmp_path / "config.toml"
    mock_args.dry_run = False
    mock_args.verbose = 1
    mock_args.yes = False

    with patch('git_mirror.__main__.validate_host_token') as mock_validate_host_token, \
         patch('git_mirror.__main__.validate_parse_args') as mock_validate_parse_args, \
         patch('git_mirror.__main__.router.route_repos') as mock_route_repos:
        mock_validate_host_token.return_value = "mock_token", 0
        mock_validate_parse_args.return_value = "test_domain", 123, 0

        # Call the function
        handle_repos(mock_args)

        # Validate calls to route_repos
        mock_route_repos.assert_called_once_with(
            command="list-repos",
            user_name="test_user",
            target_dir=Path("/test/directory"),
            token="mock_token",
            host="github",
            include_private=True,
            include_forks=False,
            config_path=tmp_path / "config.toml",
            domain="test_domain",
            group_id=123,
            logging_level=1,
            dry_run=False,
            prompt_for_changes=True
        )


if __name__ == "__main__":
    pytest.main()
```

This unit test covers the `handle_repos` function by mocking the necessary dependencies and verifying that the routing of repositories is done correctly based on the provided arguments.

Would you like to see the next unit test, or should I conclude with "No more unit tests"?