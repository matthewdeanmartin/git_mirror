# git_mirror Refocus Plan

A breaking-change refactor (target: `2.0.0`) to sharpen the value proposition,
drop GitLab, renamespace generic utilities, add real credential storage, and
build out the core "batch git over a folder of repos" experience.

## Value proposition (the reason to live)

> **Point git_mirror at a folder full of GitHub repos and operate on all of them
> at once — see their combined state, keep them in sync, and clean them up —
> safely, in parallel, without 30 terminal tabs.**

Everything that does not serve that sentence is either a generic utility (moves
to `utils/`) or gets cut. GitLab is cut because GitHub's and GitLab's
project/group/visibility models differ enough that supporting both forced
lowest-common-denominator design and a confusing `host` concept.

### Decisions locked in (from the boss)

- **Drop GitLab entirely.** GitHub only.
- **`selfhosted` survives as GitHub Enterprise only** (GHE / GitHub-compatible
  API). It is no longer a "github-or-gitlab" switch. The `host_type` field on a
  selfhosted config may only be `github`.
- **Add `keyring` (OS keychain) with `.env`/env-var fallback.** Non-breaking,
  opt-in migration. Plaintext `.env` keeps working but is no longer the
  recommended path.
- **Renamespace generic modules** into `git_mirror/utils/*` (like `bug_report`).
- **Build out all four core capabilities:** repo selection/filtering, unified
  status dashboard, safe batch mutations, and merge the duplicate
  router+services orchestration layers into one core API.
- **GUI is deferred.** Keep it importable/working but do not invest; it consumes
  the new core API once that settles.

---

## Current-state notes (why these phases)

- **Two orchestration layers have already drifted:** `router.py` (CLI) and
  `services.py` (GUI) each re-implement clone/pull/list-repos/build-status with
  subtly different filtering. This duplication is the biggest architectural debt,
  bigger than GitLab. Phase 4 collapses them.
- **No keychain today.** `pat_init._save_pat` writes the PAT into `~/.env` or
  `./.env` via `python-dotenv`'s `set_key`; everything reads it back through
  `os.getenv`. The README still instructs users to export env vars. (Answer to
  "are we still not using keychain?": correct, we are not.)
- **GitLab/selfhosted touch surface** (~125 references across):
  `manage_gitlab.py`, `pat_init_gitlab.py`, `manage_config.py`, `router.py`,
  `services.py`, `__main__.py`, `gui/app.py`, `safe_env.py`, `bug_report.py`,
  `logging_config.py`, `__about__.py`, `__init__.py`, plus `tests/tests_human/test_gitlab/*`.
- **Generic, repo-agnostic modules** ("could be any app"): `bug_report.py`,
  `safe_env.py`, `file_system.py`, `dummies.py`, `performance.py`,
  `version_check.py`, `check_cli_deps.py`, `logging_config.py`, `ui.py`.

---

## Phase 0 — Guardrails before breaking things

Goal: make the breaking change safe to perform.

1. Tag/branch the pre-refactor state so `1.x` is recoverable.
2. Confirm the test suite runs green today: `uv run pytest`. Record which tests
   are GitLab-only (they will be deleted in Phase 1, not "fixed").
3. Add a short `CHANGELOG`/migration stub for `2.0.0` capturing the breaking
   changes as they land.

Exit criteria: clean baseline test run captured; recovery point exists.

---

## Phase 1 — Drop GitLab (the breaking cut)

Goal: GitHub-only. `selfhosted` means GitHub Enterprise.

1. **Delete GitLab modules:** `manage_gitlab.py`, `pat_init_gitlab.py`, and
   `tests/tests_human/test_gitlab/`.
