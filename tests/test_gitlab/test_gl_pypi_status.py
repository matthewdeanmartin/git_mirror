from pathlib import Path
from unittest.mock import patch

import git
import httpx
import pytest

from git_mirror.manage_gitlab import GitlabRepoManager


# Helper function to initialize a git repository with a commit
def init_git_repo(repo_path: Path):
    repo = git.Repo.init(repo_path)
    (repo_path / "README.md").write_text("Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    return repo


@pytest.fixture
def gitlab_repo_manager(tmp_path):
    return GitlabRepoManager("token", tmp_path, "user_login")


@pytest.mark.parametrize(
    "pypi_owner_name,expected_owner", [(None, True), ("correct_owner", True), ("wrong_owner", False)]
)
def test_check_pypi_publish_status(gitlab_repo_manager, tmp_path, pypi_owner_name, expected_owner):
    # Setup temporary git repository
    repo_name = "test_package"
    repo_path = tmp_path / repo_name
    init_git_repo(repo_path)

    # Mock response data from PyPI
    pypi_response_data = {
        "info": {"author": "correct_owner", "version": "0.1.0"},
        "releases": {"0.1.0": [{"upload_time": "2021-09-10T18:48:49"}]},
    }

    # Mock httpx.Client.get to return the predefined PyPI response
    with patch.object(httpx.AsyncClient, "get", return_value=httpx.Response(200, json=pypi_response_data)):
        results = gitlab_repo_manager.check_pypi_publish_status(pypi_owner_name)

    # Determine if the package should appear in the results based on the owner name filter
    if expected_owner:
        assert len(results) == 1
        assert results[0]["Package"] == repo_name
        assert results[0]["On PyPI"] == "Yes"
        # Further assertions can be made based on the `results` structure
    else:
        assert len(results) == 0  # Package should not be listed due to owner mismatch
