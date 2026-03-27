"""
Pure interactions with config file.
"""

import logging
import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import inquirer
import toml
import tomlkit
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from tomlkit import TOMLDocument

import git_mirror.pat_init as pat_init
import git_mirror.pat_init_gitlab as pat_init_gitlab
from git_mirror.safe_env import load_env
from git_mirror.ui import console_with_theme

load_env()

LOGGER = logging.getLogger(__name__)

console = console_with_theme()

SUPPORTED_HOSTS = ("github", "gitlab", "selfhosted")
PUBLIC_GITHUB_API_URL = "https://api.github.com"
PUBLIC_GITLAB_URL = "https://gitlab.com"


def default_config_path() -> Path:
    """This is only for defaults, if provided by user, let it throw."""
    try:
        path = Path("~/git_mirror.toml").expanduser()
        return path
    except RuntimeError:
        pass
    return Path("git_mirror.toml")


def read_config(config_path: Path, key: str) -> str | None:
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


def _normalize_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        raise ValueError("Host URL is required.")
    if "://" not in value:
        value = f"https://{value}"
    return value.rstrip("/")


def _normalize_github_url(raw_url: str) -> str:
    value = _normalize_url(raw_url)
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    if host == "github.com":
        return PUBLIC_GITHUB_API_URL
    if host == "api.github.com":
        return value
    if not path:
        path = "/api/v3"
    elif not path.startswith("/api/"):
        path = f"{path}/api/v3"
    return urlunparse(parsed._replace(path=path, params="", query="", fragment=""))


def _coerce_path(value: str | Path | None) -> Path | None:
    if value is None or value == "":
        return None
    return Path(value).expanduser()


def _default_host_url(section_name: str, host_type: str | None = None) -> str:
    provider = host_type or section_name
    if provider == "github":
        return PUBLIC_GITHUB_API_URL
    if provider == "gitlab":
        return PUBLIC_GITLAB_URL
    raise ValueError(f"Unknown host type: {provider}")


def _token_env_var(config: "ConfigData") -> str:
    if config.host_name == "selfhosted":
        return "SELFHOSTED_ACCESS_TOKEN"
    if config.host_type == "github":
        return "GITHUB_ACCESS_TOKEN"
    return "GITLAB_ACCESS_TOKEN"


def _host_label(config: "ConfigData") -> str:
    if config.host_name == "selfhosted":
        return f"self-hosted {config.host_type}"
    return config.host_type


@dataclass
class ConfigData:
    host_name: str  # github, gitlab, selfhosted
    host_type: str  # github or gitlab
    host_url: str  # host URL or API base depending on provider
    user_name: str
    target_dir: Path | None
    include_private: bool = False
    include_forks: bool = False
    group_id: int = 0
    global_template_dir: Path | None = None


@dataclass
class SetupCheck:
    name: str
    ok: bool
    details: str
    fix: str | None = None


def _render_checks(config: ConfigData, checks: list[SetupCheck]) -> None:
    text = Text()
    text.append(f"Config key: {config.host_name}\n", style="bold cyan")
    text.append(f"Provider: {_host_label(config)}\n", style="bold cyan")
    text.append(f"Host URL: {config.host_url}\n", style="bold cyan")
    text.append(f"Username: {config.user_name}\n", style="bold cyan")
    if config.target_dir:
        text.append(f"Target dir: {config.target_dir}\n", style="bold cyan")
    for check in checks:
        prefix = "[OK]" if check.ok else "[FAIL]"
        style = "green" if check.ok else "red"
        text.append(f"{prefix} {check.name}: {check.details}\n", style=style)
        if check.fix:
            text.append(f"      Fix: {check.fix}\n", style="yellow")
    console.print(Panel(text, title=f"Doctor: {_host_label(config)}", border_style="blue"))


