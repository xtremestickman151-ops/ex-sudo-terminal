# EX SUDO TERMINAL

A Windows GUI terminal for **PowerShell**, from EX Inc.

Runs a **persistent ConPTY PowerShell** session (pywinpty) (so `cd` and variables stick), streams output live, and can relaunch itself as administrator when you need elevated rights.

## Features
- **ConPTY**: interactive tools like `grok` run inside this window (keys forwarded while Running).
- Black/grey UI with monospace output and an input line (↑/↓ history, Enter to run, Ctrl+C to stop).
- **Run as admin** relaunches the app elevated (ShellExecute `runas`).
- **Install Grok CLI** one-click button runs: `irm https://x.ai/cli/install.ps1 | iex` (only when you click it).
- **Check for updates** in the sidebar / About page.
- Footer: ©2026 EX Inc.

## Install
1. Download **`EX SUDO TERMINAL Setup <version>.exe`** from [Releases](../../releases/latest) and run it. No admin needed for install: it goes to `%LOCALAPPDATA%\Programs\EX SUDO TERMINAL`.
2. SmartScreen may warn (unsigned): **More info → Run anyway**.

## Limitations
- Needs a real Windows console host (ConPTY). Under Wine, interactive input can be flaky.
- Interactive prompts that wait for keyboard input inside the PowerShell host may not work well.
- Full-screen TUI / console apps (editors, pagers, curses-style tools) are not supported.
- Ctrl+C stops by restarting the PowerShell session (in-progress state is lost).

## Build (Windows)
```
pip install pyinstaller
pyinstaller --onedir --noconsole --name "EX SUDO TERMINAL" --icon logo.ico --version-file version.txt --add-data "logo.ico;." --add-data "logo256.png;." ex_sudo_terminal.py
```
Installer: compile `installer.iss` with Inno Setup 6.

---
©2026 EX Inc.
