# Contributing to SmartGardn ET₀

Thank you for your interest in contributing! This guide explains how to set up the development environment, run tests, and submit pull requests.

---

## Development Setup

### Prerequisites
- Python 3.10+
- Home Assistant development environment (optional for unit tests)
- Git

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Presley2/ha-smartgardn
   cd ha-smartgardn
   ```

2. **Create a Python virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

---

## Code Style

This project enforces consistent code style using automated tools:

- **Type hints:** Mandatory for all functions and variables
- **Linting:** [Ruff](https://github.com/astral-sh/ruff) (Python linter)
- **Type checking:** [mypy](https://www.mypy-lang.org/)
- **Testing:** [pytest](https://pytest.org/)

### Run linting and type checks:
```bash
ruff check custom_components/smartgardn_et0/
mypy custom_components/smartgardn_et0/ --ignore-missing-imports
```

### Format code:
```bash
ruff format custom_components/smartgardn_et0/
```

---

## Testing

The project includes 43+ unit tests covering:
- Coordinator behavior (daily calculations, queueing, scheduling)
- ET₀ calculations (FAO-56, Hargreaves, fallback)
- Water balance (NFK updates, threshold checks)
- Irrigation scheduling (Voll-Automatik, Semi-Automatik, rain-skip)
- Config flow validation
- Entity creation and updates

### Run all tests:
```bash
python -m pytest tests/ -v
```

### Run a single test:
```bash
python -m pytest tests/test_coordinator.py::test_daily_calc -v
```

### Generate coverage report:
```bash
python -m pytest tests/ --cov=custom_components/smartgardn_et0 --cov-report=html
```

---

## Before Submitting a Pull Request

1. **Ensure your branch is up to date:**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Run the full test suite** — all tests must pass:
   ```bash
   python -m pytest tests/ -v
   ```

3. **Check code style:**
   ```bash
   ruff check custom_components/smartgardn_et0/
   mypy custom_components/smartgardn_et0/ --ignore-missing-imports
   ```

4. **Format your code:**
   ```bash
   ruff format custom_components/smartgardn_et0/
   ```

5. **Test manually** in a Home Assistant instance:
   - Deploy via HACS or manual install
   - Create a config entry and verify setup flow
   - Test at least one full irrigation cycle
   - Check that entities appear and update correctly

---

## Pull Request Guidelines

When submitting a PR, please:

1. **Write a clear title** — use imperative mood (e.g., "Add DWD forecast caching")
2. **Provide a detailed description:**
   - What problem does this solve?
   - How is it implemented?
   - Any breaking changes?
3. **Reference related issues** — if fixing a bug, link the issue
4. **Ensure tests pass** — include tests for new features or bug fixes
5. **Update documentation** — if behavior changed, update README or implementation docs

---

## Areas for Contribution

We welcome contributions in these areas:

### High Priority
- Bug fixes (always welcome)
- Improved error handling and logging
- Performance optimizations
- Test coverage expansion

### Medium Priority
- Additional weather sensor integrations
- Zone-type expansion (e.g., tree irrigation)
- Localization (new languages)
- Documentation improvements

### Lower Priority
- UI enhancements (requires Lovelace card changes)
- Alternative ET₀ calculation methods
- Advanced scheduling features

---

## Questions?

- **Bug reports**: [GitHub Issues](https://github.com/Presley2/ha-smartgardn/issues)
- **Discussions**: [Home Assistant Community](https://community.home-assistant.io/)
- **General questions**: Check the [README](README.md) and [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)

---

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.
