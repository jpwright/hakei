"""Abstract base class for oscilloscopes."""

from abc import abstractmethod
from enum import Enum, auto
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel

from hakei.instruments.base import Instrument


class TriggerMode(Enum):
    """Oscilloscope trigger modes."""

    AUTO = auto()
    NORMAL = auto()
    SINGLE = auto()


class TriggerEdge(Enum):
    """Trigger edge types."""

    RISING = auto()
    FALLING = auto()
    EITHER = auto()


class Coupling(Enum):
    """Input coupling modes."""

    DC = auto()
    AC = auto()
    GND = auto()


class AcquisitionState(Enum):
    """Acquisition state."""

    STOPPED = auto()
    RUNNING = auto()
    SINGLE = auto()
    COMPLETE = auto()


class DisplayMode(Enum):
    """Oscilloscope display modes."""

    NORMAL = auto()   # Wait for full screen, then refresh
    ROLL = auto()     # Plot left-to-right, clear when reaching right edge
    SCREEN = auto()   # Continuous refresh, pushing old data off left edge


class ChannelConfig(BaseModel):
    """Configuration for an oscilloscope channel."""

    enabled: bool = False
    scale: float = 1.0  # V/div
    offset: float = 0.0  # V
    coupling: Coupling = Coupling.DC
    bandwidth_limit: bool = False
    probe_attenuation: float = 1.0


class TimebaseConfig(BaseModel):
    """Configuration for the oscilloscope timebase."""

    scale: float = 1e-3  # s/div
    offset: float = 0.0  # s
    reference: Literal["left", "center", "right"] = "center"


class TriggerConfig(BaseModel):
    """Configuration for the oscilloscope trigger."""

    enabled: bool = False
    source: int = 1  # Channel number
    mode: TriggerMode = TriggerMode.AUTO
    edge: TriggerEdge = TriggerEdge.RISING
    level: float = 0.0  # V


class WaveformData(BaseModel):
    """Waveform data from an oscilloscope channel."""

    model_config = {"arbitrary_types_allowed": True}

    channel: int
    time: NDArray[np.float64]
    voltage: NDArray[np.float64]
    sample_rate: float = 0.0
    num_points: int = 0


