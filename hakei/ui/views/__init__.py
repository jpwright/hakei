"""Device-specific view modules."""

from hakei.ui.views.base import InstrumentPanel
from hakei.ui.views.oscilloscope import OscilloscopePanel
from hakei.ui.views.power_supply import PowerSupplyChannel, PowerSupplyPanel
from hakei.ui.views.waveform_gen import WaveformGeneratorPanel

__all__ = [
    "InstrumentPanel",
    "OscilloscopePanel",
    "PowerSupplyChannel",
    "PowerSupplyPanel",
    "WaveformGeneratorPanel",
]
