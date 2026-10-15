"""EX SUDO TERMINAL - persistent PowerShell GUI with ConPTY for interactive tools. ©2026 EX Inc."""
import ctypes, json, os, queue, re, subprocess, sys, threading, time, urllib.request
import tkinter as tk
from tkinter import messagebox

APP = "EX SUDO TERMINAL"
APP_VERSION = "1.1.1"
COPYRIGHT = "\u00a92026 EX Inc."
UPDATE_URL = "https://raw.githubusercontent.com/xtremestickman151-ops/ex-sudo-terminal/main/latest.json"
GROK_CLI = "irm https://x.ai/cli/install.ps1 | iex"
MARKER = "__EXSUDO_DONE__"
NOWIN = 0x08000000
BG, SIDE, CARD, CARD2, BORDER = "#000000", "#0a0a0a", "#1c1c1e", "#2a2a2d", "#3a3a3d"
TXT, MUT, ACCENT, ERR = "#f2f2f4", "#9a9aa0", "#e5a524", "#ff453a"
FONT, MONO = "Segoe UI", "Consolas"
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)|\x1b.")
PS_PROMPT_RE = re.compile(r"(?m)^PS [^\r\n]*>\s*$")
_MUTEX = None

try:
    import winpty
    HAS_WINPTY = True
except Exception:
    HAS_WINPTY = False


def res_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def is_admin():
    try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception: return False


def is_wine():
    try: return bool(ctypes.windll.ntdll.wine_get_version)
    except Exception: return False


def relaunch_admin():
    global _MUTEX
    if _MUTEX:
        try: ctypes.windll.kernel32.CloseHandle(_MUTEX)
        except Exception: pass
    exe = sys.executable
    params = "" if getattr(sys, "frozen", False) else '"%s"' % os.path.abspath(__file__)
    if ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1) > 32:
        os._exit(0)


def single_instance():
    global _MUTEX
    if os.name != "nt": return True
    try:
        k = ctypes.windll.kernel32
        _MUTEX = k.CreateMutexW(None, False, "Local\\EXSudoTerminal_SingleInstance")
        if k.GetLastError() != 183: return True
        u = ctypes.windll.user32
        for _ in range(10):
            found = []
            def cb(h, l):
                buf = ctypes.create_unicode_buffer(256)
                u.GetWindowTextW(h, buf, 256)
                if buf.value.startswith(APP) and u.IsWindowVisible(h): found.append(h)
                return True
            u.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(cb), 0)
            if found:
                u.ShowWindow(found[0], 9); u.SetForegroundWindow(found[0]); return False
            time.sleep(0.3)
        return True
    except Exception:
        return True


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:4]) or (0,)


def check_update():
    if not UPDATE_URL.strip():
        return "unconfigured", "Update server not configured yet."
    try:
        req = urllib.request.Request(UPDATE_URL, headers={"User-Agent": APP + "/" + APP_VERSION})
        with urllib.request.urlopen(req, timeout=8) as r:
            m = json.loads(r.read(65536).decode("utf-8"))
        ver, url = str(m["version"]), str(m.get("url", ""))
    except Exception as e:
        return "error", "Could not check for updates (%s)." % (getattr(e, "reason", None) or e)
    if vtuple(ver) > vtuple(APP_VERSION):
        return "newer", {"version": ver, "url": url, "notes": str(m.get("notes", "")),
                         "full_url": str(m.get("full_url", "")),
                         "installer_url": str(m.get("installer_url", ""))}
    return "latest", "You have the latest version (%s)." % APP_VERSION


def strip_ansi(s):
    return ANSI_RE.sub("", s)


