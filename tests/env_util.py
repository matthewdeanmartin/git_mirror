import os
from contextlib import contextmanager


@contextmanager
def temporary_env_var(key, value):
    """
    Temporarily set an environment variable and revert it back after the block of code.

    :param key: The environment variable key
    :param value: The value to set for the environment variable
    """
    original_value = os.environ.get(key)
    try:
        os.environ[key] = value
        yield
    finally:
        # Revert the environment variable to its original state
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


if __name__ == "__main__":
    # Usage in tests
    with temporary_env_var("ENV_VAR_NAME", "new_value"):
        assert os.environ["ENV_VAR_NAME"] == "new_value"
