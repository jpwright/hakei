# hakei

hakei is a cross-platform control panel for laboratory instruments, built using [dearpygui](https://github.com/hoffstadt/DearPyGui). It's meant as a general purpose replacement to vendor-specific GUIs like Keysight BenchVue, National Instruments NI-SCOPE, Liquid Instruments MokuOS, etc.

## Usage

### With uv (recommended)

```bash
uv run hakei
```

### With pip

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
hakei
```

## Development

### Install dev dependencies

```bash
uv pip install -e ".[dev]"
```

### Linting

```bash
uv run ruff check hakei/
uv run ruff check --fix hakei/
```

### Documentation

Generate API documentation (requires [Quarto](https://quarto.org/)):

```bash
uv run quartodoc build
quarto preview docs
```

## Concepts

### Devices vs Instruments

hakei distinguishes between **Devices** and **Instruments**:

- **Device**: A physical piece of hardware (e.g., Digilent Analog Discovery 2, a multi-function bench instrument). A device has a single connection interface and may contain multiple instruments.
- **Instrument**: A logical function within a device (e.g., oscilloscope, waveform generator, power supply). Some devices contain only one instrument (standalone instruments), while others contain multiple.

When you connect to a multi-function device, you can choose which instruments to activate at any time.

## Project Structure

```
hakei/
├── hakei/
│   ├── __init__.py
│   ├── __main__.py              # Application entry point
│   ├── config.py                # Configuration save/load
│   ├── instruments/             # Instrument abstraction layer
│   │   ├── __init__.py
│   │   ├── base.py              # Base instrument class
│   │   ├── device.py            # Device abstraction (multi-instrument)
│   │   ├── oscilloscope.py      # Oscilloscope interface
│   │   ├── power_supply.py      # Power supply interface
│   │   ├── waveform_generator.py
│   │   ├── registry.py          # Instrument registry
│   │   ├── registry.yaml        # Known instruments/devices
│   │   ├── scanner/             # Instrument discovery
│   │   │   ├── __init__.py      # Main scanner class
│   │   │   ├── base.py          # Scanner transport interface
│   │   │   ├── digilent.py      # Digilent device scanner
│   │   │   ├── dummy.py         # Dummy instrument scanner
│   │   │   └── visa.py          # VISA instrument scanner
│   │   ├── digilent/            # Digilent Waveforms support
│   │   │   ├── __init__.py
│   │   │   ├── dwf.py           # DWF SDK loader (ctypes)
│   │   │   └── scanner.py       # Device enumeration
│   │   └── dummy/               # Dummy/simulated instruments
│   │       ├── __init__.py
│   │       ├── device.py        # Multi-function dummy device
│   │       ├── oscilloscope.py
│   │       ├── power_supply.py
│   │       └── waveform_generator.py
│   └── ui/
│       ├── __init__.py
│       ├── fdialog.py           # File dialog (vendored)
│       ├── images/              # File dialog icons
│       ├── instrument_panel.py  # Instrument connection sidebar
│       ├── layout.py            # Tiling window manager
│       ├── menu.py              # Menu bar setup
│       ├── theme.py             # UI theming and styling
│       └── views/               # Instrument UI panels
│           ├── __init__.py
│           ├── base.py          # Base panel class
│           ├── oscilloscope.py
│           ├── power_supply.py
│           └── waveform_gen.py
├── docs/                        # Quartodoc documentation
├── pyproject.toml
├── _quarto.yml
└── README.md
```
