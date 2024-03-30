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
Source Path: E:\github\git_mirror\git_mirror\menu.py

Source Path: E:\github\git_mirror\git_mirror\menu.py
Module Name: git_mirror.menu
```python
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


def ask_for_host(config_manager:ConfigManager) -> str:
    """
    Main function to run the UI that queries configuration statuses and asks the user for further actions.
    """
    config_status = config_manager.load_config_objects()
    configured_options = [service for service, is_configured  in config_status.items() if is_configured]
    unconfigured_options = [service for service, is_configured  in config_status.items() if not is_configured]

    if len(configured_options)==3:
        message = "Select a source host"
        choices = configured_options
    else:
        message = "Select as source host or configure an additional one"
        choices = configured_options + ["Configure new service"]
    questions = [
        inquirer.List('service',
                      message=message,
                      choices=choices,
                      carousel=True)
    ]

    answers = inquirer.prompt(questions)

    if answers["service"] == "Configure new service":
        config_questions = [
            inquirer.Checkbox('services_to_configure',
                              message="Select services to configure:",
                              choices=unconfigured_options,
                              carousel=True)
        ]
        config_answers = inquirer.prompt(config_questions)
        console.print(f"Selected for configuration: {config_answers['services_to_configure']}", style="bold green")
        # Here you would call your configuration function(s) for the selected services
        return ""
    else:
        console.print(f"Using {answers['service']}", style="bold green")
        return answers['service']
```

Here are function and method signatures of the dependencies

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
#git_mirror/ui.py
def console_with_theme()->Console:
    """Factory to allow for app theming."""
    ...

```
Please write some unit tests for E:\github\git_mirror\git_mirror\menu.py. If you can't think of anymore unit tests, write "No more unit tests".
Assistant: I'll start by reviewing the code for any potential bugs:

1. In the `get_command_info` function, there is a line `args.command = selected_command` where `args` is not defined within the scope of the function. This will result in a `NameError`.

I will now write pytest unit tests covering the `menu.py` module, ensuring to test various functions.

```python
# test_menu.py
from unittest.mock import patch, MagicMock
import inquirer
import sys

from git_mirror.menu import get_command_info, CommandInfo, handle_control_c, ask_for_host

@patch('git_mirror.menu.inquirer')
@patch('git_mirror.menu.sys')
def test_get_command_info(mock_sys, mock_inquirer):
    mock_inquirer.prompt.side_effect = [{'category': 'Repository Commands', 'command': 'list-repos'},
                                       {'category': 'Exit'}]
    args = MagicMock()
    args.command = None
    selected_command = get_command_info(args)
    assert selected_command == 'list-repos'
    assert mock_sys.exit.called

def test_handle_control_c():
    # sys.exit should be called when answer is None
    with patch('git_mirror.menu.sys.exit') as mock_exit:
        handle_control_c(None)
        mock_exit.assert_called_once()

@patch('git_mirror.menu.console')
@patch('git_mirror.menu.inquirer')
def test_ask_for_host(mock_inquirer, mock_console):
    config_manager = MagicMock()
    config_manager.load_config_objects.return_value = {"service1": True, "service2": False, "service3": True}
    
    mock_inquirer.prompt.side_effect = [{"service": "Configure new service"},
                                       {"services_to_configure": ["service2"]}]
    
    assert ask_for_host(config_manager) == ""
    mock_console.print.assert_called_with("Selected for configuration: ['service2']", style="bold green")

# No more unit tests
```

These tests cover the `get_command_info`, `handle_control_c`, and `ask_for_host` functions in the `menu.py` module. The tests verify the expected behavior of these functions when certain conditions are met. If you have any more specific scenarios or functions to test, feel free to provide them.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ```python
from unittest.mock import patch, MagicMock
from pathlib import Path

from git_mirror.menu import ask_for_host

@patch('git_mirror.menu.console_with_theme')
@patch('git_mirror.menu.inquirer')
def test_ask_for_host_configured_options(mock_inquirer, mock_console_with_theme):
    config_manager = MagicMock()
    config_manager.load_config_objects.return_value = {"service1": True, "service2": True, "service3": True}

    mock_inquirer.prompt.return_value = {"service": "service1"}
    assert ask_for_host(config_manager) == "service1"
    mock_console_with_theme().print.assert_called_with("Using service1", style="bold green")

@patch('git_mirror.menu.console_with_theme')
@patch('git_mirror.menu.inquirer')
def test_ask_for_host_unconfigured_options(mock_inquirer, mock_console_with_theme):
    config_manager = MagicMock()
    config_manager.load_config_objects.return_value = {"service1": True, "service2": False, "service3": False}

    mock_inquirer.prompt.side_effect = [
        {"service": "Configure new service"},
        {"services_to_configure": ["service2"]}
    ]

    assert ask_for_host(config_manager) == ""
    mock_console_with_theme().print.assert_called_with("Selected for configuration: ['service2']", style="bold green")

# No more unit tests
```
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ```python
# No more unit tests
```
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ```python
# No more unit tests
```
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ```python
# No more unit tests
```