2. **`manage_config.py`:**
   - `SUPPORTED_HOSTS` → `("github", "selfhosted")`.
   - `ConfigData.host_type` may only be `github`. Drop `group_id` and any
     GitLab-only fields from the dataclass and from `_write_config` /
     `load_config`.
   - `ask_for_section`: remove the "github or gitlab?" question for selfhosted;
     selfhosted is always GitHub-type. Drop the group-id prompt.
   - `_default_host_url` / `_normalize_url`: GitHub-only.
   - `doctor` / `_run_checks`: drop the gitlab branch; always validate via
     `utils`-side GitHub PAT check.
3. **`router.py`:** remove the `gitlab` backend branch, the `clone_group` /
   `group_id` special-case in `clone-all`, and collapse the `selfhosted`
   resolution so it always builds a `GithubRepoManager` pointed at the configured
   GHE `host_url`.
4. **`services.py`:** remove every `host_type == "gitlab"` branch in
   `list_repos_data`, `clone_all_repos`, `get_build_statuses`,
   `get_token_for_host`.
5. **`__main__.py`:**
   - Remove `main_gitlab` / `--host gitlab` / `gl_mirror` program detection.
   - `host_specific_args`: drop `--group-id` and the gitlab `--domain` framing
     (keep a generic `--domain` for GHE base URL). `host` choices →
     `["github", "selfhosted"]`.
   - Keep `gh_mirror` and `sh_mirror`; drop `gl_mirror`.
6. **`pyproject.toml`:**
   - Remove `python-gitlab` dependency.
   - Remove the `gl_mirror` entry point.
   - Update `description` / `keywords` to drop gitlab.
7. **`README.md`:** rewrite around GitHub + GHE only; remove the gitlab config
   block; note the `2.0.0` breaking change.
8. **`safe_env.py`, `bug_report.py`, `logging_config.py`, `gui/app.py`:** strip
   `GITLAB_ACCESS_TOKEN` / gitlab references. (`selfhosted` keeps
   `SELFHOSTED_ACCESS_TOKEN`.)

Exit criteria: no `gitlab` symbol remains in `git_mirror/` (verify with a grep
gate, see Phase 8); `uv run pytest` green minus the deleted gitlab tests; a
github clone-all/pull-all still works end to end.

---

## Phase 2 — Renamespace generic modules into `git_mirror/utils/*`

Goal: separate "any-app plumbing" from "the repo-batch core."

1. Create `git_mirror/utils/__init__.py`.
2. Move (and update imports for) the repo-agnostic modules:
   - `bug_report.py` → `utils/bug_report.py`
   - `safe_env.py` → `utils/safe_env.py`
   - `file_system.py` → `utils/file_system.py`
   - `dummies.py` → `utils/dummies.py`
   - `performance.py` → `utils/performance.py`
   - `version_check.py` → `utils/version_check.py`
   - `check_cli_deps.py` → `utils/check_cli_deps.py`
   - `logging_config.py` → `utils/logging_config.py`
   - `ui.py` → `utils/ui.py`
3. Leave **core** modules at top level: `manage_git.py`, `manage_github.py`,
   `manage_config.py`, `router.py`/new core, `menu.py`, `custom_types.py`,
   `__main__.py`.
4. Update every importer (`from git_mirror.ui` → `from git_mirror.utils.ui`,
   etc.) and the test imports under `tests/tests_bot/...` and `tests/tests_human/...`.
5. Decide on back-compat shims: since this is already a `2.0.0` breaking
   release, **no shims** — move cleanly.

Exit criteria: `git_mirror/` top level contains only core + `utils/`; imports
resolve; `uv run pytest` green.

---

## Phase 3 — Credential storage via keyring (with .env fallback)

Goal: stop recommending plaintext tokens; use the OS keychain.

1. Add `keyring` dependency.
2. New `git_mirror/utils/credentials.py` with a small `CredentialStore` seam:
   - `get_token(host_name) -> str | None`: resolution order
     **keyring → env var → `.env`** (env wins for CI overrides? decide:
     recommend **env var first, then keyring, then `.env`** so CI/`--token`
     stays predictable; document the order).
   - `set_token(host_name, token)`: writes to keyring by default; `.env` only on
     explicit opt-out.
   - `delete_token(host_name)`.
   - Service name e.g. `git_mirror`, username = host_name
     (`github`/`selfhosted`).
