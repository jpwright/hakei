"""Instrument connection sidebar panel."""

import logging
import threading
from pathlib import Path
from typing import Any

import dearpygui.dearpygui as dpg

from hakei.config import (
    HakeiConfig,
    apply_config_to_instrument,
    build_config_from_instruments,
    load_config,
    save_config,
)
from hakei.instruments import (
    ConnectionState,
    Device,
    DiscoveredInstrument,
    Instrument,
    InterfaceType,
    get_scanner,
)
from hakei.ui.layout import DEFAULT_SIDEBAR_WIDTH, MENUBAR_HEIGHT, PADDING, get_manager

log = logging.getLogger(__name__)

INTERFACE_MAP = {
    "VISA": InterfaceType.VISA,
    "Serial": InterfaceType.SERIAL,
    "USB": InterfaceType.USB,
    "Ethernet": InterfaceType.ETHERNET,
    "Digilent": InterfaceType.DIGILENT,
    "Dummy": InterfaceType.DUMMY,
}

_discovered_instruments: list[DiscoveredInstrument] = []
_selected_instrument: DiscoveredInstrument | None = None
_open_instruments: dict[str, Instrument] = {}
_open_devices: dict[str, Device] = {}  # device_address -> Device
_open_panels: dict[str, Any] = {}
_selectable_tags: list[str] = []


def get_open_instruments() -> dict[str, Instrument]:
    """Get the dictionary of open instruments."""
    return _open_instruments


def get_open_devices() -> dict[str, Device]:
    """Get the dictionary of open devices."""
    return _open_devices


def _on_scan() -> None:
    """Handle scan button click."""
    global _discovered_instruments, _selected_instrument
    log.info("Scanning for instruments...")

    interface_name = dpg.get_value("interface_combo")
    interface_type = INTERFACE_MAP.get(interface_name)

    scanner = get_scanner()
    _discovered_instruments = scanner.scan(interface_type)
    _selected_instrument = None

    log.info("Found %d instruments", len(_discovered_instruments))

    _update_instrument_list()
    _update_instrument_info(None)


def _update_instrument_list() -> None:
    """Update the instrument list display."""
    global _selectable_tags
    dpg.delete_item("instrument_list", children_only=True)
    _selectable_tags = []

    if not _discovered_instruments:
        dpg.add_text(
            "No instruments found", color=(150, 150, 150), parent="instrument_list"
        )
        return

    for i, instrument in enumerate(_discovered_instruments):
        tag = f"instrument_selectable_{i}"
        _selectable_tags.append(tag)
        dpg.add_selectable(
            tag=tag,
            label=instrument.description or instrument.resource_address,
            callback=_on_instrument_selected,
            user_data=instrument,
            parent="instrument_list",
        )


def _on_instrument_selected(
    sender: str, app_data: Any, user_data: DiscoveredInstrument
) -> None:
    """Handle instrument selection."""
    global _selected_instrument
    _selected_instrument = user_data
    log.info("Selected instrument: %s", user_data.resource_address)

    # Deselect all other selectables
    for tag in _selectable_tags:
        if tag != sender:
            dpg.set_value(tag, False)

    _update_instrument_info(user_data)
    dpg.set_value("address_input", user_data.resource_address)


def _update_instrument_info(instrument: DiscoveredInstrument | None) -> None:
    """Update the instrument info display."""
    if instrument is None:
        dpg.set_value("info_manufacturer", "Manufacturer: --")
        dpg.set_value("info_model", "Model: --")
        dpg.set_value("info_serial", "Serial: --")
        dpg.set_value("info_type", "Type: --")
    else:
        dpg.set_value(
            "info_manufacturer",
            f"Manufacturer: {instrument.manufacturer or '--'}",
        )
        dpg.set_value("info_model", f"Model: {instrument.model or '--'}")
        dpg.set_value("info_serial", f"Serial: {instrument.serial_number or '--'}")

        if instrument.device_address:
            dpg.set_value("info_type", f"Type: Device Instrument ({instrument.instrument_id})")
        else:
            dpg.set_value("info_type", "Type: Standalone")


def _on_open() -> None:
    """Handle open button click."""
    global _selected_instrument

    if _selected_instrument is None:
        log.warning("No instrument selected")
        return

    discovered = _selected_instrument
    address = discovered.resource_address

    if address in _open_instruments:
        log.info("Instrument already open: %s", address)
        return

    # Check if this is part of a device
    if discovered.device_address:
        _open_device_instrument(discovered)
    else:
        _open_standalone_instrument(discovered)


