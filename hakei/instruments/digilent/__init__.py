"""Digilent Waveforms device support."""

from hakei.instruments.digilent.device import AnalogDiscovery2, DigilentDevice
from hakei.instruments.digilent.dwf import get_dwf, is_dwf_available
from hakei.instruments.digilent.oscilloscope import DigilentOscilloscope
from hakei.instruments.digilent.power_supply import DigilentPowerSupply
from hakei.instruments.digilent.scanner import scan_digilent
from hakei.instruments.digilent.waveform_generator import DigilentWaveformGenerator

__all__ = [
    "AnalogDiscovery2",
    "DigilentDevice",
    "DigilentOscilloscope",
    "DigilentPowerSupply",
    "DigilentWaveformGenerator",
    "get_dwf",
    "is_dwf_available",
    "scan_digilent",
]
