"""Digilent oscilloscope implementation."""

import logging
from ctypes import byref, c_double, c_int

import numpy as np

from hakei.instruments.digilent.device import DigilentDevice
from hakei.instruments.oscilloscope import (
    AcquisitionState,
    Coupling,
    Oscilloscope,
    TriggerEdge,
    TriggerMode,
    WaveformData,
)

log = logging.getLogger(__name__)

# DWF state constants
DwfStateReady = c_int(0)
DwfStateArmed = c_int(1)
DwfStateDone = c_int(2)
DwfStateTriggered = c_int(3)
DwfStateConfig = c_int(4)
DwfStatePrefill = c_int(5)

# DWF acquisition modes
acqmodeSingle = c_int(0)
acqmodeScanShift = c_int(1)
acqmodeScanScreen = c_int(2)
acqmodeRecord = c_int(3)

# Trigger sources
trigsrcNone = c_int(0)
trigsrcPC = c_int(1)
trigsrcDetectorAnalogIn = c_int(2)

# Trigger types
trigtypeEdge = c_int(0)

# Trigger conditions
trigcondRisingPositive = c_int(0)
trigcondFallingNegative = c_int(1)


class DigilentOscilloscope(Oscilloscope):
    """Oscilloscope implementation for Digilent devices."""

    # AD2 constraints
    MIN_SAMPLE_RATE = 1.0  # 1 Hz
    MAX_SAMPLE_RATE = 100e6  # 100 MHz
    MIN_BUFFER_SIZE = 100
    MAX_BUFFER_SIZE = 8192  # AD2 buffer limit
    PREFERRED_BUFFER_SIZE = 8192

    def __init__(
        self,
        resource_address: str,
        device: DigilentDevice,
        num_channels: int = 2,
    ):
        super().__init__(resource_address, num_channels, device=device)
        self._timebase.offset = 0.0
        # Set initial timebase (10ms/div = 100ms total)
        self.set_timebase_length(100e-3)

    @property
    def hdwf(self) -> c_int:
        """Get the DWF device handle."""
        return self.device.hdwf

    def _get_dwf(self):
        """Get the DWF library."""
        from hakei.instruments.digilent.dwf import get_dwf
        return get_dwf()

    def _apply_timebase_settings(self) -> None:
        """Apply sample rate and buffer size to hardware."""
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogInFrequencySet(self.hdwf, c_double(self._sample_rate))
            dwf.FDwfAnalogInBufferSizeSet(self.hdwf, c_int(self._buffer_size))
            log.debug(
                "Timebase: %.3f ms/div, sample_rate=%.0f Hz, buffer=%d",
                self._timebase.scale * 1000, self._sample_rate, self._buffer_size
            )
            # Restart acquisition if running
            if self._acquisition_state == AcquisitionState.RUNNING:
                dwf.FDwfAnalogInConfigure(self.hdwf, c_int(0), c_int(1))

    def connect(self) -> bool:
        """Initialize the oscilloscope (connection handled by device)."""
        self._configure_acquisition()
        log.info("Digilent oscilloscope ready")
        return True

    def _configure_acquisition(self) -> None:
        """Configure the acquisition parameters."""
        dwf = self._get_dwf()
        if not dwf:
            log.warning("DWF library not available for configuration")
            return

        # Apply current timebase settings to hardware
        self._apply_timebase_settings()

        log.info(
            "Configuring acquisition: timebase=%.3f ms/div, sample_rate=%.0f Hz, buffer=%d",
            self._timebase.scale * 1000, self._sample_rate, self._buffer_size
        )

        # Enable channels by default with ±5V range
        for ch in range(self.num_channels):
            dwf.FDwfAnalogInChannelEnableSet(self.hdwf, c_int(ch), c_int(1))
            dwf.FDwfAnalogInChannelRangeSet(self.hdwf, c_int(ch), c_double(10.0))

        # Configure trigger settings
        self._configure_trigger_mode()

        self._channel_configs[0].enabled = True
        if self.num_channels > 1:
            self._channel_configs[1].enabled = True

    def _configure_trigger_mode(self) -> None:
        """Configure acquisition mode and trigger based on trigger settings."""
        dwf = self._get_dwf()
        if not dwf:
            return

        if self._trigger.enabled:
            # Use single acquisition mode for triggered capture
            dwf.FDwfAnalogInAcquisitionModeSet(self.hdwf, acqmodeSingle)
            
            # Set trigger source to analog input detector
            dwf.FDwfAnalogInTriggerSourceSet(self.hdwf, trigsrcDetectorAnalogIn)
            
            # Set trigger type to edge
            dwf.FDwfAnalogInTriggerTypeSet(self.hdwf, trigtypeEdge)
            
            # Set trigger channel (0-indexed)
            dwf.FDwfAnalogInTriggerChannelSet(self.hdwf, c_int(self._trigger.source - 1))
            
            # Set trigger level
            dwf.FDwfAnalogInTriggerLevelSet(self.hdwf, c_double(self._trigger.level))
            
            # Set trigger hysteresis (helps with noise)
            dwf.FDwfAnalogInTriggerHysteresisSet(self.hdwf, c_double(0.01))
            
            # Set trigger edge condition
            edge_cond = trigcondRisingPositive if self._trigger.edge == TriggerEdge.RISING else trigcondFallingNegative
            dwf.FDwfAnalogInTriggerConditionSet(self.hdwf, edge_cond)
            
            # Set auto timeout based on trigger mode
            if self._trigger.mode == TriggerMode.AUTO:
                dwf.FDwfAnalogInTriggerAutoTimeoutSet(self.hdwf, c_double(1.0))
            else:
                dwf.FDwfAnalogInTriggerAutoTimeoutSet(self.hdwf, c_double(0.0))
            
            log.info(
                "Trigger configured: CH%d, level=%.3fV, edge=%s, mode=%s",
                self._trigger.source, self._trigger.level,
                self._trigger.edge.name, self._trigger.mode.name
            )
        else:
            # Use scan screen mode for free-running acquisition
            dwf.FDwfAnalogInAcquisitionModeSet(self.hdwf, acqmodeScanScreen)
            dwf.FDwfAnalogInTriggerSourceSet(self.hdwf, trigsrcNone)
            log.info("Trigger disabled, using free-running mode")

    def disconnect(self) -> None:
        """Cleanup (disconnection handled by device)."""
        pass

    def reset(self) -> None:
        """Reset the oscilloscope to default settings."""
        self.stop()
        for ch in range(1, self.num_channels + 1):
            self.set_channel_enabled(ch, False)
            self.set_channel_scale(ch, 1.0)
            self.set_channel_offset(ch, 0.0)
        # Default: 10ms/div = 100ms total window (-50ms to +50ms)
        self.set_timebase_scale(10e-3)
        self._timebase.offset = 0.0

    def run(self) -> None:
        """Start continuous acquisition."""
        dwf = self._get_dwf()
        if dwf:
            log.info("Starting acquisition (hdwf=%d)", self.hdwf.value)
            # Start acquisition: reconfigure=0, start=1
            dwf.FDwfAnalogInConfigure(self.hdwf, c_int(0), c_int(1))
        else:
            log.warning("DWF library not available")
        self._acquisition_state = AcquisitionState.RUNNING

    def stop(self) -> None:
        """Stop acquisition."""
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogInConfigure(self.hdwf, c_int(0), c_int(0))
        self._acquisition_state = AcquisitionState.STOPPED

    def single(self) -> None:
        """Perform a single acquisition."""
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogInConfigure(self.hdwf, c_int(1), c_int(1))
        self._acquisition_state = AcquisitionState.SINGLE

    def force_trigger(self) -> None:
        """Force a trigger event."""
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogInTriggerForce(self.hdwf)

    def auto_scale(self) -> None:
        """Automatically configure scales for optimal viewing."""
        for ch in range(1, self.num_channels + 1):
            self.set_channel_enabled(ch, True)
            self.set_channel_scale(ch, 1.0)
        # Default: 10ms/div = 100ms total window
        self.set_timebase_scale(10e-3)

    def set_channel_enabled(self, channel: int, enabled: bool) -> None:
        """Enable or disable a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogInChannelEnableSet(self.hdwf, c_int(ch_idx), c_int(1 if enabled else 0))
        self._channel_configs[ch_idx].enabled = enabled

    def set_channel_coupling(self, channel: int, coupling: Coupling) -> None:
        """Set the input coupling for a channel (AD2 only supports DC)."""
        ch_idx = channel - 1
        self._channel_configs[ch_idx].coupling = coupling

    def set_trigger_enabled(self, enabled: bool) -> None:
        """Enable or disable the trigger."""
        was_enabled = self._trigger.enabled
        self._trigger.enabled = enabled
        
        # Reconfigure acquisition mode if trigger state changed
        if enabled != was_enabled:
            self._configure_trigger_mode()
            # Restart acquisition if it was running
            if self._acquisition_state == AcquisitionState.RUNNING:
                self.run()

    def set_trigger_source(self, channel: int) -> None:
        """Set the trigger source channel."""
        self._trigger.source = channel
        dwf = self._get_dwf()
        if dwf and self._trigger.enabled:
            dwf.FDwfAnalogInTriggerChannelSet(self.hdwf, c_int(channel - 1))

    def set_trigger_mode(self, mode: TriggerMode) -> None:
        """Set the trigger mode."""
        self._trigger.mode = mode
        dwf = self._get_dwf()
        if dwf:
            timeout = 1.0 if mode == TriggerMode.AUTO else 0.0
            dwf.FDwfAnalogInTriggerAutoTimeoutSet(self.hdwf, c_double(timeout))

    def set_trigger_edge(self, edge: TriggerEdge) -> None:
        """Set the trigger edge type."""
        self._trigger.edge = edge
        dwf = self._get_dwf()
        if dwf and self._trigger.enabled:
            edge_cond = trigcondRisingPositive if edge == TriggerEdge.RISING else trigcondFallingNegative
            dwf.FDwfAnalogInTriggerConditionSet(self.hdwf, edge_cond)

    def set_trigger_level(self, level: float) -> None:
        """Set the trigger level (V)."""
        self._trigger.level = level
        dwf = self._get_dwf()
        if dwf:
            dwf.FDwfAnalogInTriggerLevelSet(self.hdwf, c_double(level))

    def get_waveform(self, channel: int) -> WaveformData:
        """Acquire waveform data from a channel."""
        ch_idx = channel - 1
        dwf = self._get_dwf()

        empty_result = WaveformData(
            channel=channel,
            time=np.array([]),
            voltage=np.array([]),
        )

        if not dwf:
            log.warning("CH%d: DWF not available", channel)
            return empty_result

        # Read status and trigger data fetch
        state = c_int()
        dwf.FDwfAnalogInStatus(self.hdwf, c_int(1), byref(state))

        # Handle triggered vs free-running acquisition differently
        if self._trigger.enabled:
            # In triggered mode, wait for Done state (acquisition complete after trigger)
            if state.value != DwfStateDone.value:
                # Still waiting for trigger or acquiring
                log.debug("CH%d: state=%d, waiting for trigger", channel, state.value)
                return empty_result
            
            # Acquisition complete, read the full buffer
            data = (c_double * self._buffer_size)()
            dwf.FDwfAnalogInStatusData(self.hdwf, c_int(ch_idx), data, self._buffer_size)
            raw_samples = np.array(data[:], dtype=np.float64)
            
            # Re-arm for next trigger if running continuously
            if self._acquisition_state == AcquisitionState.RUNNING:
                dwf.FDwfAnalogInConfigure(self.hdwf, c_int(0), c_int(1))
        else:
            # Free-running mode: check if buffer has data
            samples_valid = c_int()
            dwf.FDwfAnalogInStatusSamplesValid(self.hdwf, byref(samples_valid))

            if samples_valid.value == 0:
                log.debug("CH%d: state=%d, no samples yet", channel, state.value)
                return empty_result

            # Read all available samples from buffer
            num_samples = min(samples_valid.value, self._buffer_size)
            data = (c_double * num_samples)()
            dwf.FDwfAnalogInStatusData(self.hdwf, c_int(ch_idx), data, num_samples)
            raw_samples = np.array(data[:], dtype=np.float64)

        samples = raw_samples

        # Calculate time array based on current timebase settings
        total_time = self._timebase.scale * 10
        t_start = self._timebase.offset - total_time / 2
        t_end = self._timebase.offset + total_time / 2
        time = np.linspace(t_start, t_end, len(samples))

        log.debug(
            "CH%d: %d samples, voltage [%.3f, %.3f]",
            channel, len(samples), samples.min(), samples.max()
        )

        return WaveformData(
            channel=channel,
            time=time,
            voltage=samples,
            sample_rate=self._sample_rate,
            num_points=len(samples),
        )
