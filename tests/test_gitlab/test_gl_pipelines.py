from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git_mirror.manage_gitlab import GitlabRepoManager


@pytest.fixture
def gitlab_repo_manager():
    return GitlabRepoManager("token", Path("/fake/path"), "user_login")


def test_loop_pipelines(gitlab_repo_manager):
    # Setup
    manager = gitlab_repo_manager

    # Create mock statuses
    mock_statuses = [
        MagicMock(
            updated_at="2021-01-01 12:00",
            id="1",
            # detailed_status={"text": "success", "label": "success"},
            # conclusion="Success",
            status="success",
            web_url="http://example.com/1",
        ),
        MagicMock(
            updated_at="2021-01-02 12:00",
            id="2",
            # detailed_status={"text": "failed", "label": "failed"},
            # conclusion="Failure",
            status="success",
            web_url="http://example.com/2",
        ),
        MagicMock(
            updated_at="2021-01-03 12:00",
            id="3",
            # detailed_status={"text": "cancelled", "label": "cancelled"},
            # conclusion="Cancelled",
            status="success",
            web_url="http://example.com/3",
        ),
    ]

    # Expected messages based on mock statuses
    expected_messages = [
        (
            "success",
            "Date: 2021-01-01 12:00 - Pipeline #1 - Status: success - URL: http://example.com/1",
        ),
        # ("failed", "Date: 2021-01-02 12:00 - Pipeline #2 - Status: failed - URL: http://example.com/2"),
        # ("cancelled", "Date: 2021-01-03 12:00 - Pipeline #3 - Status: cancelled - URL: http://example.com/3"),
    ]

    # Execute
    messages = manager._loop_pipelines(mock_statuses)

    # Assert
    assert messages == expected_messages


def list_list_repo_actions(gitlab_repo_manager):
    # Setup
    manager = gitlab_repo_manager
    manager._loop_pipelines = MagicMock()

    # Create mock statuses
    mock_statuses = [
        MagicMock(
            created_at="2021-01-01 12:00",
            display_title="Workflow 1",
            status="success",
            html_url="http://example.com/1",
        ),
        MagicMock(
            created_at="2021-01-02 12:00",
            display_title="Workflow 2",
            status="success",
            html_url="http://example.com/2",
        ),
        MagicMock(
            created_at="2021-01-03 12:00",
            display_title="Workflow 3",
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

    manager._loop_pipelines.return_value = expected_messages
    # Execute
    messages = manager.list_repo_builds(mock_statuses)

    # Assert
    assert messages == expected_messages
    assert len(expected_messages) == 3
