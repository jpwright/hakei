#!/usr/bin/env python3
"""Hakei - Electronic Bench Equipment Controller

A visualization and control application for oscilloscopes,
power supplies, and waveform generators.
"""

import logging

import coloredlogs
import dearpygui.dearpygui as dpg

from hakei.config import get_initial_viewport_size
from hakei.ui.instrument_panel import load_default_config, save_default_config, setup_instrument_panel
from hakei.ui.layout import get_manager, setup_resize_handler
from hakei.ui.menu import setup_menu_bar
from hakei.ui.theme import create_primary_window, setup_theme

log = logging.getLogger(__name__)


def main():
    coloredlogs.install(
        level=logging.INFO,
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    log.info("starting hakei")

    dpg.create_context()

    setup_theme()

    viewport_width, viewport_height = get_initial_viewport_size()
    dpg.create_viewport(
        title="hakei",
        width=viewport_width,
        height=viewport_height,
        min_width=800,
        min_height=600,
    )

    create_primary_window()
    setup_menu_bar()
    setup_instrument_panel()

    setup_resize_handler()

    dpg.setup_dearpygui()
    dpg.show_viewport()

    manager = get_manager()
    manager.on_viewport_resize()

    # Load default configuration
    load_default_config()

    while dpg.is_dearpygui_running():
        manager.check_window_drag()
        manager.run_updates()
        dpg.render_dearpygui_frame()

    # Save configuration before exiting
    save_default_config()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
