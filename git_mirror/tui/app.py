"""
git_mirror Textual TUI.

The third way to drive git_mirror (alongside the plain CLI and the tkinter GUI).
Like the GUI, this is a *thin consumer of* ``git_mirror.core`` — it renders data
and prompts, and never re-implements batch logic or builds a host manager.

Launch with ``git_mirror_tui`` (entry point ``launch_tui``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Label,
    RichLog,
    Select,
    TabbedContent,
    TabPane,
)

from git_mirror.__about__ import __version__

# Map core's semantic classification tags to Rich colour names.  The tag itself
# (ok/warn/error/dim) is decided once in core; only the colour lives here, the
# Textual analogue of router._RICH_TAG_COLOR / gui's tk tags.
TAG_COLOR = {"ok": "green", "warn": "yellow", "error": "red", "dim": "grey50"}


def _tag(tag: str, text: str) -> str:
    color = TAG_COLOR.get(tag)
    return f"[{color}]{text}[/{color}]" if color else text


def _configured_targets() -> list[tuple[str, Any]]:
    """(host, config) pairs that have an existing target dir.  Core call only."""
    from git_mirror.core import load_all_configs

    configs = load_all_configs()
    return [
        (host, c)
        for host, c in configs.items()
        if c and c.target_dir and c.target_dir.exists()
    ]


def _host_choices() -> list[tuple[str, str]]:
    """Select options for hosts that are actually configured."""
    from git_mirror.core import load_all_configs

    configs = load_all_configs()
    return [(host.title(), host) for host, c in configs.items() if c]


class DashboardPane(VerticalScroll):
    """Fleet status: one row per local repo, attention-first.  The headline view."""

    def compose(self) -> ComposeResult:
        with Horizontal(id="dash-bar"):
            yield Button("Refresh", id="dash-refresh", variant="primary")
            yield Checkbox("Include CI status (needs token)", id="dash-ci")
        yield Label("", id="dash-status")
        table: DataTable = DataTable(id="dash-table", zebra_stripes=True)
        table.cursor_type = "row"
        yield table

    def on_mount(self) -> None:
        table = self.query_one("#dash-table", DataTable)
        table.add_columns(
            "Repository", "Branch", "State", "Ahead", "Behind",
            "Untracked", "Last commit", "CI",
        )
        self.refresh_rows()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dash-refresh":
            self.refresh_rows()

    def refresh_rows(self) -> None:
        self.query_one("#dash-status", Label).update("Scanning fleet status...")
        include_ci = self.query_one("#dash-ci", Checkbox).value
        self._scan(include_ci)

    @work(thread=True, exclusive=True)
    def _scan(self, include_ci: bool) -> None:
        from git_mirror.core import get_token_for_host, repo_dashboard

        rows: list[Any] = []
        for _host, config in _configured_targets():
            token = get_token_for_host(config) if include_ci else None
            rows.extend(
                repo_dashboard(
                    config.target_dir,
                    token=token,
                    config=config if token else None,
                )
            )
        self.app.call_from_thread(self._populate, rows)

    def _populate(self, rows: list[Any]) -> None:
        from git_mirror.core import build_state, dashboard_state

        table = self.query_one("#dash-table", DataTable)
        table.clear()
        attention = 0
        for r in rows:
            tag, state = dashboard_state(r)
            if r.needs_attention:
                attention += 1
            age = "" if r.last_commit_age_days is None else f"{r.last_commit_age_days}d"
            if r.build:
                ci_tag, ci_label = build_state(r.build)
                ci = _tag(ci_tag, ci_label)
            else:
                ci = ""
            branch = (r.branch or "") + ("*" if r.dirty else "")
            table.add_row(
                r.name, branch, _tag(tag, state),
                str(r.ahead or ""), str(r.behind or ""),
                str(r.untracked_branches or ""), age, ci,
            )
        self.query_one("#dash-status", Label).update(
            f"{len(rows)} repos — {attention} need attention"
        )


class LocalChangesPane(VerticalScroll):
    """Dirty repos and unpushed/untracked branches across all target dirs."""

    def compose(self) -> ComposeResult:
        with Horizontal(id="lc-bar"):
            yield Button("Scan", id="lc-scan", variant="primary")
        yield Label("", id="lc-status")
        table: DataTable = DataTable(id="lc-table", zebra_stripes=True)
        table.cursor_type = "row"
        yield table

    def on_mount(self) -> None:
        self.query_one("#lc-table", DataTable).add_columns(
            "Repository", "Status", "Unpushed", "Untracked branches",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "lc-scan":
            self.query_one("#lc-status", Label).update("Scanning for local changes...")
            self._scan()

    @work(thread=True, exclusive=True)
    def _scan(self) -> None:
        from git_mirror.core import scan_local_changes

        statuses: list[Any] = []
        for _host, config in _configured_targets():
            statuses.extend(scan_local_changes(config.target_dir))
        self.app.call_from_thread(self._populate, statuses)

    def _populate(self, statuses: list[Any]) -> None:
        table = self.query_one("#lc-table", DataTable)
        table.clear()
        attention = 0
        for s in statuses:
            if s.error:
                status = _tag("error", s.error)
                attention += 1
            elif s.dirty or s.unpushed_branches:
                status = _tag("warn", "dirty" if s.dirty else "unpushed")
                attention += 1
            else:
                status = _tag("ok", "clean")
            table.add_row(
                s.path.name, status,
                ", ".join(s.unpushed_branches),
                ", ".join(s.untracked_branches),
            )
        self.query_one("#lc-status", Label).update(
            f"Scanned {len(statuses)} repos — {attention} need attention"
        )


class ActionsPane(VerticalScroll):
    """Run the batch mutations (clone / pull / prune) with a dry-run toggle.

    Every button delegates straight to a core function; no manager is built here.
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="act-bar"):
            yield Select(_host_choices(), id="act-host", allow_blank=True,
                         prompt="Host")
            yield Checkbox("Dry run", value=True, id="act-dry")
        with Horizontal(id="act-buttons"):
            yield Button("Clone All", id="act-clone", variant="primary")
            yield Button("Pull All", id="act-pull", variant="primary")
            yield Button("Prune", id="act-prune", variant="warning")
        yield RichLog(id="act-log", wrap=True, highlight=False, markup=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = (event.button.id or "").replace("act-", "")
        if action not in ("clone", "pull", "prune"):
            return
        dry = self.query_one("#act-dry", Checkbox).value
        log = self.query_one("#act-log", RichLog)

        # Pull is dir-based and host-agnostic; clone/prune need a host config.
        if action == "pull":
            targets = _configured_targets()
            if not targets:
                log.write(_tag("error", "No configured target directories."))
                return
            log.write(f"Pulling all repos ({'dry run' if dry else 'live'})...")
            self._run_pull([c.target_dir for _h, c in targets], dry)
            return

        host = self.query_one("#act-host", Select).value
        if host is Select.BLANK or not host:
            log.write(_tag("error", "Pick a host first."))
            return
        from git_mirror.core import get_token_for_host, load_all_configs

        config = load_all_configs().get(host)
        if not config:
            log.write(_tag("error", f"No configuration for {host}."))
            return
        token = get_token_for_host(config)
        if not token:
            log.write(_tag("error", f"No access token for {host}."))
            return
        log.write(f"{action.title()} on {host} ({'dry run' if dry else 'live'})...")
        if action == "clone":
            self._run_clone(token, config, dry)
        else:
            self._run_prune(token, config, dry)

    @work(thread=True)
    def _run_clone(self, token: str, config: Any, dry: bool) -> None:
        from git_mirror.core import clone_all_repos

        self.app.call_from_thread(self._show, clone_all_repos(token, config, dry))

    @work(thread=True)
    def _run_pull(self, dirs: list[Path], dry: bool) -> None:
        from git_mirror.core import ActionResult, pull_all_repos

        merged = ActionResult(success=True)
        for d in dirs:
            r = pull_all_repos(d, dry)
            merged.messages.extend(r.messages)
            merged.errors.extend(r.errors)
        merged.success = not merged.errors
        self.app.call_from_thread(self._show, merged)

    @work(thread=True)
    def _run_prune(self, token: str, config: Any, dry: bool) -> None:
        from git_mirror.core import prune_all_repos

        self.app.call_from_thread(self._show, prune_all_repos(token, config, dry))

    def _show(self, result: Any) -> None:
        log = self.query_one("#act-log", RichLog)
        for msg in result.messages:
            log.write(msg)
        for err in result.errors:
            log.write(_tag("error", f"ERROR: {err}"))
        log.write(_tag("ok" if result.success else "error", "— done —"))


class DoctorPane(VerticalScroll):
    """Config / token / connectivity health, straight from core.run_doctor."""

    def compose(self) -> ComposeResult:
        with Horizontal(id="doc-bar"):
            yield Button("Run Doctor", id="doc-run", variant="primary")
        yield RichLog(id="doc-log", wrap=True, markup=True)

    def on_mount(self) -> None:
        self._run()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "doc-run":
            self._run()

    @work(thread=True, exclusive=True)
    def _run(self) -> None:
        from git_mirror.core import run_doctor

        self.app.call_from_thread(self._show, run_doctor())

    def _show(self, results: list[tuple[str, list[Any]]]) -> None:
        log = self.query_one("#doc-log", RichLog)
        log.clear()
        if not results:
            log.write(_tag("warn", "No hosts configured. Run `git_mirror init` first."))
            return
        for host_label, checks in results:
            log.write(f"[bold]{host_label}[/bold]")
            for check in checks:
                tag = "ok" if check.ok else "error"
                mark = "OK  " if check.ok else "FAIL"
                log.write(_tag(tag, f"  [{mark}] {check.name}: {check.details}"))
                if getattr(check, "fix", None):
                    log.write(_tag("warn", f"         Fix: {check.fix}"))


class GitMirrorTui(App):
    """git_mirror Textual application."""

    TITLE = f"git_mirror v{__version__}"
    SUB_TITLE = "Operate on a whole folder of GitHub repos at once"

    CSS = """
    #dash-bar, #lc-bar, #act-bar, #act-buttons, #doc-bar {
        height: auto;
        padding: 1 1 0 1;
    }
    #dash-bar Button, #act-buttons Button { margin-right: 2; }
    #dash-status, #lc-status { padding: 0 1; color: $text-muted; }
    DataTable { height: 1fr; }
    RichLog { height: 1fr; border: round $panel; margin: 1; }
    Select { width: 24; }
    """

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="tab-dashboard"):
            with TabPane("Dashboard", id="tab-dashboard"):
                yield DashboardPane()
            with TabPane("Local Changes", id="tab-local"):
                yield LocalChangesPane()
            with TabPane("Actions", id="tab-actions"):
                yield ActionsPane()
            with TabPane("Doctor", id="tab-doctor"):
                yield DoctorPane()
        yield Footer()

    def action_refresh(self) -> None:
        """Refresh whichever data pane is active."""
        try:
            pane = self.query_one(TabbedContent).active_pane
        except Exception:  # pragma: no cover - defensive
            return
        if pane is None:
            return
        for cls, method in (
            (DashboardPane, "refresh_rows"),
            (DoctorPane, "_run"),
        ):
            for child in pane.query(cls):
                getattr(child, method)()


def launch_tui() -> None:
    """Entry point for the Textual TUI (``git_mirror_tui``)."""
    GitMirrorTui().run()


if __name__ == "__main__":
    launch_tui()
