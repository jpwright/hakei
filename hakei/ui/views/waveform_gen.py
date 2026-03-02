"""Waveform generator view and controls."""

import logging

import dearpygui.dearpygui as dpg
import numpy as np

from hakei.instruments.waveform_generator import (
    ModulationType,
    WaveformGenerator,
    WaveformType,
)
from hakei.ui.views.base import InstrumentPanel

log = logging.getLogger(__name__)

CHANNEL_WIDTH = 420
LEFT_COL_WIDTH = 240
RIGHT_COL_WIDTH = 170

WAVEFORM_MAP = {
    "Sine": WaveformType.SINE,
    "Square": WaveformType.SQUARE,
    "Triangle": WaveformType.TRIANGLE,
    "Ramp": WaveformType.RAMP,
    "Pulse": WaveformType.PULSE,
    "Noise": WaveformType.NOISE,
    "DC": WaveformType.DC,
    "Arb": WaveformType.ARBITRARY,
}

WAVEFORM_BUTTONS = [
    ["Sine", "Square", "Triangle", "Ramp"],
    ["Pulse", "Noise", "DC", "Arb"],
]

WAVEFORM_LABELS = {
    "Sine": "Sin",
    "Square": "Squ",
    "Triangle": "Tri",
    "Ramp": "Rmp",
    "Pulse": "Pul",
    "Noise": "Noi",
    "DC": "DC",
    "Arb": "Arb",
}

MODULATION_MAP = {
    "AM": ModulationType.AM,
    "FM": ModulationType.FM,
    "PM": ModulationType.PM,
    "FSK": ModulationType.FSK,
    "PWM": ModulationType.PWM,
}

FREQ_MULTIPLIERS = {
    "Hz": 1.0,
    "kHz": 1e3,
    "MHz": 1e6,
}


