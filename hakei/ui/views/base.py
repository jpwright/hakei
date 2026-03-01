"""Base class for instrument panels."""

import logging
from abc import ABC, abstractmethod

import dearpygui.dearpygui as dpg

from hakei.ui.layout import get_manager

log = logging.getLogger(__name__)


class InstrumentPanel(ABC):
    """Abstract base class for instrument panels."""

    def __init__(self, tag: str, label: str, preferred_height: int = 300):
        self.tag = tag
        self.label = label
        self.preferred_height = preferred_height
        self._setup_complete = False

    @property
    @abstractmethod
    def window_tag(self) -> str:
        """Return the DearPyGui window tag."""
        ...

    @abstractmethod
    def _build_ui(self) -> None:
        """Build the panel UI elements. Called within the window context."""
        ...

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
            self._build_ui()

        self._setup_complete = True
        log.debug("Panel %s setup complete", self.label)

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
