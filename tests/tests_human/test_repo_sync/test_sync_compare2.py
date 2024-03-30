from pathlib import Path

import pytest

from git_mirror.cross_repo_sync import TemplateSync  # Adjust the import as necessary


def test_compare_files_identical(tmp_path, template_sync):
    # Setup
    template_file = tmp_path / "template.txt"
    target_file = tmp_path / "target.txt"
    content = "Hello, {{PROJECT_NAME}}\n"
    template_file.write_text(content.replace("{{PROJECT_NAME}}", "World"), encoding="utf-8")
    target_file.write_text(content.replace("{{PROJECT_NAME}}", "World"), encoding="utf-8")

    # Execute
    result = template_sync._compare_files(template_file, target_file, "World")

    # Assert
    assert result == {}, "Identical files should not have differences"


def create_file(path: Path, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


@pytest.mark.parametrize(
    "content,project_name,expected",
    [
        ("Hello, {{{PROJECT_NAME}}}!", "AcmeCorp", "Hello, AcmeCorp!"),
        ("No token here.", "AcmeCorp", "No token here."),
        ("", "AcmeCorp", ""),
        ("{{{PROJECT_NAME}}}-{{{PROJECT_NAME}}}", "AcmeCorp", "AcmeCorp-AcmeCorp"),
    ],
)
def test_apply_light_templating(tmp_path, template_sync, content, project_name, expected):
    # Setup
    template_file = tmp_path / "template.txt"
    target_file = tmp_path / "target.txt"
    create_file(template_file, content)
    create_file(target_file, content)  # Content of target doesn't matter for this test

    # Execute
    target_lines, template_lines = template_sync.apply_light_templating(target_file, template_file, project_name)

    # Assert
    assert "\n".join(template_lines) == expected, "The templating did not apply correctly."


@pytest.fixture
def template_sync(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    return TemplateSync(templates_dir=templates_dir)


def test_copy_template_to_empty_target_dir(tmp_path, template_sync):
    # Setup template directory
    template_dir = tmp_path / "templates" / "project_template"
    template_dir.mkdir(parents=True)
    (template_dir / "file.txt").write_text("content", encoding="utf-8")
    (template_dir / "subdir").mkdir()
    (template_dir / "subdir" / "subfile.txt").write_text("subcontent", encoding="utf-8")

    # Setup target directory
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # Setup template mapping to simulate getting the correct template directory
    template_sync.template_map = {"target": "project_template"}

    # Execute
    template_sync._copy_template(target_dir)

    # Assert
    assert (target_dir / "file.txt").exists(), "File was not copied to target directory."
    assert (target_dir / "file.txt").read_text(encoding="utf-8") == "content", "File content is incorrect."
    assert (target_dir / "subdir" / "subfile.txt").exists(), "Subdirectory file was not copied."
    assert (target_dir / "subdir" / "subfile.txt").read_text(
        encoding="utf-8"
    ) == "subcontent", "Subdirectory file content is incorrect."


def test_copy_template_overwrite_existing_files(tmp_path, template_sync):
    # Setup template directory with a file
    template_dir = tmp_path / "templates" / "project_template"
    template_dir.mkdir(parents=True)
    template_file = template_dir / "file.txt"
    template_file.write_text("new content", encoding="utf-8")

    # Setup target directory with an existing file of the same name but different content
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    target_file = target_dir / "file.txt"
    target_file.write_text("old content", encoding="utf-8")

    # Setup template mapping
    template_sync.template_map = {"target": "project_template"}

    # Execute
    template_sync._copy_template(target_dir)

    # Assert
    assert target_file.exists(), "File in target directory should still exist after copying."
    assert (
        target_file.read_text(encoding="utf-8") == "new content"
    ), "Existing file in target directory was not overwritten with new content."
