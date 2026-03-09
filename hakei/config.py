"""Configuration save/load functionality."""

import json
import logging
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "hakei" / "default.hakei"
CONFIG_DIR = Path.home() / ".config" / "hakei"


class PowerSupplyChannelConfig(BaseModel):
    """Configuration for a power supply channel."""

    voltage_setpoint: float = 0.0
    current_limit: float = 1.0
    output_enabled: bool = False


class PowerSupplyConfig(BaseModel):
    """Configuration for a power supply instrument."""

    type: Literal["power_supply"] = "power_supply"
    resource_address: str
    channels: list[PowerSupplyChannelConfig] = Field(default_factory=list)


class OscilloscopeChannelConfig(BaseModel):
    """Configuration for an oscilloscope channel."""

    enabled: bool = False
    scale: float = 1.0
    offset: float = 0.0
    coupling: str = "DC"


class OscilloscopeConfig(BaseModel):
    """Configuration for an oscilloscope instrument."""

    type: Literal["oscilloscope"] = "oscilloscope"
    resource_address: str
    channels: list[OscilloscopeChannelConfig] = Field(default_factory=list)
    timebase_span: float = 10e-3
    trigger_enabled: bool = False
    trigger_source: int = 1
    trigger_mode: str = "AUTO"
    trigger_edge: str = "RISING"
    trigger_level: float = 0.0
    trigger_position: float = 0.0
    trigger_holdoff: float = 0.0
    display_mode_x: str = "NORMAL"
    display_mode_y: str = "OVERLAY"
    # Axis limits (UI state)
    x_axis_min: float = -10.0
    x_axis_max: float = 10.0
    y_axis_min: float = -5.0
    y_axis_max: float = 5.0


class WaveformGeneratorChannelConfig(BaseModel):
    """Configuration for a waveform generator channel."""

    output_enabled: bool = False
    waveform: str = "SINE"
    frequency: float = 1000.0
    amplitude: float = 1.0
    offset: float = 0.0
    phase: float = 0.0


class WaveformGeneratorConfig(BaseModel):
    """Configuration for a waveform generator instrument."""

    type: Literal["waveform_generator"] = "waveform_generator"
    resource_address: str
    channels: list[WaveformGeneratorChannelConfig] = Field(default_factory=list)


InstrumentConfig = Annotated[
    PowerSupplyConfig | OscilloscopeConfig | WaveformGeneratorConfig,
    Field(discriminator="type"),
]


class PanelLayoutConfig(BaseModel):
    """Configuration for a panel's layout."""

    resource_address: str
    height: int = 300


class WindowConfig(BaseModel):
    """Configuration for the application window."""

    viewport_width: int = 1600
    viewport_height: int = 1000
    sidebar_width: int = 280
    panels: list[PanelLayoutConfig] = Field(default_factory=list)


class HakeiConfig(BaseModel):
    """Root configuration for Hakei application."""

    instruments: list[InstrumentConfig] = Field(default_factory=list)
    window: WindowConfig = Field(default_factory=WindowConfig)


def ensure_config_dir() -> None:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_config(config: HakeiConfig, path: Path | None = None) -> bool:
    """
    Save configuration to a JSON file.

    Args:
        config: The configuration to save.
        path: Path to save to. If None, saves to default location.

    Returns:
        True if successful, False otherwise.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH

    try:
        ensure_config_dir()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(config.model_dump(), f, indent=2)
        log.info("Configuration saved to %s", path)
        return True
    except Exception as e:
        log.error("Failed to save configuration: %s", e)
        return False


def load_config(path: Path | None = None) -> HakeiConfig | None:
    """
    Load configuration from a JSON file.

    Args:
        path: Path to load from. If None, loads from default location.

    Returns:
        The loaded configuration, or None if loading failed.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH

    if not path.exists():
        log.debug("Configuration file not found: %s", path)
        return None

    try:
        with open(path) as f:
            data = json.load(f)
        config = HakeiConfig.model_validate(data)
        log.info("Configuration loaded from %s", path)
        return config
    except Exception as e:
        log.error("Failed to load configuration: %s", e)
        return None


def get_default_config() -> HakeiConfig:
    """Get the default configuration."""
    return HakeiConfig()


