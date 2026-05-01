# SmartGardn ET₀ — Home Assistant Custom Integration

**Scientific irrigation control based on FAO-56 Penman-Monteith ET₀ calculations with daily NFK (soil water balance) per zone and intelligent rain-skip scheduling.**

[![Language: Python](https://img.shields.io/badge/Language-Python-blue)](https://www.python.org/)
[![Home Assistant: 2024.10+](https://img.shields.io/badge/Home%20Assistant-2024.10+-green)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![HACS: Custom Integration](https://img.shields.io/badge/HACS-Custom%20Integration-blue)](https://hacs.xyz/)
[![GitHub: Presley2/ha-smartgardn](https://img.shields.io/badge/GitHub-Presley2%2Fha--smartgardn-gray)](https://github.com/Presley2/ha-smartgardn)

## 🌾 Features

### Core Irrigation Calculation
- **FAO-56 Penman-Monteith ET₀** — scientifically accurate reference evapotranspiration (vendored, no PyPI dependencies)
- **Daily NFK (Nutzbare Feldkapazität)** soil water balance per zone with 365-day rolling history
- **Grünlandtemperatursumme (GTS)** — growing-degree sum with monthly weighting (German standard)
- **Multi-method ET₀ fallback** — FAO-56 PM → Hargreaves → last_known → 0
- **Flexible weather sensors** — single current-value or min/max sensors with automatic history-based aggregation

### Irrigation Modes (per zone)
- **Aus (Off)** — zone disabled
- **Semi-Automatik** — fixed schedule (e.g., every Tuesday at 19:00)
- **Voll-Automatik** — threshold-based (water when NFK falls below target)
- **Ansaat** — intensive seed watering (hourly intervals, time-limited)

### Advanced Features
- **DWD 3-day forecast** — automatic rain-skip scheduling (Deutsches Wetterdienst MOSMIX-S)
- **Intelligent rain skip** — configurable threshold (1-50 mm) to delay watering when rain expected
- **History visualization** — 30-day NFK/ETc/rain/irrigation curves with 3-day forecast preview
- **Cycle & Soak (C&S)** — multi-cycle watering with configurable pause between cycles
- **Frost lock** — automatic halt when T_min < threshold
- **Hot-reload safe** — code updates without HA restart (all state in config entry + storage)
- **Power-loss recovery** — resumes interrupted zones after unexpected restarts
- **Failsafe** — 5-minute watchdog to prevent stuck valves
- **Trafo sequencing** — optional transformer actuation with intelligent on/off logic
- **Dry-run mode** — test configuration without opening valves

### UI
- **Overview Card** — real-time zone status (NFK%, ETc, rain, next scheduled start)
- **Settings Card** — adjust all parameters with sliders and selectors
- **History Card** — 30-day trend curves + 3-day forecast preview
- **Ansaat Card** — seed watering timeline and intensive germination schedule

---

## 🚀 Installation

### Via HACS (Recommended)
1. Settings → Devices & Services → **HACS**
2. Click **Custom repositories**
3. Add URL: `https://github.com/Presley2/ha-smartgardn`
4. Select category: **Integration**
5. Search for "SmartGardn ET₀" → Install → **Restart Home Assistant**
6. Settings → Devices & Services → **Create Integration** → "SmartGardn ET₀"

### Manual Install
1. Download this repository
2. Copy `custom_components/smartgardn_et0/` to `<ha-config>/custom_components/`
3. Restart Home Assistant
4. Settings → Devices & Services → **Create Integration** → "SmartGardn ET₀"

---

## ⚙️ Configuration

### Setup Flow (5 steps)

**1. Installation Info**
- Name (e.g., "Hauptanlage")
- GPS coordinates (map selector)
- Elevation (m)

**2. Weather Sensors**
- Temperature (required; single current-value sensor — history-based min/max auto-calculated)
- Humidity, solar radiation, wind, rainfall (all optional)
- Solar sensor type selector (W/m², Lux, PAR, none)

**3. Hardware**
- Transformer/24V switch entity (optional; if omitted, zones control valves directly)
- Frost protection threshold (°C)

**4. Zones** (add one or more)
- Zone name, type (lawn/drip), valve entity
- Soil type (sand, sandy loam, loam, clay loam, clay) → auto-calculates max NFK
- Root depth, Kc, thresholds, flow rate, initial NFK
- Add more zones or finish

**5. Forecast** (options, optional)
- Enable DWD forecast (3-day ET₀ + rain prognosis)
- Rain skip threshold (mm; default 10)
- Override coordinates (for border regions)

---

## 📊 Entities Created

### Per Zone
- `sensor.{zone}_nfk` — current soil water content (mm)
- `sensor.{zone}_nfk_prozent` — NFK as % of capacity
- `sensor.{zone}_etc_heute` — today's crop evapotranspiration (mm)
- `sensor.{zone}_regen_heute` — rainfall today (mm)
- `sensor.{zone}_beregnung_heute` — irrigation amount today (mm)
- `sensor.{zone}_naechster_start` — next scheduled irrigation (timestamp)
- `select.{zone}_modus` — irrigation mode (aus/semi/voll/ansaat)
- `number.{zone}_manuelle_dauer` — manual irrigation duration (min)
- `button.{zone}_start` — manual start button
- `switch.{zone}_montag` (etc.) — weekday enable/disable
- `switch.{zone}_aktiv` — zone enable/disable

### Global
- `sensor.{name}_et0_fao56` — today's reference ET₀ (FAO-56 PM)
- `sensor.{name}_et0_hargreaves` — ET₀ fallback method
- `sensor.{name}_gts` — growing-degree sum (current season)
- `sensor.{name}_et0_prognose_morgen` — ET₀ tomorrow (DWD forecast)
- `sensor.{name}_regen_prognose_morgen` — rain tomorrow (DWD forecast)
- `switch.{name}_dry_run` — test mode (no valve actuation)
- `binary_sensor.{name}_frost_warnung` — frost warning

---

## 🔧 Services

```yaml
# Manual zone start
service: smartgardn_et0.start_zone
data:
  zone: select.<entry_id>_<zone_id>_modus
  dauer_min: 30

# Stop all zones
service: smartgardn_et0.stop_all

# Trigger daily calculation (ET₀, NFK, scheduling)
service: smartgardn_et0.recalculate_now
```

---

## 📈 How It Works

**Daily Calculation (00:05 UTC)**
1. Read weather sensors (temperature min/max, humidity, solar, wind, rain)
2. Calculate ET₀ via selected method (FAO-56 PM, Hargreaves, or fallback)
3. For each zone: calculate ETc = ET₀ × Kc, update NFK balance
4. Check if watering needed (NFK < threshold)
5. If yes, check DWD forecast for next 2 days
6. If rain ≥ threshold, delay irrigation by 1-2 days
7. If rain < threshold, start immediately (for Voll-Automatik)
8. For Semi-Automatik, find next enabled weekday without rain
9. Schedule zone start via `async_track_point_in_time`
10. Store all data (365-day history per zone)

**Queue & Sequencing**
- Zones in queue are processed sequentially (not parallel)
- Trafo turns ON → wait 0.5s → valve opens
- Irrigation runs for configured duration
- Valve closes → wait 0.5s → trafo turns OFF (if no other zones queued)
- Cycle & Soak: repeat cycle X times with pause between

---

## 🌍 Weather Integration

### Supported Sensors
- **Home Assistant built-in**: weather.*, sensor.* entities
- **DWD Integration** (native): high-accuracy German weather data
- **Open-Meteo** (HACS): global, free, no API key
- **OpenWeatherMap**: commercial service
- **Template sensors**: custom min/max aggregation

### Solar Sensor Types
- **W/m²** — direct conversion
- **Lux** — divided by 54000 (approx 1 lux = 0.000018 W/m²)
- **PAR** (µmol/m²/s) — multiplied by 0.51
- **None** — ET₀ falls back to Hargreaves (temp-only)

---

## 🛠️ Development

### Local Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

### Code Style
- Python 3.10+
- Type hints mandatory
- Ruff + mypy linting
- 43+ pytest tests (coordinator, ET₀ calcs, water balance, etc.)

### Testing
```bash
# Run all tests
python -m pytest tests/

# Single test
python -m pytest tests/test_coordinator.py::test_daily_calc -v

# Coverage
python -m pytest tests/ --cov=custom_components/smartgardn_et0
```

---

## 📚 Documentation

- [CONTRIBUTING](CONTRIBUTING.md) — dev setup, PR guidelines
- [CHANGELOG](CHANGELOG.md) — release history
- [Deployment Guide](docs/DEPLOYMENT.md) — SMB deployment for HA on Hetzner
- [Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md) — technical details
- [Third-Party Licenses](THIRD_PARTY_LICENSES.md) — vendor attribution and license compliance

---

## 🐛 Issues & Support

Found a bug? Have a feature request?
- **Report issues**: [GitHub Issues](https://github.com/Presley2/ha-smartgardn/issues)
- **Discuss**: [Home Assistant Community](https://community.home-assistant.io/)

---

## 📄 License

MIT License — [Full Text](LICENSE)

### Third-Party Attribution

This project uses [PyETo](https://github.com/woodcrafty/PyETo) (BSD 3-Clause License) for FAO-56 Penman-Monteith ET₀ calculations. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for complete license information and compatibility details.

---

## ✨ Credits

**SmartGardn ET₀** — Precision irrigation for Germany, Austria, and Switzerland  
Built with Home Assistant + scientific weather data  
v0.1.0 — May 2026

**Powered by:**
- FAO-56 Penman-Monteith (vendored PyETo)
- DWD MOSMIX-S forecast (via brightsky.dev)
- Home Assistant 2024.10+
