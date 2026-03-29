"""
git_mirror tkinter GUI.

Layout: help/info on left, main panel in centre, action buttons on right.
Dark theme (Catppuccin Mocha inspired).  See spec/CONTRIBUTING_TKINTER.md.
"""

from __future__ import annotations

import threading
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
from pathlib import Path
from typing import Any, Callable

from git_mirror.__about__ import __version__

# ── Catppuccin Mocha palette ─────────────────────────────────────────

_CLR_OK = "#22c55e"
_CLR_WARN = "#eab308"
_CLR_ERR = "#ef4444"
_CLR_DIM = "#9ca3af"
_CLR_BG = "#1e1e2e"
_CLR_BG_ALT = "#252536"
_CLR_FG = "#cdd6f4"
_CLR_ACCENT = "#89b4fa"
_CLR_SIDEBAR = "#181825"
_CLR_BTN = "#313244"
_CLR_BTN_ACTIVE = "#45475a"
_CLR_BTN_HOVER = "#3b3b52"
_CLR_BORDER = "#313244"
_CLR_HEADER = "#a6adc8"

_FONT_UI = ("Segoe UI", 10)
_FONT_UI_BOLD = ("Segoe UI", 10, "bold")
_FONT_UI_HEADING = ("Segoe UI", 12, "bold")
_FONT_DATA = ("Consolas", 10)
_FONT_DATA_SMALL = ("Consolas", 9)

# ── Background runner ────────────────────────────────────────────────


class _BackgroundRunner:
    """Run a function in a daemon thread, post callbacks on the main thread."""

    def __init__(self, root: tk.Tk):
        self._root = root

    def run(
        self,
        func: Callable[..., Any],
        *,
        args: tuple[Any, ...] = (),
        on_success: Callable[..., Any] | None = None,
        on_error: Callable[[Exception], Any] | None = None,
    ) -> None:
        def _worker():
            try:
                result = func(*args)
                if on_success:
                    self._root.after(0, on_success, result)
            except Exception as exc:
                if on_error:
                    self._root.after(0, on_error, exc)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()


# ── Widget helpers ───────────────────────────────────────────────────


def _make_tree(parent: tk.Widget, columns: list[tuple[str, int]], height: int = 20) -> ttk.Treeview:
    """Create a themed treeview with scrollbar and colour tags."""
    frame = tk.Frame(parent, bg=_CLR_BG)
    frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Dark.Treeview",
        background=_CLR_BG_ALT,
        foreground=_CLR_FG,
        fieldbackground=_CLR_BG_ALT,
        font=_FONT_DATA,
        rowheight=24,
        borderwidth=0,
    )
    style.configure(
        "Dark.Treeview.Heading",
        background=_CLR_BTN,
        foreground=_CLR_HEADER,
        font=_FONT_UI_BOLD,
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Dark.Treeview",
        background=[("selected", _CLR_BTN_ACTIVE)],
        foreground=[("selected", _CLR_FG)],
    )
    style.map(
        "Dark.Treeview.Heading",
        background=[("active", _CLR_BTN_ACTIVE)],
    )

    col_ids = [c[0] for c in columns]
    tree = ttk.Treeview(frame, columns=col_ids, show="headings", height=height, style="Dark.Treeview")
    for col_name, col_width in columns:
        tree.heading(col_name, text=col_name)
        tree.column(col_name, width=col_width, minwidth=60)

    vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    tree.tag_configure("ok", foreground=_CLR_OK)
    tree.tag_configure("warn", foreground=_CLR_WARN)
    tree.tag_configure("error", foreground=_CLR_ERR)
    tree.tag_configure("dim", foreground=_CLR_DIM)
    return tree


def _make_output(parent: tk.Widget, height: int = 15) -> tk.Text:
    """Read-only scrolled text area for output/diff display."""
    frame = tk.Frame(parent, bg=_CLR_BG)
    frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    text = tk.Text(
        frame,
        height=height,
        bg=_CLR_BG_ALT,
        fg=_CLR_FG,
        insertbackground=_CLR_FG,
        font=_FONT_DATA,
        wrap=tk.WORD,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=_CLR_BORDER,
        state=tk.DISABLED,
    )
    vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=vsb.set)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    text.tag_configure("ok", foreground=_CLR_OK)
    text.tag_configure("warn", foreground=_CLR_WARN)
    text.tag_configure("error", foreground=_CLR_ERR)
    text.tag_configure("dim", foreground=_CLR_DIM)
    text.tag_configure("accent", foreground=_CLR_ACCENT)
    text.tag_configure("heading", foreground=_CLR_ACCENT, font=_FONT_UI_BOLD)
    return text


def _output_set(text_widget: tk.Text, content: str, tag: str | None = None) -> None:
    """Replace text content (handles enable/disable state)."""
    text_widget.configure(state=tk.NORMAL)
    text_widget.delete("1.0", tk.END)
    if tag:
        text_widget.insert(tk.END, content, tag)
    else:
        text_widget.insert(tk.END, content)
    text_widget.configure(state=tk.DISABLED)


