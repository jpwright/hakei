#!/usr/bin/env python3
"""Hakei - Electronic Bench Equipment Controller

A visualization and control application for oscilloscopes,
power supplies, and waveform generators.
"""

import logging

import coloredlogs
import dearpygui.dearpygui as dpg

from hakei.ui.device_panel import setup_device_panel
from hakei.ui.layout import get_manager, setup_resize_handler
from hakei.ui.menu import setup_menu_bar
from hakei.ui.theme import create_primary_window, setup_theme
from hakei.ui.views.oscilloscope import setup_oscilloscope_view
from hakei.ui.views.power_supply import setup_power_supply_view
from hakei.ui.views.waveform_gen import setup_waveform_gen_view

log = logging.getLogger(__name__)


def main():
    coloredlogs.install(
        level=logging.INFO,
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    log.info("starting hakei")

    dpg.create_context()

    setup_theme()

    dpg.create_viewport(
        title="hakei",
        width=1600,
        height=1000,
        min_width=800,
        min_height=600,
    )

    create_primary_window()
    setup_menu_bar()
    setup_device_panel()
    setup_oscilloscope_view()
    setup_power_supply_view(num_channels=2)
    setup_waveform_gen_view()

    setup_resize_handler()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.maximize_viewport()

    manager = get_manager()
    manager.on_viewport_resize()

    while dpg.is_dearpygui_running():
        manager.check_window_drag()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
