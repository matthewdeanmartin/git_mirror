# AI Agent Guide

This project includes a `Makefile` with specialized tasks for AI agents to use.

## Environment Management

This repository uses **uv** for dependency management.
- Always use `uv run` to execute commands.
- The virtual environment is located at `./.venv`.
- Never install libraries into the global Python environment.
- To sync dependencies, use `uv sync --all-extras`.

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
