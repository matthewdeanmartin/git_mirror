set -e
# Just the commands that don't do anything to the file system.
git_mirror --help
git_mirror --version
git_mirror --version --verbose
git_mirror --version --verbose --verbose
echo
# need limit!
echo "Testing: gl_mirror list-repos"
gl_mirror list-repos
echo "Testing: gl_mirror local-changes"
gl_mirror local-changes
echo "Testing: gl_mirror not-repo"
gl_mirror not-repo
echo
# need limit!
echo "Testing: gh_mirror list-repos"
gh_mirror list-repos
echo "Testing: gh_mirror local-changes"
gh_mirror local-changes
echo "Testing: gh_mirror not-repo"
gh_mirror not-repo
echo
echo "Testing: git_mirror list-config"
git_mirror list-config
echo
# need limit!
echo "Testing: gh_mirror pypi-status"
gh_mirror pypi-status
echo
echo "Testing: gh_mirror show-account"
gh_mirror show-account
echo "Testing: gl_mirror show-account"
gl_mirror show-account

# These modify the file system, not safe to run just to see if they blow up.
# clone-all", "pull-all", "update-from-main", "prune-all"],
# "init", "sync-config"