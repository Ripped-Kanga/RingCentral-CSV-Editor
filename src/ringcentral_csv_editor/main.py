#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = ""
__version__ = "0.8.5"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"
__disclaimer__ = ""

import sys
import os
import logging
from collections.abc import Iterable
from datetime import datetime
from importlib import resources
from pathlib import Path
from .helper.csv_helper import RingCentralCSV
from textual.app import App, ComposeResult, Binding
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, HorizontalGroup, VerticalScroll
from textual.widgets import Footer, Header, Input, Button, Static, Label, DataTable, DirectoryTree

# Standard RingCentral Global Address Book column order
RINGCENTRAL_FIELDNAMES: tuple[str, ...] = (
	"First Name",
	"Surname",
	"Job Title",
	"Company",
	"Email",
	"Home Number",
	"Business Number",
	"Mobile Number",
	"Company Main Number",
	"Source",
	"External Id",
)

class HelpScreen(ModalScreen[None]):
	def compose(self) -> ComposeResult:

		with Vertical(id="help_modal"):
			yield Static(
				"RingCentral CSV Editor — Help\n\n"
				"Navigation\n"
				"  ↑/↓   Move row cursor\n\n"
				"Shortcuts\n"
				"  n     New Address Book (blank sheet with standard headers)\n"
				"  r     Read CSV (only when a .csv is selected)\n"
				"  a     Append Row (requires headers loaded)\n"
				"  e     Edit Row (requires rows loaded)\n"
				"  d     Delete Row (requires rows; deletes selected row)\n"
				"  f     Toggle Duplicates-only view\n"
				"  w     Write CSV (timestamped output)\n"
				"  ?     Open this help screen\n"
				"  q     Quit\n\n"
				"File Import\n"
				"  - Type or paste a .csv file path and press Enter to load it.\n"
				"  - In most terminal emulators you can drag a file onto the window\n"
				"    to paste its path directly into the input box.\n\n"
				"Notes\n"
				"  - Duplicate numbers are allowed on import, but shown via warnings.\n"
				"  - Appending and editing block duplicates.\n"
				"What does this do?\n"
				"This tool is designed to ease the editing of RingCentrals Global Address  Book csv file.\n"
				"It has built in format normalisation tools to auto format fields so that they align with\n"
				"what RingCentral expects.",
				id="help_text",
			)
			yield Button("Close", id="close_help", variant="primary")

	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "close_help":
			self.dismiss(None)

	def on_mount(self) -> None:
		help_modal = self.query_one("#help_modal", Vertical)
		help_modal.border_title = "Help"



class AddRowScreen(ModalScreen[dict | None]):
	"""
	Collect a new row via Inputs; return dict on Save, None on Cancel.
	"""

	def __init__(self, fieldnames: list[str]):
		super().__init__()
		self.fieldnames = fieldnames
		self._inputs: dict[str, Input] = {}

	def compose(self) -> ComposeResult:
		with Vertical(id="add_row_modal"):
			yield Label("Add Row", id="add_row_title")

			with VerticalScroll(id="add_row_form"):
				for i, field in enumerate(self.fieldnames):
					with Horizontal(classes="add_row_line"):
						yield Label(field, classes="add_row_label")
						inp = Input(placeholder="(blank allowed)", id=f"f_{i}")
						self._inputs[field] = inp
						yield inp

			with Horizontal(id="add_row_buttons"):
				yield Button("Save", id="save_row", variant="primary")
				yield Button("Cancel", id="cancel_row", variant="default")

	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "cancel_row":
			self.dismiss(None)
			return

		if event.button.id != "save_row":
			return

		rc = RingCentralCSV()
		rc.fieldnames = self.fieldnames  # so formatter uses same names if needed

		new_entry: dict[str, str] = {}
		for field, inp in self._inputs.items():
			raw = (inp.value or "").strip()
			try:
				new_entry[field] = rc.field_formatter(field, raw)
			except ValueError as e:
				# Show error and focus the offending input
				self.app.notify(f"{field}: {e}")
				inp.focus()
				return

		self.dismiss(new_entry)


