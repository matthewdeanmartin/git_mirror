import argparse
from unittest.mock import MagicMock, patch

from git_mirror.__main__ import validate_host_token, validate_parse_args
from git_mirror.manage_config import ConfigData


def test_validate_host_token_skips_token_requirements_for_doctor(tmp_path):
    args = argparse.Namespace(command="doctor", host=None, config_path=tmp_path / "git_mirror.toml")

    token, status = validate_host_token(args)

    assert token is None
    assert status == 0


def test_validate_host_token_sets_up_selfhosted_github_token_with_configured_url(tmp_path):
    config_path = tmp_path / "git_mirror.toml"
    config_path.write_text("", encoding="utf-8")
    config = ConfigData(
        host_name="selfhosted",
        host_type="github",
        host_url="https://ghe.example.com/api/v3",
        user_name="octocat",
        target_dir=tmp_path / "repos",
    )
    args = argparse.Namespace(command="list-repos", host="selfhosted", config_path=config_path)

    with (
        patch.dict("os.environ", {}, clear=True),
        patch("git_mirror.__main__._get_config_manager") as mock_manager_factory,
        patch("git_mirror.pat_init.setup_github_pat", return_value="token") as mock_setup,
    ):
        mock_manager_factory.return_value.load_config.return_value = config
        token, status = validate_host_token(args)

    assert token == "token"
    assert status == 0
    mock_setup.assert_called_once_with(
        env_var="SELFHOSTED_ACCESS_TOKEN",
        api_url="https://ghe.example.com/api/v3",
        host_label="self-hosted GitHub",
    )


def test_validate_parse_args_populates_missing_values_from_config(tmp_path):
    config_path = tmp_path / "git_mirror.toml"
    config_path.write_text("", encoding="utf-8")
    config = ConfigData(
        host_name="gitlab",
        host_type="gitlab",
        host_url="https://gitlab.example.com",
        user_name="octocat",
        target_dir=tmp_path / "repos",
        include_private=True,
        include_forks=True,
        group_id=42,
        global_template_dir=tmp_path / "templates",
    )
    args = argparse.Namespace(
        command="list-repos",
        host="gitlab",
        user_name="",
        target_dir=None,
        include_private=False,
        include_forks=False,
        use_github=False,
        domain="",
        group_id=0,
        first_time_init=False,
        config_path=config_path,
        global_template_dir=None,
    )

    with patch("git_mirror.__main__._get_config_manager") as mock_manager_factory:
        mock_manager_factory.return_value.load_config.return_value = config
        domain, group_id, status = validate_parse_args(args)

    assert status == 0
    assert domain == "https://gitlab.example.com"
    assert group_id == 42
    assert args.user_name == "octocat"
    assert args.target_dir == tmp_path / "repos"
    assert args.include_private is True
    assert args.include_forks is True
    assert args.global_template_dir == tmp_path / "templates"


def test_validate_parse_args_requires_host_when_config_lookup_is_needed(tmp_path):
    args = argparse.Namespace(
        command="list-repos",
        host="",
        user_name="",
        target_dir=None,
        include_private=False,
        include_forks=False,
        use_github=False,
        domain="",
        group_id=0,
        first_time_init=False,
        config_path=tmp_path / "git_mirror.toml",
    )

    with patch("git_mirror.__main__._get_console") as mock_console:
        domain, group_id, status = validate_parse_args(args)

    assert (domain, group_id, status) == ("", 0, 1)
    mock_console.return_value.print.assert_called_once_with("Please specify a host, eg. --host github or --host gitlab.")
