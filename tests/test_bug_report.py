import pytest
from github import GithubException
from unittest.mock import patch, MagicMock
from git_mirror.bug_report import BugReporter
from tests.env_util import temporary_env_var


def test_mask_secrets():
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")

    # Mock environment variables
    with temporary_env_var("GITHUB_ACCESS_TOKEN", "secret_token"):
        masked_text = reporter.mask_secrets("This contains a secret_token and should be masked.")
        assert "****" in masked_text
        assert "secret_token" not in masked_text


def test_report_issue_failure():
    # Given
    reporter = BugReporter(token="dummy_token", repository_name="user/repo")
    issue_title = "Test Issue Failure"
    issue_body = "This should fail."

    # When
    with patch.object(reporter.repo, "create_issue",
                      side_effect=GithubException(404, "Not found")) as mock_create_issue:
        result = reporter.report_issue(issue_title, issue_body)

    # Then
    mock_create_issue.assert_called_once_with(title=issue_title, body=issue_body)
    assert result is None, "Expected the returned value to be None due to failure in creating an issue"


def test_find_existing_issue_by_title_and_creator_found():
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


def test_find_existing_issue_by_title_and_creator_not_found():
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
