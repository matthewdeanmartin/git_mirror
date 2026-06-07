# Installation

Install with `pipx` so the command-line tools live in an isolated environment:

```bash
pipx install git-mirror
```

The package requires Python 3.9 or newer.

The installed commands are:

- `git_mirror`: full command surface; pass `--host github` or `--host selfhosted` for repository commands.
- `gh_mirror`: GitHub shortcut; uses `github` as the host.
- `sh_mirror`: self-hosted GitHub Enterprise shortcut; uses `selfhosted` as the host.
- `git_mirror_gui`: starts the desktop GUI.

For local development, use `uv`:

```bash
uv sync --all-extras
uv run git_mirror --help
```

The project is developed and tested with the dependency set in `uv.lock`. Do not install development dependencies into the global Python environment.
