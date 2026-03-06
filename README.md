# RingCentral CSV Editor (TUI) v0.8.5

A terminal-based **Textual TUI** for importing, validating, editing, and exporting RingCentral "Global Shared Address Book" CSV files.

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
- [Keybindings](#keybindings)
- [Field Validation](#field-validation)
- [Duplicate Numbers](#duplicate-numbers)
- [Project Layout](#project-layout)
- [Build Executable (PyInstaller)](#build-executable-pyinstaller)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Features

### File Import
- **Drag-and-drop** — drag a `.csv` file onto the terminal window to paste its path, then press **Enter** to load it. The input is focused automatically on startup so no clicking is required.
- Also supports typing or pasting a path manually (surrounding quotes stripped automatically).

### Address Book Management
- **New Address Book** — creates a blank address book pre-loaded with the standard RingCentral column headers, ready for data entry without needing an existing file.
- **Read CSV** — detects the real header row by scanning for `First Name` / `Surname` (skips RingCentral preamble), reads with UTF-8 BOM support.
- **DataTable viewer** — scrollable table with row cursor for keyboard navigation.
- **Append Row** — modal form to add a new row with per-field validation. Duplicate phone numbers are blocked.
- **Edit Row** — modal form pre-populated with the selected row's current values. All field validation rules apply. Duplicate checks exclude the row being replaced.
- **Delete Row** — removes the selected row; duplicate-only view re-filters automatically.

### Write CSV
- Opens a **directory browser** to choose the output folder, with a **hidden-file filtered** tree (dotfiles not shown).
- Editable **filename field** pre-filled with a timestamped default (`AddressBook-YYYYMMDD-HHMM.csv`). Customize or leave blank to use the default. `.csv` is appended automatically if omitted.
- Output directory is created if it does not exist.

### Duplicate Detection
- **On Read** — warns if duplicates exist; import still succeeds.
- **On Append / Edit** — blocks duplicates with a clear error message.
- **Toggle duplicate-only view** (`f`) — filters the table to only show rows with conflicting phone numbers for fast cleanup.

---

## Requirements
- Python **3.11+**
- [`textual`](https://textual.textualize.io/) `>= 0.60.0`

---

## Install

### Recommended — pipx from GitHub (always latest)

```bash
pipx install git+https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
```

Upgrade to the latest release at any time:

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

### pip (editable / development)

```bash
git clone https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
cd RingCentral-CSV-Editor
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .
```

### Windows

```powershell
# Install pipx
python -m pip install pipx
python -m pipx ensurepath

# From GitHub
pipx install git+https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git

# Or from a local clone
cd RingCentral-CSV-Editor
pipx install .
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

1. Start the app — the **File Import** input is focused automatically.
2. **Drag** a `.csv` file onto the terminal window to paste its path, then press **Enter**.
   - Alternatively, type or paste the path and press **Enter**.
3. The file is validated and loaded; the table populates immediately.
4. A duplicate warning is shown if conflicting phone numbers are detected (the import still succeeds).

### Creating a new address book from scratch

1. Click **New Address Book** or press `n`.
2. The table is initialised with the standard RingCentral column headers and no rows.
3. Use **Append Row** (`a`) to add contacts, then **Write CSV** (`w`) to save.

### Editing data

| Action | Button | Key |
|---|---|---|
| Append a new row | Append Row | `a` |
| Edit the selected row | Edit Row | `e` |
| Delete the selected row | Delete Row | `d` |

All modal forms validate every field before accepting the input (see [Field Validation](#field-validation)).

### Saving

1. Press `w` or click **Write CSV**.
2. A **Save to Directory** dialog opens.
3. Browse to the desired output folder using the directory tree, or type a path directly.
4. Edit the **Filename** field if needed (default: `AddressBook-YYYYMMDD-HHMM.csv`).
5. Click **Save here**.

---

## Keybindings

| Key | Action | Condition |
|---|---|---|
| `n` | New Address Book | Always |
| `r` | Read CSV | Valid `.csv` path entered |
| `a` | Append Row | Headers loaded |
| `e` | Edit Row | Rows present |
| `d` | Delete Row | Rows present |
| `f` | Toggle duplicates-only view | Rows present |
| `w` | Write CSV | Headers loaded |
| `?` | Help | Always |
| `q` | Quit | Always |

Keybindings are silently disabled when their precondition is not met (the footer indicator dims).

---

## Field Validation

All fields are validated and normalised by `RingCentralCSV.field_formatter()` when a row is added or edited.

| Field | Rule |
|---|---|
| First Name, Surname | Letters, spaces, hyphens, apostrophes only. Title-cased. |
| Job Title, Company | Letters, numbers, spaces, hyphens, apostrophes, ampersands, periods. Title-cased. |
| Email | Must match `name@domain.tld` (lowercased). |
| Home / Business / Mobile / Company Main Number | Australian numbers normalised to E.164 format (see below). |
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

Duplicate detection scans all four phone fields (`Home Number`, `Business Number`, `Mobile Number`, `Company Main Number`) across every row.

- **Import** — duplicates are reported in a notification but the file loads successfully.
- **Append / Edit** — duplicates are **blocked**. The error message lists the conflicting rows and fields.
- **Toggle view** (`f`) — shows only the rows involved in at least one duplicate, making bulk cleanup straightforward.

---

## Project Layout

```
src/ringcentral_csv_editor/
├── __main__.py          # Entry point (calls on_startup() then RingCentralCSVApp().run())
├── main.py              # All UI code (screens, widgets, keybindings)
├── helper/
│   └── csv_helper.py    # RingCentralCSV class (read, validate, write)
├── assets/
│   └── logo.png
└── styles/
    └── RingCentralCSVApp.tcss
```

---

## Build Executable (PyInstaller)

### Linux

```bash
pip install pyinstaller
pyinstaller --onefile --name ringcentral-csv-editor \
  --add-data "src/ringcentral_csv_editor/styles:ringcentral_csv_editor/styles" \
  --add-data "src/ringcentral_csv_editor/assets:ringcentral_csv_editor/assets" \
  src/ringcentral_csv_editor/__main__.py
```

The binary is written to `dist/ringcentral-csv-editor`.

### Windows

```powershell
pip install pyinstaller
pyinstaller --onefile --name ringcentral-csv-editor `
  --add-data "src/ringcentral_csv_editor/styles;ringcentral_csv_editor/styles" `
  --add-data "src/ringcentral_csv_editor/assets;ringcentral_csv_editor/assets" `
  src/ringcentral_csv_editor/__main__.py
```

Note the semicolon (`;`) separator in `--add-data` on Windows.

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

There are no automated tests. The app logs to `~/ringcentral-csv-editor/app.log` at `INFO` level; change `logging.INFO` to `logging.DEBUG` in `main.py` for verbose output.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| File won't load | Ensure the path ends in `.csv` and the file exists. Surrounding quotes are stripped automatically. |
| "Could not find header row" | The file must contain columns named `First Name` and `Surname`. |
| Phone number rejected | Only Australian numbers are supported (mobiles `04…`, landlines `0[2378]…`, service numbers `13/1300/1800`). Include the area code for landlines. |
| Duplicate blocked on edit | The number already exists in another row. Use the duplicate toggle (`f`) to find and resolve conflicts. |
| App doesn't resize terminal | The terminal resize request is best-effort. Manually resize the window if needed. |
