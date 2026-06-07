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