3. Route all token reads through `CredentialStore`:
   - `services.get_token_for_host`, `__main__.validate_host_token`,
     `manage_config._run_checks`, `pat_init._save_pat`.
4. `pat_init.setup_github_pat`: after validating the PAT, offer
   **keychain (default) / global .env / local .env**. Default to keychain.
5. `doctor`: report *where* the token was found (keychain vs env vs .env) and
   warn if only plaintext `.env`.
6. Add a `migrate-credentials` path (or fold into `doctor --fix`) that copies an
   existing `.env` token into the keychain and offers to remove the plaintext.
7. Update README to recommend `git_mirror init` → keychain.

Exit criteria: a fresh setup stores the token in the OS keychain; `.env` and env
vars still work; `doctor` shows the source; tests cover the resolution order with
keyring mocked.

---

## Phase 4 — One core orchestration API (merge router + services)

Goal: a single, GUI- and CLI-agnostic core; kill the duplication.

1. Create `git_mirror/core.py` (or `git_mirror/operations.py`) that owns the
   batch operations and returns **plain data** (reuse the `services.py`
   dataclasses: `RepoStatus`, `RepoInfo`, `BuildInfo`, `ActionResult`).
   Functions: `list_repos`, `clone_all`, `pull_all`, `scan_local_changes`,
   `find_non_repos`, `build_statuses`, `update_from_main`, `prune_all`,
   `sync_config`, `show_account`.
2. Each function takes a resolved context (token via `CredentialStore`, config,
   target dir, dry_run, prompt policy) and delegates to `GithubRepoManager` /
   `GitManager`. **No rendering inside core.**
3. **`router.py` becomes a thin CLI adapter:** parse → call core → render via
   `utils/ui`. Delete the duplicate clone/pull logic now living in `services.py`.
4. **`gui/app.py` calls the same core** functions (it already wants data, not
   prints). Minimal GUI change: repoint imports from `services` to `core`.
5. Remove `services.py` once everything imports `core` (or rename
   `services.py` → `core.py` and fold `router`'s logic in — pick the lower-diff
   path during implementation).

Exit criteria: exactly one implementation of each batch op; CLI and GUI both go
through it; `uv run pytest` green; manual CLI smoke test passes.

---

## Phase 5 — Repo selection / filtering (config-driven subset)

Goal: deliver the README's long-standing "PENDING" focus feature.

1. Extend config: per-repo entries already exist via `sync-config`
   (`[tool.git-mirror.<host>.repos]`). Give each entry optional
   `ignore: bool` and `tags: [..]` (and keep `important`).
2. Add selection flags to all batch commands:
   `--only <name,...>`, `--tag <tag>`, `--exclude <name,...>`,
   `--ignore-config-ignores` (escape hatch).
3. Core resolves the effective repo set once and every operation respects it
   (clone/pull/status/update/prune/build-status).
4. `doctor` / `list-config` surfaces how many repos are focused vs ignored.

Exit criteria: `git_mirror pull-all --tag work` operates only on tagged repos;
ignored repos are skipped everywhere; tests cover selection resolution.

---

## Phase 6 — Unified status dashboard

Goal: "what is the state of ALL my repos" in one instant command.

1. New core function `repo_dashboard(...)` returning, per repo: dirty?,
   ahead/behind counts, current branch, untracked-branch count, last-commit age,
   latest build conclusion (GitHub Actions), and remote-exists.
2. New CLI command `status` (or `dashboard`) rendering a single Rich table,
   color-coded, sorted by "needs attention" first.
3. Parallelized (reuse the existing multiprocessing/locking pattern in
   `manage_git.py`), with graceful per-repo error cells.
