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

**Build a standalone executable (`flet pack`, Linux or Windows):**
```bash
pip install "flet[all]==0.28.3" pyinstaller   # flet-cli + desktop client + PyInstaller
flet pack src/ringcentral_csv_editor/__main__.py \
  --name ringcentral-csv-editor \
  --icon logo.png \
  --product-name "RingCentral CSV Editor" \
  --product-version "0.9.0" \
  --company-name "Ripped-Kanga"
```
`flet pack` wraps PyInstaller and bundles the Flet desktop client. The `--icon`
is honoured on Windows/macOS only (ignored on Linux). Output lands in `dist/`.

There are no automated tests in this project. A quick headless smoke check can
construct the GUI with a mock `flet.Page` (see "Testing the GUI headlessly").

## Architecture

This is a Python **Flet desktop GUI** application (`src` layout, Python 3.11+,
single runtime dependency: `flet[desktop]==0.28.3`). It was migrated from a
Textual TUI in v0.9.0; the CSV logic was kept untouched across the migration.

> **Why the dependency is pinned and uses the `[desktop]` extra:** `flet` alone
> ships no GUI client. `flet[desktop]` pulls `flet-desktop` on Windows/macOS and
> `flet-desktop-light` on Linux (platform markers handle this automatically).
> The `flet` CLI used for `flet pack` lives in `flet-cli` (`flet[cli]`/`flet[all]`),
> a build-time-only dependency. Flet 0.28.x is the mature line; the 0.80+ "Flet
> 1.0" rewrite is intentionally avoided for stability.

**Entry points:**
- `src/ringcentral_csv_editor/__main__.py` — `main()` calls `run()`. Registered
  as the `ringcentral-csv-editor` console script in `pyproject.toml`.
- `src/ringcentral_csv_editor/main.py` — all GUI code. `run()` calls
  `ft.app(target=_app_main)`; `_app_main(page)` calls `setup_logging()` then
  constructs `AddressBookGUI(page)`.
- `src/ringcentral_csv_editor/helper/csv_helper.py` — all CSV logic
  (`RingCentralCSV` class). **Completely UI-agnostic** — reused verbatim from the
  TUI version.

**UI structure (`main.py`):**
- `AddressBookGUI` — the single UI class. Holds all state (`csv_data: list[dict]`,
  `fieldnames: list[str]`, `selected_path: Path | None`, `show_dupes_only: bool`,
  `selected_index: int | None`, `_rows_by_index: dict[int, ft.DataRow]`). Builds
  and owns the whole page in `_build()`.
  - `_build()` — sets theme (Material 3, dark default, indigo seed), window size,
    `page.appbar` (title, theme toggle, help), the toolbar `Row` of buttons, the
    status bar, and the scrollable `table_host` column. Registers
    `page.on_keyboard_event`.
  - `refresh_controls()` — enables/disables toolbar buttons (append/write need
    `fieldnames`; edit/delete need a valid `selected_index`; duplicates need rows).
  - `refresh_status()` — updates the status text (`<file> · <n> rows`) and the
    duplicate-count chip.
  - `refresh_table()` — rebuilds the `DataTable` from `_current_view()`. Each
    `DataCell` and `DataRow` is wired to `select_row(src_index)`. Row keys are
    source indexes into `csv_data`. Shows a placeholder when no book is loaded.
  - `select_row(i)` — updates `selected_index` and toggles `DataRow.selected`
    in place (no full rebuild) for snappy selection.
  - `_current_view()` — returns `(rows, source_indexes)`; filtered to duplicates
    when `show_dupes_only` is on.
  - `_after_data_change()` — the common "refresh controls + status + table +
    `page.update()`" sequence called after every mutation.
  - `get_duplicate_row_indexes()` — `set[int]` of row indexes in any phone dup.
  - Action methods: `do_new_address_book`, `do_open_file`, `do_append_row`,
    `do_edit_row`, `do_delete_row`, `do_toggle_dupes`, `do_write_csv`,
    `_open_help`, `_quit`.
