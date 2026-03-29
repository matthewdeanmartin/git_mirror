# AI Agent Guide

This project includes a `Makefile` with specialized tasks for AI agents to use.

## Environment Management

This repository uses **uv** for dependency management.
- Always use `uv run` to execute commands.
- The virtual environment is located at `./.venv`.
- Never install libraries into the global Python environment.
- To sync dependencies, use `uv sync --all-extras`.
- In PowerShell sandboxes, point uv at a workspace-local cache so it does not try to use a blocked global cache directory.
- Preferred pattern for ad hoc commands: `$env:UV_CACHE_DIR='.uv-cache'; uv run ...`
- For pytest in sandboxes, also use a workspace-local temp base that is safe to recreate, for example: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest --basetemp=tmp_pytest ...`
- If you are using `make`, prefer the provided targets because the `Makefile` exports a local `UV_CACHE_DIR` for you.

## Recommended Tasks for AI Agents

When performing automated checks, AI agents should use the `*-llm` tasks to avoid side-effects like formatting which can cause synchronization issues in the agent's internal state.
...
- `make check-llm`: Runs all primary checks (mypy, tests, pylint, bandit, pre-commit) without formatting files.
- `make pylint-llm`: Runs ruff (without fix) and pylint.
- `make pre-commit-llm`: Runs pre-commit checks while skipping hooks that modify files (like black, isort, ruff).
- `make check_all-llm`: Runs documentation, markdown, spelling, and changelog checks.

## Workflow for AI Agents

1. **Modify code.**
2. **Run `make check-llm`** to verify the changes.
3. If checks fail, fix the code and repeat.
4. Do **not** run `make black`, `make isort`, or `make pylint` (without `-llm`) unless specifically requested, as these will modify the files on disk and may invalidate your current view of the codebase.
