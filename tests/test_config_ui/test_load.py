from pathlib import Path
from unittest.mock import Mock, patch

from rich.console import Console
from rich.panel import Panel

from git_mirror.manage_config import (  # Adjust the import based on your actual module structure
    ConfigData,
    display_config,
)


@patch("git_mirror.manage_config.Console")
def test_display_config(mock_console_class):
    # Create a mock Console instance
    mock_console = Mock(spec=Console)
    mock_console_class.return_value = mock_console

    # Create a sample ConfigData instance
    config = ConfigData(
        host_name="github",
        host_type="github",
        host_url="https://api.github.com",
        user_name="testuser",
        target_dir=Path("/path/to/repo"),
        pypi_owner_name="testowner",
        include_private=True,
        include_forks=False,
        group_id=123,
        global_template_dir=None,
    )

    # Call the function under test
    display_config(config)

    # Verify that console.print was called with a Panel containing the expected Text
    args, _ = mock_console.print.call_args
    panel = args[0]
    assert isinstance(panel, Panel)
    assert "Configuration Summary" in panel.title
    assert "Your current setup" in panel.subtitle
    # Further checks can be made on the content of the Text object within the Panel,
    # such as checking for the presence of specific field names and values.
    # Note: Detailed inspection of the Text content may require assumptions about the internal
    # structure of Text objects, which could make the test fragile.
