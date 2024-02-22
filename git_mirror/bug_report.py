import logging
from github import Github, GithubException
from github.Issue import Issue
import sys
import traceback

LOGGER = logging.getLogger(__name__)

class BugReporter:
    def __init__(self, token: str, repository_name: str) -> None:
        """
        Initializes the bug reporter with the GitHub API token and repository name.

        Args:
            token (str): The GitHub API token.
            repository_name (str): The full name of the repository (e.g., "user/repo").
        """
        self.github = Github(token)
        self.repository_name = repository_name
        self.repo = self.github.get_repo(repository_name)
        self.user = self.github.get_user()

    def report_issue(self, issue_title: str, issue_body: str) -> None:
        """
        Creates an issue in the specified GitHub repository.

        Args:
            issue_title (str): The title of the issue to be created.
            issue_body (str): The body text of the issue, providing details.
        """
        try:
            self.repo.create_issue(title=issue_title, body=issue_body)
            LOGGER.info(f"Issue titled '{issue_title}' created in {self.repository_name}.")
        except GithubException as e:
            LOGGER.error(f"Failed to create issue in {self.repository_name}: {e}")

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

    def handle_exception_and_report(self) -> None:
        """
        Captures the current exception, checks for existing reports, asks the user for permission
        to report it as a bug, and creates an issue on GitHub if permission is granted and no
        existing report is found.
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
        issue_body = f"An exception occurred:\n{''.join(traceback_details)}"
        issue_title = f"Bug report: {exc_value}"

        # Check if the issue already exists
        existing_issue = self.find_existing_issue_by_title_and_creator(issue_title)
        if existing_issue:
            print(f"An issue with the title '{issue_title}' has already been reported by you.")
            return

        # Ask the user for permission to report the bug
        response = input("An error occurred. Would you like to report this bug? (yes/no): ")
        if response.lower().startswith('y'):
            self.report_issue(issue_title, issue_body)
        else:
            LOGGER.info("Bug report canceled by the user.")