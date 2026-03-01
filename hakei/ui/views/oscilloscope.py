"""Oscilloscope view and controls."""

import dearpygui.dearpygui as dpg

from hakei.ui.views.base import InstrumentPanel


class OscilloscopePanel(InstrumentPanel):
    """Oscilloscope instrument panel."""

    def __init__(self):
        super().__init__(tag="oscilloscope", label="Oscilloscope", preferred_height=450)

    @property
    def window_tag(self) -> str:
        return "oscilloscope_window"

    def _build_ui(self) -> None:
        with dpg.group(horizontal=True):
            dpg.add_button(label="Run/Stop", width=80)
            dpg.add_button(label="Single", width=80)
            dpg.add_button(label="Auto", width=80)
            dpg.add_spacer(width=20)
            dpg.add_text("Status: Stopped", tag="scope_status")

        dpg.add_separator()

        with dpg.plot(
            label="Waveform Display",
            height=-150,
            width=-1,
            tag="scope_plot",
        ):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (ms)", tag="scope_x_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="Voltage (V)", tag="scope_y_axis")

            dpg.add_line_series(
                [],
                [],
                label="CH1",
                parent="scope_y_axis",
                tag="ch1_series",
            )
            dpg.add_line_series(
                [],
                [],
                label="CH2",
                parent="scope_y_axis",
                tag="ch2_series",
            )

        dpg.add_separator()

        with dpg.tab_bar():
            with dpg.tab(label="Horizontal"):
                with dpg.group(horizontal=True):
                    dpg.add_text("Time/Div:")
                    dpg.add_combo(
                        items=["1us", "10us", "100us", "1ms", "10ms", "100ms"],
                        default_value="1ms",
                        width=100,
                    )
                    dpg.add_spacer(width=20)
                    dpg.add_text("Position:")
                    dpg.add_slider_float(
                        width=150, default_value=0, min_value=-100, max_value=100
                    )

            with dpg.tab(label="Channel 1"):
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="Enable", default_value=True)
                    dpg.add_spacer(width=10)
                    dpg.add_text("V/Div:")
                    dpg.add_combo(
                        items=["10mV", "100mV", "1V", "10V"],
                        default_value="1V",
                        width=100,
                    )
                    dpg.add_spacer(width=10)
                    dpg.add_text("Coupling:")
                    dpg.add_combo(items=["DC", "AC", "GND"], default_value="DC", width=80)

            with dpg.tab(label="Channel 2"):
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="Enable", default_value=False)
                    dpg.add_spacer(width=10)
                    dpg.add_text("V/Div:")
                    dpg.add_combo(
                        items=["10mV", "100mV", "1V", "10V"],
                        default_value="1V",
                        width=100,
                    )
                    dpg.add_spacer(width=10)
                    dpg.add_text("Coupling:")
                    dpg.add_combo(items=["DC", "AC", "GND"], default_value="DC", width=80)

            with dpg.tab(label="Trigger"):
                with dpg.group(horizontal=True):
                    dpg.add_text("Source:")
                    dpg.add_combo(items=["CH1", "CH2", "EXT"], default_value="CH1", width=80)
                    dpg.add_spacer(width=10)
                    dpg.add_text("Mode:")
                    dpg.add_combo(
                        items=["Auto", "Normal", "Single"], default_value="Auto", width=80
                    )
                    dpg.add_spacer(width=10)
                    dpg.add_text("Level:")
                    dpg.add_slider_float(
                        width=120, default_value=0, min_value=-10, max_value=10
                    )


_panel: OscilloscopePanel | None = None


def setup_oscilloscope_view() -> OscilloscopePanel:
    """Create the oscilloscope visualization window."""
    global _panel
    if _panel is None:
        _panel = OscilloscopePanel()
    _panel.setup()
    return _panel
