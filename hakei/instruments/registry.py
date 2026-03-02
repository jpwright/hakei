"""Device registry for recognized devices."""

import importlib
import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

REGISTRY_FILE = Path(__file__).parent / "registry.yaml"


class DeviceInstrumentDefinition(BaseModel):
    """Definition of an instrument within a device."""

    model_config = {"arbitrary_types_allowed": True}

    id: str
    description: str = ""
    instrument_class: Any = None
    panel_class: Any = None
    instrument_kwargs: dict[str, Any] = Field(default_factory=dict)
    panel_kwargs: dict[str, Any] = Field(default_factory=dict)


class DeviceDefinition(BaseModel):
    """Definition of a recognized device."""

    model_config = {"arbitrary_types_allowed": True}

    manufacturer: str
    model: str
    device_class: Any = None
    device_kwargs: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    instruments: list[DeviceInstrumentDefinition] = Field(default_factory=list)

    def get_instrument(self, instrument_id: str) -> DeviceInstrumentDefinition | None:
        """Get an instrument definition by ID."""
        for inst in self.instruments:
            if inst.id == instrument_id:
                return inst
        return None


class DeviceRegistry:
    """Registry of recognized devices."""

    def __init__(self):
        self._devices: dict[tuple[str, str], DeviceDefinition] = {}

    def register(self, definition: DeviceDefinition) -> None:
        """Register a device definition."""
        key = (definition.manufacturer.upper(), definition.model.upper())
        self._devices[key] = definition
        log.debug("Registered device: %s %s", definition.manufacturer, definition.model)

    def lookup(self, manufacturer: str, model: str) -> DeviceDefinition | None:
        """Look up a device by manufacturer and model."""
        key = (manufacturer.upper(), model.upper())
        return self._devices.get(key)

    def is_recognized(self, manufacturer: str, model: str) -> bool:
        """Check if a device is recognized."""
        return self.lookup(manufacturer, model) is not None

    def get_all(self) -> list[DeviceDefinition]:
        """Get all registered device definitions."""
        return list(self._devices.values())

    def load_from_yaml(self, path: Path) -> int:
        """
        Load device definitions from a YAML file.

        Returns:
            Number of devices loaded.
        """
        if not path.exists():
            log.warning("Registry file not found: %s", path)
            return 0

        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except Exception as e:
            log.error("Failed to load registry file: %s", e)
            return 0

        if not data or "devices" not in data:
            log.warning("No devices found in registry file")
            return 0

        count = 0
        for entry in data["devices"]:
            try:
                definition = _parse_device_entry(entry)
                if definition:
                    self.register(definition)
                    count += 1
            except Exception as e:
                log.warning(
                    "Failed to parse device entry %s %s: %s",
                    entry.get("manufacturer", "?"),
                    entry.get("model", "?"),
                    e,
                )

        log.info("Loaded %d devices from registry", count)
        return count


def _import_class(class_path: str) -> Any:
    """Import a class from a fully qualified path."""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _try_import_class(class_path: str | None) -> Any:
    """Try to import a class, returning None if it fails or path is None."""
    if not class_path:
        return None
    try:
        return _import_class(class_path)
    except (ImportError, AttributeError) as e:
        log.debug("Could not import %s: %s", class_path, e)
        return None


def _parse_device_instrument_entry(entry: dict) -> DeviceInstrumentDefinition | None:
    """Parse a device instrument entry."""
    inst_id = entry.get("id")
    if not inst_id:
        log.warning("Device instrument entry missing 'id': %s", entry)
        return None

    return DeviceInstrumentDefinition(
        id=inst_id,
        description=entry.get("description", ""),
        instrument_class=_try_import_class(entry.get("instrument_class")),
        panel_class=_try_import_class(entry.get("panel_class")),
        instrument_kwargs=entry.get("instrument_kwargs", {}),
        panel_kwargs=entry.get("panel_kwargs", {}),
    )


def _parse_device_entry(entry: dict) -> DeviceDefinition | None:
    """Parse a YAML device entry into a DeviceDefinition."""
    manufacturer = entry.get("manufacturer")
    model = entry.get("model")

    if not all([manufacturer, model]):
        log.warning("Incomplete device entry: %s", entry)
        return None

    instruments = []
    for inst_entry in entry.get("instruments", []):
        inst_def = _parse_device_instrument_entry(inst_entry)
        if inst_def:
            instruments.append(inst_def)

    return DeviceDefinition(
        manufacturer=manufacturer,
        model=model,
        device_class=_try_import_class(entry.get("device_class")),
        device_kwargs=entry.get("device_kwargs", {}),
        description=entry.get("description", ""),
        instruments=instruments,
    )


_registry: DeviceRegistry | None = None


def get_registry() -> DeviceRegistry:
    """Get the global device registry."""
    global _registry
    if _registry is None:
        _registry = DeviceRegistry()
        _registry.load_from_yaml(REGISTRY_FILE)
    return _registry
