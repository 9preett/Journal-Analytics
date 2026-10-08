"""Tkinter user interface: Entries, Analytics and Charts tabs."""
from __future__ import annotations

import logging
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from . import analytics as an
from . import visuals
from .models import Entry, build_entry
from .sample_data import generate_entries
from .storage import JournalStorage, StorageError, export_csv, import_csv
from .validators import ValidationError, validate_date, validate_optional_date

log = logging.getLogger(__name__)
DEFAULT_CATEGORIES = ["Personal", "Study", "Work", "Health", "Travel", "Gratitude"]


class JournalApp(tk.Tk):
    """Main application window."""

    def __init__(self, data_file):
        super().__init__()
        self.title("Journal Analytics")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.storage = JournalStorage(data_file)
        self.entries: List[Entry] = []
        self.df = an.entries_to_dataframe([])
        self.selected_id: Optional[str] = None

        self._load_entries()
        self._build_menu()
        self._build_tabs()
        self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ------------------------------------------------------------------ persistence
    def _load_entries(self) -> None:
        try:
            self.entries = self.storage.load()
            if self.storage.skipped:
                messagebox.showwarning("Journal", f"{self.storage.skipped} invalid record(s) were skipped.")
        except StorageError as exc:
            messagebox.showerror("Journal file problem", str(exc))
            self.entries = []

    def _save(self) -> bool:
        try:
            self.storage.save(self.entries)
            return True
        except StorageError as exc:
            messagebox.showerror("Save failed", str(exc))
            return False

    def refresh_all(self) -> None:
        """Recompute the DataFrame and update every tab."""
        self.df = an.entries_to_dataframe(self.entries)
        self._refresh_category_choices()
        self.apply_filters()
        self.refresh_analytics()
        self.refresh_chart()
        self.status.set(f"{len(self.entries)} entries  |  file: {self.storage.path}")

    # ------------------------------------------------------------------ menu
    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Import CSV...", command=self.import_from_csv)
        file_menu.add_command(label="Export CSV...", command=self.export_to_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Load demo data", command=self.load_demo)
        file_menu.add_command(label="Delete ALL entries", command=self.clear_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo(
            "About", "Journal Analytics\nStores journal metadata and analyses writing habits.\n"
                     "Built with Python, Tkinter, Pandas, NumPy and Matplotlib."))
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _build_tabs(self) -> None:
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, relief=tk.SUNKEN, anchor="w").pack(side=tk.BOTTOM, fill=tk.X)
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.tab_entries, self.tab_analytics, self.tab_charts = (ttk.Frame(notebook) for _ in range(3))
        notebook.add(self.tab_entries, text="  Entries  ")
        notebook.add(self.tab_analytics, text="  Analytics  ")
        notebook.add(self.tab_charts, text="  Charts  ")
        self._build_entries_tab()
        self._build_analytics_tab()
        self._build_charts_tab()

    # ------------------------------------------------------------------ entries tab
    def _build_entries_tab(self) -> None:
        form = ttk.LabelFrame(self.tab_entries, text="Entry details", padding=8)
        form.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)

        self.var_date = tk.StringVar(value=date.today().isoformat())
        self.var_time = tk.StringVar(value=datetime.now().strftime("%H:%M"))
        self.var_cat = tk.StringVar()
        self.var_title = tk.StringVar()
        self.var_mood = tk.StringVar()

        rows = [("Date (YYYY-MM-DD)", ttk.Entry(form, textvariable=self.var_date, width=28)),
                ("Time (HH:MM)", ttk.Entry(form, textvariable=self.var_time, width=28))]
        self.cb_category = ttk.Combobox(form, textvariable=self.var_cat, width=26)
        rows.append(("Category", self.cb_category))
        rows.append(("Title", ttk.Entry(form, textvariable=self.var_title, width=28)))
        rows.append(("Mood 1-5 (optional)", ttk.Combobox(form, textvariable=self.var_mood, width=26,
                                                         values=["", "1", "2", "3", "4", "5"])))
        for label, widget in rows:
            ttk.Label(form, text=label).pack(anchor="w")
            widget.pack(anchor="w", pady=(0, 6))
        ttk.Label(form, text="Entry text").pack(anchor="w")
        self.txt_content = tk.Text(form, width=32, height=10, wrap="word")
        self.txt_content.pack(anchor="w", pady=(0, 8))

        buttons = ttk.Frame(form)
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Add", command=self.add_entry).grid(row=0, column=0, padx=2, pady=2)
        ttk.Button(buttons, text="Update", command=self.update_entry).grid(row=0, column=1, padx=2, pady=2)
        ttk.Button(buttons, text="Delete", command=self.delete_entry).grid(row=0, column=2, padx=2, pady=2)
        ttk.Button(buttons, text="Clear form", command=self.clear_form).grid(row=1, column=0, columnspan=3, pady=2)

        right = ttk.Frame(self.tab_entries)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        bar = ttk.LabelFrame(right, text="Search / filter", padding=6)
        bar.pack(fill=tk.X)
        self.f_keyword, self.f_cat = tk.StringVar(), tk.StringVar(value="All")
        self.f_start, self.f_end = tk.StringVar(), tk.StringVar()
        ttk.Label(bar, text="Keyword").grid(row=0, column=0, sticky="w")
        ttk.Entry(bar, textvariable=self.f_keyword, width=20).grid(row=1, column=0, padx=3)
        ttk.Label(bar, text="Category").grid(row=0, column=1, sticky="w")
        self.cb_filter_cat = ttk.Combobox(bar, textvariable=self.f_cat, width=14, state="readonly")
        self.cb_filter_cat.grid(row=1, column=1, padx=3)
        ttk.Label(bar, text="From (YYYY-MM-DD)").grid(row=0, column=2, sticky="w")
        ttk.Entry(bar, textvariable=self.f_start, width=14).grid(row=1, column=2, padx=3)
        ttk.Label(bar, text="To (YYYY-MM-DD)").grid(row=0, column=3, sticky="w")
        ttk.Entry(bar, textvariable=self.f_end, width=14).grid(row=1, column=3, padx=3)
        ttk.Button(bar, text="Apply", command=self.apply_filters).grid(row=1, column=4, padx=3)
        ttk.Button(bar, text="Reset", command=self.reset_filters).grid(row=1, column=5, padx=3)

        columns = ("date", "time", "category", "title", "words", "mood")
        self.tree = ttk.Treeview(right, columns=columns, show="headings", selectmode="browse")
        for col, width in zip(columns, (90, 55, 100, 280, 60, 50)):
            self.tree.heading(col, text=col.title(), command=lambda c=col: self._sort_tree(c))
            self.tree.column(col, width=width, anchor="w")
        scroll = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(8, 0))
        scroll.pack(side=tk.LEFT, fill=tk.Y, pady=(8, 0))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._sort_state = {}

    def _form_to_entry(self, entry_id: Optional[str] = None) -> Entry:
        return build_entry(self.var_date.get(), self.var_time.get(), self.var_cat.get(),
                           self.var_title.get(), self.txt_content.get("1.0", tk.END),
                           self.var_mood.get(), entry_id)

    def add_entry(self) -> None:
        try:
            entry = self._form_to_entry()
        except ValidationError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return
        self.entries.append(entry)
        if self._save():
            self.clear_form()
            self.refresh_all()

    def update_entry(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("Update", "Select an entry in the table first.")
            return
        try:
            new = self._form_to_entry(self.selected_id)
        except ValidationError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return
        self.entries = [new if e.id == self.selected_id else e for e in self.entries]
        if self._save():
            self.refresh_all()

    def delete_entry(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("Delete", "Select an entry in the table first.")
            return
        if not messagebox.askyesno("Delete", "Delete the selected entry?"):
            return
        self.entries = [e for e in self.entries if e.id != self.selected_id]
        if self._save():
            self.clear_form()
            self.refresh_all()

    def clear_form(self) -> None:
        self.selected_id = None
        self.var_date.set(date.today().isoformat())
        self.var_time.set(datetime.now().strftime("%H:%M"))
        self.var_cat.set("")
        self.var_title.set("")
        self.var_mood.set("")
        self.txt_content.delete("1.0", tk.END)

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = selection[0]  # Treeview iid == entry id
        entry = next((e for e in self.entries if e.id == self.selected_id), None)
        if entry is None:
            return
        self.var_date.set(entry.date)
        self.var_time.set(entry.time)
        self.var_cat.set(entry.category)
        self.var_title.set(entry.title)
        self.var_mood.set("" if entry.mood is None else str(entry.mood))
        self.txt_content.delete("1.0", tk.END)
        self.txt_content.insert("1.0", entry.content)

    def _refresh_category_choices(self) -> None:
        existing = sorted(set(DEFAULT_CATEGORIES) | {e.category for e in self.entries})
        self.cb_category["values"] = existing
        self.cb_filter_cat["values"] = ["All"] + existing

    def apply_filters(self) -> None:
        try:
            start = validate_optional_date(self.f_start.get())
            end = validate_optional_date(self.f_end.get())
        except ValidationError as exc:
            messagebox.showerror("Invalid filter", str(exc))
            return
        if start and end and start > end:
            messagebox.showerror("Invalid filter", "'From' date must not be after 'To' date.")
            return
        result = an.filter_entries(self.df, self.f_keyword.get(), self.f_cat.get(), start, end)
        self.tree.delete(*self.tree.get_children())
        for row in result.sort_values(["date", "time"], ascending=False).itertuples():
            mood = "" if row.mood != row.mood else int(row.mood)  # NaN check
            self.tree.insert("", tk.END, iid=row.id, values=(
                row.date.date().isoformat(), row.time, row.category, row.title, row.word_count, mood))
        self.status.set(f"Showing {len(result)} of {len(self.entries)} entries  |  file: {self.storage.path}")

    def reset_filters(self) -> None:
        self.f_keyword.set("")
        self.f_cat.set("All")
        self.f_start.set("")
        self.f_end.set("")
        self.apply_filters()

    def _sort_tree(self, column: str) -> None:
        reverse = self._sort_state.get(column, False)
        items = [(self.tree.set(i, column), i) for i in self.tree.get_children("")]
        try:
            items.sort(key=lambda t: float(t[0]) if t[0] != "" else -1, reverse=reverse)
        except ValueError:
            items.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for index, (_, iid) in enumerate(items):
            self.tree.move(iid, "", index)
        self._sort_state[column] = not reverse

    # ------------------------------------------------------------------ analytics tab
    def _build_analytics_tab(self) -> None:
        top = ttk.LabelFrame(self.tab_analytics, text="Insights", padding=6)
        top.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.txt_summary = tk.Text(top, height=14, wrap="word", state="disabled", font=("Consolas", 10))
        self.txt_summary.pack(fill=tk.BOTH, expand=True)

        mid = ttk.LabelFrame(self.tab_analytics, text="Compare categories", padding=6)
        mid.pack(fill=tk.X, padx=6, pady=3)
        cols = ("entries", "share %", "avg words", "avg mood")
        self.tree_cat = ttk.Treeview(mid, columns=cols, show="tree headings", height=6)
        self.tree_cat.heading("#0", text="Category")
        self.tree_cat.column("#0", width=160)
        for c in cols:
            self.tree_cat.heading(c, text=c.title())
            self.tree_cat.column(c, width=100, anchor="center")
        self.tree_cat.pack(fill=tk.X)

        bottom = ttk.LabelFrame(self.tab_analytics, text="Compare two periods", padding=6)
        bottom.pack(fill=tk.X, padx=6, pady=6)
        today = date.today()
        self.p = {k: tk.StringVar(value=v.isoformat()) for k, v in {
            "a_start": today - timedelta(days=59), "a_end": today - timedelta(days=30),
            "b_start": today - timedelta(days=29), "b_end": today}.items()}
        for col, (label, key) in enumerate([("A from", "a_start"), ("A to", "a_end"),
                                            ("B from", "b_start"), ("B to", "b_end")]):
            ttk.Label(bottom, text=label).grid(row=0, column=col, sticky="w", padx=3)
            ttk.Entry(bottom, textvariable=self.p[key], width=13).grid(row=1, column=col, padx=3)
        ttk.Button(bottom, text="Compare", command=self.compare_periods).grid(row=1, column=4, padx=8)
        self.lbl_compare = tk.Text(bottom, height=8, state="disabled", font=("Consolas", 10))
        self.lbl_compare.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(6, 0))

    @staticmethod
    def _set_text(widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def refresh_analytics(self) -> None:
        self._set_text(self.txt_summary, an.summary_text(self.df))
        self.tree_cat.delete(*self.tree_cat.get_children())
        for cat, row in an.compare_categories(self.df).iterrows():
            mood = "-" if row["avg_mood"] != row["avg_mood"] else f"{row['avg_mood']:.2f}"
            self.tree_cat.insert("", tk.END, text=cat, values=(
                int(row["entries"]), f"{row['share_pct']:.1f}", f"{row['avg_words']:.0f}", mood))

    def compare_periods(self) -> None:
        try:
            d = {k: validate_date(var.get(), allow_future=True) for k, var in self.p.items()}
            if d["a_start"] > d["a_end"] or d["b_start"] > d["b_end"]:
                raise ValidationError("In each period the start date must not be after the end date.")
        except ValidationError as exc:
            messagebox.showerror("Invalid period", str(exc))
            return
        table = an.compare_periods(self.df, d["a_start"], d["a_end"], d["b_start"], d["b_end"])
        lines = [f"{'metric':<18}{'Period A':>12}{'Period B':>12}{'change':>10}"]
        for metric, row in table.iterrows():
            change = "" if row["change"] != row["change"] or row["change"] is None else f"{row['change']:+}"
            lines.append(f"{metric:<18}{str(row['period_A']):>12}{str(row['period_B']):>12}{change:>10}")
        self._set_text(self.lbl_compare, "\n".join(lines))

    # ------------------------------------------------------------------ charts tab
    def _build_charts_tab(self) -> None:
        bar = ttk.Frame(self.tab_charts)
        bar.pack(fill=tk.X, padx=6, pady=6)
        ttk.Label(bar, text="Report:").pack(side=tk.LEFT)
        self.var_chart = tk.StringVar(value=list(visuals.CHARTS)[0])
        combo = ttk.Combobox(bar, textvariable=self.var_chart, values=list(visuals.CHARTS),
                             state="readonly", width=36)
        combo.pack(side=tk.LEFT, padx=6)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_chart())
        ttk.Button(bar, text="Save as PNG...", command=self.save_chart).pack(side=tk.LEFT, padx=6)
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.tab_charts)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    def refresh_chart(self) -> None:
        try:
            visuals.CHARTS[self.var_chart.get()](self.df, self.figure)
            self.canvas.draw_idle()
        except Exception:  # keep the app alive if a chart fails; details go to the log
            log.exception("Chart failed")
            messagebox.showerror("Chart error", "Could not draw this chart. See journal.log for details.")

    def save_chart(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG image", "*.png")])
        if not path:
            return
        try:
            self.figure.savefig(path, dpi=150)
            messagebox.showinfo("Saved", f"Chart saved to {path}")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))

    # ------------------------------------------------------------------ file menu actions
    def import_from_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            new_entries, skipped = import_csv(path)
        except StorageError as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        known = {e.id for e in self.entries}
        added = [e for e in new_entries if e.id not in known]
        self.entries.extend(added)
        if self._save():
            self.refresh_all()
            messagebox.showinfo("Import", f"Imported {len(added)} entries "
                                          f"({len(new_entries) - len(added)} duplicates, {skipped} invalid skipped).")

    def export_to_csv(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            export_csv(self.entries, path)
            messagebox.showinfo("Export", f"Exported {len(self.entries)} entries to {path}")
        except StorageError as exc:
            messagebox.showerror("Export failed", str(exc))

    def load_demo(self) -> None:
        if self.entries and not messagebox.askyesno(
                "Demo data", "Add demo entries to your existing journal?"):
            return
        self.entries.extend(generate_entries())
        if self._save():
            self.refresh_all()

    def clear_all(self) -> None:
        if self.entries and messagebox.askyesno("Delete all", "Permanently delete ALL entries?"):
            self.entries = []
            if self._save():
                self.clear_form()
                self.refresh_all()