def _prompt_for_target_dir(initial_value: str) -> Path:
    target_dir = Path(initial_value).expanduser()
    while not target_dir.exists():
        answer = inquirer.prompt(
            [inquirer.Confirm("create_target_dir", message="Target directory does not exist. Create it?", default=True)]
        )
        if answer["create_target_dir"]:
            os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir_answer = inquirer.prompt([inquirer.Text("target_dir", message="Enter the target directory")])
            target_dir = Path(target_dir_answer["target_dir"]).expanduser()
    return target_dir


def ask_for_section(already_configured: list[str]) -> ConfigData | None:
    if len(already_configured) == len(SUPPORTED_HOSTS):
        console.print("All Github, Gitlab and self-hosted are already configured.")
        return None

    choices = [host for host in SUPPORTED_HOSTS if host not in already_configured]
    first_questions = [
        inquirer.List("host_name", message="Choose the host to configure", choices=choices),
        inquirer.Text("user_name", message="Enter your username"),
        inquirer.Text("target_dir", message="What folder should the repositories be cloned to?"),
        inquirer.Confirm("include_private", message="Include private repositories?", default=False),
        inquirer.Confirm("include_forks", message="Include forks?", default=False),
    ]
    answers = inquirer.prompt(first_questions)

    target_dir = _prompt_for_target_dir(answers["target_dir"])
    section_name = answers["host_name"]
    host_type = section_name
    host_url = ""
    group_id = 0

    if section_name == "selfhosted":
        host_type = inquirer.prompt(
            [inquirer.List("host_type", message="Is this self-hosted GitHub or GitLab?", choices=["github", "gitlab"])]
        )["host_type"]
        entered_url = inquirer.prompt([inquirer.Text("host_url", message="Enter your self-hosted Git server URL")])[
            "host_url"
        ]
        host_url = _normalize_github_url(entered_url) if host_type == "github" else _normalize_url(entered_url)
    else:
        host_url = _default_host_url(section_name)

    if host_type == "gitlab":
        group_id_answer = inquirer.prompt(
            [inquirer.Text("group_id", message="Optional GitLab group id to clone a group instead of your personal namespace")]
        )
        try:
            group_id = int(group_id_answer["group_id"]) if group_id_answer["group_id"] else 0
        except ValueError:
            group_id = 0

    data = ConfigData(
        host_name=section_name,
        host_type=host_type,
        host_url=host_url,
        user_name=answers["user_name"],
        target_dir=target_dir,
        include_private=answers["include_private"],
        include_forks=answers["include_forks"],
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
    display = Console()
    text = Text()
    for field in fields(ConfigData):
        value = getattr(config, field.name)
        if isinstance(value, Path):
            value = str(value)
        text.append(f"{field.name.replace('_', ' ').title()}: ", style="bold magenta")
        text.append(f"{value}\n", style="bold green")
    panel = Panel(text, title="Configuration Summary", subtitle="Your current setup", border_style="blue")
    display.print(panel)


class ConfigManager:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or default_config_path()

    def load_config_objects(self) -> dict[str, ConfigData | None]:
        return {host_type: self.load_config(host_type) for host_type in SUPPORTED_HOSTS}

    def list_config(self) -> None:
        found = 0
        for host_type in SUPPORTED_HOSTS:
            data = self.load_config(host_type)
            if data:
                found += 1
                display_config(data)
        if not found:
            console.print("No configuration found. Run `git_mirror init` to create a new configuration.")

    def _write_config(self, config_section: ConfigData, toml_config: TOMLDocument) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        section: dict[str, Any] = {
            "host_type": config_section.host_type,
            "host_url": config_section.host_url,
            "user_name": config_section.user_name,
            "target_dir": str(config_section.target_dir) if config_section.target_dir else "",
            "include_private": config_section.include_private,
            "include_forks": config_section.include_forks,
            "global_template_dir": str(config_section.global_template_dir) if config_section.global_template_dir else None,
        }
        if config_section.group_id:
            section["group_id"] = config_section.group_id
        toml_config["tool"]["git-mirror"][config_section.host_name] = section  # type: ignore[index]
        with open(self.config_path, "w", encoding="utf-8") as file:
            file.write(tomlkit.dumps(toml_config))

    def _run_checks(self, config: ConfigData, attempt_token_setup: bool = False) -> list[SetupCheck]:
        checks = [
            SetupCheck("Config section", True, f"Configuration is stored under [tool.git-mirror.{config.host_name}]"),
            SetupCheck("Host type", config.host_type in ("github", "gitlab"), f"Provider is {config.host_type}"),
        ]

        if config.target_dir and config.target_dir.exists() and config.target_dir.is_dir():
            checks.append(SetupCheck("Target directory", True, f"{config.target_dir} exists"))
        else:
            checks.append(
                SetupCheck(
                    "Target directory",
                    False,
                    f"{config.target_dir} is missing" if config.target_dir else "No target directory configured",
                    "Run `git_mirror init` again or create the directory manually.",
                )
            )

        token_env_var = _token_env_var(config)
        token = os.getenv(token_env_var)
        if not token and attempt_token_setup:
            if config.host_type == "github":
                token = pat_init.setup_github_pat(
                    env_var=token_env_var,
                    api_url=config.host_url,
                    host_label=_host_label(config),
                )
            else:
                token = pat_init_gitlab.setup_gitlab_pat(
                    env_var=token_env_var,
                    host_url=config.host_url,
                    host_label=_host_label(config),
                )

        if not token:
            checks.append(
                SetupCheck(
                    "Access token",
                    False,
                    f"Environment variable {token_env_var} is missing.",
                    f"Create a PAT for {_host_label(config)} and set {token_env_var}, then rerun `git_mirror doctor --host {config.host_name}`.",
                )
            )
            return checks

        checks.append(SetupCheck("Access token", True, f"Environment variable {token_env_var} is set"))
        if config.host_type == "github":
            authenticated_user = pat_init.get_authenticated_user(token, api_url=config.host_url)
            valid = authenticated_user is not None
            username = authenticated_user.get("login", "") if authenticated_user else ""
        else:
            authenticated_user = pat_init_gitlab.get_authenticated_user(token, host_url=config.host_url)
            valid = authenticated_user is not None
            username = authenticated_user.get("username", "") if authenticated_user else ""

        checks.append(
            SetupCheck(
                "Token validity",
                valid,
                f"Authenticated as {username}" if valid else "Could not authenticate to the configured host.",
                None
                if valid
                else f"Make sure {token_env_var} is valid for {config.host_url} and has the scopes required to list repositories.",
            )
        )
        if valid and username and config.user_name and username.lower() != config.user_name.lower():
            checks.append(
                SetupCheck(
                    "Configured username",
                    False,
                    f"Config expects {config.user_name}, but the token belongs to {username}.",
                    "Update the configured username or use a token for the same account.",
                )
            )
        else:
            checks.append(SetupCheck("Configured username", True, f"Configured username is {config.user_name}"))
        return checks

    def doctor(self, host: str | None = None, attempt_token_setup: bool = False) -> bool:
        configured_hosts = [host] if host else [name for name, data in self.load_config_objects().items() if data]
        if host and not configured_hosts:
            console.print(f"No configuration found for {host}. Run `git_mirror init` first.")
            return False
        if not configured_hosts:
            console.print("No configuration found. Run `git_mirror init` first.")
            return False

        overall_ok = True
        for configured_host in configured_hosts:
            config = self.load_config(configured_host)
            if not config:
                overall_ok = False
                console.print(f"No configuration found for {configured_host}.")
                continue
            checks = self._run_checks(config, attempt_token_setup=attempt_token_setup)
            _render_checks(config, checks)
            overall_ok = overall_ok and all(check.ok for check in checks)

        if overall_ok:
            console.print("Setup looks good. Try `git_mirror list-repos --host github` or the host you configured.")
        else:
            console.print("Setup needs attention. Fix the failing checks above, then rerun `git_mirror doctor`.")
        return overall_ok

    def initialize_config(self) -> list[str]:
        already_configured: list[str] = []
        while len(already_configured) < len(SUPPORTED_HOSTS):
            toml_config, git_mirror_section = self.load_if_exists()

            already_configured = [host_type for host_type in SUPPORTED_HOSTS if host_type in git_mirror_section]
            console.print(f"Already configured: {already_configured}")
            config_section = ask_for_section(already_configured)
            if not config_section:
                break

            if toml_config["tool"]["git-mirror"].get(config_section.host_name, {}):  # type: ignore[index, union-attr]
                raise ValueError(
                    f"Configuration for {config_section.host_name} already exists in {self.config_path.resolve()}"
                )

            if config_section.target_dir and not config_section.target_dir.exists():
                console.print(f"Creating directory {config_section.target_dir}")
                os.makedirs(config_section.target_dir, exist_ok=True)

            self._write_config(config_section, toml_config)
            console.print(
                f"Saved configuration for {_host_label(config_section)} to {self.config_path.resolve()}",
                style="bold green",
            )
            self.doctor(config_section.host_name, attempt_token_setup=True)

            if input("Do you want to add another host? (y/n): ").lower() == "n":
                break
        return already_configured

    def load_config(self, host: str) -> ConfigData | None:
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
        if self.config_path.exists():
            config = tomlkit.loads(self.config_path.read_text(encoding="utf-8"))
            tool_config = config.get("tool", {}).get("git-mirror", {}).get(host, {})
            if not tool_config:
                return None

            target_dir = _coerce_path(tool_config.get("target_dir"))
            if not target_dir:
                raise ValueError(f"target_dir not found in config file at {self.config_path.resolve()}")
            if not target_dir.exists():
                console.print(f"Creating directory {target_dir}")
                os.makedirs(target_dir, exist_ok=True)

            host_type = tool_config.get("host_type") or tool_config.get("type") or ("github" if host == "github" else "gitlab")
            host_url = tool_config.get("host_url") or tool_config.get("url") or _default_host_url(host, host_type)
            global_template_dir = _coerce_path(tool_config.get("global_template_dir"))
            return ConfigData(
                host_name=host,
                host_type=host_type,
                host_url=host_url,
                user_name=tool_config.get("user_name"),
                target_dir=target_dir,
                include_private=tool_config.get("include_private", False),
                include_forks=tool_config.get("include_forks", False),
                group_id=tool_config.get("group_id", 0),
                global_template_dir=global_template_dir,
            )
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
            config["tool.git-mirror.repos"][repo] = existing_config.get(repo, {})

        with open(self.config_path, "w", encoding="utf-8") as file:
            toml.dump(config, file)

    def load_and_sync_config(self, host: str, repos: list[str]) -> dict[str, Any]:
        """
        Loads the TOML configuration, syncs it with the current list of GitHub repositories,
        and updates the TOML file.

        Returns:
            dict[str, Any]: The updated configuration.
        """
        config, git_mirror_section = self.load_if_exists()
        git_mirror = git_mirror_section.get(host, {}).get("repos", {})
        repos_with_data = {full_name: {"important": True} for full_name in repos}

        for repo_name, repo_config in repos_with_data.items():
            if repo_name not in git_mirror:
                git_mirror[repo_name] = tomlkit.inline_table()
                for key, value in repo_config.items():
                    git_mirror[repo_name][key] = value

        for repo_name in list(git_mirror.keys()):
            if repo_name not in repos:
                del git_mirror[repo_name]

        config["tool"]["git-mirror"][host]["repos"] = git_mirror  # type: ignore[index]

        console.print(f"Syncing configuration with {len(repos)} repositories to {self.config_path.resolve()}")
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
            git_mirror_section = config["tool"]["git-mirror"]  # type: ignore[index]
        return config, git_mirror_section


if __name__ == "__main__":
    cm = ConfigManager(config_path=Path("~/git_mirror.toml").expanduser())
    result = cm.load_config("selfhosted")
    print(result)
