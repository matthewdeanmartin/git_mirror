# Release Process

Releases use the changelog-driven flow in GitHub Actions.

1. Changes land on `main` with `CHANGELOG.md` updated under `[Unreleased]`.
2. The `Create Draft Release` workflow keeps a draft GitHub Release synchronized from the changelog.
3. A maintainer reviews and publishes that draft release.
4. The `Release` workflow bumps version files, opens a release PR, builds the package, and publishes to PyPI through trusted publishing.
5. After PyPI publishing succeeds, merge the generated release PR.

The package is published as `git-mirror` on PyPI. Documentation is published on Read the Docs at `https://git-mirror.readthedocs.io/`.

If the release workflow fails before publishing, delete the GitHub Release, close the generated release PR if one exists, fix the issue, and publish a new release.
