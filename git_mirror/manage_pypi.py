"""
Pure pypi actions.
"""

import logging
import os
from datetime import datetime
from typing import Any, Optional, Union

import colorama
import httpx
from dotenv import load_dotenv
from prettytable import PrettyTable
from prettytable.colortable import ColorTable, Themes

load_dotenv()  # Load environment variables from a .env file, if present

# Configure logging
LOGGER = logging.getLogger(__name__)


def pretty_print_pypi_results(results: list[dict[str, Any]]) -> Union[PrettyTable, ColorTable]:
    """
    Pretty print the results of the audit.

    Returns:
        Union[PrettyTable, ColorTable]: A PrettyTable or ColorTable object.
    """
    if os.environ.get("NO_COLOR") or os.environ.get("CI"):
        table = PrettyTable()
    else:
        table = ColorTable(theme=Themes.OCEAN)
    table.field_names = [
        "Package",
        "On PyPI",
        "Pypi Owner",
        "Repo last change date",
        "PyPI last change date",
        "Days difference",
    ]

    all_rows: list[list[str]] = []

    for result in results:
        row_data = [
            result["Package"],
            result["On PyPI"],
            result["Pypi Owner"],
            result["Repo last change date"],
            result["PyPI last change date"],
            result["Days difference"],
        ]
        row_transformed = []
        # Turn values red if more than 2 months stale.
        for datum in row_data:
            try:
                days_difference = int(result["Days difference"])
            except ValueError:
                days_difference = 0
            if (days_difference * -1) > 60:
                transformed = f"{colorama.Fore.RED}{datum}{colorama.Style.RESET_ALL}"
            else:
                transformed = str(datum)
            row_transformed.append(transformed)
        all_rows.append(row_transformed)

    table.add_rows(sorted(all_rows, key=lambda x: x[0]))

    return table


class PyPiManager:

    def __init__(self, pypi_owner_name: Optional[str] = None):
        self.pypi_owner_name = pypi_owner_name
        self.client = httpx.Client()

    def get_info(self, package_name):
        pypi_url = f"https://pypi.org/pypi/{package_name}/json"

        response = self.client.get(pypi_url)
        data = response.json()
        return data, response.status_code

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
