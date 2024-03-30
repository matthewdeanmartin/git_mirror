from git_mirror import logging_config
from unittest.mock import patch
from unittest.mock import patch, MagicMock
import os
import pytest






# ### Bug
# 
# 1. In the `generate_config` function, there is an import statement for `github`.
#    However, in the given code snippet, `github` module is not imported. This
#    might cause an `ImportError` when `generate_config` function is called.
# 
# ### Unit Test
# 
# I will write a pytest unit test to check if the `generate_config` function
# correctly generates the logging configuration dictionary based on the provided
# arguments.


def test_generate_config():
    with patch("git_mirror.logging_config.github") as mock_github:
        mock_github.enable_console_debug_logging = MagicMock()
        
        # Test case for logging_level = 1
        logging_level_1_config = logging_config.generate_config(level="DEBUG", logging_level=1)
        assert logging_level_1_config["version"] == 1
        assert logging_level_1_config["disable_existing_loggers"] == True
        assert logging_level_1_config["handlers"]["default"]["level"] == "DEBUG"
        assert logging_level_1_config["formatters"]["colored"]["format"] == "%(log_color)s%(levelname)-8s%(reset)s %(green)s%(message)s"
        
        # Test case for logging_level = 2
        logging_level_2_config = logging_config.generate_config(level="DEBUG", logging_level=2)
        assert logging_level_2_config["version"] == 1
        assert logging_level_2_config["disable_existing_loggers"] == True
        assert logging_level_2_config["handlers"]["default"]["level"] == "DEBUG"
        assert logging_level_2_config["formatters"]["colored"]["format"] == "%(log_color)s%(levelname)-8s%(reset)s %(module)s %(green)s%(message)s"
        
        mock_github.enable_console_debug_logging.assert_called_once()


# Add more test cases as needed

# This test case checks if the `generate_config` function correctly generates the
# logging configuration dictionary for two different logging levels. The test also
# checks if the `github.enable_console_debug_logging` is called when the logging
# level is set to 2.
# ### Unit Test
# 
# I will write a pytest unit test to verify the behavior of the logging
# configuration when the environment variables `NO_COLOR` or `CI` are present.


def test_generate_config_with_environment_vars(tmp_path):
    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        config_no_color = logging_config.generate_config(level="DEBUG", logging_level=2)
        assert config_no_color["handlers"]["default"]["formatter"] == "standard"

    with patch.dict(os.environ, {"CI": "1"}):
        config_ci = logging_config.generate_config(level="DEBUG", logging_level=2)
        assert config_ci["handlers"]["default"]["formatter"] == "standard"

    # Test with no environment variables set
    config_default = logging_config.generate_config(level="DEBUG", logging_level=2)
    assert config_default["handlers"]["default"]["formatter"] == "colored"


# Add more test cases as needed

# This test case verifies if the `generate_config` function correctly adjusts the
# logging configuration based on the presence of environment variables `NO_COLOR`
# or `CI`. The test checks if the formatter is set to `"standard"` when either of
# these environment variables is present and `"colored"` otherwise.
# ### Unit Test
# 
# I will write a pytest unit test to ensure that the `generate_config` function
# calls `github.enable_console_debug_logging()` when the logging level is set to
# 2\.


def test_generate_config_calls_github_logging(tmp_path):
    with patch("git_mirror.logging_config.github") as mock_github:
        logging_config.generate_config(level="DEBUG", logging_level=2)

        mock_github.enable_console_debug_logging.assert_called_once()


# Add more test cases as needed

# This test case verifies that the `generate_config` function correctly calls the
# `github.enable_console_debug_logging` function when the logging level is set to
# 2\.
# ### Unit Test
# 
# I will write a pytest unit test to verify the logging configuration for
# different logging levels for individual loggers.


def test_generate_config_loggers(tmp_path):
    # Test logging level less than 2
    config_logging_level_1 = logging_config.generate_config(level="DEBUG", logging_level=1)
    assert config_logging_level_1["loggers"]["urllib3"]["level"] == "WARN"
    assert config_logging_level_1["loggers"]["httpx"]["level"] == "WARN"
    assert config_logging_level_1["loggers"]["git"]["level"] == "INFO"
    assert config_logging_level_1["loggers"]["gitlab"]["level"] == "INFO"
    assert config_logging_level_1["loggers"]["github"]["level"] == "INFO"
    assert config_logging_level_1["loggers"]["requests_cache"]["level"] == "INFO"

    # Test logging level equal to 2
    config_logging_level_2 = logging_config.generate_config(level="DEBUG", logging_level=2)
    assert config_logging_level_2["loggers"]["urllib3"]["level"] == "DEBUG"
    assert config_logging_level_2["loggers"]["httpx"]["level"] == "DEBUG"
    assert config_logging_level_2["loggers"]["git"]["level"] == "DEBUG"
    assert config_logging_level_2["loggers"]["gitlab"]["level"] == "DEBUG"
    assert config_logging_level_2["loggers"]["github"]["level"] == "DEBUG"
    assert config_logging_level_2["loggers"]["requests_cache"]["level"] == "DEBUG"


# Add more test cases as needed

# This test case ensures that the logging configuration for individual loggers
# behaves correctly for different logging levels. It checks if the loggers are set
# to the appropriate levels based on the logging level provided.
# ### Unit Test
# 
# I will write a pytest unit test to verify the logging configuration when the
# logging level is set to a value greater than or equal to 2.


def test_generate_config_logging_level_2(tmp_path):
    config = logging_config.generate_config(level="DEBUG", logging_level=2)

    assert config["handlers"]["default"]["formatter"] == "colored"
    assert config["loggers"]["urllib3"]["level"] == "DEBUG"
    assert config["loggers"]["httpx"]["level"] == "DEBUG"
    assert config["loggers"]["git"]["level"] == "DEBUG"
    assert config["loggers"]["gitlab"]["level"] == "DEBUG"
    assert config["loggers"]["github"]["level"] == "DEBUG"
    assert config["loggers"]["requests_cache"]["level"] == "DEBUG"
    assert config["handlers"]["default"]["formatter"] == "colored"

# Add more test cases as needed

# This test case verifies that the logging configuration is correctly set when the
# logging level is greater than or equal to 2. It checks if the formatter,
# handlers, and logger levels are appropriately configured for this logging level.
# ### Unit Test
# 
# I will write a pytest unit test to ensure that the logging configuration
# propagates correctly for different loggers.


def test_generate_config_logger_propagation(tmp_path):
    config = logging_config.generate_config(level="DEBUG", logging_level=2)

    assert config["loggers"]["git_mirror"]["propagate"] == False
    assert config["loggers"]["urllib3"]["propagate"] == False
    assert config["loggers"]["httpx"]["propagate"] == False
    assert config["loggers"]["git"]["propagate"] == False
    assert config["loggers"]["gitlab"]["propagate"] == False
    assert config["loggers"]["github"]["propagate"] == False
    assert config["loggers"]["requests_cache"]["propagate"] == False


# Add more test cases as needed

# This test case ensures that the logger propagation settings are correctly
# configured in the logging configuration generated by the `generate_config`
# function. It checks if the propagation is set to False for each logger.
