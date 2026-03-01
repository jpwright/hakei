"""Power supply view and controls."""

import dearpygui.dearpygui as dpg


def setup_power_supply_view():
    """Create the power supply control window."""
    with dpg.window(
        label="Power Supply",
        tag="power_supply_window",
        width=400,
        height=380,
        pos=(300, 540),
        no_close=True,
    ):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Output ON", width=100, tag="psu_output_btn")
            dpg.add_spacer(width=20)
            dpg.add_text("Output: OFF", tag="psu_output_status", color=(255, 100, 100))

        dpg.add_separator()
        dpg.add_spacer(height=5)

        with dpg.child_window(height=120, border=True):
            dpg.add_text("Actual Values", color=(150, 150, 150))
            dpg.add_spacer(height=5)

            with dpg.group(horizontal=True):
                dpg.add_text("Voltage:", color=(100, 200, 100))
                dpg.add_text("0.000 V", tag="psu_actual_voltage")

            with dpg.group(horizontal=True):
                dpg.add_text("Current:", color=(100, 150, 255))
                dpg.add_text("0.000 A", tag="psu_actual_current")

            with dpg.group(horizontal=True):
                dpg.add_text("Power:", color=(255, 200, 100))
                dpg.add_text("0.000 W", tag="psu_actual_power")

        dpg.add_spacer(height=10)
        dpg.add_text("Set Points")
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_text("Voltage (V):")
            dpg.add_input_float(
                tag="psu_set_voltage",
                default_value=0.0,
                min_value=0.0,
                max_value=30.0,
                step=0.1,
                width=120,
            )
            dpg.add_button(label="Set", width=50)

        with dpg.group(horizontal=True):
            dpg.add_text("Current (A):")
            dpg.add_input_float(
                tag="psu_set_current",
                default_value=0.0,
                min_value=0.0,
                max_value=5.0,
                step=0.01,
                width=120,
            )
            dpg.add_button(label="Set", width=50)

        dpg.add_spacer(height=10)
        dpg.add_text("Presets")
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_button(label="3.3V", width=60)
            dpg.add_button(label="5V", width=60)
            dpg.add_button(label="12V", width=60)
            dpg.add_button(label="24V", width=60)
