# Codex Notes: Working Without Write Access

When this repository is used from a restricted Codex harness, most of the friction comes from tooling caches rather than the project itself.

## Key Lessons

- Do not spend time repeatedly debugging `uv` cache failures in the restricted harness.
- If `uv` reports access denied for `.uv-cache\sdists-v9\.git` or the global uv cache, the command is being blocked by the harness or by a stale cache marker.
- Prefer a fresh writable cache when possible:

```powershell
$env:UV_CACHE_DIR='C:\tmp\uv-cache-gitmirror'
uv run ...
```

- In a harness with no write access, avoid commands that need to create, update, or repair:
  - `.venv`
  - `.uv-cache`
  - `dist`
  - `site`
  - `htmlcov`
  - `tmp_pytest`

- If checks are required but the harness blocks writes, document the intended commands instead of burning time on cache repair.

## Useful Commands When Writes Are Allowed

```powershell
$env:UV_CACHE_DIR='C:\tmp\uv-cache-gitmirror'; uv sync --all-extras
$env:UV_CACHE_DIR='C:\tmp\uv-cache-gitmirror'; uv run mkdocs build --strict
$env:UV_CACHE_DIR='C:\tmp\uv-cache-gitmirror'; uv run changelogmanager validate
$env:UV_CACHE_DIR='C:\tmp\uv-cache-gitmirror'; uv run check-jsonschema --schemafile https://json.schemastore.org/github-workflow.json .github/workflows/*.yml
$env:UV_CACHE_DIR='C:\tmp\uv-cache-gitmirror'; uv build --no-sources
$env:UV_CACHE_DIR='C:\tmp\uv-cache-gitmirror'; make check-llm
```

## Current Context From This Session

- The requested docs and release-workflow work was implemented before this note was added.
- Targeted verification had passed for:
  - `uv run mkdocs build --strict`
  - `uv run changelogmanager validate`
  - `uv run check-jsonschema --schemafile https://json.schemastore.org/github-workflow.json .github/workflows/*.yml`
  - `uv build --no-sources`
  - `uv run ruff check`
  - the targeted Hypothesis test for `normalize_url`
- A full `make check-llm` run was started after fixing lint and a flaky Hypothesis generator, but the user interrupted it and asked Codex to stop.

## Behavioral Reminder

If the user asks for docs or metadata work, prioritize the docs and metadata. Do not let harness-specific cache issues consume the session. Record the verification limitation clearly and stop.
