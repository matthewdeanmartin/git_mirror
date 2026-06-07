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
from pathlib import Path
from typing import Any, Callable

from git_mirror.__about__ import __version__

# ── Catppuccin Mocha palette ─────────────────────────────────────────

CLR_OK = "#22c55e"
CLR_WARN = "#eab308"
CLR_ERR = "#ef4444"
CLR_DIM = "#9ca3af"
CLR_BG = "#1e1e2e"
CLR_BG_ALT = "#252536"
CLR_FG = "#cdd6f4"
CLR_ACCENT = "#89b4fa"
CLR_SIDEBAR = "#181825"
CLR_BTN = "#313244"
CLR_BTN_ACTIVE = "#45475a"
CLR_BTN_HOVER = "#3b3b52"
CLR_BORDER = "#313244"
CLR_HEADER = "#a6adc8"

FONT_UI = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI", 10, "bold")
FONT_UI_HEADING = ("Segoe UI", 12, "bold")
FONT_DATA = ("Consolas", 10)
FONT_DATA_SMALL = ("Consolas", 9)

# ── Background runner ────────────────────────────────────────────────


class BackgroundRunner:
    """Run a function in a daemon thread, post callbacks on the main thread."""

    def __init__(self, root: tk.Tk):
        self.root = root

    def run(
        self,
        func: Callable[..., Any],
        *,
        args: tuple[Any, ...] = (),
        on_success: Callable[..., Any] | None = None,
        on_error: Callable[[Exception], Any] | None = None,
    ) -> None:
        def worker():
            try:
                result = func(*args)
                if on_success:
                    self.root.after(0, on_success, result)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                if on_error:
                    self.root.after(0, on_error, exc)

        t = threading.Thread(target=worker, daemon=True)
        t.start()


# ── Widget helpers ───────────────────────────────────────────────────


def make_tree(parent: tk.Widget, columns: list[tuple[str, int]], height: int = 20) -> ttk.Treeview:
    """Create a themed treeview with scrollbar and colour tags."""
    frame = tk.Frame(parent, bg=CLR_BG)
    frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Dark.Treeview",
        background=CLR_BG_ALT,
        foreground=CLR_FG,
        fieldbackground=CLR_BG_ALT,
        font=FONT_DATA,
        rowheight=24,
        borderwidth=0,
    )
    style.configure(
        "Dark.Treeview.Heading",
        background=CLR_BTN,
        foreground=CLR_HEADER,
        font=FONT_UI_BOLD,
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Dark.Treeview",
        background=[("selected", CLR_BTN_ACTIVE)],
        foreground=[("selected", CLR_FG)],
    )
    style.map(
        "Dark.Treeview.Heading",
        background=[("active", CLR_BTN_ACTIVE)],
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

    tree.tag_configure("ok", foreground=CLR_OK)
    tree.tag_configure("warn", foreground=CLR_WARN)
    tree.tag_configure("error", foreground=CLR_ERR)
    tree.tag_configure("dim", foreground=CLR_DIM)
    return tree


def make_output(parent: tk.Widget, height: int = 15) -> tk.Text:
    """Read-only scrolled text area for output/diff display."""
    frame = tk.Frame(parent, bg=CLR_BG)
    frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    text = tk.Text(
        frame,
        height=height,
        bg=CLR_BG_ALT,
        fg=CLR_FG,
        insertbackground=CLR_FG,
        font=FONT_DATA,
        wrap=tk.WORD,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=CLR_BORDER,
        state=tk.DISABLED,
    )
    vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=vsb.set)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    text.tag_configure("ok", foreground=CLR_OK)
    text.tag_configure("warn", foreground=CLR_WARN)
    text.tag_configure("error", foreground=CLR_ERR)
    text.tag_configure("dim", foreground=CLR_DIM)
    text.tag_configure("accent", foreground=CLR_ACCENT)
    text.tag_configure("heading", foreground=CLR_ACCENT, font=FONT_UI_BOLD)
    return text


def output_set(text_widget: tk.Text, content: str, tag: str | None = None) -> None:
    """Replace text content (handles enable/disable state)."""
    text_widget.configure(state=tk.NORMAL)
    text_widget.delete("1.0", tk.END)
    if tag:
        text_widget.insert(tk.END, content, tag)
    else:
        text_widget.insert(tk.END, content)
    text_widget.configure(state=tk.DISABLED)


