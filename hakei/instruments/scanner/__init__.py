"""Instrument scanning and discovery."""

import logging

from hakei.instruments.scanner.base import (
    DiscoveredInstrument,
    InstrumentScannerTransport,
    InterfaceType,
)
from hakei.instruments.scanner.digilent import InstrumentScannerDigilent
from hakei.instruments.scanner.dummy import InstrumentScannerDummy
from hakei.instruments.scanner.visa import InstrumentScannerVisa

log = logging.getLogger(__name__)

__all__ = [
    "DiscoveredInstrument",
    "InstrumentScanner",
    "InstrumentScannerTransport",
    "InterfaceType",
    "get_scanner",
]


class InstrumentScanner:
    """Scans for available instruments using registered transports."""

    def __init__(self):
        self._transports: dict[InterfaceType, InstrumentScannerTransport] = {}
        self._register_default_transports()

    def _register_default_transports(self) -> None:
        """Register the default scanner transports."""
        self.register_transport(InstrumentScannerDummy())
        self.register_transport(InstrumentScannerVisa())
        self.register_transport(InstrumentScannerDigilent())

    def register_transport(self, transport: InstrumentScannerTransport) -> None:
        """
        Register a scanner transport.

        Args:
            transport: The transport to register.
        """
        self._transports[transport.interface_type] = transport
        log.debug("Registered scanner transport: %s", transport.interface_type.name)

    def get_transport(self, interface_type: InterfaceType) -> InstrumentScannerTransport | None:
        """
        Get a registered transport by interface type.

        Args:
            interface_type: The interface type to get.

        Returns:
            The transport, or None if not registered.
        """
        return self._transports.get(interface_type)

    def scan(self, interface_type: InterfaceType | None = None) -> list[DiscoveredInstrument]:
        """
        Scan for instruments.

        Args:
            interface_type: Optional filter for interface type.
                           If None, scans all interfaces.

        Returns:
            List of discovered instruments.
        """
        instruments = []

        if interface_type is not None:
            transport = self._transports.get(interface_type)
            if transport:
                instruments.extend(transport.scan())
        else:
            for transport in self._transports.values():
                instruments.extend(transport.scan())

        return instruments

    def close(self) -> None:
        """Close all transports."""
        for transport in self._transports.values():
            try:
                transport.close()
            except Exception as e:
                log.debug("Error closing transport %s: %s", transport.interface_type.name, e)
        self._transports.clear()


_scanner: InstrumentScanner | None = None


def get_scanner() -> InstrumentScanner:
    """Get the global instrument scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = InstrumentScanner()
    return _scanner
