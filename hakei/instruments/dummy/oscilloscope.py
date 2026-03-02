"""Dummy oscilloscope implementation emulating a 100 MHz scope."""

import logging
import time

import numpy as np

from hakei.instruments.base import ConnectionState, InstrumentInfo
from hakei.instruments.oscilloscope import (
    AcquisitionState,
    Coupling,
    Oscilloscope,
    TriggerEdge,
    TriggerMode,
    WaveformData,
)

log = logging.getLogger(__name__)


class DummyOscilloscope(Oscilloscope):
    """Dummy oscilloscope emulating a 100 MHz scope.

    Generates continuous signals and captures data based on timebase,
    trigger, and horizontal offset settings - just like a real scope.
    """

    # Dummy scope constraints (emulating a high-end scope)
    MIN_SAMPLE_RATE = 1.0  # 1 Hz
    MAX_SAMPLE_RATE = 100e6  # 100 MHz
    MIN_BUFFER_SIZE = 100
    MAX_BUFFER_SIZE = 100000
    PREFERRED_BUFFER_SIZE = 10000

    def __init__(self, resource_address: str = "DUMMY::OSC::1", num_channels: int = 4, device=None):
        super().__init__(resource_address, num_channels, device=device)
        self._info = InstrumentInfo(
            manufacturer="Hakei",
            model="DummyScope-100MHz",
            serial_number="DUMMY001",
            firmware_version="1.0.0",
        )
        # Oscilloscope internal clock (absolute time reference)
        self._scope_time: float = 0.0
        self._last_real_time: float = 0.0

        # Acquisition state
        self._acquisition_start_time: float = 0.0
        self._last_trigger_time: float = 0.0  # Absolute scope time of last trigger
        self._triggered: bool = False
        self._capture_time: float = 0.0  # Scope time when current capture was taken

    def connect(self) -> bool:
        """Connect to the dummy oscilloscope."""
        log.info("Connecting to dummy oscilloscope: %s", self.resource_address)
        self._state = ConnectionState.CONNECTING
        time.sleep(0.5)
        self._state = ConnectionState.CONNECTED
        self._acquisition_state = AcquisitionState.STOPPED

        self._channel_configs[0].enabled = True
        self._channel_configs[0].scale = 1.0
        self.set_timebase_length(100e-3)  # 10ms/div, 100ms total
        self._timebase.offset = 0.0

        self._scope_time = 0.0
        self._last_real_time = time.time()

        log.info("Dummy oscilloscope connected")
        return True

    def disconnect(self) -> None:
        """Disconnect from the dummy oscilloscope."""
        log.info("Disconnecting from dummy oscilloscope")
        self._state = ConnectionState.DISCONNECTED
        self._acquisition_state = AcquisitionState.STOPPED

    def reset(self) -> None:
        """Reset the dummy oscilloscope."""
        log.info("Resetting dummy oscilloscope")
        for config in self._channel_configs:
            config.enabled = False
            config.scale = 1.0
            config.offset = 0.0
            config.coupling = Coupling.DC
        self._channel_configs[0].enabled = True
        self.set_timebase_length(100e-3)  # 10ms/div
        self._timebase.offset = 0.0
        self._trigger.source = 1
        self._trigger.mode = TriggerMode.AUTO
        self._trigger.edge = TriggerEdge.RISING
        self._trigger.level = 0.0
        self._trigger.enabled = False
        self._acquisition_state = AcquisitionState.STOPPED
        self._scope_time = 0.0
        self._last_real_time = time.time()

    def _update_scope_time(self) -> None:
        """Update internal scope time based on real elapsed time."""
        now = time.time()
        if self._acquisition_state == AcquisitionState.RUNNING:
            self._scope_time += now - self._last_real_time
        self._last_real_time = now

    def run(self) -> None:
        """Start continuous acquisition."""
        self._acquisition_state = AcquisitionState.RUNNING
        self._last_real_time = time.time()
        self._acquisition_start_time = self._scope_time
        self._triggered = False
        log.debug("Dummy oscilloscope: run")

    def stop(self) -> None:
        """Stop acquisition."""
        self._update_scope_time()
        self._acquisition_state = AcquisitionState.STOPPED
        log.debug("Dummy oscilloscope: stop")

    def single(self) -> None:
        """Perform a single acquisition."""
        self._acquisition_state = AcquisitionState.SINGLE
        self._last_real_time = time.time()
        self._triggered = False
        log.debug("Dummy oscilloscope: single")

    def force_trigger(self) -> None:
        """Force a trigger event."""
        self._update_scope_time()
        self._last_trigger_time = self._scope_time
        self._triggered = True
        log.debug("Dummy oscilloscope: force trigger")

    def auto_scale(self) -> None:
        """Auto-scale channels."""
        log.debug("Dummy oscilloscope: auto scale")
        for config in self._channel_configs:
            if config.enabled:
                config.scale = 1.0
                config.offset = 0.0

    def set_channel_enabled(self, channel: int, enabled: bool) -> None:
        self._channel_configs[channel - 1].enabled = enabled

    def set_channel_coupling(self, channel: int, coupling: Coupling) -> None:
        self._channel_configs[channel - 1].coupling = coupling

    def set_trigger_enabled(self, enabled: bool) -> None:
        self._trigger.enabled = enabled

    def set_trigger_source(self, channel: int) -> None:
        self._trigger.source = channel

    def set_trigger_mode(self, mode: TriggerMode) -> None:
        self._trigger.mode = mode

    def set_trigger_edge(self, edge: TriggerEdge) -> None:
        self._trigger.edge = edge

    def set_trigger_level(self, level: float) -> None:
        self._trigger.level = level

    def _signal_value(self, channel: int, t: np.ndarray) -> np.ndarray:
        """Calculate signal value at absolute time t.

        This represents the continuous analog signal that exists
        independent of when we sample it. Channel offset is applied
        at the display level, not here.
        """
        if channel == 1:
            # 50 Hz sine wave, 3V amplitude
            voltage = 3.0 * np.sin(2 * np.pi * 50 * t)
        elif channel == 2:
            # 25 Hz square wave, 2V amplitude
            voltage = 2.0 * np.sign(np.sin(2 * np.pi * 25 * t))
        elif channel == 3:
            # 10 Hz triangle wave, 2.5V amplitude
            phase = (t * 10) % 1
            voltage = 2.5 * (4 * np.abs(phase - 0.5) - 1)
        elif channel == 4:
            # 75 Hz sawtooth wave, 1.5V amplitude
            phase = (t * 75) % 1
            voltage = 1.5 * (2 * phase - 1)
        else:
            # Additional channels: noise
            voltage = 0.5 * np.random.randn(len(t))

        return voltage

    def _find_trigger(self, t_start: float, t_end: float) -> float | None:
        """Find trigger point in the given time range.

        Returns the absolute time of the trigger, or None if not found.
        """
        # Sample the trigger source channel at high resolution
        num_search_points = 10000
        t = np.linspace(t_start, t_end, num_search_points)
        signal = self._signal_value(self._trigger.source, t)

        level = self._trigger.level
        above = signal > level
        edges = np.diff(above.astype(int))

        if self._trigger.edge == TriggerEdge.RISING:
            crossings = np.where(edges == 1)[0]
        elif self._trigger.edge == TriggerEdge.FALLING:
            crossings = np.where(edges == -1)[0]
        else:  # EITHER
            crossings = np.where(edges != 0)[0]

        if len(crossings) == 0:
            return None

        # Return the first trigger point
        return t[crossings[0]]

    def get_waveform(self, channel: int) -> WaveformData:
        """Acquire waveform data from a channel.

        Emulates real oscilloscope behavior:
        - Updates internal clock
        - Searches for trigger (if enabled)
        - Returns data for the requested view window
        - View window is centered at timebase.offset with width = scale * 10
        """
        self._update_scope_time()

        # Calculate display window parameters
        total_time = self._timebase.scale * 10  # 10 divisions

        # The display window in "display time" (what the UI shows)
        # Centered at offset, spanning total_time
        t_display_start = self._timebase.offset - total_time / 2
        t_display_end = self._timebase.offset + total_time / 2
        t_display = np.linspace(t_display_start, t_display_end, self._buffer_size)

        # Determine the reference time for signal generation
        if self._trigger.enabled:
            # Search for trigger in recent signal
            search_start = self._scope_time - total_time * 2
            search_end = self._scope_time

            trigger_time = self._find_trigger(search_start, search_end)

            if trigger_time is not None:
                self._last_trigger_time = trigger_time
                self._triggered = True
                # Reference time: trigger occurs at t=0 in signal coordinates
                reference_time = trigger_time
            elif self._trigger.mode == TriggerMode.AUTO:
                # Auto mode - use current scope time as reference
                reference_time = self._scope_time
            else:
                # Normal/Single mode - use last trigger time
                if self._triggered:
                    reference_time = self._last_trigger_time
                else:
                    reference_time = self._scope_time
        else:
            # No trigger - free running
            # Reference time advances with scope time, so signal appears to move
            reference_time = self._scope_time

        # Calculate absolute times for sampling
        # t_display represents where on screen each point appears
        # t_absolute is the actual signal time to sample
        # When t_display=0, we sample at reference_time
        t_absolute = reference_time + t_display

        # Sample the signal at these absolute times
        voltage = self._signal_value(channel, t_absolute)

        return WaveformData(
            channel=channel,
            time=t_display,
            voltage=voltage,
            sample_rate=self._sample_rate,
            num_points=self._buffer_size,
        )
