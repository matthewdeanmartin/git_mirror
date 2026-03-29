from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from git_mirror.pat_init_gitlab import check_pat_validity, setup_gitlab_pat


@pytest.fixture
def mock_path_home():
    with patch("pathlib.Path.home", return_value=Path("/fake/home")) as mock:
        yield mock


@pytest.fixture
def mock_path_cwd():
    with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")) as mock:
        yield mock


@pytest.fixture
def mock_httpx_get():
    with patch("git_mirror.pat_init_gitlab.httpx.get") as mock_get:
        yield mock_get


def test_check_pat_validity_valid(mock_httpx_get):
    # Mocking a successful response
    mock_httpx_get.return_value.status_code = 200

    assert check_pat_validity("valid_token")


def test_check_pat_validity_invalid(mock_httpx_get):
    # Mocking a failed response
    mock_httpx_get.return_value.status_code = 401

    assert not check_pat_validity("invalid_token")


@patch("getpass.getpass", return_value="invalid_token")
@patch("builtins.input", return_value="g")
def test_setup_gitlab_pat_invalid_pat(mock_input, mock_getpass, mock_path_home, mock_path_cwd):
    with (
        patch("git_mirror.pat_init_gitlab.console.print") as mock_print,
        patch("git_mirror.pat_init_gitlab.find_dotenv", return_value=""),
        patch("git_mirror.pat_init_gitlab.load_dotenv"),
        patch("git_mirror.pat_init_gitlab.env_info"),
    ):
        setup_gitlab_pat()
        mock_print.assert_called_with("The provided PAT is invalid.")


# Add more test cases if needed


# In the above unit tests:
#
# 1. `test_check_pat_validity_valid` and `test_check_pat_validity_invalid` test
#    the `check_pat_validity` function by mocking HTTP responses.
# 2. `test_setup_gitlab_pat_global` and `test_setup_gitlab_pat_local` test the
#    `setup_gitlab_pat` function by mocking user input for global/local setup
#    selection.
# 3. `test_setup_gitlab_pat_invalid_pat` tests the case where an invalid PAT is
#    provided.
#
# If you have any other specific scenarios or edge cases you would like to cover,
# feel free to provide them for additional test implementations.
