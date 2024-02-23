#!/bin/bash
#
# Usage:
#
#   find . -name .terraform -prune -o -name poetry.lock -execdir $(realpath update-dependencies.sh) \;
#
# Requirements:
#
# 1. GitLab authentication is configured for Git operations
# 2. GitLab authentication token is provided for the “glab” CLI utility - “glab
#    auth login”, $GITLAB_TOKEN, etc.

set -e -u

pwd

git checkout development
git pull

git for-each-ref --format '%(refname:short) %(upstream:track)' | grep -F '[gone]' | cut -f1 -d' ' | xargs -r git branch -D

echo "Updating dependencies"
git checkout -b update-dependencies || (git branch -D update-dependencies; git checkout -b update-dependencies)

poetry install
poetry update
git commit -m 'Update dependencies' poetry.lock

pre-commit autoupdate
git commit -m 'Update pre-commit hooks' .pre-commit-config.yaml

# Now to check whether we actually changed anything:
git fetch origin --prune

if git diff --quiet --exit-code origin/development; then
    git checkout development
    git branch -D update-dependencies
else
    git push -u origin -f update-dependencies:update-dependencies

    glab mr create --fill --assignee=cadams --reviewer=bhanner --remove-source-branch --target-branch=development --push --yes
    # Work around GitLab API mis-design (https://gitlab.com/gitlab-org/cli/-/issues/1344)
    retry -d 10 -t 10 -- glab mr merge --auto-merge --remove-source-branch --yes --squash
fi

git checkout development