def _open_standalone_instrument(discovered: DiscoveredInstrument) -> None:
    """Open a standalone instrument."""
    address = discovered.resource_address

    if discovered.instrument_class is None or discovered.panel_class is None:
        raise NotImplementedError(
            f"No driver implemented for {discovered.manufacturer} {discovered.model} "
            f"(address: {address})"
        )

    log.info("Opening standalone instrument: %s", address)

    # Create instrument (not yet connected)
    instrument = discovered.instrument_class(address, **discovered.instrument_kwargs)
    _open_instruments[address] = instrument

    # Create the panel immediately (shows "Connecting" status)
    panel = discovered.panel_class(instrument=instrument, **discovered.panel_kwargs)
    panel.setup()
    _open_panels[address] = panel

    # Update layout
    manager = get_manager()
    manager.on_viewport_resize()

    # Connect in background thread
    def connect_thread():
        instrument.connect()
        log.info("Opened %s: %s", discovered.instrument_class.__name__, address)
        save_default_config()

    thread = threading.Thread(target=connect_thread, daemon=True)
    thread.start()


def _open_device_instrument(discovered: DiscoveredInstrument) -> None:
    """Open an instrument that is part of a multi-instrument device."""
    address = discovered.resource_address
    device_address = discovered.device_address
    instrument_id = discovered.instrument_id

    if discovered.instrument_class is None or discovered.panel_class is None:
        raise NotImplementedError(
            f"No driver implemented for {discovered.manufacturer} {discovered.model} "
            f"instrument '{instrument_id}' (address: {address})"
        )

    # Check if device needs to be created
    device_needs_connect = device_address not in _open_devices
    
    if device_needs_connect:
        if discovered.device_class is None:
            raise NotImplementedError(
                f"No device driver implemented for {discovered.manufacturer} {discovered.model} "
                f"(address: {device_address})"
            )
        # Create device but don't connect yet
        device = discovered.device_class(device_address, **discovered.device_kwargs)
        _open_devices[device_address] = device
    else:
        device = _open_devices[device_address]

    # Create a placeholder instrument in CONNECTING state for the panel
    # The actual instrument will be set after device connects
    placeholder = _PlaceholderInstrument(address)
    _open_instruments[address] = placeholder

    # Create the panel immediately (shows "Connecting" status)
    panel = discovered.panel_class(instrument=placeholder, **discovered.panel_kwargs)
    panel.setup()
    _open_panels[address] = panel

    # Update layout
    manager = get_manager()
    manager.on_viewport_resize()

    # Connect and activate in background thread
    def connect_thread():
        nonlocal device
        
        if device_needs_connect:
            log.info("Connecting to device: %s", device_address)
            if not device.connect():
                log.error("Failed to connect to device: %s", device_address)
                placeholder._state = ConnectionState.ERROR
                return
            log.info("Device connected: %s", device_address)

        # Activate the instrument on the device
        instrument = device.activate_instrument(instrument_id)
        if instrument is None:
            log.error("Failed to activate instrument %s on device %s", instrument_id, device_address)
            placeholder._state = ConnectionState.ERROR
            return

        # Replace placeholder with real instrument
        _open_instruments[address] = instrument
        panel.instrument = instrument
        
        log.info("Opened device instrument: %s", address)
        save_default_config()

    thread = threading.Thread(target=connect_thread, daemon=True)
    thread.start()


class _PlaceholderInstrument:
    """Placeholder instrument used while connecting to show status."""
    
    def __init__(self, resource_address: str):
        self.resource_address = resource_address
        self._state = ConnectionState.CONNECTING
        self._info = None
    
    @property
    def state(self) -> ConnectionState:
        return self._state
    
    @property
    def info(self):
        return self._info


def save_default_config() -> None:
    """Save the current configuration as the default."""
    config = build_config_from_instruments(_open_instruments, _open_panels)
    if save_config(config):
        log.debug("Default configuration saved")
    else:
        log.error("Failed to save default configuration")


def save_config_to_file(path: Path) -> bool:
    """Save configuration to a specific file."""
    config = build_config_from_instruments(_open_instruments, _open_panels)
    return save_config(config, path)


def load_config_from_file(path: Path) -> bool:
    """Load configuration from a specific file."""
    config = load_config(path)
    if config is None:
        log.warning("Failed to load configuration from %s", path)
        return False

    _apply_config(config)
    log.info("Configuration loaded from %s", path)
    return True


