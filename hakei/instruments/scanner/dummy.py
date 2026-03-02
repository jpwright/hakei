"""Dummy instrument scanner transport."""

import logging

from hakei.instruments.scanner.base import (
    DiscoveredInstrument,
    InstrumentScannerTransport,
    InterfaceType,
)

log = logging.getLogger(__name__)


class InstrumentScannerDummy(InstrumentScannerTransport):
    """Scanner transport for dummy/simulated instruments."""

    @property
    def interface_type(self) -> InterfaceType:
        return InterfaceType.DUMMY

    def scan(self) -> list[DiscoveredInstrument]:
        """
        Get list of available dummy instruments for testing.

        Returns:
            List of discovered dummy instruments from the dummy device.
        """
        from hakei.instruments.registry import get_registry

        log.debug("Scanning for dummy instruments")
        registry = get_registry()
        instruments = []

        # Look up the dummy device in registry
        device_def = registry.lookup("Hakei", "DummyDevice")
        if device_def is None:
            log.warning("DummyDevice not found in registry")
            return instruments

        device_address = "DUMMY::DEVICE::1"

        # Expand device into its instruments
        for inst_def in device_def.instruments:
            instruments.append(DiscoveredInstrument(
                resource_address=f"{device_address}::{inst_def.id}",
                interface_type=InterfaceType.DUMMY,
                description=f"Dummy {inst_def.description}",
                manufacturer="Hakei",
                model="DummyDevice",
                instrument_class=inst_def.instrument_class,
                panel_class=inst_def.panel_class,
                instrument_kwargs=inst_def.instrument_kwargs,
                panel_kwargs=inst_def.panel_kwargs,
                device_address=device_address,
                device_class=device_def.device_class,
                device_kwargs=device_def.device_kwargs,
                instrument_id=inst_def.id,
            ))

        return instruments
