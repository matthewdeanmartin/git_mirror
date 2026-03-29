from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import pytest
import os
import git as g
from git_mirror.services import (
    load_all_configs,
    run_doctor,
    scan_local_changes,
    list_repos_data,
    clone_all_repos,
    pull_all_repos,
    find_non_repos,
    get_build_statuses,
    get_token_for_host,
    RepoStatus,
    RepoInfo,
    ActionResult,
    BuildInfo
)
from git_mirror.manage_config import ConfigData, SetupCheck

def test_load_all_configs():
    with patch("git_mirror.services.ConfigManager") as MockConfigManager:
        mock_cm = MockConfigManager.return_value
        mock_cm.load_config_objects.return_value = {"github": None}
        
        configs = load_all_configs()
        assert configs == {"github": None}
        MockConfigManager.assert_called_once()

def test_run_doctor():
    with patch("git_mirror.services.ConfigManager") as MockConfigManager:
        mock_cm = MockConfigManager.return_value
        mock_config = MagicMock()
        mock_config.host_name = "github"
        mock_config.host_type = "github"
        mock_cm.load_config_objects.return_value = {"github": mock_config}
        mock_cm.load_config.return_value = mock_config
        mock_cm._run_checks.return_value = [SetupCheck("github", True, "OK", "")]
        
        results = run_doctor()
        assert len(results) == 1
        assert results[0][0] == "github"
        assert len(results[0][1]) == 1
        assert results[0][1][0].ok is True

def test_run_doctor_no_config():
    with patch("git_mirror.services.ConfigManager") as MockConfigManager:
        mock_cm = MockConfigManager.return_value
        mock_cm.load_config_objects.return_value = {"github": None}
        mock_cm.load_config.return_value = None
        
        # run_doctor will try to iterate over hosts if host is not provided.
        # if configs.items() has None values, it skips them if host is not provided.
        # hosts = [host] if host else [name for name, data in configs.items() if data]
        # In this case host=None, and data=None, so hosts=[], so results=[]
        results = run_doctor()
        assert len(results) == 0

def test_run_doctor_no_config_with_host():
    with patch("git_mirror.services.ConfigManager") as MockConfigManager:
        mock_cm = MockConfigManager.return_value
        mock_cm.load_config_objects.return_value = {"github": None}
        mock_cm.load_config.return_value = None
        
        results = run_doctor(host="github")
        assert len(results) == 1
        assert results[0][1][0].ok is False
        assert "No configuration found" in results[0][1][0].details

def test_scan_local_changes():
    with patch("git_mirror.manage_git.find_git_repos") as mock_find_repos, \
         patch("git_mirror.services.g.Repo") as MockRepo:
        
        repo_path = Path("/mock/repo")
        mock_find_repos.return_value = [repo_path]
        
        mock_repo = MockRepo.return_value
        mock_repo.is_dirty.return_value = True
        
        mock_branch = MagicMock()
        mock_branch.name = "main"
        mock_branch.tracking_branch.return_value = MagicMock()
        mock_repo.heads = [mock_branch]
        mock_repo.iter_commits.return_value = [MagicMock()]
        
        statuses = scan_local_changes(Path("/mock"))
        
        assert len(statuses) == 1
        assert statuses[0].path == repo_path
        assert statuses[0].dirty is True
        assert "main" in statuses[0].unpushed_branches

def test_scan_local_changes_error():
    with patch("git_mirror.manage_git.find_git_repos") as mock_find_repos, \
         patch("git_mirror.services.g.Repo") as MockRepo:
        
        repo_path = Path("/mock/repo")
        mock_find_repos.return_value = [repo_path]
        MockRepo.side_effect = Exception("Test error")
        
        statuses = scan_local_changes(Path("/mock"))
        assert len(statuses) == 1
        assert statuses[0].error == "Test error"

def test_list_repos_data_github():
    config = ConfigData(
        host_name="github",
        host_type="github",
        host_url="https://api.github.com",
        user_name="testuser",
        target_dir=Path("/mock/target")
    )
    with patch("github.Github") as MockGithub:
        mock_client = MockGithub.return_value
        mock_user = mock_client.get_user.return_value
        
        mock_repo = MagicMock()
        mock_repo.name = "test-repo"
        mock_repo.description = "desc"
        mock_repo.private = False
        mock_repo.fork = False
        mock_repo.html_url = "http://github.com/testuser/test-repo"
        mock_repo.owner.login = "testuser"
        
        mock_user.get_repos.return_value = [mock_repo]
        
        repos = list_repos_data("token", "github", config)
        assert len(repos) == 1
        assert repos[0].name == "test-repo"

def test_list_repos_data_gitlab():
    config = ConfigData(
        host_name="gitlab",
        host_type="gitlab",
        host_url="https://gitlab.com",
        user_name="testuser",
        target_dir=Path("/mock/target")
    )
    with patch("gitlab.Gitlab") as MockGitlab:
        mock_gl = MockGitlab.return_value
        mock_user = mock_gl.user = MagicMock()
        
        mock_project = MagicMock()
        mock_project.name = "test-project"
        mock_project.description = "desc"
        mock_project.visibility = "public"
        mock_project.web_url = "http://gitlab.com/testuser/test-project"
        mock_project.forked_from_project = None
        
        mock_user.projects.list.return_value = [mock_project]
        
        repos = list_repos_data("token", "gitlab", config)
        assert len(repos) == 1
        assert repos[0].name == "test-project"

