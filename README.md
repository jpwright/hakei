# hakei

hakei is a cross-platform control panel for laboratory instruments, built using [dearpygui](https://github.com/hoffstadt/DearPyGui). It's meant as a general purpose replacement to vendor-specific GUIs like Keysight BenchVue, National Instruments NI-SCOPE, Liquid Instruments MokuOS, etc.

> [!caution]
> hakei is in very early development and is not ready for serious use!

![example screenshot](docs/example.png)

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

## Project Structure

```
hakei/
├── hakei/
│   ├── __main__.py           # Application entry point
│   ├── config.py             # Configuration save/load (.hakei files)
│   ├── instruments/          # Instrument abstraction layer
│   │   ├── scanner/          # Instrument discovery (VISA, Digilent, etc.)
│   │   ├── digilent/         # Digilent Waveforms SDK support
│   │   └── dummy/            # Simulated instruments for testing
│   └── ui/
│       ├── layout.py         # Tiling window manager
│       └── views/            # Instrument UI panels
├── docs/                     # Quartodoc documentation
└── pyproject.toml
```
