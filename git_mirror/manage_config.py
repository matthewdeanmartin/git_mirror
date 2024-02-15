"""
Pure interactions with config file.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import toml
import tomlkit
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file, if present

# Configure logging
LOGGER = logging.getLogger(__name__)


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
    user_name: str
    target_dir: Optional[Path]
    pypi_owner_name: str
    include_private: bool = False
    include_forks: bool = False


class ConfigManager:
    def __init__(self, repo_names: list[str], host: str):
        self.repo_names: list[str] = repo_names
        self.host = host

    def load_config(self, config_path: Optional[Path] = None) -> ConfigData:
        if not config_path:
            config_path = Path(os.getcwd()) / "pyproject.toml"
        if config_path and config_path.exists():
            config = tomlkit.loads(config_path.read_text(encoding="utf-8"))
            tool_config = config.get("tool", {}).get("git-mirror", {}).get(self.host, {})
            data = ConfigData(
                tool_config.get("user_name"),
                tool_config.get("target_dir", os.getcwd()),
                tool_config.get("pypi_owner_name", ""),
                tool_config.get("include_private", False),
                tool_config.get("include_forks", False),
            )
            return data
        return ConfigData("", None, "")

    def _write_repos_to_toml(self, repos: list[str], toml_path: Path, existing_config: dict[str, Any]) -> None:
        """
        Writes GitHub repository names to a TOML config file with specified attributes.

        Args:
            repos (List[str]): List of repository names.
            toml_path (Path): Path to the TOML config file.
            existing_config (Dict[str, Any]): Existing configuration to merge with.
        """
        config: dict[str, Any] = {"tool.git-mirror.repos": {}}
        for repo in repos:
            # Use existing config if present, else default to an empty dict
            config["tool.git-mirror.repos"][repo] = existing_config.get(repo, {})

        with open(toml_path, "w") as file:
            toml.dump(config, file)

    def load_and_sync_config(self, toml_path: Optional[Path] = None) -> dict[str, Any]:
        """
        Loads the TOML configuration, syncs it with the current list of GitHub repositories,
        and updates the TOML file.

        Args:
            toml_path (Path): Path to the TOML config file. If None, defaults to pyproject.toml in the current working directory.

        Returns:
            dict[str, Any]: The updated configuration.
        """
        if toml_path is None:
            toml_path = Path(os.getcwd()) / "pyproject.toml"

        if toml_path.exists():
            with open(toml_path, encoding="utf-8") as file:
                config = tomlkit.parse(file.read())
            git_mirror = config.get("tool", {}).get("git-mirror", {}).get(self.host, {}).get("repos", {})
        else:
            config = tomlkit.document()
            config["tool"] = {"git-mirror": {"host": self.host, "repos": {}}}
            git_mirror = config["tool"]["git-mirror"]  # type: ignore

        repos = {full_name: {"important": True} for full_name in self.repo_names}

        # Add repositories not already there.
        for repo_name, repo_config in repos.items():
            if repo_name not in git_mirror:
                git_mirror[repo_name] = tomlkit.inline_table()
                for key, value in repo_config.items():
                    git_mirror[repo_name][key] = value

        # Remove repositories no longer present
        for repo_name in list(git_mirror.keys()):
            if repo_name not in repos:
                del git_mirror[repo_name]

        config["tool"]["git-mirror"][self.host]["repos"] = git_mirror  # type: ignore

        LOGGER.info(f"Syncing configuration with {len(repos)} repositories to {toml_path.resolve()}")
        with open(toml_path, "w", encoding="utf-8") as file:
            file.write(tomlkit.dumps(config))

        return config
