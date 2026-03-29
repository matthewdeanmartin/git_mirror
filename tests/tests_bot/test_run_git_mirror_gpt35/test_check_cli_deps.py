from unittest.mock import MagicMock, patch

from git_mirror.check_cli_deps import check_tool_availability


@patch("git_mirror.check_cli_deps.models.CliToolConfig")
@patch("git_mirror.check_cli_deps.cta.process_tools")
def test_check_tool_availability_uses_git_and_uv(mock_process_tools, mock_cli_tool_config):
    mock_process_tools.return_value = [
        MagicMock(tool="git", parsed_version="2.45.0", is_available=True, is_compatible=True),
        MagicMock(tool="uv", parsed_version="0.8.0", is_available=True, is_compatible=True),
    ]

    check_tool_availability()

    assert mock_cli_tool_config.call_count == 2
    requested_names = [call.kwargs["name"] for call in mock_cli_tool_config.call_args_list]
    assert requested_names == ["git", "uv"]


@patch("git_mirror.check_cli_deps.cta.process_tools")
def test_check_tool_availability_handles_empty_results(mock_process_tools):
    mock_process_tools.return_value = []

    check_tool_availability()

    mock_process_tools.assert_called_once()
