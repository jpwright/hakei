"""Abstract base class for waveform generators."""

from abc import abstractmethod
from enum import Enum, auto

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel

from hakei.instruments.base import Instrument


class WaveformType(Enum):
    """Standard waveform types."""

    SINE = auto()
    SQUARE = auto()
    TRIANGLE = auto()
    RAMP = auto()
    PULSE = auto()
    NOISE = auto()
    DC = auto()
    ARBITRARY = auto()


class ModulationType(Enum):
    """Modulation types."""

    NONE = auto()
    AM = auto()  # Amplitude modulation
    FM = auto()  # Frequency modulation
    PM = auto()  # Phase modulation
    FSK = auto()  # Frequency-shift keying
    PWM = auto()  # Pulse-width modulation


class OutputLoad(Enum):
    """Output load impedance."""

    HIGH_Z = auto()
    FIFTY_OHM = auto()


class ChannelConfig(BaseModel):
    """Configuration for a waveform generator channel."""

    output_enabled: bool = False
    waveform: WaveformType = WaveformType.SINE
    frequency: float = 1000.0  # Hz
    amplitude: float = 1.0  # Vpp
    offset: float = 0.0  # V
    phase: float = 0.0  # degrees
    duty_cycle: float = 50.0  # % (for square/pulse)
    symmetry: float = 50.0  # % (for triangle/ramp)
    output_load: OutputLoad = OutputLoad.HIGH_Z


class ModulationConfig(BaseModel):
    """Configuration for modulation."""

    enabled: bool = False
    mod_type: ModulationType = ModulationType.NONE
    source_internal: bool = True
    mod_frequency: float = 100.0  # Hz (internal source)
    mod_depth: float = 50.0  # % (AM)
    fm_deviation: float = 100.0  # Hz (FM)
    pm_deviation: float = 90.0  # degrees (PM)


class ChannelCapabilities(BaseModel):
    """Capabilities of a waveform generator channel."""

    max_frequency: float = 25e6  # Hz
    min_frequency: float = 1e-6  # Hz
    max_amplitude: float = 10.0  # Vpp
    min_amplitude: float = 0.001  # Vpp
    max_offset: float = 5.0  # V
    min_offset: float = -5.0  # V
    arbitrary_waveform_points: int = 16384


