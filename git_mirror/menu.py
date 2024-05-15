import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import inquirer

from git_mirror.manage_config import ConfigManager
from git_mirror.ui import console_with_theme

console = console_with_theme()


@dataclass
class CommandInfo:
    command: str
    host: Optional[str] = None
    user_name: Optional[str] = None
    group_id: Optional[int] = None
    domain: Optional[str] = None
    pypi_owner_name: Optional[str] = None
    target_dir: Optional[Path] = None
    include_forks: bool = False
    include_private: bool = False
    config_path: Optional[Path] = None
    verbose: bool = False
    args: list[str] = field(default_factory=list)


def get_command_info(args: argparse.Namespace) -> Optional[str]:
    commands: list[tuple[str, str]] = [
        ("Initialize Configuration", "init"),
        ("Show Account Info", "show-account"),
        ("List repositories", "list-repos"),
        ("Clone all repositories", "clone-all"),
        ("Run pull for all repositories", "pull-all"),
        ("Report uncommitted/unpushed changes", "local-changes"),
        ("Report non-repo folders in target folder", "not-repo"),
        ("Report all build statuses", "build-status"),
        ("Sync repo list in config with source control host", "sync-config"),
        ("Report current configuration", "list-config"),
        ("Report unpublished pypi packages", "pypi-status"),
        ("Update all branches from main", "update-from-main"),
        ("Prune all branches", "prune-all"),
        ("Cross-repo report", "cross-repo-report"),
        ("Cross-repo sync", "cross-repo-sync"),
        ("Cross-repo Template Initialization", "cross-repo-init"),
        ("Poetry ", "cross-repo-init"),
        ("Main Menu", "Main Menu"),
    ]

    categories: dict[str, list[str]] = {
        "Repository Commands": ["list-repos", "clone-all", "pull-all", "local-changes", "not-repo", "Main Menu"],
        "Branch Commands": ["update-from-main", "prune-all", "Main Menu"],
        "Configuration Commands": ["init", "sync-config", "list-config", "Main Menu"],
        "PyPI Commands": ["pypi-status", "Main Menu"],
        "Source Control Host Commands": ["show-account", "Main Menu"],
        "Template Sync": ["cross-repo-report", "cross-repo-sync", "cross-repo-init", "Main Menu"],
        "Poetry Commands": ["poetry-relock", "Main Menu"],
        "Exit": [],
    }

    # Convert commands list to a dictionary for easier lookup
    # command_lookup = {description: cmd for description, cmd in commands}

    # Category selection
    category_questions = [inquirer.List("category", message="Choose a category", choices=list(categories.keys()))]
    while True:
        category_answer = inquirer.prompt(category_questions)
        handle_control_c(category_answer)
        selected_category = category_answer["category"]
        if selected_category == "Exit":
            sys.exit()

        # Command selection within the chosen category
        command_questions = [
            inquirer.List(
                "command",
                message="Choose a command",
                choices=[cmd for cmd in commands if cmd[1] in categories[selected_category]],
            )
        ]
        command_answer = inquirer.prompt(command_questions)
        handle_control_c(command_answer)
        selected_command = command_answer["command"]
        if selected_command == "Main Menu":
            continue
        args.command = selected_command
        return selected_command
    # Right now everything else should come from config and
    # user shouldn't be re-entering all that config on every command.
    return None


def handle_control_c(answer: Any) -> None:
    """
    Handle control-C exit.

    Args:
        answer (Any): The answer from the user.
    """
    if answer is None:
        print("Exiting.")
        # This happens when the user hits control-C
        sys.exit()


def ask_for_host(config_manager: ConfigManager) -> str:
    """
    Main function to run the UI that queries configuration statuses and asks the user for further actions.
    """
    config_status = config_manager.load_config_objects()
    configured_options = [service for service, is_configured in config_status.items() if is_configured]
    unconfigured_options = [service for service, is_configured in config_status.items() if not is_configured]

    if len(configured_options) == 3:
        message = "Select a source host"
        choices = configured_options
    else:
        message = "Select as source host or configure an additional one"
        choices = configured_options + ["Configure new service"]
    questions = [inquirer.List("service", message=message, choices=choices, carousel=True)]

    answers = inquirer.prompt(questions)

    if answers["service"] == "Configure new service":
        config_questions = [
            inquirer.Checkbox(
                "services_to_configure",
                message="Select services to configure:",
                choices=unconfigured_options,
                carousel=True,
            )
        ]
        config_answers = inquirer.prompt(config_questions)
        console.print(f"Selected for configuration: {config_answers['services_to_configure']}", style="bold green")
        # Here you would call your configuration function(s) for the selected services
        return ""
    else:
        console.print(f"Using {answers['service']}", style="bold green")
        return answers["service"]
