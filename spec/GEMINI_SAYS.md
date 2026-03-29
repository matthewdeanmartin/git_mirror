# GEMINI_SAYS: Code Quality & Architecture Audit

This document outlines the findings of a comprehensive code quality audit for `git_mirror` and proposes a phased plan for improvement.

## 1. Executive Summary

`git_mirror` is a useful tool with a solid foundation, but it suffers from significant architectural issues, primarily extreme code duplication between the CLI and GUI paths. The core logic is tightly coupled with the presentation layer (Rich console), leading to a "copy-paste" approach to feature implementation in `services.py`. Onboarding is functional but "no fun" due to its reliance on manual `.env` management and a somewhat fragmented setup process.

## 2. Key Findings

### 2.1 Code Quality & Architecture
- **Extreme Duplication:** The same logic for cloning, pulling, and listing repos exists in at least three places: `manage_github.py`/`manage_gitlab.py`, `router.py`, and `services.py`.
- **Tightly Coupled Presentation:** Core managers (`GithubRepoManager`, `GitlabRepoManager`) are hardcoded to use `rich` for output, which forced the creation of `services.py` to reimplement the same logic for the GUI to return data instead of printing.
- **Inconsistent Patterns:** 
    - Concurrency (multiprocessing) is implemented separately in both managers and not shared.
    - Error handling is inconsistent, often catching generic `Exception`.
    - Mixed usage of `toml` and `tomlkit`.
    - mixed usage of `termcolor` and `rich`.
- **Complex Entry Point:** `__main__.py` and `router.py` are procedural "if-else" forests that are hard to test and extend.

### 2.2 Ergonomics & UX
- **Onboarding "No Fun":** 
    - Reliance on `.env` files for PATs is clunky and less secure than using a system keyring.
    - The `init` wizard is only in the CLI, leaving GUI users stranded.
    - Multiple tool names (`gh_mirror`, `gl_mirror`) add noise without much value.
- **Clunky CLI:** The `menu` command is helpful but the category navigation is repetitive.
- **Sync Config Limitation:** Only syncs repo names, not other useful metadata or per-repo overrides.

### 2.3 WTFs & Technical Debt
- **Dead Code:** `dead_code/` and `on_hold/` directories should be removed or properly integrated.
- **False Promises:** `find_git_repos` claims to use `rglob` for safety but doesn't actually implement it.
- **Library Overlap:** Both `toml` and `tomlkit` are dependencies; one should be chosen.
- **GUI Limitations:** GUI implementation of "Update from Main" and "Prune" is GitHub-only, even though the logic exists for GitLab in the managers.

### 2.4 Security
- **PAT Storage:** Storing PATs in plain text `.env` files is "developer workstation safe" but not industry-standard. Moving to `keyring` would be a major upgrade.

---

## 3. Improvement Plan

### Phase 1: Core Consolidation (The "Great Unification")
*Goal: Stop the bleeding by unifying logic.*

1.  **Refactor Managers:** Modify `GithubRepoManager` and `GitlabRepoManager` to return data (generators or lists of objects) instead of printing. Use a `ConsoleReporter` class to handle CLI printing.
2.  **Unify Services:** Move all core logic (cloning, pulling, pruning) into a shared `core` module or keep it in the managers, but make `services.py` and `router.py` call the *same* underlying methods.
3.  **Standardize Concurrency:** Create a shared utility for parallel repository operations that both managers and services use.
4.  **Remove Library Redundancy:** Standardize on `tomlkit` and remove `toml`.

### Phase 2: Onboarding & Security
*Goal: Make it "fun" and secure.*

1.  **Keyring Integration:** Replace `.env` PAT storage with the `keyring` library.
2.  **GUI Onboarding:** Implement a basic setup wizard in the GUI.
3.  **Streamline Init:** If `gh` or `glab` CLIs are installed, offer to pull tokens from them automatically.
4.  **Doctor Improvements:** Make `doctor` more proactive in fixing issues (e.g., "Would you like me to create this directory?").

### Phase 3: Features & Ergonomics
*Goal: Add missing functionality and polish.*

1.  **Template Sync:** Implement the "Copy template files to all repos" feature.
2.  **Repo Subsets:** Implement tagging or subsetting in `git_mirror.toml` to allow operations on a specific group of repos.
3.  **Better Sync:** Enhance `sync-config` to include more repo metadata (description, primary language, etc.).
4.  **CLI Cleanup:** Deprecate `gh_mirror`/`gl_mirror` in favor of a more intelligent `git_mirror` that detects the host if unambiguous.
5.  **Remove Dead Code:** Delete `dead_code/` and `on_hold/` after ensuring no gems are lost.

### Phase 4: Modernization
*Goal: Future-proof the project.*

1.  **Pydantic Integration:** Use Pydantic for `ConfigData` and API response parsing to get better validation and IDE support.
2.  **Async/Await:** Consider moving from `multiprocessing` to `asyncio` for I/O bound tasks (API calls) while keeping `multiprocessing` for CPU-bound or subprocess-heavy tasks (git operations).
3.  **Complete GUI:** Ensure all features available in the CLI are parity-complete in the GUI.

---

## 4. Immediate Actions (WTF Fixes)
- Fix `find_git_repos` to actually be robust.
- Standardize on `rich` and remove `termcolor`.
- Clean up `__main__.py` by moving validation logic into a `CLIContext` or similar object.
