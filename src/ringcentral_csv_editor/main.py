#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = ""
__version__ = "0.9.0"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"
__disclaimer__ = ""

import logging
from datetime import datetime
from pathlib import Path

import flet as ft

from .helper.csv_helper import RingCentralCSV

logger = logging.getLogger(__name__)

# Standard RingCentral Global Address Book column order
RINGCENTRAL_FIELDNAMES: tuple[str, ...] = (
    "First Name",
    "Surname",
    "Job Title",
    "Company",
    "Email",
    "Home Number",
    "Business Number",
    "Mobile Number",
    "Company Main Number",
    "Source",
    "External Id",
)

HELP_TEXT = """\
## RingCentral CSV Editor — Help

A desktop tool for importing, validating, editing and exporting RingCentral
*Global Shared Address Book* CSV files.

### Toolbar
- **New** — start a blank address book with the standard headers.
- **Open** — load a `.csv` (the real header row is detected automatically).
- **Append** — add a new contact (every field is validated).
- **Edit** — edit the selected row.
- **Delete** — remove the selected row.
- **Duplicates** — show only rows that share a phone number.
- **Write** — save a cleaned CSV (you choose the folder and filename).

### Keyboard shortcuts
| Key | Action |
|-----|--------|
| `n` | New address book |
| `o` | Open CSV |
| `a` | Append row |
| `e` | Edit selected row |
| `d` | Delete selected row |
| `f` | Toggle duplicates-only view |
| `w` | Write CSV |
| `h` | Help |
| `q` | Quit |

### Notes
- Click a row to select it before editing or deleting.
- Duplicate numbers are **allowed on import** (you are warned) but **blocked**
  when appending or editing.
- Australian numbers are normalised to E.164 (`04…` → `+614…`, etc.).
"""


def setup_logging() -> None:
    log_dir = Path.home() / "ringcentral-csv-editor"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"

    logging.basicConfig(
        level=logging.INFO,  # change to DEBUG when needed
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
    )


