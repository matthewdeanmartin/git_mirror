from unittest.mock import patch


from git_mirror.manage_config import ConfigData, ask_for_section

# Mock responses for inquirer.prompt to simulate user input
mock_prompt_responses = {
    "host_type": "github",
    "user_name": "testuser",
    "target_dir": "~/repositories",
    "include_private": True,
    "include_forks": False,
    "create_target_dir": True,
    "host_name": "gitlab",  # For selfhosted
    "host_url": "http://self-hosted-git.example.com",
    "group_id": "123",
}


@patch("inquirer.prompt", side_effect=lambda x: {q.name: mock_prompt_responses[q.name] for q in x})
@patch("pathlib.Path.exists", return_value=True)
@patch("os.makedirs")
def test_ask_for_section_with_existing_target_dir(mock_makedirs, mock_exists, mock_prompt):
    # Simulate scenario where target directory exists
    result = ask_for_section([])
    assert result is not None
    assert isinstance(result, ConfigData)
    mock_makedirs.assert_not_called()


def test_ask_for_section_all_hosts_configured():
    result = ask_for_section(["github", "gitlab", "selfhosted"])
    assert result is None


@patch("inquirer.prompt", side_effect=lambda x: {q.name: mock_prompt_responses[q.name] for q in x})
@patch("pathlib.Path.exists", side_effect=[False, True])  # Simulate not exist then exist after creation
@patch("os.makedirs")
def test_ask_for_section_target_dir_creation(mock_makedirs, mock_exists, mock_prompt):
    # Adjust mock_prompt_responses as necessary to simulate user opting to create the directory
    _result = ask_for_section(["github"])
    assert _result.host_name == "github"
    mock_makedirs.assert_called_once()


@patch("inquirer.prompt", side_effect=lambda x: {q.name: mock_prompt_responses[q.name] for q in x})
@patch("pathlib.Path.exists", return_value=True)  # Assume the new target directory exists
def test_ask_for_section_no_target_dir_creation(mock_exists, mock_prompt):
    # Adjust mock_prompt_responses to simulate user opting not to create the directory and then providing a new path
    result = ask_for_section(["gitlab"])
    assert result is not None
    assert result.target_dir.exists()


@patch("inquirer.prompt", side_effect=lambda x: {q.name: mock_prompt_responses[q.name] for q in x})
def test_ask_for_section_host_type_github(mock_prompt):
    result = ask_for_section([])
    assert result.host_type == "github"
    assert result.host_url == "https://api.github.com"


@patch(
    "inquirer.prompt",
    side_effect=lambda x: {
        q.name: {"group_id": "not_an_int"} if q.name == "group_id" else mock_prompt_responses[q.name] for q in x
    },
)
def test_ask_for_section_group_id_non_integer(mock_prompt):
    result = ask_for_section(["gitlab"])
    assert result.group_id == 0
