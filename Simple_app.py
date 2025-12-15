
import csv
import hashlib
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


DB_PATH = Path(__file__).with_name("library.db")


def hash_password(raw: str) -> str:
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class LibraryDB:
	def __init__(self, db_path: Path):
		self.db_path = db_path
		self._ensure_db()

	def _ensure_db(self) -> None:
		con = sqlite3.connect(self.db_path)
		cur = con.cursor()
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS users (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				username TEXT UNIQUE NOT NULL,
				password_hash TEXT NOT NULL
			)
			"""
		)
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS books (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				title TEXT NOT NULL,
				author TEXT NOT NULL,
				category TEXT,
				year INTEGER,
				copies INTEGER DEFAULT 1,
				available INTEGER DEFAULT 1,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
			)
			"""
		)
		con.commit()
		if not self._user_exists(cur, "admin"):
			cur.execute(
				"INSERT INTO users (username, password_hash) VALUES (?, ?)",
				("admin", hash_password("admin")),
			)
			con.commit()
		con.close()

	@staticmethod
	def _user_exists(cur: sqlite3.Cursor, username: str) -> bool:
		cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
		return cur.fetchone() is not None

	def verify_user(self, username: str, password: str) -> bool:
		con = sqlite3.connect(self.db_path)
		cur = con.cursor()
		cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
		row = cur.fetchone()
		con.close()
		if not row:
			return False
		return row[0] == hash_password(password)

	def add_book(self, payload: dict) -> None:
		con = sqlite3.connect(self.db_path)
		cur = con.cursor()
		cur.execute(
			"""
			INSERT INTO books (title, author, category, year, copies, available)
			VALUES (:title, :author, :category, :year, :copies, :available)
			""",
			payload,
		)
		con.commit()
		con.close()

	def update_book(self, book_id: int, payload: dict) -> None:
		con = sqlite3.connect(self.db_path)
		cur = con.cursor()
		payload["id"] = book_id
		cur.execute(
			"""
			UPDATE books
			SET title=:title, author=:author, category=:category,
				year=:year, copies=:copies, available=:available
			WHERE id=:id
			""",
			payload,
		)
		con.commit()
		con.close()

	def delete_book(self, book_id: int) -> None:
		con = sqlite3.connect(self.db_path)
		cur = con.cursor()
		cur.execute("DELETE FROM books WHERE id=?", (book_id,))
		con.commit()
		con.close()

	def fetch_books(self, search: str = "") -> list[tuple]:
		con = sqlite3.connect(self.db_path)
		cur = con.cursor()
		if search:
			like = f"%{search.lower()}%"
			cur.execute(
				"""
				SELECT id, title, author, category, year, copies, available, created_at
				FROM books
				WHERE lower(title) LIKE ? OR lower(author) LIKE ? OR lower(category) LIKE ?
				ORDER BY created_at DESC
				""",
				(like, like, like),
			)
		else:
			cur.execute(
				"""
				SELECT id, title, author, category, year, copies, available, created_at
				FROM books
				ORDER BY created_at DESC
				"""
			)
		rows = cur.fetchall()
		con.close()
		return rows

	def summary(self) -> dict:
		con = sqlite3.connect(self.db_path)
		cur = con.cursor()
		cur.execute("SELECT COUNT(*), SUM(available), SUM(copies) FROM books")
		total, available, copies = cur.fetchone()
		cur.execute("SELECT COUNT(*) FROM books WHERE available=0")
		issued = cur.fetchone()[0]
		con.close()
		return {
			"total": total or 0,
			"available": available or 0,
			"copies": copies or 0,
			"issued": issued or 0,
		}


