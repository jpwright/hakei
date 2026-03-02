"""Dummy waveform generator implementation for testing."""

import logging
import time

import numpy as np
from numpy.typing import NDArray

from hakei.instruments.base import ConnectionState, InstrumentInfo
from hakei.instruments.waveform_generator import (
    ChannelCapabilities,
    ChannelConfig,
    ModulationConfig,
    ModulationType,
    WaveformGenerator,
    WaveformType,
)

log = logging.getLogger(__name__)


class DummyWaveformGenerator(WaveformGenerator):
    """Dummy waveform generator for testing."""

    def __init__(self, resource_address: str = "DUMMY::AWG::1", num_channels: int = 1, device=None):
        super().__init__(resource_address, num_channels, device=device)
        self._info = InstrumentInfo(
            manufacturer="Hakei",
            model="DummyAWG-1CH",
            serial_number="DUMMY003",
            firmware_version="1.0.0",
        )

        # Set capabilities for each channel
        for i in range(num_channels):
            self._channel_capabilities[i] = ChannelCapabilities(
                max_frequency=25e6,
                min_frequency=1e-6,
                max_amplitude=10.0,
                min_amplitude=0.001,
                max_offset=5.0,
                min_offset=-5.0,
                arbitrary_waveform_points=16384,
            )

        # Storage for arbitrary waveforms
        self._arbitrary_waveforms: dict[str, NDArray[np.float64]] = {}

    def connect(self) -> bool:
        """Connect to the dummy waveform generator."""
        log.info("Connecting to dummy waveform generator: %s", self.resource_address)
        self._state = ConnectionState.CONNECTING
        time.sleep(0.5)  # Simulate connection delay
        self._state = ConnectionState.CONNECTED
        log.info("Dummy waveform generator connected")
        return True

    def disconnect(self) -> None:
        """Disconnect from the dummy waveform generator."""
        log.info("Disconnecting from dummy waveform generator")
        # Turn off all outputs on disconnect
        for config in self._channel_configs:
            config.output_enabled = False
        self._state = ConnectionState.DISCONNECTED

    def reset(self) -> None:
        """Reset the dummy waveform generator."""
        log.info("Resetting dummy waveform generator")
        for i in range(self.num_channels):
            self._channel_configs[i] = ChannelConfig(
                output_enabled=False,
                waveform=WaveformType.SINE,
                frequency=1000.0,
                amplitude=1.0,
                offset=0.0,
                phase=0.0,
                duty_cycle=50.0,
                symmetry=50.0,
            )
            self._modulation_configs[i] = ModulationConfig(
                enabled=False,
                mod_type=ModulationType.NONE,
            )

    def _hw_set_output_enabled(self, channel: int, enabled: bool) -> None:
        """Hardware: Enable or disable output (dummy - just logs)."""
        log.debug("Channel %d output: %s", channel, "ON" if enabled else "OFF")

    def _hw_set_waveform(self, channel: int, waveform: WaveformType) -> None:
        """Hardware: Set waveform type (dummy - just logs)."""
        log.debug("Channel %d waveform: %s", channel, waveform.name)

    def _hw_set_frequency(self, channel: int, frequency: float) -> None:
        """Hardware: Set frequency (dummy - validates and logs)."""
        caps = self._channel_capabilities[channel - 1]
        clamped = max(caps.min_frequency, min(caps.max_frequency, frequency))
        if clamped != frequency:
            self._channel_configs[channel - 1].frequency = clamped
        log.debug("Channel %d frequency: %.6f Hz", channel, clamped)

    def _hw_set_amplitude(self, channel: int, amplitude: float) -> None:
        """Hardware: Set amplitude (dummy - validates and logs)."""
        caps = self._channel_capabilities[channel - 1]
        clamped = max(caps.min_amplitude, min(caps.max_amplitude, amplitude))
        if clamped != amplitude:
            self._channel_configs[channel - 1].amplitude = clamped
        log.debug("Channel %d amplitude: %.3f Vpp", channel, clamped)

    def _hw_set_offset(self, channel: int, offset: float) -> None:
        """Hardware: Set DC offset (dummy - validates and logs)."""
        caps = self._channel_capabilities[channel - 1]
        clamped = max(caps.min_offset, min(caps.max_offset, offset))
        if clamped != offset:
            self._channel_configs[channel - 1].offset = clamped
        log.debug("Channel %d offset: %.3f V", channel, clamped)

    def _hw_set_phase(self, channel: int, phase: float) -> None:
        """Hardware: Set phase (dummy - normalizes and logs)."""
        normalized = phase % 360.0
        if normalized != phase:
            self._channel_configs[channel - 1].phase = normalized
        log.debug("Channel %d phase: %.1f deg", channel, normalized)

    def _hw_set_duty_cycle(self, channel: int, duty_cycle: float) -> None:
        """Hardware: Set duty cycle (dummy - validates and logs)."""
        clamped = max(0.1, min(99.9, duty_cycle))
        if clamped != duty_cycle:
            self._channel_configs[channel - 1].duty_cycle = clamped
        log.debug("Channel %d duty cycle: %.1f%%", channel, clamped)

    def _hw_set_modulation_enabled(self, channel: int, enabled: bool) -> None:
        """Hardware: Enable or disable modulation (dummy - just logs)."""
        log.debug("Channel %d modulation: %s", channel, "ON" if enabled else "OFF")

    def _hw_set_modulation_type(self, channel: int, mod_type: ModulationType) -> None:
        """Hardware: Set modulation type (dummy - just logs)."""
        log.debug("Channel %d modulation type: %s", channel, mod_type.name)

    def _hw_set_modulation_frequency(self, channel: int, frequency: float) -> None:
        """Hardware: Set modulation frequency (dummy - just logs)."""
        log.debug("Channel %d modulation frequency: %.1f Hz", channel, frequency)

    def _hw_set_modulation_depth(self, channel: int, depth: float) -> None:
        """Hardware: Set AM modulation depth (dummy - validates and logs)."""
        clamped = max(0.0, min(100.0, depth))
        if clamped != depth:
            self._modulation_configs[channel - 1].mod_depth = clamped
        log.debug("Channel %d modulation depth: %.1f%%", channel, clamped)

    def load_arbitrary_waveform(
        self, channel: int, data: NDArray[np.float64], name: str = "ARB"
    ) -> None:
        """Load arbitrary waveform data."""
        caps = self._channel_capabilities[channel - 1]

        # Truncate or pad to max points
        if len(data) > caps.arbitrary_waveform_points:
            data = data[: caps.arbitrary_waveform_points]

        # Normalize to -1 to 1
        data = np.clip(data, -1.0, 1.0)

        self._arbitrary_waveforms[f"CH{channel}_{name}"] = data
        log.debug(
            "Channel %d loaded arbitrary waveform '%s' with %d points",
            channel,
            name,
            len(data),
        )

    def sync_channels(self, enable: bool = True) -> None:
        """Synchronize channel phases."""
        if enable:
            for config in self._channel_configs:
                config.phase = 0.0
        log.debug("Channel sync: %s", "ON" if enable else "OFF")