def rrect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class Card(tk.Canvas):
    def __init__(self, master, title="", height=None, **kw):
        super().__init__(master, bg=BG, highlightthickness=0, height=height or 100, **kw)
        self.title = title
        self.body = tk.Frame(self, bg=CARD)
        self.win = self.create_window(18, 44 if title else 16, window=self.body, anchor="nw")
        self.bind("<Configure>", self._draw)

    def _draw(self, e=None):
        self.delete("bg"); w, h = self.winfo_width(), self.winfo_height()
        rrect(self, 2, 2, w-2, h-2, 18, fill=CARD, outline=BORDER, width=1, tags="bg")
        if self.title:
            self.create_text(18, 22, text=self.title, anchor="w", fill=MUT, font=(FONT, 10, "bold"), tags="bg")
        self.tag_lower("bg"); self.itemconfigure(self.win, width=max(10, w-36))


class PillButton(tk.Canvas):
    def __init__(self, master, text, cmd, w=160, h=34, fill=ACCENT, fg="#1a1000", bg=CARD):
        super().__init__(master, width=w, height=h, bg=bg, highlightthickness=0, cursor="hand2")
        self.cmd, self.fill, self.text, self.fg = cmd, fill, text, fg
        self.bind("<Button-1>", lambda e: cmd()); self.bind("<Enter>", lambda e: self.draw(True)); self.bind("<Leave>", lambda e: self.draw())
        self.draw()

    def draw(self, hover=False):
        self.delete("all"); w, h = int(self["width"]), int(self["height"])
        f = self.fill if not hover else ("#f0c35a" if self.fill == ACCENT else "#3a3a3d")
        rrect(self, 1, 1, w-1, h-1, h//2, fill=f, outline=BORDER)
        self.create_text(w//2, h//2, text=self.text, fill=self.fg, font=(FONT, 10, "bold"))


class NoticeBox(tk.Canvas):
    def __init__(self, master, text, bg, w=160, h=28, size=8):
        super().__init__(master, width=w, height=h, bg=bg, highlightthickness=0)
        rrect(self, 1, 1, w-1, h-1, 9, fill="#1c1c1e", outline="#3a3a3d", width=1)
        self.create_text(w//2, h//2, text=text, fill="#c7c7cc", font=(FONT, size))


# -------------------- shells --------------------
class PtyShell:
    """ConPTY-backed PowerShell via pywinpty. Supports interactive tools (grok, etc.)."""
    def __init__(self, on_out, on_done, on_err, on_raw=None):
        self.on_out, self.on_done, self.on_err = on_out, on_done, on_err
        self.on_raw = on_raw
        self.pty = None; self.alive = False; self.mode = "pty"
        self._acc = ""; self._lock = threading.Lock()

    def start(self):
        if not HAS_WINPTY:
            return False
        apps = [
            (os.environ.get("SystemRoot", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe",
             "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass"),
            ("pwsh.exe", "pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass"),
        ]
        if is_wine():
            apps = [(r"C:\windows\system32\cmd.exe", "cmd.exe /Q")] + apps
        last = None
        for app, cmdline in apps:
            try:
                self.pty = winpty.PTY(120, 40)
                ok = self.pty.spawn(app, cmdline)
                if not ok:
                    raise RuntimeError("spawn returned False")
                self.alive = True
                threading.Thread(target=self._reader, daemon=True).start()
                label = "ConPTY PowerShell" if "powershell" in app.lower() or "pwsh" in app.lower() else "ConPTY cmd (Wine)"
                self.on_out("Ready (%s). Interactive tools (e.g. grok) run here.\n" % label)
                return True
            except Exception as e:
                last = e
                self.pty = None
        self.on_err("ConPTY failed: %s" % last)
        return False

    def _reader(self):
        try:
            while self.pty and self.alive:
                try:
                    data = self.pty.read(blocking=False)
                except Exception:
                    data = None
                if not data:
                    if not self.pty.isalive():
                        break
                    time.sleep(0.02)
                    continue
                if self.on_raw:
                    self.on_raw(data)
                clean = strip_ansi(data).replace("\r\n", "\n").replace("\r", "\n")
                if clean:
                    self.on_out(clean)
                with self._lock:
                    self._acc = (self._acc + clean)[-4000:]
                    if MARKER in self._acc:
                        # optional marker support if a wrapper injected it
                        before, _, rest = self._acc.partition(MARKER)
                        code = rest.strip().split()[0] if rest.strip() else "0"
                        self._acc = ""
                        self.on_done(code)
                    elif PS_PROMPT_RE.search(self._acc):
                        self._acc = ""
                        self.on_done("0")
        except Exception as e:
            self.on_err(str(e))
        finally:
            self.alive = False
            self.on_done("shell-exit")

    def write(self, s):
        if not self.pty or not self.alive: return False
        try:
            self.pty.write(s)
            return True
        except Exception as e:
            self.on_err(str(e)); return False

    def run(self, cmd):
        # Send a full line; caller enables key capture for interactive tools
        return self.write(cmd + "\r\n")

    def interrupt(self):
        return self.write("\x03")

    def stop(self):
        """Hard restart the PTY (last resort)."""
        try:
            if self.pty and self.pty.pid:
                subprocess.run(["taskkill", "/PID", str(self.pty.pid), "/T", "/F"],
                               capture_output=True, creationflags=NOWIN if os.name == "nt" else 0)
        except Exception:
            pass
        self.alive = False; self.pty = None
        return self.start()

    def close(self):
        try:
            if self.pty:
                self.write("exit\r\n"); time.sleep(0.2)
                if self.pty.pid:
                    subprocess.run(["taskkill", "/PID", str(self.pty.pid), "/T", "/F"],
                                   capture_output=True, creationflags=NOWIN if os.name == "nt" else 0)
        except Exception:
            pass
        self.alive = False; self.pty = None

    @property
    def busy(self):
        return False  # ConPTY is always live; UI tracks interactive capture


class PipeShell:
    """Fallback: pipes to powershell/cmd (no real interactive TUI)."""
    def __init__(self, on_out, on_done, on_err, on_raw=None):
        self.on_out, self.on_done, self.on_err = on_out, on_done, on_err
        self.proc = None; self.busy = False; self.mode = "pipe"
        self._lock = threading.Lock()

    def start(self):
        si = None; flags = 0
        if os.name == "nt":
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            flags = NOWIN
        cmds = []
        if not is_wine():
            cmds.append((["powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"], "ps"))
            cmds.append((["pwsh", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"], "ps"))
        cmds.append((["cmd", "/Q", "/K", "prompt $G$S"], "cmd"))
        last = None
        for cmd, mode in cmds:
            try:
                self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                             errors="replace", bufsize=1, startupinfo=si, creationflags=flags)
                self.mode = mode
                threading.Thread(target=self._reader, daemon=True).start()
                if mode == "ps":
                    self._write("$ProgressPreference='SilentlyContinue'\n")
                self.on_out("Ready (pipes %s — interactive TUIs may hang; ConPTY unavailable).\n" % mode)
                return True
            except Exception as e:
                last = e
        self.on_err("Could not start a shell: %s" % last)
        return False

    def _write(self, s):
        if not self.proc or not self.proc.stdin: return
        try: self.proc.stdin.write(s); self.proc.stdin.flush()
        except Exception as e: self.on_err(str(e))

    def write(self, s):
        self._write(s); return True

    def _reader(self):
        try:
            while self.proc and self.proc.stdout:
                line = self.proc.stdout.readline()
                if line == "": break
                clean = strip_ansi(line)
                with self._lock:
                    if MARKER in clean:
                        before, _, rest = clean.partition(MARKER)
                        if before: self.on_out(before if before.endswith("\n") else before + "\n")
                        code = rest.strip().split()[0] if rest.strip() else "0"
                        self.busy = False; self.on_done(code)
                    else:
                        self.on_out(clean)
        except Exception as e:
            self.on_err(str(e))
        finally:
            self.busy = False

    def run(self, cmd):
        if not self.proc: return False
        if self.busy: return False
        self.busy = True
        if self.mode == "ps":
            payload = ("%s; Write-Host ('%s' + $(if ($null -ne $LASTEXITCODE) {$LASTEXITCODE} elseif ($?) {0} else {1}))\r\n" % (cmd, MARKER))
        else:
            payload = ("%s & echo %s%%ERRORLEVEL%%\r\n" % (cmd, MARKER))
        self._write(payload)
        return True

    def interrupt(self):
        return False

    def stop(self):
        if not self.proc: return False
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                               capture_output=True, creationflags=NOWIN)
            else:
                self.proc.terminate()
        except Exception:
            try: self.proc.kill()
            except Exception: pass
        self.busy = False; self.proc = None
        return self.start()

    def close(self):
        if self.proc:
            try: self._write("exit\n"); self.proc.terminate()
            except Exception: pass
            self.proc = None


def make_shell(on_out, on_done, on_err, on_raw=None):
    if HAS_WINPTY:
        sh = PtyShell(on_out, on_done, on_err, on_raw)
        if sh.start():
            return sh
    sh = PipeShell(on_out, on_done, on_err, on_raw)
    sh.start()
    return sh


# -------------------- UI --------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        adm = "  [Administrator]" if is_admin() else ""
        self.title(APP + adm)
        try: self.iconbitmap(default=res_path("logo.ico"))
        except Exception: pass
        try: self._icon = tk.PhotoImage(file=res_path("logo256.png")); self.iconphoto(True, self._icon)
        except Exception: pass
        self.geometry("980x640"); self.minsize(760, 520); self.configure(bg=BG)
        self.q = queue.Queue(); self.hist = []; self.hix = -1
        self.capturing = False  # keystrokes → PTY
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        side = tk.Frame(self, bg=SIDE, width=200); side.pack(side="left", fill="y"); side.pack_propagate(False)
        logo = tk.Canvas(side, width=200, height=90, bg=SIDE, highlightthickness=0); logo.pack()
        try:
            self._logo = tk.PhotoImage(file=res_path("logo256.png")).subsample(7, 7)
            logo.create_image(36, 45, image=self._logo)
        except Exception:
            logo.create_oval(18, 27, 54, 63, fill=ACCENT, outline="")
            logo.create_text(36, 45, text="EX", fill="white", font=(FONT, 10, "bold"))
        logo.create_text(62, 36, text="EX SUDO", anchor="w", fill=TXT, font=(FONT, 13, "bold"))
        logo.create_text(62, 54, text="TERMINAL", anchor="w", fill=ACCENT, font=(FONT, 9, "bold"))

        self.navs = {}; self.pages = {}
        main = tk.Frame(self, bg=BG); main.pack(side="left", fill="both", expand=True)
        self.content = tk.Frame(main, bg=BG); self.content.pack(fill="both", expand=True, padx=16, pady=16)
        for name, icon in (("Terminal", "⌘"), ("About", "ⓘ")):
            l = tk.Label(side, text=f"  {icon}   {name}", anchor="w", bg=SIDE, fg=MUT, font=(FONT, 11),
                         cursor="hand2", padx=14, pady=10)
            l.pack(fill="x", padx=12, pady=2); l.bind("<Button-1>", lambda e, n=name: self.show(n)); self.navs[name] = l
            self.pages[name] = tk.Frame(self.content, bg=BG)
        tk.Frame(side, bg=BORDER, height=1).pack(fill="x", padx=24, pady=8)
        up = tk.Label(side, text="  ⟳   Check for updates", anchor="w", bg=SIDE, fg=MUT, font=(FONT, 11),
                      cursor="hand2", padx=14, pady=10)
        up.pack(fill="x", padx=12, pady=2); up.bind("<Button-1>", lambda e: self.update_click())
        up.bind("<Enter>", lambda e: up.configure(bg=CARD2, fg=TXT)); up.bind("<Leave>", lambda e: up.configure(bg=SIDE, fg=MUT))
        NoticeBox(side, COPYRIGHT, SIDE, w=160, h=28).pack(side="bottom", pady=(4, 14))
        tk.Label(side, text="ConPTY PowerShell · interactive\n· grok runs in this window",
                 bg=SIDE, fg=MUT, font=(FONT, 8), justify="left").pack(side="bottom", padx=20, pady=(4, 2))

        self.build_term(); self.build_about(); self.show("Terminal")
        self.shell = None
        self.after(80, self._boot_shell); self.after(50, self.pump)
        self.bind_all("<Key>", self.on_key, add="+")

    def _boot_shell(self):
        self.shell = make_shell(lambda t: self.q.put(("out", t)),
                                lambda c: self.q.put(("done", c)),
                                lambda e: self.q.put(("err", e)))

    def show(self, name):
        for n, p in self.pages.items():
            p.pack_forget(); self.navs[n].configure(bg=SIDE, fg=MUT)
        self.pages[name].pack(fill="both", expand=True); self.navs[name].configure(bg=CARD2, fg=TXT)

    def build_term(self):
        p = self.pages["Terminal"]
        bar = tk.Frame(p, bg=BG); bar.pack(fill="x", pady=(0, 8))
        if not is_admin():
            PillButton(bar, "Run as admin", relaunch_admin, w=130, h=32, fill=CARD2, fg=TXT, bg=BG).pack(side="left", padx=(0, 8))
        else:
            tk.Label(bar, text="Administrator", bg=BG, fg=ACCENT, font=(FONT, 10, "bold")).pack(side="left", padx=(0, 8))
        PillButton(bar, "Install Grok CLI", self.install_grok, w=150, h=32, fill=ACCENT, fg="#1a1000", bg=BG).pack(side="left", padx=(0, 8))
        PillButton(bar, "Clear", self.clear, w=90, h=32, fill=CARD2, fg=TXT, bg=BG).pack(side="left", padx=(0, 8))
        PillButton(bar, "End interactive", self.end_capture, w=130, h=32, fill=CARD2, fg=TXT, bg=BG).pack(side="left")
        self.status = tk.StringVar(value="Idle")
        tk.Label(bar, textvariable=self.status, bg=BG, fg=MUT, font=(FONT, 9)).pack(side="right")

        outf = tk.Frame(p, bg=BORDER); outf.pack(fill="both", expand=True)
        self.out = tk.Text(outf, bg="#0d0d0f", fg=TXT, insertbackground=TXT, relief="flat",
                           font=(MONO, 11), wrap="word", state="normal", padx=10, pady=10,
                           highlightthickness=0, takefocus=1)
        self.out.pack(fill="both", expand=True, padx=1, pady=1)
        self.out.tag_configure("cmd", foreground=ACCENT)
        self.out.tag_configure("err", foreground=ERR)
        self.out.tag_configure("meta", foreground=MUT)
        self.out.bind("<Key>", self.on_term_key)
        self.out.bind("<Button-1>", lambda e: self.out.focus_set())
        # Keep content read-only-ish: block edits but allow us to insert via append
        self.out.bind("<<Modified>>", self._guard_out)
        self._out_len = "1.0"

        row = tk.Frame(p, bg=CARD); row.pack(fill="x", pady=(8, 0), ipady=4)
        tk.Label(row, text="PS>", bg=CARD, fg=ACCENT, font=(MONO, 11, "bold")).pack(side="left", padx=(10, 6))
        self.inp = tk.Entry(row, bg=CARD, fg=TXT, insertbackground=TXT, relief="flat", font=(MONO, 11))
        self.inp.pack(side="left", fill="x", expand=True, ipady=6)
        self.inp.bind("<Return>", self.submit); self.inp.bind("<Up>", self.hist_up); self.inp.bind("<Down>", self.hist_down)
        PillButton(row, "Send", lambda: self.submit(), w=80, h=32, fill=ACCENT, fg="#1a1000", bg=CARD).pack(side="left", padx=(8, 8))
        self.inp.focus_set()

    def _guard_out(self, e=None):
        # Prevent user typing from mutating Text; PTY keys are handled separately
        try:
            if self.out.edit_modified():
                self.out.edit_modified(False)
        except Exception:
            pass

    def build_about(self):
        p = self.pages["About"]
        c = Card(p, "ABOUT & UPDATES", height=260); c.pack(fill="x")
        tk.Label(c.body, text="%s  version %s" % (APP, APP_VERSION), bg=CARD, fg=TXT, font=(FONT, 12, "bold")).pack(anchor="w")
        tk.Label(c.body, text="Uses Windows ConPTY (pywinpty) so interactive tools like grok run\n"
                 "inside this window. Type at PS>, then while a command is Running your\n"
                 "keystrokes go to the terminal. Ctrl+C / Esc interrupt.",
                 bg=CARD, fg=MUT, font=(FONT, 9), justify="left").pack(anchor="w", pady=6)
        NoticeBox(c.body, COPYRIGHT, CARD, w=170, h=30, size=9).pack(anchor="w", pady=(4, 8))
        row = tk.Frame(c.body, bg=CARD); row.pack(fill="x")
        PillButton(row, "Check for updates", self.update_click, w=180, fill=CARD2, fg=TXT).pack(side="left")
        self.upd = tk.StringVar(value=""); tk.Label(row, textvariable=self.upd, bg=CARD, fg=MUT, font=(FONT, 9)).pack(side="left", padx=12)

    def append(self, text, tag=None):
        self.out.configure(state="normal")
        self.out.insert("end", text, tag)
        self.out.see("end")
        self._out_len = self.out.index("end-1c")

    def clear(self):
        self.out.delete("1.0", "end"); self._out_len = "1.0"

    def set_capturing(self, on):
        self.capturing = on
        if on:
            self.status.set("Interactive — keys go to terminal (Ctrl+C / Esc)")
            self.inp.configure(state="disabled")
            self.out.focus_set()
        else:
            self.status.set("Idle")
            self.inp.configure(state="normal")
            self.inp.focus_set()

    def end_capture(self):
        if self.capturing:
            self.set_capturing(False)
            self.append("(interactive capture ended)\n", "meta")

    def pump(self):
        while not self.q.empty():
            kind, v = self.q.get()
            if kind == "out": self.append(v)
            elif kind == "err": self.append(v + "\n", "err"); self.status.set("Error")
            elif kind == "done":
                if v == "shell-exit":
                    self.append("\n(shell exited — restarting)\n", "meta")
                    self.set_capturing(False)
                    self.after(200, self._boot_shell)
                else:
                    # Prompt seen / marker — leave interactive if it was a short command;
                    # keep capturing if user is in a long interactive session? Heuristic: end capture.
                    if self.capturing:
                        self.set_capturing(False)
                    else:
                        self.status.set("Idle · exit %s" % v)
            elif kind == "upd": self.update_result(*v)
        self.after(40, self.pump)

    def submit(self, e=None):
        cmd = self.inp.get().strip()
        if not cmd or not self.shell: return "break"
        if self.capturing:
            # In interactive mode Enter from PS> shouldn't steal; ignore
            return "break"
        self.hist.append(cmd); self.hix = len(self.hist)
        self.inp.delete(0, "end")
        self.append("PS> %s\n" % cmd, "cmd")
        # Enable key capture immediately so interactive tools work
        self.set_capturing(True)
        if not self.shell.run(cmd):
            self.set_capturing(False)
            self.append("Shell is not ready.\n", "err")
        return "break"

    def hist_up(self, e=None):
        if self.capturing or not self.hist: return
        self.hix = max(0, self.hix - 1); self.inp.delete(0, "end"); self.inp.insert(0, self.hist[self.hix]); return "break"

    def hist_down(self, e=None):
        if self.capturing or not self.hist: return
        self.hix = min(len(self.hist), self.hix + 1)
        self.inp.delete(0, "end")
        if self.hix < len(self.hist): self.inp.insert(0, self.hist[self.hix])
        return "break"

    def _key_to_pty(self, event):
        """Map a Tk key event to PTY bytes. Returns True if handled."""
        if not self.shell: return False
        ks, ch = event.keysym, event.char
        ctrl = bool(event.state & 0x4)
        if ks in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R"):
            return True
        if ctrl and ks.lower() == "c":
            self.append("^C\n", "err")
            self.shell.interrupt()
            return True
        if ks == "Escape":
            self.shell.write("\x1b")
            self.set_capturing(False)
            self.append("(Esc — left interactive mode; Ctrl+C sent interrupt earlier if used)\n", "meta")
            return True
        mapping = {
            "Return": "\r", "KP_Enter": "\r", "BackSpace": "\x7f", "Delete": "\x1b[3~",
            "Tab": "\t", "Up": "\x1b[A", "Down": "\x1b[B", "Right": "\x1b[C", "Left": "\x1b[D",
            "Home": "\x1b[H", "End": "\x1b[F", "Prior": "\x1b[5~", "Next": "\x1b[6~",
        }
        if ks in mapping:
            self.shell.write(mapping[ks]); return True
        if ctrl and ch and ch.isalpha():
            self.shell.write(chr(ord(ch.lower()) - ord("a") + 1)); return True
        if ch and ch.isprintable():
            self.shell.write(ch); return True
        return False

    def on_term_key(self, event):
        if self.capturing:
            self._key_to_pty(event)
            return "break"  # never mutate the Text widget
        # Idle: ignore typing in output (focus PS> instead)
        if event.keysym not in ("Control_L", "Control_R", "Shift_L", "Shift_R"):
            self.inp.focus_set()
        return "break"

    def on_key(self, event):
        # Global: when capturing, route keys even if focus left the Text
        if not self.capturing:
            return
        w = self.focus_get()
        if w is self.inp:
            return  # shouldn't happen while disabled
        # Avoid double-handling when Text already got it
        if w is self.out:
            return
        if self._key_to_pty(event):
            return "break"

    def install_grok(self):
        if self.capturing:
            messagebox.showinfo(APP, "Finish or Esc the current interactive session first."); return
        if not messagebox.askyesno(APP, "Run this PowerShell command?\n\n%s\n\nIt downloads and runs x.ai's install script." % GROK_CLI):
            return
        self.inp.delete(0, "end"); self.inp.insert(0, GROK_CLI); self.submit()

    def update_click(self):
        self.upd.set("Checking…")
        def job():
            st, d = check_update(); self.q.put(("upd", (st, d)))
        threading.Thread(target=job, daemon=True).start()

    def update_result(self, st, d):
        if st != "newer":
            self.upd.set(d); (messagebox.showinfo if st == "latest" else messagebox.showwarning)(APP, d); return
        self.upd.set("Version %s available" % d["version"])
        msg = "Version %s is available (you have %s).\n\n%s" % (d["version"], APP_VERSION, d["notes"] or "")
        link = d.get("installer_url") or d["url"]
        msg += "\n\nDownload and run the installer (close this app first)."
        if link.lower().startswith(("https://", "http://")):
            if messagebox.askyesno(APP, msg + "\n\nOpen the download in your browser?"):
                import webbrowser; webbrowser.open(link)
        else:
            messagebox.showinfo(APP, msg)

    def on_close(self):
        try:
            if self.shell: self.shell.close()
        except Exception: pass
        self.destroy()


if __name__ == "__main__":
    if single_instance():
        App().mainloop()
