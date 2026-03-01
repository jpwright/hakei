"""Tiling window manager for instrument panels."""

import logging
from dataclasses import dataclass, field
from enum import Enum, auto

import dearpygui.dearpygui as dpg

log = logging.getLogger(__name__)

DEFAULT_SIDEBAR_WIDTH = 280
MIN_SIDEBAR_WIDTH = 200
MAX_SIDEBAR_WIDTH = 500
PADDING = 10
MENUBAR_HEIGHT = 25
MIN_WINDOW_HEIGHT = 100


class DropZone(Enum):
    """Drop zones for row-based layout."""

    CENTER = auto()
    TOP = auto()
    BOTTOM = auto()


@dataclass
class TiledWindow:
    tag: str
    label: str
    preferred_height: int = 300
    visible: bool = True
    last_pos: list[int] = field(default_factory=lambda: [0, 0])
    last_height: int = 0
    is_dragging: bool = False
    drag_settled_frames: int = 0
    expected_pos: list[int] = field(default_factory=lambda: [0, 0])


class TilingManager:
    """Manages row-based tiled layout for instrument windows."""

    def __init__(self):
        self.windows: list[TiledWindow] = []
        self._viewport_width = 1280
        self._viewport_height = 960
        self._sidebar_width = DEFAULT_SIDEBAR_WIDTH
        self._last_sidebar_width = DEFAULT_SIDEBAR_WIDTH
        self._dragging_window: TiledWindow | None = None
        self._drop_zone: DropZone | None = None
        self._target_idx: int | None = None

    def register_window(self, tag: str, label: str, preferred_height: int = 300) -> None:
        """Register a window to be managed by the tiling manager."""
        self.windows.append(
            TiledWindow(tag=tag, label=label, preferred_height=preferred_height)
        )

    def get_content_area(self) -> tuple[int, int, int, int]:
        """Get the content area (x, y, width, height) excluding sidebar."""
        x = self._sidebar_width + PADDING * 2
        y = MENUBAR_HEIGHT + PADDING
        width = self._viewport_width - x - PADDING
        height = self._viewport_height - y - PADDING
        return x, y, width, height

    def _check_sidebar_resize(self) -> bool:
        """Check if sidebar was resized and update layout if needed."""
        try:
            current_width = dpg.get_item_width("device_panel")
            current_width = max(MIN_SIDEBAR_WIDTH, min(MAX_SIDEBAR_WIDTH, current_width))

            if abs(current_width - self._last_sidebar_width) > 2:
                self._sidebar_width = current_width
                self._last_sidebar_width = current_width
                dpg.set_item_width("device_panel", current_width)
                return True
        except Exception:
            pass
        return False

    def _get_drop_zone(self, py: int, target_window: TiledWindow) -> DropZone:
        """Determine which drop zone the y position falls into."""
        try:
            wy = target_window.expected_pos[1]
            wh = target_window.last_height
        except Exception:
            return DropZone.CENTER

        if wh <= 0:
            return DropZone.CENTER

        rel_y = (py - wy) / wh

        if rel_y < 0.3:
            return DropZone.TOP
        elif rel_y > 0.7:
            return DropZone.BOTTOM
        else:
            return DropZone.CENTER

    def _find_window_at_pos(self, py: int) -> int | None:
        """Find which window index contains the y position."""
        visible = [w for w in self.windows if w.visible]

        for i, window in enumerate(visible):
            wy = window.expected_pos[1]
            wh = window.last_height
            if wy <= py <= wy + wh:
                return i

        return None

    def apply_layout(self, skip_dragging: bool = True) -> None:
        """Apply row layout to all visible windows, stacking them vertically."""
        visible = [w for w in self.windows if w.visible]
        if not visible:
            return

        x, start_y, width, total_height = self.get_content_area()
        num_windows = len(visible)

        for window in visible:
            if window.last_height <= 0:
                window.last_height = window.preferred_height

        current_y = start_y
        for i, window in enumerate(visible):
            is_last = i == num_windows - 1
            window.expected_pos = [x, current_y]

            if skip_dragging and window.is_dragging:
                current_y += window.last_height + PADDING
                continue

            if is_last:
                height = start_y + total_height - current_y
            else:
                height = window.last_height

            height = max(MIN_WINDOW_HEIGHT, height)

            try:
                dpg.set_item_pos(window.tag, [x, current_y])
                dpg.set_item_width(window.tag, width)
                dpg.set_item_height(window.tag, height)
                window.last_pos = [x, current_y]
                window.last_height = height
            except Exception:
                log.debug("Could not resize window %s", window.tag)

            current_y += height + PADDING

    def _check_window_resize(self) -> None:
        """Check if any window was resized and adjust layout."""
        visible = [w for w in self.windows if w.visible]
        if not visible:
            return

        resized = False
        for window in visible:
            if window.is_dragging:
                continue

            try:
                current_pos = dpg.get_item_pos(window.tag)
                current_height = dpg.get_item_height(window.tag)
                height_changed = abs(current_height - window.last_height) > 5
                top_moved = abs(current_pos[1] - window.expected_pos[1]) > 5

                if height_changed:
                    if top_moved:
                        # Top-edge resize detected - revert it
                        dpg.set_item_pos(window.tag, window.expected_pos)
                        dpg.set_item_height(window.tag, window.last_height)
                    else:
                        # Bottom-edge resize - accept it
                        window.last_height = max(MIN_WINDOW_HEIGHT, current_height)
                        resized = True
            except Exception:
                continue

        if resized:
            self.apply_layout(skip_dragging=True)

    def _handle_drop(self, dragged_idx: int, target_idx: int, zone: DropZone) -> None:
        """Handle dropping a window onto a target."""
        visible = [w for w in self.windows if w.visible]
        if dragged_idx >= len(visible) or target_idx >= len(visible):
            return

        if zone == DropZone.CENTER:
            visible[dragged_idx], visible[target_idx] = (
                visible[target_idx],
                visible[dragged_idx],
            )
        elif zone == DropZone.TOP:
            window = visible.pop(dragged_idx)
            insert_idx = target_idx if dragged_idx > target_idx else target_idx - 1
            visible.insert(insert_idx, window)
        elif zone == DropZone.BOTTOM:
            window = visible.pop(dragged_idx)
            insert_idx = target_idx + 1 if dragged_idx > target_idx else target_idx
            visible.insert(insert_idx, window)

        new_order = []
        visible_iter = iter(visible)
        for w in self.windows:
            if w.visible:
                new_order.append(next(visible_iter))
            else:
                new_order.append(w)
        self.windows = new_order

    def check_window_drag(self) -> None:
        """Check if windows have been dragged and handle snapping."""
        if self._check_sidebar_resize():
            self.apply_layout(skip_dragging=True)

        self._check_window_resize()

        visible = [w for w in self.windows if w.visible]

        for i, window in enumerate(visible):
            try:
                current_pos = dpg.get_item_pos(window.tag)
            except Exception:
                continue

            off_expected = (
                abs(current_pos[0] - window.expected_pos[0]) > 10
                or abs(current_pos[1] - window.expected_pos[1]) > 10
            )

            pos_moving = (
                abs(current_pos[0] - window.last_pos[0]) > 1
                or abs(current_pos[1] - window.last_pos[1]) > 1
            )

            window.last_pos = list(current_pos)

            if off_expected:
                if not window.is_dragging:
                    window.is_dragging = True
                    self._dragging_window = window

                window.drag_settled_frames = 0 if pos_moving else window.drag_settled_frames + 1

                mouse_pos = dpg.get_mouse_pos(local=False)
                target_idx = self._find_window_at_pos(int(mouse_pos[1]))

                if target_idx is not None:
                    self._target_idx = target_idx
                    self._drop_zone = self._get_drop_zone(
                        int(mouse_pos[1]), visible[target_idx]
                    )
                else:
                    self._target_idx = None
                    self._drop_zone = None

                if window.drag_settled_frames > 10:
                    if self._target_idx is not None and self._drop_zone is not None:
                        self._handle_drop(i, self._target_idx, self._drop_zone)
                    window.is_dragging = False
                    window.drag_settled_frames = 0
                    self._dragging_window = None
                    self._target_idx = None
                    self._drop_zone = None
                    self.apply_layout(skip_dragging=False)
                    break

            elif window.is_dragging:
                window.is_dragging = False
                window.drag_settled_frames = 0
                self._dragging_window = None
                self._target_idx = None
                self._drop_zone = None
                self.apply_layout(skip_dragging=False)

    def toggle_window(self, tag: str) -> None:
        """Toggle visibility of a window and re-layout."""
        for window in self.windows:
            if window.tag == tag:
                window.visible = not window.visible
                if window.visible:
                    dpg.show_item(tag)
                else:
                    dpg.hide_item(tag)
                break
        self._redistribute_heights()
        self.apply_layout(skip_dragging=False)

    def _redistribute_heights(self) -> None:
        """Redistribute heights based on preferred heights."""
        visible = [w for w in self.windows if w.visible]
        if not visible:
            return

        _, _, _, total_height = self.get_content_area()
        total_padding = PADDING * (len(visible) - 1)
        available = total_height - total_padding

        total_preferred = sum(w.preferred_height for w in visible)
        if total_preferred <= 0:
            total_preferred = available

        scale = available / total_preferred
        for window in visible:
            window.last_height = max(
                MIN_WINDOW_HEIGHT, int(window.preferred_height * scale)
            )

    def on_viewport_resize(self) -> None:
        """Handle viewport resize."""
        old_height = self._viewport_height
        self._viewport_width = dpg.get_viewport_width()
        self._viewport_height = dpg.get_viewport_height()
        self._update_sidebar()

        visible = [w for w in self.windows if w.visible]
        needs_initial_layout = any(w.last_height <= 0 for w in visible)

        if needs_initial_layout:
            self._redistribute_heights()
        elif old_height != self._viewport_height:
            self._scale_window_heights(old_height, self._viewport_height)

        self.apply_layout(skip_dragging=False)

    def _scale_window_heights(self, old_viewport_height: int, new_viewport_height: int) -> None:
        """Scale window heights proportionally when viewport changes."""
        visible = [w for w in self.windows if w.visible]
        if not visible:
            return

        old_content = old_viewport_height - MENUBAR_HEIGHT - PADDING * 2
        new_content = new_viewport_height - MENUBAR_HEIGHT - PADDING * 2

        if old_content <= 0:
            return

        scale = new_content / old_content
        for window in visible:
            window.last_height = max(MIN_WINDOW_HEIGHT, int(window.last_height * scale))

    def _update_sidebar(self) -> None:
        """Update sidebar dimensions."""
        try:
            dpg.set_item_height(
                "device_panel", self._viewport_height - MENUBAR_HEIGHT - PADDING * 2
            )
            current_width = dpg.get_item_width("device_panel")
            self._sidebar_width = max(MIN_SIDEBAR_WIDTH, min(MAX_SIDEBAR_WIDTH, current_width))
            self._last_sidebar_width = self._sidebar_width
        except Exception:
            pass


_manager: TilingManager | None = None


def get_manager() -> TilingManager:
    """Get the global tiling manager instance."""
    global _manager
    if _manager is None:
        _manager = TilingManager()
    return _manager


def setup_resize_handler() -> None:
    """Set up viewport resize handling."""

    def on_resize():
        get_manager().on_viewport_resize()

    dpg.set_viewport_resize_callback(on_resize)
