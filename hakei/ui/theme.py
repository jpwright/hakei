"""UI theming and styling for Hakei."""

import logging
import os
import subprocess
from pathlib import Path

import dearpygui.dearpygui as dpg

log = logging.getLogger(__name__)


def _create_disabled_theme():
    with dpg.theme_component(dpg.mvAll, enabled_state=False):
        # Text
        dpg.add_theme_color(dpg.mvThemeCol_Text, (90, 90, 95))
        dpg.add_theme_color(dpg.mvThemeCol_TextSelectedBg, (50, 55, 65))
        # Frames (inputs, combos, text fields)
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (38, 38, 42))
        dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (38, 38, 42))
        dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (38, 38, 42))
        # Borders
        dpg.add_theme_color(dpg.mvThemeCol_Border, (50, 50, 55))
        dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))
        # Buttons (including combo dropdown arrow)
        dpg.add_theme_color(dpg.mvThemeCol_Button, (38, 55, 80))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (38, 55, 80))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (38, 55, 80))
        # Headers / selectables
        dpg.add_theme_color(dpg.mvThemeCol_Header, (38, 55, 80))
        dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (38, 55, 80))
        dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (38, 55, 80))
        # Sliders / drag inputs
        dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (55, 70, 90))
        dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (55, 70, 90))
        # Checkboxes / radio buttons
        dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (90, 90, 100))
        # Scrollbars (text inputs with overflow)
        dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (30, 30, 34))
        dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (50, 55, 60))
        dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (50, 55, 60))
        dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (50, 55, 60))

def setup_theme():
    """Create and apply the application theme."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)

            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (30, 30, 35))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (20, 20, 25))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (35, 85, 140))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (45, 45, 50))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (60, 60, 70))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (50, 100, 160))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (60, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (70, 140, 210))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (50, 100, 160))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (60, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (40, 40, 50))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (60, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (50, 100, 160))

        _create_disabled_theme()

    dpg.bind_theme(global_theme)


_disabled_theme: int | None = None


def get_disabled_theme() -> int:
    """Return a bindable theme for explicitly disabled items.

    Use when DearPyGui's enabled_state=False global selector doesn't fire
    for a specific widget type (e.g. mvInputFloat).  Bind this theme to the
    item when disabling it and pass 0 to dpg.bind_item_theme() to restore
    the global theme when re-enabling.
    """
    global _disabled_theme
    if _disabled_theme is not None:
        return _disabled_theme

    with dpg.theme() as _disabled_theme:
        _create_disabled_theme()

    return _disabled_theme


def get_dpi_scale() -> float:
    """Detect system DPI scale factor."""
    scale = 1.0

    if os.environ.get("GDK_SCALE"):
        try:
            scale = float(os.environ["GDK_SCALE"])
            return scale
        except ValueError:
            pass

    if os.environ.get("QT_SCALE_FACTOR"):
        try:
            scale = float(os.environ["QT_SCALE_FACTOR"])
            return scale
        except ValueError:
            pass

    try:
        result = subprocess.run(
            ["xrdb", "-query"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        for line in result.stdout.splitlines():
            if "Xft.dpi:" in line:
                dpi = float(line.split(":")[1].strip())
                scale = dpi / 96.0
                return scale
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass

    return scale


def get_font_path():
    """Get the path to the bundled font."""
    return Path(__file__).parent.parent / "fonts" / "Inter.ttf"


def create_primary_window():
    """Create the primary window with font setup."""
    scale = get_dpi_scale()
    font_path = get_font_path()
    font_size = int(18 * scale)

    with dpg.window(tag="primary_window", no_scrollbar=True):
        if font_path.exists():
            log.debug("Loading font from %s at size %d", font_path, font_size)
            with dpg.font_registry():
                with dpg.font(str(font_path), font_size, tag="main-font") as font:
                    dpg.bind_font(font)
        else:
            log.warning("Font not found: %s", font_path)

    dpg.set_primary_window("primary_window", True)
