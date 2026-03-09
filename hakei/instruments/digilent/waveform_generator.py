"""Digilent waveform generator implementation."""

import logging
from ctypes import c_double, c_int

import numpy as np
from numpy.typing import NDArray

from hakei.instruments.digilent.device import DigilentDevice
from hakei.instruments.waveform_generator import (
    WaveformGenerator,
    WaveformType,
)

log = logging.getLogger(__name__)

funcDC = c_int(0)
funcSine = c_int(1)
funcSquare = c_int(2)
funcTriangle = c_int(3)
funcRampUp = c_int(4)
funcNoise = c_int(6)
funcPulse = c_int(7)
funcCustom = c_int(30)


def _waveform_to_dwf(waveform: WaveformType) -> c_int:
    """Convert WaveformType to DWF function constant."""
    mapping = {
        WaveformType.SINE: funcSine,
        WaveformType.SQUARE: funcSquare,
        WaveformType.TRIANGLE: funcTriangle,
        WaveformType.RAMP: funcRampUp,
        WaveformType.PULSE: funcPulse,
        WaveformType.NOISE: funcNoise,
        WaveformType.DC: funcDC,
        WaveformType.ARBITRARY: funcCustom,
    }
    return mapping.get(waveform, funcSine)


class DigilentWaveformGenerator(WaveformGenerator):
    """Waveform generator implementation for Digilent devices."""

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
        """Initialize the waveform generator (connection handled by device)."""
        log.info("Digilent waveform generator ready")
        return True

    def disconnect(self) -> None:
        """Cleanup (disconnection handled by device)."""
        pass

    def reset(self) -> None:
        """Reset the waveform generator to default settings."""
        for ch in range(1, self.num_channels + 1):
            self.set_output_enabled(ch, False)
            self.set_frequency(ch, 1000.0)
            self.set_amplitude(ch, 1.0)
            self.set_offset(ch, 0.0)

    def _hw_set_output_enabled(self, channel: int, enabled: bool) -> None:
        """Hardware: Enable or disable output on a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogOutNodeEnableSet(self.hdwf, c_int(ch_idx), c_int(0), c_int(1 if enabled else 0))
            dwf.FDwfAnalogOutConfigure(self.hdwf, c_int(ch_idx), c_int(1 if enabled else 0))
        log.info("Channel %d output %s", channel, "enabled" if enabled else "disabled")

    def _hw_set_waveform(self, channel: int, waveform: WaveformType) -> None:
        """Hardware: Set the waveform type for a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogOutNodeFunctionSet(self.hdwf, c_int(ch_idx), c_int(0), _waveform_to_dwf(waveform))

    def _hw_set_frequency(self, channel: int, frequency: float) -> None:
        """Hardware: Set the frequency (Hz) for a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogOutNodeFrequencySet(self.hdwf, c_int(ch_idx), c_int(0), c_double(frequency))

    def _hw_set_amplitude(self, channel: int, amplitude: float) -> None:
        """Hardware: Set the amplitude (Vpp) for a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogOutNodeAmplitudeSet(self.hdwf, c_int(ch_idx), c_int(0), c_double(amplitude))

    def _hw_set_offset(self, channel: int, offset: float) -> None:
        """Hardware: Set the DC offset (V) for a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogOutNodeOffsetSet(self.hdwf, c_int(ch_idx), c_int(0), c_double(offset))

    def _hw_set_phase(self, channel: int, phase: float) -> None:
        """Hardware: Set the phase (degrees) for a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogOutNodePhaseSet(self.hdwf, c_int(ch_idx), c_int(0), c_double(phase))

    def _hw_set_duty_cycle(self, channel: int, duty_cycle: float) -> None:
        """Hardware: Set the duty cycle (%) for square/pulse waveforms."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogOutNodeSymmetrySet(self.hdwf, c_int(ch_idx), c_int(0), c_double(duty_cycle))

    def load_arbitrary_waveform(
        self, channel: int, data: NDArray[np.float64], name: str = "ARB"
    ) -> None:
        """Load arbitrary waveform data to a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if not dwf:
            return

        c_data = (c_double * len(data))(*data)
        dwf.FDwfAnalogOutNodeDataSet(self.hdwf, c_int(ch_idx), c_int(0), c_data, c_int(len(data)))
        self.set_waveform(channel, WaveformType.ARBITRARY)
        log.info("Loaded arbitrary waveform '%s' to channel %d (%d points)", name, channel, len(data))