def _output_append(text_widget: tk.Text, content: str, tag: str | None = None) -> None:
    """Append to text content."""
    text_widget.configure(state=tk.NORMAL)
    if tag:
        text_widget.insert(tk.END, content, tag)
    else:
        text_widget.insert(tk.END, content)
    text_widget.configure(state=tk.DISABLED)
    text_widget.see(tk.END)


def _make_toolbar(parent: tk.Widget) -> tk.Frame:
    """Horizontal button bar."""
    bar = tk.Frame(parent, bg=_CLR_BG)
    bar.pack(fill=tk.X, padx=8, pady=(8, 4))
    return bar


def _toolbar_btn(bar: tk.Frame, text: str, command: Callable[[], Any], width: int = 18) -> tk.Button:
    """Themed button inside a toolbar."""
    btn = tk.Button(
        bar,
        text=text,
        command=command,
        bg=_CLR_BTN,
        fg=_CLR_FG,
        activebackground=_CLR_BTN_ACTIVE,
        activeforeground=_CLR_FG,
        font=_FONT_UI,
        relief=tk.FLAT,
        cursor="hand2",
        width=width,
        padx=8,
        pady=4,
    )
    btn.pack(side=tk.LEFT, padx=4)
    btn.bind("<Enter>", lambda e: btn.configure(bg=_CLR_BTN_HOVER))
    btn.bind("<Leave>", lambda e: btn.configure(bg=_CLR_BTN))
    return btn


def _make_heading(parent: tk.Widget, text: str) -> tk.Label:
    lbl = tk.Label(parent, text=text, bg=_CLR_BG, fg=_CLR_ACCENT, font=_FONT_UI_HEADING, anchor=tk.W)
    lbl.pack(fill=tk.X, padx=12, pady=(12, 4))
    return lbl


# ── Base panel ───────────────────────────────────────────────────────


class _BasePanel(tk.Frame):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, bg=_CLR_BG)
        self._app = app
        self._runner = app.runner
        self._status = app.status_var


# ── Dashboard panel ──────────────────────────────────────────────────


class DashboardPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Dashboard")

        self._output = _make_output(self, height=24)
        self._load()

    def _load(self):
        self._status.set("Loading configuration...")
        self._runner.run(self._fetch, on_success=self._display, on_error=self._on_error)

    @staticmethod
    def _fetch():
        from git_mirror.services import load_all_configs
        return load_all_configs()

    def _display(self, configs: dict[str, Any]):
        lines: list[tuple[str, str | None]] = []
        lines.append(("git_mirror v" + __version__ + "\n\n", "accent"))
        found = False
        for host, config in configs.items():
            if config:
                found = True
                lines.append((f"  {host}\n", "heading"))
                lines.append((f"    User:       {config.user_name}\n", None))
                lines.append((f"    Target dir: {config.target_dir}\n", None))
                lines.append((f"    Host URL:   {config.host_url}\n", None))
                lines.append((f"    Private:    {'Yes' if config.include_private else 'No'}\n", None))
                lines.append((f"    Forks:      {'Yes' if config.include_forks else 'No'}\n\n", None))
        if not found:
            lines.append(("No hosts configured. Use Init to set up a host.\n", "warn"))

        lines.append(("\nQuick start:\n", "heading"))
        lines.append(("  1. Click Init to configure a host (GitHub, GitLab, or self-hosted)\n", "dim"))
        lines.append(("  2. Click Doctor to verify your setup\n", "dim"))
        lines.append(("  3. Use Clone All to pull down all your repos\n", "dim"))
        lines.append(("  4. Use Pull All to keep them up to date\n", "dim"))
        lines.append(("  5. Use Local Changes to see dirty repos and unpushed commits\n", "dim"))

        self._output.configure(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        for text, tag in lines:
            if tag:
                self._output.insert(tk.END, text, tag)
            else:
                self._output.insert(tk.END, text)
        self._output.configure(state=tk.DISABLED)
        self._status.set("Ready")

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error loading config: {exc}", "error")
        self._status.set("Error loading configuration")


# ── Local Changes panel ──────────────────────────────────────────────


class LocalChangesPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Local Changes")

        bar = _make_toolbar(self)
        _toolbar_btn(bar, "Scan All Hosts", self._scan_all)

        self._tree = _make_tree(self, [
            ("Repository", 250),
            ("Status", 100),
            ("Unpushed", 200),
            ("Untracked Branches", 200),
        ], height=22)

    def _scan_all(self):
        self._status.set("Scanning for local changes...")
        configs = self._app.get_configs()
        dirs = [c.target_dir for c in configs.values() if c and c.target_dir and c.target_dir.exists()]
        if not dirs:
            self._status.set("No configured target directories found")
            return
        self._runner.run(self._fetch, args=(dirs,), on_success=self._display, on_error=self._on_error)

    @staticmethod
    def _fetch(dirs: list[Path]):
        from git_mirror.services import scan_local_changes
        all_statuses = []
        for d in dirs:
            all_statuses.extend(scan_local_changes(d))
        return all_statuses

    def _display(self, statuses: list[Any]):
        for row in self._tree.get_children():
            self._tree.delete(row)

        dirty = 0
        for s in statuses:
            if s.error:
                tag = "error"
                status_text = s.error
            elif s.dirty:
                tag = "warn"
                status_text = "Dirty"
                dirty += 1
            else:
                tag = "ok"
                status_text = "Clean"

            unpushed = ", ".join(s.unpushed_branches) if s.unpushed_branches else ""
            untracked = ", ".join(s.untracked_branches) if s.untracked_branches else ""
            if s.unpushed_branches:
                tag = "warn"
                dirty += 1

            self._tree.insert("", tk.END, values=(s.path.name, status_text, unpushed, untracked), tags=(tag,))

        self._status.set(f"Scanned {len(statuses)} repos, {dirty} need attention")

    def _on_error(self, exc: Exception):
        self._status.set(f"Error: {exc}")


# ── List Repos panel ─────────────────────────────────────────────────


class ListReposPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Repositories")

        bar = _make_toolbar(self)
        self._host_var = tk.StringVar(value="github")
        for host in ("github", "gitlab", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self._host_var, value=host,
                bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
                activeforeground=_CLR_ACCENT, font=_FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        _toolbar_btn(bar, "Fetch Repos", self._fetch_repos)

        self._tree = _make_tree(self, [
            ("Name", 200),
            ("Description", 350),
            ("Private", 80),
            ("Fork", 80),
        ], height=22)

    def _fetch_repos(self):
        host = self._host_var.get()
        configs = self._app.get_configs()
        config = configs.get(host)
        if not config:
            self._status.set(f"No configuration for {host}")
            return
        from git_mirror.services import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self._status.set(f"No access token for {host}")
            return
        self._status.set(f"Fetching repos from {host}...")
        self._runner.run(
            self._fetch, args=(token, host, config),
            on_success=self._display, on_error=self._on_error,
        )

    @staticmethod
    def _fetch(token: str, host: str, config: Any):
        from git_mirror.services import list_repos_data
        return list_repos_data(token, host, config)

    def _display(self, repos: list[Any]):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for repo in repos:
            tag = "dim" if repo.fork else ""
            self._tree.insert("", tk.END, values=(
                repo.name, repo.description,
                "Yes" if repo.private else "No",
                "Yes" if repo.fork else "No",
            ), tags=(tag,) if tag else ())
        self._status.set(f"Found {len(repos)} repositories")

    def _on_error(self, exc: Exception):
        self._status.set(f"Error: {exc}")


# ── Clone All panel ──────────────────────────────────────────────────


class CloneAllPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Clone All Repositories")

        bar = _make_toolbar(self)
        self._host_var = tk.StringVar(value="github")
        for host in ("github", "gitlab", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self._host_var, value=host,
                bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
                activeforeground=_CLR_ACCENT, font=_FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        self._dry_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text="Dry run", variable=self._dry_var,
            bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
            font=_FONT_UI,
        ).pack(side=tk.LEFT, padx=12)
        _toolbar_btn(bar, "Clone All", self._run_clone)

        self._output = _make_output(self, height=22)

    def _run_clone(self):
        host = self._host_var.get()
        configs = self._app.get_configs()
        config = configs.get(host)
        if not config:
            self._status.set(f"No configuration for {host}")
            return
        from git_mirror.services import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self._status.set(f"No access token for {host}")
            return
        if not self._dry_var.get():
            if not messagebox.askyesno("Clone All", f"Clone all repos from {host} to {config.target_dir}?"):
                return
        self._status.set(f"Cloning repos from {host}...")
        _output_set(self._output, "Cloning...\n")
        self._runner.run(
            self._do_clone, args=(token, config, self._dry_var.get()),
            on_success=self._display, on_error=self._on_error,
        )

    @staticmethod
    def _do_clone(token: str, config: Any, dry_run: bool):
        from git_mirror.services import clone_all_repos
        return clone_all_repos(token, config, dry_run)

    def _display(self, result: Any):
        lines = []
        for msg in result.messages:
            lines.append(msg)
        for err in result.errors:
            lines.append(f"ERROR: {err}")
        _output_set(self._output, "\n".join(lines))
        self._status.set(f"Clone complete: {len(result.messages)} repos, {len(result.errors)} errors")

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error: {exc}", "error")
        self._status.set(f"Error: {exc}")


# ── Pull All panel ───────────────────────────────────────────────────


class PullAllPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Pull All Repositories")

        bar = _make_toolbar(self)
        self._dry_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text="Dry run", variable=self._dry_var,
            bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
            font=_FONT_UI,
        ).pack(side=tk.LEFT, padx=12)
        _toolbar_btn(bar, "Pull All Hosts", self._run_pull)

        self._output = _make_output(self, height=22)

    def _run_pull(self):
        configs = self._app.get_configs()
        dirs = [c.target_dir for c in configs.values() if c and c.target_dir and c.target_dir.exists()]
        if not dirs:
            self._status.set("No configured target directories found")
            return
        if not self._dry_var.get():
            if not messagebox.askyesno("Pull All", f"Pull all repos in {len(dirs)} target directories?"):
                return
        self._status.set("Pulling all repos...")
        _output_set(self._output, "Pulling...\n")
        self._runner.run(
            self._do_pull, args=(dirs, self._dry_var.get()),
            on_success=self._display, on_error=self._on_error,
        )

    @staticmethod
    def _do_pull(dirs: list[Path], dry_run: bool):
        from git_mirror.services import pull_all_repos
        all_results: dict[str, Any] = {"messages": [], "errors": []}
        for d in dirs:
            r = pull_all_repos(d, dry_run)
            all_results["messages"].extend(r.messages)
            all_results["errors"].extend(r.errors)
        return all_results

    def _display(self, result: dict[str, Any]):
        lines = result["messages"] + [f"ERROR: {e}" for e in result["errors"]]
        _output_set(self._output, "\n".join(lines) if lines else "No repos found.")
        self._status.set(f"Pull complete: {len(result['messages'])} repos, {len(result['errors'])} errors")

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error: {exc}", "error")
        self._status.set(f"Error: {exc}")


# ── Not-Repo panel ──────────────────────────────────────────────────


class NotRepoPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Non-Repository Directories")

        bar = _make_toolbar(self)
        _toolbar_btn(bar, "Scan All Hosts", self._scan)

        self._tree = _make_tree(self, [
            ("Path", 450),
            ("Reason", 300),
        ], height=22)

    def _scan(self):
        configs = self._app.get_configs()
        dirs = [c.target_dir for c in configs.values() if c and c.target_dir and c.target_dir.exists()]
        if not dirs:
            self._status.set("No configured target directories found")
            return
        self._status.set("Scanning...")
        self._runner.run(self._fetch, args=(dirs,), on_success=self._display, on_error=self._on_error)

    @staticmethod
    def _fetch(dirs: list[Path]):
        from git_mirror.services import find_non_repos
        results = []
        for d in dirs:
            results.extend(find_non_repos(d))
        return results

    def _display(self, results: list[tuple[str, str]]):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for path, reason in results:
            self._tree.insert("", tk.END, values=(path, reason), tags=("warn",))
        self._status.set(f"Found {len(results)} non-repo directories")

    def _on_error(self, exc: Exception):
        self._status.set(f"Error: {exc}")


# ── Build Status panel ───────────────────────────────────────────────


class BuildStatusPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Build Status (GitHub Actions)")

        bar = _make_toolbar(self)
        self._host_var = tk.StringVar(value="github")
        for host in ("github", "gitlab", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self._host_var, value=host,
                bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
                activeforeground=_CLR_ACCENT, font=_FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        _toolbar_btn(bar, "Fetch Builds", self._fetch_builds)

        self._tree = _make_tree(self, [
            ("Repository", 180),
            ("Conclusion", 100),
            ("Details", 500),
        ], height=22)

    def _fetch_builds(self):
        host = self._host_var.get()
        configs = self._app.get_configs()
        config = configs.get(host)
        if not config:
            self._status.set(f"No configuration for {host}")
            return
        from git_mirror.services import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self._status.set(f"No access token for {host}")
            return
        self._status.set(f"Fetching build statuses from {host}...")
        self._runner.run(
            self._fetch, args=(token, config),
            on_success=self._display, on_error=self._on_error,
        )

    @staticmethod
    def _fetch(token: str, config: Any):
        from git_mirror.services import get_build_statuses
        return get_build_statuses(token, config)

    def _display(self, builds: list[Any]):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for b in builds:
            if b.conclusion == "success":
                tag = "ok"
            elif b.conclusion == "failure":
                tag = "error"
            elif b.conclusion == "cancelled":
                tag = "warn"
            else:
                tag = "dim"
            self._tree.insert("", tk.END, values=(b.repo_name, b.conclusion or "pending", b.status_message), tags=(tag,))
        self._status.set(f"Found {len(builds)} build results")

    def _on_error(self, exc: Exception):
        self._status.set(f"Error: {exc}")


# ── Doctor panel ─────────────────────────────────────────────────────


class DoctorPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Doctor - Configuration Health")

        bar = _make_toolbar(self)
        _toolbar_btn(bar, "Run Doctor", self._run_doctor)

        self._output = _make_output(self, height=22)
        self._run_doctor()

    def _run_doctor(self):
        self._status.set("Running doctor checks...")
        self._runner.run(self._fetch, on_success=self._display, on_error=self._on_error)

    @staticmethod
    def _fetch():
        from git_mirror.services import run_doctor
        return run_doctor()

    def _display(self, results: list[tuple[str, list[Any]]]):
        self._output.configure(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        if not results:
            self._output.insert(tk.END, "No hosts configured. Run Init first.\n", "warn")
        for host_label, checks in results:
            self._output.insert(tk.END, f"\n  {host_label}\n", "heading")
            for check in checks:
                prefix = "[OK]  " if check.ok else "[FAIL]"
                tag = "ok" if check.ok else "error"
                self._output.insert(tk.END, f"    {prefix} {check.name}: {check.details}\n", tag)
                if hasattr(check, "fix") and check.fix:
                    self._output.insert(tk.END, f"           Fix: {check.fix}\n", "warn")
        self._output.configure(state=tk.DISABLED)
        self._status.set("Doctor complete")

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error: {exc}", "error")
        self._status.set(f"Error: {exc}")


# ── Show Account panel ───────────────────────────────────────────────


class ShowAccountPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Account Information")

        bar = _make_toolbar(self)
        self._host_var = tk.StringVar(value="github")
        for host in ("github", "gitlab", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self._host_var, value=host,
                bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
                activeforeground=_CLR_ACCENT, font=_FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        _toolbar_btn(bar, "Fetch Account", self._fetch_account)

        self._output = _make_output(self, height=22)

    def _fetch_account(self):
        host = self._host_var.get()
        configs = self._app.get_configs()
        config = configs.get(host)
        if not config:
            self._status.set(f"No configuration for {host}")
            return
        from git_mirror.services import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self._status.set(f"No access token for {host}")
            return
        self._status.set(f"Fetching account info from {host}...")
        self._runner.run(
            self._fetch, args=(token, config),
            on_success=self._display, on_error=self._on_error,
        )

    @staticmethod
    def _fetch(token: str, config: Any):
        if config.host_type == "github":
            import github as gh
            if config.host_url and config.host_url != "https://api.github.com":
                client = gh.Github(base_url=config.host_url, login_or_token=token)
            else:
                client = gh.Github(token)
            gh_user = client.get_user(config.user_name)
            return {
                "Username": gh_user.login,
                "Name": gh_user.name or "N/A",
                "Bio": gh_user.bio or "N/A",
                "Public repos": str(gh_user.public_repos),
                "Followers": str(gh_user.followers),
                "Following": str(gh_user.following),
                "Location": gh_user.location or "N/A",
                "Company": gh_user.company or "N/A",
                "URL": gh_user.html_url,
            }
        elif config.host_type == "gitlab":
            import gitlab
            gl = gitlab.Gitlab(config.host_url, private_token=token)
            gl.auth()
            gl_user = gl.user
            if gl_user is None:
                return {"Error": "GitLab authentication failed"}
            return {
                "Username": gl_user.username,
                "Name": gl_user.name or "N/A",
                "Bio": getattr(gl_user, "bio", "") or "N/A",
                "State": gl_user.state,
                "URL": gl_user.web_url,
            }
        return {"Error": "Unknown host type"}

    def _display(self, info: dict[str, str]):
        self._output.configure(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        for key, value in info.items():
            self._output.insert(tk.END, f"  {key}: ", "accent")
            self._output.insert(tk.END, f"{value}\n")
        self._output.configure(state=tk.DISABLED)
        self._status.set("Account info loaded")

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error: {exc}", "error")
        self._status.set(f"Error: {exc}")


# ── Update From Main panel ───────────────────────────────────────────


class UpdateFromMainPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Update Branches from Main")

        bar = _make_toolbar(self)
        self._host_var = tk.StringVar(value="github")
        for host in ("github", "gitlab", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self._host_var, value=host,
                bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
                activeforeground=_CLR_ACCENT, font=_FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        self._dry_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text="Dry run", variable=self._dry_var,
            bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
            font=_FONT_UI,
        ).pack(side=tk.LEFT, padx=12)
        _toolbar_btn(bar, "Update All", self._run_update)

        self._output = _make_output(self, height=22)

    def _run_update(self):
        host = self._host_var.get()
        configs = self._app.get_configs()
        config = configs.get(host)
        if not config:
            self._status.set(f"No configuration for {host}")
            return
        from git_mirror.services import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self._status.set(f"No access token for {host}")
            return
        if not self._dry_var.get():
            if not messagebox.askyesno("Update From Main", "Merge/rebase main into all local branches?"):
                return
        self._status.set("Updating branches...")
        _output_set(self._output, "Updating...\n")
        self._runner.run(
            self._do_update, args=(token, config, self._dry_var.get()),
            on_success=self._display, on_error=self._on_error,
        )

    @staticmethod
    def _do_update(token: str, config: Any, dry_run: bool):
        if not config.target_dir:
            return {"messages": [], "errors": ["No target directory configured"]}
        import git_mirror.manage_github as mgh
        import git_mirror.manage_gitlab as mgl
        from git_mirror.dummies import Dummy

        base_path = config.target_dir.expanduser()
        messages = []
        errors = []

        if config.host_type == "github":
            mgr = mgh.GithubRepoManager(
                token, base_path, config.user_name,
                include_private=config.include_private,
                include_forks=config.include_forks,
                host_domain=config.host_url or "https://api.github.com",
                dry_run=dry_run, prompt_for_changes=False,
            )
            try:
                mgr.update_all_branches(single_threaded=True)
                messages.append("Update complete.")
            except Exception as e:
                errors.append(str(e))
        else:
            messages.append("Update-from-main is currently GitHub-only in the GUI.")

        return {"messages": messages, "errors": errors}

    def _display(self, result: dict[str, Any]):
        lines = result["messages"] + [f"ERROR: {e}" for e in result["errors"]]
        _output_set(self._output, "\n".join(lines) if lines else "Done.")
        self._status.set("Update complete")

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error: {exc}", "error")
        self._status.set(f"Error: {exc}")


# ── Prune All panel ──────────────────────────────────────────────────


class PruneAllPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Prune Branches")

        bar = _make_toolbar(self)
        self._host_var = tk.StringVar(value="github")
        for host in ("github", "gitlab", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self._host_var, value=host,
                bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
                activeforeground=_CLR_ACCENT, font=_FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        self._dry_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            bar, text="Dry run", variable=self._dry_var,
            bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
            font=_FONT_UI,
        ).pack(side=tk.LEFT, padx=12)
        _toolbar_btn(bar, "Prune All", self._run_prune)

        self._output = _make_output(self, height=22)

    def _run_prune(self):
        host = self._host_var.get()
        configs = self._app.get_configs()
        config = configs.get(host)
        if not config:
            self._status.set(f"No configuration for {host}")
            return
        from git_mirror.services import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self._status.set(f"No access token for {host}")
            return
        if not self._dry_var.get():
            if not messagebox.askyesno("Prune", "This will delete local branches not on remote. Continue?"):
                return
        self._status.set("Pruning branches...")
        _output_set(self._output, "Pruning...\n")
        self._runner.run(
            self._do_prune, args=(token, config, self._dry_var.get()),
            on_success=self._display, on_error=self._on_error,
        )

    @staticmethod
    def _do_prune(token: str, config: Any, dry_run: bool):
        if not config.target_dir:
            return {"messages": [], "errors": ["No target directory configured"]}
        import git_mirror.manage_github as mgh

        base_path = config.target_dir.expanduser()
        messages = []
        errors = []

        if config.host_type == "github":
            mgr = mgh.GithubRepoManager(
                token, base_path, config.user_name,
                include_private=config.include_private,
                include_forks=config.include_forks,
                host_domain=config.host_url or "https://api.github.com",
                dry_run=dry_run, prompt_for_changes=False,
            )
            try:
                mgr.prune_all()
                messages.append("Prune complete.")
            except Exception as e:
                errors.append(str(e))
        else:
            messages.append("Prune is currently GitHub-only in the GUI.")

        return {"messages": messages, "errors": errors}

    def _display(self, result: dict[str, Any]):
        lines = result["messages"] + [f"ERROR: {e}" for e in result["errors"]]
        _output_set(self._output, "\n".join(lines) if lines else "Done.")
        self._status.set("Prune complete")

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error: {exc}", "error")
        self._status.set(f"Error: {exc}")


# ── Config / Init panel ──────────────────────────────────────────────


class ConfigPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Configuration")

        self._output = _make_output(self, height=18)

        bar = _make_toolbar(self)
        _toolbar_btn(bar, "View Config", self._view_config)
        _toolbar_btn(bar, "Open Config File", self._open_config)
        _toolbar_btn(bar, "Init New Host", self._init_host)

        self._view_config()

    def _view_config(self):
        self._status.set("Loading config...")
        self._runner.run(self._fetch, on_success=self._display, on_error=self._on_error)

    @staticmethod
    def _fetch():
        from git_mirror.services import load_all_configs
        from git_mirror.manage_config import default_config_path
        return load_all_configs(), default_config_path()

    def _display(self, result: tuple[dict[str, Any], Path]):
        configs, config_path = result
        self._output.configure(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        self._output.insert(tk.END, f"  Config file: {config_path}\n\n", "accent")
        found = False
        for host, config in configs.items():
            if config:
                found = True
                self._output.insert(tk.END, f"  [{host}]\n", "heading")
                self._output.insert(tk.END, f"    host_type:       {config.host_type}\n")
                self._output.insert(tk.END, f"    host_url:        {config.host_url}\n")
                self._output.insert(tk.END, f"    user_name:       {config.user_name}\n")
                self._output.insert(tk.END, f"    target_dir:      {config.target_dir}\n")
                self._output.insert(tk.END, f"    include_private: {config.include_private}\n")
                self._output.insert(tk.END, f"    include_forks:   {config.include_forks}\n")
                if config.group_id:
                    self._output.insert(tk.END, f"    group_id:        {config.group_id}\n")
                self._output.insert(tk.END, "\n")
        if not found:
            self._output.insert(tk.END, "  No hosts configured.\n", "warn")
            self._output.insert(tk.END, "  Click 'Init New Host' to set up a host.\n", "dim")
        self._output.configure(state=tk.DISABLED)
        self._status.set("Config loaded")

    def _open_config(self):
        import subprocess
        from git_mirror.manage_config import default_config_path
        path = default_config_path()
        if path.exists():
            subprocess.Popen(["notepad", str(path)])
        else:
            messagebox.showinfo("Config", f"Config file not found at {path}")

    def _init_host(self):
        messagebox.showinfo(
            "Init",
            "To initialize a new host interactively, run from the command line:\n\n"
            "  git_mirror init\n\n"
            "The init wizard requires terminal input and is not available in the GUI.\n"
            "After init, restart the GUI to see the new configuration.",
        )

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error: {exc}", "error")
        self._status.set(f"Error: {exc}")


# ── Sync Config panel ────────────────────────────────────────────────


class SyncConfigPanel(_BasePanel):
    def __init__(self, parent: tk.Widget, app: "GitMirrorApp"):
        super().__init__(parent, app)
        _make_heading(self, "Sync Config with Remote")

        bar = _make_toolbar(self)
        self._host_var = tk.StringVar(value="github")
        for host in ("github", "gitlab", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self._host_var, value=host,
                bg=_CLR_BG, fg=_CLR_FG, selectcolor=_CLR_BTN, activebackground=_CLR_BG,
                activeforeground=_CLR_ACCENT, font=_FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        _toolbar_btn(bar, "Sync Config", self._run_sync)

        self._output = _make_output(self, height=22)

    def _run_sync(self):
        host = self._host_var.get()
        configs = self._app.get_configs()
        config = configs.get(host)
        if not config:
            self._status.set(f"No configuration for {host}")
            return
        from git_mirror.services import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self._status.set(f"No access token for {host}")
            return
        self._status.set(f"Syncing config with {host}...")
        self._runner.run(
            self._do_sync, args=(token, host, config),
            on_success=self._display, on_error=self._on_error,
        )

    @staticmethod
    def _do_sync(token: str, host: str, config: Any):
        from git_mirror.services import list_repos_data
        from git_mirror.manage_config import ConfigManager, default_config_path
        repos = list_repos_data(token, host, config)
        repo_names = [f"{config.user_name}/{r.name}" for r in repos]
        cm = ConfigManager(default_config_path())
        cm.load_and_sync_config(host, repo_names)
        return f"Synced {len(repo_names)} repos to config."

    def _display(self, message: str):
        _output_set(self._output, message, "ok")
        self._status.set("Sync complete")

    def _on_error(self, exc: Exception):
        _output_set(self._output, f"Error: {exc}", "error")
        self._status.set(f"Error: {exc}")


# ── Main Application ─────────────────────────────────────────────────


class GitMirrorApp:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"git_mirror v{__version__}")
        self.root.configure(bg=_CLR_BG)
        self.root.minsize(1200, 750)

        # Start large enough to be useful
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = min(1400, screen_w - 100)
        h = min(850, screen_h - 100)
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.runner = _BackgroundRunner(self.root)
        self.status_var = tk.StringVar(value="Ready")
        self._configs: dict[str, Any] | None = None
        self._current_panel: tk.Frame | None = None
        self._sidebar_buttons: dict[str, tk.Button] = {}

        self._build_ui()

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────
        top_bar = tk.Frame(self.root, bg=_CLR_SIDEBAR, height=40)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        top_bar.pack_propagate(False)
        tk.Label(
            top_bar, text=f"  git_mirror v{__version__}", bg=_CLR_SIDEBAR, fg=_CLR_ACCENT,
            font=("Segoe UI", 13, "bold"), anchor=tk.W,
        ).pack(side=tk.LEFT, padx=8)
        tk.Label(
            top_bar, text="Multi-repo management for GitHub, GitLab & self-hosted",
            bg=_CLR_SIDEBAR, fg=_CLR_DIM, font=_FONT_UI, anchor=tk.W,
        ).pack(side=tk.LEFT, padx=16)

        # ── Main area: help | content | sidebar ─────────────────
        main = tk.Frame(self.root, bg=_CLR_BG)
        main.pack(fill=tk.BOTH, expand=True)

        # Left help panel
        help_frame = tk.Frame(main, bg=_CLR_SIDEBAR, width=220)
        help_frame.pack(side=tk.LEFT, fill=tk.Y)
        help_frame.pack_propagate(False)
        self._build_help_panel(help_frame)

        # Right sidebar (action buttons)
        sidebar = tk.Frame(main, bg=_CLR_SIDEBAR, width=180)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Centre content area
        self._content = tk.Frame(main, bg=_CLR_BG)
        self._content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Status bar ───────────────────────────────────────────
        status_bar = tk.Frame(self.root, bg=_CLR_SIDEBAR, height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        tk.Label(
            status_bar, textvariable=self.status_var,
            bg=_CLR_SIDEBAR, fg=_CLR_DIM, font=_FONT_DATA_SMALL, anchor=tk.W,
        ).pack(side=tk.LEFT, padx=12)

        # Show dashboard on start
        self._show_panel("dashboard")

    def _build_help_panel(self, parent: tk.Frame):
        tk.Label(
            parent, text="  Quick Reference", bg=_CLR_SIDEBAR, fg=_CLR_ACCENT,
            font=_FONT_UI_BOLD, anchor=tk.W,
        ).pack(fill=tk.X, padx=8, pady=(16, 8))

        help_items = [
            ("Dashboard", "Overview of your config\nand quick-start guide."),
            ("Local Changes", "Find dirty repos and\nunpushed commits."),
            ("List Repos", "Fetch repo list from\nyour configured host."),
            ("Clone All", "Clone all remote repos\ninto your target dir."),
            ("Pull All", "Pull latest changes in\nall local repos."),
            ("Not Repo", "Find directories that\naren't git repos."),
            ("Build Status", "Check GitHub Actions\nworkflow run results."),
            ("Update Main", "Merge/rebase main into\nall local branches."),
            ("Prune", "Remove local branches\ndeleted on remote."),
            ("Account", "View your source host\naccount information."),
            ("Doctor", "Verify config, tokens,\nand connectivity."),
            ("Config", "View and manage your\nconfiguration file."),
            ("Sync Config", "Sync config file repo\nlist with remote."),
        ]

        for title, desc in help_items:
            tk.Label(
                parent, text=title, bg=_CLR_SIDEBAR, fg=_CLR_FG,
                font=("Segoe UI", 9, "bold"), anchor=tk.W,
            ).pack(fill=tk.X, padx=16, pady=(6, 0))
            tk.Label(
                parent, text=desc, bg=_CLR_SIDEBAR, fg=_CLR_DIM,
                font=("Segoe UI", 8), anchor=tk.W, justify=tk.LEFT,
            ).pack(fill=tk.X, padx=20, pady=(0, 2))

    def _build_sidebar(self, parent: tk.Frame):
        tk.Label(
            parent, text="  Actions", bg=_CLR_SIDEBAR, fg=_CLR_ACCENT,
            font=_FONT_UI_BOLD, anchor=tk.W,
        ).pack(fill=tk.X, padx=8, pady=(16, 8))

        items = [
            ("dashboard", "Dashboard"),
            (None, None),  # separator
            ("local_changes", "Local Changes"),
            ("list_repos", "List Repos"),
            ("clone_all", "Clone All"),
            ("pull_all", "Pull All"),
            ("not_repo", "Not Repo"),
            ("build_status", "Build Status"),
            (None, None),
            ("update_main", "Update Main"),
            ("prune", "Prune"),
            (None, None),
            ("account", "Account"),
            ("doctor", "Doctor"),
            ("config", "Config"),
            ("sync_config", "Sync Config"),
        ]

        for item_id, label in items:
            if item_id is None or label is None:
                tk.Frame(parent, bg=_CLR_BORDER, height=1).pack(fill=tk.X, padx=12, pady=6)
                continue
            
            final_item_id: str = item_id

            def show_panel_cmd(pid: str = final_item_id) -> None:
                self._show_panel(pid)

            btn = tk.Button(
                parent,
                text=label,
                command=show_panel_cmd,
                bg=_CLR_SIDEBAR,
                fg=_CLR_FG,
                activebackground=_CLR_BTN_ACTIVE,
                activeforeground=_CLR_FG,
                font=_FONT_UI,
                relief=tk.FLAT,
                cursor="hand2",
                anchor=tk.W,
                padx=16,
                pady=5,
            )
            btn.pack(fill=tk.X, padx=4, pady=1)

            def on_enter(event: tk.Event, b: tk.Button = btn) -> None:
                b.configure(bg=_CLR_BTN)

            def on_leave(event: tk.Event, b: tk.Button = btn) -> None:
                if b != self._sidebar_buttons.get("_active"):
                    b.configure(bg=_CLR_SIDEBAR)

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            self._sidebar_buttons[item_id] = btn

    def _show_panel(self, panel_id: str):
        # Destroy current panel
        if self._current_panel:
            self._current_panel.destroy()

        # Update sidebar highlight
        for sid, btn in self._sidebar_buttons.items():
            btn.configure(bg=_CLR_SIDEBAR)
        if panel_id in self._sidebar_buttons:
            self._sidebar_buttons[panel_id].configure(bg=_CLR_BTN)
            self._sidebar_buttons["_active"] = self._sidebar_buttons[panel_id]

        # Panel factory
        builders: dict[str, type[_BasePanel]] = {
            "dashboard": DashboardPanel,
            "local_changes": LocalChangesPanel,
            "list_repos": ListReposPanel,
            "clone_all": CloneAllPanel,
            "pull_all": PullAllPanel,
            "not_repo": NotRepoPanel,
            "build_status": BuildStatusPanel,
            "update_main": UpdateFromMainPanel,
            "prune": PruneAllPanel,
            "account": ShowAccountPanel,
            "doctor": DoctorPanel,
            "config": ConfigPanel,
            "sync_config": SyncConfigPanel,
        }

        panel_cls = builders.get(panel_id, DashboardPanel)
        panel = panel_cls(self._content, self)
        panel.pack(fill=tk.BOTH, expand=True)
        self._current_panel = panel

    def get_configs(self) -> dict[str, Any]:
        """Get cached configs or load fresh."""
        if self._configs is None:
            from git_mirror.services import load_all_configs
            self._configs = load_all_configs()
        return self._configs

    def refresh_configs(self):
        """Force config reload."""
        self._configs = None

    def run(self):
        self.root.mainloop()


def launch_gui():
    """Entry point for the GUI."""
    app = GitMirrorApp()
    app.run()


if __name__ == "__main__":
    launch_gui()
