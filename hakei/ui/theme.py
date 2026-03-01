"""UI theming and styling for Hakei."""

import logging
import os
import subprocess
from pathlib import Path

import dearpygui.dearpygui as dpg

log = logging.getLogger(__name__)


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

    dpg.bind_theme(global_theme)


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
