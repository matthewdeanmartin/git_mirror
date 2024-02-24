from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from git_mirror.router import route_to_command


@pytest.mark.parametrize(
    "command,expected_method,manager",
    [
        ("clone-all", "clone_all", "GithubRepoManager"),
        ("pull-all", "pull_all", "GithubRepoManager"),
        ("not-repo", "not_repo", "GithubRepoManager"),
        ("build-status", "list_repo_builds", "GithubRepoManager"),
        ("local-changes", "check_for_uncommitted_or_unpushed_changes", "GitManager"),
        ("sync-config", "load_and_sync_config", "ConfigManager"),
        ("pypi-status", "check_pypi_publish_status", "GithubRepoManager"),
    ],
)
def test_main_github_commands(command, expected_method, manager):
    github_token = "fake-token"
    user_name = "fake-user"
    target_dir = Path("/fake/path")
    include_private = False
    include_forks = False
    config_path = Path("/fake/config.toml")
    pypi_owner_name = "fake-owner"

    with (
        patch("git_mirror.manage_git.GitManager") as MockGitManager,
        patch("git_mirror.manage_github.GithubRepoManager") as MockGithubManager,
        patch("git_mirror.manage_config.ConfigManager") as MockConfigManager,
    ):
        github_manager_instance = MagicMock()
        MockGithubManager.return_value = github_manager_instance
        git_manager_instance = MagicMock()
        MockGitManager.return_value = git_manager_instance
        config_manager_instance = MagicMock()
        repo_list = []
        github_manager_instance.list_repo_names.return_value = repo_list
        MockConfigManager.return_value = config_manager_instance

        route_to_command(
            command=command,
            user_name=user_name,
            target_dir=target_dir,
            token=github_token,
            host="github",
            include_private=include_private,
            include_forks=include_forks,
            config_path=config_path,
            pypi_owner_name=pypi_owner_name,
        )

        # Assert that the expected method was called on the manager instance
        # if manager == "GithubRepoManager":
        #     getattr(MockGithubManager, expected_method).assert_called()
        # elif manager == "GitManager":
        #     getattr(MockGitManager, expected_method).assert_called()
        # elif manager == "ConfigManager":
        #     getattr(MockConfigManager, expected_method).assert_called()
        # else:
        #     raise ValueError(f"Unknown manager: {manager}")

        if manager == "GithubRepoManager":
            getattr(github_manager_instance, expected_method).assert_called()
        elif manager == "GitManager":
            getattr(git_manager_instance, expected_method).assert_called()
        elif manager == "ConfigManager":
            getattr(config_manager_instance, expected_method).assert_called()
        else:
            raise ValueError(f"Unknown manager: {manager}")

        # For methods that might have arguments, you can make more specific assertions
        if command == "pypi-status":
            github_manager_instance.check_pypi_publish_status.assert_called_with(pypi_owner_name=pypi_owner_name)
        elif command == "sync-config":
            config_manager_instance.load_and_sync_config.assert_called_with("github", [])


# Test for an unknown command which should not result in any manager method being called
def test_main_github_unknown_command():
    with (patch("git_mirror.manage_github.GithubRepoManager") as MockManager,):
        manager_instance = MagicMock()
        MockManager.return_value = manager_instance

        unknown_command = "unknown-command"
        route_to_command(
            command=unknown_command,
            user_name="user",
            target_dir=Path("/fake/path"),
            token="token",
            host="github",
            include_private=False,
            include_forks=False,
        )
        manager_instance.assert_not_called()