class WaveformGeneratorChannel:
    """A single waveform generator output channel UI."""

    def __init__(
        self,
        channel_id: int,
        panel: "WaveformGeneratorPanel | None" = None,
        name: str | None = None,
    ):
        self.channel_id = channel_id
        self.panel = panel
        self.name = name or f"CH{channel_id}"
        # Include panel tag to ensure uniqueness across multiple waveform generators
        panel_id = panel.tag if panel else "default"
        self._tag_prefix = f"{panel_id}_ch{channel_id}"
        self._output_enabled = False
        self._selected_waveform = "Sine"
        self._freq_unit = "Hz"

    @property
    def instrument(self) -> WaveformGenerator | None:
        """Get instrument from parent panel (always current, not stale reference)."""
        if self.panel:
            return self.panel.instrument
        return None

    @property
    def output_btn_tag(self) -> str:
        return f"{self._tag_prefix}_output_btn"

    @property
    def output_status_tag(self) -> str:
        return f"{self._tag_prefix}_output_status"

    @property
    def frequency_tag(self) -> str:
        return f"{self._tag_prefix}_frequency"

    @property
    def freq_unit_tag(self) -> str:
        return f"{self._tag_prefix}_freq_unit"

    @property
    def amplitude_tag(self) -> str:
        return f"{self._tag_prefix}_amplitude"

    @property
    def offset_tag(self) -> str:
        return f"{self._tag_prefix}_offset"

    @property
    def phase_tag(self) -> str:
        return f"{self._tag_prefix}_phase"

    @property
    def duty_cycle_tag(self) -> str:
        return f"{self._tag_prefix}_duty_cycle"

    @property
    def mod_enable_tag(self) -> str:
        return f"{self._tag_prefix}_mod_enable"

    @property
    def mod_type_tag(self) -> str:
        return f"{self._tag_prefix}_mod_type"

    @property
    def plot_tag(self) -> str:
        return f"{self._tag_prefix}_plot"

    @property
    def series_tag(self) -> str:
        return f"{self._tag_prefix}_series"

    @property
    def y_axis_tag(self) -> str:
        return f"{self._tag_prefix}_y_axis"

    def _waveform_btn_tag(self, waveform: str) -> str:
        return f"{self._tag_prefix}_btn_{waveform.lower()}"

    def _on_output_toggle(self) -> None:
        """Toggle output on/off."""
        self._output_enabled = not self._output_enabled
        if self.instrument and hasattr(self.instrument, 'set_output_enabled'):
            self.instrument.set_output_enabled(self.channel_id, self._output_enabled)
        self._update_output_display()

    def _update_output_display(self) -> None:
        """Update output button and status display."""
        if self._output_enabled:
            dpg.configure_item(self.output_btn_tag, label="OFF")
            dpg.set_value(self.output_status_tag, "ON")
            dpg.configure_item(self.output_status_tag, color=(100, 255, 100))
        else:
            dpg.configure_item(self.output_btn_tag, label="ON")
            dpg.set_value(self.output_status_tag, "OFF")
            dpg.configure_item(self.output_status_tag, color=(255, 100, 100))

    def _on_waveform_btn_click(self, sender: str, app_data: any, user_data: str) -> None:
        """Handle waveform button click (DPG callback)."""
        if user_data not in WAVEFORM_MAP:
            return
        self._selected_waveform = user_data
        if self.instrument and hasattr(self.instrument, 'set_waveform'):
            self.instrument.set_waveform(self.channel_id, WAVEFORM_MAP[user_data])
        self._update_waveform_buttons()
        self._update_waveform_preview()

    def _update_waveform_buttons(self) -> None:
        """Update waveform button highlights."""
        for name in WAVEFORM_MAP:
            tag = self._waveform_btn_tag(name)
            if not dpg.does_item_exist(tag):
                continue
            if name == self._selected_waveform:
                dpg.bind_item_theme(tag, "wfg_selected_theme")
            else:
                dpg.bind_item_theme(tag, 0)

    def _on_frequency_change(self, sender: str, value: float) -> None:
        """Handle frequency change."""
        if self.instrument and hasattr(self.instrument, 'set_frequency'):
            freq = value * FREQ_MULTIPLIERS.get(self._freq_unit, 1.0)
            self.instrument.set_frequency(self.channel_id, freq)

    def _on_freq_unit_change(self, sender: str, value: str) -> None:
        """Handle frequency unit change."""
        old_unit = self._freq_unit
        self._freq_unit = value
        if self.instrument and hasattr(self.instrument, 'set_frequency'):
            current_value = dpg.get_value(self.frequency_tag)
            freq = current_value * FREQ_MULTIPLIERS.get(old_unit, 1.0)
            self.instrument.set_frequency(self.channel_id, freq)

    def _on_amplitude_change(self, sender: str, value: float) -> None:
        """Handle amplitude change."""
        if self.instrument and hasattr(self.instrument, 'set_amplitude'):
            self.instrument.set_amplitude(self.channel_id, value)
        self._update_waveform_preview()

    def _on_offset_change(self, sender: str, value: float) -> None:
        """Handle offset change."""
        if self.instrument and hasattr(self.instrument, 'set_offset'):
            self.instrument.set_offset(self.channel_id, value)
        self._update_waveform_preview()

    def _on_phase_change(self, sender: str, value: float) -> None:
        """Handle phase change."""
        if self.instrument and hasattr(self.instrument, 'set_phase'):
            self.instrument.set_phase(self.channel_id, value)
        self._update_waveform_preview()

    def _on_duty_cycle_change(self, sender: str, value: float) -> None:
        """Handle duty cycle change."""
        if self.instrument and hasattr(self.instrument, 'set_duty_cycle'):
            self.instrument.set_duty_cycle(self.channel_id, value)
        self._update_waveform_preview()

    def _on_mod_enable(self, sender: str, value: bool) -> None:
        """Handle modulation enable/disable."""
        if self.instrument and hasattr(self.instrument, 'set_modulation_enabled'):
            self.instrument.set_modulation_enabled(self.channel_id, value)

    def _on_mod_type_change(self, sender: str, value: str) -> None:
        """Handle modulation type change."""
        if self.instrument and hasattr(self.instrument, 'set_modulation_type') and value in MODULATION_MAP:
            self.instrument.set_modulation_type(self.channel_id, MODULATION_MAP[value])

    def _update_waveform_preview(self) -> None:
        """Update the waveform preview plot."""
        if not dpg.does_item_exist(self.series_tag):
            return

        # Generate 2 cycles of the waveform
        num_points = 200
        t = np.linspace(0, 2, num_points)  # 2 cycles
        
        # Get current parameters
        amplitude = dpg.get_value(self.amplitude_tag) if dpg.does_item_exist(self.amplitude_tag) else 1.0
        offset = dpg.get_value(self.offset_tag) if dpg.does_item_exist(self.offset_tag) else 0.0
        duty_cycle = dpg.get_value(self.duty_cycle_tag) if dpg.does_item_exist(self.duty_cycle_tag) else 50.0
        phase = dpg.get_value(self.phase_tag) if dpg.does_item_exist(self.phase_tag) else 0.0
        
        # Phase offset (convert degrees to cycles)
        t_shifted = t + phase / 360.0
        
        # Generate waveform based on type
        waveform = self._selected_waveform
        if waveform == "Sine":
            y = np.sin(2 * np.pi * t_shifted)
        elif waveform == "Square":
            y = np.sign(np.sin(2 * np.pi * t_shifted))
        elif waveform == "Triangle":
            y = 2 * np.abs(2 * (t_shifted % 1) - 1) - 1
        elif waveform == "Ramp":
            y = 2 * (t_shifted % 1) - 1
        elif waveform == "Pulse":
            duty = duty_cycle / 100.0
            y = np.where((t_shifted % 1) < duty, 1.0, -1.0)
        elif waveform == "Noise":
            y = np.random.uniform(-1, 1, num_points)
        elif waveform == "DC":
            y = np.ones(num_points)
        else:  # Arb or unknown
            y = np.sin(2 * np.pi * t_shifted)
        
        # Apply amplitude and offset
        y = y * (amplitude / 2) + offset
        
        dpg.set_value(self.series_tag, [t.tolist(), y.tolist()])
        
        # Update y-axis limits to fit the waveform
        if dpg.does_item_exist(self.y_axis_tag):
            y_max = offset + amplitude / 2 + 0.2
            y_min = offset - amplitude / 2 - 0.2
            dpg.set_axis_limits(self.y_axis_tag, y_min, y_max)

    def build_ui(self) -> None:
        """Build the UI for this channel."""
        with dpg.child_window(width=CHANNEL_WIDTH, border=True):
            dpg.add_text(self.name, color=(200, 200, 200))
            dpg.add_separator()

            with dpg.group(horizontal=True):
                # Left column: Preview, Output, Waveform selection
                with dpg.child_window(width=LEFT_COL_WIDTH, border=False):
                    # Waveform preview plot
                    with dpg.plot(
                        height=80,
                        width=-1,
                        tag=self.plot_tag,
                        no_menus=True,
                        no_box_select=True,
                        no_mouse_pos=True,
                    ):
                        dpg.add_plot_axis(dpg.mvXAxis, no_tick_labels=True, no_tick_marks=True)
                        dpg.set_axis_limits(dpg.last_item(), 0, 2)
                        with dpg.plot_axis(
                            dpg.mvYAxis, no_tick_labels=True, no_tick_marks=True, tag=self.y_axis_tag
                        ):
                            dpg.add_line_series([], [], tag=self.series_tag)
                        dpg.set_axis_limits(self.y_axis_tag, -1.5, 1.5)

                    # Output control
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="ON",
                            width=50,
                            tag=self.output_btn_tag,
                            callback=self._on_output_toggle,
                        )
                        dpg.add_text("OFF", tag=self.output_status_tag, color=(255, 100, 100))

                    dpg.add_spacer(height=5)

                    # Waveform type selection
                    dpg.add_text("Waveform", color=(150, 150, 150))
                    for row in WAVEFORM_BUTTONS:
                        with dpg.group(horizontal=True):
                            for wf in row:
                                dpg.add_button(
                                    label=WAVEFORM_LABELS[wf],
                                    width=55,
                                    tag=self._waveform_btn_tag(wf),
                                    user_data=wf,
                                    callback=self._on_waveform_btn_click,
                                )

                # Right column: Parameters, Modulation
                with dpg.child_window(width=RIGHT_COL_WIDTH, border=False):
                    # Parameters
                    dpg.add_text("Parameters", color=(150, 150, 150))
                    dpg.add_separator()

                    dpg.add_text("Freq", color=(100, 200, 100))
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(
                            tag=self.frequency_tag,
                            default_value=1000.0,
                            min_value=0.001,
                            max_value=25000000.0,
                            step=0,
                            step_fast=0,
                            width=80,
                            format="%.1f",
                            callback=self._on_frequency_change,
                        )
                        dpg.add_combo(
                            items=list(FREQ_MULTIPLIERS.keys()),
                            default_value="Hz",
                            width=55,
                            tag=self.freq_unit_tag,
                            callback=self._on_freq_unit_change,
                        )

                    dpg.add_text("Amplitude", color=(100, 150, 255))
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(
                            tag=self.amplitude_tag,
                            default_value=1.0,
                            min_value=0.001,
                            max_value=10.0,
                            step=0.1,
                            step_fast=1.0,
                            width=80,
                            format="%.3f",
                            callback=self._on_amplitude_change,
                        )
                        dpg.add_text("Vpp")

                    dpg.add_text("Offset", color=(255, 200, 100))
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(
                            tag=self.offset_tag,
                            default_value=0.0,
                            min_value=-10.0,
                            max_value=10.0,
                            step=0.1,
                            step_fast=1.0,
                            width=80,
                            format="%.3f",
                            callback=self._on_offset_change,
                        )
                        dpg.add_text("V")

                    dpg.add_text("Phase", color=(200, 150, 255))
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(
                            tag=self.phase_tag,
                            default_value=0.0,
                            min_value=0.0,
                            max_value=360.0,
                            step=1.0,
                            step_fast=10.0,
                            width=60,
                            format="%.1f",
                            callback=self._on_phase_change,
                        )
                        dpg.add_text("deg")

                    dpg.add_text("Duty Cycle", color=(150, 200, 200))
                    with dpg.group(horizontal=True):
                        dpg.add_input_float(
                            tag=self.duty_cycle_tag,
                            default_value=50.0,
                            min_value=0.1,
                            max_value=99.9,
                            step=1.0,
                            step_fast=10.0,
                            width=60,
                            format="%.1f",
                            callback=self._on_duty_cycle_change,
                        )
                        dpg.add_text("%")

                    dpg.add_spacer(height=5)

                    # Modulation
                    dpg.add_text("Modulation", color=(150, 150, 150))
                    dpg.add_separator()
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(
                            label="",
                            tag=self.mod_enable_tag,
                            callback=self._on_mod_enable,
                        )
                        dpg.add_combo(
                            items=list(MODULATION_MAP.keys()),
                            default_value="AM",
                            width=60,
                            tag=self.mod_type_tag,
                            callback=self._on_mod_type_change,
                        )
        
        # Initialize preview and button highlights with default values
        self._update_waveform_buttons()
        self._update_waveform_preview()

    def sync_from_instrument(self) -> None:
        """Sync UI state from instrument's current values."""
        if not self.instrument:
            return
        
        # Check if instrument has required method (might be placeholder during connection)
        if not hasattr(self.instrument, 'get_channel_config'):
            return

        config = self.instrument.get_channel_config(self.channel_id)

        # Sync output state
        self._output_enabled = config.output_enabled
        self._update_output_display()

        # Sync waveform type
        self._selected_waveform = "Sine"  # Default fallback
        for name, wtype in WAVEFORM_MAP.items():
            if wtype == config.waveform:
                self._selected_waveform = name
                break
        self._update_waveform_buttons()

        # Sync parameters
        dpg.set_value(self.frequency_tag, config.frequency)
        dpg.set_value(self.amplitude_tag, config.amplitude)
        dpg.set_value(self.offset_tag, config.offset)
        dpg.set_value(self.phase_tag, config.phase)
        dpg.set_value(self.duty_cycle_tag, config.duty_cycle)

        # Sync modulation
        mod_config = self.instrument.get_modulation_config(self.channel_id)
        dpg.set_value(self.mod_enable_tag, mod_config.enabled)

        # Update preview
        self._update_waveform_preview()


