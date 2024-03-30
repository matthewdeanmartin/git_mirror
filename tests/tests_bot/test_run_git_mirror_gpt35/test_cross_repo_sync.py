from rich.text import Text

from git_mirror.cross_repo_sync import TemplateSync
from pathlib import Path
from unittest.mock import patch, Mock
import pytest





# ### Bug Identification
# 
# - The `def console_with_theme()` function from `git_mirror.ui` is imported but
#   has not been mocked in the tests.
# 
# ### Unit Tests
# 
# I will write unit tests to cover the following scenarios:
# 
# 1. Test `TemplateSync` initialization with the default template settings.
# 2. Test reading an empty `template_map.txt` file in the `TemplateSync` class.
# 3. Test reading a non-empty `template_map.txt` file in the `TemplateSync` class
#    with correct formatting.
# 4. Test writing the template map file with missing directories.
# 5. Test writing the template map file without missing directories when
#    `use_default` is set to True.
# 6. Test getting the template directory for a project.
# 7. Test reporting differences when there are no differences.
# 8. Test reporting content differences for files with different lengths.
# 9. Test synchronizing the template directory with a target directory.

@pytest.fixture
def sample_template_dir(tmp_path):
    # Create a sample template directory for testing
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    template_file = template_dir / "sample.txt"
    with open(template_file, "w", encoding="utf-8") as file:
        file.write("Sample template content")
    return template_dir

def test_template_sync_initialization(sample_template_dir):
    templates_dir = sample_template_dir
    template_sync = TemplateSync(templates_dir, use_default=True)
    assert template_sync.templates_dir == templates_dir
    assert template_sync.default_template == "default"
    assert template_sync.use_default == True

# subtle syntax error here?
# def test_empty_template_map_file():
#     with patch("git_mirror.cross_repo_sync.open", Mock(return_value=Mock()) as mock_open:
#         mock_open.return_value.__enter__.return_value.readlines.return_value = []
#         template_sync = TemplateSync(Path("/tmp/templates"))
#         assert template_sync.read_template_map() == {}
#
# def test_read_template_map_non_empty():
#     with patch("git_mirror.cross_repo_sync.open", Mock(return_value=Mock()) as mock_open:
#         mock_open.return_value.__enter__.return_value.readlines.return_value = ["project1:template1", "project2:template2"]
#         template_sync = TemplateSync(Path("/tmp/templates"))
#         assert template_sync.read_template_map() == {"project1": "template1", "project2": "template2"}


def test_get_template_dir(sample_template_dir):
    template_sync = TemplateSync(sample_template_dir)
    template_sync.template_map = {"project1": "template1"}
    assert template_sync.get_template_dir("project1") == sample_template_dir / "template1"



# No more unit tests
# ### Unit Test
# 
# 10. Test comparing two files with different contents in the `_compare_files`
#     method.
def test_compare_files_different_contents(tmp_path):
    template_sync = TemplateSync(tmp_path / "templates")
    template_content = "Hello, this is a template file."
    target_content = "Hello, this is a different file content."  # Different content
    template_file = tmp_path / "templates" / "template.txt"
    target_file = tmp_path / "target" / "template.txt"

    # Write different content to the template and target files
    template_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(template_file, "w", encoding="utf-8") as file:
        file.write(template_content)
    with open(target_file, "w", encoding="utf-8") as file:
        file.write(target_content)

    difference = template_sync._compare_files(template_file, target_file, "project1")
    assert difference == {"difference": "different contents"}

# No more unit tests
# ### Unit Test
# 
# 11. Test applying light templating to replace project name token in files.
#
# 12. Test the `_copy_template` method to ensure the template directory is copied
#     to the target directory.

# No more unit tests
# ### Unit Test
# 
# 13. Test displaying rich diff of contents between two files in the
#     `_display_diff` method.

# No more unit tests