class EditRowScreen(ModalScreen[dict | None]):
	"""
	Pre-populated form for editing an existing row.
	Returns validated dict on Save, None on Cancel.
	All field_formatter sanitisation rules apply identically to AddRowScreen.
	"""

	def __init__(self, fieldnames: list[str], current_row: dict):
		super().__init__()
		self.fieldnames = fieldnames
		self.current_row = current_row
		self._inputs: dict[str, Input] = {}

	def compose(self) -> ComposeResult:
		with Vertical(id="add_row_modal"):
			yield Label("Edit Row", id="add_row_title")

			with VerticalScroll(id="add_row_form"):
				for i, field in enumerate(self.fieldnames):
					with Horizontal(classes="add_row_line"):
						yield Label(field, classes="add_row_label")
						inp = Input(
							value=str(self.current_row.get(field, "") or ""),
							placeholder="(blank allowed)",
							id=f"ef_{i}",
						)
						self._inputs[field] = inp
						yield inp

			with Horizontal(id="add_row_buttons"):
				yield Button("Save", id="save_row", variant="primary")
				yield Button("Cancel", id="cancel_row", variant="default")

	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "cancel_row":
			self.dismiss(None)
			return

		if event.button.id != "save_row":
			return

		rc = RingCentralCSV()
		rc.fieldnames = self.fieldnames

		new_entry: dict[str, str] = {}
		for field, inp in self._inputs.items():
			raw = (inp.value or "").strip()
			try:
				new_entry[field] = rc.field_formatter(field, raw)
			except ValueError as e:
				self.app.notify(f"{field}: {e}")
				inp.focus()
				return

		self.dismiss(new_entry)

	def on_mount(self) -> None:
		self.query_one("#add_row_modal", Vertical).border_title = "Edit Row"


class VisibleDirectoryTree(DirectoryTree):
	"""DirectoryTree that hides dotfiles and hidden directories."""

	def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
		return [p for p in paths if not p.name.startswith(".")]


class WriteDirectoryScreen(ModalScreen[Path | None]):
	"""
	Browse and confirm an output directory before writing the CSV.
	Clicking a directory or file (uses its parent) updates the path input.
	The user can also type a path directly. Dismisses with the chosen Path or None.
	"""

	def __init__(self, default_dir: Path):
		super().__init__()
		self._selected_dir = default_dir
		self._default_filename = f"AddressBook-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"

	def compose(self) -> ComposeResult:
		with Vertical(id="write_dir_modal"):
			yield Label("Output directory:", id="write_dir_label")
			yield Input(value=str(self._selected_dir), id="write_dir_input")
			with VerticalScroll(id="write_dir_tree_box"):
				yield VisibleDirectoryTree(str(Path.home()), id="write_dir_tree")
			yield Label("Filename:", id="write_dir_filename_label")
			yield Input(value=self._default_filename, id="write_dir_filename")
			with Horizontal(id="add_row_buttons"):
				yield Button("Save here", id="save_dir", variant="primary")
				yield Button("Cancel", id="cancel_dir", variant="default")

	def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
		self._selected_dir = event.path
		self.query_one("#write_dir_input", Input).value = str(event.path)
		event.stop()

	def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
		# When a file is clicked, use its parent directory
		self._selected_dir = event.path.parent
		self.query_one("#write_dir_input", Input).value = str(event.path.parent)
		event.stop()

	def on_input_changed(self, event: Input.Changed) -> None:
		if event.input.id == "write_dir_input":
			raw = event.value.strip()
			self._selected_dir = Path(raw).expanduser() if raw else Path.cwd()

	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "cancel_dir":
			self.dismiss(None)
			return
		if event.button.id == "save_dir":
			dir_raw = self.query_one("#write_dir_input", Input).value.strip()
			if not dir_raw:
				self.app.notify("Enter a directory path")
				return
			name_raw = self.query_one("#write_dir_filename", Input).value.strip() or self._default_filename
			if not name_raw.lower().endswith(".csv"):
				name_raw += ".csv"
			self.dismiss(Path(dir_raw).expanduser() / name_raw)

	def on_mount(self) -> None:
		self.query_one("#write_dir_modal", Vertical).border_title = "Save to Directory"


