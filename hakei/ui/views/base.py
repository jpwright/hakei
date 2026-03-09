"""Base class for instrument panels."""

import logging
from abc import ABC, abstractmethod
from typing import Any

import dearpygui.dearpygui as dpg

from hakei.instruments.base import ConnectionState, Instrument
from hakei.ui.layout import get_manager

log = logging.getLogger(__name__)


class InstrumentPanel(ABC):
    """Abstract base class for instrument panels."""

    def __init__(
        self,
        tag: str,
        label: str,
        preferred_height: int = 300,
        instrument: Instrument | None = None,
    ):
        self.tag = tag
        self.label = label
        self.preferred_height = preferred_height
        self.instrument: Any = instrument
        self._setup_complete = False
        self._controls_enabled = True
        self._was_connected = False

    @property
    @abstractmethod
    def window_tag(self) -> str:
        """Return the DearPyGui window tag."""
        ...

    @property
    def status_tag(self) -> str:
        """Return the connection status text tag."""
        return f"{self.tag}_conn_status"

    @property
    def controls_tag(self) -> str:
        """Return the controls container tag."""
        return f"{self.tag}_controls"

    @abstractmethod
    def _build_ui(self) -> None:
        """Build the panel UI elements. Called within the window context."""
        ...

    def _on_close(self) -> None:
        """Handle close button click."""
        from hakei.ui.instrument_panel import close_instrument

        if self.instrument:
            close_instrument(self.instrument.resource_address)

    def setup(self) -> None:
        """Set up the instrument panel window."""
        if self._setup_complete:
            log.warning("Panel %s already set up", self.label)
            return

        get_manager().register_window(
            self.window_tag, self.label, self.preferred_height
        )

        with dpg.window(
            label=self.label,
            tag=self.window_tag,
            no_close=True,
            no_collapse=True,
        ):
            # Header with close button and connection status
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="X",
                    width=25,
                    callback=self._on_close,
                )
                dpg.add_text(self.label, color=(200, 200, 200))
                if self.instrument:
                    dpg.add_text(
                        f"({self.instrument.resource_address})",
                        color=(120, 120, 120),
                    )
                dpg.add_spacer(width=10)
                dpg.add_text(
                    "[Connecting...]",
                    tag=self.status_tag,
                    color=(200, 200, 100),
                )

            dpg.add_separator()
            dpg.add_spacer(height=5)

            # Wrap controls in a group for enable/disable
            with dpg.group(tag=self.controls_tag):
                self._build_ui()

        self._setup_complete = True
        self._update_connection_status()

        # Register update callback for connection status
        get_manager().register_update_callback(self._update_connection_status)

        log.debug("Panel %s setup complete", self.label)

    def _update_connection_status(self) -> None:
        """Update the connection status display based on instrument state."""
        if not dpg.does_item_exist(self.status_tag):
            return

        if not self.instrument:
            dpg.set_value(self.status_tag, "[No Instrument]")
            dpg.configure_item(self.status_tag, color=(150, 150, 150))
            self._set_controls_enabled(False)
            self._was_connected = False
            return

        state = self.instrument.state
        is_connected = state == ConnectionState.CONNECTED

        if state == ConnectionState.CONNECTED:
            dpg.set_value(self.status_tag, "[Connected]")
            dpg.configure_item(self.status_tag, color=(100, 200, 100))
            self._set_controls_enabled(True)
        elif state == ConnectionState.CONNECTING:
            dpg.set_value(self.status_tag, "[Connecting...]")
            dpg.configure_item(self.status_tag, color=(200, 200, 100))
            self._set_controls_enabled(False)
        elif state == ConnectionState.ERROR:
            dpg.set_value(self.status_tag, "[Error]")
            dpg.configure_item(self.status_tag, color=(200, 100, 100))
            self._set_controls_enabled(False)
        else:
            dpg.set_value(self.status_tag, "[Disconnected]")
            dpg.configure_item(self.status_tag, color=(150, 150, 150))
            self._set_controls_enabled(False)

        # Trigger sync when transitioning to connected
        if is_connected and not self._was_connected:
            self._on_connected()
        self._was_connected = is_connected

    def _on_connected(self) -> None:
        """Called when the instrument transitions to connected state.

        Override in subclasses to sync UI with instrument values.
        """
        pass

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable all controls in the panel."""
        if self._controls_enabled == enabled:
            return
        self._controls_enabled = enabled

        if not dpg.does_item_exist(self.controls_tag):
            return

        # Recursively enable/disable all interactive children
        self._set_children_enabled(self.controls_tag, enabled)

    def _set_children_enabled(self, parent: str | int, enabled: bool) -> None:
        """Recursively set enabled state for all children."""
        try:
            children = dpg.get_item_children(parent)
            if not children:
                return

            # Children dict has slot keys (0, 1, 2, etc.)
            for slot_children in children.values():
                if not slot_children:
                    continue
                for child in slot_children:
                    # Try to enable/disable the item
                    try:
                        item_type = dpg.get_item_type(child)
                        # Only disable interactive items
                        interactive_types = [
                            "mvAppItemType::mvButton",
                            "mvAppItemType::mvCheckbox",
                            "mvAppItemType::mvCombo",
                            "mvAppItemType::mvInputFloat",
                            "mvAppItemType::mvInputInt",
                            "mvAppItemType::mvInputText",
                            "mvAppItemType::mvSliderFloat",
                            "mvAppItemType::mvSliderInt",
                            "mvAppItemType::mvDragFloat",
                            "mvAppItemType::mvDragInt",
                            "mvAppItemType::mvRadioButton",
                            "mvAppItemType::mvListbox",
                            "mvAppItemType::mvSelectable",
                        ]
                        if item_type in interactive_types:
                            dpg.configure_item(child, enabled=enabled)
                    except Exception:
                        pass

                    # Recurse into children
                    self._set_children_enabled(child, enabled)
        except Exception:
            pass

    def show(self) -> None:
        """Show the panel."""
        dpg.show_item(self.window_tag)

    def hide(self) -> None:
        """Hide the panel."""
        dpg.hide_item(self.window_tag)

    def is_visible(self) -> bool:
        """Check if the panel is visible."""
        try:
            return dpg.is_item_visible(self.window_tag)
        except Exception:
            return False