def close_instrument(address: str) -> None:
    """Close an instrument and its panel."""
    if address not in _open_instruments:
        log.warning("Instrument not open: %s", address)
        return

    instrument = _open_instruments.pop(address)
    panel = _open_panels.pop(address, None)

    device = instrument.device
    if device is not None:
        # Find instrument_id by checking which key in device._active_instruments has this instrument
        instrument_id = None
        for inst_id, inst in device.active_instruments.items():
            if inst is instrument:
                instrument_id = inst_id
                break

        if instrument_id:
            device.deactivate_instrument(instrument_id)

        # Check if device has any remaining active instruments
        if not device.active_instruments:
            log.info("No more instruments open from device %s, disconnecting", device.resource_address)
            device.disconnect()
            _open_devices.pop(device.resource_address, None)
    else:
        # Standalone instrument
        try:
            instrument.disconnect()
        except Exception as e:
            log.error("Error disconnecting instrument: %s", e)

    if panel is not None:
        try:
            dpg.delete_item(panel.window_tag)
        except Exception as e:
            log.error("Error deleting panel: %s", e)

        manager = get_manager()
        manager.windows = [w for w in manager.windows if w.tag != panel.window_tag]
        manager.on_viewport_resize()

    log.info("Closed instrument: %s", address)
    save_default_config()


def _apply_config(config: HakeiConfig) -> None:
    """Apply a configuration, opening instruments as needed."""
    from hakei.config import PowerSupplyConfig, WaveformGeneratorConfig, apply_config_to_panel, apply_window_config

    for address, instrument in _open_instruments.items():
        for inst_config in config.instruments:
            if inst_config.resource_address == address:
                apply_config_to_instrument(instrument, inst_config)
                if address in _open_panels:
                    panel = _open_panels[address]
                    apply_config_to_panel(panel, inst_config)
                    if isinstance(inst_config, PowerSupplyConfig):
                        for channel in getattr(panel, "channels", []):
                            if hasattr(channel, "sync_from_instrument"):
                                channel.sync_from_instrument()
                    elif isinstance(inst_config, WaveformGeneratorConfig):
                        if hasattr(panel, "_sync_from_instrument"):
                            panel._sync_from_instrument()
                break

    _open_instruments_from_config(config)
    
    # Apply window layout config after all panels are created
    apply_window_config(config.window)
    manager = get_manager()
    manager.apply_layout(skip_dragging=False)


def _open_instruments_from_config(config: HakeiConfig) -> None:
    """Open instruments specified in config that aren't already open."""
    from hakei.instruments.dummy import (
        DummyOscilloscope,
        DummyPowerSupply,
        DummyWaveformGenerator,
    )
    from hakei.instruments.oscilloscope import Oscilloscope
    from hakei.instruments.power_supply import PowerSupply
    from hakei.instruments.waveform_generator import WaveformGenerator

    dummy_classes = [DummyPowerSupply, DummyOscilloscope, DummyWaveformGenerator]

    for inst_config in config.instruments:
        if inst_config.resource_address in _open_instruments:
            continue

        address = inst_config.resource_address
        
        # Handle dummy instruments directly
        if address.startswith("DUMMY"):
            for inst_class in dummy_classes:
                config_class = inst_class.get_config_class()
                if config_class is not None and isinstance(inst_config, config_class):
                    num_channels = len(getattr(inst_config, "channels", [])) or inst_class.default_channels
                    instrument = inst_class(address, num_channels=num_channels)
                    _open_instruments[address] = instrument

                    panel_class = inst_class.get_panel_class()
                    panel_kwargs = {}
                    if issubclass(inst_class, (PowerSupply, WaveformGenerator, Oscilloscope)):
                        panel_kwargs["num_channels"] = num_channels
                    panel = panel_class(instrument=instrument, **panel_kwargs)
                    panel.setup()
                    _open_panels[address] = panel
                    
                    # Apply panel-specific config (axis limits, etc.)
                    from hakei.config import apply_config_to_panel
                    apply_config_to_panel(panel, inst_config)
                    
                    # Connect in background
                    def connect_thread(inst=instrument, cfg=inst_config, name=inst_class.__name__):
                        inst.connect()
                        apply_config_to_instrument(inst, cfg)
                        log.info("Opened %s from config: %s", name, address)
                    
                    thread = threading.Thread(target=connect_thread, daemon=True)
                    thread.start()
                    break
        else:
            # For non-dummy instruments, scan and find matching instrument
            _open_scanned_instrument_from_config(inst_config)

    manager = get_manager()
    manager.on_viewport_resize()


