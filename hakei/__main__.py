#!/usr/bin/env python3
"""Hakei - Electronic Bench Equipment Controller

A visualization and control application for oscilloscopes,
power supplies, and waveform generators.
"""

import logging
import time

import click
from click_loglevel import LogLevel
import coloredlogs
import dearpygui.dearpygui as dpg

from hakei.config import get_initial_viewport_size
from hakei.ui.instrument_panel import (
    load_default_config,
    save_default_config,
    setup_instrument_panel,
)
from hakei.ui.layout import get_manager, setup_resize_handler
from hakei.ui.menu import setup_menu_bar
from hakei.ui.theme import create_primary_window, setup_theme

log = logging.getLogger(__name__)

APP_TITLE = "hakei"


class _FpsCounter:
    """Tracks frame times and updates the viewport title."""

    def __init__(self, window: float = 0.5):
        self._window = window
        self._frame_count = 0
        self._last_time = time.monotonic()
        self._enabled = False

    def tick(self) -> None:
        if not self._enabled:
            return
        self._frame_count += 1
        now = time.monotonic()
        elapsed = now - self._last_time
        if elapsed >= self._window:
            fps = self._frame_count / elapsed
            dpg.set_viewport_title(
                f"{APP_TITLE}  [{fps:.0f} FPS]"
            )
            self._frame_count = 0
            self._last_time = now

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        if not enabled:
            dpg.set_viewport_title(APP_TITLE)
        else:
            self._frame_count = 0
            self._last_time = time.monotonic()


_fps = _FpsCounter()


def _on_setting_changed(key: str, value) -> None:
    if key == "ui.show_fps":
        _fps.set_enabled(bool(value))


@click.command()
@click.option('--log-level', type=LogLevel(), default='INFO', help='Set the logging level (CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET).')
def main(log_level):
    coloredlogs.install(
        level=log_level,
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    log.info("starting hakei")

    dpg.create_context()

    setup_theme()

    viewport_width, viewport_height = get_initial_viewport_size()
    dpg.create_viewport(
        title=APP_TITLE,
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

    load_default_config()

    from hakei.settings import get_manager as get_settings
    settings = get_settings()
    settings.on_change(_on_setting_changed)
    _fps.set_enabled(settings.get("ui.show_fps"))

    while dpg.is_dearpygui_running():
        manager.check_window_drag()
        manager.run_updates()
        dpg.render_dearpygui_frame()
        _fps.tick()

    save_default_config()
    settings.save()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
