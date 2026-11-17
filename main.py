import csv
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime, timedelta
from pathlib import Path

APP_NAME = "FocusFlow"
DB_PATH = Path(__file__).with_name("focusflow.db")

BG = "#101722"
SIDEBAR = "#151F2D"
PANEL = "#1B2838"
PANEL_2 = "#202F42"
TEXT = "#EDF3FA"
MUTED = "#91A2B7"
ACCENT = "#7C9CFF"
ACCENT_HOVER = "#91ACFF"
GREEN = "#56C7A5"
YELLOW = "#F3BE68"
RED = "#F07878"
BORDER = "#2B3B50"

class Store:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                notes TEXT DEFAULT '',
                category TEXT DEFAULT 'Personal',
                priority TEXT DEFAULT 'Medium',
                due_date TEXT DEFAULT '',
                completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT DEFAULT ''
            )
        """)
        self.conn.commit()

    def all(self):
        return self.conn.execute("SELECT * FROM tasks ORDER BY completed ASC, due_date ASC, id DESC").fetchall()

    def save(self, data, task_id=None):
        if task_id:
            self.conn.execute("""UPDATE tasks SET title=?, notes=?, category=?, priority=?, due_date=? WHERE id=?""",
                (data["title"], data["notes"], data["category"], data["priority"], data["due_date"], task_id))
        else:
            self.conn.execute("""INSERT INTO tasks(title,notes,category,priority,due_date,created_at)
                VALUES(?,?,?,?,?,?)""",
                (data["title"], data["notes"], data["category"], data["priority"], data["due_date"], datetime.now().isoformat(timespec="seconds")))
        self.conn.commit()

    def toggle(self, task_id, completed):
        self.conn.execute("UPDATE tasks SET completed=?, completed_at=? WHERE id=?",
            (int(completed), datetime.now().isoformat(timespec="seconds") if completed else "", task_id))
        self.conn.commit()

    def delete(self, task_id):
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()

class FocusFlow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FocusFlow — Plan with clarity")
        self.geometry("1180x760")
        self.minsize(940, 620)
        self.configure(bg=BG)
        self.store = Store()
        self.active_filter = "All tasks"
        self.search_var = tk.StringVar()
        self.category_var = tk.StringVar(value="All categories")
        self.sort_var = tk.StringVar(value="Due date")
        self.selected_id = None
        self._style()
        self._layout()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=38, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=PANEL_2, foreground=MUTED,
                        relief="flat", font=("Segoe UI Semibold", 9))
        style.map("Treeview", background=[("selected", "#30466A")], foreground=[("selected", TEXT)])
        style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER)

    def label(self, parent, text, size=10, color=TEXT, weight="normal"):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI" if weight == "normal" else "Segoe UI Semibold", size))

    def button(self, parent, text, command, primary=False, width=None):
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
            bg=ACCENT if primary else PANEL_2, fg="#101722" if primary else TEXT,
            activebackground=ACCENT_HOVER if primary else BORDER,
            activeforeground="#101722" if primary else TEXT,
            font=("Segoe UI Semibold", 9), padx=15, pady=9, cursor="hand2", width=width)

    def _layout(self):
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=225)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="✦  FocusFlow", bg=SIDEBAR, fg=TEXT,
                 font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=22, pady=(28, 4))
        self.label(self.sidebar, "MAKE SPACE FOR WHAT MATTERS", 8, MUTED, "bold").pack(anchor="w", padx=24, pady=(0, 32))
        self.label(self.sidebar, "WORKSPACE", 8, MUTED, "bold").pack(anchor="w", padx=22, pady=(0, 10))
        self.nav_buttons = {}
        for name, icon in [("All tasks", "▦"), ("Today", "◷"), ("Upcoming", "↗"), ("Completed", "✓")]:
            b = tk.Button(self.sidebar, text=f"  {icon}   {name}", anchor="w", command=lambda n=name: self.set_filter(n),
                          relief="flat", bd=0, bg=SIDEBAR, fg=TEXT, activebackground=PANEL_2,
                          activeforeground=TEXT, font=("Segoe UI Semibold", 10), padx=14, pady=12, cursor="hand2")
            b.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[name] = b
        self.label(self.sidebar, "QUICK TIP", 8, MUTED, "bold").pack(anchor="w", padx=22, pady=(35, 10))
        tk.Label(
    self.sidebar,
    text="Keep tasks small, clear,\nand actionable. Progress\ncomes from consistency.",
    justify="left",
    bg=SIDEBAR,
    fg=MUTED,
    font=("Segoe UI", 9)
).pack(anchor="w", padx=22, pady=5)

        self.main = tk.Frame(self, bg=BG)
        self.main.pack(side="left", fill="both", expand=True, padx=30, pady=25)
        top = tk.Frame(self.main, bg=BG)
        top.pack(fill="x")
        left = tk.Frame(top, bg=BG); left.pack(side="left")
        self.heading = tk.Label(left, text="All tasks", bg=BG, fg=TEXT, font=("Segoe UI Semibold", 25))
        self.heading.pack(anchor="w")
        self.subheading = tk.Label(left, text="A calm place to organise your day.", bg=BG, fg=MUTED, font=("Segoe UI", 10))
        self.subheading.pack(anchor="w", pady=(3, 0))
        self.button(top, "+  Add task", self.open_editor, True).pack(side="right", anchor="center")

        stats = tk.Frame(self.main, bg=BG)
        stats.pack(fill="x", pady=(25, 20))
        self.stat_values = {}
        for title, key, color in [("TOTAL TASKS", "total", ACCENT), ("COMPLETED", "done", GREEN), ("DUE TODAY", "today", YELLOW), ("OVERDUE", "late", RED)]:
            card = tk.Frame(stats, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
            card.pack(side="left", fill="x", expand=True, padx=(0, 12))
            tk.Label(card, text=title, bg=PANEL, fg=MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=16, pady=(13, 2))
            val = tk.Label(card, text="0", bg=PANEL, fg=color, font=("Segoe UI Semibold", 23))
            val.pack(anchor="w", padx=16, pady=(0, 12))
            self.stat_values[key] = val

        toolbar = tk.Frame(self.main, bg=BG)
        toolbar.pack(fill="x", pady=(0, 12))
        search = tk.Entry(toolbar, textvariable=self.search_var, bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
                          relief="flat", font=("Segoe UI", 10))
        search.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 10))
        search.insert(0, "")
        search.bind("<KeyRelease>", lambda e: self.refresh())
        self.cat_box = ttk.Combobox(toolbar, textvariable=self.category_var, state="readonly",
                                    values=["All categories", "Personal", "Work", "Study", "Health", "Shopping", "Other"], width=16)
        self.cat_box.pack(side="left", padx=(0, 10), ipady=5)
        self.cat_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self.sort_box = ttk.Combobox(toolbar, textvariable=self.sort_var, state="readonly",
                                     values=["Due date", "Priority", "Recently added"], width=15)
        self.sort_box.pack(side="left", ipady=5)
        self.sort_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        table_wrap = tk.Frame(self.main, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        table_wrap.pack(fill="both", expand=True)
        cols = ("status", "task", "category", "priority", "due")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="browse")
        for col, title, width in [("status", "DONE", 65), ("task", "TASK", 360), ("category", "CATEGORY", 120),
                                  ("priority", "PRIORITY", 100), ("due", "DUE DATE", 120)]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w" if col == "task" else "center")
        self.tree.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.tree.bind("<<TreeviewSelect>>", self.selection_changed)

        bottom = tk.Frame(self.main, bg=BG)
        bottom.pack(fill="x", pady=(13, 0))
        self.selected_label = tk.Label(bottom, text="Select a task to edit, complete or delete it.", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.selected_label.pack(side="left")
        self.button(bottom, "Complete / Undo", self.toggle_selected).pack(side="right", padx=(8, 0))
        self.button(bottom, "Edit", self.edit_selected).pack(side="right", padx=(8, 0))
        self.button(bottom, "Delete", self.delete_selected).pack(side="right")

        menu = tk.Menu(self, tearoff=0, bg=PANEL, fg=TEXT)
        menu.add_command(label="Export tasks to CSV", command=self.export_csv)
        menu.add_command(label="Import tasks from CSV", command=self.import_csv)
        menu.add_command(label="Back up database", command=self.backup_db)
        self.config(menu=menu)

    def set_filter(self, name):
        self.active_filter = name
        self.heading.config(text=name)
        for n, b in self.nav_buttons.items():
            b.config(bg=PANEL_2 if n == name else SIDEBAR)
        self.refresh()

    def refresh(self):
        rows = self.store.all()
        today = date.today()
        total = len(rows)
        done = sum(r["completed"] for r in rows)
        due_today = sum(not r["completed"] and r["due_date"] == today.isoformat() for r in rows)
        overdue = sum(not r["completed"] and r["due_date"] and r["due_date"] < today.isoformat() for r in rows)
        for k, v in [("total", total), ("done", done), ("today", due_today), ("late", overdue)]:
            self.stat_values[k].config(text=str(v))
        for item in self.tree.get_children():
            self.tree.delete(item)
        query = self.search_var.get().strip().lower()
        cat = self.category_var.get()
        filtered = []
        for r in rows:
            if self.active_filter == "Today" and (r["completed"] or r["due_date"] != today.isoformat()): continue
            if self.active_filter == "Upcoming" and (r["completed"] or not r["due_date"] or r["due_date"] <= today.isoformat()): continue
            if self.active_filter == "Completed" and not r["completed"]: continue
            if self.active_filter != "Completed" and self.active_filter != "All tasks" and r["completed"]: continue
            if cat != "All categories" and r["category"] != cat: continue
            if query and query not in (r["title"] + " " + r["notes"] + " " + r["category"]).lower(): continue
            filtered.append(r)
        if self.sort_var.get() == "Priority":
            order = {"High": 0, "Medium": 1, "Low": 2}
            filtered.sort(key=lambda r: (r["completed"], order.get(r["priority"], 1), r["due_date"]))
        elif self.sort_var.get() == "Recently added":
            filtered.sort(key=lambda r: r["created_at"], reverse=True)
        for r in filtered:
            due = r["due_date"] or "—"
            if r["due_date"] and r["due_date"] < today.isoformat() and not r["completed"]:
                due = "Overdue · " + due
            status = "✓" if r["completed"] else "○"
            self.tree.insert("", "end", iid=str(r["id"]), values=(status, r["title"], r["category"], r["priority"], due),
                             tags=("completed",) if r["completed"] else (r["priority"].lower(),))
        self.tree.tag_configure("completed", foreground=MUTED)
        self.tree.tag_configure("high", foreground=RED)
        self.tree.tag_configure("medium", foreground=YELLOW)
        self.tree.tag_configure("low", foreground=GREEN)
        self.selected_label.config(text=f"{len(filtered)} task(s) shown")

    def selection_changed(self, _=None):
        sel = self.tree.selection()
        if sel:
            self.selected_label.config(text=f"Selected task #{sel[0]}")

    def selected_task(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def open_editor(self, task_id=None):
        task = None
        if task_id:
            task = next((r for r in self.store.all() if r["id"] == task_id), None)
        win = tk.Toplevel(self)
        win.title("Edit task" if task else "Create a task")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.geometry("480x540")
        pad = tk.Frame(win, bg=BG); pad.pack(fill="both", expand=True, padx=26, pady=24)
        tk.Label(pad, text="Edit task" if task else "New task", bg=BG, fg=TEXT, font=("Segoe UI Semibold", 21)).pack(anchor="w")
        tk.Label(pad, text="Give your next action a clear name.", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 20))
        def field(label, widget):
            tk.Label(pad, text=label.upper(), bg=BG, fg=MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(9, 5))
            widget.pack(fill="x", ipady=8)
        title_var = tk.StringVar(value=task["title"] if task else "")
        title_entry = tk.Entry(pad, textvariable=title_var, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 10))
        field("Task name", title_entry)
        notes = tk.Text(pad, height=4, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 9), wrap="word")
        notes.insert("1.0", task["notes"] if task else "")
        field("Notes", notes)
        cat_var = tk.StringVar(value=task["category"] if task else "Personal")
        cat = ttk.Combobox(pad, textvariable=cat_var, state="readonly", values=["Personal", "Work", "Study", "Health", "Shopping", "Other"])
        field("Category", cat)
        priority_var = tk.StringVar(value=task["priority"] if task else "Medium")
        priority = ttk.Combobox(pad, textvariable=priority_var, state="readonly", values=["Low", "Medium", "High"])
        field("Priority", priority)
        due_var = tk.StringVar(value=task["due_date"] if task else "")
        due = tk.Entry(pad, textvariable=due_var, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 10))
        field("Due date (YYYY-MM-DD, optional)", due)
        tk.Label(pad, text="Example: 2026-12-01", bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))
        def save():
            title = title_var.get().strip()
            if not title:
                messagebox.showwarning("Missing task name", "Please enter a task name.", parent=win); return
            d = due_var.get().strip()
            if d:
                try: datetime.strptime(d, "%Y-%m-%d")
                except ValueError:
                    messagebox.showwarning("Invalid date", "Use YYYY-MM-DD, for example 2026-12-01.", parent=win); return
            self.store.save({"title": title, "notes": notes.get("1.0", "end").strip(),
                             "category": cat_var.get(), "priority": priority_var.get(), "due_date": d}, task_id)
            win.destroy(); self.refresh()
        self.button(pad, "Save task", save, True).pack(fill="x", pady=(22, 0))
        title_entry.focus_set()

    def edit_selected(self):
        task_id = self.selected_task()
        if task_id: self.open_editor(task_id)
        else: messagebox.showinfo("Select a task", "Choose a task first.")

    def toggle_selected(self):
        task_id = self.selected_task()
        if not task_id:
            messagebox.showinfo("Select a task", "Choose a task first."); return
        row = next(r for r in self.store.all() if r["id"] == task_id)
        self.store.toggle(task_id, not row["completed"])
        self.refresh()

    def delete_selected(self):
        task_id = self.selected_task()
        if not task_id:
            messagebox.showinfo("Select a task", "Choose a task first."); return
        if messagebox.askyesno("Delete task", "Delete this task permanently?"):
            self.store.delete(task_id); self.refresh()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile="focusflow_tasks.csv")
        if not path: return
        rows = self.store.all()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "notes", "category", "priority", "due_date", "completed", "created_at"])
            writer.writeheader()
            for r in rows: writer.writerow({k: r[k] for k in writer.fieldnames})
        messagebox.showinfo("Export complete", f"Exported {len(rows)} tasks.")

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path: return
        try:
            count = 0
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    if row.get("title", "").strip():
                        self.store.save({"title": row["title"].strip(), "notes": row.get("notes", ""),
                            "category": row.get("category", "Personal"), "priority": row.get("priority", "Medium"),
                            "due_date": row.get("due_date", "")})
                        count += 1
            self.refresh(); messagebox.showinfo("Import complete", f"Imported {count} tasks.")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def backup_db(self):
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite database", "*.db")], initialfile="focusflow_backup.db")
        if path:
            self.store.conn.commit()
            import shutil
            shutil.copy2(DB_PATH, path)
            messagebox.showinfo("Backup complete", "Your database backup has been saved.")

    def on_close(self):
        self.store.close()
        self.destroy()

if __name__ == "__main__":
    app = FocusFlow()
    app.mainloop()
