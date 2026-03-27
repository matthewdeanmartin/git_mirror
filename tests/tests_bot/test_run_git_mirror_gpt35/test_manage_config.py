from unittest.mock import patch

import tomlkit

from git_mirror.manage_config import ConfigData, ConfigManager, _prompt_for_target_dir, read_config


def test_read_config_returns_value_from_file(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text('key1 = "value1"\nkey2 = 42\n', encoding="utf-8")

    assert read_config(config_path, "key1") == "value1"


def test_prompt_for_target_dir_reprompts_with_new_string_value(tmp_path):
    missing_dir = tmp_path / "missing"
    replacement_dir = tmp_path / "replacement"
    replacement_dir.mkdir()

    with (
        patch("git_mirror.manage_config.inquirer.prompt") as mock_prompt,
        patch("git_mirror.manage_config.os.makedirs") as mock_makedirs,
    ):
        mock_prompt.side_effect = [
            {"create_target_dir": False},
            {"target_dir": str(replacement_dir)},
        ]

        result = _prompt_for_target_dir(str(missing_dir))

    assert result == replacement_dir
    mock_makedirs.assert_not_called()


def test_load_config_supports_legacy_keys_and_creates_missing_target_dir(tmp_path):
    config_path = tmp_path / "git_mirror.toml"
    target_dir = tmp_path / "repos"
    global_template_dir = tmp_path / "templates"
    config_path.write_text(
        tomlkit.dumps(
            {
                "tool": {
                    "git-mirror": {
                        "github": {
                            "type": "github",
                            "url": "https://ghe.example.com/api/v3",
                            "user_name": "octocat",
                            "target_dir": str(target_dir),
                            "include_private": True,
                            "include_forks": True,
                            "group_id": 99,
                            "global_template_dir": str(global_template_dir),
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(config_path=config_path)
    with patch("git_mirror.manage_config.os.makedirs") as mock_makedirs:
        config = manager.load_config("github")

    assert config == ConfigData(
        host_name="github",
        host_type="github",
        host_url="https://ghe.example.com/api/v3",
        user_name="octocat",
        target_dir=target_dir,
        include_private=True,
        include_forks=True,
        group_id=99,
        global_template_dir=global_template_dir,
    )
    mock_makedirs.assert_called_once_with(target_dir, exist_ok=True)


def test_doctor_returns_true_for_valid_github_config(tmp_path):
    config_path = tmp_path / "git_mirror.toml"
    target_dir = tmp_path / "repos"
    target_dir.mkdir()
    config_path.write_text(
        tomlkit.dumps(
            {
                "tool": {
                    "git-mirror": {
                        "github": {
                            "host_type": "github",
                            "host_url": "https://api.github.com",
                            "user_name": "octocat",
                            "target_dir": str(target_dir),
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(config_path=config_path)
    with (
        patch.dict("os.environ", {"GITHUB_ACCESS_TOKEN": "token"}, clear=True),
        patch("git_mirror.manage_config.pat_init.get_authenticated_user", return_value={"login": "octocat"}),
        patch("git_mirror.manage_config._render_checks") as mock_render_checks,
        patch("git_mirror.manage_config.console.print") as mock_print,
    ):
        result = manager.doctor(host="github")

    assert result is True
    mock_render_checks.assert_called_once()
    mock_print.assert_called_with("Setup looks good. Try `git_mirror list-repos --host github` or the host you configured.")


def test_doctor_returns_false_when_token_username_differs_from_config(tmp_path):
    config_path = tmp_path / "git_mirror.toml"
    target_dir = tmp_path / "repos"
    target_dir.mkdir()
    config_path.write_text(
        tomlkit.dumps(
            {
                "tool": {
                    "git-mirror": {
                        "github": {
                            "host_type": "github",
                            "host_url": "https://api.github.com",
                            "user_name": "expected-user",
                            "target_dir": str(target_dir),
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(config_path=config_path)
    with (
        patch.dict("os.environ", {"GITHUB_ACCESS_TOKEN": "token"}, clear=True),
        patch("git_mirror.manage_config.pat_init.get_authenticated_user", return_value={"login": "actual-user"}),
        patch("git_mirror.manage_config._render_checks") as mock_render_checks,
        patch("git_mirror.manage_config.console.print") as mock_print,
    ):
        result = manager.doctor(host="github")

    rendered_checks = mock_render_checks.call_args.args[1]

    assert result is False
    assert any(check.name == "Configured username" and not check.ok for check in rendered_checks)
    mock_print.assert_called_with("Setup needs attention. Fix the failing checks above, then rerun `git_mirror doctor`.")


def test_initialize_config_writes_config_and_runs_doctor(tmp_path):
    config_path = tmp_path / "git_mirror.toml"
    target_dir = tmp_path / "repos"
    config_section = ConfigData(
        host_name="github",
        host_type="github",
        host_url="https://api.github.com",
        user_name="octocat",
        target_dir=target_dir,
        include_private=True,
        include_forks=False,
        group_id=0,
        global_template_dir=tmp_path / "templates",
    )
    manager = ConfigManager(config_path=config_path)

    with (
        patch("git_mirror.manage_config.ask_for_section", return_value=config_section),
        patch("git_mirror.manage_config.input", return_value="n"),
        patch.object(manager, "doctor", return_value=True) as mock_doctor,
    ):
        already_configured = manager.initialize_config()

    saved_config = tomlkit.loads(config_path.read_text(encoding="utf-8"))
    github_config = saved_config["tool"]["git-mirror"]["github"]
    assert already_configured == []
    assert github_config["user_name"] == "octocat"
    assert github_config["target_dir"] == str(target_dir)
    assert github_config["global_template_dir"] == str(tmp_path / "templates")
    mock_doctor.assert_called_once_with("github", attempt_token_setup=True)
    assert target_dir.exists()

