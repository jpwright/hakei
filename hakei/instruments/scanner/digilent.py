"""Digilent instrument scanner transport."""

import logging

from hakei.instruments.scanner.base import (
    DiscoveredInstrument,
    InstrumentScannerTransport,
    InterfaceType,
)

log = logging.getLogger(__name__)


class InstrumentScannerDigilent(InstrumentScannerTransport):
    """Scanner transport for Digilent Waveforms devices."""

    @property
    def interface_type(self) -> InterfaceType:
        return InterfaceType.DIGILENT

    def scan(self) -> list[DiscoveredInstrument]:
        """
        Scan for Digilent Waveforms devices (Analog Discovery, etc).

        Digilent devices are multi-function devices. This scanner expands
        each device into its available instruments based on the registry.

        Returns:
            List of discovered instruments from Digilent devices.
        """
        from hakei.instruments.digilent import scan_digilent
        from hakei.instruments.registry import get_registry

        instruments = []
        devices = scan_digilent()
        registry = get_registry()

        for device in devices:
            device_address = f"DIGILENT::{device['device_index']}::{device['serial_number']}"
            device_name = device["device_name"]
            serial = device["serial_number"]

            # Look up device in registry
            log.debug("Looking up device: manufacturer='Digilent', model='%s'", device_name)
            device_def = registry.lookup("Digilent", device_name)

            if device_def is None:
                log.warning("Unrecognized Digilent device: '%s'", device_name)
                log.debug("Available devices: %s", [(d.manufacturer, d.model) for d in registry.get_all()])
                # Add a placeholder instrument so the device shows up
                instruments.append(DiscoveredInstrument(
                    resource_address=device_address,
                    interface_type=InterfaceType.DIGILENT,
                    description=f"{device_name} (unrecognized)",
                    manufacturer="Digilent",
                    model=device_name,
                    serial_number=serial,
                ))
                continue

            # Expand device into its instruments from registry
            for inst_def in device_def.instruments:
                instruments.append(DiscoveredInstrument(
                    resource_address=f"{device_address}::{inst_def.id}",
                    interface_type=InterfaceType.DIGILENT,
                    description=f"{device_name} {inst_def.description}",
                    manufacturer="Digilent",
                    model=device_name,
                    serial_number=serial,
                    instrument_class=inst_def.instrument_class,
                    panel_class=inst_def.panel_class,
                    instrument_kwargs=inst_def.instrument_kwargs,
                    panel_kwargs=inst_def.panel_kwargs,
                    device_address=device_address,
                    device_class=device_def.device_class,
                    device_kwargs={
                        **device_def.device_kwargs,
                        "device_index": device["device_index"],
                    },
                    instrument_id=inst_def.id,
                ))

        return instruments
