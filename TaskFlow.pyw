"""TaskFlow - a full-featured to-do app for Windows (Python 3.8+, no extra installs).
Double-click TaskFlow.pyw to run. Data is saved to %APPDATA%\\TaskFlow\\data.json
"""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog, simpledialog
import json, os, uuid, copy, calendar, math
import datetime as dt

APP = "TaskFlow"
DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP)
FILE = os.path.join(DIR, "data.json")
FONT = "Segoe UI"

THEMES = {
    "light": dict(bg="#f3eae0", card="#fcf8f3", card2="#f4ece3", hover="#efe3d6", line="#e6d9cb", shadow="#e0d3c5",
                  fg="#3b322d", mute="#8f8176", accent="#ec8f5e", teal="#6fb1b8", accent_fg="#ffffff",
                  danger="#d9534f"),
    "dark": dict(bg="#1c1816", card="#272221", card2="#312b29", hover="#3a3330", line="#3b3431", shadow="#141110",
                 fg="#f3e9df", mute="#a39588", accent="#f0a273", teal="#7cc0c6", accent_fg="#2a1d15",
                 danger="#ff7b6b"),
}
PRI = ["None", "Low", "Medium", "High"]
PCOL = ["#b9aca0", "#6fb1b8", "#f0b45d", "#e5664f"]
REPEAT = ["Never", "Daily", "Weekly", "Monthly"]
FILTERS = [("All tasks", "all"), ("Today", "today"), ("Upcoming", "upcoming"),
           ("Overdue", "overdue"), ("Important", "important"), ("Completed", "done")]


def parse(s):
    if not s:
        return None
    for f in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def fmt_due(s):
    d = parse(s)
    if not d:
        return ""
    diff = (d.date() - dt.date.today()).days
    lab = {0: "Today", 1: "Tomorrow", -1: "Yesterday"}.get(diff, d.strftime("%a %d %b"))
    return lab + (d.strftime(", %H:%M") if " " in s else "")


def is_overdue(t):
    d = parse(t["due"])
    if t["done"] or not d:
        return False
    return d < dt.datetime.now() if " " in t["due"] else d.date() < dt.date.today()


def next_due(s, rep):
    d = parse(s)
    if rep == "Daily":
        d += dt.timedelta(days=1)
    elif rep == "Weekly":
        d += dt.timedelta(weeks=1)
    else:
        m = d.month % 12 + 1
        y = d.year + (d.month == 12)
        d = d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))
    return d.strftime("%Y-%m-%d %H:%M" if " " in s else "%Y-%m-%d")


TABS = ["Dashboard", "Tasks", "Analytics", "Settings"]


def mix(a, b, t):
    A = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    B = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(A, B))


def rrect(cv, x1, y1, x2, y2, r, **kw):
    p = [x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r,
         x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
         x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1]
    return cv.create_polygon(p, smooth=True, **kw)


class Card(tk.Canvas):
    """Rounded card with a soft drop shadow; put widgets in .body"""

    def __init__(self, parent, c, pad=18, r=16, fill=None, shadow=True):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, width=10, height=10)
        self.c, self.pad, self.r, self.fill, self.sh = c, pad, r, fill or c["card"], shadow
        self.body = tk.Frame(self, bg=self.fill)
        self.win = self.create_window(pad, pad, window=self.body, anchor="nw")
        self.bind("<Configure>", self.draw)
        self.body.bind("<Configure>", lambda e: self.configure(height=self.body.winfo_reqheight() + 2 * pad + 6))

    def draw(self, e=None):
        w, h = self.winfo_width(), self.winfo_height()
        self.delete("bg")
        if self.sh:
            rrect(self, 3, 5, w - 2, h - 1, self.r, fill=self.c["shadow"], outline="", tags="bg")
        rrect(self, 1, 1, w - 4, h - 5 if self.sh else h - 1, self.r, fill=self.fill,
              outline=self.c["line"], tags="bg")
        self.tag_lower("bg")
        self.itemconfig(self.win, width=max(w - 2 * self.pad - 4, 1), height=max(h - 2 * self.pad - 6, 1))




