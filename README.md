# RingCentral CSV Editor (TUI)

A terminal-based **Textual TUI** for importing, validating, editing, and exporting RingCentral “Global Shared Address Book” CSV files.

It’s designed to:
- **Find the real header row** even when RingCentral includes “junk” preamble text
- **Validate/normalise fields** (names, emails, AU phone numbers → E.164)
- **Detect duplicate phone numbers** (warn on import, block on append)
- **Edit data interactively** (append rows, delete rows)
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
- **Directory browser** (DirectoryTree) to select a file
- **Read CSV**
  - Detects header row by searching for required headers (`First Name`, `Surname`)
  - Imports into `list[dict]` via `csv.DictReader`
- **DataTable viewer**
  - Row cursor selection enabled for fast keyboard navigation
- **Append Row**
  - Modal form to enter values (no blocking `input()` calls)
  - Field normalisation/validation per column
  - Prevents introducing duplicate phone numbers
- **Delete Row**
  - Deletes selected DataTable row from backing `csv_data`
  - Works in both full view and filtered duplicate view
- **Duplicate detection**
  - On **Read**: **warns** if duplicates exist (import still succeeds)
  - On **Append**: **blocks** duplicates with a clear error message
  - Toggle “duplicates-only” view for fast cleanup
- **Write CSV**
  - Saves to a `results/` folder using timestamped filenames (e.g. `AddressBook-20260126-1530.csv`)

---

## Requirements
- Python **3.11+** recommended
- Dependencies:
  - [`textual`](https://textual.textualize.io/) (TUI framework)

---

## Install (pip / pipx)

### Linux
Recommended for “app-like” installs: **pipx** (isolated environment, easy upgrades).

```bash
# Install pipx if needed (varies by distro; example for Ubuntu/Debian)
sudo apt install pipx
pipx ensurepath

# From the repo directory
pipx install .

