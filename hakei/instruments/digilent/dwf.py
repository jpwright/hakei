"""Digilent Waveforms SDK wrapper."""

import logging
import sys
from ctypes import CDLL

log = logging.getLogger(__name__)

_dwf: CDLL | None = None
_dwf_loaded = False


def _load_dwf() -> CDLL | None:
    """Load the Digilent Waveforms library."""
    global _dwf, _dwf_loaded

    if _dwf_loaded:
        return _dwf

    _dwf_loaded = True

    try:
        if sys.platform.startswith("win"):
            from ctypes import cdll
            _dwf = cdll.dwf
        elif sys.platform.startswith("darwin"):
            _dwf = CDLL("/Library/Frameworks/dwf.framework/dwf")
        else:
            _dwf = CDLL("libdwf.so")
        log.info("Digilent Waveforms SDK loaded successfully")
    except OSError as e:
        log.debug("Could not load Digilent Waveforms library: %s", e)
        _dwf = None

    return _dwf


def get_dwf() -> CDLL | None:
    """
    Get the Digilent Waveforms library handle.

    Returns:
        The DWF library handle, or None if not available.
    """
    return _load_dwf()


def is_dwf_available() -> bool:
    """
    Check if the Digilent Waveforms SDK is available.

    Returns:
        True if the SDK is available, False otherwise.
    """
    return _load_dwf() is not None