4. Respects Phase 5 selection.

Exit criteria: one command shows the full fleet state; large folders complete in
parallel; errors degrade gracefully per row.

---

## Phase 7 — Harden safe batch mutations

Goal: make the dangerous operations trustworthy.

1. Audit `update-from-main`, `prune-all`, `clone-all`, `sync-config` for:
   consistent `--dry-run`, per-repo confirm (honor `--yes`), and clear
   before/after reporting via `ActionResult`.
2. Prune safety: never delete a branch with unpushed commits or uncommitted work
   without explicit confirm; show exactly what would be deleted in dry-run.
3. update-from-main: surface rebase-vs-merge choice (`--prefer-rebase` already
   exists in the manager) and stop on conflict per repo without aborting the
   whole batch.
4. Consistent parallelism + an interrupt-safe path (Ctrl-C leaves repos in a
   known state).

Exit criteria: every mutating command has dry-run + confirm + per-repo error
isolation; tests cover the "refuse to destroy unpushed work" guard.

---

## Phase 8 — Mechanical cleanup (BOT WORK — do LAST)

Tasks suitable for an automated agent once the human-judgment refactor is done.
**Run this phase last so it doesn't churn against in-flight changes.**

1. Grep gate: assert no `gitlab` / `python-gitlab` / `gl_mirror` symbols remain
   anywhere in `git_mirror/` and `tests/`.
2. `uv run ruff check --fix` / formatter pass across the new layout.
3. `uv run mypy git_mirror` clean (fix types exposed by the `utils/` move and the
   new `core` API; tighten `ConfigData` now that gitlab fields are gone).
4. Prune now-dead code (`features.CACHING` if unused, `dummies` if the merged
   core no longer needs the lock dummy, stale `# TODO` lock comments).
5. Update/regenerate `tests/tests_bot/...` for renamed modules; remove
   gitlab-specific bot tests.
6. Refresh `docs/TODO.md`, README usage/`--help` block, and `__help__` epilog to
   match the final command set.
7. Bump version to `2.0.0` in `__about__.py`; finalize CHANGELOG/migration notes.

Exit criteria: lint + mypy clean; grep gate passes; docs match reality;
`2.0.0` ready to tag.

---

## Sequencing summary

| Phase | Theme | Depends on | Human vs Bot | Status |
|------|-------|-----------|--------------|--------|
| 0 | Guardrails | — | Human | ✅ done (baseline 186 passed) |
| 1 | Drop GitLab | 0 | Human | ✅ done |
| 2 | utils/ renamespace | 1 | Human (mechanical-ish) | ✅ done |
| 3 | keyring credentials | 2 | Human | ⬜ next |
| 4 | Merge router+services into core | 2 | Human | ⬜ |
| 5 | Repo selection/filtering | 4 | Human | ⬜ |
| 6 | Status dashboard | 4,5 | Human | ⬜ |
| 7 | Harden mutations | 4,5 | Human | ⬜ |
| 8 | Lint / mypy / dead code / docs / version | all | **Bot, LAST** | ⬜ |

### Progress log

- **Phases 0–2 complete** on branch `refocus-2.0-github-only`. GitLab removed
  (modules, tests, `python-gitlab` dep, `gl_mirror` entrypoint, config/router/
  services/CLI branches, GUI account-fetch, smoke scripts). `selfhosted` is now
  GitHub-Enterprise-only and old GitLab configs raise a clear migration error.
  Nine generic modules moved to `git_mirror/utils/*` with all imports updated.
  Suite: **159 passed, 6 skipped, 0 failed** (drop from 186 = deleted GitLab
  tests). Phase 8 bot work (lint/mypy/dead-comment cleanup) still pending.

## Out of scope for now

- GUI investment (kept working, repointed to core in Phase 4, improved later).
- Any non-GitHub host beyond GHE.
- Renaming the package away from "git_mirror".