class LibraryApp(tk.Tk):
	def __init__(self) -> None:
		super().__init__()
		self.title("Library Manager")
		self.geometry("1050x650")
		self.resizable(False, False)
		self.db = LibraryDB(DB_PATH)
		self.theme = tk.StringVar(value="light")
		self._configure_styles()
		self._build_login()

	def _configure_styles(self) -> None:
		self.style = ttk.Style(self)
		self.light_palette = {
			"bg": "#f7f7fa",
			"panel": "#ffffff",
			"fg": "#222222",
			"accent": "#2d7dd2",
			"border": "#d8d8e0",
		}
		self.dark_palette = {
			"bg": "#12141b",
			"panel": "#1c1f2a",
			"fg": "#e9ecf5",
			"accent": "#7cb7ff",
			"border": "#2d3346",
		}
		self.apply_palette(self.light_palette)

	def apply_palette(self, palette: dict) -> None:
		self.configure(bg=palette["bg"])
		self.style.configure("TFrame", background=palette["panel"], borderwidth=1, relief="solid")
		self.style.configure("TLabel", background=palette["panel"], foreground=palette["fg"], font=("Segoe UI", 10))
		self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
		self.style.configure("TButton", font=("Segoe UI", 10), padding=6)
		self.style.map("TButton", background=[("active", palette["accent"]), ("pressed", palette["accent"])], foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
		self.style.configure("Treeview", background=palette["panel"], fieldbackground=palette["panel"], foreground=palette["fg"], bordercolor=palette["border"])
		self.style.configure("Treeview.Heading", background=palette["panel"], foreground=palette["fg"], relief="flat")

	def _build_login(self) -> None:
		self.login_frame = ttk.Frame(self, padding=24)
		self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

		ttk.Label(self.login_frame, text="Library Manager", style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 12))
		ttk.Label(self.login_frame, text="Username").grid(row=1, column=0, sticky="w")
		ttk.Label(self.login_frame, text="Password").grid(row=2, column=0, sticky="w", pady=(6, 0))

		self.username_var = tk.StringVar()
		self.password_var = tk.StringVar()
		username_entry = ttk.Entry(self.login_frame, textvariable=self.username_var, width=28)
		password_entry = ttk.Entry(self.login_frame, textvariable=self.password_var, show="*", width=28)
		username_entry.grid(row=1, column=1, pady=4)
		password_entry.grid(row=2, column=1, pady=4)

		login_btn = ttk.Button(self.login_frame, text="Login", command=self.handle_login)
		login_btn.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="ew")
		self.bind("<Return>", lambda _event: self.handle_login())

	def handle_login(self) -> None:
		username = self.username_var.get().strip()
		password = self.password_var.get()
		if not username or not password:
			messagebox.showwarning("Missing fields", "Enter both username and password")
			return
		if not self.db.verify_user(username, password):
			messagebox.showerror("Login failed", "Invalid credentials")
			return
		self.login_frame.destroy()
		self._build_main_ui()

	def _build_main_ui(self) -> None:
		palette = self.light_palette if self.theme.get() == "light" else self.dark_palette
		self.configure(bg=palette["bg"])

		self.topbar = ttk.Frame(self, padding=12)
		self.topbar.pack(fill="x", padx=12, pady=(12, 6))
		ttk.Label(self.topbar, text="Library Dashboard", style="Header.TLabel").pack(side="left")
		ttk.Button(self.topbar, text="Toggle Theme", command=self.toggle_theme).pack(side="right", padx=6)
		ttk.Button(self.topbar, text="Export CSV", command=self.export_csv).pack(side="right", padx=6)

		self.body = ttk.Frame(self, padding=12)
		self.body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

		self.left_panel = ttk.Frame(self.body, padding=12)
		self.left_panel.pack(side="left", fill="y")
		self.right_panel = ttk.Frame(self.body, padding=12)
		self.right_panel.pack(side="right", fill="both", expand=True)

		self._build_stats(self.left_panel)
		self._build_form(self.left_panel)
		self._build_table(self.right_panel)
		self.refresh_table()
		self.update_stats()

	def toggle_theme(self) -> None:
		if self.theme.get() == "light":
			self.theme.set("dark")
			self.apply_palette(self.dark_palette)
		else:
			self.theme.set("light")
			self.apply_palette(self.light_palette)
		self.update_idletasks()

	def _build_stats(self, parent: ttk.Frame) -> None:
		stats_frame = ttk.Frame(parent, padding=12)
		stats_frame.pack(fill="x", pady=(0, 12))
		ttk.Label(stats_frame, text="Overview", style="Header.TLabel").pack(anchor="w")
		self.stat_total = ttk.Label(stats_frame, text="Total books: 0")
		self.stat_available = ttk.Label(stats_frame, text="Available copies: 0")
		self.stat_issued = ttk.Label(stats_frame, text="Issued titles: 0")
		self.stat_total.pack(anchor="w", pady=2)
		self.stat_available.pack(anchor="w", pady=2)
		self.stat_issued.pack(anchor="w", pady=2)

	def _build_form(self, parent: ttk.Frame) -> None:
		form = ttk.Frame(parent, padding=12)
		form.pack(fill="both", expand=False)
		ttk.Label(form, text="Manage Books", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

		labels = ["Title", "Author", "Category", "Year", "Copies", "Available"]
		self.form_vars = {name: tk.StringVar() for name in labels}
		for idx, name in enumerate(labels, start=1):
			ttk.Label(form, text=name).grid(row=idx, column=0, sticky="w", pady=4)
			entry = ttk.Entry(form, textvariable=self.form_vars[name], width=26)
			entry.grid(row=idx, column=1, pady=4)
		self.form_vars["Available"].set("1")

		btn_frame = ttk.Frame(form)
		btn_frame.grid(row=len(labels) + 1, column=0, columnspan=2, pady=(8, 0))
		ttk.Button(btn_frame, text="Add", command=self.add_book).pack(side="left", padx=4)
		ttk.Button(btn_frame, text="Update", command=self.update_selected).pack(side="left", padx=4)
		ttk.Button(btn_frame, text="Delete", command=self.delete_selected).pack(side="left", padx=4)
		ttk.Button(btn_frame, text="Clear", command=self.clear_form).pack(side="left", padx=4)

	def _build_table(self, parent: ttk.Frame) -> None:
		top = ttk.Frame(parent)
		top.pack(fill="x", pady=(0, 8))
		ttk.Label(top, text="Books", style="Header.TLabel").pack(side="left")
		ttk.Label(top, text="Search:").pack(side="left", padx=(16, 4))
		self.search_var = tk.StringVar()
		search_entry = ttk.Entry(top, textvariable=self.search_var, width=30)
		search_entry.pack(side="left")
		search_entry.bind("<KeyRelease>", lambda _e: self.refresh_table())

		columns = ("id", "title", "author", "category", "year", "copies", "available", "created")
		self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=22)
		headings = {
			"id": "ID",
			"title": "Title",
			"author": "Author",
			"category": "Category",
			"year": "Year",
			"copies": "Copies",
			"available": "Available",
			"created": "Created",
		}
		for key, text in headings.items():
			self.tree.heading(key, text=text, command=lambda c=key: self.sort_by_column(c, False))
			self.tree.column(key, width=110 if key != "title" else 200, anchor="center")
		self.tree.pack(fill="both", expand=True)
		self.tree.bind("<<TreeviewSelect>>", self.on_select)

		scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
		self.tree.configure(yscrollcommand=scrollbar.set)
		scrollbar.pack(side="right", fill="y")

	def refresh_table(self) -> None:
		search = self.search_var.get().strip()
		for row in self.tree.get_children():
			self.tree.delete(row)
		for row in self.db.fetch_books(search):
			self.tree.insert("", "end", values=row)
		self.update_stats()

	def on_select(self, _event=None) -> None:
		selected = self.tree.focus()
		if not selected:
			return
		values = self.tree.item(selected, "values")
		keys = ["ID", "Title", "Author", "Category", "Year", "Copies", "Available", "Created"]
		data = dict(zip(keys, values))
		self.selected_id = int(data["ID"])
		self.form_vars["Title"].set(data["Title"])
		self.form_vars["Author"].set(data["Author"])
		self.form_vars["Category"].set(data["Category"])
		self.form_vars["Year"].set(data["Year"])
		self.form_vars["Copies"].set(data["Copies"])
		self.form_vars["Available"].set(data["Available"])

	def _form_payload(self) -> dict | None:
		title = self.form_vars["Title"].get().strip()
		author = self.form_vars["Author"].get().strip()
		category = self.form_vars["Category"].get().strip()
		year = self.form_vars["Year"].get().strip()
		copies = self.form_vars["Copies"].get().strip() or "0"
		available = self.form_vars["Available"].get().strip() or "0"
		if not title or not author:
			messagebox.showwarning("Missing data", "Title and Author are required")
			return None
		try:
			year_val = int(year) if year else None
			copies_val = max(0, int(copies))
			available_val = max(0, min(int(available), copies_val))
		except ValueError:
			messagebox.showerror("Invalid number", "Year, Copies, Available must be numbers")
			return None
		return {
			"title": title,
			"author": author,
			"category": category,
			"year": year_val,
			"copies": copies_val,
			"available": available_val,
		}

	def add_book(self) -> None:
		payload = self._form_payload()
		if not payload:
			return
		self.db.add_book(payload)
		self.clear_form()
		self.refresh_table()
		messagebox.showinfo("Added", "Book added successfully")

	def update_selected(self) -> None:
		if not hasattr(self, "selected_id"):
			messagebox.showwarning("Select a row", "Choose a book to update")
			return
		payload = self._form_payload()
		if not payload:
			return
		self.db.update_book(self.selected_id, payload)
		self.refresh_table()
		messagebox.showinfo("Updated", "Book updated")

	def delete_selected(self) -> None:
		if not hasattr(self, "selected_id"):
			messagebox.showwarning("Select a row", "Choose a book to delete")
			return
		if not messagebox.askyesno("Confirm", "Delete this book? This cannot be undone."):
			return
		self.db.delete_book(self.selected_id)
		self.clear_form()
		self.refresh_table()

	def clear_form(self) -> None:
		for var in self.form_vars.values():
			var.set("")
		self.form_vars["Available"].set("1")
		if hasattr(self, "selected_id"):
			delattr(self, "selected_id")

	def update_stats(self) -> None:
		stats = self.db.summary()
		self.stat_total.config(text=f"Total books: {stats['total']}")
		self.stat_available.config(text=f"Available copies: {stats['available']}")
		self.stat_issued.config(text=f"Issued titles: {stats['issued']}")

	def sort_by_column(self, col: str, reverse: bool) -> None:
		data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
		try:
			data.sort(key=lambda t: int(t[0]), reverse=reverse)
		except ValueError:
			data.sort(key=lambda t: t[0].lower(), reverse=reverse)
		for index, (_, k) in enumerate(data):
			self.tree.move(k, "", index)
		self.tree.heading(col, command=lambda: self.sort_by_column(col, not reverse))

	def export_csv(self) -> None:
		rows = self.db.fetch_books(self.search_var.get().strip())
		if not rows:
			messagebox.showinfo("No data", "No rows to export")
			return
		csv_path = DB_PATH.with_suffix(".csv")
		with open(csv_path, "w", newline="", encoding="utf-8") as fh:
			writer = csv.writer(fh)
			writer.writerow(["ID", "Title", "Author", "Category", "Year", "Copies", "Available", "Created"])
			writer.writerows(rows)
		messagebox.showinfo("Exported", f"Data exported to {csv_path}")


if __name__ == "__main__":
	app = LibraryApp()
	app.mainloop()
