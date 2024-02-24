import pytest

from git_mirror.cross_repo_sync import TemplateSync


def test_read_template_map_valid_content(tmp_path):
    # Setup: Create a temporary template_map.txt
    template_map_file = tmp_path / "template_map.txt"
    template_map_file.write_text("Project1: Template1\nProject2: Template2\n", encoding="utf-8")
    # Instantiate TemplateSync with tmp_path as templates_dir
    ts = TemplateSync(templates_dir=tmp_path)
    # Overwrite ts.template_map_file after initialization due to the identified issue
    ts.template_map_file = template_map_file
    # Execute
    template_map = ts.read_template_map()
    # Assert
    assert template_map == {"Project1": "Template1", "Project2": "Template2"}


@pytest.fixture
def template_sync(tmp_path):
    # Setup a TemplateSync instance with a temporary directory
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    return TemplateSync(templates_dir=templates_dir, use_default=False)


def test_write_template_map_no_missing_dirs(template_sync, tmp_path):
    # Setup: Assume existing template map and no missing directories
    template_map_file = tmp_path / "template_map.txt"
    template_map_file.write_text("existing_dir:template\n", encoding="utf-8")
    template_sync.template_map_file = template_map_file  # Adjust for the late initialization issue

    target_dirs = [tmp_path / "existing_dir"]
    target_dirs[0].mkdir()

    # Execute
    template_sync.write_template_map(target_dirs)

    # Assert
    assert (
        template_map_file.read_text(encoding="utf-8") == "existing_dir:template\n"
    ), "Template map should not change if there are no missing directories"


def test_write_template_map_with_missing_dirs_use_default_true(template_sync, tmp_path):
    template_sync.use_default = True
    template_sync.template_map_file = tmp_path / "template_map.txt"  # Adjust for the late initialization issue

    missing_dir = tmp_path / "missing_dir"
    missing_dir.mkdir()

    # Execute
    template_sync.write_template_map([missing_dir])

    # Assert
    expected_content = "missing_dir:default\n"
    assert (
        template_sync.template_map_file.read_text(encoding="utf-8") == expected_content
    ), "Template map should be updated with default template for missing directories"
