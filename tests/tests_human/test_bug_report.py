from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from git_mirror.bug_report import BugReporter
from tests.env_util import temporary_env_var


@pytest.fixture
def mock_github():
    with patch("github.Github") as mock:
        # Mock get_user to return a mock user object
        mock_user = MagicMock()
        mock.return_value.get_user.return_value = mock_user
        mock_repo = MagicMock()
        mock.return_value.get_repo.return_value = mock_repo
        yield mock


def test_mask_secrets(mock_github):
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")

    # Mock environment variables
    with temporary_env_var("GITHUB_ACCESS_TOKEN", "secret_token"):
        masked_text = reporter.mask_secrets("This contains a secret_token and should be masked.")
        assert "****" in masked_text
        assert "secret_token" not in masked_text


def test_report_issue_failure(mock_github):
    # Given
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")
    issue_title = "Test Issue Failure"
    issue_body = "This should fail."

    # When
    with patch.object(
        reporter.repo, "create_issue", side_effect=GithubException(404, "Not found")
    ) as mock_create_issue:
        result = reporter.report_issue(issue_title, issue_body)

    # Then
    mock_create_issue.assert_called_once_with(title=issue_title, body=issue_body)
    assert result is None, "Expected the returned value to be None due to failure in creating an issue"


def test_find_existing_issue_by_title_and_creator_found(mock_github):
    # Given
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")
    issue_title = "Existing Issue"
    mock_issue = MagicMock()
    mock_issue.title = issue_title
    mock_issue.user.login = reporter.user.login  # Simulating the issue was created by the same user

    # Mock `get_issues` to return a list containing our mock issue
    with patch.object(reporter.repo, "get_issues", return_value=[mock_issue]) as mock_get_issues:
        # When
        result = reporter.find_existing_issue_by_title_and_creator(issue_title)

    # Then
    mock_get_issues.assert_called_once_with(state="all")
    assert result == mock_issue, "Expected to find the mock issue that matches the title and creator"


def test_find_existing_issue_by_title_and_creator_not_found(mock_github):
    # Given
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")
    issue_title = "Nonexistent Issue"
    mock_issue = MagicMock()
    mock_issue.title = "Some Other Issue"
    mock_issue.user.login = "other_user"

    # Mock `get_issues` to return a list that does not contain a matching issue
    with patch.object(reporter.repo, "get_issues", return_value=[mock_issue]) as mock_get_issues:
        # When
        result = reporter.find_existing_issue_by_title_and_creator(issue_title)

    # Then
    mock_get_issues.assert_called_once_with(state="all")
    assert result is None, "Expected not to find an issue, should return None"


def test_handle_exception_and_report_user_agrees_no_existing_issue(mock_github):
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")
    exc_type, exc_value, exc_traceback = Exception, Exception("Test exception"), None

    # Mocks
    with (
        patch("traceback.format_exception", return_value=["Traceback details"]),
        patch("builtins.input", return_value="yes"),
        patch.object(reporter, "find_existing_issue_by_title_and_creator", return_value=None) as mock_find_issue,
        patch.object(
            reporter, "report_issue", return_value=MagicMock(html_url="http://issue_url")
        ) as mock_report_issue,
    ):
        # Action
        reporter.handle_exception_and_report(exc_type, exc_value, exc_traceback)

    # Assertions
    mock_find_issue.assert_called_once()
    mock_report_issue.assert_called_once()


def test_handle_exception_and_report_user_declines(mock_github):
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")
    exc_type, exc_value, exc_traceback = Exception, Exception("Test exception"), None

    # Mocks
    with (
        patch("traceback.format_exception", return_value=["Traceback details"]),
        patch("builtins.input", return_value="no"),
        patch.object(reporter, "report_issue") as mock_report_issue,
    ):
        # Action
        reporter.handle_exception_and_report(exc_type, exc_value, exc_traceback)

    # Assertions
    mock_report_issue.assert_not_called()


def test_handle_exception_and_report_existing_issue_found(mock_github):
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")
    exc_type, exc_value, exc_traceback = Exception, Exception("Test exception"), None

    # Mocks
    with (
        patch("traceback.format_exception", return_value=["Traceback details"]),
        patch.object(reporter, "find_existing_issue_by_title_and_creator", return_value=MagicMock()) as mock_find_issue,
        patch.object(reporter, "report_issue") as mock_report_issue,
    ):
        # Action
        reporter.handle_exception_and_report(exc_type, exc_value, exc_traceback)

    # Assertions
    mock_find_issue.assert_called_once()
    mock_report_issue.assert_not_called()
