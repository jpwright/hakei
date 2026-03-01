"""Power supply view and controls."""

import dearpygui.dearpygui as dpg

from hakei.ui.views.base import InstrumentPanel

CHANNEL_WIDTH = 220


class PowerSupplyChannel:
    """A single power supply output channel."""

    def __init__(self, channel_id: int, name: str | None = None):
        self.channel_id = channel_id
        self.name = name or f"CH{channel_id}"
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

    def build_ui(self) -> None:
        """Build the UI for this channel."""
        with dpg.child_window(width=CHANNEL_WIDTH, border=True):
            dpg.add_text(self.name, color=(200, 200, 200))
            dpg.add_separator()

            with dpg.group(horizontal=True):
                dpg.add_button(label="ON", width=50, tag=self.output_btn_tag)
                dpg.add_text(
                    "OFF", tag=self.output_status_tag, color=(255, 100, 100)
                )

            dpg.add_spacer(height=8)

            with dpg.child_window(height=80, border=True):
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

            dpg.add_text("Voltage", color=(150, 150, 150))
            with dpg.group(horizontal=True):
                dpg.add_input_float(
                    tag=self.set_voltage_tag,
                    default_value=0.0,
                    min_value=0.0,
                    max_value=30.0,
                    step=0.1,
                    width=100,
                    format="%.2f",
                )
                dpg.add_text("V")

            dpg.add_text("Current", color=(150, 150, 150))
            with dpg.group(horizontal=True):
                dpg.add_input_float(
                    tag=self.set_current_tag,
                    default_value=0.0,
                    min_value=0.0,
                    max_value=5.0,
                    step=0.01,
                    width=100,
                    format="%.3f",
                )
                dpg.add_text("A")

            dpg.add_spacer(height=8)
            dpg.add_text("Presets", color=(150, 150, 150))

            with dpg.group(horizontal=True):
                dpg.add_button(label="3.3", width=45)
                dpg.add_button(label="5", width=45)
                dpg.add_button(label="12", width=45)
                dpg.add_button(label="24", width=45)

    def set_voltage(self, voltage: float) -> None:
        """Set the voltage setpoint."""
        dpg.set_value(self.set_voltage_tag, voltage)

    def set_current(self, current: float) -> None:
        """Set the current setpoint."""
        dpg.set_value(self.set_current_tag, current)

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
        super().__init__(tag="power_supply", label="Power Supply", preferred_height=320)
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
