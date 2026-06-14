# RingCentral CSV Editor (GUI) v0.9.0

A cross-platform **desktop GUI** (built with [Flet](https://flet.dev/)) for
importing, validating, editing, and exporting RingCentral "Global Shared Address
Book" CSV files. Runs on **Windows** and **Linux**.

> **v0.9.0 — modernised UI.** The application moved from a terminal TUI (Textual)
> to a native windowed desktop GUI. All functionality was retained; the CSV engine
> (`helper/csv_helper.py`) is unchanged. File open/save now use **native OS
> dialogs**.

It's designed to:
- **Find the real header row** even when RingCentral includes "junk" preamble text
- **Validate/normalise fields** (names, emails, AU phone numbers → E.164)
- **Detect duplicate phone numbers** (warn on import, block on append/edit)
- **Edit data interactively** (append rows, edit rows, delete rows)
- **Save a cleaned CSV** to a directory and filename of your choice

---

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Install](#install)
- [Run](#run)
- [Usage Overview](#usage-overview)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Field Validation](#field-validation)
- [Duplicate Numbers](#duplicate-numbers)
- [Project Layout](#project-layout)
- [Build a Standalone Executable](#build-a-standalone-executable)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Features

### Modern desktop UI
- Native windowed app (Material 3 theme, light/dark toggle in the title bar).
- Toolbar with clearly labelled, icon-backed actions; buttons enable/disable
  based on context (e.g. **Edit**/**Delete** require a selected row).
- Status bar showing the current file, row count, and a duplicate-count chip.

### File Import / Export
- **Open** — a **native OS file dialog** filtered to `.csv`. The real header row
  is detected automatically (RingCentral preamble skipped), read with UTF-8 BOM
  support.
- **Write** — a **native OS save dialog**; pick the folder and filename. The
  default filename is timestamped (`AddressBook-YYYYMMDD-HHMM.csv`) and `.csv` is
  appended automatically if omitted.

### Address Book Management
- **New Address Book** — a blank book pre-loaded with the standard RingCentral
  column headers, ready for data entry without an existing file.
- **DataTable viewer** — scrollable table; click a row to select it.
- **Append Row** — modal form with per-field validation; duplicate phone numbers
  are blocked.
- **Edit Row** — modal form pre-populated with the selected row's values; same
  validation; duplicate checks exclude the row being replaced.
- **Delete Row** — removes the selected row; the duplicates-only view re-filters
  automatically.

### Duplicate Detection
- **On import** — warns if duplicates exist; import still succeeds.
- **On append / edit** — blocks duplicates with a clear error message.
- **Toggle duplicates-only view** (`f`) — filters the table to only rows with
  conflicting phone numbers for fast cleanup.

---

## Requirements
- Python **3.11+**
- [`flet[desktop]`](https://flet.dev/) `== 0.28.3` (installed automatically)

The `[desktop]` extra pulls the platform-correct GUI client:
`flet-desktop` on Windows, `flet-desktop-light` on Linux.

---

## Install

### Recommended — pipx from GitHub (always latest)

```bash
pipx install git+https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
```

Upgrade at any time:

```bash
pipx upgrade ringcentral-csv-editor
# or reinstall from the repo
pipx install --force git+https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
```

### pipx from a local clone

```bash
# Install pipx if needed (Ubuntu/Debian example)
sudo apt install pipx
pipx ensurepath

git clone https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
cd RingCentral-CSV-Editor
pipx install .
```

#### Desktop launcher (Linux, optional)

Register a `.desktop` entry so the app appears in your application launcher:

```bash
ringcentral-csv-editor-desktop --install
```

This writes `~/.local/share/applications/ringcentral-csv-editor.desktop` and
copies the icon to `~/.local/share/icons/`. If your launcher doesn't pick it up:

```bash
update-desktop-database ~/.local/share/applications
```

To remove it before uninstalling:

```bash
ringcentral-csv-editor-desktop --uninstall
pipx uninstall ringcentral-csv-editor
```

> **Note:** `pipx uninstall` does not remove the `.desktop` file — always run
> `--uninstall` first.

### Windows

A pre-built Windows installer is available on the
[Releases](https://github.com/Ripped-Kanga/RingCentral-CSV-Editor/releases) page —
no Python required.

To install via pipx instead (requires Python 3.11+):

```powershell
python -m pip install pipx
python -m pipx ensurepath
pipx install git+https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
```

### pip (editable / development)

```bash
git clone https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
cd RingCentral-CSV-Editor
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .
```

---

## Run

```bash
ringcentral-csv-editor
```

Or directly from a cloned repo (with the venv active):

```bash
python -m ringcentral_csv_editor
```

---

## Usage Overview

### Loading a file
1. Click **Open** (or press `o`) — a native file dialog opens, filtered to `.csv`.
2. Pick a file; it's validated and loaded, and the table populates.
3. A duplicate warning appears if conflicting phone numbers are detected (the
   import still succeeds).

### Creating a new address book from scratch
1. Click **New** (or press `n`).
2. The table is initialised with the standard RingCentral headers and no rows.
3. Use **Append** (`a`) to add contacts, then **Write** (`w`) to save.

### Editing data
| Action | Button | Key |
|---|---|---|
| Append a new row | Append | `a` |
| Edit the selected row | Edit | `e` |
| Delete the selected row | Delete | `d` |

Click a row to select it first. All modal forms validate every field before
accepting input (see [Field Validation](#field-validation)).

### Saving
1. Press `w` or click **Write**.
2. A native save dialog opens with a timestamped default filename.
3. Choose the folder/filename and save (`.csv` is appended if omitted).

---

## Keyboard Shortcuts

| Key | Action | Condition |
|---|---|---|
| `n` | New Address Book | Always |
| `o` | Open CSV | Always |
| `a` | Append Row | Headers loaded |
| `e` | Edit Row | A row is selected |
| `d` | Delete Row | A row is selected |
| `f` | Toggle duplicates-only view | Rows present |
| `w` | Write CSV | Headers loaded |
| `h` | Help | Always |
| `q` | Quit | Always |

Buttons whose precondition isn't met are disabled.

---

## Field Validation

All fields are validated and normalised by `RingCentralCSV.field_formatter()` when
a row is added or edited.

| Field | Rule |
|---|---|
| First Name, Surname | Letters, spaces, hyphens, apostrophes only. Title-cased. |
| Job Title, Company | Letters, numbers, spaces, hyphens, apostrophes, ampersands, periods. Title-cased. |
| Email | Must match `name@domain.tld` (lowercased). |
| Home / Business / Mobile / Company Main Number | Australian numbers normalised to E.164 (see below). |
| Source, External Id | Passed through unchanged. |

### Australian phone number normalisation

| Input format | Output |
|---|---|
| `04XXXXXXXX` | `+614XXXXXXXX` |
| `0[2378]XXXXXXXX` | `+61[2378]XXXXXXXX` |
| `13XXXX` | `+6113XXXX` |
| `1300XXXXXX` | `+611300XXXXXX` |
| `1800XXXXXX` | `+611800XXXXXX` |
| Already E.164 (`+61…`) | Validated and returned as-is. |

---

## Duplicate Numbers

Duplicate detection scans all four phone fields (`Home Number`, `Business Number`,
`Mobile Number`, `Company Main Number`) across every row.

- **Import** — duplicates are reported in a notification but the file loads.
- **Append / Edit** — duplicates are **blocked**; the error lists the conflicting
  rows and fields.
- **Toggle view** (`f`) — shows only rows involved in at least one duplicate.

---

## Project Layout

```
src/ringcentral_csv_editor/
├── __main__.py          # Entry point (main() -> run())
├── main.py              # All GUI code (AddressBookGUI, dialogs, keybindings, run())
├── desktop.py           # Linux desktop entry install/uninstall CLI
├── helper/
│   └── csv_helper.py    # RingCentralCSV class (read, validate, write) — UI-agnostic
└── assets/
    └── logo.png
```

---

## Build a Standalone Executable

The app is packaged with [`flet pack`](https://flet.dev/docs/publish), which wraps
PyInstaller and bundles the Flet desktop client.

```bash
pip install "flet[all]==0.28.3" pyinstaller
flet pack src/ringcentral_csv_editor/__main__.py \
  --name ringcentral-csv-editor \
  --icon logo.png \
  --product-name "RingCentral CSV Editor" \
  --product-version "0.9.0" \
  --company-name "Ripped-Kanga"
```

The binary is written to `dist/`. The `--icon` is honoured on Windows/macOS
(ignored on Linux). Build on the OS you want to target.

### Windows installer
A signed-style installer is produced automatically by GitHub Actions on each
tagged release (see `.github/workflows/build-windows.yml`): `flet pack` builds the
exe, then Inno Setup (`installer.iss`) packages it.

---

## Development

```bash
git clone https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
cd RingCentral-CSV-Editor
python -m venv venv
source venv/bin/activate
pip install -e .
python -m ringcentral_csv_editor
```

There are no automated tests. The app logs to `~/ringcentral-csv-editor/app.log`
at `INFO` level; change `logging.INFO` to `logging.DEBUG` in `main.py` for verbose
output.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| File won't load | Ensure the path ends in `.csv` and the file exists. |
| "Could not find header row" | The file must contain columns named `First Name` and `Surname`. |
| Phone number rejected | Only Australian numbers are supported (mobiles `04…`, landlines `0[2378]…`, service numbers `13/1300/1800`). Include the area code for landlines. |
| Duplicate blocked on edit | The number already exists in another row. Use the duplicates toggle (`f`) to find and resolve conflicts. |
| Edit/Delete buttons greyed out | Click a row in the table to select it first. |
| Window doesn't open on Linux | Ensure a graphical session is running and the GUI client is installed (`pip show flet-desktop-light`). |
| Linux: `libmpv.so.1: cannot open shared object file` | The Flet 0.28 Linux client links the **old** `libmpv.so.1`, but modern distros (Arch, recent Fedora/Ubuntu) ship `libmpv.so.2`. Create a compatibility symlink: `sudo ln -s $(ldconfig -p \| grep -m1 'libmpv.so.2' \| awk '{print $NF}') /usr/lib/libmpv.so.1` (Arch path shown; adjust for your distro). Then re-launch. Verify the source exists first with `ls /usr/lib/libmpv.so.2*`. |
| `flet pack` fails with "install PyInstaller" | `pip install pyinstaller` — `flet pack` wraps it but doesn't install it. |
| `flet` command not found when packaging | Install the CLI: `pip install "flet[cli]==0.28.3"` (or `flet[all]`). |
