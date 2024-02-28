import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from git_mirror.ui import console_with_theme

# Configure logging
LOGGER = logging.getLogger(__name__)

LOADED = False

console = console_with_theme()


def load_env() -> None:
    global LOADED  # noqa
    if LOADED:
        return
    try:
        # check if .env file exists in root of home directory and if has any of the 3 expected
        # GITHUB_ACCESS_TOKEN, GITLAB_ACCESS_TOKEN, SELFHOSTED_ACCESS_TOKEN
        global_env = Path.home() / ".env"
        if global_env.exists() and global_env.is_file():
            found = 0
            with open(global_env, encoding="utf-8") as f:
                for line in f:
                    if "GITHUB_ACCESS_TOKEN" in line:
                        found += 1
                    if "GITLAB_ACCESS_TOKEN" in line:
                        found += 1
                    if "SELFHOSTED_ACCESS_TOKEN" in line:
                        found += 1
            if found > 0:
                LOGGER.info(f"Found .env file with expected tokens in {global_env}")
                load_dotenv(global_env)
                LOADED = True
                return

        load_dotenv()  # Load environment variables from .env file in cwd() if present
        LOADED = True
    except Exception as e:
        console.print(f"Error loading .env file: {e}", style="danger")
        console.print("Continuing without .env file.", style="danger")


def env_info() -> None:
    console.print(f".env file in current folder exists: {(Path.cwd() / '.env').exists()}")
    console.print(f".env file in home folder exists: {(Path.home() / '.env').exists()}")
    console.print(f"GITHUB_ACCESS_TOKEN exists: {bool(os.getenv('GITHUB_ACCESS_TOKEN'))}")
    console.print(f"GITLAB_ACCESS_TOKEN exists: {bool(os.getenv('GITLAB_ACCESS_TOKEN'))}")
    console.print(f"SELFHOSTED_ACCESS_TOKEN exists: {bool(os.getenv('SELFHOSTED_ACCESS_TOKEN'))}")


if __name__ == "__main__":
    load_env()
    env_info()
