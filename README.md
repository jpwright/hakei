# Hakei - Electronic Bench Equipment Controller

A Python application for visualization and control of electronic bench equipment including oscilloscopes, power supplies, and waveform generators.

## Requirements

- Python 3.9+
- dearpygui

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

## Supported Equipment

- Oscilloscopes
- DC Power Supplies
- Waveform/Function Generators
- Digital Multimeters (planned)

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
│   ├── __init__.py
│   ├── __main__.py      # Application entry point
│   └── ui/
│       ├── __init__.py
│       ├── layout.py    # Tiling window manager
│       ├── theme.py     # UI theming and styling
│       ├── menu.py      # Menu bar setup
│       ├── device_panel.py
│       └── views/
│           ├── __init__.py
│           ├── oscilloscope.py
│           ├── power_supply.py
│           └── waveform_gen.py
├── docs/                # Quartodoc documentation
├── pyproject.toml
└── README.md
```
