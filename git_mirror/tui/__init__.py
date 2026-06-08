# Deferred import — like git_mirror/gui, the Textual app is only loaded when the
# user explicitly launches the TUI (git_mirror_tui).  Importing this package
# does not pull in textual; that happens inside app.launch_tui().
