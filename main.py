#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = ""
__version__ = "0.1"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"
__disclaimer__ = ""


# Import Libraries
import sys
import os
import pprint
from pathlib import Path
from typing import Iterable
from helper.csv_helper import RingCentralCSV
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, HorizontalGroup, VerticalScroll
from textual.widgets import Footer, Header, Button, Static, DirectoryTree, DataTable

def __init__(self, *args, **kwargs):
	super().__init__(*args, **kwargs)
	self.selected_path: Path = None
	self.csv_data: list[dict] = []
	self.fieldnames: list[str] = []

class RingCentralCSVApp(App):
	'''
	A Textual app to manage the csv imports.
	'''
	CSS_PATH = str(Path(__file__).parent / "styles" / "RingCentralCSVApp.tcss")
	BINDINGS = [
		("q", "quit", "Quit")
	]

	def compose(self) -> ComposeResult:
		'''
		Creates child widgets for the app
		'''
		yield Header()
		yield Footer()
		yield VerticalScroll(ImportRingCentralCSV())


class ImportRingCentralCSV(HorizontalGroup):

	def compose(self) -> ComposeResult:
		'''
		Creates child widgets for the app
		'''

		with Horizontal(id="main_container"):
			
			with Vertical(id="side_commands_container", classes="content_box"):
				yield Static("File Operations", classes="header")
				yield Button("Read CSV", id="read", variant="default", disabled=True)
				yield Button("Append Row", id="append", variant="default", disabled=True)
				yield Button("Delete Row", id="delete_selection", variant="default", disabled=True)
				yield Button("Write CSV", id="write_csv", variant="default", disabled=True)
			
			with Vertical(id="csv_viewer", classes="content_box"):
				yield Static("CSV Viewer", classes="header")
				yield Static("No file selected:", id="selected_path", classes="sub-header")
				yield Static("", id="file_update", classes="sub-header")
				
				with VerticalScroll(id="csv_browser"):
					yield DataTable(id="csv_table")
			
			with Vertical(id="directory", classes="content_box"):
				yield Static("Directory Browser", classes="header")
				yield DirectoryTree(str(Path.home()), id="dir_tree")

	def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
		'''
		Triggers when a file is selected from the DirectoryTree Applet
		'''
		self.selected_path = event.path
		self.query_one("#selected_path", Static).update(f"File: {self.selected_path}")
		is_csv = self.selected_path.suffix.lower() == ".csv"
		self.query_one("#read", Button).disabled = not is_csv

		if not is_csv:
			self.app.notify("Pick a .csv file to enable Import")
			
		event.stop()


	def on_button_pressed(self, event: Button.Pressed) -> None:
		'''
		Lister for button actions, acts according to which button clicked.
		'''
		btn = event.button.id

		# Logic for 'read' button.
		if btn == "read":
			# Catch for odd behavior in dir_tree.
			if self.selected_path is None:
				self.app.notify("Select a CSV file first")
				return

			path: Path = self.selected_path
			# Catch the user selecting something other then a .csv.
			if path.suffix.lower() != ".csv":
				self.app.notify("Please select a .csv file")
				return

			# Catch for odd behavior in dir_tree.
			if not path.exists():
				self.app.notify(f"File not found: {path}")
				return

			# Try import the selected file, send to checker().
			try:
				rc_csv = RingCentralCSV()
				csv_name = str(self.selected_path)
				self.app.notify(f"Importing: {self.selected_path}")
				csv_data = rc_csv.checker(csv_name, required_headers=("First Name", "Surname"))
				row_count  = len(csv_data)
				self.fieldnames = rc_csv.fieldnames
				self.csv_data = csv_data
				self.populate_table(self.csv_data)
				self.query_one("#delete_selection", Button).disabled = (len(self.csv_data) == 0)
				self.query_one("#write_csv", Button).disabled = (len(self.csv_data) == 0)
				self.query_one("#file_update", Static).update(f"There is currently {row_count} rows in the csv file.")
				if csv_data:
					self.app.notify("Import Complete!")
					
			# Catch any errors and raise to notification.
			except ValueError as e:
				self.app.notify(str(e))
				return

			except Exception as e:
				self.app.notify(f"Import Failed: {type(e).__name__}: {e}")
				return

		# Logic for 'delete_row' button.
		if btn == "delete_selection":
			self.delete_selected_row()

			return

		# Logic for 'write_csv' button.
		if btn == "write_csv":
			rc_csv = RingCentralCSV()
			csv_path = rc_csv.writer(self.fieldnames, self.csv_data)
			self.app.notify(f"Saved: {csv_path}")


	def populate_table(self, csv_data: list[dict]) -> None:
		'''
		Takes the returned list[dict] from checker() and displays it as a DataTable.
		'''
		table = self.query_one(DataTable)

		table.clear(columns=True)

		# Set curses selections
		cursors = "row"
		table.cursor_type = cursors
		table.show_cursor = True
		# Prefer fieldnames from DictRead
		columns = getattr(self, "fieldnames", None) or []

		# if fieldnames aren't retrievable, fallback to keys
		if not columns and csv_data:
			columns = list(csv_data[0].keys())

		# Render nothing if no headers retrieved.
		if not columns:
			return

		table.add_columns(*[str(c) for c in columns])

		if not csv_data:
			return 

		def cell(v) -> str:
			return "" if v is None else str(v)

		table.add_rows([[cell(r.get(c, "")) for c in columns] for r in csv_data])

	def delete_selected_row(self) -> None:
		'''
		Allows selection of rows in the DataTable, removing a row removes the entry from csv_data list.
		'''
		table = self.query_one(DataTable)
		key = table.cursor_row

		if key is None:
			self.app.notify("No row selected")
			return

		idx = int(key)  # only works if you used index as the row key
		if not hasattr(self, "csv_data") or idx >= len(self.csv_data):
			self.app.notify("Nothing to delete")
			return

		# Delete the row
		del self.csv_data[idx]
		self.populate_table(self.csv_data)
		self.app.notify("Row deleted")


# Start Execution
if __name__ == "__main__":
	# Start 
	app = RingCentralCSVApp()
	app.run()
