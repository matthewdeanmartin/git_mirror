"""
Pure pypi actions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

import httpx
from rich.table import Table

from git_mirror.safe_env import load_env

load_env()

# Configure logging
LOGGER = logging.getLogger(__name__)


def pretty_print_pypi_results(results: list[dict[str, Any]]) -> Table:
    """
    Pretty prints the results of the PyPI audit using the rich library.

    Args:
        results (List[dict[str, Any]]): A list of dictionaries containing the audit results.
    """
    table = Table()

    table.add_column("Package")
    table.add_column("On PyPI")
    table.add_column("Pypi Owner")
    table.add_column("Repo last change date")
    table.add_column("PyPI last change date")
    table.add_column("Days difference")

    for result in results:
        days_difference = int(result.get("Days difference", "0"))
        style = "red" if days_difference * -1 > 60 else ""

        row_data = [
            result["Package"],
            result["On PyPI"],
            result["Pypi Owner"],
            str(result["Repo last change date"]),
            str(result["PyPI last change date"]),
            str(result["Days difference"]),
        ]

        # Apply style to the entire row if needed
        table.add_row(*row_data, style=style)
    return table


if __name__ == "__main__":
    # Example usage
    results = [
        {
            "Package": "ExamplePackage",
            "On PyPI": "Yes",
            "Pypi Owner": "OwnerName",
            "Repo last change date": "2023-01-01",
            "PyPI last change date": "2023-02-01",
            "Days difference": "-30",
        }
    ]
    pretty_print_pypi_results(results)


class PyPiManager:

    def __init__(self, pypi_owner_name: Optional[str] = None):
        self.pypi_owner_name = pypi_owner_name
        self.client = httpx.AsyncClient()  # nosec

    async def get_info(self, package_name: str) -> tuple[dict[str, Any], int]:
        """
        Asynchronously get package information from PyPI.

        Args:
            package_name (str): The name of the package to retrieve information for.

        Returns:
            Tuple[Dict[str, Any], int]: A tuple containing the package information and the HTTP status code.
        """
        pypi_url = f"https://pypi.org/pypi/{package_name}/json"
        response = await self.client.get(pypi_url)
        data = response.json()
        print(".", end="", flush=True)
        return data, response.status_code

    async def get_infos(self, package_names: list[str]) -> dict[str, tuple[dict[str, Any], int]]:
        """
        Asynchronously get information for multiple packages from PyPI.

        Args:
            package_names (List[str]): A list of package names to retrieve information for.

        Returns:
            Dict[str, Tuple[Dict[str, Any], int]]: A dictionary where keys are package names and values are tuples containing the package information and the HTTP status code.
        """
        tasks = [self.get_info(package_name) for package_name in package_names]
        results = await asyncio.gather(*tasks)
        return {package_names[i]: result for i, result in enumerate(results)}

    @classmethod
    def _get_latest_pypi_release_date(self, pypi_data: dict) -> datetime:
        """
        Parses the PyPI package data to find the release date of the latest version.

        Args:
            pypi_data (dict): The package data from PyPI.

        Returns:
            datetime: The release date of the latest version on PyPI.

        Examples:
            >>> data ={"info": {"version": "0.1.0"}, "releases": {"0.1.0": [{"upload_time": "2021-09-10T18:48:49"}]}}
            >>> PyPiManager._get_latest_pypi_release_date(data)
            datetime.datetime(2021, 9, 10, 18, 48, 49)
        """
        releases = pypi_data.get("releases", {})
        latest_version = pypi_data.get("info", {}).get("version", "")
        if latest_version in releases:
            latest_release = releases[latest_version][-1]  # Get the latest release
            release_date = datetime.strptime(latest_release["upload_time"], "%Y-%m-%dT%H:%M:%S")
            return release_date
        return datetime.now()  # Fallback if no release found