def output_append(text_widget: tk.Text, content: str, tag: str | None = None) -> None:
    """Append to text content."""
    text_widget.configure(state=tk.NORMAL)
    if tag:
        text_widget.insert(tk.END, content, tag)
    else:
        text_widget.insert(tk.END, content)
    text_widget.configure(state=tk.DISABLED)
    text_widget.see(tk.END)


def make_toolbar(parent: tk.Widget) -> tk.Frame:
    """Horizontal button bar."""
    bar = tk.Frame(parent, bg=CLR_BG)
    bar.pack(fill=tk.X, padx=8, pady=(8, 4))
    return bar


def toolbar_btn(bar: tk.Frame, text: str, command: Callable[[], Any], width: int = 18) -> tk.Button:
    """Themed button inside a toolbar."""
    btn = tk.Button(
        bar,
        text=text,
        command=command,
        bg=CLR_BTN,
        fg=CLR_FG,
        activebackground=CLR_BTN_ACTIVE,
        activeforeground=CLR_FG,
        font=FONT_UI,
        relief=tk.FLAT,
        cursor="hand2",
        width=width,
        padx=8,
        pady=4,
    )
    btn.pack(side=tk.LEFT, padx=4)
    btn.bind("<Enter>", lambda e: btn.configure(bg=CLR_BTN_HOVER))
    btn.bind("<Leave>", lambda e: btn.configure(bg=CLR_BTN))
    return btn


def make_heading(parent: tk.Widget, text: str) -> tk.Label:
    lbl = tk.Label(parent, text=text, bg=CLR_BG, fg=CLR_ACCENT, font=FONT_UI_HEADING, anchor=tk.W)
    lbl.pack(fill=tk.X, padx=12, pady=(12, 4))
    return lbl


# ── Base panel ───────────────────────────────────────────────────────


class BasePanel(tk.Frame):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, bg=CLR_BG)
        self.app = app
        self.runner = app.runner
        self.status = app.status_var


# ── Dashboard panel ──────────────────────────────────────────────────


class DashboardPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Dashboard")

        self.output = make_output(self, height=24)
        self.load()

    def load(self):
        self.status.set("Loading configuration...")
        self.runner.run(self.fetch, on_success=self.display, on_error=self.on_error)

    @staticmethod
    def fetch():
        from git_mirror.core import load_all_configs
        return load_all_configs()

    def display(self, configs: dict[str, Any]):
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
        lines.append(("  1. Click Init to configure a host (GitHub or self-hosted GitHub Enterprise)\n", "dim"))
        lines.append(("  2. Click Doctor to verify your setup\n", "dim"))
        lines.append(("  3. Use Clone All to pull down all your repos\n", "dim"))
        lines.append(("  4. Use Pull All to keep them up to date\n", "dim"))
        lines.append(("  5. Use Local Changes to see dirty repos and unpushed commits\n", "dim"))

        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        for text, tag in lines:
            if tag:
                self.output.insert(tk.END, text, tag)
            else:
                self.output.insert(tk.END, text)
        self.output.configure(state=tk.DISABLED)
        self.status.set("Ready")

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error loading config: {exc}", "error")
        self.status.set("Error loading configuration")


# ── Local Changes panel ──────────────────────────────────────────────


class LocalChangesPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Local Changes")

        bar = make_toolbar(self)
        toolbar_btn(bar, "Scan All Hosts", self.scan_all)

        self.tree = make_tree(self, [
            ("Repository", 250),
            ("Status", 100),
            ("Unpushed", 200),
            ("Untracked Branches", 200),
        ], height=22)

    def scan_all(self):
        self.status.set("Scanning for local changes...")
        configs = self.app.get_configs()
        dirs = [c.target_dir for c in configs.values() if c and c.target_dir and c.target_dir.exists()]
        if not dirs:
            self.status.set("No configured target directories found")
            return
        self.runner.run(self.fetch, args=(dirs,), on_success=self.display, on_error=self.on_error)

    @staticmethod
    def fetch(dirs: list[Path]):
        from git_mirror.core import scan_local_changes
        all_statuses = []
        for d in dirs:
            all_statuses.extend(scan_local_changes(d))
        return all_statuses

    def display(self, statuses: list[Any]):
        for row in self.tree.get_children():
            self.tree.delete(row)

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

            self.tree.insert("", tk.END, values=(s.path.name, status_text, unpushed, untracked), tags=(tag,))

        self.status.set(f"Scanned {len(statuses)} repos, {dirty} need attention")

    def on_error(self, exc: Exception):
        self.status.set(f"Error: {exc}")


