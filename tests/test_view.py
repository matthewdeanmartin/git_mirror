import os

import pytest

from git_mirror.manage_pypi import ColorTable, PrettyTable, pretty_print_pypi_results


@pytest.fixture
def sample_results():
    return [
        {
            "Package": "example_pkg",
            "On PyPI": "Yes",
            "Pypi Owner": "owner1",
            "Repo last change date": "2023-01-01",
            "PyPI last change date": "2023-01-02",
            "Days difference": "1",
        },
        {
            "Package": "stale_pkg",
            "On PyPI": "Yes",
            "Pypi Owner": "owner2",
            "Repo last change date": "2022-06-01",
            "PyPI last change date": "2022-08-01",
            "Days difference": "-61",
        },
    ]


@pytest.mark.parametrize("env_var", [("NO_COLOR",), ("CI",)])
def test_pretty_print_pypi_results_no_color_or_ci(env_var, sample_results, monkeypatch):
    monkeypatch.setenv(env_var[0], "true")
    table = pretty_print_pypi_results(sample_results)
    assert isinstance(table, PrettyTable)
    assert len(table._rows) == len(sample_results)  # Using internal _rows for test demonstration


@pytest.mark.parametrize("env_var", [("NO_COLOR",), ("CI",)])
def test_pretty_print_pypi_results_color(env_var, sample_results, monkeypatch):
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("Skipping test that requires color output on Github Actions")
        return
    monkeypatch.delenv(env_var[0], raising=False)
    table = pretty_print_pypi_results(sample_results)
    assert isinstance(table, ColorTable)
    assert len(table._rows) == len(sample_results)  # Using internal _rows for test demonstration


if __name__ == "__main__":
    pytest.main()
