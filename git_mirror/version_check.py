import httpx
from packaging import version
from packaging.version import Version

# Import the current version of your package
from git_mirror.__about__ import __version__


def call_pypi_with_version_check(package_name: str, current_version: str) -> tuple[bool, Version]:
    """
    Synchronously checks if the latest version of the package on PyPI is greater than the current version.

    Args:
        package_name (str): The name of the package to check.
        current_version (str): The current version of the package.

    Returns:
        bool: True if the latest version on PyPI is greater than the current version, False otherwise.
    """
    pypi_url = f"https://pypi.org/pypi/{package_name}/json"
    response = httpx.get(pypi_url)
    response.raise_for_status()  # Raises an exception for 4XX/5XX responses
    data = response.json()
    latest_version = data["info"]["version"]

    return version.parse(latest_version) > version.parse(current_version), version.parse(latest_version)


# Example usage
def display_version_check_message() -> None:
    try:
        package_name = "git_mirror"
        available, new_version = call_pypi_with_version_check(package_name, __version__)
        if available:
            print(f"A newer version of {package_name} is available on PyPI. Upgrade to {new_version}.")
    except httpx.HTTPError as e:
        print(f"An error occurred while checking the latest version: {e}")


if __name__ == "__main__":
    display_version_check_message()
