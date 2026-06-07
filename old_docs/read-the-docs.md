# Read the Docs

The documentation site is built with MkDocs and published by Read the Docs.

The required Read the Docs configuration file is `.readthedocs.yaml` at the repository root. Keep it at the top level of the default branch; moving it into `docs/` or renaming it will make Read the Docs report that the config file was not found. See the official Read the Docs [configuration file reference](https://docs.readthedocs.com/platform/en/latest/config-file/v2.html) and [MkDocs guide](https://docs.readthedocs.com/platform/stable/intro/mkdocs.html).

The build uses:

- `.readthedocs.yaml` for the Read the Docs build environment.
- `mkdocs.yml` for site navigation, theme, plugins, and strict validation.
- `docs/requirements.txt` for documentation build dependencies.
- `docs/*.md` for the published pages.

## Local verification

Use the same documentation toolchain locally:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mkdocs build --strict
```

If the Codex harness blocks cache writes, use a fresh cache path:

```powershell
$env:UV_CACHE_DIR='C:\tmp\uv-cache-gitmirror'; uv run mkdocs build --strict
```

## Read the Docs project settings

The Read the Docs project should point at this repository and build from the branch that contains `.readthedocs.yaml`. The config file tells Read the Docs to:

- Use Ubuntu 24.04.
- Use Python 3.13.
- Install `docs/requirements.txt`.
- Build the site from `mkdocs.yml`.

No Sphinx configuration is required.