class ImportRingCentralCSV(HorizontalGroup):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.selected_path: Path | None = None
		self.csv_data: list[dict] = []
		self.fieldnames: list[str] = []
		self.show_dupes_only: bool = False


	def compose(self) -> ComposeResult:
		with Vertical(id="sidebar_box"):
			yield Label(f"RingCentral CSV Editor - {__version__}", id="title_block")

			with Vertical(id="file_operations_box"):
				yield Button("New Address Book", id="new_address_book", variant="default")
				yield Button("Read CSV", id="read_csv", variant="default", disabled=True)
				yield Button("Append Row", id="append_csv", variant="default", disabled=True)
				yield Button("Edit Row", id="edit_row", variant="default", disabled=True)
				yield Button("Delete Row", id="delete_row", variant="default", disabled=True)
				yield Button("Write CSV", id="write_csv", variant="default", disabled=True)

			with Vertical(id="directory_box"):
				yield Label(
					"Type or paste a .csv path and press Enter, or Browse:",
					id="file_path_label",
				)
				yield Input(placeholder="/path/to/AddressBook.csv", id="file_path_input")
				yield Button("Browse...", id="browse_file", variant="default")

		with Vertical(id="csv_viewer", classes="content_box"):
			yield Static("No file selected:", id="selected_path", classes="sub-header")
			yield Static("", id="file_update", classes="sub-header")
			with VerticalScroll(id="csv_browser"):
				yield DataTable(id="csv_table")

	# ---------------- Rules ----------------

	def can_read_csv(self) -> bool:
		p = self.selected_path
		return bool(p and p.exists() and p.suffix.lower() == ".csv")

	def can_append_csv(self) -> bool:
		return bool(self.fieldnames)

	def can_edit_row(self) -> bool:
		return bool(self.csv_data)

	def can_delete_row(self) -> bool:
		return bool(self.csv_data)

	def can_write_csv(self) -> bool:
		return bool(self.fieldnames)

	def refresh_controls(self) -> None:
		self.query_one("#read_csv", Button).disabled = not self.can_read_csv()
		self.query_one("#append_csv", Button).disabled = not self.can_append_csv()
		self.query_one("#edit_row", Button).disabled = not self.can_edit_row()
		self.query_one("#delete_row", Button).disabled = not self.can_delete_row()
		self.query_one("#write_csv", Button).disabled = not self.can_write_csv()

	# ---------------- File path input events ----------------

	def on_input_changed(self, event: Input.Changed) -> None:
		if event.input.id != "file_path_input":
			return
		raw = event.value.strip().strip('"').strip("'")
		self.selected_path = Path(raw).expanduser() if raw else None
		self.refresh_controls()

	def on_input_submitted(self, event: Input.Submitted) -> None:
		if event.input.id != "file_path_input":
			return
		raw = event.value.strip().strip('"').strip("'")
		if not raw:
			return

		path = Path(raw).expanduser()
		self.selected_path = path
		self.query_one("#selected_path", Static).update(f"File: {path.name}")

		if path.suffix.lower() != ".csv":
			self.app.notify("Not a .csv file — pick a .csv to load")
			self.refresh_controls()
			return

		if not path.exists():
			self.app.notify(f"File not found: {path}")
			self.refresh_controls()
			return

		self.refresh_controls()
		self.do_read_csv()

	# ---------------- Buttons forward to the same actions ----------------

	def on_button_pressed(self, event: Button.Pressed) -> None:
		btn = event.button.id

		if btn == "new_address_book":
			self.do_new_address_book()
			return

		if btn == "read_csv":
			self.do_read_csv()
			return

		if btn == "append_csv":
			self.do_append_csv()
			return

		if btn == "edit_row":
			self.do_edit_row()
			return

		if btn == "delete_row":
			self.do_delete_row()
			return

		if btn == "write_csv":
			self.do_write_csv()
			return

		if btn == "browse_file":
			self.do_browse_file()
			return

	# ---------------- Actions ----------------

	def do_new_address_book(self) -> None:
		self.fieldnames = list(RINGCENTRAL_FIELDNAMES)
		self.csv_data = []
		self.show_dupes_only = False
		self.selected_path = None
		self.populate_table(self.csv_data)
		self.query_one("#selected_path", Static).update("New Address Book")
		self.query_one("#file_update", Static).update("There is currently 0 rows in the csv file.")
		self.refresh_controls()
		self.app.notify("New address book ready — append rows then write to save")

	def _native_file_picker(self) -> str | None:
		"""Open a native OS file-picker and return the chosen path, or None on cancel/failure."""
		# Try tkinter (works on Windows and Linux with python3-tk installed)
		try:
			import tkinter as tk
			from tkinter import filedialog
			root = tk.Tk()
			root.withdraw()
			try:
				root.wm_attributes("-topmost", True)
			except Exception:
				pass  # Not supported on all window managers (e.g. Wayland)
			path = filedialog.askopenfilename(
				title="Select CSV file",
				filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
			)
			root.destroy()
			return path or None
		except Exception:
			pass

		# Try zenity (GNOME / GTK environments on Linux)
		try:
			import subprocess
			result = subprocess.run(
				["zenity", "--file-selection", "--title=Select CSV file", "--file-filter=CSV files (*.csv) | *.csv"],
				capture_output=True, text=True, timeout=60,
			)
			if result.returncode == 0:
				return result.stdout.strip() or None
		except Exception:
			pass

		# Try kdialog (KDE environments on Linux)
		try:
			import subprocess
			result = subprocess.run(
				["kdialog", "--getopenfilename", ".", "*.csv", "--title", "Select CSV file"],
				capture_output=True, text=True, timeout=60,
			)
			if result.returncode == 0:
				return result.stdout.strip() or None
		except Exception:
			pass

		return None

	def do_browse_file(self) -> None:
		path = self._native_file_picker()
		if path is None:
			self.app.notify("File browser not available — type the path manually", severity="warning")
			return
		file_input = self.query_one("#file_path_input", Input)
		file_input.value = path
		self.selected_path = Path(path)
		self.refresh_controls()
		self.do_read_csv()

	def do_read_csv(self) -> None:
		if not self.can_read_csv():
			self.app.notify("Select a valid .csv file first")
			self.refresh_controls()
			return

		path = self.selected_path  # non-None here
		self.app.notify(f"Importing: {path}")

		try:
			rc_csv = RingCentralCSV()
			csv_data = rc_csv.checker(str(path), required_headers=("First Name", "Surname"))

			self.fieldnames = rc_csv.fieldnames
			self.csv_data = csv_data
			dups_msg = rc_csv.format_duplicate_report(self.csv_data, limit=10)
			if dups_msg:
				self.app.notify(dups_msg)

			self.populate_table(self.csv_data)

			row_count = len(self.csv_data)
			self.query_one("#selected_path", Static).update(f"File: {path.name}")
			self.query_one("#file_update", Static).update(
				f"There is currently {row_count} rows in the csv file."
			)

			self.app.notify("Import Complete!" if row_count else "Imported headers only.")

		except ValueError as e:
			self.app.notify(str(e))
		except Exception as e:
			self.app.notify(f"Import Failed: {type(e).__name__}: {e}")

		self.refresh_controls()

	def do_append_csv(self) -> None:
		if not self.can_append_csv():
			self.app.notify("Load a CSV first")
			self.refresh_controls()
			return

		self.app.push_screen(AddRowScreen(self.fieldnames), self._append_row_done)

	def _append_row_done(self, raw_row: dict | None) -> None:
		if raw_row is None:
			return

		try:
			rc = RingCentralCSV()
			rc.fieldnames = self.fieldnames  # use current headers

			rc.append_row(self.csv_data, raw_row)  # validates + appends

			self.populate_table(self.csv_data)
			self.query_one("#file_update", Static).update(
				f"There is currently {len(self.csv_data)} rows in the csv file."
			)
			self.app.notify("Row appended")
			self.refresh_controls()

		except ValueError as e:
			self.app.notify(str(e))

	def do_edit_row(self) -> None:
		if not self.can_edit_row():
			self.app.notify("Nothing to edit")
			self.refresh_controls()
			return

		table = self.query_one("#csv_table", DataTable)
		try:
			row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
			idx = int(row_key.value)
			current_row = self.csv_data[idx]
		except Exception:
			self.app.notify("Select a row first")
			return

		self.app.push_screen(
			EditRowScreen(self.fieldnames, current_row),
			lambda result: self._edit_row_done(idx, result),
		)

	def _edit_row_done(self, idx: int, new_row: dict | None) -> None:
		if new_row is None:
			return

		try:
			rc = RingCentralCSV()
			rc.fieldnames = self.fieldnames

			# Check duplicates against all rows except the one being replaced
			temp_data = [r for i, r in enumerate(self.csv_data) if i != idx]
			rc.assert_no_duplicate_numbers(temp_data + [new_row])

			self.csv_data[idx] = new_row

			if self.show_dupes_only:
				dup_rows = sorted(self.get_duplicate_row_indexes())
				if dup_rows:
					filtered = [self.csv_data[i] for i in dup_rows]
					self.populate_table(filtered, source_indexes=dup_rows)
				else:
					self.show_dupes_only = False
					self.populate_table(self.csv_data)
			else:
				self.populate_table(self.csv_data)

			self.app.notify("Row updated")
			self.refresh_controls()

		except ValueError as e:
			self.app.notify(str(e))

	def do_delete_row(self) -> None:
		if not self.can_delete_row():
			self.app.notify("Nothing to delete")
			self.refresh_controls()
			return

		self.delete_selected_row()
		self.refresh_controls()

	def do_write_csv(self) -> None:
		if not self.can_write_csv():
			self.app.notify("Nothing to write")
			self.refresh_controls()
			return

		self.app.push_screen(
			WriteDirectoryScreen(Path("results").resolve()),
			self._write_csv_done,
		)

	def _write_csv_done(self, out_path: Path | None) -> None:
		if out_path is None:
			return

		try:
			rc_csv = RingCentralCSV()
			saved = rc_csv.writer(self.fieldnames, self.csv_data, out_path=out_path)
			self.app.notify(f"Saved: {saved}")
		except Exception as e:
			self.app.notify(f"Write Failed: {type(e).__name__}: {e}")

		self.refresh_controls()


	# ---------------- Table + deletion + duplication detection ----------------

	def populate_table(self, csv_data: list[dict], source_indexes: list[int] | None = None) -> None:
		table = self.query_one("#csv_table", DataTable)
		table.clear(columns=True)
		table.cursor_type = "row"
		table.show_cursor = True

		columns = self.fieldnames or (list(csv_data[0].keys()) if csv_data else [])
		if not columns:
			return
		table.add_columns(*[str(c) for c in columns])

		def cell(v) -> str:
			return "" if v is None else str(v)

		if source_indexes is None:
			source_indexes = list(range(len(csv_data)))

		for src_i, r in zip(source_indexes, csv_data):
			table.add_row(*[cell(r.get(c, "")) for c in columns], key=src_i)

	def delete_selected_row(self) -> None:
		table = self.query_one("#csv_table", DataTable)

		row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
		if row_key is None:
			self.app.notify("No row selected")
			return

		idx = int(row_key.value)

		if idx < 0 or idx >= len(self.csv_data):
			self.app.notify("Nothing to delete")
			return

		del self.csv_data[idx]

		self.query_one("#file_update", Static).update(
			f"There is currently {len(self.csv_data)} rows in the csv file."
		)

		if getattr(self, "show_dupes_only", False):
			dup_rows = sorted(self.get_duplicate_row_indexes())
			if not dup_rows:
				self.show_dupes_only = False
				self.populate_table(self.csv_data)
				self.app.notify("Row deleted (no duplicates left)")
				return

			filtered = [self.csv_data[i] for i in dup_rows]
			self.populate_table(filtered, source_indexes=dup_rows)
			self.app.notify("Row deleted (duplicates view updated)")
			return

		self.populate_table(self.csv_data)
		self.app.notify("Row deleted")


	def get_duplicate_row_indexes(self) -> set[int]:
		rc = RingCentralCSV()
		dups = rc.find_duplicate_numbers(self.csv_data)

		dup_rows: set[int] = set()
		for number, first_i, first_field, dup_i, dup_field in dups:
			dup_rows.add(first_i)
			dup_rows.add(dup_i)

		return dup_rows

	def do_toggle_dupes(self) -> None:
		if not self.csv_data:
			self.app.notify("Load a CSV first")
			return

		# If switching ON, check if there are any dupes first
		if not self.show_dupes_only:
			dup_rows = sorted(self.get_duplicate_row_indexes())
			if not dup_rows:
				self.app.notify("No duplicate numbers found")
				return

			self.show_dupes_only = True
			filtered = [self.csv_data[i] for i in dup_rows]
			self.populate_table(filtered, source_indexes=dup_rows)
			self.app.notify(f"Showing duplicates only ({len(filtered)} rows)")
			return

		# Switching OFF
		self.show_dupes_only = False
		self.populate_table(self.csv_data)
		self.app.notify("Showing all rows")



