# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-05-01

### Fixed
- **HACS metadata consistency** — unified repository links across README, `info.md`, and integration metadata
- **Release workflow output reference** — added missing `id: create_release` so release asset upload can resolve `upload_url`
- **Coordinator storage initialization** — ensure per-zone storage schema and defaults are created for configured zones
- **Power-loss recovery persistence** — persist and clear `running_since` / remaining runtime state on start/stop/frost paths
- **Dry-run behavior** — prevent physical valve/trafo switching while dry-run mode is enabled
- **Rain-skip scheduling timing** — load forecast before computing next start times so skip logic uses fresh forecast data
- **Service/API alignment** — expose `recalculate_now` service in runtime registration and service docs

## [0.2.0] - 2026-05-01

### Fixed
- **CRITICAL: Frost lock bug** — now works with both `temp_entity` and legacy `temp_min_entity` configs
- **CRITICAL: Unsafe dict access** — add safe zone config checks to prevent crashes during reconfiguration
- **CRITICAL: Entity ID parsing** — replace string-based parsing with Base64 encoding for robustness
- **CRITICAL: Cycle & Soak blocking** — replace `asyncio.sleep()` with event-based scheduling to keep coordinator responsive
- **CRITICAL: Startup recovery race condition** — improve thread-safety with proper dict access patterns
- **Calculation: LUX sensor conversion** — fix 1000× underestimation (was `1/54000`, now `1/54`)
- **Calculation: PAR sensor accuracy** — improve conversion from `0.51` to `0.0219` (more physically accurate)
- **Recorder timeout** — add 5-second timeout to prevent coordinator from blocking on slow database
- **Input validation** — enhance config flow with longitude range, elevation bounds, Kc plausibility, zone uniqueness checks
- **Manifest** — add lovelace resources section with 4 custom cards
- **Test updates** — fix repairs tests for Base64 encoding, update C&S test for event scheduling

### Security
- Implement safe dictionary access throughout coordinator to prevent KeyError crashes
- Add null-checks for entity configuration during runtime operations

## [0.1.0] - 2026-05-01

### Added
- **FAO-56 Penman-Monteith ET₀ calculations** — scientifically accurate reference evapotranspiration with daily NFK (Nutzbare Feldkapazität) soil water balance per zone
- **365-day rolling history** — track soil water content, ET₀, rainfall, and irrigation over one year per zone
- **Grünlandtemperatursumme (GTS)** — growing-degree sum calculation with monthly weighting (German standard)
- **Multi-method ET₀ fallback** — FAO-56 PM → Hargreaves → last_known → 0
- **Flexible weather sensors** — single current-value temperature sensor with automatic history-based min/max calculation
- **DWD 3-day forecast** — integration with Deutsches Wetterdienst MOSMIX-S via brightsky.dev (free, no API key)
- **Intelligent rain-skip scheduling** — configurable threshold (1-50 mm) to delay irrigation when rain expected
- **History visualization** — 30-day NFK/ETc/rain/irrigation curves with 3-day forecast preview in custom Lovelace card
- **Four irrigation modes per zone**:
  - Aus (Off) — zone disabled
  - Semi-Automatik — fixed schedule (weekday selection)
  - Voll-Automatik — threshold-based (water when NFK falls below target)
  - Ansaat — intensive seed watering (hourly intervals, time-limited)
- **Cycle & Soak (C&S)** — multi-cycle watering with configurable pause between cycles
- **Frost lock** — automatic halt when T_min < threshold
- **Optional transformer sequencing** — intelligent trafo on/off with 0.5s delay
- **Zone types** — lawn (ET₀-based) or drip (time-controlled)
- **Manual irrigation control** — start zones manually with pre-set duration
- **Power-loss recovery** — resumes interrupted zones after unexpected restarts
- **Failsafe watchdog** — 5-minute check to prevent stuck valves
- **Hot-reload safe** — code updates without Home Assistant restart (all state in config entry + storage)
- **Dry-run mode** — test configuration without opening valves
- **Full HA configuration flow** — 5-step setup with map-based location selector
- **Options flow** — modify settings at runtime without re-setup (weather sensors, forecast, thresholds)
- **Multiple UI cards**:
  - Overview Card — real-time zone status (NFK%, ETc, rain, next scheduled start)
  - Settings Card — adjust all parameters with sliders and selectors
  - History Card — 30-day trend curves + 3-day forecast preview
  - Ansaat Card — seed watering timeline and intensive germination schedule
- **Comprehensive entity creation**:
  - Per-zone sensors: NFK (mm + %), ETc, rainfall, irrigation, next start timestamp
  - Per-zone controls: mode selector, manual duration, start button, weekday toggles, enable/disable
  - Global sensors: ET₀ (FAO-56 + Hargreaves fallback), GTS, forecast (ET₀ + rain for 3 days)
  - Global controls: dry-run mode, frost warning
- **Services**:
  - `start_zone` — manual zone start with custom duration
  - `stop_all` — stop all running zones immediately
  - `recalculate_now` — trigger daily calculation outside schedule
- **Scientific validation** — all calculations follow FAO-56 standard and German agricultural practices
- **German localization** — full UI and documentation in German (Deutsch)
- **Solar sensor flexibility** — supports W/m² (direct), Lux (approx 1 lux = 0.000018 W/m²), PAR µmol/m²/s (×0.51)
- **Documentation**:
  - Comprehensive README with features, installation (HACS + manual), configuration, entities, services, how-it-works
  - Contributing guidelines with dev setup (Python venv, pytest, ruff, mypy)
  - Implementation summary with technical details
  - Deployment guide for Hetzner/SMB setups
  - Complete Home Assistant integration manifest and localization

### Fixed
- None (initial release)

### Changed
- None (initial release)

### Removed
- None (initial release)

---

## Future Releases

### [Planned]
- Advanced zone scheduling with holiday overrides
- Soil moisture sensor integration (skip ET₀ calc if soil probe available)
- Plant-specific Kc curve libraries (vegetable, fruit, turf varieties)
- MQTT integration for remote monitoring
- Statistics dashboard with seasonal water use
- Integration with commercial weather APIs (OpenWeatherMap, Weatherflow)
- Mobile app push notifications for irrigation events
