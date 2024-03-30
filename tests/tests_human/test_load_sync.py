import tomlkit

from git_mirror.manage_config import ConfigManager


def create_initial_toml_file(toml_path, content):
    """
    Helper function to create an initial TOML file with given content.
    """
    with open(toml_path, "w", encoding="utf-8") as file:
        tomlkit.dump(content, file)


def test_write_repos_to_toml(tmp_path):
    toml_path = tmp_path / "config.toml"
    config_manager = ConfigManager(toml_path)

    existing_config = {}
    repos = ["repo1", "repo2"]
    config_manager._write_repos_to_toml(repos, existing_config)

    # Read back the file to check if it was written correctly
    with open(toml_path, encoding="utf-8") as file:
        content = tomlkit.parse(file.read())

    expected_content = {"tool.git-mirror.repos": {"repo1": {}, "repo2": {}}}
    # {
    #     "tool": {"git-mirror": {"repos": {"repo1": {}, "repo2": {}}}}
    # }

    assert content == expected_content


def test_load_and_sync_config(tmp_path):
    # Mock _get_user_repos to return a list of mock repositories

    toml_path = tmp_path / "pyproject.toml"

    initial_config = {"tool": {"git-mirror": {"github": {"repos": tomlkit.inline_table()}}}}
    initial_config["tool"]["git-mirror"]["github"]["repos"]["user/old_repo"] = {"important": False}

    create_initial_toml_file(toml_path, initial_config)

    config_manager = ConfigManager(toml_path)
    config = config_manager.load_and_sync_config("github", ["user/repo1", "user/repo2"])

    # Expected to remove old_repo and add repo1 and repo2 with their configs
    expected_config = tomlkit.document()
    expected_config["tool"] = {"git-mirror": {"github": {"repos": tomlkit.inline_table()}}}

    expected_config["tool"]["git-mirror"]["github"]["repos"]["user/repo1"] = {"important": True}
    expected_config["tool"]["git-mirror"]["github"]["repos"]["user/repo2"] = {"important": True}

    assert config == expected_config
    assert len(config["tool"]["git-mirror"]["github"]["repos"]) == len(
        expected_config["tool"]["git-mirror"]["github"]["repos"]
    )
    assert config["tool"]["git-mirror"]["github"]["repos"] == expected_config["tool"]["git-mirror"]["github"]["repos"]