class RingCentralCSVApp(App):
	"""
	A Textual app to manage the csv imports.
	"""
	@staticmethod
	def resource_path(relative: str) -> str:
		"""Return an absolute path to a resource for dev/pip installs and PyInstaller bundles."""
		if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
			base = Path(sys._MEIPASS)
		else:
			base = Path(__file__).resolve().parent
		return str(base / relative)

	CSS_PATH = resource_path("styles/RingCentralCSVApp.tcss")

	BINDINGS = [
		Binding("q", "quit", "Quit"),
		Binding("n", "new_address_book", "New"),
		Binding("r", "read_csv", "Read"),
		Binding("a", "append_csv", "Append"),
		Binding("e", "edit_row", "Edit Row"),
		Binding("d", "delete_row", "Delete Row"),
		Binding("w", "write_csv", "Write CSV"),
		Binding("f", "toggle_dupes", "Duplicates Only"),
		Binding("?", "help", "Help")
	]

	def compose(self) -> ComposeResult:
		yield Header()
		yield Footer()
		# Your UI widget
		yield VerticalScroll(ImportRingCentralCSV())

	def on_mount(self) -> None:
		setup_logging()
		self.theme = "tokyo-night"

		# Set border titles
		file_ops = self.query_one("#file_operations_box", Vertical)
		file_ops.border_title = "File Operations"

		dir_box = self.query_one("#directory_box", Vertical)
		dir_box.border_title = "File Import"

		csv_viewer = self.query_one("#csv_viewer", Vertical)
		csv_viewer.border_title = "CSV Viewer"

		# Ensure controls start in correct state
		self.query_one(ImportRingCentralCSV).refresh_controls()

		# Auto-focus the file input so drag-and-drop works without a click
		self.query_one("#file_path_input", Input).focus()

	# -------- Keybinding actions forward to the same UI methods --------

	def action_new_address_book(self) -> None:
		self.query_one(ImportRingCentralCSV).do_new_address_book()

	def action_read_csv(self) -> None:
		self.query_one(ImportRingCentralCSV).do_read_csv()

	def action_append_csv(self) -> None:
		self.query_one(ImportRingCentralCSV).do_append_csv()

	def action_edit_row(self) -> None:
		self.query_one(ImportRingCentralCSV).do_edit_row()

	def action_delete_row(self) -> None:
		self.query_one(ImportRingCentralCSV).do_delete_row()

	def action_write_csv(self) -> None:
		self.query_one(ImportRingCentralCSV).do_write_csv()

	def action_toggle_dupes(self) -> None:
		self.query_one(ImportRingCentralCSV).do_toggle_dupes()

	def action_help(self) -> None:
		self.push_screen(HelpScreen())


	# -------- Keybinding restrictions (same rules as button disabling) --------

	def check_action(self, action: str, parameters: tuple[object, ...]) -> bool:
		ui = self.query_one(ImportRingCentralCSV)

		if action == "read_csv":
			return ui.can_read_csv()

		if action == "append_csv":
			return ui.can_append_csv()

		if action == "edit_row":
			return ui.can_edit_row()

		if action == "delete_row":
			return ui.can_delete_row()

		if action == "write_csv":
			return ui.can_write_csv()

		if action == "toggle_dupes":
			return bool(ui.csv_data)

		return True


