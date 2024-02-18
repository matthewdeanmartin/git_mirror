import os
from unittest.mock import ANY, patch

import pytest
import tomlkit

from git_mirror.__main__ import main  # Adjust import path as necessary


# Fixture for CLI arguments
@pytest.fixture
def cli_args(tmp_path):
    return [
        "--host",
        "github",
        "--user-name",
        "testuser",
        "--target-dir",
        str(tmp_path),
        "--config-path",
        str(tmp_path / "pyproject.toml"),
    ]


# Test parsing and command execution
@patch("git_mirror.router.route_to_command")
@patch.dict(os.environ, {"GITHUB_ACCESS_TOKEN": "testtoken"})
def test_cli_clone_all(mock_main_github, cli_args):
    argv = ["clone-all"] + cli_args
    with patch("sys.argv", ["git_mirror"] + argv):
        assert main() == 0
    mock_main_github.assert_called_once_with(
        command="clone-all",
        config_path=ANY,
        host="github",
        include_forks=False,
        include_private=False,
        target_dir=ANY,
        token="testtoken",
        pypi_owner_name=None,
        user_name="testuser",
        domain="",
        group_id=0,
    )


# Test missing GitHub token
@patch("git_mirror.router.route_to_command")
@patch.dict(os.environ, clear=True)
def test_cli_missing_github_token(mock_main_github, cli_args):
    argv = ["clone-all"] + cli_args
    with patch("sys.argv", ["prog"] + argv):
        assert main() == 1
    mock_main_github.assert_not_called()


# Test configuration loading from TOML
@patch("git_mirror.router.route_to_command")
@patch.dict(os.environ, {"GITHUB_ACCESS_TOKEN": "testtoken"})
def test_cli_config_loading(mock_main_github, tmp_path):
    config_path = tmp_path / "pyproject.toml"
    config_content = tomlkit.dumps(
        {"tool": {"git-mirror": {"github": {"user_name": "tomluser", "target_dir": str(tmp_path)}}}}
    )
    config_path.write_text(config_content, encoding="utf-8")

    argv = ["clone-all", "--host", "github", "--config-path", str(config_path)]
    with patch("sys.argv", ["git_mirror"] + argv):
        assert main() == 0
    mock_main_github.assert_called_once()
