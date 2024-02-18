import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

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
    commands = [
        ("Initialize Configuration", "init"),
        ("Show Account Info", "show-account"),
        # ("menu", ""),
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
    ]

    categories = {
        "Repository Commands": ["list-repos", "clone-all", "pull-all", "local-changes", "not-repo"],
        "Branch Commands": ["update-from-main", "prune-all"],
        "Configuration Commands": ["init", "sync-config", "list-config"],
        "PyPI Commands": ["pypi-status"],
        "Source Control Host Commands": ["show-account"],
    }

    # Convert commands list to a dictionary for easier lookup
    # command_lookup = {description: cmd for description, cmd in commands}

    # Category selection
    category_questions = [inquirer.List("category", message="Choose a category", choices=list(categories.keys()))]
    category_answer = inquirer.prompt(category_questions)
    selected_category = category_answer["category"]

    # Command selection within the chosen category
    command_questions = [
        inquirer.List(
            "command",
            message="Choose a command",
            choices=[cmd for cmd in commands if cmd[1] in categories[selected_category]],
        )
    ]
    command_answer = inquirer.prompt(command_questions)
    selected_command = command_answer["command"]

    args.command = selected_command

    # Right now everything else should come from config and
    # user shouldn't be re-entering all that config on every command.
    return
    # # Depending on the command, prompt for additional arguments
    # # This example shows a generic approach; customize it based on your command's needs
    # args_questions = []
    # if selected_command in ["init", "clone-all"]:
    #     args_questions.append(inquirer.Text('user_name', message="Enter your username"))
    #     # Add other argument prompts as needed
    #
    # args_answers = inquirer.prompt(args_questions)
    #
    # for key, value in args_answers.items():
    #     print(key, value)
    #     setattr(args, key, value)
