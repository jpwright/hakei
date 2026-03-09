"""Power supply view and controls."""

import logging

import dearpygui.dearpygui as dpg

from hakei.instruments.power_supply import PowerSupply
from hakei.ui.layout import get_manager
from hakei.ui.views.base import InstrumentPanel

log = logging.getLogger(__name__)

CHANNEL_WIDTH = 280


class PowerSupplyChannel:
    """A single power supply output channel UI."""

    def __init__(
        self,
        channel_id: int,
        panel: "PowerSupplyPanel",
        name: str | None = None,
        max_voltage: float = 30.0,
        max_current: float = 5.0,
    ):
        self.channel_id = channel_id
        self.panel = panel
        self.name = name or f"CH{channel_id}"
        self.max_voltage = max_voltage
        self.max_current = max_current
        # Include panel tag to ensure uniqueness across multiple power supplies
        self._tag_prefix = f"{panel.tag}_ch{channel_id}"
        self._output_enabled = False

    @property
    def instrument(self) -> PowerSupply | None:
        """Get instrument from parent panel (always current, not stale reference)."""
        return self.panel.instrument if self.panel else None

    @property
    def output_btn_tag(self) -> str:
        return f"{self._tag_prefix}_output_btn"

    @property
    def output_status_tag(self) -> str:
        return f"{self._tag_prefix}_output_status"

    @property
    def actual_voltage_tag(self) -> str:
        return f"{self._tag_prefix}_actual_voltage"

    @property
    def actual_current_tag(self) -> str:
        return f"{self._tag_prefix}_actual_current"

    @property
    def actual_power_tag(self) -> str:
        return f"{self._tag_prefix}_actual_power"

    @property
    def set_voltage_tag(self) -> str:
        return f"{self._tag_prefix}_set_voltage"

    @property
    def set_current_tag(self) -> str:
        return f"{self._tag_prefix}_set_current"

    @property
    def voltage_knob_tag(self) -> str:
        return f"{self._tag_prefix}_voltage_knob"

    @property
    def current_knob_tag(self) -> str:
        return f"{self._tag_prefix}_current_knob"

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

    def _on_voltage_knob_change(self, sender: str, value: float) -> None:
        """Handle voltage knob change."""
        dpg.set_value(self.set_voltage_tag, value)
        if self.instrument and hasattr(self.instrument, 'set_voltage'):
            self.instrument.set_voltage(self.channel_id, value)

    def _on_voltage_input_change(self, sender: str, value: float) -> None:
        """Handle voltage input change."""
        clamped = max(0.0, min(self.max_voltage, value))
        dpg.set_value(self.voltage_knob_tag, clamped)
        if value != clamped:
            dpg.set_value(self.set_voltage_tag, clamped)
        if self.instrument and hasattr(self.instrument, 'set_voltage'):
            self.instrument.set_voltage(self.channel_id, clamped)

    def _on_current_knob_change(self, sender: str, value: float) -> None:
        """Handle current knob change."""
        dpg.set_value(self.set_current_tag, value)
        if self.instrument and hasattr(self.instrument, 'set_current_limit'):
            self.instrument.set_current_limit(self.channel_id, value)

    def _on_current_input_change(self, sender: str, value: float) -> None:
        """Handle current input change."""
        clamped = max(0.0, min(self.max_current, value))
        dpg.set_value(self.current_knob_tag, clamped)
        if value != clamped:
            dpg.set_value(self.set_current_tag, clamped)
        if self.instrument and hasattr(self.instrument, 'set_current_limit'):
            self.instrument.set_current_limit(self.channel_id, clamped)

    def build_ui(self) -> None:
        """Build the UI for this channel."""
        with dpg.child_window(width=CHANNEL_WIDTH, border=True):
            dpg.add_text(self.name, color=(200, 200, 200))
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="ON",
                    width=50,
                    tag=self.output_btn_tag,
                    callback=self._on_output_toggle,
                )
                dpg.add_text("OFF", tag=self.output_status_tag, color=(255, 100, 100))

            dpg.add_spacer(height=8)

            with dpg.group():
                with dpg.group(horizontal=True):
                    dpg.add_text("V:", color=(100, 200, 100))
                    dpg.add_text("0.000", tag=self.actual_voltage_tag)

                with dpg.group(horizontal=True):
                    dpg.add_text("A:", color=(100, 150, 255))
                    dpg.add_text("0.000", tag=self.actual_current_tag)

                with dpg.group(horizontal=True):
                    dpg.add_text("W:", color=(255, 200, 100))
                    dpg.add_text("0.000", tag=self.actual_power_tag)

            dpg.add_spacer(height=8)

            with dpg.group(horizontal=True):
                with dpg.table(
                    header_row=False,
                    borders_innerV=False,
                    borders_outerH=False,
                    borders_outerV=False,
                    borders_innerH=False,
                ):
                    dpg.add_table_column()
                    dpg.add_table_column()

                    with dpg.table_row():
                        with dpg.group():
                            dpg.add_text("Voltage", color=(100, 200, 100))
                            dpg.add_knob_float(
                                tag=self.voltage_knob_tag,
                                default_value=0.0,
                                min_value=0.0,
                                max_value=self.max_voltage,
                                width=80,
                                height=80,
                                indent=20,
                                callback=self._on_voltage_knob_change,
                            )
                            with dpg.group(horizontal=True):
                                dpg.add_input_float(
                                    tag=self.set_voltage_tag,
                                    default_value=0.0,
                                    min_value=0.0,
                                    max_value=self.max_voltage,
                                    step=0,
                                    step_fast=0,
                                    width=60,
                                    format="%.2f",
                                    callback=self._on_voltage_input_change,
                                    label="V",
                                )

                        with dpg.group():
                            dpg.add_text("Current", color=(100, 150, 255))
                            dpg.add_knob_float(
                                tag=self.current_knob_tag,
                                default_value=0.0,
                                min_value=0.0,
                                max_value=self.max_current,
                                width=80,
                                height=80,
                                indent=20,
                                callback=self._on_current_knob_change,
                            )
                            with dpg.group(horizontal=True):
                                dpg.add_input_float(
                                    tag=self.set_current_tag,
                                    default_value=0.0,
                                    min_value=0.0,
                                    max_value=self.max_current,
                                    step=0,
                                    step_fast=0,
                                    width=70,
                                    format="%.3f",
                                    callback=self._on_current_input_change,
                                )

            dpg.add_spacer(height=8)
            dpg.add_text("Presets", color=(150, 150, 150))

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="3.3V", width=55, callback=lambda: self.set_voltage(3.3)
                )
                dpg.add_button(
                    label="5V", width=55, callback=lambda: self.set_voltage(5.0)
                )
                dpg.add_button(
                    label="12V", width=55, callback=lambda: self.set_voltage(12.0)
                )
                dpg.add_button(
                    label="24V", width=55, callback=lambda: self.set_voltage(24.0)
                )

    def set_voltage(self, voltage: float) -> None:
        """Set the voltage setpoint."""
        clamped = max(0.0, min(self.max_voltage, voltage))
        dpg.set_value(self.set_voltage_tag, clamped)
        dpg.set_value(self.voltage_knob_tag, clamped)
        if self.instrument and hasattr(self.instrument, 'set_voltage'):
            self.instrument.set_voltage(self.channel_id, clamped)

    def set_current(self, current: float) -> None:
        """Set the current setpoint."""
        clamped = max(0.0, min(self.max_current, current))
        dpg.set_value(self.set_current_tag, clamped)
        dpg.set_value(self.current_knob_tag, clamped)
        if self.instrument and hasattr(self.instrument, 'set_current_limit'):
            self.instrument.set_current_limit(self.channel_id, clamped)

    def get_voltage_setpoint(self) -> float:
        """Get the voltage setpoint."""
        return dpg.get_value(self.set_voltage_tag)

    def get_current_setpoint(self) -> float:
        """Get the current setpoint."""
        return dpg.get_value(self.set_current_tag)

    def update_readings(self) -> None:
        """Update actual readings from instrument."""
        if not self.instrument or not hasattr(self.instrument, 'get_voltage'):
            return

        voltage = self.instrument.get_voltage(self.channel_id)
        current = self.instrument.get_current(self.channel_id)
        power = self.instrument.get_power(self.channel_id)

        dpg.set_value(self.actual_voltage_tag, f"{voltage:.3f}")
        dpg.set_value(self.actual_current_tag, f"{current:.3f}")
        dpg.set_value(self.actual_power_tag, f"{power:.3f}")

    def set_output_status(self, is_on: bool) -> None:
        """Update the output status display."""
        self._output_enabled = is_on
        self._update_output_display()

    def sync_from_instrument(self) -> None:
        """Sync UI state from instrument's current values."""
        if not self.instrument:
            return

        # Check if instrument has required method (might be placeholder during connection)
        if not hasattr(self.instrument, 'get_channel_state'):
            return

        state = self.instrument.get_channel_state(self.channel_id)

        # Sync voltage setpoint
        dpg.set_value(self.voltage_knob_tag, state.voltage_setpoint)
        dpg.set_value(self.set_voltage_tag, state.voltage_setpoint)

        # Sync current limit
        dpg.set_value(self.current_knob_tag, state.current_limit)
        dpg.set_value(self.set_current_tag, state.current_limit)

        # Sync output state
        self._output_enabled = state.output_enabled
        self._update_output_display()


