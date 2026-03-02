"""Dummy instrument implementations for testing."""

from hakei.instruments.dummy.device import DummyDevice
from hakei.instruments.dummy.oscilloscope import DummyOscilloscope
from hakei.instruments.dummy.power_supply import DummyPowerSupply
from hakei.instruments.dummy.waveform_generator import DummyWaveformGenerator

__all__ = [
    "DummyDevice",
    "DummyOscilloscope",
    "DummyPowerSupply",
    "DummyWaveformGenerator",
]
