import cli_tool_audit as cta
import cli_tool_audit.models as models

from git_mirror.ui import console_with_theme

console = console_with_theme()


def check_tool_availability():
    """
    This function is used to check the availability of the 3rd party cli tools
    """
    git_version = models.CliToolConfig(
        name="git",
        version=">=1.7.*",
        schema=models.SchemaType.SEMVER,
    )
    poetry_version = models.CliToolConfig(
        name="poetry",
        version="*",
        schema=models.SchemaType.SEMVER,
    )
    to_check = {
        "git": git_version,
        "poetry": poetry_version,
    }
    results = cta.process_tools(to_check, no_cache=True, disable_progress_bar=True)
    for result in results:
        console.print(f"{result.tool}", style="underline")
        if result.is_compatible:
            console.print(f"{result.parsed_version}: available {result.is_available}, {result.is_compatible}")
        else:
            console.print(f"{result.parsed_version}: available {result.is_available}, {result.is_compatible}", "danger")


if __name__ == "__main__":
    check_tool_availability()
