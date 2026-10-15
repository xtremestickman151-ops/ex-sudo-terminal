"""EX SUDO TERMINAL - persistent PowerShell GUI for Windows. ©2026 EX Inc."""
import ctypes, json, os, queue, re, subprocess, sys, threading, time, urllib.request
import tkinter as tk
from tkinter import messagebox

APP = "EX SUDO TERMINAL"
APP_VERSION = "1.0.0"
COPYRIGHT = "\u00a92026 EX Inc."
UPDATE_URL = "https://raw.githubusercontent.com/xtremestickman151-ops/ex-sudo-terminal/main/latest.json"
GROK_CLI = "irm https://x.ai/cli/install.ps1 | iex"
MARKER = "__EXSUDO_DONE__"
NOWIN = 0x08000000
BG, SIDE, CARD, CARD2, BORDER = "#000000", "#0a0a0a", "#1c1c1e", "#2a2a2d", "#3a3a3d"
TXT, MUT, ACCENT, ERR = "#f2f2f4", "#9a9aa0", "#e5a524", "#ff453a"
FONT, MONO = "Segoe UI", "Consolas"
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\x1b.")
_MUTEX = None


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


class Shell:
    """Persistent PowerShell (or cmd under Wine). Commands end with MARKER."""
    def __init__(self, on_out, on_done, on_err):
        self.on_out, self.on_done, self.on_err = on_out, on_done, on_err
        self.proc = None; self.busy = False; self.mode = "ps"
        self._buf = ""; self._lock = threading.Lock()

    def start(self):
        si = None; flags = 0
        if os.name == "nt":
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            flags = NOWIN
        cmds = []
        if not is_wine():
            cmds.append((["powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"], "ps"))
            cmds.append((["pwsh", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"], "ps"))
        cmds.append((["cmd", "/Q", "/K", "prompt $G$S"], "cmd"))  # Wine smoke / last resort
        last = None
        for cmd, mode in cmds:
            try:
                self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                             errors="replace", bufsize=1, startupinfo=si, creationflags=flags)
                self.mode = mode
                threading.Thread(target=self._reader, daemon=True).start()
                if mode == "ps":
                    self._write("$ProgressPreference='SilentlyContinue'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new()\n")
                self.on_out("Ready (%s).\n" % ("PowerShell" if mode == "ps" else "cmd — Wine fallback"))
                return True
            except Exception as e:
                last = e
        self.on_err("Could not start a shell: %s" % last)
        return False

    def _write(self, s):
        if not self.proc or not self.proc.stdin: return
        try: self.proc.stdin.write(s); self.proc.stdin.flush()
        except Exception as e: self.on_err(str(e))

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
            # Run command; always emit marker with exit code (works for native cmds & PS cmdlets)
            payload = ("%s; Write-Host ('%s' + $(if ($null -ne $LASTEXITCODE) {$LASTEXITCODE} elseif ($?) {0} else {1}))\r\n" % (cmd, MARKER))
        else:
            # Single line so cmd expands %%ERRORLEVEL%% after the command
            payload = ("%s & echo %s%%ERRORLEVEL%%\r\n" % (cmd, MARKER))
        self._write(payload)
        return True

    def stop(self):
        if not self.proc: return
        try:
            if os.name == "nt":
                # Kill the whole tree; PowerShell child processes too
                subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                               capture_output=True, creationflags=NOWIN)
            else:
                self.proc.terminate()
        except Exception:
            try: self.proc.kill()
            except Exception: pass
        self.busy = False
        self.proc = None
        self.start()

    def close(self):
        if self.proc:
            try: self._write("exit\n"); self.proc.terminate()
            except Exception: pass
            self.proc = None


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
        self.q = queue.Queue(); self.hist = []; self.hix = -1; self.busy = False
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
        tk.Label(side, text="PowerShell GUI · persistent session\n· run as admin when you need it",
                 bg=SIDE, fg=MUT, font=(FONT, 8), justify="left").pack(side="bottom", padx=20, pady=(4, 2))

        self.build_term(); self.build_about(); self.show("Terminal")
        self.shell = Shell(lambda t: self.q.put(("out", t)), lambda c: self.q.put(("done", c)),
                           lambda e: self.q.put(("err", e)))
        self.after(100, self.shell.start); self.after(200, self.pump)
        self.bind_all("<Control-c>", self.ctrl_c)

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
        PillButton(bar, "Clear", self.clear, w=90, h=32, fill=CARD2, fg=TXT, bg=BG).pack(side="left")
        self.status = tk.StringVar(value="Idle")
        tk.Label(bar, textvariable=self.status, bg=BG, fg=MUT, font=(FONT, 9)).pack(side="right")

        outf = tk.Frame(p, bg=BORDER); outf.pack(fill="both", expand=True)
        self.out = tk.Text(outf, bg="#0d0d0f", fg=TXT, insertbackground=TXT, relief="flat",
                           font=(MONO, 11), wrap="word", state="disabled", padx=10, pady=10,
                           highlightthickness=0)
        self.out.pack(fill="both", expand=True, padx=1, pady=1)
        self.out.tag_configure("cmd", foreground=ACCENT)
        self.out.tag_configure("err", foreground=ERR)
        self.out.tag_configure("meta", foreground=MUT)

        row = tk.Frame(p, bg=CARD); row.pack(fill="x", pady=(8, 0), ipady=4)
        tk.Label(row, text="PS>", bg=CARD, fg=ACCENT, font=(MONO, 11, "bold")).pack(side="left", padx=(10, 6))
        self.inp = tk.Entry(row, bg=CARD, fg=TXT, insertbackground=TXT, relief="flat", font=(MONO, 11))
        self.inp.pack(side="left", fill="x", expand=True, ipady=6)
        self.inp.bind("<Return>", self.submit); self.inp.bind("<Up>", self.hist_up); self.inp.bind("<Down>", self.hist_down)
        self.inp.focus_set()

    def build_about(self):
        p = self.pages["About"]
        c = Card(p, "ABOUT & UPDATES", height=220); c.pack(fill="x")
        tk.Label(c.body, text="%s  version %s" % (APP, APP_VERSION), bg=CARD, fg=TXT, font=(FONT, 12, "bold")).pack(anchor="w")
        tk.Label(c.body, text="Runs PowerShell in a persistent session so cd and variables stick.\n"
                 "Does not elevate every command — use Run as admin when you need elevated rights.",
                 bg=CARD, fg=MUT, font=(FONT, 9), justify="left").pack(anchor="w", pady=6)
        NoticeBox(c.body, COPYRIGHT, CARD, w=170, h=30, size=9).pack(anchor="w", pady=(4, 8))
        row = tk.Frame(c.body, bg=CARD); row.pack(fill="x")
        PillButton(row, "Check for updates", self.update_click, w=180, fill=CARD2, fg=TXT).pack(side="left")
        self.upd = tk.StringVar(value=""); tk.Label(row, textvariable=self.upd, bg=CARD, fg=MUT, font=(FONT, 9)).pack(side="left", padx=12)

    def append(self, text, tag=None):
        self.out.configure(state="normal")
        self.out.insert("end", text, tag)
        self.out.see("end"); self.out.configure(state="disabled")

    def clear(self):
        self.out.configure(state="normal"); self.out.delete("1.0", "end"); self.out.configure(state="disabled")

    def pump(self):
        while not self.q.empty():
            kind, v = self.q.get()
            if kind == "out": self.append(v)
            elif kind == "err": self.append(v + "\n", "err"); self.status.set("Error")
            elif kind == "done":
                self.busy = False; self.status.set("Idle · exit %s" % v); self.inp.configure(state="normal"); self.inp.focus_set()
            elif kind == "upd": self.update_result(*v)
        self.after(50, self.pump)

    def submit(self, e=None):
        cmd = self.inp.get().strip()
        if not cmd: return "break"
        if self.busy:
            self.append("(busy — Ctrl+C to stop)\n", "meta"); return "break"
        self.hist.append(cmd); self.hix = len(self.hist)
        self.inp.delete(0, "end")
        self.append("PS> %s\n" % cmd, "cmd")
        self.busy = True; self.status.set("Running…"); self.inp.configure(state="disabled")
        if not self.shell.run(cmd):
            self.busy = False; self.status.set("Shell not ready"); self.inp.configure(state="normal")
            self.append("Shell is not ready.\n", "err")
        return "break"

    def hist_up(self, e=None):
        if not self.hist: return
        self.hix = max(0, self.hix - 1); self.inp.delete(0, "end"); self.inp.insert(0, self.hist[self.hix]); return "break"

    def hist_down(self, e=None):
        if not self.hist: return
        self.hix = min(len(self.hist), self.hix + 1)
        self.inp.delete(0, "end")
        if self.hix < len(self.hist): self.inp.insert(0, self.hist[self.hix])
        return "break"

    def ctrl_c(self, e=None):
        if self.busy:
            self.append("^C\n", "err"); self.status.set("Stopping…")
            threading.Thread(target=self.shell.stop, daemon=True).start()
        return "break"

    def install_grok(self):
        if self.busy:
            messagebox.showinfo(APP, "Wait for the current command to finish, or press Ctrl+C."); return
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
        try: self.shell.close()
        except Exception: pass
        self.destroy()


if __name__ == "__main__":
    if single_instance():
        App().mainloop()
