"""Device connection sidebar panel."""

import dearpygui.dearpygui as dpg


def setup_device_panel():
    """Create the device connection and management panel."""
    with dpg.window(
        label="Devices",
        tag="device_panel",
        width=280,
        height=-1,
        pos=(10, 30),
        no_close=True,
        no_collapse=True,
    ):
        dpg.add_text("Connection")
        dpg.add_separator()

        dpg.add_combo(
            label="Interface",
            items=["VISA", "Serial", "USB", "Ethernet"],
            default_value="VISA",
            width=-1,
        )
        dpg.add_input_text(
            label="Address",
            hint="TCPIP::192.168.1.100::INSTR",
            width=-1,
        )
        dpg.add_button(label="Connect", width=-1)
        dpg.add_button(label="Scan", width=-1)

        dpg.add_spacer(height=15)
        dpg.add_text("Connected Devices")
        dpg.add_separator()

        with dpg.child_window(height=200, border=True):
            dpg.add_text("No devices connected", color=(150, 150, 150))

        dpg.add_spacer(height=15)
        dpg.add_text("Device Info")
        dpg.add_separator()

        with dpg.child_window(height=-1, border=True):
            dpg.add_text("Manufacturer: --")
            dpg.add_text("Model: --")
            dpg.add_text("Serial: --")
            dpg.add_text("Firmware: --")
