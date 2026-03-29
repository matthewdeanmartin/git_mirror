import os
import getpass
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from git_mirror.pat_init import (
    get_authenticated_user,
    check_pat_validity,
    _save_pat,
    setup_github_pat,
)

@pytest.fixture
def mock_httpx_get():
    with patch("httpx.get") as mock_get:
        yield mock_get

def test_get_authenticated_user_success(mock_httpx_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"login": "testuser"}
    mock_httpx_get.return_value = mock_response

    result = get_authenticated_user("valid_token")
    assert result == {"login": "testuser"}
    mock_httpx_get.assert_called_once()

def test_get_authenticated_user_failure(mock_httpx_get):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_httpx_get.return_value = mock_response

    result = get_authenticated_user("invalid_token")
    assert result is None

def test_get_authenticated_user_request_error(mock_httpx_get):
    mock_httpx_get.side_effect = httpx.RequestError("error")

    result = get_authenticated_user("token")
    assert result is None

def test_check_pat_validity_true(mock_httpx_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"login": "testuser"}
    mock_httpx_get.return_value = mock_response

    assert check_pat_validity("valid_token") is True

def test_check_pat_validity_false(mock_httpx_get):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_httpx_get.return_value = mock_response

    assert check_pat_validity("invalid_token") is False

@patch("git_mirror.pat_init.set_key")
@patch("pathlib.Path.home")
def test_save_pat_global(mock_home, mock_set_key):
    mock_home.return_value = Path("/home/user")
    with patch.dict(os.environ, {}, clear=True):
        result = _save_pat("g", "GITHUB_ACCESS_TOKEN", "new_token")
        assert result is True
        mock_set_key.assert_called_once_with(Path("/home/user") / ".env", "GITHUB_ACCESS_TOKEN", "new_token")
        assert os.environ["GITHUB_ACCESS_TOKEN"] == "new_token"

@patch("git_mirror.pat_init.set_key")
def test_save_pat_local(mock_set_key):
    with patch.dict(os.environ, {}, clear=True):
        result = _save_pat("l", "GITHUB_ACCESS_TOKEN", "new_token")
        assert result is True
        mock_set_key.assert_called_once_with(Path(".env"), "GITHUB_ACCESS_TOKEN", "new_token")
        assert os.environ["GITHUB_ACCESS_TOKEN"] == "new_token"

def test_save_pat_invalid():
    result = _save_pat("invalid", "GITHUB_ACCESS_TOKEN", "new_token")
    assert result is False

@patch("git_mirror.pat_init.env_info")
@patch("git_mirror.pat_init.find_dotenv")
@patch("git_mirror.pat_init.load_dotenv")
@patch("git_mirror.pat_init.check_pat_validity")
@patch("os.getenv")
def test_setup_github_pat_existing_valid(mock_getenv, mock_check_valid, mock_load, mock_find, mock_env_info):
    mock_getenv.return_value = "existing_token"
    mock_check_valid.return_value = True

    result = setup_github_pat()
    assert result == "existing_token"



@patch("git_mirror.pat_init.env_info")
@patch("git_mirror.pat_init.find_dotenv")
@patch("git_mirror.pat_init.load_dotenv")
@patch("git_mirror.pat_init.check_pat_validity")
@patch("os.getenv")
@patch("getpass.getpass")
def test_setup_github_pat_new_invalid(mock_getpass, mock_getenv, mock_check_valid, mock_load, mock_find, mock_env_info):
    mock_getenv.return_value = None
    mock_check_valid.return_value = False
    mock_getpass.return_value = "invalid_token"

    result = setup_github_pat()
    assert result is None

@patch("git_mirror.pat_init.env_info")
@patch("git_mirror.pat_init.find_dotenv")
@patch("git_mirror.pat_init.load_dotenv")
@patch("git_mirror.pat_init.check_pat_validity")
@patch("os.getenv")
@patch("getpass.getpass")
@patch("builtins.input")
@patch("git_mirror.pat_init._save_pat")
def test_setup_github_pat_save_fails(mock_save, mock_input, mock_getpass, mock_getenv, mock_check_valid, mock_load, mock_find, mock_env_info):
    mock_getenv.return_value = None
    mock_check_valid.side_effect = [False, True]
    mock_getpass.return_value = "new_token"
    mock_input.return_value = "g"
    mock_save.return_value = False

    result = setup_github_pat()
    assert result is None