def _open_scanned_instrument_from_config(inst_config: Any) -> bool:
    """Try to open a non-dummy instrument by scanning for it."""
    from hakei.instruments.oscilloscope import Oscilloscope
    from hakei.instruments.power_supply import PowerSupply
    from hakei.instruments.waveform_generator import WaveformGenerator

    address = inst_config.resource_address
    
    # Scan all interface types to find matching instrument
    scanner = get_scanner()
    
    # Try Digilent first, then other interfaces
    for interface_type in [InterfaceType.DIGILENT, InterfaceType.VISA, InterfaceType.USB]:
        try:
            discovered_list = scanner.scan(interface_type)
        except Exception as e:
            log.debug("Failed to scan %s: %s", interface_type, e)
            continue
        
        for discovered in discovered_list:
            if discovered.resource_address != address:
                continue
            
            # Found matching instrument
            log.info("Found instrument from config: %s", address)
            
            if discovered.instrument_class is None or discovered.panel_class is None:
                log.warning("No driver for instrument: %s", address)
                return False
            
            # Open the instrument
            if discovered.device_address:
                # Device-based instrument
                if discovered.device_address not in _open_devices:
                    if discovered.device_class is None:
                        log.warning("No device driver for: %s", discovered.device_address)
                        return False
                    
                    device = discovered.device_class(
                        discovered.device_address, **discovered.device_kwargs
                    )
                    if not device.connect():
                        log.error("Failed to connect to device: %s", discovered.device_address)
                        return False
                    _open_devices[discovered.device_address] = device
                
                device = _open_devices[discovered.device_address]
                instrument = device.activate_instrument(discovered.instrument_id)
                if instrument is None:
                    log.error("Failed to activate instrument: %s", address)
                    return False
            else:
                # Standalone instrument
                instrument = discovered.instrument_class(
                    address, **discovered.instrument_kwargs
                )
                instrument.connect()
            
            _open_instruments[address] = instrument
            apply_config_to_instrument(instrument, inst_config)
            
            # Create panel
            panel_kwargs = dict(discovered.panel_kwargs)
            panel = discovered.panel_class(instrument=instrument, **panel_kwargs)
            panel.setup()
            _open_panels[address] = panel
            
            # Apply panel-specific config (axis limits, etc.)
            from hakei.config import apply_config_to_panel
            apply_config_to_panel(panel, inst_config)
            
            log.info("Opened %s from config: %s", type(instrument).__name__, address)
            return True
    
    log.warning("Could not find instrument from config: %s", address)
    return False


def load_default_config() -> None:
    """Load the default configuration on startup."""
    config = load_config()
    if config is not None:
        _apply_config(config)


def setup_instrument_panel():
    """Create the instrument connection and management panel (resizable sidebar)."""
    with dpg.window(
        label="Instruments",
        tag="instrument_panel",
        width=DEFAULT_SIDEBAR_WIDTH,
        height=900,
        pos=(PADDING, MENUBAR_HEIGHT + PADDING),
        no_close=True,
        no_collapse=True,
        no_move=True,
    ):
        dpg.add_text("Connection")
        dpg.add_separator()

        dpg.add_text("Interface", color=(150, 150, 150))
        dpg.add_combo(
            tag="interface_combo",
            items=list(INTERFACE_MAP.keys()),
            default_value="Dummy",
            width=-1,
        )

        dpg.add_spacer(height=5)
        dpg.add_text("Address", color=(150, 150, 150))
        dpg.add_input_text(
            tag="address_input",
            hint="TCPIP::192.168.1.100::INSTR",
            width=-1,
        )

        dpg.add_spacer(height=5)
        dpg.add_button(label="Scan", width=-1, callback=_on_scan)

        dpg.add_spacer(height=15)
        dpg.add_text("Discovered Instruments")
        dpg.add_separator()

        with dpg.child_window(tag="instrument_list", height=200, border=True):
            dpg.add_text("Click 'Scan' to find instruments", color=(150, 150, 150))

        dpg.add_spacer(height=5)
        dpg.add_button(label="Open", width=-1, callback=_on_open)

        dpg.add_spacer(height=15)
        dpg.add_text("Selected Info")
        dpg.add_separator()

        with dpg.child_window(height=100, border=True):
            dpg.add_text("Manufacturer: --", tag="info_manufacturer")
            dpg.add_text("Model: --", tag="info_model")
            dpg.add_text("Serial: --", tag="info_serial")
            dpg.add_text("Type: --", tag="info_type")

