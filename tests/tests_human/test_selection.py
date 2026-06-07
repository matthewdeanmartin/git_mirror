import tomlkit

from git_mirror.core import RepoSelection, build_selection
from git_mirror.manage_config import ConfigManager


def sel(**kw):
    overrides = kw.pop("overrides", {})
    return RepoSelection(overrides=overrides, **kw)


def test_default_selection_keeps_everything():
    s = sel()
    assert s.filter(["a", "b", "c"]) == ["a", "b", "c"]


def test_exclude_drops_named():
    s = sel(exclude={"b"})
    assert s.filter(["a", "b", "c"]) == ["a", "c"]


def test_only_keeps_named():
    s = sel(only={"a", "c"})
    assert s.filter(["a", "b", "c"]) == ["a", "c"]


def test_only_and_exclude_combine():
    s = sel(only={"a", "b"}, exclude={"b"})
    assert s.filter(["a", "b", "c"]) == ["a"]


def test_ignore_in_config_is_skipped():
    s = sel(overrides={"b": {"ignore": True, "tags": []}})
    assert s.filter(["a", "b"]) == ["a"]


def test_include_ignored_overrides_config():
    s = sel(overrides={"b": {"ignore": True, "tags": []}}, include_ignored=True)
    assert s.filter(["a", "b"]) == ["a", "b"]


def test_only_overrides_ignore():
    s = sel(overrides={"b": {"ignore": True, "tags": []}}, only={"b"})
    assert s.filter(["a", "b"]) == ["b"]


def test_tag_filtering():
    overrides = {"a": {"tags": ["work"]}, "b": {"tags": ["fun"]}, "c": {"tags": []}}
    s = sel(overrides=overrides, tags={"work"})
    assert s.filter(["a", "b", "c"]) == ["a"]


def test_build_selection_reads_overrides(tmp_path):
    config_path = tmp_path / "git_mirror.toml"
    doc = {
        "tool": {
            "git-mirror": {
                "github": {
                    "host_type": "github",
                    "host_url": "https://api.github.com",
                    "user_name": "octocat",
                    "target_dir": str(tmp_path),
                    "repos": {
                        "keep": {"tags": ["work"]},
                        "skip": {"ignore": True},
                    },
                }
            }
        }
    }
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    selection = build_selection("github", config_path=config_path)
    assert selection.filter(["keep", "skip", "other"]) == ["keep", "other"]

    tagged = build_selection("github", config_path=config_path, tags=["work"])
    assert tagged.filter(["keep", "skip", "other"]) == ["keep"]


def test_load_repo_overrides_empty_when_no_section(tmp_path):
    config_path = tmp_path / "git_mirror.toml"
    config_path.write_text("", encoding="utf-8")
    cm = ConfigManager(config_path=config_path)
    assert cm.load_repo_overrides("github") == {}