# ── List Repos panel ─────────────────────────────────────────────────


class ListReposPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Repositories")

        bar = make_toolbar(self)
        self.host_var = tk.StringVar(value="github")
        for host in ("github", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self.host_var, value=host,
                bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
                activeforeground=CLR_ACCENT, font=FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        toolbar_btn(bar, "Fetch Repos", self.fetch_repos)

        self.tree = make_tree(self, [
            ("Name", 200),
            ("Description", 350),
            ("Private", 80),
            ("Fork", 80),
        ], height=22)

    def fetch_repos(self):
        host = self.host_var.get()
        configs = self.app.get_configs()
        config = configs.get(host)
        if not config:
            self.status.set(f"No configuration for {host}")
            return
        from git_mirror.core import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self.status.set(f"No access token for {host}")
            return
        self.status.set(f"Fetching repos from {host}...")
        self.runner.run(
            self.fetch, args=(token, host, config),
            on_success=self.display, on_error=self.on_error,
        )

    @staticmethod
    def fetch(token: str, host: str, config: Any):
        from git_mirror.core import list_repos_data
        return list_repos_data(token, host, config)

    def display(self, repos: list[Any]):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for repo in repos:
            tag = "dim" if repo.fork else ""
            self.tree.insert("", tk.END, values=(
                repo.name, repo.description,
                "Yes" if repo.private else "No",
                "Yes" if repo.fork else "No",
            ), tags=(tag,) if tag else ())
        self.status.set(f"Found {len(repos)} repositories")

    def on_error(self, exc: Exception):
        self.status.set(f"Error: {exc}")


# ── Clone All panel ──────────────────────────────────────────────────


class CloneAllPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Clone All Repositories")

        bar = make_toolbar(self)
        self.host_var = tk.StringVar(value="github")
        for host in ("github", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self.host_var, value=host,
                bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
                activeforeground=CLR_ACCENT, font=FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        self.dry_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text="Dry run", variable=self.dry_var,
            bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
            font=FONT_UI,
        ).pack(side=tk.LEFT, padx=12)
        toolbar_btn(bar, "Clone All", self.run_clone)

        self.output = make_output(self, height=22)

    def run_clone(self):
        host = self.host_var.get()
        configs = self.app.get_configs()
        config = configs.get(host)
        if not config:
            self.status.set(f"No configuration for {host}")
            return
        from git_mirror.core import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self.status.set(f"No access token for {host}")
            return
        if not self.dry_var.get():
            if not messagebox.askyesno("Clone All", f"Clone all repos from {host} to {config.target_dir}?"):
                return
        self.status.set(f"Cloning repos from {host}...")
        output_set(self.output, "Cloning...\n")
        self.runner.run(
            self.do_clone, args=(token, config, self.dry_var.get()),
            on_success=self.display, on_error=self.on_error,
        )

    @staticmethod
    def do_clone(token: str, config: Any, dry_run: bool):
        from git_mirror.core import clone_all_repos
        return clone_all_repos(token, config, dry_run)

    def display(self, result: Any):
        lines = []
        for msg in result.messages:
            lines.append(msg)
        for err in result.errors:
            lines.append(f"ERROR: {err}")
        output_set(self.output, "\n".join(lines))
        self.status.set(f"Clone complete: {len(result.messages)} repos, {len(result.errors)} errors")

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error: {exc}", "error")
        self.status.set(f"Error: {exc}")


# ── Pull All panel ───────────────────────────────────────────────────


class PullAllPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Pull All Repositories")

        bar = make_toolbar(self)
        self.dry_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text="Dry run", variable=self.dry_var,
            bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
            font=FONT_UI,
        ).pack(side=tk.LEFT, padx=12)
        toolbar_btn(bar, "Pull All Hosts", self.run_pull)

        self.output = make_output(self, height=22)

    def run_pull(self):
        configs = self.app.get_configs()
        dirs = [c.target_dir for c in configs.values() if c and c.target_dir and c.target_dir.exists()]
        if not dirs:
            self.status.set("No configured target directories found")
            return
        if not self.dry_var.get():
            if not messagebox.askyesno("Pull All", f"Pull all repos in {len(dirs)} target directories?"):
                return
        self.status.set("Pulling all repos...")
        output_set(self.output, "Pulling...\n")
        self.runner.run(
            self.do_pull, args=(dirs, self.dry_var.get()),
            on_success=self.display, on_error=self.on_error,
        )

    @staticmethod
    def do_pull(dirs: list[Path], dry_run: bool):
        from git_mirror.core import pull_all_repos
        all_results: dict[str, Any] = {"messages": [], "errors": []}
        for d in dirs:
            r = pull_all_repos(d, dry_run)
            all_results["messages"].extend(r.messages)
            all_results["errors"].extend(r.errors)
        return all_results

    def display(self, result: dict[str, Any]):
        lines = result["messages"] + [f"ERROR: {e}" for e in result["errors"]]
        output_set(self.output, "\n".join(lines) if lines else "No repos found.")
        self.status.set(f"Pull complete: {len(result['messages'])} repos, {len(result['errors'])} errors")

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error: {exc}", "error")
        self.status.set(f"Error: {exc}")


