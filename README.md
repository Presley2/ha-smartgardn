# Irrigation ET₀ — Home Assistant Integration

**Scientific irrigation control based on FAO-56 Penman-Monteith ET₀ calculations with daily NFK (soil water balance) per zone.**

![Language: Python](https://img.shields.io/badge/Language-Python-blue)
![Home Assistant: 2024.10+](https://img.shields.io/badge/Home%20Assistant-2024.10+-green)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)
![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-blue)

## Features

### 🌾 Core Irrigation Control
- **FAO-56 Penman-Monteith ET₀ calculation** with vendored PyETo (no external Python dependencies)
- **Daily NFK (Nutzbare Feldkapazität) soil water balance** per zone with historical tracking
- **Grünlandtemperatursumme (GTS)** growing-degree sum with monthly weighting
- **5 irrigation zones** with HomeMatic DRS8 valve actuators (or any HA switch entity)
- **Multi-method ET₀ fallback chain**: FAO56 PM → Hargreaves → last_known → 0

### 🎯 Irrigation Modes
- **Aus (Off)**: Zone disabled
- **Semi-Automatik**: Scheduled irrigation at fixed time
- **Voll-Automatik**: Threshold-based irrigation when NFK falls below target
- **Ansaat**: Intensive seed watering with hourly intervals (time-limited, e.g., 21 days)

### 🔄 Advanced Features
- **Cycle & Soak (C&S)**: Irrigation in multiple cycles with configurable pauses for better soil penetration
- **Frost lock**: Automatically blocks all irrigation when T_min drops below threshold
- **Hot-reload safe**: Update integration without restarting Home Assistant (all state in config entry)
- **Dry-run mode**: Test configuration without opening valves
- **Power-loss recovery**: Resumes interrupted zones after power outages via storage persistence

## Installation & Configuration

Via HACS: Settings → Devices & Services → HACS → Integrations → Search "Irrigation ET₀" → Install → Restart HA

Then: Settings → Devices & Services → Create Integration → "Irrigation ET₀"

Configuration steps:
1. Installation location (name, GPS coordinates, elevation)
2. Weather sensors (temperature, rainfall, optional: solar radiation, humidity, wind)
3. Hardware (trafo valve switch, frost threshold)
4. Zones (name, soil type, root depth, zone switch entity)

## Usage

- **Overview Card**: Real-time zone status with NFK%, ETc, rain, next start
- **Settings Card**: Adjust all zone parameters with sliders
- **History Card**: 7-day water balance trends
- **Ansaat Card**: Seed watering timeline for intensive germination watering

Services:
- `smartgardn_et0.start_zone(zone, dauer_min)` — Manual start
- `smartgardn_et0.stop_zone(zone)` — Manual stop
- `smartgardn_et0.stop_all()` — Emergency stop all
- `smartgardn_et0.import_nodered_data(data)` — Migrate from Node-RED

## Development

Tests: `python -m pytest tests/ -v` (43+ tests)

Structure:
- `custom_components/smartgardn_et0/` — Main integration (Python)
- `src/cards/` — Lovelace card source (Lit + JavaScript)
- `dist/cards/` — Built cards for distribution
- `.github/workflows/` — CI/CD (tests, linting, releases)

## License

MIT License

## Author

Michael Richter — [GitHub](https://github.com/michaelrichter)

v0.1.0 — 2026-05-01
