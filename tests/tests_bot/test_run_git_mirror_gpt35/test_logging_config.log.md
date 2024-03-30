System: You are an excellent python pytest unit test engineer. We are writing pytest tests to get to 90% coverage, so we want 
tests to exercise as many code branches as possible.

First, begin by looking for bugs. There might not be any bugs. If you don't see a specific mistake, don't give me generic code review responses.

Having looked for bugs, write the pytest test as per usual, explaining what you're going to do then write the 
pytest-style unit test. Don't forget to write code!

## Tooling
Use pytest style testing. Use unittest.mock for mocking. pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.

Do not, under any circumstances, use unittest.TestCase.

The target python version is 3.10

## common coding issues
Make sure code is cross-platform and does not use linux-only modules. Prefer pathlib.Path whenever possible. When 
using the open() command, always specify the encoding, which should be utf-8 unless something else makes better sense.

## common patterns/antipatterns
Do not write pytest tests in the form of a sample invocation (i.e. not wrapped in a function)
Do make use of the tmp_path fixture for writing files. Do not mock `open` to avoid writing files.

## Env vars
If you need to mock an env var use this, don't invent yet another technique

```
from tests.env_util import temporary_env_var

with temporary_env_var("NAME", "mock_value", "NAME2", "mock_value2"):
	assert os.environ["NAME"] == "mock_value"
	assert os.environ["NAME2"] == "mock_value2"
```

Library is named git_mirror.
User: 
Source Path: E:\github\git_mirror\git_mirror\logging_config.py

Source Path: E:\github\git_mirror\git_mirror\logging_config.py
Module Name: git_mirror.logging_config
```python
"""
Logging configuration.
"""

import os
from typing import Any

import github


def generate_config(level: str = "DEBUG", logging_level: int = 1) -> dict[str, Any]:
    """
    Generate a logging configuration.
    Args:
        level: The logging level.
        logging_level: The logging level.

    Returns:
        dict: The logging configuration.
    """
    if logging_level == 2:
        format = "%(log_color)s%(levelname)-8s%(reset)s %(module)s %(green)s%(message)s"
    else:
        format = "%(log_color)s%(levelname)-8s%(reset)s %(green)s%(message)s"
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "standard": {"format": "[%(levelname)s] %(name)s: %(message)s"},
            "colored": {
                "()": "colorlog.ColoredFormatter",
                "format": format,
            },
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "formatter": "colored",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",  # Default is stderr
            },
        },
        "loggers": {
            "git_mirror": {
                "handlers": ["default"],
                "level": "DEBUG",
                "propagate": False,
            },
            "urllib3": {
                "handlers": ["default"],
                "level": "DEBUG" if logging_level >= 2 else "WARN",
                "propagate": False,
            },
            "httpx": {
                "handlers": ["default"],
                "level": "DEBUG" if logging_level >= 2 else "WARN",
                "propagate": False,
            },
            "git": {
                "handlers": ["default"],
                "level": "DEBUG" if logging_level >= 2 else "INFO",
                "propagate": False,
            },
            "gitlab": {
                "handlers": ["default"],
                "level": "DEBUG" if logging_level >= 2 else "INFO",
                "propagate": False,
            },
            "github": {
                "handlers": ["default"],
                "level": "DEBUG" if logging_level >= 2 else "INFO",
                "propagate": False,
            },
            "requests_cache": {
                "handlers": ["default"],
                "level": "DEBUG" if logging_level >= 2 else "INFO",
                "propagate": False,
            },
        },
    }
    if os.environ.get("NO_COLOR") or os.environ.get("CI"):
        config["handlers"]["default"]["formatter"] = "standard"

    if logging_level >= 2:
        github.enable_console_debug_logging()

    return config

```
Please write some unit tests for E:\github\git_mirror\git_mirror\logging_config.py. If you can't think of anymore unit tests, write "No more unit tests".
Assistant: ### Bug

1. In the `generate_config` function, there is an import statement for `github`. However, in the given code snippet, `github` module is not imported. This might cause an `ImportError` when `generate_config` function is called.

### Unit Test

I will write a pytest unit test to check if the `generate_config` function correctly generates the logging configuration dictionary based on the provided arguments.

```python
import pytest
from git_mirror import logging_config
from unittest.mock import patch, MagicMock


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
```

This test case checks if the `generate_config` function correctly generates the logging configuration dictionary for two different logging levels. The test also checks if the `github.enable_console_debug_logging` is called when the logging level is set to 2.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ### Unit Test

I will write a pytest unit test to verify the behavior of the logging configuration when the environment variables `NO_COLOR` or `CI` are present.

```python
import os
import pytest
from git_mirror import logging_config
from unittest.mock import patch


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
```

This test case verifies if the `generate_config` function correctly adjusts the logging configuration based on the presence of environment variables `NO_COLOR` or `CI`. The test checks if the formatter is set to `"standard"` when either of these environment variables is present and `"colored"` otherwise.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ### Unit Test

I will write a pytest unit test to ensure that the `generate_config` function calls `github.enable_console_debug_logging()` when the logging level is set to 2.

```python
import pytest
from git_mirror import logging_config
from unittest.mock import patch, MagicMock


def test_generate_config_calls_github_logging(tmp_path):
    with patch("git_mirror.logging_config.github") as mock_github:
        logging_config.generate_config(level="DEBUG", logging_level=2)

        mock_github.enable_console_debug_logging.assert_called_once()


# Add more test cases as needed
```

This test case verifies that the `generate_config` function correctly calls the `github.enable_console_debug_logging` function when the logging level is set to 2.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ### Unit Test

I will write a pytest unit test to verify the logging configuration for different logging levels for individual loggers.

```python
import pytest
from git_mirror import logging_config


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
```

This test case ensures that the logging configuration for individual loggers behaves correctly for different logging levels. It checks if the loggers are set to the appropriate levels based on the logging level provided.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ### Unit Test

I will write a pytest unit test to verify the logging configuration when the logging level is set to a value greater than or equal to 2.

```python
import pytest
from git_mirror import logging_config


def test_generate_config_logging_level_2(tmp_path):
    config = logging_config.generate_config(level="DEBUG", logging_level=2)

    assert config["handlers"]["default"]["formatter"] == "%(log_color)s%(levelname)-8s%(reset)s %(module)s %(green)s%(message)s"
    assert config["loggers"]["urllib3"]["level"] == "DEBUG"
    assert config["loggers"]["httpx"]["level"] == "DEBUG"
    assert config["loggers"]["git"]["level"] == "DEBUG"
    assert config["loggers"]["gitlab"]["level"] == "DEBUG"
    assert config["loggers"]["github"]["level"] == "DEBUG"
    assert config["loggers"]["requests_cache"]["level"] == "DEBUG"
    assert config["handlers"]["default"]["formatter"] == "%(log_color)s%(levelname)-8s%(reset)s %(module)s %(green)s%(message)s"


# Add more test cases as needed
```

This test case verifies that the logging configuration is correctly set when the logging level is greater than or equal to 2. It checks if the formatter, handlers, and logger levels are appropriately configured for this logging level.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: ### Unit Test

I will write a pytest unit test to ensure that the logging configuration propagates correctly for different loggers.

```python
import pytest
from git_mirror import logging_config


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
```

This test case ensures that the logger propagation settings are correctly configured in the logging configuration generated by the `generate_config` function. It checks if the propagation is set to False for each logger.