- **Row add/edit dialog** — `_open_row_dialog(title, edit_index)` builds an
  `ft.AlertDialog` with one `ft.TextField` per field. The shared `do_save`
  closure: (1) per-field validation via `RingCentralCSV.field_formatter()` —
  errors set `TextField.error_text` and focus the first bad field; (2) a
  duplicate-number check via `assert_no_duplicate_numbers()` (excluding the row
  being edited) — failures fill a red `error_banner`; (3) on success, append or
  replace in `csv_data`, close the dialog, recompute the view. `edit_index=None`
  means append.
- **Help** — `_open_help()` shows an `ft.AlertDialog` with an `ft.Markdown` body.
- **File dialogs** — two `ft.FilePicker`s in `page.overlay`: `open_picker`
  (`pick_files`, csv filter) → `_on_open_result` → `_read_csv`; `save_picker`
  (`save_file`, timestamped default name) → `_on_save_result` → `writer`. These
  are the **native OS dialogs** (the big UX win over the old in-app tree browser).

**Utility functions in `main.py`:**
- `setup_logging()` — file logging to `~/ringcentral-csv-editor/app.log` at INFO.
- `run()` — `ft.app(target=_app_main)`; the public entry point.

**Keyboard shortcuts** (`_on_keyboard`, modifiers ignored):
`n` new · `o` open · `a` append · `e` edit · `d` delete · `f` toggle duplicates ·
`w` write · `h` help · `q` quit.

> **Gotcha:** Flet's `page.on_keyboard_event` fires even while a dialog
> `TextField` has focus, so typing a contact name would otherwise trigger
> letter shortcuts (e.g. "w" → Write). A `self._dialog_open` flag is set when any
> dialog opens and `_on_keyboard` bails while it is `True`. The flag is reset by
> the Cancel/Save/Close handlers **and** by each dialog's `on_dismiss` (for
> Escape / barrier-tap dismissal) so shortcuts can't get permanently stuck off.

**Data flow:**
1. **Open**: `do_open_file()` → native picker → `_on_open_result` →
   `_read_csv(path)` → `RingCentralCSV.checker()` (finds the real header row past
   RingCentral preamble, reads with `utf-8-sig`) → stored in `csv_data`/
   `fieldnames` → `format_duplicate_report()` warns if dups exist (import still
   succeeds) → table populated.
2. **New**: `do_new_address_book()` seeds `fieldnames` with `RINGCENTRAL_FIELDNAMES`
   and an empty `csv_data`.
3. **Append/Edit**: dialog → `field_formatter()` per field → duplicate check →
   append to or replace in `csv_data`.
4. **Delete**: `del csv_data[selected_index]`; duplicates-only view re-filters and
   falls back to the full view if no dups remain.
5. **Write**: `do_write_csv()` → native save dialog → `RingCentralCSV.writer()`
   writes to the chosen path (`.csv` appended if missing); **returns `Path`**.

**`RingCentralCSV` helper class (`csv_helper.py`)** — unchanged by the GUI migration:
- `checker(csv_in_path, required_headers=("First Name", "Surname"))` — scans for
  the real header row, reads with `utf-8-sig`; returns `list[dict]`, sets
  `self.fieldnames`.
- `normalise_row(raw_row)` — cleans a raw dict via `field_formatter()`; raises
  `ValueError` if `self.fieldnames` is unset.
- `append_row(csv_data, raw_row)` — normalises, checks intra-row then cross-row
  phone duplicates, appends; returns the cleaned row.
- `writer(fieldnames, csv_data, out_path=None)` — writes timestamped output into
  `csv_path_out` when `out_path` is omitted, else to `out_path`; **returns `Path`**.
