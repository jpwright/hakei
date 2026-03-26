# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Hakei** is a Python GUI application for controlling and visualizing laboratory electronic instruments (oscilloscopes, power supplies, waveform generators, etc.). It uses DearPyGui (immediate mode GUI) and is intended as a cross-platform replacement for vendor-specific GUIs like Keysight BenchVue.

## Commands

```bash
# Run the application
uv run hakei
uv run hakei --log-level DEBUG

# Lint
uv run ruff check hakei/
uv run ruff check --fix hakei/

# Install dev dependencies
uv pip install -e ".[dev]"

# Build docs (requires Quarto installed separately)
uv run quartodoc build
quarto preview docs
```

There are no tests currently.

## Architecture

### Instrument Abstraction Layer (`hakei/instruments/`)

Two distinct base types:
- **`Instrument`** (`base.py`): A single instrument function (oscilloscope, power supply, etc.). Has `ConnectionState`, `connect()`/`disconnect()`, and lazy-loads its UI panel and config class via string import paths stored on the class.
- **`Device`** (`device.py`): A hardware unit containing multiple instruments (e.g., Analog Discovery 2 has oscilloscope + power supply + waveform gen). Manages instrument activation/deactivation independently.

Concrete implementations live in `instruments/digilent/` (Digilent Waveforms SDK) and `instruments/dummy/` (simulation for UI development). VISA instruments are handled generically via PyVISA.

**Device Registry** (`registry.py` + `registry.yaml`): YAML-based lookup mapping manufacturer/model strings to device classes and their associated instrument classes. This is the extension point for adding new hardware.

**Scanner transports** (`instruments/scanner/`): Pluggable discovery backends (VISA, Digilent SDK, Dummy). `get_scanner()` aggregates all transports.

### UI Layer (`hakei/ui/`)

- **`layout.py` — `TilingManager`**: Row-based tiling window manager. Instrument panels register here and are allocated height dynamically. Handles drag-to-reorder between drop zones. This is the core of the UI composition.
- **`instrument_panel.py`**: Left sidebar — scan, select, and connect instruments. Spawns instrument view panels and registers them with TilingManager.
- **`views/`**: Per-instrument-type UI panels (`OscilloscopePanel`, `PowerSupplyPanel`, `WaveformGeneratorPanel`), all extending `BasePanel`.
- **`theme.py`**: DearPyGui dark theme + DPI detection (reads GDK_SCALE, QT_SCALE_FACTOR, xrdb).

### Configuration (`hakei/config.py`, `hakei/settings.py`)

- **`config.py`**: Pydantic models for full application state (window size, panel heights, per-instrument settings). Saved to `~/.config/hakei/default.hakei` as JSON. Uses discriminated unions for instrument config types.
- **`settings.py`**: Lightweight YAML-persisted runtime settings (`~/.config/hakei/settings.yaml`). Supports change callbacks (e.g., toggling FPS display).

### Application Entry Point (`hakei/__main__.py`)

Click CLI → DearPyGui context → theme/menu/panel setup → main event loop. The loop manually checks for window drag events, runs instrument update ticks, and renders frames.

## Key Conventions

- Line length: 100 characters (ruff)
- Python target: 3.8+ (ruff), runtime requires 3.9+
- Instrument panel/config class references are stored as dotted import path strings on the class, then lazily imported — this avoids circular imports between `instruments/` and `ui/`.
- `dearpygui` uses tag-based item references (strings/ints), not object references. UI state is queried imperatively.
