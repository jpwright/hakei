#!/usr/bin/env python3
"""Hakei - Electronic Bench Equipment Controller

A visualization and control application for oscilloscopes,
power supplies, and waveform generators.
"""

import logging

import dearpygui.dearpygui as dpg

from hakei.ui.device_panel import setup_device_panel
from hakei.ui.menu import setup_menu_bar
from hakei.ui.theme import create_primary_window, setup_theme
from hakei.ui.views.oscilloscope import setup_oscilloscope_view
from hakei.ui.views.power_supply import setup_power_supply_view
from hakei.ui.views.waveform_gen import setup_waveform_gen_view

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    dpg.create_context()

    try:
        setup_theme()

        dpg.create_viewport(
            title="Hakei",
            width=1280,
            height=960,
            min_width=800,
            min_height=600,
        )

        create_primary_window()
        setup_menu_bar()
        setup_device_panel()
        setup_oscilloscope_view()
        setup_power_supply_view()
        setup_waveform_gen_view()

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()

    except Exception:
        log.exception("Fatal error")
        raise
    finally:
        dpg.destroy_context()


if __name__ == "__main__":
    main()
