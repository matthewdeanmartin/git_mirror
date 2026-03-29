from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from git_mirror.__main__ import handle_repos, validate_host_token, validate_parse_args
from git_mirror.manage_config import ConfigData

# Let's start by writing a pytest unit test to cover the `validate_host_token`
# function in `__main__.py`. We will mock necessary dependencies and test the
# different branches of logic based on the input arguments.


# This test mocks the dependencies and covers different scenarios for the
# `validate_host_token` function. We are testing the logic when the host is
# "selfhosted" and "github", as well as handling scenarios where config data is
# not present or tokens need to be setup.
#
# Next unit test, or "No more unit tests"?
# Next, I will write a pytest unit test to cover the `validate_parse_args`
# function in `__main__.py`. This test will focus on verifying the behavior of the
# function when arguments are not provided, and it needs to read from the config
# file.


# This test covers different scenarios for the `validate_parse_args` function by
# mocking the dependencies and checking the behavior when arguments are not
# provided but need to be read from the config file.
#
# Would you like to see the next unit test, or should I stop here with "No more
# unit tests"?
# Certainly! For the next unit test, I will cover the `main` function from
# `__main__.py`. This test will focus on testing the logic of determining the
# program based on the input arguments and handling the case when the user input
# command is in the available choices.


# This test simulates different scenarios for the `main` function in
# `__main__.py`, including determining the program based on the input arguments
# and handling user input commands.
#
# Next unit test, or should I conclude with "No more unit tests"?
# Let's proceed with writing a pytest unit test for the `handle_repos` function in
# `__main__.py`. This test will focus on verifying the correct routing of
# repositories based on the provided arguments and mocked dependencies.


def test_handle_repos(tmp_path):
    # Mock arguments and dependencies
    mock_args = MagicMock()
    mock_args.host = "github"
    mock_args.command = "list-repos"
    mock_args.user_name = "test_user"
    mock_args.target_dir = Path("/test/directory")
    mock_args.include_private = True
    mock_args.include_forks = False
    mock_args.config_path = tmp_path / "config.toml"
    mock_args.dry_run = False
    mock_args.verbose = 1
    mock_args.yes = False

    with (
        patch("git_mirror.__main__.validate_host_token") as mock_validate_host_token,
        patch("git_mirror.__main__.validate_parse_args") as mock_validate_parse_args,
        patch("git_mirror.__main__.router.route_repos") as mock_route_repos,
    ):
        mock_validate_host_token.return_value = "mock_token", 0
        mock_validate_parse_args.return_value = "test_domain", 123, 0

        # Call the function
        handle_repos(mock_args)

        # Validate calls to route_repos
        mock_route_repos.assert_called_once_with(
            command="list-repos",
            user_name="test_user",
            target_dir=Path("/test/directory"),
            token="mock_token",
            host="github",
            include_private=True,
            include_forks=False,
            config_path=tmp_path / "config.toml",
            domain="test_domain",
            group_id=123,
            logging_level=1,
            dry_run=False,
            prompt_for_changes=True,
        )


def test_handle_repos_exits_when_validate_host_token_fails():
    mock_args = MagicMock()
    mock_args.host = "github"
    mock_args.command = "list-repos"
    mock_args.config_path = Path("config.toml")

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
    args = MagicMock()
    args.command = "doctor"
    args.config_path = Path("git_mirror.toml")

    token, return_value = validate_host_token(args)

    assert token is None
    assert return_value == 0


def test_validate_host_token_selfhosted_github_uses_selfhosted_setup():
    args = MagicMock()
    args.command = "list-repos"
    args.host = "selfhosted"
    args.config_path = Path("git_mirror.toml")

    config = ConfigData(
        host_name="selfhosted",
        host_type="github",
        host_url="https://ghe.example.com/api/v3",
        user_name="octocat",
        target_dir=Path("repos"),
    )

    with (
        patch("git_mirror.__main__.ConfigManager") as mock_manager_cls,
        patch.dict("os.environ", {}, clear=True),
        patch("git_mirror.__main__.pat_init.setup_github_pat", return_value="selfhosted-token") as mock_setup,
    ):
        mock_manager_cls.return_value.load_config.return_value = config
        token, return_value = validate_host_token(args)

    assert token == "selfhosted-token"
    assert return_value == 0
    mock_setup.assert_called_once_with(
        env_var="SELFHOSTED_ACCESS_TOKEN",
        api_url="https://ghe.example.com/api/v3",
        host_label="self-hosted GitHub",
    )


def test_validate_parse_args_reads_values_from_config():
    args = MagicMock()
    args.user_name = None
    args.target_dir = None
    args.first_time_init = False
    args.command = "list-repos"
    args.config_path = MagicMock()
    args.config_path.exists.return_value = True
    args.host = "selfhosted"
    args.include_private = False
    args.include_forks = False
    args.use_github = False
    args.domain = None
    args.group_id = None
    args.global_template_dir = None

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

    with patch("git_mirror.__main__.ConfigManager") as mock_manager_cls:
        mock_manager_cls.return_value.load_config.return_value = config
        domain, group_id, return_value = validate_parse_args(args)

    assert (domain, group_id, return_value) == ("https://gitlab.example.com", 55, 0)
    assert args.user_name == "octocat"
    assert args.target_dir == Path("repos")
    assert args.include_private is True
    assert args.include_forks is True
    assert args.global_template_dir == Path("templates")


def test_validate_parse_args_requires_host_when_config_lookup_needed():
    args = MagicMock()
    args.user_name = None
    args.target_dir = None
    args.first_time_init = False
    args.command = "list-repos"
    args.config_path = Path("git_mirror.toml")
    args.host = None

    domain, group_id, return_value = validate_parse_args(args)

    assert (domain, group_id, return_value) == ("", 0, 1)


if __name__ == "__main__":
    pytest.main()

# This unit test covers the `handle_repos` function by mocking the necessary
# dependencies and verifying that the routing of repositories is done correctly
# based on the provided arguments.
#
# Would you like to see the next unit test, or should I conclude with "No more
# unit tests"?
