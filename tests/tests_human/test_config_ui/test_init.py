from pathlib import Path
from unittest.mock import mock_open, patch

from git_mirror.manage_config import ConfigManager

# not going to work without a real config file.
# @patch('builtins.open', new_callable=mock_open)
# @patch('os.makedirs')
# @patch('builtins.input', side_effect=['y', 'n'])  # Simulate user adding one host then stopping
# @patch('git_mirror.manage_config.ask_for_section', return_value=ConfigData(
#         host_name="github",
#         host_type="github",
#         host_url="https://api.github.com",
#         user_name="testuser",
#         target_dir=Path("/path/to/repo"),
#         pypi_owner_name="testowner",
#         include_private=True,
#         include_forks=False,
#         group_id=123,
#         global_template_dir=None
#     ))  # Provide a mock return value
# def test_initialize_config_no_existing(mock_ask_for_section, mock_input, mock_makedirs, mock_file):
#     config_manager = ConfigManager(Path('/path/to/config.toml'))
#     already_configured = config_manager.initialize_config()
#
#     # Verify file was written to, directories created as needed, etc.
#     mock_file.assert_called_with(Path('/path/to/config.toml'), 'w', encoding='utf-8')
#     # Further assertions based on expected behavior


@patch("builtins.open", new_callable=mock_open, read_data='tool = {"git-mirror": {}}')
@patch("git_mirror.manage_config.tomlkit.dumps", return_value="")
@patch(
    "git_mirror.manage_config.input", side_effect=["n"]
)  # Simulate user input to not add another host after the first
@patch("git_mirror.manage_config.ask_for_section", return_value=None)  # Simulate no more sections to add
@patch(
    "git_mirror.manage_config.ConfigManager.load_if_exists", return_value=({}, {"gitlab": {}})
)  # Simulate existing gitlab config
@patch("git_mirror.manage_config.os.makedirs")
def test_initialize_config_already_done(
    mock_makedirs, mock_load_if_exists, mock_ask_for_section, mock_input, mock_toml_dumps, mock_file
):
    config_manager = ConfigManager(config_path=Path("/path/to/config.toml"))

    # Execute the method under test
    already_configured = config_manager.initialize_config()

    # Assertions to verify behavior
    mock_ask_for_section.assert_called()  # Verify ask_for_section was called
    assert "gitlab" in already_configured  # Verify gitlab is recognized as already configured
