from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git_mirror.manage_github import GithubRepoManager


@pytest.fixture
def github_repo_manager():
    return GithubRepoManager("token", Path("/fake/path"), "user_login", prompt_for_changes=False)


def test_loop_actions(github_repo_manager):
    # Setup
    manager = github_repo_manager

    # Create mock statuses
    mock_statuses = [
        MagicMock(
            created_at="2021-01-01 12:00",
            display_title="Workflow 1",
            conclusion="Success",
            status="completed",
            html_url="http://example.com/1",
        ),
        MagicMock(
            created_at="2021-01-02 12:00",
            display_title="Workflow 2",
            conclusion="Failure",
            status="completed",
            html_url="http://example.com/2",
        ),
        MagicMock(
            created_at="2021-01-03 12:00",
            display_title="Workflow 3",
            conclusion="Cancelled",
            status="completed",
            html_url="http://example.com/3",
        ),
    ]

    # Expected messages based on mock statuses
    expected_messages = [
        (
            "success",
            "Date: 2021-01-01 12:00 - Workflow 1 - Conclusion - Success  Status: completed - URL: http://example.com/1",
        ),
        # ("failure", "Date: 2021-01-02 12:00 - Workflow 2 - Conclusion - Failure  Status: completed - URL: http://example.com/2"),
        # ("cancelled", "Date: 2021-01-03 12:00 - Workflow 3 - Conclusion - Cancelled  Status: completed - URL: http://example.com/3"),
    ]

    # Execute
    messages = manager._loop_actions(mock_statuses)

    # Assert
    assert messages == expected_messages


def list_list_repo_actions(github_repo_manager):
    # Setup
    manager = github_repo_manager
    manager._loop_actions = MagicMock()

    # Create mock statuses
    mock_statuses = [
        MagicMock(
            created_at="2021-01-01 12:00",
            display_title="Workflow 1",
            conclusion="Success",
            status="completed",
            html_url="http://example.com/1",
        ),
        MagicMock(
            created_at="2021-01-02 12:00",
            display_title="Workflow 2",
            conclusion="Failure",
            status="completed",
            html_url="http://example.com/2",
        ),
        MagicMock(
            created_at="2021-01-03 12:00",
            display_title="Workflow 3",
            conclusion="Cancelled",
            status="completed",
            html_url="http://example.com/3",
        ),
    ]

    # Expected messages based on mock statuses
    expected_messages = [
        (
            "success",
            "Date: 2021-01-01 12:00 - Workflow 1 - Conclusion - Success  Status: completed - URL: http://example.com/1",
        ),
        (
            "failure",
            "Date: 2021-01-02 12:00 - Workflow 2 - Conclusion - Failure  Status: completed - URL: http://example.com/2",
        ),
        (
            "cancelled",
            "Date: 2021-01-03 12:00 - Workflow 3 - Conclusion - Cancelled  Status: completed - URL: http://example.com/3",
        ),
    ]

    manager._loop_actions.return_value = expected_messages
    # Execute
    messages = manager.list_repo_builds(mock_statuses)

    # Assert
    assert messages == expected_messages
    assert len(expected_messages) == 3
