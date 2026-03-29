# Pre-release Instructions

Run these steps locally before publishing to PyPI.

## 1. Sync the environment

```bash
uv sync --all-extras
```

## 2. Refresh GitHub Action pins

This step needs outbound network access to GitHub.

```bash
uv run gha-update
```

If you want to review the workflow changes before continuing:

```bash
git diff .github/workflows
```

## 3. Lint GitHub Actions

This step needs network access for schema resolution and may need GitHub access depending on your environment.

```bash
make lint-actions
```

That runs:

```bash
uv run zizmor . --config .zizmor.yml --min-severity informational --persona pedantic
uv run check-jsonschema --schemafile https://json.schemastore.org/github-workflow.json .github/workflows/*.yml
```

## 4. Run the pre-publication checks

```bash
make pre-publication
```

This covers:

- the lightweight no-fix validation path
- the CLI smoke coverage
- the bash dry-run smoke scripts
- docs and changelog checks
- GitHub Actions linting
- package build validation

## 5. Optional targeted smoke checks

If you want to inspect the CLI surface manually:

```bash
uv run python -m git_mirror.__main__ --help
uv run python -m git_mirror.__main__ list-config --config-path ./tmp_git_mirror.toml
uv run python -c "import sys; from git_mirror.__main__ import main_github; raise SystemExit(main_github(['clone-all', '--help']))"
uv run python -c "import sys; from git_mirror.__main__ import main_gitlab; raise SystemExit(main_gitlab(['build-status', '--help']))"
```

## 6. Publish

Test PyPI:

```bash
make publish_test
```

PyPI:

```bash
make publish
```

## Notes

- `fix-actions` is available if you want to refresh workflow action references directly:

```bash
make fix-actions
```

- The bash smoke scripts live in `scripts/` and are intended to stay dry-run/help-only.
- If `GITHUB_ACCESS_TOKEN` is set, run the smoke commands from a clean shell if you want to avoid unrelated networked features.
