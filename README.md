# RingCentral CSV Editor (TUI)

A terminal-based **Textual TUI** for importing, validating, editing, and exporting RingCentral "Global Shared Address Book" CSV files.

It's designed to:
- **Find the real header row** even when RingCentral includes "junk" preamble text
- **Validate/normalise fields** (names, emails, AU phone numbers → E.164)
- **Detect duplicate phone numbers** (warn on import, block on append)
- **Edit data interactively** (append rows, edit rows, delete rows)
- **Save a cleaned CSV** with a timestamped filename

---

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Install (pip / pipx)](#install-pip--pipx)
  - [Linux](#linux)
  - [Windows](#windows)
- [Run](#run)
- [Usage Overview](#usage-overview)
- [Keybindings](#keybindings)
- [Duplicate Numbers](#duplicate-numbers)
- [Export / Write CSV](#export--write-csv)
- [Project Layout](#project-layout)
- [Build Executable (PyInstaller)](#build-executable-pyinstaller)
  - [Linux Build](#linux-build)
  - [Windows Build](#windows-build)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Features
- **File browser** — type/paste a path, or click **Browse...** to open a native OS file picker
- **Read CSV**
  - Detects header row by searching for required headers (`First Name`, `Surname`)
  - Imports into `list[dict]` via `csv.DictReader`
- **DataTable viewer**
  - Row cursor selection enabled for fast keyboard navigation
- **Append Row**
  - Modal form to enter values
  - Field normalisation/validation per column
  - Prevents introducing duplicate phone numbers
- **Edit Row**
  - Modal form pre-populated with existing values
  - Same validation as Append; duplicate check excludes the row being replaced
- **Delete Row**
  - Deletes selected row from backing data
  - Works in both full view and filtered duplicate view
- **New Address Book**
  - Start a blank address book without loading a file
- **Duplicate detection**
  - On **Read**: warns if duplicates exist (import still succeeds)
  - On **Append/Edit**: blocks duplicates with a clear error message
  - Toggle "duplicates-only" view for fast cleanup
- **Write CSV**
  - Saves to a `results/` folder using timestamped filenames (e.g. `AddressBook-20260126-1530.csv`)

---

## Requirements
- Python **3.11+**
- Dependencies:
  - [`textual`](https://textual.textualize.io/) (TUI framework)

---

## Install (pip / pipx)

### Linux
Recommended for "app-like" installs: **pipx** (isolated environment, easy upgrades).

```bash
# Install pipx if needed (varies by distro; example for Ubuntu/Debian)
sudo apt install pipx
pipx ensurepath

# Install directly from GitHub
pipx install git+https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git

# Or from a local clone
pipx install .
```

#### Desktop launcher (optional)

After installing, register a `.desktop` entry so the app appears in your application launcher:

```bash
ringcentral-csv-editor-desktop --install
```

This installs `~/.local/share/applications/ringcentral-csv-editor.desktop` and copies the icon to `~/.local/share/icons/`. If your launcher doesn't pick it up immediately, run:

```bash
update-desktop-database ~/.local/share/applications
```

To remove the launcher entry before uninstalling:

```bash
ringcentral-csv-editor-desktop --uninstall
pipx uninstall ringcentral-csv-editor
```

> **Note:** The **Browse...** button uses `tkinter` if available (`python3-tk` on Debian/Ubuntu), then falls back to `zenity` (GNOME) or `kdialog` (KDE). If none are present, type or paste the file path manually.

### Windows

A pre-built Windows installer (`.exe`) is available on the [Releases](https://github.com/Ripped-Kanga/RingCentral-CSV-Editor/releases) page — no Python required.

Alternatively, install via pipx if you have Python 3.11+ installed:

```powershell
pipx install git+https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
```

---

## Run

```bash
ringcentral-csv-editor
```

Or in development (from the repo root):

```bash
source venv/bin/activate
python -m ringcentral_csv_editor
```

---

## Usage Overview

1. **Load a file** — type or paste a `.csv` path into the input box and press **Enter**, or click **Browse...** to open a native file picker. The file is read automatically.
2. **Review data** — the DataTable shows all rows. Duplicate phone numbers are flagged with a warning notification.
3. **Edit** — use the buttons or keybindings to append, edit, or delete rows.
4. **Save** — press **w** or click **Write CSV** to export a cleaned, timestamped file to the `results/` folder.

---

## Keybindings

| Key | Action          |
|-----|-----------------|
| `n` | New Address Book |
| `r` | Read CSV        |
| `a` | Append Row      |
| `e` | Edit Row        |
| `d` | Delete Row      |
| `w` | Write CSV       |
| `f` | Toggle Duplicates Only |
| `?` | Help            |
| `q` | Quit            |

---

## Duplicate Numbers

- **On import (Read):** duplicates are allowed but a warning is shown. A "Duplicates Only" view (`f`) lets you review and delete them.
- **On Append/Edit:** duplicate phone numbers are blocked with a descriptive error showing which rows conflict.
- The four checked fields are: `Home Number`, `Business Number`, `Mobile Number`, `Company Main Number`.

---

## Export / Write CSV

- Output goes to `results/AddressBook-YYYYMMDD-HHMM.csv` relative to the working directory.
- The directory is created automatically if it doesn't exist.
- Column order matches the standard RingCentral Global Address Book format.

---

## Project Layout

```
src/ringcentral_csv_editor/
├── __main__.py        # Entry point
├── main.py            # All UI code (Textual app)
├── desktop.py         # Desktop entry install/uninstall CLI
├── helper/
│   └── csv_helper.py  # CSV logic (RingCentralCSV class)
├── assets/
│   └── logo.png
└── styles/
    └── RingCentralCSVApp.tcss
```

---

## Build Executable (PyInstaller)

### Linux Build

```bash
pip install pyinstaller
pyinstaller --onefile --name ringcentral-csv-editor \
  --add-data "src/ringcentral_csv_editor/styles:styles" \
  --add-data "src/ringcentral_csv_editor/assets:assets" \
  src/ringcentral_csv_editor/__main__.py
```

### Windows Build

```powershell
pip install pyinstaller
pyinstaller --onefile --name ringcentral-csv-editor `
  --add-data "src/ringcentral_csv_editor/styles;styles" `
  --add-data "src/ringcentral_csv_editor/assets;assets" `
  src/ringcentral_csv_editor/__main__.py
```

A Windows installer is also built automatically via GitHub Actions on each release. See `.github/workflows/build-windows.yml`.

---

## Development

```bash
git clone https://github.com/Ripped-Kanga/RingCentral-CSV-Editor.git
cd RingCentral-CSV-Editor
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .
python -m ringcentral_csv_editor
```

Logs are written to `~/ringcentral-csv-editor/app.log`.

---

## Troubleshooting

**Browse button shows a warning on Linux**
Install `tkinter` (`sudo apt install python3-tk` on Debian/Ubuntu), or ensure `zenity` (GNOME) or `kdialog` (KDE) is available.

**StylesheetError on startup (PyInstaller build)**
Ensure `--add-data` destinations are `styles` and `assets` (not `ringcentral_csv_editor/styles`). See [Build Executable](#build-executable-pyinstaller).

**File not found after Write CSV**
The `results/` folder is created in the current working directory when the app is launched — check there.
