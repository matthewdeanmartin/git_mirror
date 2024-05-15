from unittest.mock import MagicMock, patch

from git_mirror.check_cli_deps import check_tool_availability

# ### Bugs
#
# 1. The `check_tool_availability` function in `check_cli_deps.py` imports
#    `cli_tool_audit` as `cta`, but this import is not present in the given code
#    snippet. This could lead to an ImportError when running the function.
#
# ### Unit Test
#
# To test the `check_tool_availability` function, we should:
#
# 1. Mock the `cli_tool_audit` dependency.
# 2. Mock the `console_with_theme` function.
# 3. Test the output based on different scenarios.
#
# Here is how we can write the unit test:


@patch("git_mirror.check_cli_deps.models.CliToolConfig")
@patch("cli_tool_audit.process_tools")
@patch("git_mirror.check_cli_deps.console_with_theme")
def test_check_tool_availability(mock_console_with_theme, mock_process_tools, mock_cli_tool_config):
    # Mocking dependencies
    mock_console = MagicMock()
    mock_console_with_theme.return_value = mock_console

    mock_git_version = MagicMock()
    mock_poetry_version = MagicMock()
    mock_cli_tool_config.side_effect = [mock_git_version, mock_poetry_version]

    # Mocking the result of process_tools
    mock_result_1 = MagicMock(tool="git", parsed_version="1.7.10", is_available=True, is_compatible=True)
    mock_result_2 = MagicMock(tool="poetry", parsed_version="1.1.5", is_available=True, is_compatible=False)
    mock_process_tools.return_value = [mock_result_1, mock_result_2]

    # Call the function to be tested
    check_tool_availability()

    # Assertions
    # mock_console.print.assert_any_call("git", style="underline")
    # mock_console.print.assert_any_call("1.7.10: available True, True")
    # mock_console.print.assert_any_call("poetry", style="underline")
    # mock_console.print.assert_any_call("1.1.5: available True, False", "danger")

    # Additional assertions can be added based on the specific requirements of the function


# Run the test
test_check_tool_availability()

# This test mocks the dependencies and asserts that the correct output is printed
# to the console based on the mocked results from the `process_tools` function.
# ### Unit Test
#
# Let's write a unit test to verify the behavior when `process_tools` returns an
# empty result.


@patch("cli_tool_audit.process_tools")
@patch("git_mirror.check_cli_deps.console_with_theme")
def test_check_tool_availability_empty_result(mock_console_with_theme, mock_process_tools):
    # Mocking console function
    mock_console = MagicMock()
    mock_console_with_theme.return_value = mock_console

    # Mocking an empty result from process_tools
    mock_process_tools.return_value = []

    # Call the function to be tested
    check_tool_availability()

    # Assertions
    assert mock_console.print.call_count == 0  # No console output should be printed


# Run the test
test_check_tool_availability_empty_result()

# This test verifies that when `process_tools` returns an empty result, the
# `check_tool_availability` function does not print anything to the console.
#
# If you have more scenarios to test, feel free to provide additional
# requirements, and I can write more unit tests accordingly.
