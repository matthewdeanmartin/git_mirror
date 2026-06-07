from unittest.mock import patch

from git_mirror.utils import credentials
from git_mirror.utils.credentials import TokenSource


def test_env_var_for_host():
    assert credentials.env_var_for_host("github") == "GITHUB_ACCESS_TOKEN"
    assert credentials.env_var_for_host("selfhosted") == "SELFHOSTED_ACCESS_TOKEN"
    assert credentials.env_var_for_host("anything-else") == "GITHUB_ACCESS_TOKEN"


def test_resolve_token_explicit_env_wins_over_keyring():
    with (
        patch.dict("os.environ", {"GITHUB_ACCESS_TOKEN": "env-token"}, clear=True),
        patch("git_mirror.utils.credentials.dotenv_get", return_value=None),
        patch("git_mirror.utils.credentials.keyring_get", return_value="keyring-token"),
    ):
        token, source = credentials.resolve_token("github")

    assert token == "env-token"
    assert source == TokenSource.ENV


def test_resolve_token_keyring_wins_over_dotenv_loaded_env():
    # Simulate safe_env having loaded the .env value into the process env.
    with (
        patch.dict("os.environ", {"GITHUB_ACCESS_TOKEN": "dotenv-token"}, clear=True),
        patch("git_mirror.utils.credentials.dotenv_get", return_value="dotenv-token"),
        patch("git_mirror.utils.credentials.keyring_get", return_value="keyring-token"),
    ):
        token, source = credentials.resolve_token("github")

    assert token == "keyring-token"
    assert source == TokenSource.KEYRING


def test_resolve_token_falls_back_to_dotenv():
    with (
        patch.dict("os.environ", {}, clear=True),
        patch("git_mirror.utils.credentials.dotenv_get", return_value="dotenv-token"),
        patch("git_mirror.utils.credentials.keyring_get", return_value=None),
    ):
        token, source = credentials.resolve_token("github")

    assert token == "dotenv-token"
    assert source == TokenSource.DOTENV


def test_resolve_token_missing():
    with (
        patch.dict("os.environ", {}, clear=True),
        patch("git_mirror.utils.credentials.dotenv_get", return_value=None),
        patch("git_mirror.utils.credentials.keyring_get", return_value=None),
    ):
        token, source = credentials.resolve_token("github")

    assert token is None
    assert source == TokenSource.MISSING


def test_set_token_writes_to_keyring_and_env():
    fake_kr = type("FakeKR", (), {"set_password": lambda self, s, u, p: None})()
    with (
        patch("git_mirror.utils.credentials.keyring", return_value=fake_kr),
        patch.dict("os.environ", {}, clear=True),
    ):
        assert credentials.set_token("github", "new-token") is True
        import os

        assert os.environ["GITHUB_ACCESS_TOKEN"] == "new-token"


def test_set_token_returns_false_without_keyring():
    with patch("git_mirror.utils.credentials.keyring", return_value=None):
        assert credentials.set_token("github", "x") is False


def test_migrate_dotenv_to_keychain_moves_token():
    captured = {}

    class FakeKR:
        def set_password(self, service, user, password):
            captured[user] = password

    with (
        patch("git_mirror.utils.credentials.resolve_token", return_value=("dotenv-token", TokenSource.DOTENV)),
        patch("git_mirror.utils.credentials.keyring", return_value=FakeKR()),
        patch.dict("os.environ", {}, clear=True),
    ):
        assert credentials.migrate_dotenv_to_keychain("github") is True
        assert captured["github"] == "dotenv-token"


def test_migrate_noop_when_already_in_keychain():
    with patch("git_mirror.utils.credentials.resolve_token", return_value=("t", TokenSource.KEYRING)):
        assert credentials.migrate_dotenv_to_keychain("github") is False
