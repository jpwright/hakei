"""Base class for instrument scanner transports."""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any

from pydantic import BaseModel, Field


class InterfaceType(Enum):
    """Interface types for instrument connections."""

    VISA = auto()
    SERIAL = auto()
    USB = auto()
    ETHERNET = auto()
    DIGILENT = auto()
    DUMMY = auto()


class DiscoveredInstrument(BaseModel):
    """Information about a discovered instrument."""

    model_config = {"arbitrary_types_allowed": True}

    resource_address: str
    interface_type: InterfaceType
    instrument_class: Any = None
    panel_class: Any = None
    instrument_kwargs: dict[str, Any] = Field(default_factory=dict)
    panel_kwargs: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""

    # Device reference (if this instrument is part of a multi-instrument device)
    device_address: str | None = None
    device_class: Any = None
    device_kwargs: dict[str, Any] = Field(default_factory=dict)
    instrument_id: str | None = None  # ID within the device (e.g., "oscilloscope")


class InstrumentScannerTransport(ABC):
    """Abstract base class for instrument scanner transports."""

    @property
    @abstractmethod
    def interface_type(self) -> InterfaceType:
        """The interface type this transport handles."""
        ...

    @abstractmethod
    def scan(self) -> list[DiscoveredInstrument]:
        """
        Scan for instruments using this transport.

        Returns:
            List of discovered instruments.
        """
        ...

    def close(self) -> None:
        """Clean up any resources. Override if needed."""
        pass
