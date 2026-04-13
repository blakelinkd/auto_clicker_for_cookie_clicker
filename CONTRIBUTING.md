# Contributing

## Development Setup

```bash
pip install -r requirements.txt
python main.py
```

## Code Style

- PEP 8 with 4-space indentation
- `snake_case` for functions/variables, `PascalCase` for classes
- No inline styles in Qt HUD (use `qt_hud/styles/theme.py`)

## Testing

```bash
python -m pytest -q
```

Run a specific module:
```bash
python -m pytest -q tests/test_stock_trader.py
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests for new behavior
4. Ensure tests pass
5. Open a pull request

## Areas for Contribution

- Game automation features (buildings, spells, garden, etc.)
- UI/HUD improvements
- Bug fixes and edge case handling
- Test coverage