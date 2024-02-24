set -e
# These modify the file system, not safe to run just to see if they blow up.
gl_mirror clone-all --dry-run
gl_mirror pull-all --dry-run
gl_mirror update-from-main --dry-run
gl_mirror prune-all --dry-run

gh_mirror clone-all --dry-run
gh_mirror pull-all --dry-run
gh_mirror update-from-main --dry-run
gh_mirror prune-all --dry-run

# "init", "sync-config"