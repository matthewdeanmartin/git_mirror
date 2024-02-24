import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import inquirer


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


def get_command_info(args: argparse.Namespace) -> None:
    commands: list[tuple[str, str]] = [
        ("Initialize Configuration", "init"),
        ("Show Account Info", "show-account"),
        ("List repositories", "list-repos"),
        ("Clone all repositories", "clone-all"),
        ("Run pull for all repositories", "pull-all"),
        ("Report uncommitted/unpushed changes", "local-changes"),
        ("Report non-repo files in target folder", "not-repo"),
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
        break
    # Right now everything else should come from config and
    # user shouldn't be re-entering all that config on every command.
    return


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
