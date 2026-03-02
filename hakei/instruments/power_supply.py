"""Abstract base class for power supplies."""

from abc import abstractmethod
from enum import Enum, auto

from pydantic import BaseModel

from hakei.instruments.base import Instrument


class OutputMode(Enum):
    """Power supply output regulation mode."""

    CONSTANT_VOLTAGE = auto()
    CONSTANT_CURRENT = auto()
    UNREGULATED = auto()


class ProtectionState(Enum):
    """Protection state for a channel."""

    NONE = auto()
    OVER_VOLTAGE = auto()
    OVER_CURRENT = auto()
    OVER_POWER = auto()
    OVER_TEMPERATURE = auto()


class ChannelState(BaseModel):
    """Current state of a power supply channel."""

    output_enabled: bool = False
    voltage_setpoint: float = 0.0
    current_limit: float = 0.0
    actual_voltage: float = 0.0
    actual_current: float = 0.0
    actual_power: float = 0.0
    mode: OutputMode = OutputMode.CONSTANT_VOLTAGE
    protection: ProtectionState = ProtectionState.NONE


class ChannelCapabilities(BaseModel):
    """Capabilities of a power supply channel."""

    max_voltage: float = 30.0
    max_current: float = 5.0
    max_power: float = 150.0
    min_voltage: float = 0.0
    min_current: float = 0.0
    voltage_resolution: float = 0.001
    current_resolution: float = 0.001


class PowerSupply(Instrument):
    """Abstract base class for power supplies."""

    _panel_class_path = "hakei.ui.views.PowerSupplyPanel"
    _config_class_path = "hakei.config.PowerSupplyConfig"
    default_channels = 2

    def __init__(self, resource_address: str, num_channels: int = 1, device=None):
        super().__init__(resource_address, device=device)
        self.num_channels = num_channels
        self._channel_states: list[ChannelState] = [
            ChannelState() for _ in range(num_channels)
        ]
        self._channel_capabilities: list[ChannelCapabilities] = [
            ChannelCapabilities() for _ in range(num_channels)
        ]

    def get_channel_state(self, channel: int) -> ChannelState:
        """Get the current state of a channel (1-indexed)."""
        return self._channel_states[channel - 1]

    def get_channel_capabilities(self, channel: int) -> ChannelCapabilities:
        """Get the capabilities of a channel (1-indexed)."""
        return self._channel_capabilities[channel - 1]

    @abstractmethod
    def set_output_enabled(self, channel: int, enabled: bool) -> None:
        """Enable or disable the output of a channel."""
        ...

    @abstractmethod
    def set_voltage(self, channel: int, voltage: float) -> None:
        """Set the voltage setpoint for a channel."""
        ...

    @abstractmethod
    def set_current_limit(self, channel: int, current: float) -> None:
        """Set the current limit for a channel."""
        ...

    @abstractmethod
    def get_voltage(self, channel: int) -> float:
        """Get the actual output voltage of a channel."""
        ...

    @abstractmethod
    def get_current(self, channel: int) -> float:
        """Get the actual output current of a channel."""
        ...

    @abstractmethod
    def get_power(self, channel: int) -> float:
        """Get the actual output power of a channel."""
        ...

    @abstractmethod
    def get_voltage_setpoint(self, channel: int) -> float:
        """Get the voltage setpoint of a channel."""
        ...

    @abstractmethod
    def get_current_limit(self, channel: int) -> float:
        """Get the current limit of a channel."""
        ...

    @abstractmethod
    def is_output_enabled(self, channel: int) -> bool:
        """Check if the output of a channel is enabled."""
        ...

    @abstractmethod
    def get_output_mode(self, channel: int) -> OutputMode:
        """Get the current output mode (CV/CC) of a channel."""
        ...

    @abstractmethod
    def clear_protection(self, channel: int) -> None:
        """Clear any protection state on a channel."""
        ...

    def set_all_outputs_enabled(self, enabled: bool) -> None:
        """Enable or disable all outputs."""
        for channel in range(1, self.num_channels + 1):
            self.set_output_enabled(channel, enabled)

    def update_channel_state(self, channel: int) -> ChannelState:
        """
        Update and return the state of a channel by querying the instrument.

        Args:
            channel: Channel number (1-indexed).

        Returns:
            Updated ChannelState.
        """
        state = self._channel_states[channel - 1]
        state.output_enabled = self.is_output_enabled(channel)
        state.voltage_setpoint = self.get_voltage_setpoint(channel)
        state.current_limit = self.get_current_limit(channel)
        state.actual_voltage = self.get_voltage(channel)
        state.actual_current = self.get_current(channel)
        state.actual_power = self.get_power(channel)
        state.mode = self.get_output_mode(channel)
        return state