# ── Not-Repo panel ──────────────────────────────────────────────────


class NotRepoPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Non-Repository Directories")

        bar = make_toolbar(self)
        toolbar_btn(bar, "Scan All Hosts", self.scan)

        self.tree = make_tree(self, [
            ("Path", 450),
            ("Reason", 300),
        ], height=22)

    def scan(self):
        configs = self.app.get_configs()
        dirs = [c.target_dir for c in configs.values() if c and c.target_dir and c.target_dir.exists()]
        if not dirs:
            self.status.set("No configured target directories found")
            return
        self.status.set("Scanning...")
        self.runner.run(self.fetch, args=(dirs,), on_success=self.display, on_error=self.on_error)

    @staticmethod
    def fetch(dirs: list[Path]):
        from git_mirror.core import find_non_repos
        results = []
        for d in dirs:
            results.extend(find_non_repos(d))
        return results

    def display(self, results: list[tuple[str, str]]):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for path, reason in results:
            self.tree.insert("", tk.END, values=(path, reason), tags=("warn",))
        self.status.set(f"Found {len(results)} non-repo directories")

    def on_error(self, exc: Exception):
        self.status.set(f"Error: {exc}")


# ── Build Status panel ───────────────────────────────────────────────


class BuildStatusPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Build Status (GitHub Actions)")

        bar = make_toolbar(self)
        self.host_var = tk.StringVar(value="github")
        for host in ("github", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self.host_var, value=host,
                bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
                activeforeground=CLR_ACCENT, font=FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        toolbar_btn(bar, "Fetch Builds", self.fetch_builds)

        self.tree = make_tree(self, [
            ("Repository", 180),
            ("Conclusion", 100),
            ("Details", 500),
        ], height=22)

    def fetch_builds(self):
        host = self.host_var.get()
        configs = self.app.get_configs()
        config = configs.get(host)
        if not config:
            self.status.set(f"No configuration for {host}")
            return
        from git_mirror.core import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self.status.set(f"No access token for {host}")
            return
        self.status.set(f"Fetching build statuses from {host}...")
        self.runner.run(
            self.fetch, args=(token, config),
            on_success=self.display, on_error=self.on_error,
        )

    @staticmethod
    def fetch(token: str, config: Any):
        from git_mirror.core import get_build_statuses
        return get_build_statuses(token, config)

    def display(self, builds: list[Any]):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for b in builds:
            if b.conclusion == "success":
                tag = "ok"
            elif b.conclusion == "failure":
                tag = "error"
            elif b.conclusion == "cancelled":
                tag = "warn"
            else:
                tag = "dim"
            self.tree.insert("", tk.END, values=(b.repo_name, b.conclusion or "pending", b.status_message), tags=(tag,))
        self.status.set(f"Found {len(builds)} build results")

    def on_error(self, exc: Exception):
        self.status.set(f"Error: {exc}")


# ── Doctor panel ─────────────────────────────────────────────────────


class DoctorPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Doctor - Configuration Health")

        bar = make_toolbar(self)
        toolbar_btn(bar, "Run Doctor", self.run_doctor)

        self.output = make_output(self, height=22)
        self.run_doctor()

    def run_doctor(self):
        self.status.set("Running doctor checks...")
        self.runner.run(self.fetch, on_success=self.display, on_error=self.on_error)

    @staticmethod
    def fetch():
        from git_mirror.core import run_doctor
        return run_doctor()

    def display(self, results: list[tuple[str, list[Any]]]):
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        if not results:
            self.output.insert(tk.END, "No hosts configured. Run Init first.\n", "warn")
        for host_label, checks in results:
            self.output.insert(tk.END, f"\n  {host_label}\n", "heading")
            for check in checks:
                prefix = "[OK]  " if check.ok else "[FAIL]"
                tag = "ok" if check.ok else "error"
                self.output.insert(tk.END, f"    {prefix} {check.name}: {check.details}\n", tag)
                if hasattr(check, "fix") and check.fix:
                    self.output.insert(tk.END, f"           Fix: {check.fix}\n", "warn")
        self.output.configure(state=tk.DISABLED)
        self.status.set("Doctor complete")

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error: {exc}", "error")
        self.status.set(f"Error: {exc}")


# ── Show Account panel ───────────────────────────────────────────────


class ShowAccountPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Account Information")

        bar = make_toolbar(self)
        self.host_var = tk.StringVar(value="github")
        for host in ("github", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self.host_var, value=host,
                bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
                activeforeground=CLR_ACCENT, font=FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        toolbar_btn(bar, "Fetch Account", self.fetch_account)

        self.output = make_output(self, height=22)

    def fetch_account(self):
        host = self.host_var.get()
        configs = self.app.get_configs()
        config = configs.get(host)
        if not config:
            self.status.set(f"No configuration for {host}")
            return
        from git_mirror.core import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self.status.set(f"No access token for {host}")
            return
        self.status.set(f"Fetching account info from {host}...")
        self.runner.run(
            self.fetch, args=(token, config),
            on_success=self.display, on_error=self.on_error,
        )

    @staticmethod
    def fetch(token: str, config: Any):
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
        return {"Error": "Unknown host type"}

    def display(self, info: dict[str, str]):
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        for key, value in info.items():
            self.output.insert(tk.END, f"  {key}: ", "accent")
            self.output.insert(tk.END, f"{value}\n")
        self.output.configure(state=tk.DISABLED)
        self.status.set("Account info loaded")

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error: {exc}", "error")
        self.status.set(f"Error: {exc}")


# ── Update From Main panel ───────────────────────────────────────────


class UpdateFromMainPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Update Branches from Main")

        bar = make_toolbar(self)
        self.host_var = tk.StringVar(value="github")
        for host in ("github", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self.host_var, value=host,
                bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
                activeforeground=CLR_ACCENT, font=FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        self.dry_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text="Dry run", variable=self.dry_var,
            bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
            font=FONT_UI,
        ).pack(side=tk.LEFT, padx=12)
        toolbar_btn(bar, "Update All", self.run_update)

        self.output = make_output(self, height=22)

    def run_update(self):
        host = self.host_var.get()
        configs = self.app.get_configs()
        config = configs.get(host)
        if not config:
            self.status.set(f"No configuration for {host}")
            return
        from git_mirror.core import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self.status.set(f"No access token for {host}")
            return
        if not self.dry_var.get():
            if not messagebox.askyesno("Update From Main", "Merge/rebase main into all local branches?"):
                return
        self.status.set("Updating branches...")
        output_set(self.output, "Updating...\n")
        self.runner.run(
            self.do_update, args=(token, config, self.dry_var.get()),
            on_success=self.display, on_error=self.on_error,
        )

    @staticmethod
    def do_update(token: str, config: Any, dry_run: bool):
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
                mgr.update_all_branches(single_threaded=True)
                messages.append("Update complete.")
            except Exception as e:
                errors.append(str(e))
        else:
            messages.append("Update-from-main is currently GitHub-only in the GUI.")

        return {"messages": messages, "errors": errors}

    def display(self, result: dict[str, Any]):
        lines = result["messages"] + [f"ERROR: {e}" for e in result["errors"]]
        output_set(self.output, "\n".join(lines) if lines else "Done.")
        self.status.set("Update complete")

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error: {exc}", "error")
        self.status.set(f"Error: {exc}")


# ── Prune All panel ──────────────────────────────────────────────────


class PruneAllPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Prune Branches")

        bar = make_toolbar(self)
        self.host_var = tk.StringVar(value="github")
        for host in ("github", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self.host_var, value=host,
                bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
                activeforeground=CLR_ACCENT, font=FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        self.dry_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            bar, text="Dry run", variable=self.dry_var,
            bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
            font=FONT_UI,
        ).pack(side=tk.LEFT, padx=12)
        toolbar_btn(bar, "Prune All", self.run_prune)

        self.output = make_output(self, height=22)

    def run_prune(self):
        host = self.host_var.get()
        configs = self.app.get_configs()
        config = configs.get(host)
        if not config:
            self.status.set(f"No configuration for {host}")
            return
        from git_mirror.core import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self.status.set(f"No access token for {host}")
            return
        if not self.dry_var.get():
            if not messagebox.askyesno("Prune", "This will delete local branches not on remote. Continue?"):
                return
        self.status.set("Pruning branches...")
        output_set(self.output, "Pruning...\n")
        self.runner.run(
            self.do_prune, args=(token, config, self.dry_var.get()),
            on_success=self.display, on_error=self.on_error,
        )

    @staticmethod
    def do_prune(token: str, config: Any, dry_run: bool):
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
            except Exception as e:  # pylint: disable=broad-exception-caught
                errors.append(str(e))
        else:
            messages.append("Prune is currently GitHub-only in the GUI.")

        return {"messages": messages, "errors": errors}

    def display(self, result: dict[str, Any]):
        lines = result["messages"] + [f"ERROR: {e}" for e in result["errors"]]
        output_set(self.output, "\n".join(lines) if lines else "Done.")
        self.status.set("Prune complete")

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error: {exc}", "error")
        self.status.set(f"Error: {exc}")


# ── Config / Init panel ──────────────────────────────────────────────


class ConfigPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Configuration")

        self.output = make_output(self, height=18)

        bar = make_toolbar(self)
        toolbar_btn(bar, "View Config", self.view_config)
        toolbar_btn(bar, "Open Config File", self.open_config)
        toolbar_btn(bar, "Init New Host", self.init_host)

        self.view_config()

    def view_config(self):
        self.status.set("Loading config...")
        self.runner.run(self.fetch, on_success=self.display, on_error=self.on_error)

    @staticmethod
    def fetch():
        from git_mirror.core import load_all_configs
        from git_mirror.manage_config import default_config_path
        return load_all_configs(), default_config_path()

    def display(self, result: tuple[dict[str, Any], Path]):
        configs, config_path = result
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, f"  Config file: {config_path}\n\n", "accent")
        found = False
        for host, config in configs.items():
            if config:
                found = True
                self.output.insert(tk.END, f"  [{host}]\n", "heading")
                self.output.insert(tk.END, f"    host_type:       {config.host_type}\n")
                self.output.insert(tk.END, f"    host_url:        {config.host_url}\n")
                self.output.insert(tk.END, f"    user_name:       {config.user_name}\n")
                self.output.insert(tk.END, f"    target_dir:      {config.target_dir}\n")
                self.output.insert(tk.END, f"    include_private: {config.include_private}\n")
                self.output.insert(tk.END, f"    include_forks:   {config.include_forks}\n")
                self.output.insert(tk.END, "\n")
        if not found:
            self.output.insert(tk.END, "  No hosts configured.\n", "warn")
            self.output.insert(tk.END, "  Click 'Init New Host' to set up a host.\n", "dim")
        self.output.configure(state=tk.DISABLED)
        self.status.set("Config loaded")

    def open_config(self):
        import os

        from git_mirror.manage_config import default_config_path

        path = default_config_path()
        if path.exists():
            try:
                os.startfile(path)  # nosec
            except AttributeError:
                # Not on Windows, though this GUI is currently Windows-focused
                import subprocess  # nosec

                subprocess.Popen(["notepad", str(path)])  # nosec
        else:
            messagebox.showinfo("Config Not Found", f"No config file found at {path}")

    def init_host(self):
        messagebox.showinfo(
            "Init",
            "To initialize a new host interactively, run from the command line:\n\n"
            "  git_mirror init\n\n"
            "The init wizard requires terminal input and is not available in the GUI.\n"
            "After initializing, click 'Refresh Dashboard' to see the new host.",
        )

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error: {exc}", "error")
        self.status.set(f"Error: {exc}")



# ── Sync Config panel ────────────────────────────────────────────────


class SyncConfigPanel(BasePanel):
    def __init__(self, parent: tk.Widget, app: GitMirrorApp):
        super().__init__(parent, app)
        make_heading(self, "Sync Config with Remote")

        bar = make_toolbar(self)
        self.host_var = tk.StringVar(value="github")
        for host in ("github", "selfhosted"):
            tk.Radiobutton(
                bar, text=host.title(), variable=self.host_var, value=host,
                bg=CLR_BG, fg=CLR_FG, selectcolor=CLR_BTN, activebackground=CLR_BG,
                activeforeground=CLR_ACCENT, font=FONT_UI, indicatoron=False,
                padx=12, pady=4, relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.LEFT, padx=2)
        toolbar_btn(bar, "Sync Config", self.run_sync)

        self.output = make_output(self, height=22)

    def run_sync(self):
        host = self.host_var.get()
        configs = self.app.get_configs()
        config = configs.get(host)
        if not config:
            self.status.set(f"No configuration for {host}")
            return
        from git_mirror.core import get_token_for_host
        token = get_token_for_host(config)
        if not token:
            self.status.set(f"No access token for {host}")
            return
        self.status.set(f"Syncing config with {host}...")
        self.runner.run(
            self.do_sync, args=(token, host, config),
            on_success=self.display, on_error=self.on_error,
        )

    @staticmethod
    def do_sync(token: str, host: str, config: Any):
        from git_mirror.core import list_repos_data
        from git_mirror.manage_config import ConfigManager, default_config_path
        repos = list_repos_data(token, host, config)
        repo_names = [f"{config.user_name}/{r.name}" for r in repos]
        cm = ConfigManager(default_config_path())
        cm.load_and_sync_config(host, repo_names)
        return f"Synced {len(repo_names)} repos to config."

    def display(self, message: str):
        output_set(self.output, message, "ok")
        self.status.set("Sync complete")

    def on_error(self, exc: Exception):
        output_set(self.output, f"Error: {exc}", "error")
        self.status.set(f"Error: {exc}")


# ── Main Application ─────────────────────────────────────────────────


class GitMirrorApp:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"git_mirror v{__version__}")
        self.root.configure(bg=CLR_BG)
        self.root.minsize(1200, 750)

        # Start large enough to be useful
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = min(1400, screen_w - 100)
        h = min(850, screen_h - 100)
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.runner = BackgroundRunner(self.root)
        self.status_var = tk.StringVar(value="Ready")
        self.configs: dict[str, Any] | None = None
        self.current_panel: tk.Frame | None = None
        self.sidebar_buttons: dict[str, tk.Button] = {}

        self.build_ui()

    def build_ui(self):
        # ── Top bar ──────────────────────────────────────────────
        top_bar = tk.Frame(self.root, bg=CLR_SIDEBAR, height=40)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        top_bar.pack_propagate(False)
        tk.Label(
            top_bar, text=f"  git_mirror v{__version__}", bg=CLR_SIDEBAR, fg=CLR_ACCENT,
            font=("Segoe UI", 13, "bold"), anchor=tk.W,
        ).pack(side=tk.LEFT, padx=8)
        tk.Label(
            top_bar, text="Multi-repo management for GitHub & self-hosted GitHub Enterprise",
            bg=CLR_SIDEBAR, fg=CLR_DIM, font=FONT_UI, anchor=tk.W,
        ).pack(side=tk.LEFT, padx=16)

        # ── Main area: help | content | sidebar ─────────────────
        main = tk.Frame(self.root, bg=CLR_BG)
        main.pack(fill=tk.BOTH, expand=True)

        # Left help panel
        help_frame = tk.Frame(main, bg=CLR_SIDEBAR, width=220)
        help_frame.pack(side=tk.LEFT, fill=tk.Y)
        help_frame.pack_propagate(False)
        self.build_help_panel(help_frame)

        # Right sidebar (action buttons)
        sidebar = tk.Frame(main, bg=CLR_SIDEBAR, width=180)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar.pack_propagate(False)
        self.build_sidebar(sidebar)

        # Centre content area
        self.content = tk.Frame(main, bg=CLR_BG)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Status bar ───────────────────────────────────────────
        status_bar = tk.Frame(self.root, bg=CLR_SIDEBAR, height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        tk.Label(
            status_bar, textvariable=self.status_var,
            bg=CLR_SIDEBAR, fg=CLR_DIM, font=FONT_DATA_SMALL, anchor=tk.W,
        ).pack(side=tk.LEFT, padx=12)

        # Show dashboard on start
        self.show_panel("dashboard")

    def build_help_panel(self, parent: tk.Frame):
        tk.Label(
            parent, text="  Quick Reference", bg=CLR_SIDEBAR, fg=CLR_ACCENT,
            font=FONT_UI_BOLD, anchor=tk.W,
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
                parent, text=title, bg=CLR_SIDEBAR, fg=CLR_FG,
                font=("Segoe UI", 9, "bold"), anchor=tk.W,
            ).pack(fill=tk.X, padx=16, pady=(6, 0))
            tk.Label(
                parent, text=desc, bg=CLR_SIDEBAR, fg=CLR_DIM,
                font=("Segoe UI", 8), anchor=tk.W, justify=tk.LEFT,
            ).pack(fill=tk.X, padx=20, pady=(0, 2))

    def build_sidebar(self, parent: tk.Frame):
        tk.Label(
            parent, text="  Actions", bg=CLR_SIDEBAR, fg=CLR_ACCENT,
            font=FONT_UI_BOLD, anchor=tk.W,
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
                tk.Frame(parent, bg=CLR_BORDER, height=1).pack(fill=tk.X, padx=12, pady=6)
                continue
            
            final_item_id: str = item_id

            def show_panel_cmd(pid: str = final_item_id) -> None:
                self.show_panel(pid)

            btn = tk.Button(
                parent,
                text=label,
                command=show_panel_cmd,
                bg=CLR_SIDEBAR,
                fg=CLR_FG,
                activebackground=CLR_BTN_ACTIVE,
                activeforeground=CLR_FG,
                font=FONT_UI,
                relief=tk.FLAT,
                cursor="hand2",
                anchor=tk.W,
                padx=16,
                pady=5,
            )
            btn.pack(fill=tk.X, padx=4, pady=1)

            def on_enter(event: tk.Event, b: tk.Button = btn) -> None:
                b.configure(bg=CLR_BTN)

            def on_leave(event: tk.Event, b: tk.Button = btn) -> None:
                if b != self.sidebar_buttons.get("active"):
                    b.configure(bg=CLR_SIDEBAR)

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            self.sidebar_buttons[item_id] = btn

    def show_panel(self, panel_id: str):
        # Destroy current panel
        if self.current_panel:
            self.current_panel.destroy()

        # Update sidebar highlight
        for _, btn in self.sidebar_buttons.items():
            btn.configure(bg=CLR_SIDEBAR)
        if panel_id in self.sidebar_buttons:
            self.sidebar_buttons[panel_id].configure(bg=CLR_BTN)
            self.sidebar_buttons["active"] = self.sidebar_buttons[panel_id]

        # Panel factory
        builders: dict[str, type[BasePanel]] = {
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
        panel = panel_cls(self.content, self)
        panel.pack(fill=tk.BOTH, expand=True)
        self.current_panel = panel

    def get_configs(self) -> dict[str, Any]:
        """Get cached configs or load fresh."""
        if self.configs is None:
            from git_mirror.core import load_all_configs
            self.configs = load_all_configs()
        return self.configs

    def refresh_configs(self):
        """Force config reload."""
        self.configs = None

    def run(self):
        self.root.mainloop()


def launch_gui():
    """Entry point for the GUI."""
    app = GitMirrorApp()
    app.run()


if __name__ == "__main__":
    launch_gui()
