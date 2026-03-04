# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the app (development):**
```bash
source venv/bin/activate
python -m ringcentral_csv_editor
```

**Install in editable mode (for development):**
```bash
pip install -e .
```

**Install via pipx (app-like install):**
```bash
pipx install .
```

**Run as installed entry point:**
```bash
ringcentral-csv-editor
```

**Build with PyInstaller (Linux):**
```bash
pyinstaller --onefile --name ringcentral-csv-editor \
  --add-data "src/ringcentral_csv_editor/styles:ringcentral_csv_editor/styles" \
  --add-data "src/ringcentral_csv_editor/assets:ringcentral_csv_editor/assets" \
  src/ringcentral_csv_editor/__main__.py
```

There are no automated tests in this project.

## Architecture

This is a Python **Textual TUI** application (`src` layout, Python 3.11+, single dependency: `textual`).

**Entry points:**
- `src/ringcentral_csv_editor/__main__.py` — calls `RingCentralCSVApp().run()`
- `src/ringcentral_csv_editor/main.py` — all UI code
- `src/ringcentral_csv_editor/helper/csv_helper.py` — all CSV logic (`RingCentralCSV` class)

**UI structure (`main.py`):**
- `RingCentralCSVApp(App)` — top-level Textual app. Owns keybindings (`q/r/a/d/w/f/?`), CSS loading, and forwards all actions to `ImportRingCentralCSV`.
- `ImportRingCentralCSV(HorizontalGroup)` — main widget. Holds all state (`csv_data: list[dict]`, `fieldnames: list[str]`, `selected_path`, `show_dupes_only`). Contains the sidebar (buttons + `DirectoryTree`) and the `DataTable` viewer.
- `AddRowScreen(ModalScreen)` — modal form for appending a row; calls `RingCentralCSV.field_formatter()` per field on save.
- `HelpScreen(ModalScreen)` — static help text modal.

**Data flow:**
1. User picks a `.csv` file via `DirectoryTree` → enables Read button
2. `RingCentralCSV.checker()` scans for the real header row (skipping RingCentral preamble), returns `list[dict]`
3. Data stored in `ImportRingCentralCSV.csv_data`; displayed in `DataTable` with row keys = source indexes into `csv_data`
4. Append: `AddRowScreen` collects fields → `RingCentralCSV.append_row()` normalises + duplicate-checks → appended to `csv_data`
5. Delete: row key (source index) used to `del csv_data[idx]`; duplicate-only view re-filters after each delete
6. Write: `RingCentralCSV.writer()` saves to `results/AddressBook-YYYYMMDD-HHMM.csv`

**`RingCentralCSV` helper class (`csv_helper.py`):**
- `checker()` — finds real header row, returns `list[dict]`, sets `self.fieldnames`
- `field_formatter(field, value)` — static normaliser: names/job title/company → `.title()`, emails → lowercase + validated, AU phone numbers → E.164 (`+61...`), source/external id → passthrough
- `find_duplicate_numbers()` — scans phone fields (`home number`, `business number`, `mobile number`, `company main number`) across all rows; returns list of `(number, first_i, first_field, dup_i, dup_field)` tuples
- `format_duplicate_report()` — formats `find_duplicate_numbers()` output into a human-readable string (used after read)
- `assert_no_duplicate_numbers()` — raises `ValueError` with the formatted report if duplicates exist (used on append)
- `append_row()` — normalises via `normalise_row()` then calls `assert_no_duplicate_numbers()` before appending
- `writer()` — writes to `results/` dir (created if missing)

**Gotcha:** `RingCentralCSV()` creates the `results/` directory on every instantiation — including for duplicate-check-only calls. This is harmless but worth knowing if the class is reused.

**`RingCentralCSVApp` guards:** `check_action()` enforces the same rules as button disabling — keybindings are silently blocked when the precondition isn't met (e.g. `r` is blocked unless a `.csv` is selected).

**Styling:** `styles/RingCentralCSVApp.tcss` — Textual CSS; uses `tokyo-night` theme. Logo bundled in `assets/logo.png`, both included via `pyproject.toml` `package-data`.

**Logging:** Writes to `~/ringcentral-csv-editor/app.log` at INFO level (set up in `setup_logging()` called on `on_mount`).

**Version:** Tracked manually in both `pyproject.toml` (`version = "0.7.7"`) and `main.py` (`__version__ = "0.7.7"`). Keep these in sync when bumping.