class PowerSupplyPanel(InstrumentPanel):
    """Power supply instrument panel with configurable channels."""

    _instance_counter = 0

    def __init__(
        self,
        instrument: PowerSupply | None = None,
        num_channels: int = 1,
        channel_names: list[str] | None = None,
    ):
        # Generate unique tag for this panel instance
        PowerSupplyPanel._instance_counter += 1
        instance_id = PowerSupplyPanel._instance_counter
        unique_tag = f"psu_{instance_id}"

        super().__init__(
            tag=unique_tag,
            label="Power Supply",
            preferred_height=380,
            instrument=instrument,
        )
        self.channels: list[PowerSupplyChannel] = []
        self._num_channels = num_channels
        self._channel_names = channel_names or []
        self._update_timer: str | None = None

    @property
    def window_tag(self) -> str:
        return f"{self.tag}_window"

    def _build_ui(self) -> None:
        with dpg.group(horizontal=True):
            for i in range(self._num_channels):
                name = self._channel_names[i] if i < len(self._channel_names) else None

                max_v = 30.0
                max_i = 5.0
                if self.instrument and hasattr(self.instrument, 'get_channel_capabilities'):
                    caps = self.instrument.get_channel_capabilities(i + 1)
                    max_v = caps.max_voltage
                    max_i = caps.max_current

                channel = PowerSupplyChannel(
                    channel_id=i + 1,
                    panel=self,
                    name=name,
                    max_voltage=max_v,
                    max_current=max_i,
                )
                channel.build_ui()
                channel.sync_from_instrument()
                self.channels.append(channel)

    def setup(self) -> None:
        """Set up the panel and start update timer."""
        super().setup()
        self._start_update_timer()

    def _on_connected(self) -> None:
        """Sync all channels when instrument connects."""
        for channel in self.channels:
            channel.sync_from_instrument()

    def _start_update_timer(self) -> None:
        """Register update callback with the layout manager."""
        if self._update_timer is None:
            self._update_timer = "psu_update"
            get_manager().register_update_callback(self.update_readings)

    def update_readings(self) -> None:
        """Update all channel readings from instrument."""
        if not self._setup_complete:
            return
        for channel in self.channels:
            channel.update_readings()

    def get_channel(self, channel_id: int) -> PowerSupplyChannel | None:
        """Get a channel by its ID (1-indexed)."""
        for channel in self.channels:
            if channel.channel_id == channel_id:
                return channel
        return None


_panel: PowerSupplyPanel | None = None


def setup_power_supply_view(
    instrument: PowerSupply | None = None,
    num_channels: int = 1,
    channel_names: list[str] | None = None,
) -> PowerSupplyPanel:
    """Create the power supply control window."""
    global _panel
    if _panel is None:
        _panel = PowerSupplyPanel(
            instrument=instrument,
            num_channels=num_channels,
            channel_names=channel_names,
        )
    _panel.setup()
    return _panel
