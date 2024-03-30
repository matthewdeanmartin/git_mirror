from unittest.mock import MagicMock, patch

import httpx
import pytest

from git_mirror.version_check import call_pypi_with_version_check, display_version_check_message


@pytest.fixture
def mock_response():
    mock = MagicMock()
    mock.json.return_value = {"info": {"version": "2.0.0"}}
    return mock


def test_version_check_new_version_available(mock_response):
    with patch("httpx.get", return_value=mock_response):
        available, new_version = call_pypi_with_version_check("your_package", "1.0.0")
        assert available is True
        assert str(new_version) == "2.0.0"


def test_version_check_current_version_is_latest(mock_response):
    with patch("httpx.get", return_value=mock_response):
        available, new_version = call_pypi_with_version_check("your_package", "2.0.0")
        assert available is False
        assert str(new_version) == "2.0.0"


def test_http_error_handling():
    with patch("httpx.get", side_effect=httpx.HTTPError("Mocked error")):
        with pytest.raises(httpx.HTTPError):
            call_pypi_with_version_check("your_package", "1.0.0")


def test_display_version_check_message_new_version(capsys, mock_response):
    with patch("httpx.get", return_value=mock_response):
        with patch("git_mirror.__about__.__version__", "1.0.0"):
            display_version_check_message()
            captured = capsys.readouterr()
            assert "A newer version of git_mirror is available on PyPI. Upgrade to 2.0.0." in captured.out