def request_terminal_size(rows: int = 55, cols: int = 160) -> None:
	'''
	Best-effort terminal resize request.
	'''
	try:
		sys.stdout.write(f"\x1b[8;{rows};{cols}t")
		sys.stdout.flush()
	except Exception:
		pass

def request_windows_console_size(rows: int = 55, cols: int = 160) -> None:
	'''
	Works for older Windows Console (CMD)
	'''
	try:
		if os.name == "nt":
			os.system(f"mode con: cols={cols} lines={rows}")
	except Exception:
		pass

def on_startup(rows: int = 55, cols: int = 160) -> None:
	request_windows_console_size(rows, cols)
	request_terminal_size(rows, cols)

def setup_logging() -> None:
	log_dir = Path.home() / "ringcentral-csv-editor"
	log_dir.mkdir(parents=True, exist_ok=True)
	log_path = log_dir / "app.log"

	logging.basicConfig(
		level=logging.INFO,  # change to DEBUG when needed
		format="%(asctime)s %(levelname)s %(name)s: %(message)s",
		handlers=[
			logging.FileHandler(log_path, encoding="utf-8"),
			# logging.StreamHandler(),  # optional console output
		],
	)

if __name__ == "__main__":
	on_startup()
	app = RingCentralCSVApp()
	app.run()
