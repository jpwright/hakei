"""Waveform generator view and controls."""

import dearpygui.dearpygui as dpg


def setup_waveform_gen_view():
    """Create the waveform generator control window."""
    with dpg.window(
        label="Waveform Generator",
        tag="waveform_gen_window",
        width=400,
        height=380,
        pos=(710, 540),
        no_close=True,
    ):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Output ON", width=100, tag="wfg_output_btn")
            dpg.add_spacer(width=20)
            dpg.add_text("Output: OFF", tag="wfg_output_status", color=(255, 100, 100))

        dpg.add_separator()
        dpg.add_spacer(height=5)

        dpg.add_text("Waveform Type")
        with dpg.group(horizontal=True):
            dpg.add_button(label="Sine", width=70)
            dpg.add_button(label="Square", width=70)
            dpg.add_button(label="Triangle", width=70)
            dpg.add_button(label="Ramp", width=70)

        with dpg.group(horizontal=True):
            dpg.add_button(label="Pulse", width=70)
            dpg.add_button(label="Noise", width=70)
            dpg.add_button(label="DC", width=70)
            dpg.add_button(label="Arb", width=70)

        dpg.add_spacer(height=10)
        dpg.add_text("Parameters")
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_text("Frequency:")
            dpg.add_input_float(
                tag="wfg_frequency",
                default_value=1000.0,
                min_value=0.001,
                max_value=25000000.0,
                step=100,
                width=120,
            )
            dpg.add_combo(items=["Hz", "kHz", "MHz"], default_value="Hz", width=60)

        with dpg.group(horizontal=True):
            dpg.add_text("Amplitude:")
            dpg.add_input_float(
                tag="wfg_amplitude",
                default_value=1.0,
                min_value=0.001,
                max_value=10.0,
                step=0.1,
                width=120,
            )
            dpg.add_combo(items=["Vpp", "Vrms", "dBm"], default_value="Vpp", width=60)

        with dpg.group(horizontal=True):
            dpg.add_text("Offset:")
            dpg.add_input_float(
                tag="wfg_offset",
                default_value=0.0,
                min_value=-10.0,
                max_value=10.0,
                step=0.1,
                width=120,
            )
            dpg.add_text("V")

        with dpg.group(horizontal=True):
            dpg.add_text("Phase:")
            dpg.add_input_float(
                tag="wfg_phase",
                default_value=0.0,
                min_value=0.0,
                max_value=360.0,
                step=1.0,
                width=120,
            )
            dpg.add_text("deg")

        dpg.add_spacer(height=10)
        dpg.add_text("Modulation")
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="Enable", tag="wfg_mod_enable")
            dpg.add_spacer(width=10)
            dpg.add_text("Type:")
            dpg.add_combo(
                items=["AM", "FM", "PM", "FSK", "PWM"],
                default_value="AM",
                width=80,
            )
