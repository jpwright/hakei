"""Dummy power supply implementation for testing."""

import logging
import time

import numpy as np

from hakei.instruments.base import ConnectionState, InstrumentInfo
from hakei.instruments.power_supply import (
    ChannelCapabilities,
    OutputMode,
    PowerSupply,
    ProtectionState,
)

log = logging.getLogger(__name__)


class DummyPowerSupply(PowerSupply):
    """Dummy power supply that simulates output behavior."""

    def __init__(self, resource_address: str = "DUMMY::PSU::1", num_channels: int = 2, device=None):
        super().__init__(resource_address, num_channels, device=device)
        self._info = InstrumentInfo(
            manufacturer="Hakei",
            model="DummyPSU-2CH",
            serial_number="DUMMY002",
            firmware_version="1.0.0",
        )

        # Set capabilities and default current limit for each channel
        for i in range(num_channels):
            self._channel_capabilities[i] = ChannelCapabilities(
                max_voltage=30.0,
                max_current=5.0,
                max_power=150.0,
                min_voltage=0.0,
                min_current=0.0,
                voltage_resolution=0.001,
                current_resolution=0.001,
            )
            # Set sensible default current limit
            self._channel_states[i].current_limit = 1.0

        # Simulated load resistance for each channel (ohms)
        self._load_resistance = [100.0] * num_channels

    def connect(self) -> bool:
        """Connect to the dummy power supply."""
        log.info("Connecting to dummy power supply: %s", self.resource_address)
        self._state = ConnectionState.CONNECTING
        time.sleep(0.5)  # Simulate connection delay
        self._state = ConnectionState.CONNECTED
        log.info("Dummy power supply connected")
        return True

    def disconnect(self) -> None:
        """Disconnect from the dummy power supply."""
        log.info("Disconnecting from dummy power supply")
        # Turn off all outputs on disconnect
        for state in self._channel_states:
            state.output_enabled = False
        self._state = ConnectionState.DISCONNECTED

    def reset(self) -> None:
        """Reset the dummy power supply."""
        log.info("Resetting dummy power supply")
        for state in self._channel_states:
            state.output_enabled = False
            state.voltage_setpoint = 0.0
            state.current_limit = 1.0
            state.actual_voltage = 0.0
            state.actual_current = 0.0
            state.actual_power = 0.0
            state.mode = OutputMode.CONSTANT_VOLTAGE
            state.protection = ProtectionState.NONE

    def set_output_enabled(self, channel: int, enabled: bool) -> None:
        """Enable or disable output."""
        state = self._channel_states[channel - 1]
        state.output_enabled = enabled
        if not enabled:
            state.actual_voltage = 0.0
            state.actual_current = 0.0
            state.actual_power = 0.0
        log.debug("Channel %d output: %s", channel, "ON" if enabled else "OFF")

    def set_voltage(self, channel: int, voltage: float) -> None:
        """Set voltage setpoint."""
        caps = self._channel_capabilities[channel - 1]
        voltage = max(caps.min_voltage, min(caps.max_voltage, voltage))
        self._channel_states[channel - 1].voltage_setpoint = voltage
        log.debug("Channel %d voltage setpoint: %.3f V", channel, voltage)

    def set_current_limit(self, channel: int, current: float) -> None:
        """Set current limit."""
        caps = self._channel_capabilities[channel - 1]
        current = max(caps.min_current, min(caps.max_current, current))
        self._channel_states[channel - 1].current_limit = current
        log.debug("Channel %d current limit: %.3f A", channel, current)

    def _simulate_output(self, channel: int) -> None:
        """Simulate the output based on setpoints and load."""
        state = self._channel_states[channel - 1]
        caps = self._channel_capabilities[channel - 1]

        if not state.output_enabled:
            state.actual_voltage = 0.0
            state.actual_current = 0.0
            state.actual_power = 0.0
            state.mode = OutputMode.CONSTANT_VOLTAGE
            return

        log.debug("Simulating CH%d: setpoint=%.3f V", channel, state.voltage_setpoint)

        load_r = self._load_resistance[channel - 1]

        # Calculate what current would flow at set voltage
        ideal_current = state.voltage_setpoint / load_r if load_r > 0 else 0

        if ideal_current <= state.current_limit:
            # Constant voltage mode
            state.mode = OutputMode.CONSTANT_VOLTAGE
            state.actual_voltage = state.voltage_setpoint
            state.actual_current = ideal_current
        else:
            # Constant current mode
            state.mode = OutputMode.CONSTANT_CURRENT
            state.actual_current = state.current_limit
            state.actual_voltage = state.current_limit * load_r

        # Add some noise
        state.actual_voltage += np.random.randn() * 0.001
        state.actual_current += np.random.randn() * 0.0001

        # Clamp to valid ranges
        state.actual_voltage = max(0, min(caps.max_voltage, state.actual_voltage))
        state.actual_current = max(0, min(caps.max_current, state.actual_current))

        state.actual_power = state.actual_voltage * state.actual_current

    def get_voltage(self, channel: int) -> float:
        """Get actual output voltage."""
        self._simulate_output(channel)
        return self._channel_states[channel - 1].actual_voltage

    def get_current(self, channel: int) -> float:
        """Get actual output current."""
        self._simulate_output(channel)
        return self._channel_states[channel - 1].actual_current

    def get_power(self, channel: int) -> float:
        """Get actual output power."""
        self._simulate_output(channel)
        return self._channel_states[channel - 1].actual_power

    def get_voltage_setpoint(self, channel: int) -> float:
        """Get voltage setpoint."""
        return self._channel_states[channel - 1].voltage_setpoint

    def get_current_limit(self, channel: int) -> float:
        """Get current limit."""
        return self._channel_states[channel - 1].current_limit

    def is_output_enabled(self, channel: int) -> bool:
        """Check if output is enabled."""
        return self._channel_states[channel - 1].output_enabled

    def get_output_mode(self, channel: int) -> OutputMode:
        """Get output mode (CV/CC)."""
        self._simulate_output(channel)
        return self._channel_states[channel - 1].mode

    def clear_protection(self, channel: int) -> None:
        """Clear protection state."""
        self._channel_states[channel - 1].protection = ProtectionState.NONE
        log.debug("Channel %d protection cleared", channel)

    def set_load_resistance(self, channel: int, resistance: float) -> None:
        """Set simulated load resistance for testing (dummy-specific)."""
        self._load_resistance[channel - 1] = max(0.1, resistance)
        log.debug("Channel %d simulated load: %.1f ohms", channel, resistance)
