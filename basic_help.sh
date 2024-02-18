set -e
# make sure this doesn't fail on TERM not set
clear || true
git_mirror --help
git_mirror --version
git_mirror --version --verbose
git_mirror --version --verbose --verbose