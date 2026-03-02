"""Device abstraction - a physical device containing one or more instruments."""

import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any

from pydantic import BaseModel

from hakei.instruments.registry import DeviceInstrumentDefinition

log = logging.getLogger(__name__)


class DeviceConnectionState(Enum):
    """Connection state for a device."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()


class DeviceInfo(BaseModel):
    """Information about a device."""

    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    firmware_version: str = ""
    description: str = ""


class Device(ABC):
    """
    Abstract base class for a physical device.

    A device represents a single piece of hardware that may contain
    multiple instruments (e.g., oscilloscope, waveform generator, etc.).
    """

    def __init__(self, resource_address: str):
        self.resource_address = resource_address
        self._connection_state = DeviceConnectionState.DISCONNECTED
        self._info = DeviceInfo()
        self._available_instruments: list[DeviceInstrumentDefinition] = []
        self._active_instruments: dict[str, Any] = {}

    @property
    def connection_state(self) -> DeviceConnectionState:
        """Get the current connection state."""
        return self._connection_state

    @property
    def is_connected(self) -> bool:
        """Check if the device is connected."""
        return self._connection_state == DeviceConnectionState.CONNECTED

    @property
    def info(self) -> DeviceInfo:
        """Get device information."""
        return self._info

    @property
    def available_instruments(self) -> list[DeviceInstrumentDefinition]:
        """Get list of instruments available on this device."""
        return self._available_instruments

    @property
    def active_instruments(self) -> dict[str, Any]:
        """Get dictionary of currently active instrument instances."""
        return self._active_instruments

    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the device.

        Returns:
            True if connection successful, False otherwise.
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the device."""
        ...

    def get_instrument(self, instrument_id: str) -> Any | None:
        """
        Get an active instrument instance by ID.

        Args:
            instrument_id: The instrument identifier.

        Returns:
            The instrument instance, or None if not active.
        """
        return self._active_instruments.get(instrument_id)

    def activate_instrument(self, instrument_id: str) -> Any | None:
        """
        Activate an instrument on this device.

        Args:
            instrument_id: The instrument identifier.

        Returns:
            The instrument instance, or None if activation failed.
        """
        if not self.is_connected:
            log.error("Cannot activate instrument: device not connected")
            return None

        if instrument_id in self._active_instruments:
            return self._active_instruments[instrument_id]

        # Find the instrument definition
        inst_def = None
        for definition in self._available_instruments:
            if definition.id == instrument_id:
                inst_def = definition
                break

        if inst_def is None:
            log.error("Unknown instrument ID: %s", instrument_id)
            return None

        # Create the instrument instance
        instrument = self._create_instrument(inst_def)
        if instrument:
            self._active_instruments[instrument_id] = instrument
            log.info("Activated instrument: %s", instrument_id)

        return instrument

    def deactivate_instrument(self, instrument_id: str) -> None:
        """
        Deactivate an instrument on this device.

        Args:
            instrument_id: The instrument identifier.
        """
        if instrument_id in self._active_instruments:
            instrument = self._active_instruments.pop(instrument_id)
            self._cleanup_instrument(instrument)
            log.info("Deactivated instrument: %s", instrument_id)

    @abstractmethod
    def _create_instrument(self, inst_def: DeviceInstrumentDefinition) -> Any | None:
        """
        Create an instrument instance.

        Args:
            inst_def: The instrument definition from the registry.

        Returns:
            The instrument instance, or None if creation failed.
        """
        ...

    def _cleanup_instrument(self, instrument: Any) -> None:
        """
        Clean up an instrument instance.

        Args:
            instrument: The instrument to clean up.
        """
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
