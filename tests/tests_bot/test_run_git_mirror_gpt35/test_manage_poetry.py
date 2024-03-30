from git import Repo
from git_mirror.custom_types import SourceHost
from git_mirror.manage_poetry import PoetryManager
from git_mirror.manage_poetry import PoetryManager, clean_gone_branches
from unittest.mock import MagicMock, call
from unittest.mock import mock_open, patch
import pytest


# ## Bug Report
# 
# 1. In the `install` method of the `PoetryManager` class, the subprocess calls to
#    `poetry lock` and `poetry install --with dev` are using `shell=True`. This
#    can be a security risk and should be avoided. Instead, the command should be
#    provided as a list of strings without using `shell=True`.
# 
# 2. The `update_dependencies` method of the `PoetryManager` class has a TODO
#    comment suggesting making the group configuration driven. This comment should
#    be expanded upon or addressed to ensure clarity on what needs to be done.
# 
# 3. The `clean_gone_branches` function should not be called inside the
#    `update_dependencies` method without proper consideration of its necessity
#    and impact. It's currently commented out in the code, and its
#    inclusion/exclusion should be decided based on the desired behavior.
# 
# 4. In the `PoetryManager` class `update_dependencies` method, there is a
#    commented block of code with
#    `origin.push('-f', f'{dependency_update_branch}:{dependency_update_branch}', set_upstream=True)`.
#    This block of code is commented out and should either be implemented or
#    removed based on the intended functionality.
# 
# ## Unit Tests

@pytest.fixture
def mock_repo():
    # Mocking the git.Repo object
    return MagicMock(spec=Repo)

@pytest.fixture
def mock_source_host():
    # Mocking the SourceHost object
    return MagicMock(spec=SourceHost)

def test_clean_gone_branches():
    # Test clean_gone_branches function
    repo = MagicMock()
    repo.git.for_each_ref.return_value = "branch1 [gone]\nbranch2 [ahead]"
    clean_gone_branches(repo)
    assert repo.git.branch.call_args_list == [call("-D", "branch1")]

