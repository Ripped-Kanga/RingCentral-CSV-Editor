"""
CLI helper to install or uninstall the .desktop launcher entry.

Usage:
    ringcentral-csv-editor-desktop --install
    ringcentral-csv-editor-desktop --uninstall
"""

import argparse
import shutil
import sys
from importlib import resources
from pathlib import Path

DESKTOP_DIR = Path.home() / ".local" / "share" / "applications"
ICON_DIR = Path.home() / ".local" / "share" / "icons"
DESKTOP_FILE = DESKTOP_DIR / "ringcentral-csv-editor.desktop"
ICON_FILE = ICON_DIR / "ringcentral-csv-editor.png"

DESKTOP_ENTRY = """\
[Desktop Entry]
Name=RingCentral CSV Editor
Comment=Manage RingCentral CSV address books
Exec=ringcentral-csv-editor
Icon=ringcentral-csv-editor
Type=Application
Categories=Utility;Office;
Terminal=true
"""


def install() -> None:
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    ICON_DIR.mkdir(parents=True, exist_ok=True)

    # Copy bundled logo to icons directory
    with resources.files("ringcentral_csv_editor").joinpath("assets/logo.png").open("rb") as src:
        ICON_FILE.write_bytes(src.read())

    DESKTOP_FILE.write_text(DESKTOP_ENTRY)

    print(f"Installed: {DESKTOP_FILE}")
    print(f"Installed: {ICON_FILE}")
    print("You may need to run: update-desktop-database ~/.local/share/applications")


def uninstall() -> None:
    removed = False
    for path in (DESKTOP_FILE, ICON_FILE):
        if path.exists():
            path.unlink()
            print(f"Removed: {path}")
            removed = True
    if not removed:
        print("Nothing to remove.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ringcentral-csv-editor-desktop",
        description="Install or uninstall the .desktop launcher for RingCentral CSV Editor.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true", help="Install the .desktop file and icon")
    group.add_argument("--uninstall", action="store_true", help="Remove the .desktop file and icon")
    args = parser.parse_args()

    if args.install:
        install()
    elif args.uninstall:
        uninstall()


if __name__ == "__main__":
    main()
