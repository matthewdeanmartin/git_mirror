# Three Ways to Drive git_mirror (and a UI dependency diet)

Status: **All parts done (A, B.1–B.3).** Target: a `2.1` cleanup release.

> **Decision change (from the boss):** Textual is a **direct dependency**, not
> an optional `[tui]` extra. To pull the latest Textual we uncapped Rich
> (`rich>=13.7,<14` → `rich>=14.2`, now resolving to Rich 15) and bumped
> `textual>=8`. No Python version had to be dropped — Textual 8 still supports
> `>=3.9`. The old Rich `<14` cap was a leftover from supporting very old
> Pythons and is gone.

## Progress log

- **Part A done.** `termcolor` (3 lines in `manage_github.loop_actions`),
  `prettytable` (dead), and `colorama` (dead) removed from `dependencies`;
  `types-colorama` removed from the dev group. The `# ui` block is now just
  `rich` + `inquirer`. `loop_actions` colours via `console.print(..., style=...)`.
- **Part B.3 done (the de-duplication pass).** Two kinds of duplication across
  the front ends were collapsed into `core.py`:
  1. **Status classification.** `core.dashboard_state(row)` and
     `core.build_state(conclusion)` are the one source of truth that turns repo
     state / CI conclusion into a semantic tag (`ok`/`warn`/`error`/`dim`) +
     label. The CLI (`router.render_dashboard`, `manage_github.loop_actions`)
     and the tkinter GUI (`DashboardPanel`, `BuildStatusPanel`) now call these
     instead of re-deriving colours. Rich's tag→colour map lives once in
     `utils/ui.RICH_TAG_STYLE` / `rich_markup`.
  2. **Operation wiring.** The GUI used to build a `GithubRepoManager` by hand
     in `UpdateFromMainPanel` and `PruneAllPanel` (with its own
     `host_type == "github"` branching). Added `core.update_from_main_repos`
     and `core.prune_all_repos` (returning `ActionResult` like
     `clone_all_repos`); the GUI now calls them and constructs **no** manager
     itself. The Textual TUI must do the same — call core, never build a manager.

git_mirror should be usable three ways, each a thin shell over the one
GUI/CLI-agnostic `core.py` API. None of them should re-implement batch logic;
they only *render* and *prompt*.

| Way | For whom | Stack | Install |
|-----|----------|-------|---------|
| **1. CLI** (non-interactive) | scripts, CI, power users | `rich` | default |
| **2. Interactive prompts** | humans at a terminal, guided setup | `rich` + `inquirer` | default |
| **3. TUI** (full-screen) | people who prefer a TUI app | `textual` | default (direct dep) |

(The existing tkinter GUI stays as a fourth, separate `[gui]`-style path — out
of scope for this spec, which is about the terminal UIs and the dependency diet.)

---

## Part A — Trim the UI dependencies (do this first, it's cheap)

Today the `# ui` block of `pyproject.toml` carries **five** libraries:

```toml
"rich>=13.7.0,<14",
"inquirer>=3.2.3,<4",
"termcolor",
"prettytable<4",
"colorama>=0.4.6,<1",
```

An audit of `git_mirror/` shows what each is *actually* used for:

| Library | Where used | Keep? |
|---------|-----------|-------|
| `rich` | tables/panels/console/theme across `manage_github`, `manage_config`, `router`, `custom_types`, `utils/ui`, `utils/bug_report` | **Keep** — the backbone |
| `inquirer` | interactive prompts in `menu.py`, `manage_config.py`, `manage_github.py` | **Keep** (way #2) |
| `termcolor` | **3 lines** in `manage_github.py`: `colored(status_message, "green"/"red"/"yellow")`, each already passed to `console.print(...)` | **Cut** |
| `prettytable` | **no imports anywhere** in `git_mirror/` or `tests/` | **Cut (dead)** |
| `colorama` | **no imports anywhere**; `rich` already enables Windows ANSI | **Cut (dead)** |

### A.1 Remove the two dead deps

- Delete `prettytable<4` and `colorama>=0.4.6,<1` from `dependencies`.
- Remove `types-colorama` from the dev group.
- No code changes needed — nothing imports them.

### A.2 Replace `termcolor` with `rich`

The only use is three lines in `manage_github.py` (~L337–341). `rich` already
colors via `console.print(text, style=...)`, and the text is *already* going
through `console.print`. Replace:

```python
from termcolor import colored
...
console.print(colored(status_message, "green"))
console.print(colored(status_message, "red"))
console.print(colored(status_message, "yellow"))
```

with:

```python
console.print(status_message, style="green")
console.print(status_message, style="red")
console.print(status_message, style="yellow")
```

Then drop `termcolor` from `dependencies`.

**Result:** the `# ui` block shrinks from 5 libs to 2:

```toml
# ui
"rich>=13.7.0,<14",
"inquirer>=3.2.3,<4",
```

Exit criteria: `uv run pytest` green; `uv run python -c "import git_mirror"`
clean; no `termcolor`/`prettytable`/`colorama` symbol anywhere in `git_mirror/`.

### A.3 (Optional, deferred) collapse `inquirer` too

`inquirer` is the only remaining interactive dep. If we later want **one** UI
library, `questionary` (built on `prompt_toolkit`, plays well with `rich`) can
replace every `inquirer.List/Text/Confirm/Checkbox` prompt. There are ~9 prompt
sites (`menu.py` 4, `manage_config.py` 3, `manage_github.py` 2). This is a real
port with little user-visible payoff, so it is **not** part of the first pass —
listed here only so the option is recorded. Decision: keep `inquirer` for now.

---

## Part B — Add a Textual TUI (way #3)  ✅ done

Textual is a **direct dependency** (boss's call), so the TUI is always
available — no extra to install, no import-hint fallback needed.

### B.1 Packaging  ✅

```toml
# dependencies
"rich>=14.2.0",      # uncapped; Textual 8 needs rich>=14.2
"textual>=8",

[project.scripts]
git_mirror_tui = "git_mirror.tui.app:launch_tui"
```

The TUI is a terminal app, so it lives under `[project.scripts]` (not
`gui-scripts`). `git_mirror/tui/__init__.py` keeps the deferred-import note for
parity with `gui/`, but since textual is now a hard dep there is no missing-dep
branch to handle.

### B.2 Module layout  ✅

```
git_mirror/tui/
    __init__.py     # deferred-import note, like gui/__init__.py
    app.py          # Textual App: launch_tui() entry point
```

The TUI is a **thin consumer of `core.py`** — exactly like the tkinter GUI:
- `core.repo_dashboard(...)`  → a Textual `DataTable` (the fleet status screen)
- `core.scan_local_changes`, `find_non_repos`, `clone_all_repos`,
  `pull_all_repos`, `get_build_statuses`, `run_doctor`, `load_all_configs`
  → their own screens/tabs.

No batch logic, no token resolution, no rendering rules live in the TUI; it
calls core and displays `DashboardRow` / `RepoStatus` / `ActionResult` data.
Long operations run via a worker (`@work` / `run_worker`) so the UI stays
responsive — the TUI analogue of the tkinter `BackgroundRunner`.

Screens implemented (a `TabbedContent` with four tabs):
1. **Dashboard** — fleet status `DataTable`, attention-first (the headline),
   with a "Include CI status" toggle.
2. **Local Changes** — dirty/unpushed/untracked `DataTable`.
3. **Actions** — Clone All / Pull All / Prune with a host `Select`, a dry-run
   toggle, and a `RichLog` output pane.
4. **Doctor** — config/token/connectivity health from `core.run_doctor`.

Long operations run on Textual worker threads (`@work(thread=True)`) and post
results back with `app.call_from_thread(...)` — the TUI analogue of the tkinter
`BackgroundRunner`. No batch logic, token resolution, or manager construction
lives in the TUI; every button calls a `core` function and renders the returned
`DashboardRow` / `RepoStatus` / `ActionResult` data.

### B.3 Don't fork the rendering rules  ✅ (done in the previous pass)

Status→color classification now lives once in `core.dashboard_state` /
`core.build_state` (returning `ok`/`warn`/`error`/`dim` tags). The TUI maps
those tags to Textual/Rich colours via its own small `TAG_COLOR` table — the
same pattern as `router`'s `rich_markup` and the GUI's tk tags. One decision,
three colour tables, zero duplicated logic.

Exit criteria (met): `git_mirror_tui` opens the dashboard; a headless
`App.run_test()` smoke test composes all tabs, runs the dashboard/doctor
workers to completion, and exercises an Actions button end to end; the core
suite is unaffected (191 passed, 6 skipped).

---

## Sequencing

1. ✅ **Part A** (dependency diet) — 5 UI libs → `rich` + `inquirer` (+ textual).
2. ✅ **Part B.3** (shared classification + operation wiring into `core`).
3. ✅ **Part B.1–B.2** (Textual TUI, direct dep, `git_mirror_tui`).
4. **Part A.3** (`inquirer`→`questionary`) — only if we later want a single
   interactive lib; not scheduled.

## Out of scope

- The tkinter GUI redesign (already done separately).
- Replacing `rich` (it stays; it is the shared rendering layer for all ways).
- Any non-GitHub host work.
