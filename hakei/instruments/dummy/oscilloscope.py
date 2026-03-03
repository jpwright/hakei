"""Dummy oscilloscope implementation emulating a 100 MHz scope."""

import logging
import threading
import time
from collections import deque

import numpy as np

from hakei.instruments.base import ConnectionState, InstrumentInfo
from hakei.instruments.oscilloscope import (
    AcquisitionState,
    Coupling,
    DisplayMode,
    Oscilloscope,
    TriggerEdge,
    TriggerMode,
    WaveformData,
)

log = logging.getLogger(__name__)

class DummyOscilloscope(Oscilloscope):
    """Dummy oscilloscope backed by a background generation thread."""

    num_channels: int = 4
    chunk_period: float = 1e-3

    def __init__(self, resource_address: str = "DUMMY::OSC::1", device=None):
        super().__init__(resource_address, device=device)
        self._buffer_size = int(1e9)
        self._sample_rate = 10e3
        self._info = InstrumentInfo(
            manufacturer="Hakei",
            model="DummyScope-100MHz",
            serial_number="DUMMY001",
            firmware_version="1.0.0",
        )
        self._acquisition_stop = threading.Event()
        self._acquisition_thread: threading.Thread | None = None
        self._buf_lock = threading.Lock()
        self._buf_deques: list[deque[float]] = [
            deque(maxlen=self._buffer_size)
            for _ in range(self.num_channels)
        ]
        self._time = 0.0

        self._normal_snapshot: WaveformData | None = None
        self._normal_next_k: int = 0

    def _acquisition_loop(self) -> None:
        nch = self.num_channels
        next_wake = time.monotonic() + self.chunk_period
        while not self._acquisition_stop.is_set():
            sr = self._sample_rate
            chunk_samples = max(
                1, int(sr * self.chunk_period)
            )
            dt = 1.0 / sr
            t_arr = self._time + np.arange(
                chunk_samples, dtype=np.float64
            ) * dt
            vol = np.zeros(
                (nch, chunk_samples), dtype=np.float64
            )
            for ch in range(nch):
                if self._channel_configs[ch].enabled:
                    vol[ch] = self._signal_value(
                        ch + 1, t_arr
                    )
            with self._buf_lock:
                for ch in range(nch):
                    self._buf_deques[ch].extend(
                        vol[ch].tolist()
                    )
            self._time = t_arr[-1] + dt
            remaining = next_wake - time.monotonic()
            if remaining > 0:
                self._acquisition_stop.wait(
                    timeout=remaining
                )
            next_wake += self.chunk_period

    def connect(self) -> bool:
        log.info("Connecting to dummy oscilloscope: %s", self.resource_address)
        self._state = ConnectionState.CONNECTING
        time.sleep(0.5)
        self._state = ConnectionState.CONNECTED
        self._acquisition_state = AcquisitionState.STOPPED
        self._channel_configs[0].enabled = True
        self._channel_configs[0].scale = 1.0
        self.set_timebase_length(100e-3)
        self._timebase.offset = 0.0
        self._acquisition_stop.clear()
        self._acquisition_thread = threading.Thread(target=self._acquisition_loop, daemon=True)
        self._acquisition_thread.start()
        log.info("Dummy oscilloscope connected")
        return True

    def disconnect(self) -> None:
        log.info("Disconnecting from dummy oscilloscope")
        self._acquisition_stop.set()
        if self._acquisition_thread is not None:
            self._acquisition_thread.join(timeout=2.0)
            self._acquisition_thread = None
        self._state = ConnectionState.DISCONNECTED
        self._acquisition_state = AcquisitionState.STOPPED

    def reset(self) -> None:
        log.info("Resetting dummy oscilloscope")
        for config in self._channel_configs:
            config.enabled = False
            config.scale = 1.0
            config.offset = 0.0
            config.coupling = Coupling.DC
        self._channel_configs[0].enabled = True
        self.set_timebase_length(100e-3)
        self._timebase.offset = 0.0
        self._trigger.source = 1
        self._trigger.mode = TriggerMode.AUTO
        self._trigger.edge = TriggerEdge.RISING
        self._trigger.level = 0.0
        self._trigger.enabled = False
        self._acquisition_state = AcquisitionState.STOPPED

    def run(self) -> None:
        self._acquisition_state = AcquisitionState.RUNNING
        self._normal_snapshot = None
        with self._buf_lock:
            N = len(self._buf_deques[0]) if self._buf_deques else 0
        self._normal_next_k = N
        log.debug("Dummy oscilloscope: run")

    def _apply_timebase_settings(self) -> None:
        span = self._timebase.span
        self._buffer_size = 10_000
        self._sample_rate = self._buffer_size / span
        self._normal_snapshot = None
        with self._buf_lock:
            for d in self._buf_deques:
                d.clear()
        self._normal_next_k = 0
        self._time = 0.0

    def stop(self) -> None:
        self._acquisition_state = AcquisitionState.STOPPED
        with self._buf_lock:
            for d in self._buf_deques:
                d.clear()
        self._normal_snapshot = None
        self._normal_next_k = 0
        self._time = 0.0
        log.debug("Dummy oscilloscope: stop")

    def single(self) -> None:
        self._acquisition_state = AcquisitionState.SINGLE
        log.debug("Dummy oscilloscope: single")

    def force_trigger(self) -> None:
        self._acquisition_state = AcquisitionState.RUNNING
        log.debug("Dummy oscilloscope: force trigger")

    def auto_scale(self) -> None:
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

    # ECG component parameters: (centre as fraction of RR interval,
    #                              half-width in seconds, amplitude in V)
    _ECG_WAVES: list[tuple[float, float, float]] = [
        (0.12, 0.035, 0.15),   # P
        (0.21, 0.008, -0.10),  # Q
        (0.23, 0.010, 1.20),   # R
        (0.25, 0.008, -0.25),  # S
        (0.40, 0.050, 0.25),   # T
    ]
    _ECG_BPM: float = 72.0

    def _ecg(self, t: np.ndarray) -> np.ndarray:
        """Synthetic ECG (QRS complex) at ~72 BPM."""
        rr = 60.0 / self._ECG_BPM
        phase = np.mod(t, rr)
        sig = np.zeros_like(t)
        for centre_frac, width, amp in self._ECG_WAVES:
            centre = centre_frac * rr
            sig += amp * np.exp(
                -0.5 * ((phase - centre) / width) ** 2
            )
        sig += 0.05 * np.random.randn(len(t))
        return sig

    def _signal_value(self, channel: int, t: np.ndarray) -> np.ndarray:
        """Signal at time t (continuous analog)."""
        if channel == 1:
            return 3.0 * np.sin(2 * np.pi * 50 * t)
        if channel == 2:
            return 2.0 * np.sign(np.sin(2 * np.pi * 25 * t))
        if channel == 3:
            phase = (t * 10) % 1
            return 2.5 * (4 * np.abs(phase - 0.5) - 1)
        if channel == 4:
            return self._ecg(t)
        return 0.5 * np.random.randn(len(t))

    def _read_buffer(self) -> tuple[int, list[list[float]]]:
        """Snapshot the deque lengths and contents under lock.

        Returns (N, channel_lists) where N is the number of
        samples per channel and channel_lists[c] is a plain list
        for channel c.
        """
        with self._buf_lock:
            N = (
                len(self._buf_deques[0])
                if self._buf_deques
                else 0
            )
            if N == 0:
                return 0, []
            channel_lists = [
                list(self._buf_deques[c])
                for c in range(self.num_channels)
            ]
        return N, channel_lists

    def _slice(
        self,
        channel_lists: list[list[float]],
        k_start: int,
        k_end: int,
    ) -> np.ndarray:
        """Extract a slice from the buffer.

        Returns voltage array of shape (num_channels, count).
        """
        return np.array(
            [
                channel_lists[c][k_start : k_end + 1]
                for c in range(self.num_channels)
            ],
            dtype=np.float64,
        )

    def get_waveform(self) -> WaveformData:
        """Return voltage data whose shape depends on display mode."""
        nch = self.num_channels
        screen_samples = self._buffer_size
        empty = WaveformData(
            voltage=np.zeros((nch, 0), dtype=np.float64),
            sample_rate=self._sample_rate,
            num_points=0,
            num_channels=nch,
        )

        N, ch_lists = self._read_buffer()
        if N == 0:
            return empty

        mode = self._display_mode

        if mode == DisplayMode.NORMAL:
            return self._get_waveform_normal(
                N, ch_lists, screen_samples, empty,
            )
        if mode == DisplayMode.ROLL:
            return self._get_waveform_roll(
                N, ch_lists, screen_samples, empty,
            )
        # SCREEN
        return self._get_waveform_screen(
            N, ch_lists, screen_samples, empty,
        )

    # ----------------------------------------------------------
    # NORMAL: return empty until a full screen is ready, then
    # keep returning the same snapshot until the *next* full
    # screen of data has been generated.  When a trigger is
    # enabled, the screen is aligned to the trigger event.
    # ----------------------------------------------------------
    def _get_waveform_normal(
        self,
        N: int,
        ch_lists: list[list[float]],
        screen_samples: int,
        empty: WaveformData,
    ) -> WaveformData:
        k_start = self._normal_next_k

        if self._trigger.enabled:
            trig_k = self._find_trigger(
                ch_lists, k_start, N,
            )
            if trig_k is None:
                if self._normal_snapshot is not None:
                    return self._normal_snapshot
                return empty
            offset = int(self._trigger.position * self._sample_rate)
            k_start = max(0, trig_k - offset)

        k_end = k_start + screen_samples - 1
        if k_end >= N:
            if self._normal_snapshot is not None:
                return self._normal_snapshot
            return empty
        vol = self._slice(ch_lists, k_start, k_end)
        self._normal_snapshot = WaveformData(
            voltage=vol,
            sample_rate=self._sample_rate,
            num_points=vol.shape[1],
            num_channels=self.num_channels,
        )
        holdoff_samples = int(
            self._trigger.holdoff * self._sample_rate
        )
        self._normal_next_k = k_end + 1 + holdoff_samples
        return self._normal_snapshot

    def _find_trigger(
        self,
        ch_lists: list[list[float]],
        k_start: int,
        N: int,
    ) -> int | None:
        """Find the first trigger crossing at or after k_start.

        Returns the buffer index of the crossing, or None.
        """
        ch_idx = self._trigger.source - 1
        if ch_idx < 0 or ch_idx >= self.num_channels:
            return None
        level = self._trigger.level
        edge = self._trigger.edge
        data = ch_lists[ch_idx]
        for k in range(max(1, k_start), N):
            prev = data[k - 1]
            cur = data[k]
            if edge == TriggerEdge.RISING:
                if prev < level <= cur:
                    return k
            elif edge == TriggerEdge.FALLING:
                if prev > level >= cur:
                    return k
            else:  # EITHER
                if (prev < level <= cur) or (
                    prev > level >= cur
                ):
                    return k
        return None

    # ----------------------------------------------------------
    # ROLL: return partial data from _normal_next_k up to the
    # latest sample (or a full screen, whichever is smaller).
    # ----------------------------------------------------------
    def _get_waveform_roll(
        self,
        N: int,
        ch_lists: list[list[float]],
        screen_samples: int,
        empty: WaveformData,
    ) -> WaveformData:
        k_start = self._normal_next_k
        available = N - k_start
        if available <= 0:
            return empty
        k_end = min(
            k_start + screen_samples - 1,
            N - 1,
        )
        vol = self._slice(ch_lists, k_start, k_end)
        # Once a full screen is filled, advance the cursor
        if k_end - k_start + 1 >= screen_samples:
            self._normal_next_k = k_end + 1
        return WaveformData(
            voltage=vol,
            sample_rate=self._sample_rate,
            num_points=vol.shape[1],
            num_channels=self.num_channels,
        )

    # ----------------------------------------------------------
    # SCREEN: always return the most recent slice (up to a full
    # screen worth).
    # ----------------------------------------------------------
    def _get_waveform_screen(
        self,
        N: int,
        ch_lists: list[list[float]],
        screen_samples: int,
        empty: WaveformData,
    ) -> WaveformData:
        count = min(screen_samples, N)
        k_start = N - count
        k_end = N - 1
        vol = self._slice(ch_lists, k_start, k_end)
        return WaveformData(
            voltage=vol,
            sample_rate=self._sample_rate,
            num_points=vol.shape[1],
            num_channels=self.num_channels,
        )
