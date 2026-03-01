"""Menu bar setup for Hakei."""

import dearpygui.dearpygui as dpg


def _on_exit():
    dpg.stop_dearpygui()


def setup_menu_bar():
    """Create the application menu bar."""
    with dpg.viewport_menu_bar():
        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Save Configuration")
            dpg.add_menu_item(label="Load Configuration")
            dpg.add_separator()
            dpg.add_menu_item(label="Export Data")
            dpg.add_separator()
            dpg.add_menu_item(label="Exit", callback=_on_exit)

        with dpg.menu(label="Devices"):
            dpg.add_menu_item(label="Scan for Devices")
            dpg.add_menu_item(label="Add Device Manually")
            dpg.add_separator()
            dpg.add_menu_item(label="Disconnect All")

        with dpg.menu(label="View"):
            dpg.add_menu_item(label="Oscilloscope", check=True, default_value=True)
            dpg.add_menu_item(label="Power Supply", check=True, default_value=True)
            dpg.add_menu_item(label="Waveform Generator", check=True, default_value=True)
            dpg.add_separator()
            dpg.add_menu_item(label="Show Device Panel", check=True, default_value=True)

        with dpg.menu(label="Help"):
            dpg.add_menu_item(label="Documentation")
            dpg.add_menu_item(label="About")