def build_window_config() -> WindowConfig:
    """Build window configuration from current layout state."""
    import dearpygui.dearpygui as dpg

    from hakei.ui.layout import get_manager

    manager = get_manager()
    window_config = WindowConfig(
        viewport_width=dpg.get_viewport_width(),
        viewport_height=dpg.get_viewport_height(),
        sidebar_width=manager._sidebar_width,
    )

    for window in manager.windows:
        window_config.panels.append(
            PanelLayoutConfig(
                resource_address=window.tag,
                height=window.last_height,
            )
        )

    return window_config


def build_config_from_instruments(
    instruments: dict[str, Any],
    panels: dict[str, Any] | None = None,
) -> HakeiConfig:
    """
    Build a configuration from currently open instruments.

    Args:
        instruments: Dictionary mapping resource addresses to instrument objects.
        panels: Optional dictionary mapping resource addresses to UI panels.

    Returns:
        Configuration capturing current instrument states.
    """
    from hakei.instruments.oscilloscope import Oscilloscope
    from hakei.instruments.power_supply import PowerSupply
    from hakei.instruments.waveform_generator import WaveformGenerator

    panels = panels or {}
    config = HakeiConfig()
    config.window = build_window_config()

    for address, instrument in instruments.items():
        if isinstance(instrument, PowerSupply):
            psu_config = PowerSupplyConfig(resource_address=address)
            for ch in range(1, instrument.num_channels + 1):
                state = instrument.get_channel_state(ch)
                psu_config.channels.append(
                    PowerSupplyChannelConfig(
                        voltage_setpoint=state.voltage_setpoint,
                        current_limit=state.current_limit,
                        output_enabled=state.output_enabled,
                    )
                )
            config.instruments.append(psu_config)

        elif isinstance(instrument, Oscilloscope):
            osc_config = OscilloscopeConfig(resource_address=address)
            for ch in range(1, instrument.num_channels + 1):
                ch_config = instrument.get_channel_config(ch)
                osc_config.channels.append(
                    OscilloscopeChannelConfig(
                        enabled=ch_config.enabled,
                        scale=ch_config.scale,
                        offset=ch_config.offset,
                        coupling=ch_config.coupling.name,
                    )
                )
            osc_config.timebase_span = instrument.timebase.span
            osc_config.trigger_enabled = instrument.trigger.enabled
            osc_config.trigger_source = instrument.trigger.source
            osc_config.trigger_mode = instrument.trigger.mode.name
            osc_config.trigger_edge = instrument.trigger.edge.name
            osc_config.trigger_level = instrument.trigger.level
            osc_config.trigger_position = instrument.trigger.position
            osc_config.trigger_holdoff = instrument.trigger.holdoff
            osc_config.display_mode_x = instrument.display_mode_x.name
            osc_config.display_mode_y = instrument.display_mode_y.name
            # Get axis limits from panel if available
            panel = panels.get(address)
            if panel and hasattr(panel, 'get_axis_limits'):
                x_limits, y_limits = panel.get_axis_limits()
                osc_config.x_axis_min = x_limits[0]
                osc_config.x_axis_max = x_limits[1]
                osc_config.y_axis_min = y_limits[0]
                osc_config.y_axis_max = y_limits[1]
            config.instruments.append(osc_config)

        elif isinstance(instrument, WaveformGenerator):
            wfg_config = WaveformGeneratorConfig(resource_address=address)
            for ch in range(1, instrument.num_channels + 1):
                ch_config = instrument.get_channel_config(ch)
                wfg_config.channels.append(
                    WaveformGeneratorChannelConfig(
                        output_enabled=ch_config.output_enabled,
                        waveform=ch_config.waveform.name,
                        frequency=ch_config.frequency,
                        amplitude=ch_config.amplitude,
                        offset=ch_config.offset,
                        phase=ch_config.phase,
                    )
                )
            config.instruments.append(wfg_config)

    return config


