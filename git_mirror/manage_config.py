"""
Pure interactions with config file.
"""

import logging
import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Optional

import inquirer
import toml
import tomlkit
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from tomlkit import TOMLDocument

from git_mirror.safe_env import load_env

load_env()

# Configure logging
LOGGER = logging.getLogger(__name__)


def default_config_path() -> Path:
    """This is only for defaults, if provided by user, let it throw."""
    try:
        path = Path("~/git_mirror.toml").expanduser()
        return path
    except RuntimeError:
        # Can't expand ~
        pass
    return Path("git_mirror.toml")


def read_config(config_path: Path, key: str) -> Optional[str]:
    """
    Reads a specific key from the TOML configuration file.

    Args:
        config_path (Path): Path to the TOML config file.
        key (str): Key to read from the config.

    Returns:
        Optional[str]: The value for the specified key if found, else None.
    """
    if config_path.exists():
        with open(config_path, encoding="utf-8") as file:
            config = tomlkit.parse(file.read())
            return config.get(key, None)
    return None


@dataclass
class ConfigData:
    host_name: str  # github, gitlab
    host_type: str  # github, gitlab or name of self hosted
    host_url: str  # API endpoint
    user_name: str
    target_dir: Optional[Path]
    pypi_owner_name: str
    include_private: bool = False
    include_forks: bool = False
    group_id: int = 0
    global_template_dir: Optional[Path] = None


def ask_for_section(already_configured: list[str]) -> Optional[ConfigData]:
    if len(already_configured) == 3:
        print("All Github, Gitlab and a self-hosted Gitlab are already configured.")
        return None
    choices = ["github", "gitlab", "selfhosted"]
    for host in already_configured:
        choices.remove(host)

    first_questions = [
        inquirer.List(
            "host_type",
            message="Choose the host type",
            choices=choices,
        ),
        inquirer.Text("user_name", message="Enter your username"),
        inquirer.Text("target_dir", message="What folder should the repositories be cloned to?"),
        inquirer.Confirm("include_private", message="Include private repositories?", default=False),
        inquirer.Confirm("include_forks", message="Include forks?", default=False),
    ]

    answers = inquirer.prompt(first_questions)

    target_dir = Path(answers["target_dir"]).expanduser()
    while not target_dir.exists():
        answer = inquirer.prompt(
            [inquirer.Confirm("create_target_dir", message="Target directory does not exist. Create it?", default=True)]
        )
        print(answer)
        if answer["create_target_dir"]:
            os.makedirs(target_dir)
        else:
            target_dir_answer = inquirer.prompt([inquirer.Text("target_dir", message="Enter the target directory")])
            target_dir = Path(target_dir_answer).expanduser()

    host_type = answers["host_type"]
    host_name = host_type  # Default to host_type, override if selfhosted
    host_url = ""
    group_id_answer = None

    if host_type == "selfhosted":
        host_name = inquirer.prompt(
            [inquirer.List("host_name", message="Is this self hosted github or gitlab?", choices=["github", "gitlab"])]
        )["host_name"]
        host_url = inquirer.prompt([inquirer.Text("host_url", message="Enter your self-hosted Git server URL")])[
            "host_url"
        ]
        group_id_answer = inquirer.prompt(
            [inquirer.Text("group_id", message="Group id to clone a group instead of your personal namespace")]
        )
    elif host_type == "github":
        host_url = "https://api.github.com"
    elif host_type == "gitlab":
        host_url = "https://gitlab.com/api/v4"
        group_id_answer = inquirer.prompt(
            [inquirer.Text("group_id", message="Group id to clone a group instead of your personal namespace")]
        )
    else:
        raise ValueError(f"Unknown host type: {host_type}")

    try:
        if group_id_answer:
            group_id = int(group_id_answer["group_id"])
        else:
            group_id = 0
    except ValueError:
        group_id = 0

    data = ConfigData(
        host_name=host_name,
        host_type=host_type,
        host_url=host_url,
        user_name=answers["user_name"],
        target_dir=target_dir,
        include_private=answers["include_private"],
        include_forks=answers["include_forks"],
        pypi_owner_name="",  # advanced feature.
        group_id=group_id,
    )
    LOGGER.debug(f"Configuration data: {data}")
    return data


