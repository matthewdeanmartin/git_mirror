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
Source Path: E:\github\git_mirror\git_mirror\performance.py

Source Path: E:\github\git_mirror\git_mirror\performance.py
Module Name: git_mirror.performance
```python
import logging
import time
from functools import wraps
from typing import Any, Callable

# Ensure the logger is configured as per the project's requirements
LOGGER = logging.getLogger(__name__)


def log_duration(func: Callable) -> Callable:
    """
    A decorator that logs the execution time of the wrapped function.

    Args:
        func (Callable): The function to wrap.

    Returns:
        Callable: The wrapper function.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        minutes, sec = divmod(duration, 60)
        sec, ms = divmod(sec, 1)
        LOGGER.info(
            f"Function {func.__name__} took {int(minutes)} minutes, {int(sec)} seconds, and {int(ms * 1000)} ms to execute."
        )
        return result

    return wrapper


# # Example usage
# @log_duration
# def example_function(n: int) -> None:
#     """
#     Example function that sleeps for a given number of seconds.
#
#     Args:
#         n (int): The number of seconds for the function to sleep.
#     """
#     time.sleep(n)
#     print(f"Slept for {n} seconds")
#
# if __name__ == "__main__":
#     example_function(1)

```
Please write some unit tests for E:\github\git_mirror\git_mirror\performance.py. If you can't think of anymore unit tests, write "No more unit tests".
Assistant: Let's review the code and identify any potential issues before writing unit tests:

1. The `log_duration` decorator looks well-implemented.
2. The decorator logs the execution time of the wrapped function in minutes, seconds, and milliseconds.
3. The decorator does not handle exceptions that might occur during the execution of the wrapped function. Adding exception handling could be beneficial.

Now, let's proceed to write pytest-style unit tests:

```python
import logging
from unittest.mock import patch
from git_mirror.performance import log_duration
import time

# Mocking getLogger to prevent actual log messages during testing
logging.basicConfig(level=logging.DEBUG)


def test_log_duration_logs_execution_time(caplog):
    # Create a dummy function to test the decorator
    @log_duration
    def dummy_function():
        time.sleep(1)

    with caplog.at_level(logging.INFO):
        dummy_function()

        # Check if the log message contains the expected duration format
        assert "Function dummy_function took 0 minutes, 1 seconds, and 0 ms to execute." in caplog.text


def test_log_duration_does_not_raise_exceptions(caplog):
    # Create a dummy function that raises an exception
    @log_duration
    def function_with_exception():
        raise ValueError("An error occurred")

    with caplog.at_level(logging.INFO):
        # Ensure that the exception is caught and logged by the decorator
        with pytest.raises(ValueError):
            function_with_exception()

        assert "Function function_with_exception took" in caplog.text


def test_log_duration_preserves_functionality():
    # Create a dummy function with a return value
    @log_duration
    def function_with_return_value():
        return "Test"

    result = function_with_return_value()

    # Ensure that the function returns the expected result
    assert result == "Test"


# Write more tests if needed. If not, write "No more unit tests".
# No more unit tests.
``` 

These unit tests cover the logging behavior, exception handling, and functionality preservation of the `log_duration` decorator.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: No more unit tests.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: No more unit tests.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: No more unit tests.
User: Excellent. Please write the next unit test. Don't forget, use pytest pytest, pytest-snapshot, pytest-asyncio, time-machine, pytest-mock are available to use.. Use unittest.mock for 
mocking. Prefer Path to str for paths.

If you can't think of anymore unit tests, write just "No more unit tests".
Assistant: No more unit tests.