def apply_config_to_instrument(instrument: Any, config: InstrumentConfig) -> None:
    """
    Apply configuration to an instrument.

    Args:
        instrument: The instrument to configure.
        config: The configuration to apply.
    """
    from hakei.instruments.oscilloscope import Coupling, Oscilloscope, TriggerMode
    from hakei.instruments.power_supply import PowerSupply
    from hakei.instruments.waveform_generator import WaveformGenerator, WaveformType

    if isinstance(instrument, PowerSupply) and isinstance(config, PowerSupplyConfig):
        for ch, ch_config in enumerate(config.channels, start=1):
            if ch <= instrument.num_channels:
                instrument.set_voltage(ch, ch_config.voltage_setpoint)
                instrument.set_current_limit(ch, ch_config.current_limit)
                instrument.set_output_enabled(ch, ch_config.output_enabled)

    elif isinstance(instrument, Oscilloscope) and isinstance(config, OscilloscopeConfig):
        from hakei.instruments.oscilloscope import TriggerEdge

        for ch, ch_config in enumerate(config.channels, start=1):
            if ch <= instrument.num_channels:
                instrument.set_channel_enabled(ch, ch_config.enabled)
                instrument.set_channel_scale(ch, ch_config.scale)
                instrument.set_channel_offset(ch, ch_config.offset)
                try:
                    coupling = Coupling[ch_config.coupling]
                    instrument.set_channel_coupling(ch, coupling)
                except KeyError:
                    pass

        instrument.set_timebase_span(config.timebase_span)
        instrument.set_trigger_source(config.trigger_source)
        try:
            mode = TriggerMode[config.trigger_mode]
            instrument.set_trigger_mode(mode)
        except KeyError:
            pass
        try:
            edge = TriggerEdge[config.trigger_edge]
            instrument.set_trigger_edge(edge)
        except KeyError:
            pass
        instrument.set_trigger_level(config.trigger_level)
        instrument.set_trigger_position(config.trigger_position)
        instrument.set_trigger_holdoff(config.trigger_holdoff)
        instrument.set_trigger_enabled(config.trigger_enabled)

        from hakei.instruments.oscilloscope import DisplayModeX, DisplayModeY
        try:
            instrument.set_display_mode_x(DisplayModeX[config.display_mode_x])
        except KeyError:
            pass
        try:
            instrument.set_display_mode_y(DisplayModeY[config.display_mode_y])
        except KeyError:
            pass

    elif isinstance(instrument, WaveformGenerator) and isinstance(
        config, WaveformGeneratorConfig
    ):
        for ch, ch_config in enumerate(config.channels, start=1):
            if ch <= instrument.num_channels:
                try:
                    waveform = WaveformType[ch_config.waveform]
                    instrument.set_waveform(ch, waveform)
                except KeyError:
                    pass
                instrument.set_frequency(ch, ch_config.frequency)
                instrument.set_amplitude(ch, ch_config.amplitude)
                instrument.set_offset(ch, ch_config.offset)
                instrument.set_phase(ch, ch_config.phase)
                instrument.set_output_enabled(ch, ch_config.output_enabled)


def get_initial_viewport_size() -> tuple[int, int]:
    """Get viewport size from saved config, or defaults if none exists."""
    config = load_config()
    if config is not None:
        return config.window.viewport_width, config.window.viewport_height
    return 1600, 1000


def apply_window_config(config: WindowConfig) -> None:
    """Apply window configuration to restore layout state."""
    import dearpygui.dearpygui as dpg

    from hakei.ui.layout import get_manager

    manager = get_manager()
    manager._sidebar_width = config.sidebar_width
    manager._last_sidebar_width = config.sidebar_width

    try:
        dpg.set_item_width("instrument_panel", config.sidebar_width)
    except Exception:
        pass

    panel_heights = {p.resource_address: p.height for p in config.panels}
    for window in manager.windows:
        if window.tag in panel_heights:
            window.last_height = panel_heights[window.tag]
            window.preferred_height = panel_heights[window.tag]


def apply_config_to_panel(panel: Any, config: InstrumentConfig) -> None:
    """
    Apply UI-specific configuration to a panel.

    Args:
        panel: The UI panel to configure.
        config: The configuration to apply.
    """
    if isinstance(config, OscilloscopeConfig) and hasattr(panel, 'set_axis_limits'):
        panel.set_axis_limits(
            config.x_axis_min,
            config.x_axis_max,
            config.y_axis_min,
            config.y_axis_max,
        )
