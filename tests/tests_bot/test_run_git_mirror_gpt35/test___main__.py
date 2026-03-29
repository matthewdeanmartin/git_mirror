from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from git_mirror.__main__ import handle_repos, main, validate_host_token, validate_parse_args
from git_mirror.manage_config import ConfigData


def test_handle_repos_routes_to_repo_handler():
    config_path = Path("tests") / "fixtures-config.toml"
    mock_args = SimpleNamespace(
        host="github",
        command="list-repos",
        user_name="test_user",
        target_dir=Path("/test/directory"),
        include_private=True,
        include_forks=False,
        config_path=config_path,
        dry_run=False,
        verbose=1,
        yes=False,
    )

    with (
        patch("git_mirror.__main__.validate_host_token", return_value=("mock_token", 0)),
        patch("git_mirror.__main__.validate_parse_args", return_value=("test_domain", 123, 0)),
        patch("git_mirror.router.route_repos") as mock_route_repos,
    ):
        handle_repos(mock_args)

    mock_route_repos.assert_called_once_with(
        command="list-repos",
        user_name="test_user",
        target_dir=Path("/test/directory"),
        token="mock_token",
        host="github",
        include_private=True,
        include_forks=False,
        config_path=config_path,
        domain="test_domain",
        group_id=123,
        logging_level=1,
        dry_run=False,
        prompt_for_changes=True,
    )


def test_handle_repos_exits_when_validate_host_token_fails():
    mock_args = SimpleNamespace(host="github", command="list-repos", config_path=Path("config.toml"))

    with (
        patch("git_mirror.__main__.validate_host_token", return_value=("", 2)),
        patch("git_mirror.__main__.validate_parse_args") as mock_validate_parse_args,
        patch("git_mirror.__main__.sys.exit", side_effect=SystemExit(2)) as mock_exit,
    ):
        with pytest.raises(SystemExit, match="2"):
            handle_repos(mock_args)

    mock_exit.assert_called_once_with(2)
    mock_validate_parse_args.assert_not_called()


def test_validate_host_token_returns_none_for_doctor_without_host():
    args = SimpleNamespace(command="doctor", config_path=Path("git_mirror.toml"))

    token, return_value = validate_host_token(args)

    assert token is None
    assert return_value == 0


def test_validate_host_token_selfhosted_github_uses_selfhosted_setup():
    args = SimpleNamespace(command="list-repos", host="selfhosted", config_path=Path("git_mirror.toml"))
    config = ConfigData(
        host_name="selfhosted",
        host_type="github",
        host_url="https://ghe.example.com/api/v3",
        user_name="octocat",
        target_dir=Path("repos"),
    )

    with (
        patch("git_mirror.__main__._get_config_manager") as mock_manager_factory,
        patch.dict("os.environ", {}, clear=True),
        patch("git_mirror.pat_init.setup_github_pat", return_value="selfhosted-token") as mock_setup,
    ):
        mock_manager_factory.return_value.load_config.return_value = config
        token, return_value = validate_host_token(args)

    assert token == "selfhosted-token"
    assert return_value == 0
    mock_setup.assert_called_once_with(
        env_var="SELFHOSTED_ACCESS_TOKEN",
        api_url="https://ghe.example.com/api/v3",
        host_label="self-hosted GitHub",
    )


def test_validate_parse_args_reads_values_from_config():
    args = SimpleNamespace(
        user_name=None,
        target_dir=None,
        first_time_init=False,
        command="list-repos",
        config_path=MagicMock(),
        host="selfhosted",
        include_private=False,
        include_forks=False,
        use_github=False,
        domain=None,
        group_id=None,
        global_template_dir=None,
    )
    args.config_path.exists.return_value = True

    config = ConfigData(
        host_name="selfhosted",
        host_type="gitlab",
        host_url="https://gitlab.example.com",
        user_name="octocat",
        target_dir=Path("repos"),
        include_private=True,
        include_forks=True,
        group_id=55,
        global_template_dir=Path("templates"),
    )

    with patch("git_mirror.__main__._get_config_manager") as mock_manager_factory:
        mock_manager_factory.return_value.load_config.return_value = config
        domain, group_id, return_value = validate_parse_args(args)

    assert (domain, group_id, return_value) == ("https://gitlab.example.com", 55, 0)
    assert args.user_name == "octocat"
    assert args.target_dir == Path("repos")
    assert args.include_private is True
    assert args.include_forks is True
    assert args.global_template_dir == Path("templates")


def test_validate_parse_args_requires_host_when_config_lookup_needed():
    args = SimpleNamespace(
        user_name=None,
        target_dir=None,
        first_time_init=False,
        command="list-repos",
        config_path=Path("git_mirror.toml"),
        host=None,
    )

    domain, group_id, return_value = validate_parse_args(args)

    assert (domain, group_id, return_value) == ("", 0, 1)


def test_help_path_does_not_install_requests_cache_or_check_versions():
    with (
        patch("git_mirror.__main__._install_requests_cache") as mock_install_cache,
        patch("git_mirror.__main__.validate_host_token", return_value=(None, 0)) as mock_validate_host_token,
        patch("git_mirror.version_check.display_version_check_message") as mock_version_check,
    ):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])

    assert exc_info.value.code == 0
    mock_install_cache.assert_not_called()
    mock_validate_host_token.assert_not_called()
    mock_version_check.assert_not_called()