class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP)
        self.geometry("1200x800")
        self.minsize(1000, 660)
        self.data = {"tasks": [], "cats": ["Personal", "Work", "Shopping"], "theme": "light",
                     "name": os.environ.get("USERNAME", "there").title(), "log": []}
        self.load()
        self.view, self.cat, self.undo, self.notified, self.page = "all", None, [], set(), "Dashboard"
        self.search = tk.StringVar()
        self.sort = tk.StringVar(value="Created")
        self.search.trace_add("write", self.on_search)
        self.f_title = tkfont.Font(family=FONT, size=11)
        self.f_done = tkfont.Font(family=FONT, size=11, overstrike=True)
        self.bind("<Control-n>", lambda e: (self.goto("Tasks"), self.quick.focus_set()))
        self.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.bind("<Control-z>", lambda e: self.do_undo())
        self.bind("<Control-d>", lambda e: self.toggle_theme())
        self.bind_all("<MouseWheel>", self.wheel)
        self.protocol("WM_DELETE_WINDOW", lambda: (self.save(), self.destroy()))
        self.build()
        self.after(1000, self.check_reminders)

    # ---------- small widgets ----------
    def btn(self, parent, text, fn, ghost=False, h=34):
        c = self.c
        f = tkfont.Font(family=FONT, size=10, weight="bold")
        w = f.measure(text) + 34
        cv = tk.Canvas(parent, width=w, height=h, bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        rrect(cv, 1, 1, w - 1, h - 1, h // 2, fill=c["card"] if ghost else c["accent"],
              outline=c["line"] if ghost else c["accent"])
        cv.create_text(w / 2, h / 2, text=text, font=f, fill=c["fg"] if ghost else c["accent_fg"])
        cv.bind("<Button-1>", lambda e: fn())
        return cv

    def chip(self, parent, text, bg, fg):
        f = tkfont.Font(family=FONT, size=9, weight="bold")
        w = f.measure(text) + 20
        cv = tk.Canvas(parent, width=w, height=22, bg=parent.cget("bg"), highlightthickness=0)
        rrect(cv, 1, 1, w - 1, 21, 10, fill=bg, outline="")
        cv.create_text(w / 2, 11, text=text, font=f, fill=fg)
        return cv

    def check(self, parent, t, size=24):
        c, bg = self.c, parent.cget("bg")
        cv = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0, cursor="hand2")
        cv.create_oval(2, 2, size - 2, size - 2, outline=c["teal"] if t["done"] else c["mute"], width=2,
                       fill=c["teal"] if t["done"] else bg)
        if t["done"]:
            cv.create_text(size / 2, size / 2, text="\u2713", fill="#ffffff", font=(FONT, int(size * .42), "bold"))
        cv.bind("<Button-1>", lambda e: self.toggle(t))
        return cv

    def bar(self, cv, p, col):
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        rrect(cv, 0, 0, w, h, h / 2, fill=self.c["line"], outline="")
        if p > 0:
            rrect(cv, 0, 0, max(w * p, h), h, h / 2, fill=col, outline="")

    def heading(self, parent, text):
        tk.Label(parent, text=text, bg=parent.cget("bg"), fg=self.c["fg"], font=(FONT, 12, "bold")).pack(anchor="w")
        tk.Frame(parent, bg=self.c["line"], height=1).pack(fill="x", pady=(8, 10))

    def clear(self, f):
        for w in f.winfo_children():
            w.destroy()

    def lbl(self, parent, text, size=10, fg=None, bold=False, **kw):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg or self.c["fg"],
                        font=(FONT, size, "bold" if bold else "normal"), **kw)

    # ---------- shell ----------
    def build(self):
        for w in self.winfo_children():
            w.destroy()
        c = self.c = THEMES[self.data["theme"]]
        self.charts = []
        self.hint = "Add a task - try 'Pay rent tomorrow'"
        self.configure(bg=c["bg"])
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure("TCombobox", fieldbackground=c["card"], background=c["card"], foreground=c["fg"],
                     arrowcolor=c["mute"], bordercolor=c["line"], lightcolor=c["card"], darkcolor=c["card"],
                     padding=4)
        st.map("TCombobox", fieldbackground=[("readonly", c["card"])], foreground=[("readonly", c["fg"])],
               selectbackground=[("readonly", c["card"])], selectforeground=[("readonly", c["fg"])])
        self.option_add("*TCombobox*Listbox.background", c["card"])
        self.option_add("*TCombobox*Listbox.foreground", c["fg"])

        top = tk.Frame(self, bg=c["card"], height=66)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="\u25cf", bg=c["card"], fg=c["accent"], font=(FONT, 14)).pack(side="left", padx=(30, 6))
        tk.Label(top, text="TaskFlow", bg=c["card"], fg=c["fg"], font=(FONT, 15, "bold")).pack(side="left")
        av = tk.Canvas(top, width=40, height=40, bg=c["card"], highlightthickness=0, cursor="hand2")
        av.pack(side="right", padx=(8, 30))
        av.create_oval(2, 2, 38, 38, fill=c["teal"], outline="")
        av.create_text(20, 20, text=(self.data["name"] or "?")[0].upper(), font=(FONT, 13, "bold"), fill="#ffffff")
        av.bind("<Button-1>", lambda e: self.goto("Settings"))
        self.bellcv = tk.Canvas(top, width=32, height=34, bg=c["card"], highlightthickness=0, cursor="hand2")
        self.bellcv.pack(side="right", padx=6)
        self.bellcv.bind("<Button-1>", lambda e: (setattr(self, "view", "overdue"), setattr(self, "cat", None),
                                                  self.goto("Tasks"), self.render()))
        sb = tk.Frame(top, bg=c["bg"], highlightthickness=1, highlightbackground=c["line"])
        sb.pack(side="right", padx=14)
        mag = tk.Canvas(sb, width=24, height=24, bg=c["bg"], highlightthickness=0)
        mag.create_oval(5, 5, 15, 15, outline=c["mute"], width=2)
        mag.create_line(14, 14, 19, 19, fill=c["mute"], width=2)
        mag.pack(side="left", padx=(8, 0))
        self.search_entry = tk.Entry(sb, textvariable=self.search, bg=c["bg"], fg=c["fg"], relief="flat",
                                     insertbackground=c["fg"], font=(FONT, 10), width=20)
        self.search_entry.pack(side="left", padx=6, ipady=5)
        tabs = tk.Frame(top, bg=c["card"])
        tabs.place(relx=.5, rely=.5, anchor="center")
        self.tab = {}
        for name in TABS:
            f = tk.Frame(tabs, bg=c["card"], cursor="hand2")
            f.pack(side="left", padx=18)
            l = tk.Label(f, text=name, bg=c["card"], font=(FONT, 11), cursor="hand2")
            l.pack(pady=(19, 9))
            u = tk.Frame(f, height=3, bg=c["card"])
            u.pack(fill="x")
            for w in (f, l, u):
                w.bind("<Button-1>", lambda e, n=name: self.goto(n))
            self.tab[name] = (l, u)
        tk.Frame(self, bg=c["line"], height=1).pack(fill="x")

        box = tk.Frame(self, bg=c["bg"])
        box.pack(fill="both", expand=True)
        box.grid_rowconfigure(0, weight=1)
        box.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for n in TABS:
            f = tk.Frame(box, bg=c["bg"])
            f.grid(row=0, column=0, sticky="nsew")
            self.pages[n] = f
        self.snack = tk.Label(self, bg=c["fg"], fg=c["bg"], font=(FONT, 10, "bold"), padx=18, pady=9)
        self.make_dash()
        self.make_tasks()
        self.make_analytics()
        self.make_settings()
        self.goto(self.page)
        self.render()

    def goto(self, n):
        c = self.c
        self.page = n
        self.pages[n].tkraise()
        for k, (l, u) in self.tab.items():
            on = k == n
            l.config(fg=c["fg"] if on else c["mute"], font=(FONT, 11, "bold" if on else "normal"))
            u.config(bg=c["accent"] if on else c["card"])

    def on_search(self, *a):
        if self.page != "Tasks" and self.search.get():
            self.goto("Tasks")
        self.fill_tasks()

    def wheel(self, e):
        if self.page == "Tasks":
            self.cv.yview_scroll(int(-e.delta / 120) * 2, "units")

    def flash(self, msg):
        if getattr(self, "_fl", None):
            self.after_cancel(self._fl)
        self.snack.config(text=msg)
        self.snack.place(relx=.5, rely=1, y=-26, anchor="s")
        self.snack.lift()
        self._fl = self.after(2600, self.unflash)

    def unflash(self):
        try:
            self.snack.place_forget()
        except tk.TclError:
            pass

    def changed(self, msg=""):
        self.save()
        self.render()
        if msg:
            self.flash(msg)

    def render(self):
        self.fill_dash()
        self.fill_tasks()
        self.fill_analytics()
        self.fill_settings()
        self.fill_bell()
        for cv in self.charts:
            self.draw_chart(cv)

    def reset_quick(self):
        self.quick.delete(0, "end")
        if self.focus_get() is not self.quick:
            self.set_hint()

    def set_view(self, k):
        self.view = k
        self.render()

    def set_cat(self, ct):
        self.cat = ct if (self.cat != ct or self.page != "Tasks") else None
        self.goto("Tasks")
        self.render()

    def toggle(self, t):
        self.snap()
        now = dt.datetime.now().isoformat()
        log = self.data.setdefault("log", [])
        if not t["done"] and t["repeat"] != "Never" and parse(t["due"]):
            t["due"] = next_due(t["due"], t["repeat"])
            for s in t["subs"]:
                s["d"] = False
            self.notified.discard(t["id"])
            log.append(now)
            self.changed(f"Repeats {t['repeat'].lower()} - next due {fmt_due(t['due'])}")
        else:
            t["done"] = not t["done"]
            if t["done"]:
                log.append(now)
            elif log:
                log.pop()
            self.changed("Nice work - completed" if t["done"] else "Reopened")

    def set_name(self):
        self.data["name"] = self.name_e.get().strip() or "there"
        self.save()
        self.build()
        self.flash("Name saved")

    def set_theme(self, x):
        self.data["theme"] = x
        self.save()
        self.build()

    def fill_bell(self):
        c, b = self.c, self.bellcv
        b.delete("all")
        b.create_polygon([13, 5, 19, 11, 19, 18, 22, 22, 4, 22, 7, 18, 7, 11], smooth=True, fill=c["mute"], outline="")
        b.create_oval(10, 23, 16, 29, fill=c["mute"], outline="")
        n = sum(is_overdue(t) for t in self.tasks)
        if n:
            b.create_oval(15, 1, 29, 15, fill=c["accent"], outline="")
            b.create_text(22, 8, text=str(min(n, 9)), fill="#ffffff", font=(FONT, 7, "bold"))

    # ---------- chart ----------
    def cosine(self, pts, steps=14):
        out = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            for s in range(steps):
                t = s / steps
                m = (1 - math.cos(t * math.pi)) / 2
                out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * m))
        out.append(pts[-1])
        return out

    def chart_card(self, b, title, h):
        c = self.c
        hd = tk.Frame(b, bg=c["card"])
        hd.pack(fill="x")
        self.lbl(hd, title, 12, bold=True).pack(side="left")
        for txt, col in (("Last Week", c["accent"]), ("This Week", c["teal"])):
            self.lbl(hd, txt, 9, c["mute"]).pack(side="right", padx=(4, 0))
            self.lbl(hd, "\u25cf", 10, col).pack(side="right", padx=(12, 0))
        tk.Frame(b, bg=c["line"], height=1).pack(fill="x", pady=(8, 6))
        cv = tk.Canvas(b, bg=c["card"], highlightthickness=0, height=h)
        cv.pack(fill="both", expand=True)
        cv.bind("<Configure>", lambda e: self.draw_chart(cv))
        return cv

    def draw_chart(self, cv):
        c = self.c
        cv.delete("all")
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 80 or H < 60:
            return
        cnt = {}
        for s in self.data.get("log", []):
            cnt[s[:10]] = cnt.get(s[:10], 0) + 1
        today = dt.date.today()
        mon = today - dt.timedelta(days=today.weekday())
        day = lambda i: mon + dt.timedelta(days=i)
        this = [cnt.get(day(i).isoformat(), 0) if day(i) <= today else None for i in range(7)]
        last = [cnt.get(day(i - 7).isoformat(), 0) for i in range(7)]
        mx = max(3, max(v for v in this + last if v is not None))
        L, R, T, B = 30, 14, 10, 26
        X = lambda i: L + (W - L - R) * i / 6
        Y = lambda v: T + (H - T - B) * (1 - v / mx)
        for v in sorted({0, mx // 2, mx}):
            cv.create_line(L, Y(v), W - R, Y(v), fill=c["line"])
            cv.create_text(L - 8, Y(v), text=str(v), fill=c["mute"], font=(FONT, 8), anchor="e")
        for i, d in enumerate("MTWTFSS"):
            cv.create_text(X(i), H - 10, text=d, fill=c["mute"], font=(FONT, 9))
        series = []
        for vals, col in ((last, c["accent"]), (this, c["teal"])):
            pts = [(X(i), Y(v)) for i, v in enumerate(vals) if v is not None]
            if len(pts) > 1:
                series.append((pts, self.cosine(pts), col))
        for pts, d, col in series:
            poly = [p for xy in d for p in xy] + [pts[-1][0], Y(0), pts[0][0], Y(0)]
            cv.create_polygon(poly, fill=mix(col, c["card"], .62), outline="")
        for pts, d, col in series:
            cv.create_line([p for xy in d for p in xy], fill=col, width=2)
            for x, y in pts:
                cv.create_oval(x - 3.5, y - 3.5, x + 3.5, y + 3.5, fill=c["card"], outline=col, width=2)

    # ---------- dashboard ----------
    def make_dash(self):
        c = self.c
        g = tk.Frame(self.pages["Dashboard"], bg=c["bg"])
        g.pack(fill="both", expand=True, padx=40, pady=(26, 28))
        for i in range(3):
            g.grid_columnconfigure(i, weight=1, uniform="d")
        g.grid_rowconfigure(2, weight=1)
        g.grid_rowconfigure(3, weight=1)
        self.welcome = self.lbl(g, "", 22, bold=True, anchor="w")
        self.welcome.grid(row=0, column=0, columnspan=3, sticky="w", padx=8)
        self.sub = self.lbl(g, "", 10, c["mute"], anchor="w")
        self.sub.grid(row=1, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 8))
        self.dc = {}
        for key, (r, col, span) in {"ov": (2, 0, 1), "act": (2, 1, 2), "proj": (3, 0, 1),
                                    "tl": (3, 1, 1), "ev": (3, 2, 1)}.items():
            cd = Card(g, c)
            cd.grid(row=r, column=col, columnspan=span, sticky="nsew", padx=8, pady=8)
            self.dc[key] = cd.body
        self.charts.append(self.chart_card(self.dc["act"], "Activity Stats", 170))

    def fill_dash(self):
        c, today = self.c, dt.date.today()
        open_ = [t for t in self.tasks if not t["done"]]
        od = sum(is_overdue(t) for t in open_)
        self.welcome.config(text=f"Welcome Back, {self.data['name']}!")
        self.sub.config(text=today.strftime("%A, %d %B %Y") + f"   -   {len(open_)} open, {od} overdue")

        b = self.dc["ov"]
        self.clear(b)
        self.heading(b, "Today's Overview")
        row = tk.Frame(b, bg=c["card"])
        row.pack(fill="x")
        done_today = sum(1 for s in self.data.get("log", []) if s[:10] == today.isoformat())
        for i, (num, lab) in enumerate([(len(open_), "Open tasks"), (done_today, "Done today")]):
            bg, fg = (c["accent"], c["accent_fg"]) if i == 0 else (c["card2"], c["fg"])
            tile = tk.Frame(row, bg=bg)
            tile.pack(side="left", fill="x", expand=True)
            tk.Label(tile, text=str(num), bg=bg, fg=fg, font=(FONT, 28)).pack(anchor="w", padx=16, pady=(10, 0))
            tk.Label(tile, text=lab, bg=bg, fg=fg if i == 0 else c["mute"], font=(FONT, 9)).pack(
                anchor="w", padx=16, pady=(0, 12))
        dtoday = sum(1 for t in open_ if parse(t["due"]) and parse(t["due"]).date() == today)
        self.lbl(b, f"{dtoday} due today  -  {od} overdue", 9, c["mute"]).pack(anchor="w", pady=(10, 0))

        b = self.dc["proj"]
        self.clear(b)
        self.heading(b, "My Projects")
        cats = self.data["cats"][:3]
        if not cats:
            self.lbl(b, "Create a list to see projects here.", 10, c["mute"]).pack(anchor="w")
        for i, ct in enumerate(cats):
            allc = [t for t in self.tasks if t["cat"] == ct]
            dn = sum(t["done"] for t in allc)
            tile = Card(b, c, pad=10, r=10, fill=c["card2"], shadow=False)
            tile.pack(fill="x", pady=4)
            tb = tile.body
            top = tk.Frame(tb, bg=c["card2"])
            top.pack(fill="x")
            self.lbl(top, ct, 11).pack(side="left")
            self.lbl(top, "\u203a", 14, c["mute"]).pack(side="right")
            self.lbl(top, f"{len(allc) - dn} open" if allc else "Empty", 9, c["mute"]).pack(side="right", padx=6)
            bar = tk.Canvas(tb, height=6, bg=c["card2"], highlightthickness=0)
            bar.pack(fill="x", pady=(6, 0))
            bar.bind("<Configure>", lambda e, w=bar, p=(dn / len(allc) if allc else 0),
                     col=[c["accent"], c["teal"]][i % 2]: self.bar(w, p, col))
            for w in (tile, tb, top) + tuple(top.winfo_children()):
                w.bind("<Button-1>", lambda e, x=ct: self.set_cat(x))

        b = self.dc["tl"]
        self.clear(b)
        self.heading(b, "Task List")
        nxt = sorted(open_, key=lambda t: (t["due"] == "", t["due"], -t["pri"]))[:4]
        if not nxt:
            self.lbl(b, "You're all caught up.", 10, c["mute"]).pack(anchor="w", pady=10)
        for t in nxt:
            r = tk.Frame(b, bg=c["card"])
            r.pack(fill="x", pady=5)
            self.check(r, t, 22).pack(side="left")
            ttl = t["title"] if len(t["title"]) < 22 else t["title"][:20] + "\u2026"
            self.lbl(r, ttl, 10).pack(side="left", padx=10)
            if t["due"]:
                bad = is_overdue(t)
                self.chip(r, fmt_due(t["due"]), c["danger"] if bad else c["accent"],
                          "#ffffff").pack(side="right")
            tk.Frame(b, bg=c["line"], height=1).pack(fill="x")
        self.btn(b, "Add Task", lambda: self.open_editor(None)).pack(anchor="e", pady=(12, 0))

        b = self.dc["ev"]
        self.clear(b)
        self.heading(b, "Upcoming Events")
        start = dt.datetime.combine(today, dt.time.min)
        evs = sorted([t for t in open_ if parse(t["due"]) and parse(t["due"]) >= start], key=lambda t: t["due"])[:3]
        if not evs:
            self.lbl(b, "Nothing scheduled. Give a task a due date.", 10, c["mute"]).pack(anchor="w", pady=10)
        for i, t in enumerate(evs):
            tile = Card(b, c, pad=10, r=10, fill=c["card2"], shadow=False)
            tile.pack(fill="x", pady=4)
            tb = tile.body
            col = [c["accent"], c["teal"]][i % 2]
            sq = tk.Canvas(tb, width=38, height=38, bg=c["card2"], highlightthickness=0)
            rrect(sq, 1, 1, 37, 37, 9, fill=mix(col, c["card2"], .7), outline="")
            sq.create_text(19, 19, text=str(parse(t["due"]).day), fill=col, font=(FONT, 13, "bold"))
            sq.pack(side="left", padx=(0, 10))
            tx = tk.Frame(tb, bg=c["card2"])
            tx.pack(side="left")
            ttl = t["title"] if len(t["title"]) < 20 else t["title"][:18] + "\u2026"
            self.lbl(tx, ttl, 10, bold=True).pack(anchor="w")
            self.lbl(tx, fmt_due(t["due"]), 9, c["mute"]).pack(anchor="w")
            for w in (tile, tb, sq, tx) + tuple(tx.winfo_children()):
                w.bind("<Button-1>", lambda e, x=t: self.open_editor(x))

    # ---------- tasks page ----------
    def make_tasks(self):
        c = self.c
        p = tk.Frame(self.pages["Tasks"], bg=c["bg"])
        p.pack(fill="both", expand=True, padx=48, pady=(26, 18))
        hd = tk.Frame(p, bg=c["bg"])
        hd.pack(fill="x")
        self.h1 = self.lbl(hd, "", 22, bold=True)
        self.h1.pack(side="left")
        sort = ttk.Combobox(hd, textvariable=self.sort, state="readonly", width=12,
                            values=["Created", "Due date", "Priority", "A-Z"])
        sort.pack(side="right")
        sort.bind("<<ComboboxSelected>>", lambda e: self.fill_tasks())
        self.h2 = self.lbl(p, "", 10, c["mute"], anchor="w")
        self.h2.pack(fill="x", pady=(0, 6))
        self.fbar = tk.Frame(p, bg=c["bg"])
        self.fbar.pack(fill="x", pady=(6, 6))
        self.lbar = tk.Frame(p, bg=c["bg"])
        self.lbar.pack(fill="x", pady=(0, 12))
        qa = Card(p, c, pad=10, r=14)
        qa.pack(fill="x", pady=(0, 10))
        qb = qa.body
        self.quick = tk.Entry(qb, bg=c["card"], fg=c["mute"], relief="flat", font=(FONT, 12),
                              insertbackground=c["fg"])
        self.quick.pack(side="left", fill="x", expand=True, padx=(8, 8), ipady=8)
        self.quick.insert(0, self.hint)
        self.quick.bind("<Return>", lambda e: self.quick_add())
        self.quick.bind("<FocusIn>", self.clear_hint)
        self.quick.bind("<FocusOut>", self.set_hint)
        self.btn(qb, "Add task", self.quick_add).pack(side="right")
        self.btn(qb, "Details", lambda: self.open_editor(None, self.quick_text()), ghost=True).pack(
            side="right", padx=8)
        wrap = tk.Frame(p, bg=c["bg"])
        wrap.pack(fill="both", expand=True)
        self.cv = tk.Canvas(wrap, bg=c["bg"], highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.lst = tk.Frame(self.cv, bg=c["bg"])
        self.win = self.cv.create_window(0, 0, window=self.lst, anchor="nw")
        self.lst.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfig(self.win, width=e.width))
        foot = tk.Frame(p, bg=c["bg"])
        foot.pack(fill="x", pady=(8, 0))
        self.lbl(foot, "Ctrl+N new   Ctrl+F search   Ctrl+Z undo   Ctrl+D theme", 9, c["mute"]).pack(side="left")
        cl = self.lbl(foot, "Clear completed", 9, c["danger"], bold=True, cursor="hand2")
        cl.pack(side="right")
        cl.bind("<Button-1>", lambda e: self.clear_done())

    def fill_tasks(self):
        c = self.c
        for f in (self.fbar, self.lbar, self.lst):
            self.clear(f)
        pool = [t for t in self.tasks if not self.cat or t["cat"] == self.cat]
        for name, key in FILTERS:
            n = sum(self.matches(t, key) for t in pool)
            self.btn(self.fbar, f"{name}  {n}" if n else name, lambda k=key: self.set_view(k),
                     ghost=(key != self.view), h=32).pack(side="left", padx=(0, 8))
        self.lbl(self.lbar, "Lists", 9, c["mute"], bold=True).pack(side="left", padx=(2, 10))
        for ct in self.data["cats"]:
            n = sum(1 for t in self.tasks if t["cat"] == ct and not t["done"])
            b = self.btn(self.lbar, "# " + ct + (f"  {n}" if n else ""), lambda x=ct: self.set_cat(x),
                         ghost=(ct != self.cat), h=28)
            b.pack(side="left", padx=(0, 8))
            b.bind("<Button-3>", lambda e, x=ct: self.cat_menu(e, x))
        self.btn(self.lbar, "+ New list", self.add_cat, ghost=True, h=28).pack(side="left")
        vis = self.visible()
        self.h1.config(text=self.cat or dict((k, n) for n, k in FILTERS)[self.view])
        done = sum(t["done"] for t in pool)
        self.h2.config(text=f"{len(vis)} shown   -   {done} of {len(pool)} completed")
        if not vis:
            self.lbl(self.lst, "Nothing here yet.\nType a task above and press Enter.", 11, c["mute"],
                     pady=60).pack(fill="x")
        for t in vis:
            self.row(t)

    def row(self, t):
        c = self.c
        card = Card(self.lst, c, pad=12, r=14)
        card.pack(fill="x", pady=5, padx=(0, 6))
        b = card.body
        tk.Frame(b, bg=PCOL[t["pri"]], width=4).pack(side="left", fill="y", padx=(0, 12))
        self.check(b, t, 26).pack(side="left", padx=(0, 12))
        info = tk.Frame(b, bg=c["card"])
        info.pack(side="left", fill="x", expand=True)
        tl = tk.Label(info, text=t["title"], bg=c["card"], anchor="w", justify="left",
                      fg=c["mute"] if t["done"] else c["fg"], font=self.f_done if t["done"] else self.f_title)
        tl.pack(fill="x")
        chips = []
        if t["due"]:
            bad = is_overdue(t)
            chips.append(("\u23f0 " + fmt_due(t["due"]), mix(c["danger"] if bad else c["accent"], c["card"], .82),
                          c["danger"] if bad else c["accent"]))
        if t["cat"]:
            chips.append(("# " + t["cat"], c["card2"], c["mute"]))
        if t["subs"]:
            chips.append((f"\u2611 {sum(s['d'] for s in t['subs'])}/{len(t['subs'])}", c["card2"], c["mute"]))
        if t["repeat"] != "Never":
            chips.append(("\u21bb " + t["repeat"], c["card2"], c["mute"]))
        if t["notes"]:
            chips.append(("\u270e notes", c["card2"], c["mute"]))
        if chips:
            mf = tk.Frame(info, bg=c["card"])
            mf.pack(fill="x", pady=(5, 0))
            for txt, bg, fg in chips:
                self.chip(mf, txt, bg, fg).pack(side="left", padx=(0, 6))
        acts = tk.Frame(b, bg=c["card"])
        acts.pack(side="right", padx=4)
        for sym, fn, col in [("\u270e", lambda: self.open_editor(t), c["mute"]),
                             ("\u2715", lambda: self.delete(t), c["danger"])]:
            x = self.lbl(acts, sym, 12, col, cursor="hand2", padx=6)
            x.pack(side="left")
            x.bind("<Button-1>", lambda e, f=fn: f())
        for w in (card, b, info, tl):
            w.bind("<Double-Button-1>", lambda e: self.open_editor(t))

    # ---------- analytics ----------
    def make_analytics(self):
        c = self.c
        g = tk.Frame(self.pages["Analytics"], bg=c["bg"])
        g.pack(fill="both", expand=True, padx=40, pady=(26, 28))
        for i in range(4):
            g.grid_columnconfigure(i, weight=1, uniform="a")
        g.grid_rowconfigure(2, weight=1)
        self.lbl(g, "Analytics", 22, bold=True).grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 6))
        self.st = []
        for i in range(4):
            cd = Card(g, c)
            cd.grid(row=1, column=i, sticky="nsew", padx=8, pady=8)
            self.st.append(cd.body)
        cd = Card(g, c)
        cd.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=8, pady=8)
        self.charts.append(self.chart_card(cd.body, "Weekly completions", 240))
        cd = Card(g, c)
        cd.grid(row=2, column=3, sticky="nsew", padx=8, pady=8)
        self.pri_body = cd.body

    def fill_analytics(self):
        c, today, tasks = self.c, dt.date.today(), self.tasks
        done = sum(t["done"] for t in tasks)
        op, od = len(tasks) - done, sum(is_overdue(t) for t in tasks)
        days = {s[:10] for s in self.data.get("log", [])}
        d, streak = today, 0
        if d.isoformat() not in days:
            d -= dt.timedelta(days=1)
        while d.isoformat() in days:
            streak += 1
            d -= dt.timedelta(days=1)
        rate = f"{round(100 * done / len(tasks))}%" if tasks else "0%"
        vals = [("Completion rate", rate, c["teal"]), ("Open tasks", str(op), c["accent"]),
                ("Overdue", str(od), c["danger"]), ("Day streak", str(streak), c["fg"])]
        for b, (lab, val, col) in zip(self.st, vals):
            self.clear(b)
            self.lbl(b, lab, 10, c["mute"]).pack(anchor="w")
            self.lbl(b, val, 28, col, bold=True).pack(anchor="w")
        b = self.pri_body
        self.clear(b)
        self.heading(b, "Open by priority")
        for p in (3, 2, 1, 0):
            n = sum(1 for t in tasks if not t["done"] and t["pri"] == p)
            r = tk.Frame(b, bg=c["card"])
            r.pack(fill="x", pady=6)
            self.lbl(r, PRI[p], 10, width=7, anchor="w").pack(side="left")
            cv = tk.Canvas(r, height=8, bg=c["card"], highlightthickness=0)
            cv.pack(side="left", fill="x", expand=True, padx=6)
            cv.bind("<Configure>", lambda e, w=cv, v=n / max(1, op), col=PCOL[p]: self.bar(w, v, col))
            self.lbl(r, str(n), 10, c["mute"]).pack(side="left")

    # ---------- settings ----------
    def make_settings(self):
        c = self.c
        g = tk.Frame(self.pages["Settings"], bg=c["bg"])
        g.pack(fill="both", expand=True, padx=40, pady=(26, 28))
        for i in (0, 1):
            g.grid_columnconfigure(i, weight=1, uniform="s")
        self.lbl(g, "Settings", 22, bold=True).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        def card(r, col):
            cd = Card(g, c)
            cd.grid(row=r, column=col, sticky="new", padx=8, pady=8)
            return cd.body
        b = card(1, 0)
        self.heading(b, "Profile")
        self.lbl(b, "Display name", 9, c["mute"]).pack(anchor="w")
        self.name_e = tk.Entry(b, bg=c["card2"], fg=c["fg"], relief="flat", insertbackground=c["fg"],
                               highlightthickness=1, highlightbackground=c["line"], font=(FONT, 11))
        self.name_e.insert(0, self.data["name"])
        self.name_e.pack(fill="x", ipady=7, pady=6)
        self.name_e.bind("<Return>", lambda e: self.set_name())
        self.btn(b, "Save name", self.set_name).pack(anchor="e", pady=(4, 0))
        b = card(1, 1)
        self.heading(b, "Appearance")
        row = tk.Frame(b, bg=c["card"])
        row.pack(anchor="w")
        for x in ("light", "dark"):
            self.btn(row, x.title() + " theme", lambda x=x: self.set_theme(x),
                     ghost=self.data["theme"] != x).pack(side="left", padx=(0, 8))
        b = card(2, 1)
        self.heading(b, "Data")
        for txt, fn in [("Export backup", self.export), ("Import backup", self.import_),
                        ("Undo last change", self.do_undo), ("Clear completed tasks", self.clear_done)]:
            self.btn(b, txt, fn, ghost=True).pack(anchor="w", pady=4)
        self.lists_body = card(2, 0)

    def fill_settings(self):
        c, b = self.c, self.lists_body
        self.clear(b)
        self.heading(b, "Lists")
        for ct in self.data["cats"]:
            r = tk.Frame(b, bg=c["card"])
            r.pack(fill="x", pady=4)
            self.lbl(r, "# " + ct, 11).pack(side="left")
            self.btn(r, "Delete", lambda x=ct: self.del_cat(x), ghost=True, h=28).pack(side="right", padx=(6, 0))
            self.btn(r, "Rename", lambda x=ct: self.rename_cat(x), ghost=True, h=28).pack(side="right")
        self.btn(b, "+ New list", self.add_cat).pack(anchor="w", pady=(10, 0))


    def load(self):
        try:
            with open(FILE, encoding="utf-8") as f:
                self.data.update(json.load(f))
        except Exception:
            pass

    def save(self):
        os.makedirs(DIR, exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1)

    def snap(self):
        self.undo.append(copy.deepcopy(self.data["tasks"]))
        self.undo = self.undo[-30:]

    def do_undo(self):
        if self.undo:
            self.data["tasks"] = self.undo.pop()
            self.changed("Undone")

    @property
    def tasks(self):
        return self.data["tasks"]

    def clear_hint(self, e=None):
        if self.quick.cget("fg") == self.c["mute"]:
            self.quick.delete(0, "end")
            self.quick.config(fg=self.c["fg"])

    def set_hint(self, e=None):
        if not self.quick.get():
            self.quick.insert(0, self.hint)
            self.quick.config(fg=self.c["mute"])

    def quick_text(self):
        return "" if self.quick.cget("fg") == self.c["mute"] else self.quick.get().strip()

    def matches(self, t, view):
        d = parse(t["due"])
        today = dt.date.today()
        return {"all": not t["done"], "done": t["done"], "important": t["pri"] == 3 and not t["done"],
                "overdue": is_overdue(t), "today": bool(d) and d.date() == today and not t["done"],
                "upcoming": bool(d) and d.date() > today and not t["done"]}[view]

    def visible(self):
        q = self.search.get().lower().strip()
        out = [t for t in self.tasks if self.matches(t, self.view) and (not self.cat or t["cat"] == self.cat)
               and (not q or q in t["title"].lower() or q in t["notes"].lower() or
                    any(q in s["t"].lower() for s in t["subs"]))]
        s = self.sort.get()
        if s == "Due date":
            out.sort(key=lambda t: (t["due"] == "", t["due"]))
        elif s == "Priority":
            out.sort(key=lambda t: -t["pri"])
        elif s == "A-Z":
            out.sort(key=lambda t: t["title"].lower())
        return out

    def new_task(self, title, **kw):
        t = dict(id=uuid.uuid4().hex, title=title, notes="", due="", pri=0, cat=self.cat or "", done=False,
                 repeat="Never", subs=[], created=dt.datetime.now().isoformat())
        t.update(kw)
        return t

    def quick_add(self):
        txt = self.quick_text()
        if not txt:
            return
        due = ""
        words = txt.split()
        if words[-1].lower() in ("today", "tomorrow") and len(words) > 1:
            due = (dt.date.today() + dt.timedelta(days=words[-1].lower() == "tomorrow")).isoformat()
            txt = " ".join(words[:-1])
        pri = 3 if txt.endswith("!!!") else 0
        self.snap()
        self.tasks.insert(0, self.new_task(txt.rstrip("!") if pri else txt, due=due, pri=pri))
        self.reset_quick()
        self.changed("Task added")

    def delete(self, t):
        self.snap()
        self.tasks.remove(t)
        self.changed("Deleted - press Ctrl+Z to undo")

    def clear_done(self):
        if any(t["done"] for t in self.tasks) and messagebox.askyesno(APP, "Remove all completed tasks?"):
            self.snap()
            self.data["tasks"] = [t for t in self.tasks if not t["done"]]
            self.changed("Completed tasks cleared")

    def add_cat(self):
        n = simpledialog.askstring(APP, "Name for the new list:", parent=self)
        if n and n.strip() and n.strip() not in self.data["cats"]:
            self.data["cats"].append(n.strip())
            self.changed("List created")

    def cat_menu(self, e, ct):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="Rename list", command=lambda: self.rename_cat(ct))
        m.add_command(label="Delete list", command=lambda: self.del_cat(ct))
        m.tk_popup(e.x_root, e.y_root)

    def rename_cat(self, ct):
        n = simpledialog.askstring(APP, "New name:", initialvalue=ct, parent=self)
        if n and n.strip():
            self.data["cats"][self.data["cats"].index(ct)] = n.strip()
            for t in self.tasks:
                if t["cat"] == ct:
                    t["cat"] = n.strip()
            self.cat = None
            self.changed("List renamed")

    def del_cat(self, ct):
        if messagebox.askyesno(APP, f"Delete '{ct}'? Its tasks stay, but lose their list."):
            self.data["cats"].remove(ct)
            for t in self.tasks:
                if t["cat"] == ct:
                    t["cat"] = ""
            self.cat = None
            self.changed("List deleted")

    def toggle_theme(self):
        self.data["theme"] = "light" if self.data["theme"] == "dark" else "dark"
        self.save()
        self.build()

    def export(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="taskflow-backup.json")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=1)
            self.flash("Backup saved")

    def import_(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if p:
            try:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
                self.snap()
                ids = {t["id"] for t in self.tasks}
                self.tasks.extend(t for t in d["tasks"] if t["id"] not in ids)
                for ct in d.get("cats", []):
                    if ct not in self.data["cats"]:
                        self.data["cats"].append(ct)
                self.changed("Backup imported")
            except Exception:
                messagebox.showerror(APP, "That file isn't a valid TaskFlow backup.")

    def check_reminders(self):
        now = dt.datetime.now()
        for t in self.tasks:
            d = parse(t["due"])
            if d and " " in t["due"] and not t["done"] and d <= now and t["id"] not in self.notified:
                self.notified.add(t["id"])
                self.toast(t)
        self.after(20000, self.check_reminders)

    def toast(self, t):
        c = self.c
        w = tk.Toplevel(self)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=c["accent"])
        inner = tk.Frame(w, bg=c["card"])
        inner.pack(padx=2, pady=2)
        tk.Label(inner, text="Reminder", bg=c["card"], fg=c["accent"], font=(FONT, 9, "bold")).pack(
            anchor="w", padx=16, pady=(12, 0))
        tk.Label(inner, text=t["title"], bg=c["card"], fg=c["fg"], font=(FONT, 12, "bold"),
                 wraplength=280, justify="left").pack(anchor="w", padx=16, pady=(2, 8))
        row = tk.Frame(inner, bg=c["card"])
        row.pack(anchor="e", padx=12, pady=(0, 12))
        self.btn(row, "Snooze 10 min", lambda: (self.snooze(t), w.destroy()), ghost=True).pack(side="left", padx=4)
        self.btn(row, "Done", lambda: (self.toggle(t), w.destroy())).pack(side="left")
        w.update_idletasks()
        w.geometry(f"+{self.winfo_screenwidth() - w.winfo_width() - 24}+{self.winfo_screenheight() - w.winfo_height() - 70}")
        self.bell()
        w.after(15000, lambda: w.winfo_exists() and w.destroy())

    def snooze(self, t):
        t["due"] = (dt.datetime.now() + dt.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
        self.notified.discard(t["id"])
        self.changed("Snoozed 10 minutes")

    def open_editor(self, t, title=""):
        c = self.c
        new = t is None
        t = t or self.new_task(title)
        w = tk.Toplevel(self)
        w.title("New task" if new else "Edit task")
        w.configure(bg=c["bg"])
        w.geometry("520x700")
        w.transient(self)
        w.grab_set()
        pad = dict(padx=26, anchor="w")

        def lab(txt):
            tk.Label(w, text=txt, bg=c["bg"], fg=c["mute"], font=(FONT, 9, "bold")).pack(pady=(12, 3), **pad)

        def ent(parent=w, **kw):
            e = tk.Entry(parent, bg=c["card"], fg=c["fg"], relief="flat", insertbackground=c["fg"],
                         highlightthickness=1, highlightbackground=c["line"], font=(FONT, 11), **kw)
            return e
        lab("Title")
        title_e = ent()
        title_e.insert(0, t["title"])
        title_e.pack(fill="x", padx=26, ipady=7)
        lab("Notes")
        notes = tk.Text(w, height=4, bg=c["card"], fg=c["fg"], relief="flat", insertbackground=c["fg"],
                        highlightthickness=1, highlightbackground=c["line"], font=(FONT, 10), wrap="word")
        notes.insert("1.0", t["notes"])
        notes.pack(fill="x", padx=26)
        lab("Due date (YYYY-MM-DD)  and time (HH:MM, optional)")
        r = tk.Frame(w, bg=c["bg"])
        r.pack(fill="x", padx=26)
        d0 = parse(t["due"])
        date_e, time_e = ent(r, width=14), ent(r, width=8)
        date_e.insert(0, d0.strftime("%Y-%m-%d") if d0 else "")
        time_e.insert(0, d0.strftime("%H:%M") if d0 and " " in t["due"] else "")
        date_e.pack(side="left", ipady=6)
        time_e.pack(side="left", padx=8, ipady=6)
        for txt, days in [("Today", 0), ("Tomorrow", 1), ("+1 week", 7), ("Clear", None)]:
            def setd(days=days):
                date_e.delete(0, "end")
                if days is not None:
                    date_e.insert(0, (dt.date.today() + dt.timedelta(days=days)).isoformat())
                else:
                    time_e.delete(0, "end")
            b = tk.Label(r, text=txt, bg=c["bg"], fg=c["accent"], font=(FONT, 9, "bold"), cursor="hand2")
            b.pack(side="left", padx=5)
            b.bind("<Button-1>", lambda e, f=setd: f())
        grid = tk.Frame(w, bg=c["bg"])
        grid.pack(fill="x", padx=26, pady=(12, 0))
        vp, vc, vr = tk.StringVar(value=PRI[t["pri"]]), tk.StringVar(value=t["cat"]), tk.StringVar(value=t["repeat"])
        for i, (name, var, vals) in enumerate([("Priority", vp, PRI), ("List", vc, [""] + self.data["cats"]),
                                               ("Repeat", vr, REPEAT)]):
            col = tk.Frame(grid, bg=c["bg"])
            col.pack(side="left", expand=True, fill="x", padx=(0 if i == 0 else 8, 0))
            tk.Label(col, text=name, bg=c["bg"], fg=c["mute"], font=(FONT, 9, "bold")).pack(anchor="w", pady=(0, 3))
            ttk.Combobox(col, textvariable=var, values=vals, state="readonly").pack(fill="x")
        lab("Subtasks (double-click to tick)")
        subs = [dict(s) for s in t["subs"]]
        lb = tk.Listbox(w, height=5, bg=c["card"], fg=c["fg"], relief="flat", font=(FONT, 10),
                        highlightthickness=1, highlightbackground=c["line"], selectbackground=c["hover"],
                        selectforeground=c["fg"], activestyle="none")
        lb.pack(fill="x", padx=26)

        def refresh():
            lb.delete(0, "end")
            for s in subs:
                lb.insert("end", ("\u2611  " if s["d"] else "\u2610  ") + s["t"])

        def flip(e=None):
            if lb.curselection():
                subs[lb.curselection()[0]]["d"] ^= True
                refresh()
        lb.bind("<Double-Button-1>", flip)
        refresh()
        sr = tk.Frame(w, bg=c["bg"])
        sr.pack(fill="x", padx=26, pady=6)
        sub_e = ent(sr)
        sub_e.pack(side="left", fill="x", expand=True, ipady=5)

        def add_sub(e=None):
            if sub_e.get().strip():
                subs.append({"t": sub_e.get().strip(), "d": False})
                sub_e.delete(0, "end")
                refresh()

        def rm_sub():
            if lb.curselection():
                subs.pop(lb.curselection()[0])
                refresh()
        sub_e.bind("<Return>", add_sub)
        self.btn(sr, "Add", add_sub, ghost=True).pack(side="left", padx=(6, 0))
        self.btn(sr, "Remove", rm_sub, ghost=True).pack(side="left", padx=(6, 0))

        def save():
            ttl = title_e.get().strip()
            if not ttl:
                return messagebox.showwarning(APP, "Give the task a title.", parent=w)
            ds, ts = date_e.get().strip(), time_e.get().strip()
            if ds and not parse(ds):
                return messagebox.showwarning(APP, "Date should look like 2026-11-30.", parent=w)
            if ts and (not ds or not parse(f"{ds} {ts}")):
                return messagebox.showwarning(APP, "Time should look like 14:30, with a date set.", parent=w)
            if t["repeat"] == "Never" and vr.get() != "Never" and not ds:
                return messagebox.showwarning(APP, "Repeating tasks need a due date.", parent=w)
            self.snap()
            t.update(title=ttl, notes=notes.get("1.0", "end").strip(), due=(f"{ds} {ts}" if ts else ds),
                     pri=PRI.index(vp.get()), cat=vc.get(), repeat=vr.get(), subs=subs)
            self.notified.discard(t["id"])
            if new:
                self.tasks.insert(0, t)
                self.reset_quick()
            w.destroy()
            self.changed("Task saved")
        bar = tk.Frame(w, bg=c["bg"])
        bar.pack(side="bottom", fill="x", padx=26, pady=18)
        self.btn(bar, "Save task", save).pack(side="right")
        self.btn(bar, "Cancel", w.destroy, ghost=True).pack(side="right", padx=8)
        w.bind("<Control-Return>", lambda e: save())
        w.bind("<Escape>", lambda e: w.destroy())
        title_e.focus_set()



if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()