def display_config(config: ConfigData):
    """
    Displays the configuration data beautifully using Rich.

    Args:
        config (ConfigData): The configuration data to display.
    """
    console = Console()
    text = Text()

    # Iterate over all fields in the dataclass and append them to the Text object
    for field in fields(ConfigData):
        value = getattr(config, field.name)
        if isinstance(value, Path):
            value = str(value)  # Convert Path to string for display
        text.append(f"{field.name.replace('_', ' ').title()}: ", style="bold magenta")
        text.append(f"{value}\n", style="bold green")

    # Create a Panel with the Text object
    panel = Panel(text, title="Configuration Summary", subtitle="Your current setup", border_style="blue")

    # Print the Panel
    console.print(panel)


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or default_config_path()

    def list_config(self) -> None:
        found = 0
        for host_type in ["selfhosted", "gitlab", "github"]:
            data = self.load_config(host_type)
            if data:
                found += 1
                display_config(data)
        if not found:
            print("No configuration found. Run `git-mirror init` to create a new configuration.")

    def initialize_config(self) -> list[str]:
        already_configured: list[str] = []
        while len(already_configured) < 3:
            toml_config, git_mirror_section = self.load_if_exists()

            def already(gm) -> list[str]:
                # so that these variables don't persist.
                already_done = []
                for host_type in ["selfhosted", "gitlab", "github"]:
                    if host_type in gm:
                        already_done.append(host_type)
                return already_done

            already_configured = already(git_mirror_section)
            print(f"Already configured: {already_configured}")
            config_section = ask_for_section(already_configured)
            if not config_section:
                break

            if toml_config["tool"]["git-mirror"].get(config_section.host_type, {}):  # type: ignore
                raise ValueError(
                    f"Configuration for {config_section.host_type} " f"already exists in {self.config_path.resolve()}"
                )
            if config_section.target_dir and not config_section.target_dir.exists():
                print(f"Creating directory {config_section.target_dir}")
                os.makedirs(config_section.target_dir)

            if config_section.host_type not in ("github", "gitlab"):
                raise ValueError(f"host_type must be github or gitlab even if self hosted. {config_section.host_type}")
            section = {
                "host_type": config_section.host_type,
                "host_url": config_section.host_url,
                "user_name": config_section.user_name,
                "target_dir": str(config_section.target_dir),
                "include_private": config_section.include_private,
                "include_forks": config_section.include_forks,
                "pypi_owner_name": config_section.pypi_owner_name,
                "global_template_dir": config_section.global_template_dir,
            }
            if config_section.group_id:
                section["group_id"] = config_section.group_id
            toml_config["tool"]["git-mirror"][config_section.host_type] = section  # type: ignore

            with open(self.config_path, "w", encoding="utf-8") as file:
                file.write(tomlkit.dumps(toml_config))

            if input("Do you want to add another host? (y/n): ").lower() == "n":
                break
        return already_configured

    def load_config(self, host: str) -> Optional[ConfigData]:
        """
        Loads the configuration for the specified host from the TOML file.
        Args:
            host (str): The host name (github, gitlab, selfhosted).

        Returns:
            Optional[ConfigData]: The configuration data if found, else None.
        """
        LOGGER.debug(f"Loading configuration for {host} from {self.config_path.resolve()}")
        if not host:
            raise ValueError("Host name (gitlab, github, selfhosted) is required.")
        if self.config_path and self.config_path.exists():
            config = tomlkit.loads(self.config_path.read_text(encoding="utf-8"))
            tool_config = config.get("tool", {}).get("git-mirror", {}).get(host, {})
            if not tool_config:
                return None
            target_dir = tool_config.get("target_dir")
            if not target_dir:
                raise ValueError(f"target_dir not found in config file at {self.config_path.resolve()}")

            if target_dir and not Path(target_dir).exists():
                print(f"Creating directory {target_dir}")
                os.makedirs(target_dir)
            data = ConfigData(
                host,
                tool_config.get("host_type", host),
                tool_config.get("host_url", ""),
                tool_config.get("user_name"),
                target_dir,
                tool_config.get("pypi_owner_name", ""),
                tool_config.get("include_private", False),
                tool_config.get("include_forks", False),
                tool_config.get("group_id", 0),
                tool_config.get("global_template_dir", None),
            )
            return data
        return None

    def _write_repos_to_toml(self, repos: list[str], existing_config: dict[str, Any]) -> None:
        """
        Writes GitHub repository names to a TOML config file with specified attributes.

        Args:
            repos (List[str]): List of repository names.
            existing_config (Dict[str, Any]): Existing configuration to merge with.
        """
        config: dict[str, Any] = {"tool.git-mirror.repos": {}}
        for repo in repos:
            # Use existing config if present, else default to an empty dict
            config["tool.git-mirror.repos"][repo] = existing_config.get(repo, {})

        with open(self.config_path, "w") as file:
            toml.dump(config, file)

    def load_and_sync_config(self, host: str, repos: list[str]) -> dict[str, Any]:
        """
        Loads the TOML configuration, syncs it with the current list of GitHub repositories,
        and updates the TOML file.

        Returns:
            dict[str, Any]: The updated configuration.
        """
        config, git_mirror_section = self.load_if_exists()

        # repos section
        git_mirror = git_mirror_section.get(host, {}).get("repos", {})

        repos_with_data = {full_name: {"important": True} for full_name in repos}

        # Add repositories not already there.
        for repo_name, repo_config in repos_with_data.items():
            if repo_name not in git_mirror:
                git_mirror[repo_name] = tomlkit.inline_table()
                for key, value in repo_config.items():
                    git_mirror[repo_name][key] = value

        # Remove repositories no longer present
        for repo_name in list(git_mirror.keys()):
            if repo_name not in repos:
                del git_mirror[repo_name]

        config["tool"]["git-mirror"][host]["repos"] = git_mirror  # type: ignore

        print(f"Syncing configuration with {len(repos)} repositories to {self.config_path.resolve()}")
        with open(self.config_path, "w", encoding="utf-8") as file:
            file.write(tomlkit.dumps(config))

        return config

    def load_if_exists(self) -> tuple[TOMLDocument, dict[str, Any]]:
        if self.config_path.exists():
            LOGGER.debug(f"Loading config from {self.config_path.resolve()}")
            with open(self.config_path, encoding="utf-8") as file:
                config = tomlkit.parse(file.read())
            git_mirror_section = config.get("tool", {}).get("git-mirror", {})
        else:
            LOGGER.debug(f"Config file {self.config_path.resolve()} does not exist. Creating a new one.")
            config = tomlkit.document()
            config["tool"] = {"git-mirror": {}}
            git_mirror_section = config["tool"]["git-mirror"]  # type: ignore
        return config, git_mirror_section


if __name__ == "__main__":
    cm = ConfigManager(config_path=Path("~/git_mirror.toml").expanduser())
    result = cm.load_config("selfhosted")
    print(result)
