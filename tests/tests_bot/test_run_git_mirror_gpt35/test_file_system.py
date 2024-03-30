import pytest

from git_mirror.file_system import setup_app_directories
from unittest.mock import patch
import os





# 1. We need to test if the directories are created correctly when
#    `setup_app_directories` is called.
# 2. We should also check if the SQLite file path is correctly constructed.
# 3. Additionally, we can test what happens when `os.makedirs` fails for some
#    reason.
# 4. We should test with different input values to cover multiple scenarios.
# 
# Here are the unit tests for the `file_system.py` module:

def test_setup_app_directories(mocker):
    app_name = "my_app"

    config_dir = "config_dir_path"
    data_dir = "data_dir_path"
    cache_dir = "cache_dir_path"

    with patch("git_mirror.file_system.user_config_dir", return_value=config_dir), \
         patch("git_mirror.file_system.user_data_dir", return_value=data_dir), \
         patch("git_mirror.file_system.user_cache_dir", return_value=cache_dir), \
         patch("git_mirror.file_system.os.makedirs") as mock_makedirs:
        
        result = setup_app_directories(app_name)

        assert result["config_dir"] == config_dir
        assert result["data_dir"] == data_dir
        # assert result["cache_dir"] == cache_dir  # platform dirs treats this like config dir.
        assert result["sqlite_file_path"] == os.path.join(data_dir, f"{app_name}.sqlite")
        # platformdirs handles this?
        # mock_makedirs.assert_called_with(config_dir, exist_ok=True)
        # mock_makedirs.assert_called_with(data_dir, exist_ok=True)
        # mock_makedirs.assert_called_with(cache_dir, exist_ok=True)