def test_clone_all_repos_github():
    config = ConfigData(
        host_name="github",
        host_type="github",
        host_url="https://api.github.com",
        user_name="testuser",
        target_dir=Path("/mock/target")
    )
    with patch("git_mirror.manage_github.GithubRepoManager") as MockMgr, \
         patch("git_mirror.services.g.Repo") as MockRepo, \
         patch("git_mirror.services.Path.exists") as mock_exists:
        
        mock_exists.return_value = False
        mock_mgr = MockMgr.return_value
        mock_mgr._get_user_repos.return_value = [{"name": "repo1", "html_url": "http://url"}]
        mock_mgr._thread_safe_repos.side_effect = lambda x: x
        
        result = clone_all_repos("token", config)
        assert result.success is True
        assert "Cloned: repo1" in result.messages
        MockRepo.clone_from.assert_called_once()

def test_pull_all_repos():
    with patch("git_mirror.manage_git.find_git_repos") as mock_find_repos, \
         patch("git_mirror.services.g.Repo") as MockRepo:
        
        mock_find_repos.return_value = [Path("/mock/repo")]
        mock_repo = MockRepo.return_value
        mock_remote = MagicMock()
        mock_repo.remotes = MagicMock()
        mock_repo.remotes.origin = mock_remote
        
        result = pull_all_repos(Path("/mock"))
        assert result.success is True
        assert "Pulled: repo" in result.messages
        mock_remote.pull.assert_called_once()

def test_find_non_repos():
    with patch("git_mirror.services.Path.iterdir") as mock_iterdir, \
         patch("git_mirror.services.Path.exists") as mock_exists:
        
        mock_exists.return_value = True
        mock_dir = MagicMock(spec=Path)
        mock_dir.is_dir.return_value = True
        mock_dir.name = "not-a-repo"
        # mock_dir / ".git"
        mock_git_dir = MagicMock(spec=Path)
        mock_git_dir.exists.return_value = False
        mock_dir.__truediv__.return_value = mock_git_dir
        
        mock_iterdir.return_value = [mock_dir]
        
        results = find_non_repos(Path("/mock"))
        assert len(results) == 1
        assert results[0][0] == str(mock_dir)

def test_get_build_statuses_github():
    config = ConfigData(
        host_name="github",
        host_type="github",
        host_url="https://api.github.com",
        user_name="testuser",
        target_dir=Path("/mock/target")
    )
    with patch("github.Github") as MockGithub:
        mock_client = MockGithub.return_value
        mock_user = mock_client.get_user.return_value
        
        mock_repo = MagicMock()
        mock_repo.owner.login = "testuser"
        mock_repo.private = False
        mock_repo.fork = False
        mock_repo.name = "repo1"
        
        mock_run = MagicMock()
        mock_run.conclusion = "success"
        mock_run.created_at = "2023-01-01"
        mock_run.display_title = "workflow"
        mock_run.status = "completed"
        
        mock_repo.get_workflow_runs.return_value = [mock_run]
        mock_user.get_repos.return_value = [mock_repo]
        
        builds = get_build_statuses("token", config)
        assert len(builds) == 1
        assert builds[0].repo_name == "repo1"
        assert builds[0].conclusion == "success"

def test_get_token_for_host():
    with patch("git_mirror.services.os.getenv") as mock_getenv:
        mock_getenv.return_value = "secret-token"
        
        config_gh = ConfigData(
            host_name="github",
            host_type="github",
            host_url="https://api.github.com",
            user_name="testuser",
            target_dir=Path("/mock/target")
        )
        assert get_token_for_host(config_gh) == "secret-token"
        
        config_gl = ConfigData(
            host_name="gitlab",
            host_type="gitlab",
            host_url="https://gitlab.com",
            user_name="testuser",
            target_dir=Path("/mock/target")
        )
        assert get_token_for_host(config_gl) == "secret-token"

        config_sh = ConfigData(
            host_name="selfhosted",
            host_type="github",
            host_url="https://git.example.com",
            user_name="testuser",
            target_dir=Path("/mock/target")
        )
        assert get_token_for_host(config_sh) == "secret-token"

def test_clone_all_repos_gitlab():
    config = ConfigData(
        host_name="gitlab",
        host_type="gitlab",
        host_url="https://gitlab.com",
        user_name="testuser",
        target_dir=Path("/mock/target")
    )
    with patch("git_mirror.manage_gitlab.GitlabRepoManager") as MockMgr, \
         patch("git_mirror.services.g.Repo") as MockRepo, \
         patch("git_mirror.services.Path.exists") as mock_exists:
        
        mock_exists.return_value = False
        mock_mgr = MockMgr.return_value
        mock_repo_data = MagicMock()
        mock_repo_data.name = "repo1"
        mock_repo_data.http_url_to_repo = "http://url"
        mock_mgr._get_user_repos.return_value = [mock_repo_data]
        
        result = clone_all_repos("token", config)
        assert result.success is True
        assert "Cloned: repo1" in result.messages
        MockRepo.clone_from.assert_called_once()

def test_list_repos_data_unknown():
    config = ConfigData(
        host_name="unknown",
        host_type="unknown",
        host_url="http://unknown",
        user_name="testuser",
        target_dir=Path("/mock/target")
    )
    repos = list_repos_data("token", "unknown", config)
    assert repos == []

def test_get_build_statuses_non_github():
    config = ConfigData(
        host_name="gitlab",
        host_type="gitlab",
        host_url="https://gitlab.com",
        user_name="testuser",
        target_dir=Path("/mock/target")
    )
    builds = get_build_statuses("token", config)
    assert builds == []
