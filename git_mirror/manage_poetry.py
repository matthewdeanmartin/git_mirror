import logging
import os
import subprocess  # nosec

import git

from git_mirror.custom_types import SourceHost

logger = logging.getLogger(__name__)


def clean_gone_branches(repo: git.Repo) -> None:
    """Clean branches that are gone from remote.

    Args:
        repo: The Git repository object.
    """
    gone_branches = [
        ref.split()[0]
        for ref in repo.git.for_each_ref("--format=%(refname:short) %(upstream:track)").split("\n")
        if "[gone]" in ref
    ]
    for branch in gone_branches:
        repo.git.branch("-D", branch)


class PoetryManager:
    def __init__(self, host: SourceHost):
        self.host = host

    def update_dependencies(
        self, main_branch: str, dependency_update_branch: str, project_id: int, repo_name: str, user: str, reviewer: str
    ) -> None:
        """Update project dependencies and create a merge request if changes are made.

        Args:
            main_branch: The main branch name.
            dependency_update_branch: The dependency update branch name.
            project_id: The ID of the GitLab project.
            repo_name: The name of the Github repository.
            user: Username for assigning the merge request.
            reviewer: Username for reviewing the merge request.
        """
        # Setup
        repo = git.Repo(os.getcwd())
        origin = repo.remotes.origin

        # Checkout and pull main branch
        repo.git.checkout(main_branch)
        origin.pull()

        # Clean gone branches (Should this really be here?)
        # clean_gone_branches(repo)

        logger.info("Updating dependencies")
        try:
            repo.git.checkout("-b", dependency_update_branch)
        except git.exc.GitCommandError:
            repo.git.branch("-D", dependency_update_branch)
            repo.git.checkout("-b", dependency_update_branch)

        # Update dependencies using Poetry
        subprocess.run(["poetry", "install"], check=True, shell=True)  # nosec
        subprocess.run(["poetry", "update"], check=True, shell=True)  # nosec
        repo.git.add("poetry.lock")
        repo.index.commit("Update dependencies")

        # get rid of local branches that are gone from remote
        # prune should be a separate step
        origin.fetch(prune=False)

        # Check if there are changes
        if repo.git.diff("--quiet", "--exit-code", f"origin/{main_branch}"):
            # no changes, nevermind.
            repo.git.checkout(main_branch)
            repo.git.branch("-D", dependency_update_branch)
        else:
            # origin.push('-f', f'{dependency_update_branch}:{dependency_update_branch}', set_upstream=True)
            push_info = origin.push(
                refspec=f"{dependency_update_branch}:{dependency_update_branch}", force=True, set_upstream=True
            )
            logger.debug(push_info)

            self.host.merge_request(
                dependency_update_branch, main_branch, "Update Poetry lock file", reviewer, project_id, repo_name
            )

        repo.git.checkout(main_branch)


# if __name__ == "__main__":
#     update_dependencies(
#         main_branch=os.environ.get("MAIN_BRANCH"),
#         dependency_update_branch=os.environ.get("DEPENDENCY_UPDATE_BRANCH"),
#         gitlab_token=os.environ.get("GITLAB_TOKEN"),
#         gitlab_url=os.environ.get("GITLAB_URL", "https://gitlab.com"),
#         project_id=int(os.environ.get("PROJECT_ID")),
#         user=os.environ.get("USER"),
#         reviewer=os.environ.get("REVIEWER")
#     )
