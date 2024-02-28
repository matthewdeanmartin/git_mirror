set -e
# These modify the file system, not safe to run just to see if they blow up.
gl_mirror clone-all --dry-run --yes
gl_mirror pull-all --dry-run --yes
gl_mirror update-from-main --dry-run --yes
gl_mirror prune-all --dry-run --yes

gh_mirror clone-all --dry-run --yes
gh_mirror pull-all --dry-run --yes
gh_mirror update-from-main --dry-run --yes
gh_mirror prune-all --dry-run --yes

# "init", "sync-config"