import logging
import os
import traceback
from typing import Optional

import github as gh
from github.Issue import Issue
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

LOGGER = logging.getLogger(__name__)


class BugReporter:
    def __init__(self, token: str, repository_name: str) -> None:
        """
        Initializes the bug reporter with the GitHub API token and repository name.

        Args:
            token (str): The GitHub API token.
            repository_name (str): The full name of the repository (e.g., "user/repo").
        """
        self.github = gh.Github(token)
        self.repository_name = repository_name
        self.repo = self.github.get_repo(repository_name)
        self.user = self.github.get_user()

    def mask_secrets(self, text: str) -> str:
        """
        Masks any secrets in the given text with asterisks.

        Args:
            text (str): The text to mask.

        Returns:
            str: The masked text.
        """
        token_names = ("GITHUB_ACCESS_TOKEN", "GITLAB_ACCESS_TOKEN", "SELFHOSTED_ACCESS_TOKEN")
        for token in token_names:
            if os.environ.get(token):
                secret = os.environ.get(token, "")  # default to make mypy happy
                text = text.replace(secret, "****")

        return text

    def report_issue(self, issue_title: str, issue_body: str) -> Optional[Issue]:
        """
        Creates an issue in the specified GitHub repository.

        Args:
            issue_title (str): The title of the issue to be created.
            issue_body (str): The body text of the issue, providing details.
        """
        try:
            issue: Issue = self.repo.create_issue(title=issue_title, body=issue_body)
            print(f"Issue titled '{issue_title}' created in {self.repository_name}.")
            return issue
        except gh.GithubException as e:
            print(f"Failed to create issue in {self.repository_name}: {e}")
        return None

    def find_existing_issue_by_title_and_creator(self, title: str) -> Optional[Issue]:
        """
        Searches for an existing issue by title and the issue creator.

        Args:
            title (str): The title of the issue to search for.

        Returns:
            Optional[Issue]: The found issue if any; otherwise, None.
        """
        issues = self.repo.get_issues(state="all")
        for issue in issues:
            if issue.title == title and issue.user.login == self.user.login:
                LOGGER.info(f"Found existing issue titled '{title}' by {self.user.login}.")
                return issue
        LOGGER.info(f"No existing issue titled '{title}' found by {self.user.login}.")
        return None

    def handle_exception_and_report(self, exc_type, exc_value, exc_traceback) -> None:
        """
        Captures the current exception, checks for existing reports, asks the user for permission
        to report it as a bug, and creates an issue on GitHub if permission is granted and no
        existing report is found.
        """
        if isinstance(exc_value, KeyboardInterrupt):
            return
        # exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
        issue_body = self.mask_secrets(f"An exception occurred:\n{''.join(traceback_details)}")
        issue_title = self.mask_secrets(f"Bug report: {exc_value}")

        # Check if the issue already exists
        existing_issue = self.find_existing_issue_by_title_and_creator(issue_title)
        if existing_issue:
            print(f"An issue with the title '{issue_title}' has already been reported by you.")
            return

        # Ask the user for permission to report the bug
        console = Console()
        summary = Text.assemble(
            ("Issue Title: ", "bold cyan"),
            f"{issue_title}\n",
            ("Issue Body: ", "bold cyan"),
            f"{issue_body}\n",
        )
        console.print(Panel(summary, title="Github Issue"))

        response = input(
            "An error occurred. Would you like to report this bug? "
            "It will be posted as a public issue using your gitlab token as credentials. (yes/no): "
        )
        if response.lower().startswith("y"):
            issue = self.report_issue(issue_title, issue_body)
            if issue:
                print(f"Bug report created at: {issue.html_url}")
        else:
            print("You can manually report this issue at https://github.com/matthewdeanmartin/git_mirror/issues")
            LOGGER.info("Bug report canceled by the user.")
