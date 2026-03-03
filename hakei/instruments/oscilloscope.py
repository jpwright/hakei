"""Abstract base class for oscilloscopes."""

from abc import abstractmethod
from enum import Enum, auto
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

    span: float = 10e-3  # total time span in seconds
    offset: float = 0.0  # s


class TriggerConfig(BaseModel):
    """Configuration for the oscilloscope trigger."""

    enabled: bool = False
    source: int = 1  # Channel number
    mode: TriggerMode = TriggerMode.AUTO
    edge: TriggerEdge = TriggerEdge.RISING
    level: float = 0.0  # V
    position: float = 0.0  # seconds, time offset of trigger point from left edge
    holdoff: float = 0.0  # seconds, minimum time before re-trigger


class WaveformData(BaseModel):
    """Waveform data from an oscilloscope acquisition.

    voltage is shape (num_channels, num_points) with voltage[channel_index]
    for channel (channel_index + 1). The time axis is not included; the
    caller derives it from sample_rate and num_points.
    """

    model_config = {"arbitrary_types_allowed": True}

    voltage: NDArray[np.float64]  # shape (num_channels, num_points)
    sample_rate: float = 0.0
    num_points: int = 0
    num_channels: int = 0


class Oscilloscope(Instrument):
    """Abstract base class for oscilloscopes."""

    _panel_class_path = "hakei.ui.views.OscilloscopePanel"
    _config_class_path = "hakei.config.OscilloscopeConfig"
    num_channels: int = 4

    def __init__(self, resource_address: str, device=None):
        super().__init__(resource_address, device=device)
        self._channel_configs: list[ChannelConfig] = [
            ChannelConfig() for _ in range(self.num_channels)
        ]
        self._timebase = TimebaseConfig()
        self._trigger = TriggerConfig()
        self._acquisition_state = AcquisitionState.STOPPED
        self._display_mode: DisplayMode = DisplayMode.NORMAL
        self._sample_rate: float = 1e6
        self._buffer_size: int = 10000

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
    def display_mode(self) -> DisplayMode:
        """Get the display mode (Normal, Roll, or Screen)."""
        return self._display_mode

    def set_display_mode(self, mode: DisplayMode) -> None:
        """Set the display mode. Provided by the UI."""
        self._display_mode = mode

    @property
    def sample_rate(self) -> float:
        """Get the current sample rate in Hz."""
        return self._sample_rate

    @property
    def buffer_size(self) -> int:
        """Get the current buffer size in samples."""
        return self._buffer_size

    def set_timebase_length(self, length: float) -> None:
        """Set the total timebase span in seconds.

        Updates ``_timebase.span`` then calls
        ``_apply_timebase_settings`` so subclasses can adjust
        ``_sample_rate``, ``_buffer_size``, or hardware registers.
        """
        self._timebase.span = length
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

    def set_timebase_span(self, span: float) -> None:
        """Set the total horizontal time span (s)."""
        self.set_timebase_length(span)

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

    def set_trigger_position(self, position: float) -> None:
        """Set trigger position in seconds from the left edge of the screen."""
        self._trigger.position = max(0.0, position)

    def set_trigger_holdoff(self, holdoff: float) -> None:
        """Set trigger holdoff in seconds (minimum time before re-trigger)."""
        self._trigger.holdoff = max(0.0, holdoff)

    @abstractmethod
    def get_waveform(self) -> WaveformData:
        """
        Acquire waveform data for all configured channels.

        Returns:
            WaveformData with voltage shape (num_channels, num_points).
            Channel index i corresponds to channel number i + 1.
        """
        ...

    def measure_frequency(self, channel: int) -> float:
        """Measure the frequency on a channel using zero-crossing detection."""
        waveform = self.get_waveform()
        ch_idx = channel - 1
        if ch_idx >= waveform.num_channels or waveform.num_points < 2 or waveform.sample_rate <= 0:
            return 0.0
        v = waveform.voltage[ch_idx]
        crossings = np.where(np.diff(np.sign(v - np.mean(v))))[0]
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
        waveform = self.get_waveform()
        ch_idx = channel - 1
        if ch_idx >= waveform.num_channels or waveform.num_points == 0:
            return 0.0
        v = waveform.voltage[ch_idx]
        return float(np.max(v) - np.min(v))

    def measure_mean(self, channel: int) -> float:
        """Measure the mean voltage on a channel."""
        waveform = self.get_waveform()
        ch_idx = channel - 1
        if ch_idx >= waveform.num_channels or waveform.num_points == 0:
            return 0.0
        return float(np.mean(waveform.voltage[ch_idx]))

    def measure_rms(self, channel: int) -> float:
        """Measure the RMS voltage on a channel."""
        waveform = self.get_waveform()
        ch_idx = channel - 1
        if ch_idx >= waveform.num_channels or waveform.num_points == 0:
            return 0.0
        v = waveform.voltage[ch_idx]
        return float(np.sqrt(np.mean(v ** 2)))
