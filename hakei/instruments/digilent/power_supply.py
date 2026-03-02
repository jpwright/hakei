"""Digilent power supply implementation."""

import logging
from ctypes import byref, c_double, c_int

from hakei.instruments.base import ConnectionState
from hakei.instruments.digilent.device import DigilentDevice
from hakei.instruments.power_supply import (
    ChannelCapabilities,
    OutputMode,
    PowerSupply,
)

log = logging.getLogger(__name__)


class DigilentPowerSupply(PowerSupply):
    """
    Power supply implementation for Digilent devices.

    The Analog Discovery 2 has two programmable power supplies:
    - V+ (positive): 0 to +5V
    - V- (negative): 0 to -5V (shown as channel 2)
    """

    def __init__(
        self,
        resource_address: str,
        device: DigilentDevice,
        num_channels: int = 2,
    ):
        super().__init__(resource_address, num_channels, device=device)

    @property
    def hdwf(self) -> c_int:
        """Get the DWF device handle."""
        return self.device.hdwf

    def _get_dwf(self):
        """Get the DWF library."""
        from hakei.instruments.digilent.dwf import get_dwf
        return get_dwf()

    def connect(self) -> bool:
        """Connect is handled by the parent device."""
        self._state = ConnectionState.CONNECTED
        log.info("Digilent power supply ready")
        return True

    def disconnect(self) -> None:
        """Disconnect is handled by the parent device."""
        for ch in range(1, self.num_channels + 1):
            try:
                self.set_output_enabled(ch, False)
            except Exception:
                pass
        self._state = ConnectionState.DISCONNECTED

    def reset(self) -> None:
        """Reset the power supply to default settings."""
        for ch in range(1, self.num_channels + 1):
            self.set_output_enabled(ch, False)
            self.set_voltage(ch, 0.0)

    def set_voltage(self, channel: int, voltage: float) -> None:
        """Set the output voltage for a channel."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")

        dwf = self._get_dwf()
        if not dwf:
            return

        ch_idx = channel - 1
        dwf.FDwfAnalogIOChannelNodeSet(
            self.hdwf, c_int(ch_idx), c_int(0), c_double(voltage)
        )

        self._channel_states[ch_idx].voltage_setpoint = voltage
        log.debug("Channel %d voltage set to %.3f V", channel, voltage)

    def set_current_limit(self, channel: int, current: float) -> None:
        """Set the current limit for a channel (AD2 has fixed limit)."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")

        ch_idx = channel - 1
        self._channel_states[ch_idx].current_limit = current
        log.debug("Channel %d current limit set to %.3f A", channel, current)

    def set_output_enabled(self, channel: int, enabled: bool) -> None:
        """Enable or disable output on a channel."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")

        dwf = self._get_dwf()
        if not dwf:
            return

        ch_idx = channel - 1
        dwf.FDwfAnalogIOChannelNodeSet(
            self.hdwf, c_int(ch_idx), c_int(1), c_double(1.0 if enabled else 0.0)
        )
        dwf.FDwfAnalogIOEnableSet(self.hdwf, c_int(1 if enabled else 0))

        self._channel_states[ch_idx].output_enabled = enabled
        log.info("Channel %d output %s", channel, "enabled" if enabled else "disabled")

    def get_voltage(self, channel: int) -> float:
        """Get the actual output voltage for a channel."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")

        dwf = self._get_dwf()
        ch_idx = channel - 1

        if not dwf:
            return self._channel_states[ch_idx].voltage_setpoint

        dwf.FDwfAnalogIOStatus(self.hdwf)
        voltage = c_double()
        dwf.FDwfAnalogIOChannelNodeStatus(
            self.hdwf, c_int(ch_idx), c_int(0), byref(voltage)
        )

        self._channel_states[ch_idx].actual_voltage = voltage.value
        return voltage.value

    def get_current(self, channel: int) -> float:
        """Get the actual output current for a channel."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")

        dwf = self._get_dwf()
        ch_idx = channel - 1

        if not dwf:
            return 0.0

        dwf.FDwfAnalogIOStatus(self.hdwf)
        current = c_double()
        dwf.FDwfAnalogIOChannelNodeStatus(
            self.hdwf, c_int(ch_idx), c_int(1), byref(current)
        )

        self._channel_states[ch_idx].actual_current = current.value
        return current.value

    def get_power(self, channel: int) -> float:
        """Get the actual output power for a channel."""
        voltage = self.get_voltage(channel)
        current = self.get_current(channel)
        power = abs(voltage * current)
        self._channel_states[channel - 1].actual_power = power
        return power

    def get_voltage_setpoint(self, channel: int) -> float:
        """Get the voltage setpoint of a channel."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")
        return self._channel_states[channel - 1].voltage_setpoint

    def get_current_limit(self, channel: int) -> float:
        """Get the current limit of a channel."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")
        return self._channel_states[channel - 1].current_limit

    def is_output_enabled(self, channel: int) -> bool:
        """Check if the output of a channel is enabled."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")
        return self._channel_states[channel - 1].output_enabled

    def get_output_mode(self, channel: int) -> OutputMode:
        """Get the current output mode (CV/CC) of a channel."""
        if not 1 <= channel <= self.num_channels:
            raise ValueError(f"Invalid channel: {channel}")
        return self._channel_states[channel - 1].mode

    def clear_protection(self, channel: int) -> None:
        """Clear any protection state on a channel (no-op for AD2)."""
        pass

    def get_channel_capabilities(self, channel: int) -> ChannelCapabilities:
        """Get the capabilities for a channel."""
        if channel == 1:
            return ChannelCapabilities(
                min_voltage=0.0,
                max_voltage=5.0,
                min_current=0.0,
                max_current=0.7,
                voltage_resolution=0.01,
                current_resolution=0.001,
            )
        else:
            return ChannelCapabilities(
                min_voltage=-5.0,
                max_voltage=0.0,
                min_current=0.0,
                max_current=0.7,
                voltage_resolution=0.01,
                current_resolution=0.001,
            )
