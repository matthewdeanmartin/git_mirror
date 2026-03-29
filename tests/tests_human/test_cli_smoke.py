import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ENTRYPOINT_RUNNERS = {
    "git_mirror": [sys.executable, "-m", "git_mirror.__main__"],
    "gh_mirror": [
        sys.executable,
        "-c",
        "import sys; from git_mirror.__main__ import main_github; raise SystemExit(main_github(sys.argv[1:]))",
    ],
    "gl_mirror": [
        sys.executable,
        "-c",
        "import sys; from git_mirror.__main__ import main_gitlab; raise SystemExit(main_gitlab(sys.argv[1:]))",
    ],
    "sh_mirror": [
        sys.executable,
        "-c",
        "import sys; from git_mirror.__main__ import main_selfhosted; raise SystemExit(main_selfhosted(sys.argv[1:]))",
    ],
}


def _smoke_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")
    env["XDG_CACHE_HOME"] = str(tmp_path / "xdg-cache")
    env["HISTFILE"] = str(tmp_path / "bash_history")
    env["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"
    env["PYTEST_CURRENT_TEST"] = "smoke"
    env.setdefault("GITHUB_ACCESS_TOKEN", "smoke-token")
    env.setdefault("GITLAB_ACCESS_TOKEN", "smoke-token")
    env.setdefault("SELFHOSTED_ACCESS_TOKEN", "smoke-token")
    Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
    Path(env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
    return env


@pytest.mark.parametrize("entrypoint", ["git_mirror", "gh_mirror", "gl_mirror", "sh_mirror"])
@pytest.mark.parametrize("args", [["--help"], ["--version"]])
def test_entrypoint_smoke(entrypoint: str, args: list[str], tmp_path: Path):
    result = subprocess.run(
        [*ENTRYPOINT_RUNNERS[entrypoint], *args],
        capture_output=True,
        text=True,
        env=_smoke_env(tmp_path),
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["list-config", "--config-path", "TMP_CONFIG"],
        ["list-config", "--config-path", "TMP_CONFIG", "--host", "github"],
        ["doctor", "--help"],
        ["init", "--help"],
        ["menu", "--help"],
        ["gui", "--help"],
        ["list-repos", "--help"],
        ["clone-all", "--help"],
        ["pull-all", "--help"],
        ["local-changes", "--help"],
        ["not-repo", "--help"],
        ["update-from-main", "--help"],
        ["prune-all", "--help"],
        ["sync-config", "--help"],
        ["build-status", "--help"],
    ],
)
def test_git_mirror_command_surface(args: list[str], tmp_path: Path):
    config_path = tmp_path / "git_mirror.toml"
    resolved_args = [str(config_path) if arg == "TMP_CONFIG" else arg for arg in args]

    result = subprocess.run(
        [*ENTRYPOINT_RUNNERS["git_mirror"], *resolved_args],
        capture_output=True,
        text=True,
        env=_smoke_env(tmp_path),
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("script_name", ["basic_help.sh", "basic_test.sh", "basic_test_dry.sh", "entrypoint_help.sh"])
def test_bash_smoke_scripts(script_name: str, tmp_path: Path):
    if os.name == "nt":
        pytest.skip("bash smoke scripts run in GitHub Actions on Ubuntu")

    bash_path = shutil.which("bash")
    if bash_path is None:
        pytest.skip("bash is not available")

    result = subprocess.run(
        [bash_path, str(Path("scripts") / script_name)],
        capture_output=True,
        text=True,
        env=_smoke_env(tmp_path),
        check=False,
    )

    assert result.returncode == 0, result.stderr