class AddressBookGUI:
    """Flet GUI wrapper around the RingCentralCSV helper."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page

        # ---- state ----
        self.csv_data: list[dict] = []
        self.fieldnames: list[str] = []
        self.selected_path: Path | None = None
        self.show_dupes_only: bool = False
        self.selected_index: int | None = None  # source index into csv_data
        self._rows_by_index: dict[int, ft.DataRow] = {}
        self._dialog_open: bool = False  # suppress shortcuts while typing in a dialog

        # ---- file pickers (native dialogs) ----
        self.open_picker = ft.FilePicker(on_result=self._on_open_result)
        self.save_picker = ft.FilePicker(on_result=self._on_save_result)
        page.overlay.extend([self.open_picker, self.save_picker])

        self._build()
        self.refresh_controls()
        self.refresh_status()
        self.refresh_table()
        self.page.update()

    # ------------------------------------------------------------------ UI

    def _build(self) -> None:
        page = self.page
        page.title = f"RingCentral CSV Editor — {__version__}"
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO, use_material3=True)
        page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO, use_material3=True)
        page.padding = 0
        page.on_keyboard_event = self._on_keyboard

        try:
            page.window.width = 1180
            page.window.height = 760
            page.window.min_width = 900
            page.window.min_height = 560
            page.window.center()
        except Exception:
            pass

        self.theme_button = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE,
            tooltip="Toggle light / dark theme",
            on_click=self._toggle_theme,
        )
        page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.CONTACTS),
            leading_width=44,
            title=ft.Text("RingCentral CSV Editor", weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.PRIMARY),
            actions=[
                self.theme_button,
                ft.IconButton(
                    icon=ft.Icons.HELP_OUTLINE,
                    tooltip="Help (h)",
                    on_click=lambda e: self._open_help(),
                ),
            ],
        )

        # ---- toolbar ----
        self.btn_new = ft.FilledTonalButton(
            "New", icon=ft.Icons.ADD, tooltip="New address book (n)",
            on_click=lambda e: self.do_new_address_book(),
        )
        self.btn_open = ft.FilledButton(
            "Open", icon=ft.Icons.FOLDER_OPEN, tooltip="Open a CSV file (o)",
            on_click=lambda e: self.do_open_file(),
        )
        self.btn_append = ft.OutlinedButton(
            "Append", icon=ft.Icons.PERSON_ADD, tooltip="Append a row (a)",
            on_click=lambda e: self.do_append_row(),
        )
        self.btn_edit = ft.OutlinedButton(
            "Edit", icon=ft.Icons.EDIT, tooltip="Edit selected row (e)",
            on_click=lambda e: self.do_edit_row(),
        )
        self.btn_delete = ft.OutlinedButton(
            "Delete", icon=ft.Icons.DELETE_OUTLINE, tooltip="Delete selected row (d)",
            on_click=lambda e: self.do_delete_row(),
        )
        self.btn_dupes = ft.OutlinedButton(
            "Duplicates", icon=ft.Icons.FILTER_ALT, tooltip="Show duplicates only (f)",
            on_click=lambda e: self.do_toggle_dupes(),
        )
        self.btn_write = ft.FilledButton(
            "Write", icon=ft.Icons.SAVE, tooltip="Write CSV (w)",
            on_click=lambda e: self.do_write_csv(),
        )

        toolbar = ft.Container(
            content=ft.Row(
                [
                    self.btn_new,
                    self.btn_open,
                    ft.VerticalDivider(width=1),
                    self.btn_append,
                    self.btn_edit,
                    self.btn_delete,
                    ft.VerticalDivider(width=1),
                    self.btn_dupes,
                    ft.Container(expand=True),
                    self.btn_write,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )

        # ---- status bar ----
        self.status_text = ft.Text("No address book loaded", weight=ft.FontWeight.W_500)
        self.dupe_text = ft.Text("", color=ft.Colors.AMBER)
        status_bar = ft.Container(
            content=ft.Row(
                [self.status_text, ft.Container(expand=True), self.dupe_text],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=6),
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
        )

        # ---- table host ----
        self.table_host = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        table_area = ft.Container(
            content=self.table_host,
            expand=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
        )

        page.add(
            ft.Column(
                [toolbar, ft.Divider(height=1), status_bar, table_area],
                spacing=0,
                expand=True,
            )
        )

    # --------------------------------------------------------------- helpers

    def notify(self, message: str, error: bool = False) -> None:
        sb = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
            duration=6000,
        )
        self.page.open(sb)

    def _toggle_theme(self, e=None) -> None:
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.theme_button.icon = ft.Icons.DARK_MODE
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.theme_button.icon = ft.Icons.LIGHT_MODE
        self.page.update()

    # --------------------------------------------------------------- rules

    def can_append(self) -> bool:
        return bool(self.fieldnames)

    def can_write(self) -> bool:
        return bool(self.fieldnames)

    def _has_selection(self) -> bool:
        return (
            self.selected_index is not None
            and 0 <= self.selected_index < len(self.csv_data)
        )

    def refresh_controls(self) -> None:
        self.btn_append.disabled = not self.can_append()
        self.btn_write.disabled = not self.can_write()
        self.btn_edit.disabled = not self._has_selection()
        self.btn_delete.disabled = not self._has_selection()
        self.btn_dupes.disabled = not bool(self.csv_data)

    def refresh_status(self) -> None:
        if not self.fieldnames:
            self.status_text.value = "No address book loaded"
        else:
            where = self.selected_path.name if self.selected_path else "New Address Book"
            self.status_text.value = f"{where}  ·  {len(self.csv_data)} rows"

        dups = RingCentralCSV().find_duplicate_numbers(self.csv_data) if self.csv_data else []
        if dups:
            n = len({d[0] for d in dups})
            self.dupe_text.value = f"⚠ {n} duplicate number{'s' if n != 1 else ''}"
        else:
            self.dupe_text.value = ""

    # ------------------------------------------------------------- the table

    def _current_view(self) -> tuple[list[dict], list[int]]:
        if self.show_dupes_only:
            dup_rows = sorted(self.get_duplicate_row_indexes())
            return [self.csv_data[i] for i in dup_rows], dup_rows
        return self.csv_data, list(range(len(self.csv_data)))

    def refresh_table(self) -> None:
        self._rows_by_index = {}

        if not self.fieldnames:
            self.table_host.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.TABLE_VIEW, size=48,
                                    color=ft.Colors.OUTLINE),
                            ft.Text("No address book loaded",
                                    size=18, color=ft.Colors.OUTLINE),
                            ft.Text("Open a CSV or create a New Address Book to begin.",
                                    color=ft.Colors.OUTLINE),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=40,
                )
            ]
            return

        rows, source_indexes = self._current_view()

        columns = [
            ft.DataColumn(ft.Text(c, weight=ft.FontWeight.BOLD))
            for c in self.fieldnames
        ]

        data_rows: list[ft.DataRow] = []
        for src_i, r in zip(source_indexes, rows):
            cells = [
                ft.DataCell(
                    ft.Text(str(r.get(c, "") or "")),
                    on_tap=lambda e, i=src_i: self.select_row(i),
                )
                for c in self.fieldnames
            ]
            row = ft.DataRow(
                cells=cells,
                selected=(src_i == self.selected_index),
                on_select_changed=lambda e, i=src_i: self.select_row(i),
            )
            self._rows_by_index[src_i] = row
            data_rows.append(row)

        table = ft.DataTable(
            columns=columns,
            rows=data_rows,
            show_checkbox_column=False,
            column_spacing=22,
            heading_row_color=ft.Colors.with_opacity(0.08, ft.Colors.PRIMARY),
            heading_text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
            data_row_min_height=36,
            data_row_max_height=46,
            divider_thickness=1,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=8,
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.with_opacity(0.4, ft.Colors.OUTLINE_VARIANT)),
        )

        if not data_rows:
            self.table_host.controls = [
                ft.Container(
                    content=ft.Text("No rows yet — use Append to add a contact.",
                                    color=ft.Colors.OUTLINE),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=40,
                )
            ]
        else:
            # Row wrapper allows horizontal scrolling for the wide table.
            self.table_host.controls = [ft.Row([table], scroll=ft.ScrollMode.AUTO)]

    def select_row(self, i: int) -> None:
        if i == self.selected_index:
            return
        prev = self.selected_index
        self.selected_index = i
        if prev is not None and prev in self._rows_by_index:
            self._rows_by_index[prev].selected = False
        if i in self._rows_by_index:
            self._rows_by_index[i].selected = True
        self.refresh_controls()
        self.page.update()

    def get_duplicate_row_indexes(self) -> set[int]:
        rc = RingCentralCSV()
        dups = rc.find_duplicate_numbers(self.csv_data)
        dup_rows: set[int] = set()
        for _number, first_i, _first_field, dup_i, _dup_field in dups:
            dup_rows.add(first_i)
            dup_rows.add(dup_i)
        return dup_rows

    def _after_data_change(self) -> None:
        self.refresh_controls()
        self.refresh_status()
        self.refresh_table()
        self.page.update()

    # ------------------------------------------------------------- actions

    def do_new_address_book(self) -> None:
        self.fieldnames = list(RINGCENTRAL_FIELDNAMES)
        self.csv_data = []
        self.show_dupes_only = False
        self.selected_path = None
        self.selected_index = None
        self._after_data_change()
        self.notify("New address book ready — append rows then write to save")

    def do_open_file(self) -> None:
        self.open_picker.pick_files(
            dialog_title="Open RingCentral CSV",
            allowed_extensions=["csv"],
            allow_multiple=False,
        )

    def _on_open_result(self, e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        self._read_csv(Path(e.files[0].path))

    def _read_csv(self, path: Path) -> None:
        try:
            rc_csv = RingCentralCSV()
            csv_data = rc_csv.checker(str(path), required_headers=("First Name", "Surname"))

            self.fieldnames = rc_csv.fieldnames
            self.csv_data = csv_data
            self.selected_path = path
            self.show_dupes_only = False
            self.selected_index = None

            dups_msg = rc_csv.format_duplicate_report(self.csv_data, limit=10)

            self._after_data_change()

            if dups_msg:
                self.notify(dups_msg)
            else:
                self.notify(
                    "Import complete!" if self.csv_data else "Imported headers only."
                )
        except ValueError as ex:
            self.notify(str(ex), error=True)
        except Exception as ex:  # noqa: BLE001 - surface to user
            self.notify(f"Import failed: {type(ex).__name__}: {ex}", error=True)

    def do_append_row(self) -> None:
        if not self.can_append():
            self.notify("Open a CSV or start a New Address Book first")
            return
        self._open_row_dialog(title="Append Row", edit_index=None)

    def do_edit_row(self) -> None:
        if not self._has_selection():
            self.notify("Select a row first")
            return
        self._open_row_dialog(title="Edit Row", edit_index=self.selected_index)

    def do_delete_row(self) -> None:
        if not self._has_selection():
            self.notify("Select a row first")
            return

        idx = self.selected_index
        del self.csv_data[idx]
        self.selected_index = None

        # If the duplicates-only view is empty now, fall back to the full view.
        if self.show_dupes_only and not self.get_duplicate_row_indexes():
            self.show_dupes_only = False
            self._after_data_change()
            self.notify("Row deleted (no duplicates left)")
            return

        self._after_data_change()
        self.notify("Row deleted")

    def do_toggle_dupes(self) -> None:
        if not self.csv_data:
            self.notify("Open a CSV first")
            return

        if not self.show_dupes_only:
            if not self.get_duplicate_row_indexes():
                self.notify("No duplicate numbers found")
                return
            self.show_dupes_only = True
            self.btn_dupes.icon = ft.Icons.FILTER_ALT_OFF
            self.btn_dupes.text = "Show all"
            self.selected_index = None
            self._after_data_change()
            self.notify("Showing duplicates only")
            return

        self.show_dupes_only = False
        self.btn_dupes.icon = ft.Icons.FILTER_ALT
        self.btn_dupes.text = "Duplicates"
        self.selected_index = None
        self._after_data_change()
        self.notify("Showing all rows")

    def do_write_csv(self) -> None:
        if not self.can_write():
            self.notify("Nothing to write")
            return
        default_name = f"AddressBook-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
        self.save_picker.save_file(
            dialog_title="Write RingCentral CSV",
            file_name=default_name,
            allowed_extensions=["csv"],
        )

    def _on_save_result(self, e: ft.FilePickerResultEvent) -> None:
        if not e.path:
            return
        out_path = Path(e.path)
        if out_path.suffix.lower() != ".csv":
            out_path = out_path.with_suffix(".csv")
        try:
            saved = RingCentralCSV().writer(self.fieldnames, self.csv_data, out_path=out_path)
            self.notify(f"Saved: {saved}")
        except Exception as ex:  # noqa: BLE001 - surface to user
            self.notify(f"Write failed: {type(ex).__name__}: {ex}", error=True)

    # --------------------------------------------------------- row dialog

    def _open_row_dialog(self, title: str, edit_index: int | None) -> None:
        is_edit = edit_index is not None
        current = self.csv_data[edit_index] if is_edit else {}

        inputs: dict[str, ft.TextField] = {}
        form_controls: list[ft.Control] = []
        for field in self.fieldnames:
            tf = ft.TextField(
                label=field,
                value=str(current.get(field, "") or "") if is_edit else "",
                dense=True,
                hint_text="(blank allowed)",
            )
            inputs[field] = tf
            form_controls.append(tf)

        error_banner = ft.Text("", color=ft.Colors.ERROR, selectable=True)

        def do_save(e=None) -> None:
            for tf in inputs.values():
                tf.error_text = None
            error_banner.value = ""

            cleaned: dict[str, str] = {}
            first_bad: ft.TextField | None = None
            for field, tf in inputs.items():
                try:
                    cleaned[field] = RingCentralCSV.field_formatter(field, (tf.value or "").strip())
                except ValueError as ex:
                    tf.error_text = str(ex)
                    if first_bad is None:
                        first_bad = tf
            if first_bad is not None:
                self.page.update()
                first_bad.focus()
                return

            # Duplicate-number check (intra-row and against other rows).
            rc = RingCentralCSV()
            rc.fieldnames = self.fieldnames
            try:
                if is_edit:
                    others = [r for i, r in enumerate(self.csv_data) if i != edit_index]
                    rc.assert_no_duplicate_numbers(others + [cleaned])
                else:
                    rc.assert_no_duplicate_numbers(self.csv_data + [cleaned])
            except ValueError as ex:
                error_banner.value = str(ex)
                self.page.update()
                return

            if is_edit:
                self.csv_data[edit_index] = cleaned
            else:
                self.csv_data.append(cleaned)

            self._dialog_open = False
            self.page.close(dlg)

            # Editing may make a row stop being a duplicate; recompute the view.
            if self.show_dupes_only and not self.get_duplicate_row_indexes():
                self.show_dupes_only = False
                self.btn_dupes.icon = ft.Icons.FILTER_ALT
                self.btn_dupes.text = "Duplicates"
            self._after_data_change()
            self.notify("Row updated" if is_edit else "Row appended")

        def do_cancel(e=None) -> None:
            self._dialog_open = False
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Container(
                width=540,
                height=460,
                content=ft.Column(
                    [error_banner, *form_controls],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    tight=True,
                ),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=do_cancel),
                ft.FilledButton("Save", icon=ft.Icons.CHECK, on_click=do_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            # Reset the guard if the dialog is dismissed out-of-band (Escape /
            # barrier tap) so keyboard shortcuts don't stay disabled forever.
            on_dismiss=lambda e: setattr(self, "_dialog_open", False),
        )
        self._dialog_open = True
        self.page.open(dlg)

    # ------------------------------------------------------------- help

    def _close_help(self, dlg: ft.AlertDialog) -> None:
        self._dialog_open = False
        self.page.close(dlg)

    def _open_help(self) -> None:
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Help"),
            content=ft.Container(
                width=600,
                height=520,
                content=ft.Column(
                    [ft.Markdown(HELP_TEXT, selectable=True)],
                    scroll=ft.ScrollMode.AUTO,
                ),
            ),
            actions=[ft.FilledButton("Close", on_click=lambda e: self._close_help(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=lambda e: setattr(self, "_dialog_open", False),
        )
        self._dialog_open = True
        self.page.open(dlg)

    # ------------------------------------------------------------- keyboard

    def _quit(self) -> None:
        for attempt in (
            lambda: self.page.window.close(),
            lambda: self.page.window.destroy(),
            lambda: self.page.window_destroy(),
        ):
            try:
                attempt()
                return
            except Exception:
                continue

    def _on_keyboard(self, e: ft.KeyboardEvent) -> None:
        # Page-level key events still fire while a dialog TextField is focused,
        # so suppress shortcuts whenever a dialog is open or a modifier is held.
        if self._dialog_open or e.ctrl or e.alt or e.meta:
            return
        key = (e.key or "").lower()
        actions = {
            "n": self.do_new_address_book,
            "o": self.do_open_file,
            "a": self.do_append_row,
            "e": self.do_edit_row,
            "d": self.do_delete_row,
            "f": self.do_toggle_dupes,
            "w": self.do_write_csv,
            "h": self._open_help,
            "q": self._quit,
        }
        handler = actions.get(key)
        if handler is not None:
            handler()


def _app_main(page: ft.Page) -> None:
    setup_logging()
    logger.info("Starting RingCentral CSV Editor %s", __version__)
    AddressBookGUI(page)


def run() -> None:
    """Console-script / module entry point."""
    ft.app(target=_app_main)


if __name__ == "__main__":
    run()
