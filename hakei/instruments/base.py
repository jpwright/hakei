"""Base class for all instruments."""

import importlib
import logging
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any

from pydantic import BaseModel

log = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Instrument connection state."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()


class InstrumentInfo(BaseModel):
    """Information about an instrument."""

    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    firmware_version: str = ""


def _import_class(class_path: str) -> type | None:
    """Import a class from a dotted path string."""
    try:
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError, ValueError) as e:
        log.warning("Failed to import %s: %s", class_path, e)
        return None


class Instrument(ABC):
    """Abstract base class for all instruments."""

    _panel_class_path: str | None = None
    _config_class_path: str | None = None
    default_channels: int = 1

    _panel_class_cache: type[Any] | None = None
    _config_class_cache: type[BaseModel] | None = None

    @classmethod
    def get_panel_class(cls) -> type[Any] | None:
        """Get the panel class, importing lazily if needed."""
        if cls._panel_class_cache is None and cls._panel_class_path:
            cls._panel_class_cache = _import_class(cls._panel_class_path)
        return cls._panel_class_cache

    @classmethod
    def get_config_class(cls) -> type[BaseModel] | None:
        """Get the config class, importing lazily if needed."""
        if cls._config_class_cache is None and cls._config_class_path:
            cls._config_class_cache = _import_class(cls._config_class_path)
        return cls._config_class_cache

    def __init__(self, resource_address: str, device: Any = None):
        self.resource_address = resource_address
        self.device = device
        self._state = ConnectionState.DISCONNECTED
        self._info = InstrumentInfo()
        self._error_message: str = ""

    @property
    def state(self) -> ConnectionState:
        """Get the current connection state.

        If instrument is part of a device, returns state based on device connection.
        """
        if self.device is not None:
            # Map device connection state to instrument connection state
            from hakei.instruments.device import DeviceConnectionState
            device_state = self.device.connection_state
            if device_state == DeviceConnectionState.CONNECTED:
                return ConnectionState.CONNECTED
            elif device_state == DeviceConnectionState.CONNECTING:
                return ConnectionState.CONNECTING
            elif device_state == DeviceConnectionState.ERROR:
                return ConnectionState.ERROR
            else:
                return ConnectionState.DISCONNECTED
        return self._state

    @property
    def info(self) -> InstrumentInfo:
        """Get instrument information."""
        return self._info

    @property
    def error_message(self) -> str:
        """Get the last error message."""
        return self._error_message

    @property
    def is_connected(self) -> bool:
        """Check if the instrument is connected."""
        return self.state == ConnectionState.CONNECTED

    def connect(self) -> bool:
        """Connect to the instrument.

        For standalone instruments, override this method.
        For device-based instruments, connection is handled by the device.

        Returns:
            True if connection was successful, False otherwise.
        """
        if self.device is not None:
            # Connection handled by device
            return self.device.is_connected
        # Default for standalone: just set state
        self._state = ConnectionState.CONNECTED
        return True

    def disconnect(self) -> None:
        """Disconnect from the instrument.

        For standalone instruments, override this method.
        For device-based instruments, disconnection is handled by the device.
        """
        if self.device is not None:
            # Disconnection handled by device
            return
        self._state = ConnectionState.DISCONNECTED

    @abstractmethod
    def reset(self) -> None:
        """Reset the instrument to default settings."""
        ...

    def identify(self) -> InstrumentInfo:
        """
        Query instrument identification.

        Returns:
            InstrumentInfo with manufacturer, model, serial, and firmware.
        """
        return self._info

    def _set_error(self, message: str) -> None:
        """Set error state with message."""
        self._state = ConnectionState.ERROR
        self._error_message = message
        log.error("Instrument error (%s): %s", self.resource_address, message)

    def _clear_error(self) -> None:
        """Clear error state."""
        self._error_message = ""
        if self._state == ConnectionState.ERROR:
            self._state = ConnectionState.DISCONNECTED
