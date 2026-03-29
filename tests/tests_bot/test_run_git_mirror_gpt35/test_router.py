from pathlib import Path
from unittest.mock import MagicMock, patch

from git_mirror.router import route_config, route_repos, route_simple


def test_route_simple_unknown_command():
    mock_console = MagicMock()
    with patch("git_mirror.router._get_console", return_value=mock_console):
        route_simple("unknown-command")
    mock_console.print.assert_called_once_with("Unknown command: unknown-command")


def test_route_config_unknown_command():
    mock_console = MagicMock()
    with patch("git_mirror.router._get_console", return_value=mock_console):
        route_config("unknown-command")
    mock_console.print.assert_called_once_with("Unknown command: unknown-command")


def test_route_config_doctor():
    with patch("git_mirror.manage_config.ConfigManager") as mock_config_manager:
        instance = mock_config_manager.return_value
        route_config("doctor", host="selfhosted")
    instance.doctor.assert_called_once_with(host="selfhosted")


def test_route_repos_selfhosted_github_uses_github_manager():
    with (
        patch("git_mirror.manage_config.ConfigManager") as mock_config_manager,
        patch("git_mirror.manage_github.GithubRepoManager") as mock_github_manager,
        patch("git_mirror.manage_gitlab.GitlabRepoManager") as mock_gitlab_manager,
    ):
        config_manager_instance = mock_config_manager.return_value
        config_manager_instance.load_config.return_value = MagicMock(
            host_type="github",
            host_url="https://ghe.example.com/api/v3",
        )
        github_manager_instance = mock_github_manager.return_value

        route_repos(
            command="list-repos",
            user_name="user",
            target_dir=Path("/fake/path"),
            token="token",
            host="selfhosted",
            include_private=False,
            include_forks=False,
            config_path=Path("/fake/config.toml"),
        )

    mock_github_manager.assert_called_once()
    github_manager_instance.list_repos.assert_called_once()
    mock_gitlab_manager.assert_not_called()
