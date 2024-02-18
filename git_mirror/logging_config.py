"""
Logging configuration.
"""

import os
from typing import Any

import github


def generate_config(level: str = "DEBUG", double_verbose: bool = False) -> dict[str, Any]:
    """
    Generate a logging configuration.
    Args:
        level: The logging level.
        double_verbose: Whether to enable double verbose logging.

    Returns:
        dict: The logging configuration.
    """
    if double_verbose:
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
                "level": "DEBUG" if double_verbose else "WARN",
                "propagate": False,
            },
            "httpx": {
                "handlers": ["default"],
                "level": "DEBUG" if double_verbose else "WARN",
                "propagate": False,
            },
            "git": {
                "handlers": ["default"],
                "level": "DEBUG" if double_verbose else "INFO",
                "propagate": False,
            },
            "gitlab": {
                "handlers": ["default"],
                "level": "DEBUG" if double_verbose else "INFO",
                "propagate": False,
            },
            "github": {
                "handlers": ["default"],
                "level": "DEBUG" if double_verbose else "INFO",
                "propagate": False,
            },
        },
    }
    if os.environ.get("NO_COLOR") or os.environ.get("CI"):
        config["handlers"]["default"]["formatter"] = "standard"

    if double_verbose:
        github.enable_console_debug_logging()

    return config
