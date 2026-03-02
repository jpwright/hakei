"""Oscilloscope view and controls."""

import logging
import time

import dearpygui.dearpygui as dpg
import numpy as np

from hakei.instruments.oscilloscope import (
    AcquisitionState,
    Coupling,
    DisplayMode,
    Oscilloscope,
    TriggerEdge,
    TriggerMode,
)
from hakei.ui.layout import get_manager
from hakei.ui.views.base import InstrumentPanel

log = logging.getLogger(__name__)

COUPLING_MAP = {
    "DC": Coupling.DC,
    "AC": Coupling.AC,
    "GND": Coupling.GND,
}

TRIGGER_MODE_MAP = {
    "Auto": TriggerMode.AUTO,
    "Normal": TriggerMode.NORMAL,
    "Single": TriggerMode.SINGLE,
}

TRIGGER_EDGE_MAP = {
    "Rising": TriggerEdge.RISING,
    "Falling": TriggerEdge.FALLING,
    "Either": TriggerEdge.EITHER,
}

DISPLAY_MODE_MAP = {
    "Normal": DisplayMode.NORMAL,
    "Screen": DisplayMode.SCREEN,
}

# Threshold for auto-roll: if x-axis span > 1 second, use roll behavior
AUTO_ROLL_THRESHOLD_MS = 1000.0

# ImPlot "Deep" colormap colors (default)
CHANNEL_COLORS = [
    (76, 114, 176, 255),   # Blue
    (221, 132, 82, 255),   # Orange
    (85, 168, 104, 255),   # Green
    (196, 78, 82, 255),    # Red
    (129, 114, 179, 255),  # Purple
    (147, 120, 96, 255),   # Brown
    (218, 139, 195, 255),  # Pink
    (140, 140, 140, 255),  # Gray
]


