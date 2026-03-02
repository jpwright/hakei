"""Digilent device scanning."""

import logging
from ctypes import byref, c_int, create_string_buffer

from hakei.instruments.digilent.dwf import get_dwf

log = logging.getLogger(__name__)


def scan_digilent() -> list[dict]:
    """
    Scan for Digilent Waveforms devices (Analog Discovery, etc).

    Returns:
        List of dictionaries with device info:
        - device_index: int
        - device_name: str
        - serial_number: str
    """
    devices = []
    dwf = get_dwf()
    if dwf is None:
        log.debug("Digilent Waveforms SDK not available")
        return devices

    try:
        # Check for library errors
        szerr = create_string_buffer(512)
        dwf.FDwfGetLastErrorMsg(szerr)
        if szerr[0] != b'\0':
            log.warning("DWF library error: %s", szerr.value.decode())
            return devices

        # Get DWF version
        version = create_string_buffer(16)
        dwf.FDwfGetVersion(version)
        log.debug("DWF Version: %s", version.value.decode())

        # Enumerate devices
        cDevice = c_int()
        dwf.FDwfEnum(c_int(0), byref(cDevice))
        log.info("Found %d Digilent devices", cDevice.value)

        devicename = create_string_buffer(64)
        serialnum = create_string_buffer(16)

        for iDevice in range(cDevice.value):
            dwf.FDwfEnumDeviceName(c_int(iDevice), devicename)
            dwf.FDwfEnumSN(c_int(iDevice), serialnum)

            name = devicename.value.decode()
            serial = serialnum.value.decode()

            devices.append({
                "device_index": iDevice,
                "device_name": name,
                "serial_number": serial,
            })
            log.debug("Found Digilent device: %s (%s)", name, serial)

    except Exception as e:
        log.error("Digilent scan failed: %s", e)

    return devices
