# Hakei - Electronic Bench Equipment Controller

A Python application for visualization and control of electronic bench equipment including oscilloscopes, power supplies, and waveform generators.

## Requirements

- Python 3.8+
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

## Project Structure

```
hakei/
├── hakei/
│   ├── __init__.py
│   ├── __main__.py      # Application entry point
│   └── ui/
│       ├── __init__.py
│       ├── theme.py     # UI theming and styling
│       ├── menu.py      # Menu bar setup
│       ├── device_panel.py
│       └── views/
│           ├── __init__.py
│           ├── oscilloscope.py
│           ├── power_supply.py
│           └── waveform_gen.py
├── pyproject.toml
├── requirements.txt
└── README.md
```
