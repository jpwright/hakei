"""VISA instrument scanner transport."""

import logging

import pyvisa

from hakei.instruments.scanner.base import (
    DiscoveredInstrument,
    InstrumentScannerTransport,
    InterfaceType,
)

log = logging.getLogger(__name__)


class InstrumentScannerVisa(InstrumentScannerTransport):
    """Scanner transport for VISA instruments."""

    def __init__(self):
        self._resource_manager: pyvisa.ResourceManager | None = None

    @property
    def interface_type(self) -> InterfaceType:
        return InterfaceType.VISA

    def _get_resource_manager(self) -> pyvisa.ResourceManager:
        """Get or create the VISA resource manager."""
        if self._resource_manager is None:
            try:
                self._resource_manager = pyvisa.ResourceManager()
                log.info("VISA resource manager initialized")
            except Exception as e:
                log.error("Failed to initialize VISA resource manager: %s", e)
                raise
        return self._resource_manager

    def scan(self) -> list[DiscoveredInstrument]:
        """
        Scan for VISA resources.

        Returns:
            List of discovered instruments.
        """
        instruments = []
        try:
            rm = self._get_resource_manager()
            resources = rm.list_resources()
            log.info("Found %d VISA resources", len(resources))

            for resource in resources:
                instrument = DiscoveredInstrument(
                    resource_address=resource,
                    interface_type=self._classify_interface(resource),
                    description=resource,
                )

                try:
                    instrument = self._identify_instrument(resource, instrument)
                except Exception as e:
                    log.debug("Could not identify %s: %s", resource, e)

                instruments.append(instrument)

        except Exception as e:
            log.error("VISA scan failed: %s", e)

        return instruments

    def _classify_interface(self, resource: str) -> InterfaceType:
        """Classify the interface type based on resource string."""
        resource_upper = resource.upper()
        if resource_upper.startswith("TCPIP"):
            return InterfaceType.ETHERNET
        elif resource_upper.startswith("USB"):
            return InterfaceType.USB
        elif resource_upper.startswith("ASRL") or resource_upper.startswith("COM"):
            return InterfaceType.SERIAL
        else:
            return InterfaceType.VISA

    def _identify_instrument(
        self, resource: str, instrument: DiscoveredInstrument
    ) -> DiscoveredInstrument:
        """Try to identify an instrument by querying *IDN?"""
        from hakei.instruments.registry import get_registry

        rm = self._get_resource_manager()
        try:
            instr = rm.open_resource(resource, timeout=2000)
            try:
                idn = instr.query("*IDN?").strip()
                parts = idn.split(",")
                if len(parts) >= 4:
                    instrument.manufacturer = parts[0].strip()
                    instrument.model = parts[1].strip()
                    instrument.serial_number = parts[2].strip()
                    instrument.description = f"{instrument.manufacturer} {instrument.model}"

                    # Look up in registry
                    registry = get_registry()
                    definition = registry.lookup(instrument.manufacturer, instrument.model)
                    if definition:
                        instrument.instrument_class = definition.instrument_class
                        instrument.panel_class = definition.panel_class
                        instrument.instrument_kwargs = definition.instrument_kwargs
                        instrument.panel_kwargs = definition.panel_kwargs
            finally:
                instr.close()
        except Exception as e:
            log.debug("IDN query failed for %s: %s", resource, e)

        return instrument

    def close(self) -> None:
        """Close the resource manager."""
        if self._resource_manager is not None:
            try:
                self._resource_manager.close()
            except Exception:
                pass
            self._resource_manager = None
