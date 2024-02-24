from pathlib import Path

import pytest

from git_mirror.cross_repo_sync import TemplateSync  # Adjust this import according to your project structure


@pytest.fixture
def template_sync(tmp_path):
    # Setup TemplateSync with a mock templates directory
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    return TemplateSync(templates_dir=templates_dir)


def create_file(path: Path, content: str):
    """Helper function to create a file with the given content."""
    path.write_text(content, encoding="utf-8")


@pytest.mark.parametrize(
    "template_content,target_content,project_name,expected_result",
    [
        ("", "Any content", "", {"difference": "Empty templates match all file contents."}),
        ("Hello, {{{PROJECT_NAME}}}", "Hello, World", "World", {}),
        ("Line 1\nLine 2", "Line 1\nLine 2", "", {}),
        ("Line 1\nLine 2\nLine 3", "Line 1\nLine 2", "", {"difference": "different length"}),
        ("Line 1\nLine 2", "Line 1\nDifferent Line 2", "", {"difference": "different contents"}),
    ],
)
def test_compare_files(tmp_path, template_sync, template_content, target_content, project_name, expected_result):
    # Setup template and target files
    template_file = tmp_path / "template.txt"
    target_file = tmp_path / "target.txt"
    create_file(template_file, template_content)
    create_file(target_file, target_content)

    # Execute _compare_files
    result = template_sync._compare_files(template_file, target_file, project_name)

    # Assert
    assert result == expected_result, f"Expected {expected_result}, got {result}"
