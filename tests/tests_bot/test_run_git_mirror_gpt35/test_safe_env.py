from pathlib import Path
from unittest.mock import mock_open, patch

from git_mirror import safe_env


def test_load_env_prefers_home_env_when_token_present():
    fake_home_env = Path("/fake/home/.env")

    with (
        patch("git_mirror.safe_env.LOADED", False),
        patch("git_mirror.safe_env.Path.home", return_value=Path("/fake/home")),
        patch("git_mirror.safe_env.load_dotenv") as mock_load_dotenv,
        patch("builtins.open", mock_open(read_data="GITHUB_ACCESS_TOKEN=secret\n")),
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "is_file", return_value=True),
    ):
        safe_env.load_env()

    mock_load_dotenv.assert_called_once_with(fake_home_env)


def test_load_env_falls_back_to_default_lookup_when_home_env_has_no_expected_tokens():
    with (
        patch("git_mirror.safe_env.LOADED", False),
        patch("git_mirror.safe_env.Path.home", return_value=Path("/fake/home")),
        patch("git_mirror.safe_env.load_dotenv") as mock_load_dotenv,
        patch("builtins.open", mock_open(read_data="UNRELATED=value\n")),
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "is_file", return_value=True),
    ):
        safe_env.load_env()

    mock_load_dotenv.assert_called_once_with()


def test_load_env_reports_errors_and_keeps_going():
    with (
        patch("git_mirror.safe_env.LOADED", False),
        patch("git_mirror.safe_env.Path.home", side_effect=RuntimeError("boom")),
        patch("git_mirror.safe_env.console.print") as mock_print,
    ):
        safe_env.load_env()

    assert mock_print.call_count == 2