class WaveformGenerator(Instrument):
    """Abstract base class for waveform generators."""

    _panel_class_path = "hakei.ui.views.WaveformGeneratorPanel"
    _config_class_path = "hakei.config.WaveformGeneratorConfig"
    default_channels = 1

    def __init__(self, resource_address: str, num_channels: int = 1, device=None):
        super().__init__(resource_address, device=device)
        self.num_channels = num_channels
        self._channel_configs: list[ChannelConfig] = [
            ChannelConfig() for _ in range(num_channels)
        ]
        self._modulation_configs: list[ModulationConfig] = [
            ModulationConfig() for _ in range(num_channels)
        ]
        self._channel_capabilities: list[ChannelCapabilities] = [
            ChannelCapabilities() for _ in range(num_channels)
        ]

    def get_channel_config(self, channel: int) -> ChannelConfig:
        """Get configuration for a channel (1-indexed)."""
        return self._channel_configs[channel - 1]

    def get_modulation_config(self, channel: int) -> ModulationConfig:
        """Get modulation configuration for a channel (1-indexed)."""
        return self._modulation_configs[channel - 1]

    def get_channel_capabilities(self, channel: int) -> ChannelCapabilities:
        """Get capabilities of a channel (1-indexed)."""
        return self._channel_capabilities[channel - 1]

    # State management methods (handle _channel_configs, call hardware methods)

    def set_output_enabled(self, channel: int, enabled: bool) -> None:
        """Enable or disable the output of a channel."""
        self._channel_configs[channel - 1].output_enabled = enabled
        self._hw_set_output_enabled(channel, enabled)

    def is_output_enabled(self, channel: int) -> bool:
        """Check if the output of a channel is enabled."""
        return self._channel_configs[channel - 1].output_enabled

    def set_waveform(self, channel: int, waveform: WaveformType) -> None:
        """Set the waveform type for a channel."""
        self._channel_configs[channel - 1].waveform = waveform
        self._hw_set_waveform(channel, waveform)

    def set_frequency(self, channel: int, frequency: float) -> None:
        """Set the frequency (Hz) for a channel."""
        self._channel_configs[channel - 1].frequency = frequency
        self._hw_set_frequency(channel, frequency)

    def set_amplitude(self, channel: int, amplitude: float) -> None:
        """Set the amplitude (Vpp) for a channel."""
        self._channel_configs[channel - 1].amplitude = amplitude
        self._hw_set_amplitude(channel, amplitude)

    def set_offset(self, channel: int, offset: float) -> None:
        """Set the DC offset (V) for a channel."""
        self._channel_configs[channel - 1].offset = offset
        self._hw_set_offset(channel, offset)

    def set_phase(self, channel: int, phase: float) -> None:
        """Set the phase (degrees) for a channel."""
        self._channel_configs[channel - 1].phase = phase
        self._hw_set_phase(channel, phase)

    def set_duty_cycle(self, channel: int, duty_cycle: float) -> None:
        """Set the duty cycle (%) for square/pulse waveforms."""
        self._channel_configs[channel - 1].duty_cycle = duty_cycle
        self._hw_set_duty_cycle(channel, duty_cycle)

    def get_frequency(self, channel: int) -> float:
        """Get the current frequency setting (Hz) of a channel."""
        return self._channel_configs[channel - 1].frequency

    def get_amplitude(self, channel: int) -> float:
        """Get the current amplitude setting (Vpp) of a channel."""
        return self._channel_configs[channel - 1].amplitude

    def get_offset(self, channel: int) -> float:
        """Get the current offset setting (V) of a channel."""
        return self._channel_configs[channel - 1].offset

    def set_modulation_enabled(self, channel: int, enabled: bool) -> None:
        """Enable or disable modulation on a channel."""
        self._modulation_configs[channel - 1].enabled = enabled
        self._hw_set_modulation_enabled(channel, enabled)

    def set_modulation_type(self, channel: int, mod_type: ModulationType) -> None:
        """Set the modulation type for a channel."""
        self._modulation_configs[channel - 1].mod_type = mod_type
        self._hw_set_modulation_type(channel, mod_type)

    def set_modulation_frequency(self, channel: int, frequency: float) -> None:
        """Set the internal modulation frequency (Hz)."""
        self._modulation_configs[channel - 1].mod_frequency = frequency
        self._hw_set_modulation_frequency(channel, frequency)

    def set_modulation_depth(self, channel: int, depth: float) -> None:
        """Set the AM modulation depth (%)."""
        self._modulation_configs[channel - 1].mod_depth = depth
        self._hw_set_modulation_depth(channel, depth)

    # Abstract hardware methods (to be implemented by subclasses)

    @abstractmethod
    def _hw_set_output_enabled(self, channel: int, enabled: bool) -> None:
        """Hardware: Enable or disable the output of a channel."""
        ...

    @abstractmethod
    def _hw_set_waveform(self, channel: int, waveform: WaveformType) -> None:
        """Hardware: Set the waveform type for a channel."""
        ...

    @abstractmethod
    def _hw_set_frequency(self, channel: int, frequency: float) -> None:
        """Hardware: Set the frequency (Hz) for a channel."""
        ...

    @abstractmethod
    def _hw_set_amplitude(self, channel: int, amplitude: float) -> None:
        """Hardware: Set the amplitude (Vpp) for a channel."""
        ...

    @abstractmethod
    def _hw_set_offset(self, channel: int, offset: float) -> None:
        """Hardware: Set the DC offset (V) for a channel."""
        ...

    @abstractmethod
    def _hw_set_phase(self, channel: int, phase: float) -> None:
        """Hardware: Set the phase (degrees) for a channel."""
        ...

    @abstractmethod
    def _hw_set_duty_cycle(self, channel: int, duty_cycle: float) -> None:
        """Hardware: Set the duty cycle (%) for square/pulse waveforms."""
        ...

    def _hw_set_modulation_enabled(self, channel: int, enabled: bool) -> None:
        """Hardware: Enable or disable modulation on a channel. Optional."""
        pass

    def _hw_set_modulation_type(self, channel: int, mod_type: ModulationType) -> None:
        """Hardware: Set the modulation type for a channel. Optional."""
        pass

    def _hw_set_modulation_frequency(self, channel: int, frequency: float) -> None:
        """Hardware: Set the internal modulation frequency (Hz). Optional."""
        pass

    def _hw_set_modulation_depth(self, channel: int, depth: float) -> None:
        """Hardware: Set the AM modulation depth (%). Optional."""
        pass

    @abstractmethod
    def load_arbitrary_waveform(
        self, channel: int, data: NDArray[np.float64], name: str = "ARB"
    ) -> None:
        """
        Load arbitrary waveform data to a channel.

        Args:
            channel: Channel number (1-indexed).
            data: Normalized waveform data (-1.0 to 1.0).
            name: Name for the waveform in instrument memory.
        """
        ...

    def sync_channels(self, enable: bool = True) -> None:
        """
        Synchronize phases of all channels.

        Default implementation does nothing; override if supported.
        """
        pass
