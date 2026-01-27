#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = ""
__version__ = "0.7.1"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"
__disclaimer__ = ""

import csv
import sys
from pathlib import Path
from .helper.csv_helper import RingCentralCSV
from textual.app import App, ComposeResult, Binding
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, HorizontalGroup, VerticalScroll
from textual.widgets import Footer, Header, Input, Button, Static, Label, DirectoryTree, DataTable

class HelpScreen(ModalScreen[None]):
	def compose(self) -> ComposeResult:

		with Vertical(id="help_modal"):
			yield Static(
				"RingCentral CSV Editor — Help\n\n"
				"Navigation\n"
				"  ↑/↓   Move row cursor\n"
				"  Enter Select (DirectoryTree)\n\n"
				"Shortcuts\n"
				"  r     Read CSV (only when a .csv is selected)\n"
				"  a     Append Row (requires headers loaded)\n"
				"  d     Delete Row (requires rows; deletes selected row)\n"
				"  f     Toggle Duplicates-only view\n"
				"  w     Write CSV (timestamped output)\n"
				"  ?     Open this help screen\n"
				"  q     Quit\n\n"
				"Notes\n"
				"  - Duplicate numbers are allowed on import, but shown via warnings.\n"
				"  - Appending blocks duplicates.\n"
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


class ImportRingCentralCSV(HorizontalGroup):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.selected_path: Path | None = None
		self.csv_data: list[dict] = []
		self.fieldnames: list[str] = []
		self.show_dupes_only: bool = False


	def compose(self) -> ComposeResult:
		with Vertical(id="sidebar_box"):
			yield Label("RingCentral CSV Editor - V0.7", id="title_block")

			with Vertical(id="file_operations_box"):
				yield Button("Read CSV", id="read_csv", variant="default", disabled=True)
				yield Button("Append Row", id="append_csv", variant="default", disabled=True)
				yield Button("Delete Row", id="delete_row", variant="default", disabled=True)
				yield Button("Write CSV", id="write_csv", variant="default", disabled=True)

			with Vertical(id="directory_box"):
				yield DirectoryTree(str(Path.home()), id="dir_tree")

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

	def can_delete_row(self) -> bool:
		return bool(self.csv_data)

	def can_write_csv(self) -> bool:
		return bool(self.fieldnames)

	def refresh_controls(self) -> None:
		# Buttons mirror the same rules as keybindings
		self.query_one("#read_csv", Button).disabled = not self.can_read_csv()
		self.query_one("#append_csv", Button).disabled = not self.can_append_csv()
		self.query_one("#delete_row", Button).disabled = not self.can_delete_row()
		self.query_one("#write_csv", Button).disabled = not self.can_write_csv()

	# ---------------- DirectoryTree events ----------------

	def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
		self.selected_path = event.path
		self.query_one("#selected_path", Static).update(f"File: {self.selected_path}")

		if self.selected_path.suffix.lower() != ".csv":
			self.app.notify("Pick a .csv file to enable Read")

		self.refresh_controls()
		event.stop()

	def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
		# If the user clicks a directory, treat as "no file selected".
		self.selected_path = None
		self.query_one("#selected_path", Static).update(f"Dir: {event.path}")
		self.refresh_controls()
		event.stop()

	# ---------------- Buttons forward to the same actions ----------------

	def on_button_pressed(self, event: Button.Pressed) -> None:
		btn = event.button.id

		if btn == "read_csv":
			self.do_read_csv()
			return

		if btn == "append_csv":
			self.do_append_csv()
			return

		if btn == "delete_row":
			self.do_delete_row()
			return

		if btn == "write_csv":
			self.do_write_csv()
			return

	# ---------------- Actions ----------------

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

		try:
			rc_csv = RingCentralCSV()
			csv_path = rc_csv.writer(self.fieldnames, self.csv_data)
			self.app.notify(f"Saved: {csv_path}")
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

		key_val = row_key.value
		idx = key_val if isinstance(key_val, int) else int(str(key_val))

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
		if not hasattr(self, "show_dupes_only"):
			self.show_dupes_only = False

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
	def resource_path(relative: str) -> str:
		"""Return an absolute path to a resource for dev/pip installs and PyInstaller bundles."""
		if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
			base = Path(sys._MEIPASS)  # PyInstaller extraction dir :contentReference[oaicite:1]{index=1}
		else:
			base = Path(__file__).resolve().parent
		return str(base / relative)

	CSS_PATH = CSS_PATH = resource_path("styles/RingCentralCSVApp.tcss")

	BINDINGS = [
		Binding("q", "quit", "Quit"),
		Binding("r", "read_csv", "Read"),
		Binding("a", "append_csv", "Append"),
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
		self.theme = "tokyo-night"

		# Set border titles
		file_ops = self.query_one("#file_operations_box", Vertical)
		file_ops.border_title = "File Operations"

		dir_box = self.query_one("#directory_box", Vertical)
		dir_box.border_title = "Directory Browser"

		csv_viewer = self.query_one("#csv_viewer", Vertical)
		csv_viewer.border_title = "CSV Viewer"

		# Ensure controls start in correct state
		self.query_one(ImportRingCentralCSV).refresh_controls()

	# -------- Keybinding actions forward to the same UI methods --------

	def action_read_csv(self) -> None:
		self.query_one(ImportRingCentralCSV).do_read_csv()

	def action_append_csv(self) -> None:
		self.query_one(ImportRingCentralCSV).do_append_csv()

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

def best_effort_resize(rows: int = 55, cols: int = 160) -> None:
	request_windows_console_size(rows, cols)
	request_terminal_size(rows, cols)


if __name__ == "__main__":
	best_effort_resize()
	app = RingCentralCSVApp()
	app.run()
