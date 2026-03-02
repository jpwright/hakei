"""Instrument abstraction layer."""

from hakei.instruments.base import (
    ConnectionState,
    Instrument,
    InstrumentInfo,
)
from hakei.instruments.device import (
    Device,
    DeviceConnectionState,
    DeviceInfo,
)
from hakei.instruments.dummy import (
    DummyOscilloscope,
    DummyPowerSupply,
    DummyWaveformGenerator,
)
from hakei.instruments.oscilloscope import (
    AcquisitionState,
    Coupling,
    DisplayMode,
    Oscilloscope,
    TimebaseConfig,
    TriggerConfig,
    TriggerEdge,
    TriggerMode,
    WaveformData,
)
from hakei.instruments.oscilloscope import (
    ChannelConfig as OscilloscopeChannelConfig,
)
from hakei.instruments.power_supply import (
    ChannelCapabilities as PowerSupplyChannelCapabilities,
)
from hakei.instruments.power_supply import (
    ChannelState as PowerSupplyChannelState,
)
from hakei.instruments.power_supply import (
    OutputMode,
    PowerSupply,
    ProtectionState,
)
from hakei.instruments.registry import (
    DeviceDefinition,
    DeviceInstrumentDefinition,
    DeviceRegistry,
    get_registry,
)
from hakei.instruments.scanner import (
    DiscoveredInstrument,
    InstrumentScanner,
    InterfaceType,
    get_scanner,
)
from hakei.instruments.waveform_generator import (
    ChannelCapabilities as WaveformGeneratorChannelCapabilities,
)
from hakei.instruments.waveform_generator import (
    ChannelConfig as WaveformGeneratorChannelConfig,
)
from hakei.instruments.waveform_generator import (
    ModulationConfig,
    ModulationType,
    OutputLoad,
    WaveformGenerator,
    WaveformType,
)

__all__ = [
    # Base
    "ConnectionState",
    "Instrument",
    "InstrumentInfo",
    # Device
    "Device",
    "DeviceConnectionState",
    "DeviceInfo",
    # Registry
    "DeviceDefinition",
    "DeviceInstrumentDefinition",
    "DeviceRegistry",
    "get_registry",
    # Scanner
    "DiscoveredInstrument",
    "InstrumentScanner",
    "InterfaceType",
    "get_scanner",
    # Dummy Instruments
    "DummyOscilloscope",
    "DummyPowerSupply",
    "DummyWaveformGenerator",
    # Oscilloscope
    "AcquisitionState",
    "Coupling",
    "DisplayMode",
    "Oscilloscope",
    "OscilloscopeChannelConfig",
    "TimebaseConfig",
    "TriggerConfig",
    "TriggerEdge",
    "TriggerMode",
    "WaveformData",
    # Power Supply
    "OutputMode",
    "PowerSupply",
    "PowerSupplyChannelCapabilities",
    "PowerSupplyChannelState",
    "ProtectionState",
    # Waveform Generator
    "ModulationConfig",
    "ModulationType",
    "OutputLoad",
    "WaveformGenerator",
    "WaveformGeneratorChannelCapabilities",
    "WaveformGeneratorChannelConfig",
    "WaveformType",
]