class OscilloscopeChannel:
    """A single oscilloscope channel UI module."""

    def __init__(
        self,
        channel_id: int,
        panel: "OscilloscopePanel",
        color: tuple[int, int, int, int] = (255, 255, 255, 255),
    ):
        self.channel_id = channel_id
        self.panel = panel
        self.color = color
        # Include panel tag to ensure uniqueness across multiple oscilloscopes
        self._tag_prefix = f"{panel.tag}_ch{channel_id}"
        self._enabled = channel_id == 1  # CH1 enabled by default

    @property
    def instrument(self) -> Oscilloscope | None:
        """Get instrument from parent panel (always current, not stale reference)."""
        return self.panel.instrument if self.panel else None

    @property
    def enable_tag(self) -> str:
        return f"{self._tag_prefix}_enable"

    @property
    def coupling_tag(self) -> str:
        return f"{self._tag_prefix}_coupling"

    @property
    def offset_tag(self) -> str:
        return f"{self._tag_prefix}_offset"

    @property
    def scale_tag(self) -> str:
        return f"{self._tag_prefix}_scale"

    @property
    def series_tag(self) -> str:
        return f"ch{self.channel_id}_series"

    @property
    def drag_line_tag(self) -> str:
        return f"{self._tag_prefix}_drag_line"

    def _on_enable(self, sender: str, value: bool) -> None:
        """Handle enable/disable."""
        self._enabled = value
        if self.instrument and hasattr(self.instrument, 'set_channel_enabled'):
            self.instrument.set_channel_enabled(self.channel_id, value)
        # Show/hide drag line
        if dpg.does_item_exist(self.drag_line_tag):
            dpg.configure_item(self.drag_line_tag, show=value)

    def _on_coupling(self, sender: str, value: str) -> None:
        """Handle coupling change."""
        if self.instrument and hasattr(self.instrument, 'set_channel_coupling') and value in COUPLING_MAP:
            self.instrument.set_channel_coupling(self.channel_id, COUPLING_MAP[value])

    def _on_offset(self, sender: str, value: float) -> None:
        """Handle offset change from input field."""
        if self.instrument and hasattr(self.instrument, 'set_channel_offset'):
            self.instrument.set_channel_offset(self.channel_id, value)
        # Update drag line position
        if dpg.does_item_exist(self.drag_line_tag):
            dpg.set_value(self.drag_line_tag, value)
        # Notify panel to update trigger line if this channel is trigger source
        if self.panel:
            self.panel._update_trigger_drag_line()

    def _on_drag_line(self, sender: str, app_data) -> None:
        """Handle offset change from drag line."""
        value = dpg.get_value(sender)
        if value is None:
            return
        value = float(value)
        if self.instrument and hasattr(self.instrument, 'set_channel_offset'):
            self.instrument.set_channel_offset(self.channel_id, value)
        # Update input field
        if dpg.does_item_exist(self.offset_tag):
            dpg.set_value(self.offset_tag, value)
        # Notify panel to update trigger line if this channel is trigger source
        if self.panel:
            self.panel._update_trigger_drag_line()

    def _on_scale(self, sender: str, value: float) -> None:
        """Handle scale change."""
        if self.instrument and hasattr(self.instrument, 'set_channel_scale'):
            self.instrument.set_channel_scale(self.channel_id, value)

    def build_ui(self) -> None:
        """Build the channel UI."""
        with dpg.child_window(
            width=180,
            height=180,
            no_scrollbar=True,
            border=True,
        ):
            # Channel header
            with dpg.group(horizontal=True):
                dpg.add_text(f"CH{self.channel_id}")
                dpg.add_spacer(width=10)
                dpg.add_checkbox(
                    label="Enable",
                    default_value=self._enabled,
                    tag=self.enable_tag,
                    callback=self._on_enable,
                )

            # Coupling
            with dpg.group(horizontal=True):
                dpg.add_text("Coupling:")
                dpg.add_combo(
                    items=list(COUPLING_MAP.keys()),
                    default_value="DC",
                    width=60,
                    tag=self.coupling_tag,
                    callback=self._on_coupling,
                )

            # Offset
            with dpg.group(horizontal=True):
                dpg.add_text("Offset:")
                dpg.add_input_float(
                    default_value=0.0,
                    width=70,
                    step=0,
                    tag=self.offset_tag,
                    callback=self._on_offset,
                )

            # Scale
            with dpg.group(horizontal=True):
                dpg.add_text("Scale:")
                dpg.add_input_float(
                    default_value=1.0,
                    width=70,
                    step=0,
                    min_value=0.001,
                    tag=self.scale_tag,
                    callback=self._on_scale,
                )

    def sync_from_instrument(self) -> None:
        """Sync UI state from instrument."""
        if not self.instrument:
            return
        
        # Check if instrument has required method (might be placeholder during connection)
        if not hasattr(self.instrument, 'get_channel_config'):
            return
        
        config = self.instrument.get_channel_config(self.channel_id)
        self._enabled = config.enabled
        if dpg.does_item_exist(self.enable_tag):
            dpg.set_value(self.enable_tag, config.enabled)
        if dpg.does_item_exist(self.offset_tag):
            dpg.set_value(self.offset_tag, config.offset)
        if dpg.does_item_exist(self.scale_tag):
            dpg.set_value(self.scale_tag, config.scale)
        # Update drag line visibility and position
        if dpg.does_item_exist(self.drag_line_tag):
            dpg.configure_item(self.drag_line_tag, show=config.enabled)
            dpg.set_value(self.drag_line_tag, config.offset)

    @property
    def enabled(self) -> bool:
        return self._enabled


