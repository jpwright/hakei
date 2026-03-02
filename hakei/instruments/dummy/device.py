"""Dummy device implementation for testing."""

import logging
import time
from typing import Any

from hakei.instruments.device import Device, DeviceConnectionState, DeviceInfo
from hakei.instruments.registry import DeviceInstrumentDefinition

log = logging.getLogger(__name__)


class DummyDevice(Device):
    """A dummy device for testing that contains multiple instruments."""

    def __init__(self, resource_address: str = "DUMMY::DEVICE::1", **kwargs):
        super().__init__(resource_address)
        self._info = DeviceInfo(
            manufacturer="Hakei",
            model="DummyDevice",
            serial_number="DUMMY001",
            firmware_version="1.0.0",
            description="Dummy multi-function device for testing",
        )

    def connect(self) -> bool:
        """Connect to the dummy device."""
        log.info("Connecting to dummy device: %s", self.resource_address)
        self._connection_state = DeviceConnectionState.CONNECTING

        try:
            time.sleep(0.5)  # Simulate connection delay
            self._populate_available_instruments()
            self._connection_state = DeviceConnectionState.CONNECTED
            log.info("Dummy device connected")
            return True
        except Exception as e:
            log.error("Failed to connect to dummy device: %s", e)
            self._connection_state = DeviceConnectionState.ERROR
            return False

    def disconnect(self) -> None:
        """Disconnect from the dummy device."""
        log.info("Disconnecting dummy device: %s", self.resource_address)

        for instrument_id in list(self._active_instruments.keys()):
            self.deactivate_instrument(instrument_id)

        self._available_instruments.clear()
        self._connection_state = DeviceConnectionState.DISCONNECTED
        log.info("Dummy device disconnected")

    def _populate_available_instruments(self) -> None:
        """Populate instruments from the registry."""
        from hakei.instruments.registry import get_registry

        registry = get_registry()
        device_def = registry.lookup("Hakei", "DummyDevice")

        if device_def:
            self._available_instruments = list(device_def.instruments)
        else:
            log.warning("DummyDevice not found in registry")
            self._available_instruments = []

    def _create_instrument(self, inst_def: DeviceInstrumentDefinition) -> Any | None:
        """Create an instrument instance."""
        if inst_def.instrument_class is None:
            log.error("No instrument class for %s", inst_def.id)
            return None

        try:
            address = f"{self.resource_address}::{inst_def.id}"
            instrument = inst_def.instrument_class(
                address, device=self, **inst_def.instrument_kwargs
            )

            if hasattr(instrument, "connect"):
                instrument.connect()

            return instrument
        except Exception as e:
            log.error("Failed to create instrument %s: %s", inst_def.id, e)
            return None

    def _cleanup_instrument(self, instrument: Any) -> None:
        """Clean up an instrument instance."""
        if hasattr(instrument, "disconnect"):
            try:
                instrument.disconnect()
            except Exception as e:
                log.debug("Error disconnecting instrument: %s", e)
