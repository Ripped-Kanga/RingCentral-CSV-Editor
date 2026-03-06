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

**Install via pipx directly from GitHub:**
```bash
pipx install git+https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
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

This is a Python **Textual TUI** application (`src` layout, Python 3.11+, single dependency: `textual>=0.60.0`).

**Entry points:**
- `src/ringcentral_csv_editor/__main__.py` — defines `main()` which calls `on_startup()` then `RingCentralCSVApp().run()`. Registered as the `ringcentral-csv-editor` console script in `pyproject.toml`.
- `src/ringcentral_csv_editor/main.py` — all UI code
- `src/ringcentral_csv_editor/helper/csv_helper.py` — all CSV logic (`RingCentralCSV` class)

**UI structure (`main.py`):**
- `RingCentralCSVApp(App)` — top-level Textual app. Owns keybindings (`q/r/a/e/d/w/f/?`), PyInstaller-safe CSS loading via `resource_path()` static method, and forwards all actions to `ImportRingCentralCSV`. Implements `check_action()` to silently block keybindings when preconditions aren't met.
- `ImportRingCentralCSV(HorizontalGroup)` — main widget. Holds all state (`csv_data: list[dict]`, `fieldnames: list[str]`, `selected_path`, `show_dupes_only`). Contains the sidebar (buttons + file-path Input) and the `DataTable` viewer.
  - `refresh_controls()` — syncs button disabled state to the same rules enforced by `check_action()`
  - `populate_table(csv_data, source_indexes=None)` — clears and rebuilds the `DataTable`; row keys are source indexes into `csv_data`
  - `delete_selected_row()` — reads row key from cursor, deletes from `csv_data`, re-populates table
  - `get_duplicate_row_indexes()` — returns `set[int]` of row indexes involved in any phone duplicate
  - `do_toggle_dupes()` — toggles duplicate-only view; filters table to `get_duplicate_row_indexes()` when turning on
  - `on_input_changed()` — updates `selected_path` as the user types in the file-path input
  - `on_input_submitted()` — strips surrounding quotes from pasted paths, validates, then auto-triggers `do_read_csv()`
- `AddRowScreen(ModalScreen[dict | None])` — modal form for appending a row; calls `RingCentralCSV.field_formatter()` per field on Save, returns the validated dict or `None` on Cancel.
- `EditRowScreen(ModalScreen[dict | None])` — modal form for editing an existing row; pre-populated with current values; same per-field `field_formatter()` validation as `AddRowScreen`; returns validated dict or `None` on Cancel.
- `HelpScreen(ModalScreen[None])` — static help text modal.

**Utility functions in `main.py`:**
- `on_startup()` — calls both terminal-resize helpers; invoked before `app.run()`
- `request_terminal_size(rows, cols)` — sends ANSI escape to resize terminal (best-effort)
- `request_windows_console_size(rows, cols)` — resizes Windows CMD console via `mode con:`
- `setup_logging()` — configures file logging to `~/ringcentral-csv-editor/app.log` at INFO level; called in `on_mount`
- `get_logo_path()` — returns a filesystem path to the bundled `assets/logo.png` using `importlib.resources`, safe for both editable installs and PyInstaller bundles

**Data flow:**
1. User types/pastes/drags a `.csv` file path into the File Import input and presses Enter (surrounding quotes are stripped automatically)
2. `RingCentralCSV.checker()` scans for the real header row (skipping RingCentral preamble lines that lack `First Name`/`Surname`), reads with `utf-8-sig` encoding (handles BOM), returns `list[dict]`
3. Data stored in `ImportRingCentralCSV.csv_data`; displayed in `DataTable` with row keys = source indexes into `csv_data`
4. Append: `AddRowScreen` collects fields → `RingCentralCSV.append_row()` normalises, checks for intra-row phone duplicates, then checks against existing data → appended to `csv_data`
5. Edit: `EditRowScreen` pre-populates with current row values → on Save, duplicate check runs against all rows *except* the one being replaced → `csv_data[idx]` updated in-place
6. Delete: row key (source index) used to `del csv_data[idx]`; duplicate-only view re-filters after each delete
7. Write: `RingCentralCSV.writer()` saves to `results/AddressBook-YYYYMMDD-HHMM.csv`, returns the output `Path`

**`RingCentralCSV` helper class (`csv_helper.py`):**
- `checker(csv_in_path, required_headers=("First Name", "Surname"))` — finds real header row by scanning lines until `required_headers` are present; reads with `utf-8-sig` encoding; returns `list[dict]`, sets `self.fieldnames`
- `normalise_row(raw_row)` — takes raw `dict[str, str]`, returns cleaned dict by calling `field_formatter()` on each field; raises `ValueError` if `self.fieldnames` is not set
- `append_row(csv_data, raw_row)` — normalises via `normalise_row()`, checks for phone duplicates within the new row itself, then calls `assert_no_duplicate_numbers()` against the combined list before appending; returns the cleaned row
- `writer(fieldnames, csv_data)` — creates `results/` dir if missing, writes timestamped output; **returns `Path`** to the written file
- `field_formatter(field, value)` — static normaliser (note: the parameter is named `fieldnames` in the source but represents a single field name):
  - `first name`, `surname` → `.title()`, letters/spaces/hyphens/apostrophes only
  - `job title`, `company` → `.title()`, alphanumeric + spaces/hyphens/apostrophes/ampersands/periods
  - `email` → lowercase + regex validation (`name@domain.tld`)
  - `home number`, `business number`, `mobile number`, `company main number` → AU E.164 normalisation:
    - Mobile: `04XXXXXXXX` → `+614XXXXXXXX`
    - Landline: `0[2378]XXXXXXXX` → `+61[2378]XXXXXXXX`
    - Service: `13XXXX` / `1300XXXXXX` / `1800XXXXXX` → `+61`-prefixed
  - `source`, `external id` → passthrough unchanged
  - Unknown fields → passthrough unchanged
- `find_duplicate_numbers(rows)` — scans the four phone fields across all rows; returns `list[tuple[str, int, str, int, str]]` of `(number, first_i, first_field, dup_i, dup_field)`
- `format_duplicate_report(rows, limit=10)` — formats `find_duplicate_numbers()` output into a human-readable string (used after read); returns `""` if no duplicates
- `assert_no_duplicate_numbers(rows)` — raises `ValueError` with the formatted report if duplicates exist (used on append and edit)
- `_is_phone_field(field)` — returns `True` if the (case-folded) field name is one of the four phone fields

**Gotcha:** `RingCentralCSV()` instantiation does **not** create any directories. The `results/` directory is created inside `writer()` only, so instantiating the class for duplicate-check-only calls is side-effect-free.

**`RingCentralCSVApp` guards:** `check_action()` enforces the same rules as button disabling — keybindings are silently blocked when the precondition isn't met (e.g. `r` is blocked unless a valid `.csv` path is entered). `refresh_controls()` mirrors these rules for buttons.

**File import (drag-and-drop):** The DirectoryTree has been replaced with a plain text `Input` widget (`#file_path_input`). In most terminal emulators, dragging a file onto the terminal window pastes its path into the focused input. Surrounding quotes are stripped automatically so paths pasted with `"..."` or `'...'` wrappers work. Pressing Enter validates and auto-reads the file.

**Edit row:** `EditRowScreen` reuses the same modal CSS (`#add_row_modal`) as `AddRowScreen`. The duplicate check in `_edit_row_done` excludes the row being replaced by building a temporary list without that index before calling `assert_no_duplicate_numbers`.

**Styling:** `styles/RingCentralCSVApp.tcss` — Textual CSS; uses `tokyo-night` theme. Logo bundled in `assets/logo.png`, both included via `pyproject.toml` `package-data`. CSS is loaded via `resource_path()` which handles both normal installs and PyInstaller bundles by checking `sys.frozen`/`sys._MEIPASS`.

**Logging:** Writes to `~/ringcentral-csv-editor/app.log` at INFO level (set up in `setup_logging()` called in `on_mount`). Change `logging.INFO` to `logging.DEBUG` for verbose output during development.

**Version:** Tracked manually in both `pyproject.toml` (`version = "0.8.0"`) and `main.py` (`__version__ = "0.8.0"`). Keep these in sync when bumping.
