import pytest

from git_mirror.cross_repo_sync import TemplateSync  # Ensure this points to your module where TemplateSync is defined


def setup_template_directory(tmp_path):
    # Setup template directory structure
    templates_dir = tmp_path / "template"
    templates_dir.mkdir()

    (templates_dir / "template_map.txt").write_text("target:source", encoding="utf-8")

    template_dir = templates_dir / "source"
    template_dir.mkdir()
    (template_dir / "file1.txt").write_text("File 1 content", encoding="utf-8")
    sub_dir = template_dir / "subdir"
    sub_dir.mkdir()
    (sub_dir / "file2.txt").write_text("File 2 content", encoding="utf-8")
    return template_dir


@pytest.fixture
def template_sync(tmp_path):
    setup_template_directory(tmp_path)
    # Initialize TemplateSync with the temporary template directory
    return TemplateSync(templates_dir=tmp_path / "template")


def test_copy_template_new_target(template_sync, tmp_path):
    # Create a new target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    # Execute the _copy_template method
    template_sync._copy_template(target_dir)
    # Assert that files and directories were copied correctly
    assert (target_dir / "file1.txt").exists()
    assert (target_dir / "file1.txt").read_text(encoding="utf-8") == "File 1 content"
    assert (target_dir / "subdir" / "file2.txt").exists()
    assert (target_dir / "subdir" / "file2.txt").read_text(encoding="utf-8") == "File 2 content"


def test_copy_template_overwrite_files(template_sync, tmp_path):
    # Create a target directory with existing files to be overwritten
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "file1.txt").write_text("Old File 1 content", encoding="utf-8")
    # Execute the _copy_template method
    template_sync._copy_template(target_dir)
    # Assert that the existing file was overwritten
    assert (target_dir / "file1.txt").read_text(encoding="utf-8") == "File 1 content"
