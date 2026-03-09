"""Menu bar setup for Hakei."""

import logging
from importlib.metadata import version
from pathlib import Path

import dearpygui.dearpygui as dpg

from hakei.ui.fdialog import FileDialog


def _get_version() -> str:
    """Return the application version from package metadata."""
    try:
        return version("hakei")
    except Exception:
        from hakei import __version__
        return __version__

log = logging.getLogger(__name__)

_save_dialog: FileDialog | None = None
_load_dialog: FileDialog | None = None


def _on_exit():
    dpg.stop_dearpygui()


def _on_save_config():
    """Show file dialog for saving configuration."""
    if _save_dialog:
        _save_dialog.show_file_dialog()


def _on_load_config():
    """Show file dialog for loading configuration."""
    if _load_dialog:
        _load_dialog.show_file_dialog()


def _on_save_file_selected(selected_files: list[str]):
    """Handle save file selection."""
    from hakei.ui.instrument_panel import save_config_to_file

    if not selected_files:
        log.warning("No file selected for save")
        return

    file_path = Path(selected_files[0])
    if not file_path.suffix:
        file_path = file_path.with_suffix(".hakei")

    if save_config_to_file(file_path):
        log.info("Configuration saved to %s", file_path)
    else:
        log.error("Failed to save configuration to %s", file_path)


def _on_load_file_selected(selected_files: list[str]):
    """Handle load file selection."""
    from hakei.ui.instrument_panel import load_config_from_file

    if not selected_files:
        return

    file_path = Path(selected_files[0])

    if not file_path.is_file():
        log.warning("Selected path is not a file: %s", file_path)
        return

    if load_config_from_file(file_path):
        log.info("Configuration loaded from %s", file_path)
    else:
        log.error("Failed to load configuration from %s", file_path)


def _on_settings():
    """Open the settings window."""
    from hakei.settings import show_settings_window
    show_settings_window()


def _on_about():
    """Show the About dialog with version info."""
    ver = _get_version()
    with dpg.window(label="about", tag="about_window", modal=True):
        with dpg.table(header_row=False, policy=dpg.mvTable_SizingStretchProp):
            dpg.add_table_column()
            dpg.add_table_column()
            dpg.add_table_column()
            with dpg.table_row():
                dpg.add_spacer()
                dpg.add_text(f"version {ver}")
                dpg.add_spacer()
        dpg.add_separator()
        with dpg.table(header_row=False):
            dpg.add_table_column()
            dpg.add_table_column()
            dpg.add_table_column()
            with dpg.table_row():
                dpg.add_spacer()
                dpg.add_button(label="OK", callback=lambda: dpg.delete_item("about_window"))
                dpg.add_spacer()


def setup_menu_bar():
    """Create the application menu bar."""
    global _save_dialog, _load_dialog

    _save_dialog = FileDialog(
        title="Save Configuration",
        tag="save_config_fd",
        width=1000,
        height=700,
        default_path=str(Path.home()),
        dirs_only=False,
        callback=_on_save_file_selected,
        multi_selection=False,
        show_hidden_files=False,
        filter_list=[".hakei"],
        file_filter=".hakei",
        modal=False,
        default_filename="config.hakei",
    )

    _load_dialog = FileDialog(
        title="Load Configuration",
        tag="load_config_fd",
        width=1000,
        height=700,
        default_path=str(Path.home()),
        dirs_only=False,
        callback=_on_load_file_selected,
        multi_selection=False,
        show_hidden_files=False,
        filter_list=[".hakei"],
        file_filter=".hakei",
        modal=False,
    )

    with dpg.viewport_menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Save Configuration...", callback=_on_save_config)
            dpg.add_menu_item(label="Load Configuration...", callback=_on_load_config)
            dpg.add_separator()
            dpg.add_menu_item(label="Export Data")
            dpg.add_separator()
            dpg.add_menu_item(label="Settings...", callback=_on_settings)
            dpg.add_separator()
            dpg.add_menu_item(label="Exit", callback=_on_exit)

        with dpg.menu(label="Help"):
            dpg.add_menu_item(label="Documentation")
            dpg.add_menu_item(label="About", callback=_on_about)
