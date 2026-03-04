"""Application settings with generic typed entries and YAML persistence."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import yaml

log = logging.getLogger(__name__)

SETTINGS_PATH = Path.home() / ".config" / "hakei" / "settings.yaml"


# ---------------------------------------------------------------------------
# Setting descriptors
# ---------------------------------------------------------------------------

class SettingKind(Enum):
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    COMBO = "combo"


class Setting:
    """A single named setting with type info and constraints."""

    def __init__(
        self,
        key: str,
        label: str,
        kind: SettingKind,
        default: Any,
        *,
        group: str = "General",
        tooltip: str = "",
        options: list[str] | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
    ):
        self.key = key
        self.label = label
        self.kind = kind
        self.default = default
        self.group = group
        self.tooltip = tooltip
        self.options = options or []
        self.min_value = min_value
        self.max_value = max_value


# ---------------------------------------------------------------------------
# Settings manager (singleton)
# ---------------------------------------------------------------------------

class SettingsManager:
    """Manages typed settings with YAML persistence and change callbacks."""

    def __init__(self) -> None:
        self._definitions: dict[str, Setting] = {}
        self._values: dict[str, Any] = {}
        self._callbacks: list[Callable[[str, Any], None]] = []
        self._loaded = False

    # -- definition ----------------------------------------------------------

    def define(self, setting: Setting) -> None:
        self._definitions[setting.key] = setting
        if setting.key not in self._values:
            self._values[setting.key] = setting.default

    # -- access --------------------------------------------------------------

    def get(self, key: str) -> Any:
        if key in self._values:
            return self._values[key]
        defn = self._definitions.get(key)
        return defn.default if defn else None

    def set(self, key: str, value: Any) -> None:
        defn = self._definitions.get(key)
        if defn:
            value = _coerce(value, defn)
        old = self._values.get(key)
        self._values[key] = value
        if value != old:
            for cb in self._callbacks:
                try:
                    cb(key, value)
                except Exception:
                    log.exception("Settings callback error for %s", key)

    def on_change(self, callback: Callable[[str, Any], None]) -> None:
        self._callbacks.append(callback)

    @property
    def definitions(self) -> dict[str, Setting]:
        return dict(self._definitions)

    # -- persistence ---------------------------------------------------------

    def load(self, path: Path | None = None) -> None:
        path = path or SETTINGS_PATH
        if not path.exists():
            log.debug("No settings file at %s", path)
            self._loaded = True
            return
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            for key, val in data.items():
                defn = self._definitions.get(key)
                if defn:
                    self._values[key] = _coerce(val, defn)
                else:
                    self._values[key] = val
            log.info("Settings loaded from %s", path)
        except Exception:
            log.exception("Failed to load settings from %s", path)
        self._loaded = True

    def save(self, path: Path | None = None) -> None:
        path = path or SETTINGS_PATH
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for key, defn in self._definitions.items():
                val = self._values.get(key, defn.default)
                data[key] = val
            with open(path, "w") as f:
                yaml.safe_dump(
                    data, f,
                    default_flow_style=False,
                    sort_keys=False,
                )
            log.info("Settings saved to %s", path)
        except Exception:
            log.exception("Failed to save settings to %s", path)


def _coerce(value: Any, defn: Setting) -> Any:
    """Coerce a raw value to the expected type."""
    try:
        if defn.kind == SettingKind.BOOL:
            return bool(value)
        if defn.kind == SettingKind.INT:
            v = int(value)
            if defn.min_value is not None:
                v = max(int(defn.min_value), v)
            if defn.max_value is not None:
                v = min(int(defn.max_value), v)
            return v
        if defn.kind == SettingKind.FLOAT:
            v = float(value)
            if defn.min_value is not None:
                v = max(defn.min_value, v)
            if defn.max_value is not None:
                v = min(defn.max_value, v)
            return v
        if defn.kind == SettingKind.STRING:
            return str(value)
        if defn.kind == SettingKind.COMBO:
            s = str(value)
            if defn.options and s not in defn.options:
                return defn.default
            return s
    except (TypeError, ValueError):
        return defn.default
    return value


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_manager: SettingsManager | None = None


def get_manager() -> SettingsManager:
    global _manager
    if _manager is None:
        _manager = SettingsManager()
        _register_builtin_settings(_manager)
        _manager.load()
    return _manager


# ---------------------------------------------------------------------------
# Built-in settings definitions
# ---------------------------------------------------------------------------

def _register_builtin_settings(
    mgr: SettingsManager,
) -> None:
    mgr.define(Setting(
        "ui.show_fps",
        "Show FPS counter",
        SettingKind.BOOL,
        False,
        group="Interface",
        tooltip="Display an FPS counter in the title bar",
    ))
    mgr.define(Setting(
        "ui.theme",
        "Theme",
        SettingKind.COMBO,
        "Dark",
        group="Interface",
        options=["Dark", "Light"],
        tooltip="Color theme (requires restart)",
    ))
    mgr.define(Setting(
        "startup.load_session",
        "Load previous session on startup",
        SettingKind.BOOL,
        True,
        group="Startup",
        tooltip="Restore instruments from last session",
    ))
    mgr.define(Setting(
        "startup.auto_connect",
        "Auto-connect devices on startup",
        SettingKind.BOOL,
        True,
        group="Startup",
        tooltip="Automatically connect to devices on launch",
    ))
    mgr.define(Setting(
        "acquisition.default_timebase",
        "Default timebase span (s)",
        SettingKind.FLOAT,
        0.1,
        group="Instruments",
        tooltip="Default horizontal span for new scopes",
        min_value=1e-6,
        max_value=100.0,
    ))
    mgr.define(Setting(
        "data.export_format",
        "Default export format",
        SettingKind.COMBO,
        "CSV",
        group="Data",
        options=["CSV", "NumPy", "HDF5"],
        tooltip="Format for waveform data export",
    ))


# ---------------------------------------------------------------------------
# Settings window (DearPyGui)
# ---------------------------------------------------------------------------

_WINDOW_TAG = "settings_window"


def show_settings_window() -> None:
    """Open (or focus) the settings window."""
    import dearpygui.dearpygui as dpg

    if dpg.does_item_exist(_WINDOW_TAG):
        dpg.focus_item(_WINDOW_TAG)
        return

    mgr = get_manager()
    groups: dict[str, list[Setting]] = {}
    for defn in mgr.definitions.values():
        groups.setdefault(defn.group, []).append(defn)

    with dpg.window(
        label="Settings",
        tag=_WINDOW_TAG,
        width=480,
        height=400,
        on_close=lambda: dpg.delete_item(_WINDOW_TAG),
    ):
        for group_name, settings in groups.items():
            dpg.add_text(group_name, color=(180, 210, 255))
            dpg.add_separator()

            for s in settings:
                tag = f"settings_{s.key}"
                with dpg.group(horizontal=True):
                    _add_widget(dpg, mgr, s, tag)
                    if s.tooltip:
                        with dpg.tooltip(dpg.last_item()):
                            dpg.add_text(s.tooltip)

            dpg.add_spacer(height=8)


def _add_widget(
    dpg, mgr: SettingsManager, s: Setting, tag: str,
) -> None:
    """Add the DearPyGui widget for a setting."""

    cur = mgr.get(s.key)

    setting_key = s.key

    def _cb(sender, value, _user_data=None):
        mgr.set(setting_key, value)
        mgr.save()

    if s.kind == SettingKind.BOOL:
        dpg.add_checkbox(
            label=s.label,
            default_value=cur,
            tag=tag,
            callback=_cb,
        )

    elif s.kind == SettingKind.INT:
        dpg.add_text(f"{s.label}:")
        kw: dict[str, Any] = dict(
            default_value=cur,
            tag=tag,
            callback=_cb,
            width=120,
            step=1,
        )
        if s.min_value is not None:
            kw["min_value"] = int(s.min_value)
            kw["min_clamped"] = True
        if s.max_value is not None:
            kw["max_value"] = int(s.max_value)
            kw["max_clamped"] = True
        dpg.add_input_int(**kw)

    elif s.kind == SettingKind.FLOAT:
        dpg.add_text(f"{s.label}:")
        kw = dict(
            default_value=cur,
            tag=tag,
            callback=_cb,
            width=120,
            step=0,
            format="%.6g",
        )
        if s.min_value is not None:
            kw["min_value"] = s.min_value
            kw["min_clamped"] = True
        if s.max_value is not None:
            kw["max_value"] = s.max_value
            kw["max_clamped"] = True
        dpg.add_input_float(**kw)

    elif s.kind == SettingKind.STRING:
        dpg.add_text(f"{s.label}:")
        dpg.add_input_text(
            default_value=cur,
            tag=tag,
            callback=_cb,
            width=200,
        )

    elif s.kind == SettingKind.COMBO:
        dpg.add_text(f"{s.label}:")
        dpg.add_combo(
            items=s.options,
            default_value=cur,
            tag=tag,
            callback=_cb,
            width=150,
        )