class WaveformGeneratorPanel(InstrumentPanel):
    """Waveform generator instrument panel with configurable channels."""

    _instance_counter = 0

    def __init__(
        self,
        instrument: WaveformGenerator | None = None,
        num_channels: int = 1,
        channel_names: list[str] | None = None,
    ):
        # Generate unique tag for this panel instance
        WaveformGeneratorPanel._instance_counter += 1
        instance_id = WaveformGeneratorPanel._instance_counter
        unique_tag = f"wfg_{instance_id}"
        
        super().__init__(
            tag=unique_tag,
            label="Waveform Generator",
            preferred_height=500,
            instrument=instrument,
        )
        self.channels: list[WaveformGeneratorChannel] = []
        self._num_channels = num_channels
        self._channel_names = channel_names or []

    @property
    def window_tag(self) -> str:
        return f"{self.tag}_window"

    def _build_ui(self) -> None:
        # Create selected button theme (shared across all channels)
        if not dpg.does_item_exist("wfg_selected_theme"):
            with dpg.theme(tag="wfg_selected_theme"):
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (80, 120, 80))

        with dpg.group(horizontal=True):
            for i in range(self._num_channels):
                name = self._channel_names[i] if i < len(self._channel_names) else None
                channel = WaveformGeneratorChannel(
                    channel_id=i + 1,
                    panel=self,
                    name=name,
                )
                channel.build_ui()
                self.channels.append(channel)

    def setup(self) -> None:
        """Set up the panel and sync from instrument."""
        super().setup()
        for channel in self.channels:
            channel.sync_from_instrument()

    def _on_connected(self) -> None:
        """Sync all channels when instrument connects."""
        for channel in self.channels:
            channel.sync_from_instrument()

    def get_channel(self, channel_id: int) -> WaveformGeneratorChannel | None:
        """Get a channel by its ID (1-indexed)."""
        for channel in self.channels:
            if channel.channel_id == channel_id:
                return channel
        return None


_panel: WaveformGeneratorPanel | None = None


def setup_waveform_gen_view(
    instrument: WaveformGenerator | None = None,
    num_channels: int = 1,
    channel_names: list[str] | None = None,
) -> WaveformGeneratorPanel:
    """Create the waveform generator control window."""
    global _panel
    if _panel is None:
        _panel = WaveformGeneratorPanel(
            instrument=instrument,
            num_channels=num_channels,
            channel_names=channel_names,
        )
    _panel.setup()
    return _panel
