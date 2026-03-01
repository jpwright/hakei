"""Power supply view and controls."""

import dearpygui.dearpygui as dpg

from hakei.ui.views.base import InstrumentPanel

CHANNEL_WIDTH = 280


class PowerSupplyChannel:
    """A single power supply output channel."""

    def __init__(
        self,
        channel_id: int,
        name: str | None = None,
        max_voltage: float = 30.0,
        max_current: float = 5.0,
    ):
        self.channel_id = channel_id
        self.name = name or f"CH{channel_id}"
        self.max_voltage = max_voltage
        self.max_current = max_current
        self._tag_prefix = f"psu_ch{channel_id}"

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

    def _on_voltage_knob_change(self, sender: str, value: float) -> None:
        """Sync input field when knob changes."""
        dpg.set_value(self.set_voltage_tag, value)

    def _on_voltage_input_change(self, sender: str, value: float) -> None:
        """Sync knob when input field changes."""
        clamped = max(0.0, min(self.max_voltage, value))
        dpg.set_value(self.voltage_knob_tag, clamped)
        if value != clamped:
            dpg.set_value(self.set_voltage_tag, clamped)

    def _on_current_knob_change(self, sender: str, value: float) -> None:
        """Sync input field when knob changes."""
        dpg.set_value(self.set_current_tag, value)

    def _on_current_input_change(self, sender: str, value: float) -> None:
        """Sync knob when input field changes."""
        clamped = max(0.0, min(self.max_current, value))
        dpg.set_value(self.current_knob_tag, clamped)
        if value != clamped:
            dpg.set_value(self.set_current_tag, clamped)

    def build_ui(self) -> None:
        """Build the UI for this channel."""
        with dpg.child_window(width=CHANNEL_WIDTH, border=True):
            dpg.add_text(self.name, color=(200, 200, 200))
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_button(label="ON", width=50, tag=self.output_btn_tag)
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
                with dpg.table(header_row=False, borders_innerV=False, borders_outerH=False,
                            borders_outerV=False, borders_innerH=False):
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
                                    label='V',
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

    def set_current(self, current: float) -> None:
        """Set the current setpoint."""
        clamped = max(0.0, min(self.max_current, current))
        dpg.set_value(self.set_current_tag, clamped)
        dpg.set_value(self.current_knob_tag, clamped)

    def get_voltage_setpoint(self) -> float:
        """Get the voltage setpoint."""
        return dpg.get_value(self.set_voltage_tag)

    def get_current_setpoint(self) -> float:
        """Get the current setpoint."""
        return dpg.get_value(self.set_current_tag)

    def update_actual_values(
        self, voltage: float, current: float, power: float | None = None
    ) -> None:
        """Update the displayed actual values."""
        dpg.set_value(self.actual_voltage_tag, f"{voltage:.3f}")
        dpg.set_value(self.actual_current_tag, f"{current:.3f}")
        if power is None:
            power = voltage * current
        dpg.set_value(self.actual_power_tag, f"{power:.3f}")

    def set_output_status(self, is_on: bool) -> None:
        """Update the output status display."""
        if is_on:
            dpg.set_value(self.output_status_tag, "ON")
            dpg.configure_item(self.output_status_tag, color=(100, 255, 100))
        else:
            dpg.set_value(self.output_status_tag, "OFF")
            dpg.configure_item(self.output_status_tag, color=(255, 100, 100))


class PowerSupplyPanel(InstrumentPanel):
    """Power supply instrument panel with configurable channels."""

    def __init__(self, num_channels: int = 1, channel_names: list[str] | None = None):
        super().__init__(tag="power_supply", label="Power Supply", preferred_height=380)
        self.channels: list[PowerSupplyChannel] = []
        self._num_channels = num_channels
        self._channel_names = channel_names or []

    @property
    def window_tag(self) -> str:
        return "power_supply_window"

    def _build_ui(self) -> None:
        with dpg.group(horizontal=True):
            for i in range(self._num_channels):
                name = self._channel_names[i] if i < len(self._channel_names) else None
                channel = PowerSupplyChannel(channel_id=i + 1, name=name)
                channel.build_ui()
                self.channels.append(channel)

    def get_channel(self, channel_id: int) -> PowerSupplyChannel | None:
        """Get a channel by its ID (1-indexed)."""
        for channel in self.channels:
            if channel.channel_id == channel_id:
                return channel
        return None


_panel: PowerSupplyPanel | None = None


def setup_power_supply_view(
    num_channels: int = 1, channel_names: list[str] | None = None
) -> PowerSupplyPanel:
    """Create the power supply control window."""
    global _panel
    if _panel is None:
        _panel = PowerSupplyPanel(num_channels=num_channels, channel_names=channel_names)
    _panel.setup()
    return _panel