- `field_formatter(field, value)` — static normaliser:
  - `first name`, `surname` → `.title()`, letters/spaces/hyphens/apostrophes only
  - `job title`, `company` → `.title()`, alphanumeric + spaces/hyphens/apostrophes/ampersands/periods
  - `email` → lowercase + `name@domain.tld` validation
  - phone fields → AU E.164 normalisation (mobile `04…`→`+614…`, landline
    `0[2378]…`→`+61[2378]…`, service `13/1300/1800`→`+61…`)
  - `source`, `external id`, unknown → passthrough
- `find_duplicate_numbers(rows)` — scans the four phone fields; returns
  `list[tuple[str, int, str, int, str]]`. Catches both cross-row and intra-row
  duplicates (a row that repeats a number across two of its own phone fields
  appears as row `i` vs row `i`).
- `format_duplicate_report(rows, limit=10)` / `assert_no_duplicate_numbers(rows)`
  — human-readable report / raises `ValueError` with that report.
- `_is_phone_field(field)` — case-folded membership test for the four phone fields.

**Gotcha:** `RingCentralCSV()` instantiation creates **no** directories — `results/`
is only made inside `writer()` when `out_path` is omitted, so duplicate-check-only
instantiations are side-effect-free.

**Service-number fix (v0.9.0):** `field_formatter`'s already-`61`-prefixed service
branch used `61(300|800)\d{6}`, which wrongly rejected valid `611300…`/`611800…`
and accepted invalid `61300…`/`61800…`. Corrected to `611(300|800)\d{6}` to match
the `+61`-prefixed branch.

## Testing the GUI headlessly

There is no display in CI/headless runs, but Flet control objects can be
constructed without a running app. Drive `AddressBookGUI` with a
`unittest.mock.MagicMock` page: `page.overlay.extend(...)`, `page.open(...)`,
`page.update()` etc. become no-ops, while every real `ft.*` control is still
constructed (catching wrong kwargs/enums/icons). Inject `csv_data`, call
`refresh_table()`, grab dialogs from `page.open.call_args`, set `TextField.value`
and invoke the Save button's `on_click` to exercise validate/dup-block/append/edit.
Note: `TextField.focus()` asserts unless the control is attached to a real page,
so tolerate that one call when testing the invalid-field path.

## Packaging notes

- **Linux desktop launcher:** `desktop.py` installs a `.desktop` entry. It is a
  GUI app, so `Terminal=false` (changed from `true` in the TUI era).
- **Windows installer:** `.github/workflows/build-windows.yml` builds the exe with
  `flet pack` (not raw PyInstaller) then packages it with Inno Setup
  (`installer.iss`). The exe name `ringcentral-csv-editor.exe` is unchanged, so
  `installer.iss` needed no edits.
- `package-data` ships `assets/*.png` only (the old `styles/*.tcss` is gone).
- **Linux libmpv requirement (verified gotcha):** the Flet 0.28 desktop client
  (`flet-desktop-light`) dynamically links `libmpv.so.1`. Modern distros (Arch,
  recent Fedora/Ubuntu) ship `libmpv.so.2`, so the GUI fails to launch with
  `libmpv.so.1: cannot open shared object file`. Fix on the host with a symlink:
  `sudo ln -s /usr/lib/libmpv.so.2 /usr/lib/libmpv.so.1` (confirmed to work on
  Arch + mpv 0.41). This affects both `pip`/`pipx` runs and the `flet pack`
  binary on Linux; Windows is unaffected. Verified end-to-end on 2026-06-14:
  with the shim, `python -m ringcentral_csv_editor` launches and logs
  `Starting RingCentral CSV Editor 0.9.0`.

**Logging:** `~/ringcentral-csv-editor/app.log` at INFO (set in `setup_logging()`).
Change `logging.INFO` to `logging.DEBUG` for verbose output.

**Version:** Tracked manually in both `pyproject.toml` (`version = "0.9.0"`) and
`main.py` (`__version__ = "0.9.0"`). Keep these in sync when bumping.