class OscilloscopePanel(InstrumentPanel):
    """Oscilloscope instrument panel with modular channel displays."""

    NUM_POINTS = 1000

    _instance_counter = 0

    def __init__(self, instrument: Oscilloscope | None = None, num_channels: int = 2):
        # Generate unique tag for this panel instance
        OscilloscopePanel._instance_counter += 1
        instance_id = OscilloscopePanel._instance_counter
        unique_tag = f"scope_{instance_id}"
        
        super().__init__(
            tag=unique_tag,
            label="Oscilloscope",
            preferred_height=500,
            instrument=instrument,
        )
        self._num_channels = num_channels
        self._channels: list[OscilloscopeChannel] = []
        self._running = False
        self._update_registered = False
        self._last_x_min = -50.0
        self._last_x_max = 50.0
        self._display_mode = DisplayMode.NORMAL
        self._using_roll_behavior = False  # Track if currently using roll behavior

        # Buffers for roll/screen modes
        self._roll_time: dict[int, list[float]] = {}
        self._roll_voltage: dict[int, list[float]] = {}
        self._roll_start_time: float = 0.0
        self._last_sample_time: float = 0.0


        # Initialize channels
        for i in range(num_channels):
            color = CHANNEL_COLORS[i % len(CHANNEL_COLORS)]
            self._channels.append(
                OscilloscopeChannel(i + 1, panel=self, color=color)
            )
            self._roll_time[i + 1] = []
            self._roll_voltage[i + 1] = []

    @property
    def window_tag(self) -> str:
        return f"{self.tag}_window"

    @property
    def _plot_tag(self) -> str:
        return f"{self.tag}_plot"

    @property
    def _x_axis_tag(self) -> str:
        return f"{self.tag}_x_axis"

    @property
    def _y_axis_tag(self) -> str:
        return f"{self.tag}_y_axis"

    @property
    def _run_btn_tag(self) -> str:
        return f"{self.tag}_run_btn"

    @property
    def _status_tag(self) -> str:
        return f"{self.tag}_status"

    @property
    def _display_mode_tag(self) -> str:
        return f"{self.tag}_display_mode"

    @property
    def _trigger_enable_tag(self) -> str:
        return f"{self.tag}_trigger_enable"

    @property
    def _trigger_level_tag(self) -> str:
        return f"{self.tag}_trigger_level"

    @property
    def _trigger_source_tag(self) -> str:
        return f"{self.tag}_trigger_source"

    @property
    def _trigger_edge_tag(self) -> str:
        return f"{self.tag}_trigger_edge"

    @property
    def _trigger_mode_tag(self) -> str:
        return f"{self.tag}_trigger_mode"

    @property
    def _trigger_drag_line_tag(self) -> str:
        return f"{self.tag}_trigger_drag_line"

    @property
    def _roll_cursor_tag(self) -> str:
        return f"{self.tag}_roll_cursor"

    def _on_run_stop(self) -> None:
        """Toggle run/stop state."""
        if self._running:
            self._running = False
            if self.instrument and hasattr(self.instrument, 'stop'):
                self.instrument.stop()
            dpg.set_value(self._status_tag, "Status: Stopped")
            dpg.configure_item(self._run_btn_tag, label="Run")
        else:
            self._running = True
            self._clear_roll_buffers()
            if self.instrument and hasattr(self.instrument, 'run'):
                self.instrument.run()
            dpg.set_value(self._status_tag, "Status: Running")
            dpg.configure_item(self._run_btn_tag, label="Stop")

    def _on_single(self) -> None:
        """Trigger single acquisition."""
        if self.instrument and hasattr(self.instrument, 'single'):
            self.instrument.single()
            self._update_waveforms()

    def _on_auto(self) -> None:
        """Auto-scale."""
        if self.instrument and hasattr(self.instrument, 'auto_scale'):
            self.instrument.auto_scale()

    def _on_trigger_source(self, sender: str, value: str) -> None:
        """Handle trigger source change."""
        if self.instrument and hasattr(self.instrument, 'set_trigger_source'):
            ch = int(value.replace("CH", "").replace("EXT", "0"))
            self.instrument.set_trigger_source(ch)
            self._update_trigger_drag_line()

    def _on_trigger_mode(self, sender: str, value: str) -> None:
        """Handle trigger mode change."""
        if self.instrument and hasattr(self.instrument, 'set_trigger_mode') and value in TRIGGER_MODE_MAP:
            self.instrument.set_trigger_mode(TRIGGER_MODE_MAP[value])

    def _on_trigger_level(self, sender: str, value: float) -> None:
        """Handle trigger level change from slider."""
        if self.instrument and hasattr(self.instrument, 'set_trigger_level'):
            self.instrument.set_trigger_level(value)
        self._update_trigger_drag_line()

    def _on_trigger_drag_line(self, sender: str, app_data) -> None:
        """Handle trigger level change from drag line."""
        display_value = dpg.get_value(sender)
        if display_value is None:
            return
        display_value = float(display_value)

        # Convert display position back to actual trigger level by removing channel offset
        if self.instrument and hasattr(self.instrument, 'trigger'):
            source_ch = self.instrument.trigger.source
            if 1 <= source_ch <= len(self._channels) and hasattr(self.instrument, 'get_channel_config'):
                config = self.instrument.get_channel_config(source_ch)
                actual_level = display_value - config.offset
            else:
                actual_level = display_value
            if hasattr(self.instrument, 'set_trigger_level'):
                self.instrument.set_trigger_level(actual_level)
            # Update slider with actual level
            if dpg.does_item_exist(self._trigger_level_tag):
                dpg.set_value(self._trigger_level_tag, actual_level)

    def _update_trigger_drag_line(self) -> None:
        """Update trigger drag line position accounting for source channel offset."""
        if not self.instrument or not hasattr(self.instrument, 'trigger') or not dpg.does_item_exist(self._trigger_drag_line_tag):
            return

        trigger_level = self.instrument.trigger.level
        source_ch = self.instrument.trigger.source

        # Apply source channel's offset to display position
        if 1 <= source_ch <= len(self._channels) and hasattr(self.instrument, 'get_channel_config'):
            config = self.instrument.get_channel_config(source_ch)
            display_level = trigger_level + config.offset
        else:
            display_level = trigger_level

        dpg.set_value(self._trigger_drag_line_tag, display_level)

    def _on_trigger_enable(self, sender: str, value: bool) -> None:
        """Handle trigger enable/disable."""
        if self.instrument and hasattr(self.instrument, 'set_trigger_enabled'):
            self.instrument.set_trigger_enabled(value)
        # Show/hide trigger drag line
        if dpg.does_item_exist(self._trigger_drag_line_tag):
            dpg.configure_item(self._trigger_drag_line_tag, show=value)

    def _on_trigger_edge(self, sender: str, value: str) -> None:
        """Handle trigger edge change."""
        if self.instrument and hasattr(self.instrument, 'set_trigger_edge') and value in TRIGGER_EDGE_MAP:
            self.instrument.set_trigger_edge(TRIGGER_EDGE_MAP[value])

    def _on_display_mode_change(self, sender: str, value: str) -> None:
        """Handle display mode change."""
        if value in DISPLAY_MODE_MAP:
            self._display_mode = DISPLAY_MODE_MAP[value]
            self._clear_roll_buffers()
            self._using_roll_behavior = False
            # Roll cursor visibility is now managed by _update_waveforms based on auto-roll
            if dpg.does_item_exist(self._roll_cursor_tag):
                dpg.configure_item(self._roll_cursor_tag, show=False)

    def _clear_roll_buffers(self) -> None:
        """Clear the roll/screen mode buffers."""
        for ch in self._roll_time:
            self._roll_time[ch] = []
            self._roll_voltage[ch] = []
        self._roll_start_time = time.time()
        self._last_sample_time = 0.0

    def _build_ui(self) -> None:
        # Control bar
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Run",
                width=80,
                tag=self._run_btn_tag,
                callback=self._on_run_stop,
            )
            dpg.add_button(label="Single", width=80, callback=self._on_single)
            dpg.add_button(label="Auto", width=80, callback=self._on_auto)
            dpg.add_spacer(width=20)
            dpg.add_text("Status: Stopped", tag=self._status_tag)
            dpg.add_spacer(width=20)
            dpg.add_text("Display:")
            dpg.add_combo(
                items=list(DISPLAY_MODE_MAP.keys()),
                default_value="Normal",
                width=100,
                tag=self._display_mode_tag,
                callback=self._on_display_mode_change,
            )

        dpg.add_separator()

        # Plot
        with dpg.plot(
            height=-180,
            width=-1,
            tag=self._plot_tag,
            crosshairs=True,
            query=True,
        ):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (ms)", tag=self._x_axis_tag)
            dpg.add_plot_axis(dpg.mvYAxis, label="Voltage (V)", tag=self._y_axis_tag)

            # Create line series for each channel
            for ch in self._channels:
                dpg.add_line_series(
                    [],
                    [],
                    label=f"CH{ch.channel_id}",
                    parent=self._y_axis_tag,
                    tag=ch.series_tag,
                )

            # Create horizontal drag lines for channel offset adjustment
            for ch in self._channels:
                # Use semi-transparent version of channel color for drag line
                drag_color = (ch.color[0], ch.color[1], ch.color[2], 150)
                dpg.add_drag_line(
                    label=f"CH{ch.channel_id} Offset",
                    tag=ch.drag_line_tag,
                    color=drag_color,
                    default_value=0.0,
                    vertical=False,
                    show=ch._enabled,
                    callback=ch._on_drag_line,
                    parent=self._plot_tag,
                )

            # Trigger level drag line (white, hidden by default)
            dpg.add_drag_line(
                label="Trigger",
                tag=self._trigger_drag_line_tag,
                color=(255, 255, 255, 200),
                default_value=0.0,
                vertical=False,
                show=False,
                callback=self._on_trigger_drag_line,
                parent=self._plot_tag,
            )

            # Roll mode cursor (vertical line showing data edge)
            dpg.add_drag_line(
                label="",
                tag=self._roll_cursor_tag,
                color=(255, 255, 0, 180),
                default_value=0.0,
                vertical=True,
                show=False,
                parent=self._plot_tag,
            )

        # Create theme for each channel with matching color and line weight
        for ch in self._channels:
            with dpg.theme() as line_theme:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_style(
                        dpg.mvPlotStyleVar_LineWeight, 2.0, category=dpg.mvThemeCat_Plots
                    )
                    dpg.add_theme_color(
                        dpg.mvPlotCol_Line, ch.color, category=dpg.mvThemeCat_Plots
                    )
            dpg.bind_item_theme(ch.series_tag, line_theme)

        dpg.add_separator()

        # Channel modules and trigger side by side
        with dpg.group(horizontal=True):
            for ch in self._channels:
                ch.build_ui()

            # Trigger module
            with dpg.child_window(
                width=300,
                height=180,
                no_scrollbar=True,
                border=True,
            ):
                dpg.add_text("Trigger", color=(255, 200, 100))

                with dpg.group(horizontal=True):
                    dpg.add_checkbox(
                        label="Enable",
                        default_value=False,
                        tag=self._trigger_enable_tag,
                        callback=self._on_trigger_enable,
                    )
                    dpg.add_spacer(width=10)
                    dpg.add_text("Source:")
                    source_items = [f"CH{i+1}" for i in range(self._num_channels)] + ["EXT"]
                    dpg.add_combo(
                        items=source_items,
                        default_value="CH1",
                        width=60,
                        tag=self._trigger_source_tag,
                        callback=self._on_trigger_source,
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Edge:")
                    dpg.add_combo(
                        items=list(TRIGGER_EDGE_MAP.keys()),
                        default_value="Rising",
                        width=70,
                        tag=self._trigger_edge_tag,
                        callback=self._on_trigger_edge,
                    )
                    dpg.add_spacer(width=10)
                    dpg.add_text("Mode:")
                    dpg.add_combo(
                        items=list(TRIGGER_MODE_MAP.keys()),
                        default_value="Auto",
                        width=70,
                        tag=self._trigger_mode_tag,
                        callback=self._on_trigger_mode,
                    )

                with dpg.group(horizontal=True):
                    dpg.add_text("Level:")
                    dpg.add_slider_float(
                        width=150,
                        default_value=0,
                        min_value=-10,
                        max_value=10,
                        tag=self._trigger_level_tag,
                        callback=self._on_trigger_level,
                    )

    def setup(self) -> None:
        """Set up the panel and register update callback."""
        super().setup()
        # Set default axis limits (using hack to keep them scrollable)
        self.set_axis_limits(-10, 10, -5, 5)
        # Sync channel states from instrument
        for ch in self._channels:
            ch.sync_from_instrument()
        if not self._update_registered:
            get_manager().register_update_callback(self._update_waveforms)
            get_manager().register_update_callback(self._check_axis_changes)
            self._update_registered = True

    def _on_connected(self) -> None:
        """Sync all channels and trigger settings when instrument connects."""
        for ch in self._channels:
            ch.sync_from_instrument()
        
        # Sync trigger settings
        if self.instrument and hasattr(self.instrument, 'trigger'):
            trigger = self.instrument.trigger
            if dpg.does_item_exist(self._trigger_enable_tag):
                dpg.set_value(self._trigger_enable_tag, trigger.enabled)
            if dpg.does_item_exist(self._trigger_level_tag):
                dpg.set_value(self._trigger_level_tag, trigger.level)
            if dpg.does_item_exist(self._trigger_source_tag):
                dpg.set_value(self._trigger_source_tag, f"CH{trigger.source}")
            if dpg.does_item_exist(self._trigger_edge_tag):
                dpg.set_value(self._trigger_edge_tag, trigger.edge.name.capitalize())
            if dpg.does_item_exist(self._trigger_mode_tag):
                dpg.set_value(self._trigger_mode_tag, trigger.mode.name.capitalize())
            # Update trigger drag line visibility and position
            if dpg.does_item_exist(self._trigger_drag_line_tag):
                dpg.configure_item(self._trigger_drag_line_tag, show=trigger.enabled)
            self._update_trigger_drag_line()

    def get_axis_limits(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get current axis limits for saving to config.
        
        Returns:
            Tuple of ((x_min, x_max), (y_min, y_max))
        """
        x_limits = (-10.0, 10.0)
        y_limits = (-5.0, 5.0)
        if dpg.does_item_exist(self._x_axis_tag):
            x_limits = dpg.get_axis_limits(self._x_axis_tag)
        if dpg.does_item_exist(self._y_axis_tag):
            y_limits = dpg.get_axis_limits(self._y_axis_tag)
        return (x_limits, y_limits)

    def set_axis_limits(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        """Set axis limits from config.
        
        Uses a workaround: creates an invisible "bounds" series at the corners
        to anchor the axis limits, then enables auto-limits and fits.
        """
        if not dpg.does_item_exist(self._y_axis_tag):
            return
        
        # Delete old bounds helper if it exists
        bounds_tag = f"{self.tag}_bounds_helper"
        if dpg.does_item_exist(bounds_tag):
            dpg.delete_item(bounds_tag)
            
        # Create line series at corner points to define bounds
        # Use line series with same point twice - no line will be drawn
        dpg.add_line_series(
            [x_min, x_min, x_max, x_max],
            [y_min, y_max, y_min, y_max],
            parent=self._y_axis_tag,
            tag=bounds_tag,
        )
        # Apply transparent theme to hide the lines
        bounds_theme = f"{self.tag}_bounds_theme"
        if not dpg.does_item_exist(bounds_theme):
            with dpg.theme(tag=bounds_theme):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, (0, 0, 0, 0), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 0, category=dpg.mvThemeCat_Plots)
        dpg.bind_item_theme(bounds_tag, bounds_theme)
        
        # Enable auto limits (makes axes scrollable)
        dpg.set_axis_limits_auto(self._x_axis_tag)
        dpg.set_axis_limits_auto(self._y_axis_tag)
        
        # Fit to show all data including our bounds markers
        dpg.fit_axis_data(self._x_axis_tag)
        dpg.fit_axis_data(self._y_axis_tag)
        
        self._last_x_min = x_min
        self._last_x_max = x_max

    def _check_axis_changes(self) -> None:
        """Check for axis changes and update instrument."""
        if not self._setup_complete or not self.instrument:
            return
        self._update_timebase_from_axis()

    def _update_timebase_from_axis(self) -> None:
        """Update instrument timebase based on current axis limits."""
        if not self.instrument:
            return

        x_min, x_max = dpg.get_axis_limits(self._x_axis_tag)

        if (abs(x_min - self._last_x_min) > abs(self._last_x_min) * 0.01 + 1e-6 or
            abs(x_max - self._last_x_max) > abs(self._last_x_max) * 0.01 + 1e-6):

            self._last_x_min = x_min
            self._last_x_max = x_max

            # Restart roll mode when axis changes
            if self._display_mode == DisplayMode.ROLL:
                self._clear_roll_buffers()

            total_time_ms = x_max - x_min
            total_time_s = total_time_ms / 1000.0
            scale = total_time_s / 10.0

            center_ms = (x_min + x_max) / 2.0
            offset = center_ms / 1000.0

            log.debug(
                "Updating timebase: scale=%.3f ms/div, position=%.3f ms, span=%.3f ms",
                scale * 1000, offset * 1000, total_time_s * 1000
            )

            self.instrument.set_timebase_scale(scale)
            self.instrument.set_timebase_offset(offset)

    def _update_waveforms(self) -> None:
        """Update waveform display from instrument."""
        if not self.instrument or not self._running:
            return

        if self.instrument.acquisition_state not in (
            AcquisitionState.RUNNING,
            AcquisitionState.COMPLETE,
        ):
            return

        if self._display_mode == DisplayMode.NORMAL:
            # Auto-switch between normal and roll behavior based on time span
            x_min, x_max = dpg.get_axis_limits(self._x_axis_tag)
            span_ms = x_max - x_min
            use_roll = span_ms > AUTO_ROLL_THRESHOLD_MS
            
            # Clear buffers when switching between modes
            if use_roll != self._using_roll_behavior:
                self._clear_roll_buffers()
                self._using_roll_behavior = use_roll
            
            # Update roll cursor visibility
            if dpg.does_item_exist(self._roll_cursor_tag):
                dpg.configure_item(self._roll_cursor_tag, show=use_roll)
            
            if use_roll:
                self._update_roll_mode()
            else:
                self._update_normal_mode()
        elif self._display_mode == DisplayMode.SCREEN:
            # Hide roll cursor in screen mode
            if dpg.does_item_exist(self._roll_cursor_tag):
                dpg.configure_item(self._roll_cursor_tag, show=False)
            self._using_roll_behavior = False
            self._update_screen_mode()

    def _update_normal_mode(self) -> None:
        """Normal mode: wait for full screen, then refresh."""
        self._update_timebase_from_axis()

        for ch in self._channels:
            if ch.enabled:
                waveform = self.instrument.get_waveform(ch.channel_id)
                if waveform.num_points > 0:
                    time_ms = (waveform.time * 1000).tolist()
                    # Apply channel offset and scale for display
                    # Scale is V/div - dividing by scale zooms in (smaller scale = more zoom)
                    config = self.instrument.get_channel_config(ch.channel_id)
                    scale = config.scale if config.scale > 0 else 1.0
                    voltage_display = ((waveform.voltage * scale) + config.offset).tolist()
                    dpg.set_value(ch.series_tag, [time_ms, voltage_display])
            else:
                dpg.set_value(ch.series_tag, [[], []])

    def _update_roll_mode(self) -> None:
        """Roll mode: plot left-to-right, clear when reaching right edge.
        
        Uses get_waveform() and appends new data to create a rolling display.
        """
        x_min, x_max = dpg.get_axis_limits(self._x_axis_tag)
        window_width_ms = x_max - x_min
        current_time = time.time()
        elapsed_ms = (current_time - self._roll_start_time) * 1000
        current_x = x_min + elapsed_ms

        # Check if we've reached the right edge - clear ALL channels
        if current_x >= x_max:
            for ch_id in self._roll_time:
                self._roll_time[ch_id] = []
                self._roll_voltage[ch_id] = []
            self._roll_start_time = current_time
            self._last_sample_time = 0.0
            elapsed_ms = 0
            current_x = x_min

        # Update roll cursor position
        if dpg.does_item_exist(self._roll_cursor_tag):
            dpg.set_value(self._roll_cursor_tag, current_x)

        # Get waveform data and use latest samples
        for ch in self._channels:
            ch_id = ch.channel_id
            if not ch.enabled:
                dpg.set_value(ch.series_tag, [[], []])
                continue

            waveform = self.instrument.get_waveform(ch_id)
            if waveform.num_points == 0:
                continue

            # Calculate how much time has passed and how many samples to add
            time_since_last_ms = elapsed_ms - self._last_sample_time
            if time_since_last_ms <= 0:
                continue

            # Use the last portion of the waveform data
            samples_per_ms = waveform.num_points / window_width_ms
            num_new_samples = max(1, min(int(time_since_last_ms * samples_per_ms), waveform.num_points))
            
            # Get the latest samples from the waveform
            voltage = waveform.voltage[-num_new_samples:]
            
            # Apply scale and offset
            config = self.instrument.get_channel_config(ch_id)
            scale = config.scale if config.scale > 0 else 1.0
            voltage = (voltage * scale) + config.offset

            # Generate display time points
            display_times = np.linspace(
                x_min + self._last_sample_time,
                current_x,
                num_new_samples
            )

            self._roll_time[ch_id].extend(display_times.tolist())
            self._roll_voltage[ch_id].extend(voltage.tolist())

            dpg.set_value(ch.series_tag, [self._roll_time[ch_id], self._roll_voltage[ch_id]])

        self._last_sample_time = elapsed_ms

    def _update_screen_mode(self) -> None:
        """Screen mode: continuous refresh showing latest waveform data.
        
        Simply displays the most recent waveform, similar to Normal mode
        but updates continuously without waiting for full acquisition.
        """
        self._update_timebase_from_axis()

        for ch in self._channels:
            if ch.enabled:
                waveform = self.instrument.get_waveform(ch.channel_id)
                if waveform.num_points > 0:
                    time_ms = (waveform.time * 1000).tolist()
                    config = self.instrument.get_channel_config(ch.channel_id)
                    scale = config.scale if config.scale > 0 else 1.0
                    voltage_display = ((waveform.voltage * scale) + config.offset).tolist()
                    dpg.set_value(ch.series_tag, [time_ms, voltage_display])
            else:
                dpg.set_value(ch.series_tag, [[], []])


_panel: OscilloscopePanel | None = None


def setup_oscilloscope_view(instrument: Oscilloscope | None = None) -> OscilloscopePanel:
    """Create the oscilloscope visualization window."""
    global _panel
    if _panel is None:
        _panel = OscilloscopePanel(instrument=instrument)
    _panel.setup()
    return _panel
