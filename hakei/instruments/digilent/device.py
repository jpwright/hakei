"""Digilent device implementation."""

import logging
from ctypes import byref, c_int, create_string_buffer
from typing import Any

from hakei.instruments.device import Device, DeviceConnectionState, DeviceInfo
from hakei.instruments.digilent.dwf import get_dwf
from hakei.instruments.registry import DeviceInstrumentDefinition

log = logging.getLogger(__name__)


class DigilentDevice(Device):
    """
    Base class for Digilent Waveforms devices.

    Handles connection management and provides access to the DWF handle.
    """

    def __init__(self, resource_address: str, device_index: int = 0, **kwargs):
        super().__init__(resource_address)
        self._device_index = device_index
        self._hdwf = c_int(0)

    @property
    def hdwf(self) -> c_int:
        """Get the DWF device handle."""
        return self._hdwf

    @property
    def device_index(self) -> int:
        """Get the device index."""
        return self._device_index

    def connect(self) -> bool:
        """Connect to the Digilent device."""
        log.info("Connecting to Digilent device: %s (index %d)",
                 self.resource_address, self._device_index)
        self._connection_state = DeviceConnectionState.CONNECTING

        dwf = get_dwf()
        if dwf is None:
            log.error("DWF SDK not available")
            self._connection_state = DeviceConnectionState.ERROR
            return False

        try:
            dwf.FDwfDeviceOpen(c_int(self._device_index), byref(self._hdwf))

            if self._hdwf.value == 0:
                log.error("Failed to open Digilent device")
                self._connection_state = DeviceConnectionState.ERROR
                return False

            self._read_device_info()
            self._populate_available_instruments()

            self._connection_state = DeviceConnectionState.CONNECTED
            log.info("Connected to Digilent device: %s", self._info.model)
            return True

        except Exception as e:
            log.error("Failed to connect to Digilent device: %s", e)
            self._connection_state = DeviceConnectionState.ERROR
            return False

    def disconnect(self) -> None:
        """Disconnect from the Digilent device."""
        log.info("Disconnecting from Digilent device: %s", self.resource_address)

        for instrument_id in list(self._active_instruments.keys()):
            self.deactivate_instrument(instrument_id)

        dwf = get_dwf()
        if dwf and self._hdwf.value != 0:
            try:
                dwf.FDwfDeviceClose(self._hdwf)
            except Exception as e:
                log.debug("Error closing device: %s", e)

        self._hdwf = c_int(0)
        self._available_instruments.clear()
        self._connection_state = DeviceConnectionState.DISCONNECTED
        log.info("Digilent device disconnected")

    def _read_device_info(self) -> None:
        """Read device information from the hardware."""
        dwf = get_dwf()
        if not dwf:
            return

        devicename = create_string_buffer(64)
        serialnum = create_string_buffer(16)

        dwf.FDwfEnumDeviceName(c_int(self._device_index), devicename)
        dwf.FDwfEnumSN(c_int(self._device_index), serialnum)

        self._info = DeviceInfo(
            manufacturer="Digilent",
            model=devicename.value.decode(),
            serial_number=serialnum.value.decode(),
            description=f"Digilent {devicename.value.decode()}",
        )

    def _populate_available_instruments(self) -> None:
        """Populate instruments from the registry based on device model."""
        from hakei.instruments.registry import get_registry

        registry = get_registry()
        device_def = registry.lookup("Digilent", self._info.model)

        if device_def:
            self._available_instruments = list(device_def.instruments)
        else:
            log.warning("Device %s not found in registry", self._info.model)
            self._available_instruments = []

    def _create_instrument(self, inst_def: DeviceInstrumentDefinition) -> Any | None:
        """Create an instrument instance."""
        if inst_def.instrument_class is None:
            log.error("No instrument class for %s", inst_def.id)
            return None

        try:
            address = f"{self.resource_address}::{inst_def.id}"
            instrument = inst_def.instrument_class(
                address,
                device=self,
                **inst_def.instrument_kwargs
            )
            # Initialize the instrument (configures acquisition parameters etc.)
            if hasattr(instrument, "connect"):
                instrument.connect()
            return instrument
        except Exception as e:
            log.error("Failed to create instrument %s: %s", inst_def.id, e)
            return None


class AnalogDiscovery2(DigilentDevice):
    """Digilent Analog Discovery 2 device."""
    pass