class Oscilloscope(Instrument):
    """Abstract base class for oscilloscopes."""

    _panel_class_path = "hakei.ui.views.OscilloscopePanel"
    _config_class_path = "hakei.config.OscilloscopeConfig"
    default_channels = 4

    # Subclasses should override these constraints
    MIN_SAMPLE_RATE: float = 1.0  # Hz
    MAX_SAMPLE_RATE: float = 100e6  # Hz
    MIN_BUFFER_SIZE: int = 100
    MAX_BUFFER_SIZE: int = 100000
    PREFERRED_BUFFER_SIZE: int = 10000

    def __init__(self, resource_address: str, num_channels: int = 4, device=None):
        super().__init__(resource_address, device=device)
        self.num_channels = num_channels
        self._channel_configs: list[ChannelConfig] = [
            ChannelConfig() for _ in range(num_channels)
        ]
        self._timebase = TimebaseConfig()
        self._trigger = TriggerConfig()
        self._acquisition_state = AcquisitionState.STOPPED
        self._sample_rate: float = 1e6
        self._buffer_size: int = self.PREFERRED_BUFFER_SIZE

    @property
    def acquisition_state(self) -> AcquisitionState:
        """Get the current acquisition state."""
        return self._acquisition_state

    def get_channel_config(self, channel: int) -> ChannelConfig:
        """Get configuration for a channel (1-indexed)."""
        return self._channel_configs[channel - 1]

    @property
    def timebase(self) -> TimebaseConfig:
        """Get the timebase configuration."""
        return self._timebase

    @property
    def trigger(self) -> TriggerConfig:
        """Get the trigger configuration."""
        return self._trigger

    @property
    def sample_rate(self) -> float:
        """Get the current sample rate in Hz."""
        return self._sample_rate

    @property
    def buffer_size(self) -> int:
        """Get the current buffer size in samples."""
        return self._buffer_size

    def set_timebase_length(self, length: float) -> None:
        """Set the total timebase length and compute sample rate and buffer size.

        Args:
            length: Total time window in seconds.
        """
        # Start with preferred buffer size and compute ideal sample rate
        ideal_sample_rate = self.PREFERRED_BUFFER_SIZE / length

        # Clamp sample rate to valid range
        self._sample_rate = max(self.MIN_SAMPLE_RATE, min(ideal_sample_rate, self.MAX_SAMPLE_RATE))

        # Compute buffer size from clamped sample rate
        ideal_buffer_size = int(self._sample_rate * length)

        # Clamp buffer size to valid range
        self._buffer_size = max(self.MIN_BUFFER_SIZE, min(ideal_buffer_size, self.MAX_BUFFER_SIZE))

        # If buffer size was clamped, recalculate sample rate to match
        if ideal_buffer_size != self._buffer_size:
            self._sample_rate = self._buffer_size / length

        # Update timebase scale (10 divisions)
        self._timebase.scale = length / 10

        # Subclasses can override to apply hardware settings
        self._apply_timebase_settings()

    def _apply_timebase_settings(self) -> None:
        """Apply timebase settings to hardware. Override in subclasses."""
        pass

    @abstractmethod
    def run(self) -> None:
        """Start continuous acquisition."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop acquisition."""
        ...

    @abstractmethod
    def single(self) -> None:
        """Perform a single acquisition."""
        ...

    @abstractmethod
    def force_trigger(self) -> None:
        """Force a trigger event."""
        ...

    @abstractmethod
    def auto_scale(self) -> None:
        """Automatically configure scales for optimal viewing."""
        ...

    @abstractmethod
    def set_channel_enabled(self, channel: int, enabled: bool) -> None:
        """Enable or disable a channel."""
        ...

    def set_channel_scale(self, channel: int, scale: float) -> None:
        """Set the vertical scale for a channel.
        
        This is a display-only scale applied in the UI.
        """
        self._channel_configs[channel - 1].scale = scale

    def set_channel_offset(self, channel: int, offset: float) -> None:
        """Set the vertical offset for a channel.
        
        This is a display-only offset applied in the UI.
        """
        self._channel_configs[channel - 1].offset = offset

    @abstractmethod
    def set_channel_coupling(self, channel: int, coupling: Coupling) -> None:
        """Set the input coupling for a channel."""
        ...

    def set_timebase_scale(self, scale: float) -> None:
        """Set the horizontal scale (s/div).
        
        Internally calls set_timebase_length with scale * 10 divisions.
        """
        self.set_timebase_length(scale * 10)

    def set_timebase_offset(self, offset: float) -> None:
        """Set the horizontal offset (s)."""
        self._timebase.offset = offset

    @abstractmethod
    def set_trigger_enabled(self, enabled: bool) -> None:
        """Enable or disable the trigger."""
        ...

    @abstractmethod
    def set_trigger_source(self, channel: int) -> None:
        """Set the trigger source channel."""
        ...

    @abstractmethod
    def set_trigger_mode(self, mode: TriggerMode) -> None:
        """Set the trigger mode."""
        ...

    @abstractmethod
    def set_trigger_edge(self, edge: TriggerEdge) -> None:
        """Set the trigger edge type."""
        ...

    @abstractmethod
    def set_trigger_level(self, level: float) -> None:
        """Set the trigger level (V)."""
        ...

    @abstractmethod
    def get_waveform(self, channel: int) -> WaveformData:
        """
        Acquire waveform data from a channel.

        Args:
            channel: Channel number (1-indexed).

        Returns:
            WaveformData containing time and voltage arrays.
        """
        ...

    def measure_frequency(self, channel: int) -> float:
        """Measure the frequency on a channel using zero-crossing detection."""
        waveform = self.get_waveform(channel)
        if len(waveform.voltage) < 2 or waveform.sample_rate <= 0:
            return 0.0
        crossings = np.where(np.diff(np.sign(waveform.voltage - np.mean(waveform.voltage))))[0]
        if len(crossings) < 2:
            return 0.0
        period = np.mean(np.diff(crossings)) * 2 / waveform.sample_rate
        return 1.0 / period if period > 0 else 0.0

    def measure_period(self, channel: int) -> float:
        """Measure the period on a channel."""
        freq = self.measure_frequency(channel)
        return 1.0 / freq if freq > 0 else 0.0

    def measure_amplitude(self, channel: int) -> float:
        """Measure the peak-to-peak amplitude on a channel."""
        waveform = self.get_waveform(channel)
        if len(waveform.voltage) == 0:
            return 0.0
        return float(np.max(waveform.voltage) - np.min(waveform.voltage))

    def measure_mean(self, channel: int) -> float:
        """Measure the mean voltage on a channel."""
        waveform = self.get_waveform(channel)
        if len(waveform.voltage) == 0:
            return 0.0
        return float(np.mean(waveform.voltage))

    def measure_rms(self, channel: int) -> float:
        """Measure the RMS voltage on a channel."""
        waveform = self.get_waveform(channel)
        if len(waveform.voltage) == 0:
            return 0.0
        return float(np.sqrt(np.mean(waveform.voltage ** 2)))
