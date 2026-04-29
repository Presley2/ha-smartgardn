# irrigation_et0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Home Assistant Custom Component (`irrigation_et0`) for irrigation control via FAO-56 Penman-Monteith ET₀ + daily NFK soil-water-balance, with 4 Lovelace cards, HACS-ready, no HA-restart on updates.

**Architecture:** DataUpdateCoordinator pattern, all state inside config entry (hot-reload safe), per-zone Device Registry, vendored PyETo, HA Storage with versioned schema, async event-driven scheduling, dry-run-default for safe onboarding.

**Tech Stack:** Python 3.12+, Home Assistant 2024.10+, pytest-homeassistant-custom-component, vendored PyETo, vanilla JS Lovelace card, HACS, GitHub Actions.

**Spec:** [`docs/superpowers/specs/2026-04-28-irrigation-et0-design.md`](../specs/2026-04-28-irrigation-et0-design.md)

---

## How to use this plan

- Each Phase = a logical milestone, end with a green CI run + commit + tag.
- Each Task = one focused PR-sized unit with TDD steps.
- TDD discipline: write the failing test → see it fail → minimal code → see it pass → commit.
- When the spec is the source of truth (e.g., entity tables, scheduling logic), reference the spec section rather than restating.
- All file paths are relative to the repo root `/Users/michael/irrigation-ha/`.

---

## File Structure (final state)

```
irrigation-ha/
├── custom_components/
│   ├── irrigation_et0/
│   │   ├── __init__.py
│   │   ├── const.py
│   │   ├── manifest.json
│   │   ├── services.yaml
│   │   ├── config_flow.py
│   │   ├── coordinator.py
│   │   ├── _pyeto_vendor.py        # vendored ET formulas (no external dep)
│   │   ├── et0_calculator.py
│   │   ├── water_balance.py
│   │   ├── gts_calculator.py
│   │   ├── storage.py
│   │   ├── recovery.py
│   │   ├── diagnostics.py
│   │   ├── repairs.py
│   │   ├── sensor.py
│   │   ├── binary_sensor.py
│   │   ├── switch.py
│   │   ├── select.py
│   │   ├── number.py
│   │   ├── button.py
│   │   ├── time.py
│   │   └── translations/
│   │       ├── de.json
│   │       └── en.json
│   └── irrigation_et0_card/
│       ├── irrigation-et0-card.js
│       └── irrigation-et0-card-editor.js
├── tests/
│   ├── conftest.py
│   ├── test_pyeto_vendor.py
│   ├── test_et0_calculator.py
│   ├── test_water_balance.py
│   ├── test_gts_calculator.py
│   ├── test_storage.py
│   ├── test_storage_migration.py
│   ├── test_coordinator.py
│   ├── test_recovery.py
│   ├── test_config_flow.py
│   ├── test_services.py
│   ├── test_repairs.py
│   ├── test_diagnostics.py
│   ├── test_unload_reload_cycle.py
│   ├── test_card_data_contract.py
│   └── fixtures/
│       └── fao_annex6_examples.json
├── .github/workflows/
│   ├── ci.yml
│   ├── hacs-validate.yml
│   └── release.yml
├── docs/superpowers/
│   ├── specs/2026-04-28-irrigation-et0-design.md
│   └── plans/2026-04-29-irrigation-et0-implementation.md
├── hacs.json
├── pyproject.toml
├── README.md
├── info.md
├── LICENSE
└── .gitignore
```

---

## Phase 1 — Foundation & Calculation Modules

**Goal:** Pure-Python calculation core + storage, fully unit-tested, no HA dependency yet. Buildable and testable without HA.

### Task 1.1: Repo skeleton & dev tooling

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `LICENSE`, `README.md`, `info.md`, `tests/conftest.py`

- [ ] Create `pyproject.toml` with build-system, dependencies (pytest, pytest-asyncio, pytest-cov, pytest-homeassistant-custom-component, ruff, mypy, freezegun, homeassistant), and tool config (ruff line-length 100, mypy strict, pytest asyncio mode auto, coverage source `custom_components.irrigation_et0`)
- [ ] Create `.gitignore` covering Python, `.venv/`, `__pycache__/`, `.pytest_cache/`, `htmlcov/`, `*.egg-info/`, IDE files
- [ ] Create `LICENSE` (MIT) with current year + user name
- [ ] Create `README.md` skeleton (sections: About, Features, Installation via HACS, Configuration, Cards, Services, Troubleshooting — content TBD in Phase 8)
- [ ] Create `info.md` placeholder (HACS landing page)
- [ ] Create `tests/conftest.py` with HA test fixtures (import `pytest_homeassistant_custom_component` plugin)
- [ ] Run `uv venv && uv sync` to verify pyproject installs cleanly
- [ ] Commit: `chore: repo skeleton with pyproject, license, gitignore`

### Task 1.2: Constants module

**Files:**
- Create: `custom_components/irrigation_et0/const.py`

- [ ] Write `const.py` with: `DOMAIN = "irrigation_et0"`, `STORAGE_KEY`, `STORAGE_VERSION = 1`, all event names from spec §16 (`EVENT_ZONE_STARTED`, `EVENT_ZONE_FINISHED`, `EVENT_FROST_LOCK`, `EVENT_FROST_RELEASE`, `EVENT_CALC_DONE`, `EVENT_FALLBACK_ACTIVE`, `EVENT_UNEXPECTED_STATE`), all service names from spec §15, soil-type → mm/dm dict (from spec §3 step 4), default Kc per Zonentyp, default frost threshold 4°C, scheduling magic numbers (TRAFO_DELAY_S=0.5, FAILSAFE_INTERVAL_MIN=5, DAILY_CALC_HOUR=0, DAILY_CALC_MIN=5, GTS_RESET_MONTH=1, GTS_RESET_DAY=1)
- [ ] Add sensor-clamp limits dict from spec §9a.2: `SENSOR_LIMITS = {"temp": (-50, 60), "humidity": (0, 100), "wind": (0, 50), "solar": (0, 1500), "rain": (0, 200)}`
- [ ] Commit: `feat: add const.py with all integration constants`

### Task 1.3: Vendor PyETo

**Files:**
- Create: `custom_components/irrigation_et0/_pyeto_vendor.py`
- Test: `tests/test_pyeto_vendor.py`

- [ ] Identify the 6 PyETo functions we need: `fao56_penman_monteith`, `hargreaves`, `delta_svp`, `psy_const`, `svp_from_t`, `avp_from_rhmin_rhmax_tmin_tmax`, `net_rad`, `mean_svp`, plus solar-radiation helpers (`sol_dec`, `inv_rel_dist_earth_sun`, `sunset_hour_angle`, `et_rad`, `cs_rad`, `net_in_sol_rad`, `net_out_lw_rad`)
- [ ] Copy MIT-licensed implementations from upstream PyETo (commit hash + LICENSE attribution preserved at top of vendored file as comment)
- [ ] **Step 1 (failing test):** in `tests/test_pyeto_vendor.py` write `test_fao_annex6_example_chapter4`, asserting that `fao56_penman_monteith(...)` with the published Annex 6 inputs produces ET₀ within 0.1mm of the published reference value
- [ ] Run: `uv run pytest tests/test_pyeto_vendor.py -v` → expect FAIL (function not yet defined)
- [ ] Implement vendored module
- [ ] Run again → expect PASS
- [ ] Add `test_hargreaves_example` and `test_psychrometric_constant`
- [ ] Commit: `feat: vendor PyETo subset with FAO-56 reference tests`

### Task 1.4: et0_calculator module

**Files:**
- Create: `custom_components/irrigation_et0/et0_calculator.py`
- Test: `tests/test_et0_calculator.py`

Module exposes 3 pure functions:
```python
def calc_et0_fao56(t_min, t_max, rh_min, rh_max, solar_w_m2, wind_m_s, latitude, elevation, julian_day) -> float
def calc_et0_hargreaves(t_min, t_max, latitude, julian_day) -> float
def calc_et0_haude(t14, rh14, month) -> float
```

- [ ] **Step 1:** Write `test_calc_et0_fao56_returns_positive_for_summer_input`
- [ ] Run → FAIL
- [ ] Implement `calc_et0_fao56` calling vendored functions; convert solar W/m² → MJ/m²/d (× 0.0864)
- [ ] Run → PASS
- [ ] Add tests: `test_calc_et0_fao56_matches_fao_annex6_example`, `test_calc_et0_fao56_clamps_unrealistic_inputs`, `test_calc_et0_fao56_with_swapped_temps_normalizes`, `test_calc_et0_hargreaves_known_value`, `test_calc_et0_haude_monthly_factor`, `test_negative_solar_treated_as_zero`
- [ ] Implement remaining functions, all tests pass
- [ ] Add Geisenheim Ka function: `def calc_ka(t_max: float) -> float` returning `0.6 + 0.028*t_max - 0.0002*t_max**2` clamped to [0.4, 1.4]
- [ ] Test `test_calc_ka_at_known_temps`
- [ ] Commit: `feat: et0_calculator with FAO-56, Hargreaves, Haude, Ka`

### Task 1.5: water_balance module

**Files:**
- Create: `custom_components/irrigation_et0/water_balance.py`
- Test: `tests/test_water_balance.py`

Module exposes:
```python
@dataclass
class DailyBalance:
    datum: date; nfk_anfang: float; etc: float; regen: float; beregnung: float; nfk_ende: float

def calc_daily_balance(nfk_anfang, etc, regen, beregnung, nfk_max) -> DailyBalance
def calc_etc(et0, kc, ka) -> float
def needs_watering(nfk_aktuell, nfk_max, schwellwert_pct) -> bool
def watering_dauer_min(nfk_aktuell, nfk_max, zielwert_pct, durchfluss_mm_min) -> float
```

- [ ] **Step 1:** Write `test_calc_daily_balance_clamps_zero` — input `nfk_anfang=2, etc=10, regen=0, beregnung=0` → `nfk_ende == 0` (clamped, not negative)
- [ ] Run → FAIL
- [ ] Implement `calc_daily_balance` with clamp 0..nfk_max
- [ ] Run → PASS
- [ ] Add tests: `test_clamps_max_on_overflow`, `test_etc_multiplies_factors`, `test_needs_watering_below_threshold`, `test_does_not_need_watering_at_threshold`, `test_dauer_returns_zero_when_above_zielwert`, `test_dauer_for_typical_zone`
- [ ] Implement remaining; all pass
- [ ] Commit: `feat: water_balance module with NFK bilanz`

### Task 1.6: gts_calculator module

**Files:**
- Create: `custom_components/irrigation_et0/gts_calculator.py`
- Test: `tests/test_gts_calculator.py`

```python
def gts_weight(month: int) -> float            # 0.5 Jan, 0.75 Feb, 1.0 sonst
def gts_increment(t_mittel: float, month: int) -> float    # negative T → 0
def gts_should_reset(today: date, last_reset: date | None) -> bool   # neuer Jan 1
```

- [ ] Write tests for all three functions covering: each weight, T<0 ignored, reset on Jan 1 only
- [ ] Implement; all pass
- [ ] Commit: `feat: gts_calculator with monthly weights and reset logic`

### Task 1.7: storage module — schema v1

**Files:**
- Create: `custom_components/irrigation_et0/storage.py`
- Test: `tests/test_storage.py`

`storage.py` wraps `homeassistant.helpers.storage.Store`. Schema per spec §9.3.

```python
class IrrigationStorage:
    async def async_load(self) -> StorageData
    async def async_save(self, data: StorageData) -> None       # coalesced
    async def async_save_immediate(self, data: StorageData) -> None  # sync, for power-loss
    async def async_migrate(self, old_version: int, old_data: dict) -> dict
```

- [ ] Write `test_storage_returns_default_when_empty` (no file exists)
- [ ] Implement `async_load` returning typed `StorageData` dataclass with sensible defaults
- [ ] Run → PASS
- [ ] Add: `test_round_trip_save_load_preserves_data`, `test_async_save_immediate_does_not_coalesce`, `test_verlauf_retention_365_days_truncates_oldest`
- [ ] Add: `test_async_migrate_v1_returns_unchanged` (placeholder for future migrations) — put these in `tests/test_storage_migration.py` (separate file matching the file structure)
- [ ] All pass
- [ ] Commit: `feat: storage module with schema v1 and migration framework`

### Phase 1 Exit

- [ ] Run full test suite: `uv run pytest --cov=custom_components.irrigation_et0 --cov-report=term-missing`
- [ ] Coverage of touched modules ≥85%
- [ ] All tests green
- [ ] Tag: `git tag v0.0.1-foundation`

---

## Phase 2 — HA Integration Setup

**Goal:** Load as a custom component, config flow works in UI, no entities yet but coordinator running.

### Task 2.1: manifest.json + hacs.json

**Files:**
- Create: `custom_components/irrigation_et0/manifest.json`, `hacs.json`

- [ ] Write `manifest.json` per spec §14.2 (no `requirements` since PyETo is vendored)
- [ ] Write `hacs.json` per spec §14.1
- [ ] Run `python -m homeassistant.scripts.check_config` (or hassfest in CI) to validate manifest
- [ ] Commit: `feat: HACS manifest and component manifest`

### Task 2.2: __init__.py minimal setup/unload

**Files:**
- Create: `custom_components/irrigation_et0/__init__.py`
- Test: `tests/test_unload_reload_cycle.py`

Per spec §2.9 — strict listener tracking via `entry.async_on_unload`.

```python
async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": None}
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    # Coordinator + platforms come in later tasks
    return True

async def async_unload_entry(hass, entry):
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)
```

- [ ] Write `test_setup_then_unload_clears_data`
- [ ] Run → FAIL
- [ ] Implement
- [ ] Run → PASS
- [ ] Add `test_ten_reload_cycles_no_listener_leak` (counts listeners on hass before/after 10× reload)
- [ ] Commit: `feat: minimal __init__ with hot-reload-safe setup/unload`

### Task 2.3: config_flow.py — Step 1 (Anlage)

**Files:**
- Create: `custom_components/irrigation_et0/config_flow.py`
- Test: `tests/test_config_flow.py`
- Modify: translations/de.json, translations/en.json (add config flow strings)

- [ ] Write `test_user_step_creates_entry_with_basic_config` (mock user input: name, lat, lon, elevation)
- [ ] Run → FAIL
- [ ] Implement `IrrigationConfigFlow.async_step_user` with vol schema (name str, lat float -90..90, lon float -180..180, elevation int -500..9000)
- [ ] Run → PASS
- [ ] Add `test_invalid_lat_shows_error`, `test_duplicate_anlage_name_aborts`
- [ ] Commit: `feat: config flow step 1 (Anlage)`

### Task 2.4: config_flow.py — Step 2 (Wetter-Sensoren)

- [ ] Write `test_weather_step_accepts_dwd_weather_entity` (selector accepts both `sensor.*` and `weather.*`)
- [ ] Implement `async_step_weather` with selector for each parameter from spec §3 step 2
- [ ] All sensor params optional except T_min/T_max (Hargreaves fallback minimum)
- [ ] Add `test_minimum_pm_inputs_present_yields_pm_method`, `test_only_temp_inputs_yields_hargreaves_default`
- [ ] Commit: `feat: config flow step 2 (Wetter-Sensoren)`

### Task 2.5: config_flow.py — Step 3 (Hardware)

- [ ] Write `test_hardware_step_validates_trafo_is_switch_entity`
- [ ] Implement `async_step_hardware` (Trafo-Entity selector domain=switch, frost-Schwelle number -10..15)
- [ ] Commit: `feat: config flow step 3 (Hardware)`

### Task 2.6: config_flow.py — Step 4 (Zonen, repeated)

- [ ] Write `test_zone_step_can_be_repeated_until_user_finishes`
- [ ] Implement `async_step_zone` with vol schema for all zone params from spec §3 step 4
- [ ] After zone-add: menu choice "add another zone" or "finish"
- [ ] Generate UUID4 zone_id when zone added; store in entry.data["zones"]
- [ ] Add `test_zone_with_predefined_soil_calculates_nfk_max`, `test_two_zones_persist_independently`
- [ ] Commit: `feat: config flow step 4 (Zonen, repeatable)`

### Task 2.7: OptionsFlow

- [ ] Write `test_options_flow_can_change_frost_threshold_without_restart`
- [ ] Implement `IrrigationOptionsFlow` mirroring config flow steps but pre-populated with current values
- [ ] On submit: write to `entry.options`, trigger reload via update listener
- [ ] Add `test_options_flow_can_add_zone`, `test_options_flow_can_remove_zone_preserves_other_zones_storage`
- [ ] Commit: `feat: options flow for runtime reconfig`

### Task 2.8: Coordinator skeleton

**Files:**
- Create: `custom_components/irrigation_et0/coordinator.py`
- Test: `tests/test_coordinator.py`

```python
class IrrigationCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=5))
        self.entry = entry
        self.storage = IrrigationStorage(hass, entry.entry_id)
        self._unsubs: list[Callable[[], None]] = []

    async def async_setup(self) -> None:
        await self.storage.async_load()
        # Daily 00:05 callback registered here; tracked in self._unsubs
        # Trafo failsafe registered here

    async def async_shutdown(self) -> None:
        for unsub in self._unsubs: unsub()
        self._unsubs.clear()

    async def _async_update_data(self) -> dict:
        # Read weather sensors, frost check, trafo status
        return {"weather": ..., "frost_active": ..., "trafo_state": ...}
```

- [ ] Write `test_coordinator_setup_loads_storage`
- [ ] Implement minimal coordinator
- [ ] Add `test_coordinator_5min_refresh_fires_update_data`, `test_coordinator_shutdown_unsubscribes_all_listeners`
- [ ] Wire coordinator into `__init__.async_setup_entry`
- [ ] Commit: `feat: coordinator skeleton with lifecycle and refresh`

### Task 2.9: Device Registry

- [ ] Write `test_setup_creates_hub_device_and_zone_devices`
- [ ] Implement device registration in `async_setup_entry` after coordinator init: 1 hub device + N zone devices with `via_device=hub`
- [ ] Use `unique_id` strategy from spec §2.5
- [ ] Commit: `feat: device registry entries for hub and zones`

### Phase 2 Exit

- [ ] Install component manually in dev HA, walk through config flow in UI
- [ ] Verify devices appear in Settings → Devices
- [ ] Verify reload via Options Flow does not require HA restart
- [ ] All tests green, coverage ≥85%
- [ ] Tag: `v0.0.2-ha-loadable`

---

## Phase 3 — Entities (all platforms)

**Goal:** All entities from spec §8 exist and reflect the data the coordinator produces.

### Task 3.1: sensor.py — Zone NFK sensors

**Files:**
- Create: `custom_components/irrigation_et0/sensor.py`
- Test: `tests/test_sensors.py`

- [ ] Write `test_zone_nfk_sensor_state_matches_storage`
- [ ] Implement `IrrigationZoneNFKSensor(CoordinatorEntity, SensorEntity)` with `device_class=None`, `state_class=measurement`, `native_unit_of_measurement=mm`, `unique_id=f"{entry_id}_{zone_id}_nfk"`
- [ ] Implement `IrrigationZoneNFKProzentSensor` (% derived from nfk_aktuell / nfk_max)
- [ ] Add `test_nfk_prozent_calculates_correctly`, `test_nfk_unavailable_when_storage_missing`
- [ ] Commit: `feat: zone NFK sensors`

### Task 3.2: sensor.py — Daily counters & timer

- [ ] Implement `IrrigationZoneEtcHeute`, `IrrigationZoneRegenHeute`, `IrrigationZoneBeregnungHeute`, `IrrigationZoneTimer`, `IrrigationZoneCsZyklenRest`, `IrrigationZoneNaechsterStart` (`device_class=timestamp`), `IrrigationZoneBucketPrognose`
- [ ] All extend CoordinatorEntity, all subscribe to coordinator updates
- [ ] Test each with synthetic coordinator data
- [ ] Commit: `feat: zone daily and timer sensors`

### Task 3.3: sensor.py — Global ET₀ sensors

- [ ] Implement `IrrigationEt0FaoSensor` (always present), `IrrigationEt0HargreavesSensor`, `IrrigationEt0HaudeSensor`, `IrrigationGtsSensor`
- [ ] Conditional registration: in `async_setup_entry` check `entry.options["et_methode"]` and register only the active fallback method's sensor
- [ ] Test conditional registration
- [ ] Commit: `feat: global ET₀ and GTS sensors with conditional registration`

### Task 3.4: binary_sensor.py

- [ ] Create `binary_sensor.py` with: `FrostWarnung`, `TrafoProblem`, `EtFallbackActive`, `SensorenOk`
- [ ] Each reads coordinator.data fields
- [ ] Tests for each
- [ ] Commit: `feat: binary sensors for frost, trafo, fallback, sensor-ok`

### Task 3.5: switch.py

- [ ] Create `switch.py` with: `IrrigationZoneStatus` (per zone), `IrrigationWeekday` (Mon-Sun, 7 per zone), `IrrigationDryRun` (global)
- [ ] On state change, persist to entry.options or coordinator state and call `coordinator.async_request_refresh`
- [ ] Test toggling each
- [ ] Commit: `feat: switch entities`

### Task 3.6: select.py

- [ ] Create `select.py` with: `IrrigationZoneModus` (options Aus/Semi/Voll/Ansaat), `IrrigationEtMethode` (global; on change → schedule reload via async_call_later 1s)
- [ ] Test mode change persists
- [ ] Test ET-method change triggers config_entries.async_reload
- [ ] Commit: `feat: select entities for modus and ET-methode`

### Task 3.7: number.py

- [ ] Create `number.py` with all per-zone number entities from spec §8: `dauer`, `schwellwert`, `zielwert`, `manuelle_dauer`, `cs_zyklen`, `cs_pause`, `ansaat_intervall`, `ansaat_dauer`, `ansaat_laufzeit_tage`
- [ ] Each with proper `min/max/step/unit_of_measurement`
- [ ] Tests for each
- [ ] Commit: `feat: number entities per zone`

### Task 3.8: button.py

- [ ] Create `button.py` with `IrrigationZoneStartButton` button per zone (entity_id suffix `_start_button`; calls `coordinator.start_zone_manual(zone_id, manuelle_dauer_min)`)
- [ ] Test button press triggers coordinator method
- [ ] Commit: `feat: manual start button per zone`

### Task 3.9: time.py

- [ ] Create `time.py` with: `IrrigationZoneStartTime` (entity_id suffix `_start`; daily start time for Semi-Auto), `IrrigationAnsaatVon`, `IrrigationAnsaatBis`
- [ ] On change: persist + `coordinator.async_reschedule_zone(zone_id)`
- [ ] Tests for each
- [ ] Commit: `feat: time entities for start time and ansaat window`

### Phase 3 Exit

- [ ] In dev HA: all entities visible in Developer Tools → States
- [ ] Each entity has `device_id`, attached to the right device
- [ ] All unique_ids stable across reload
- [ ] Tests green, coverage ≥85%
- [ ] Tag: `v0.0.3-entities`

---

## Phase 4 — Coordinator Logic (Scheduling, Modes, Trafo, Queue)

**Goal:** The integration actually irrigates.

### Task 4.1: Trafo sequencing

**Files:**
- Modify: `coordinator.py`
- Test: `tests/test_coordinator.py`

```python
async def _trafo_on_then_valve(self, valve_entity_id: str) -> None:
    await self._switch_service("turn_on", self.trafo_entity_id)
    await asyncio.sleep(TRAFO_DELAY_S)
    await self._switch_service("turn_on", valve_entity_id)

async def _valve_off_then_trafo_check(self, valve_entity_id: str) -> None:
    await self._switch_service("turn_off", valve_entity_id)
    await asyncio.sleep(TRAFO_DELAY_S)
    if all(self._valve_state(v) == STATE_OFF for v in self.all_valves):
        await self._switch_service("turn_off", self.trafo_entity_id)
```

- [ ] Write `test_trafo_on_before_valve_with_delay`
- [ ] Implement
- [ ] Add `test_trafo_off_only_when_all_valves_closed`, `test_failsafe_turns_off_trafo_if_all_valves_off`
- [ ] Implement failsafe via `async_track_time_interval(5min)`
- [ ] Commit: `feat: trafo sequencing with failsafe`

### Task 4.2: Zone Queue (FIFO)

```python
@dataclass
class QueueItem:
    zone_id: str
    dauer_min: float
    cs_remaining: int      # 0 if no C&S
    cs_pause_min: int

self.queue: list[QueueItem] = []
self.running: QueueItem | None = None
```

- [ ] Write `test_two_starts_queue_serially`
- [ ] Implement `async_enqueue_start`, `async_run_next_in_queue`, `_zone_done` (called from timer end)
- [ ] Add `test_zone_done_pops_next_from_queue`, `test_empty_queue_turns_off_trafo`
- [ ] Commit: `feat: FIFO queue for zone runs`

### Task 4.3: Daily 00:05 calculation

- [ ] Write `test_daily_calc_at_005_writes_storage_and_fires_event`
- [ ] Implement `_daily_calc` per spec §4 + §7:
  1. Read weather sensors → daily aggregate (use Recorder if needed for the past 24h)
  2. Compute ET₀ via active method
  3. For each zone: compute ETc, NFK bilanz, persist
  4. Compute GTS, check year-reset
  5. For Ansaat zones: register first ansaat_tick of today
  6. For Semi/Voll zones: compute next_start_dt, register async_track_point_in_time
  7. Fire `irrigation_et0_calc_done` event
- [ ] Test individual sub-functions
- [ ] Commit: `feat: daily 00:05 calculation`

### Task 4.4: Year reset

- [ ] In `_daily_calc`: if today is Jan 1, reset GTS, reset NFK to startwert per zone
- [ ] Test `test_year_reset_only_on_jan_1`
- [ ] Commit: `feat: year reset within daily calc`

### Task 4.5: Semi-Automatik scheduling

- [ ] Write `test_semi_zone_starts_at_configured_time_on_enabled_weekday`
- [ ] Implement `_compute_next_start_semi(zone)` returning next datetime considering weekday switches + start time
- [ ] Test boundary cases (today's slot already passed → tomorrow), all-weekdays-off → None
- [ ] Commit: `feat: Semi-Automatik scheduling`

### Task 4.6: Voll-Automatik scheduling

- [ ] Write `test_voll_zone_triggers_when_nfk_below_schwellwert`
- [ ] Implement `_check_voll_trigger(zone)` called during daily calc and on coordinator refresh
- [ ] Compute dauer = `(zielwert_pct − nfk_aktuell_pct) / 100 * nfk_max / durchfluss_mm_min`
- [ ] Enqueue zone with computed dauer
- [ ] Test `test_voll_does_not_trigger_above_schwellwert`, `test_voll_dauer_calculation_correct`
- [ ] Commit: `feat: Voll-Automatik trigger and duration calc`

### Task 4.7: Ansaat-Modus chained ticks

- [ ] Write `test_ansaat_chains_ticks_within_window`
- [ ] Implement `_ansaat_tick(zone_id)`:
  1. If frost or status off: skip (no re-register)
  2. Enqueue zone with `dauer = ansaat_dauer`
  3. Compute `next_tick = now + ansaat_intervall_min`
  4. If next_tick within `[ansaat_von, ansaat_bis]`: register again
  5. Else: stop chain, daily_calc will resume tomorrow
- [ ] Test boundary: tick exactly at ansaat_bis re-registers (last one), tick after ansaat_bis stops
- [ ] Implement Ansaat auto-deactivation: if `ansaat_laufzeit_tage > 0` and `today >= start_datum + tage`: set modus=Aus, clear ansaat_start_datum
- [ ] Test `test_ansaat_auto_deactivates_after_n_days`
- [ ] Commit: `feat: Ansaat chained ticks and auto-deactivation`

### Task 4.8: Cycle & Soak

- [ ] Write `test_cs_splits_dauer_into_n_cycles_with_pauses`
- [ ] Implement: when enqueueing a zone with `cs_zyklen > 1`, split dauer / N per cycle. Between cycles: sleep cs_pause_min, then run next cycle (re-issue trafo+valve sequence). Update `cs_zyklen_rest` sensor.
- [ ] Test mid-CS frost-stop drops remaining cycles
- [ ] Commit: `feat: Cycle & Soak per zone`

### Task 4.9: Frost interlock

- [ ] Write `test_frost_blocks_all_starts`
- [ ] Implement: in `_async_update_data` check temperature; if below threshold:
  - Set `frost_active = True`, fire `EVENT_FROST_LOCK`, create persistent_notification
  - If running: hard stop (valve off, trafo off), drain entire queue
- [ ] On frost release: fire `EVENT_FROST_RELEASE`, dismiss notification, do not auto-resume
- [ ] Test running zone interrupted, queue drained, daily calc skips registering starts while frost active
- [ ] Commit: `feat: frost interlock`

### Task 4.10: zone_status OFF behavior

- [ ] Write `test_zone_status_off_stops_only_that_zone`
- [ ] Implement: switch handler turns running zone off + drops only this zone's pending queue entries; other zones unaffected
- [ ] Commit: `feat: zone_status switch hard-override`

### Task 4.11: Manual start

- [ ] Write `test_manual_start_button_runs_zone_for_slider_duration`
- [ ] Implement `async_start_zone_manual(zone_id, dauer_min)` → enqueue
- [ ] Test override during automatic run: stops current cleanly, sets next_start to tomorrow
- [ ] Commit: `feat: manual start with override semantics`

### Task 4.12: Zone end + reschedule

- [ ] Write `test_zone_done_fires_finished_event_with_actual_mm`
- [ ] Implement `_zone_done(item, abgebrochen=False)`:
  - Update beregnung_heute, beregnung in storage daily entry
  - Fire `EVENT_ZONE_FINISHED` with `{zone_id, name, beregnet_mm, abgebrochen}`
  - Update next_start_dt sensor
  - Re-register async_track_point_in_time for next start
  - Persist running_since=None via `async_save_immediate`
  - Run next from queue
- [ ] Commit: `feat: zone-done lifecycle and reschedule`

### Phase 4 Exit

- [ ] Manual end-to-end test in dev HA with dry_run=ON: schedule a Semi zone, verify `EVENT_ZONE_STARTED`/`FINISHED` fire, valve switches don't actually fire (dry run)
- [ ] Disable dry_run, run a 1-minute manual start on a real test valve, verify trafo sequence
- [ ] All tests green, coverage ≥85%
- [ ] Tag: `v0.0.4-irrigates`

---

## Phase 5 — Reliability (Recovery, Catch-up, Fallback, Repairs)

### Task 5.1: Startup recovery of open valves

**Files:**
- Create: `custom_components/irrigation_et0/recovery.py`
- Test: `tests/test_recovery.py`

- [ ] Write `test_recovery_resumes_zone_with_remaining_time`
- [ ] Implement per spec §9a.1: read each zone's valve state at startup; if running_since persisted → compute remaining → resume timer; else hard-close
- [ ] Add `test_recovery_hard_closes_unexpected_open_valve`, `test_recovery_runs_trafo_failsafe_after`
- [ ] Wire into `__init__.async_setup_entry` after coordinator setup
- [ ] Commit: `feat: startup recovery of open valves`

### Task 5.2: Catch-up on missed days

- [ ] Write `test_catchup_recomputes_nfk_from_recorder_history`
- [ ] Implement: if `letzte_berechnung < today - 1`, fetch missing days' weather aggregates from recorder, compute NFK retroactively
- [ ] Add `test_catchup_creates_repair_issue_on_too_many_missing_days`
- [ ] Commit: `feat: catch-up on missed days via recorder history`

### Task 5.3: Sensor fallback chain

- [ ] Write `test_fallback_pm_to_hargreaves_when_solar_unavailable`
- [ ] Implement `et0_calculator.calc_et0_with_fallback` returning `(et0, method_used, fallback_reason)`
- [ ] Set `binary_sensor.et_fallback_active` on, fire `EVENT_FALLBACK_ACTIVE`
- [ ] Add `test_fallback_to_last_known_when_all_inputs_missing`, `test_fallback_to_zero_when_no_history`
- [ ] Commit: `feat: ET₀ fallback chain with binary sensor and event`

### Task 5.4: Trafo problem detection

- [ ] Write `test_trafo_problem_set_when_unavailable_for_2min`
- [ ] Implement in `_async_update_data`: track trafo state history; set `binary_sensor.trafo_problem` on after 2min unavailable OR mismatch >30s
- [ ] Add `test_trafo_problem_blocks_starts`, `test_trafo_mismatch_aggressive_close`
- [ ] Commit: `feat: trafo problem detection and aggressive close`

### Task 5.5: Power-loss safety

- [ ] Write `test_zone_start_persists_running_since_immediately`
- [ ] In `async_run_next_in_queue` start-path: call `storage.async_save_immediate({running_since: now})`
- [ ] In `_zone_done`: same with `running_since: None`
- [ ] Test no coalescing on start/stop
- [ ] Commit: `feat: power-loss safety with sync writes on start/stop`

### Task 5.6: Repairs

**Files:**
- Create: `custom_components/irrigation_et0/repairs.py`
- Test: `tests/test_repairs.py`

- [ ] Write `test_repair_issue_created_when_weather_entity_unavailable_24h`
- [ ] Implement `repairs.py` with `async_create_fix_flow` for issues `missing_entity_*`
- [ ] Repair flow offers: pick alternative entity, accept default, dismiss
- [ ] Add `test_repair_resolved_when_user_picks_alternative`, `test_issue_auto_dismissed_when_entity_returns`
- [ ] Commit: `feat: repair flows for missing entities`

### Phase 5 Exit

- [ ] Manually crash HA mid-zone, verify recovery resumes
- [ ] Take HA offline for 3 days (clock-shift in dev), verify catch-up works
- [ ] All tests green
- [ ] Tag: `v0.0.5-reliable`

---

## Phase 6 — Services, Events, Diagnostics

### Task 6.1: Services

**Files:**
- Create: `custom_components/irrigation_et0/services.yaml` (already in const planning)
- Modify: `__init__.py` to register services
- Test: `tests/test_services.py`

- [ ] Write `services.yaml` content per spec §15
- [ ] Implement service handlers in `__init__.async_setup_entry`:
  - `start_zone(zone, dauer_min)` → maps zone entity-id to zone_id, calls coordinator.start_zone_manual
  - `stop_zone(zone)` → coordinator.stop_zone
  - `stop_all()` → coordinator.stop_all
  - `recalculate_now()` → coordinator._daily_calc(forced=True)
  - `set_nfk(zone, value_mm)` → coordinator.set_nfk(zone_id, value_mm) + storage immediate save
  - `skip_next_run(zone)` → coordinator.skip_next(zone_id)
  - `import_node_red_state()` → reads `input_number.{zone}_bucket` for each zone, sets NFK
- [ ] Tests: each service with valid + invalid args; zone-entity-id → zone_id mapping
- [ ] On `async_unload_entry`: `hass.services.async_remove(DOMAIN, service)` for each
- [ ] Commit: `feat: services with handlers and lifecycle`

### Task 6.2: Events end-to-end

- [ ] Already firing `irrigation_et0_calc_done`, `_zone_started/finished`, `_frost_lock/release`, `_fallback_active`, `_unexpected_state` from earlier tasks
- [ ] Audit: write a single `test_event_contract.py` listening to bus and verifying each event has the documented payload shape
- [ ] Commit: `test: event contract verification`

### Task 6.3: Diagnostics

**Files:**
- Create: `custom_components/irrigation_et0/diagnostics.py`
- Test: `tests/test_diagnostics.py`

- [ ] Write `test_diagnostics_includes_storage_summary_redacted`
- [ ] Implement `async_get_config_entry_diagnostics(hass, entry)` returning dict with: redacted entry data, storage summary, last 14 days history per zone, queue state, current ET₀ values
- [ ] Use `async_redact_data` for sensor entity-IDs
- [ ] Commit: `feat: diagnostics with redacted output`

### Task 6.4: Notifications

- [ ] Implement in coordinator helper `_notify(title, message, notification_id)` calling `hass.services.async_call("persistent_notification", "create", ...)`
- [ ] Wire into: frost lock, sensor outage, trafo problem, fallback, unexpected state, migration needed
- [ ] Add Options switch `enable_notifications` (default on)
- [ ] Test `test_notification_created_on_frost_lock`
- [ ] Commit: `feat: persistent notifications for critical events`

### Phase 6 Exit

- [ ] Trigger each service from Developer Tools → Services UI
- [ ] Listen on Developer Tools → Events: verify all 7 event types fire correctly
- [ ] Download diagnostics from device page, verify content
- [ ] Tag: `v0.0.6-services-events`

---

## Phase 7 — Frontend Cards

**Goal:** 4 Lovelace cards usable in dashboards.

### Task 7.1: Card scaffold + registration

**Files:**
- Create: `custom_components/irrigation_et0_card/irrigation-et0-card.js`

- [ ] Implement base `class IrrigationEt0Card extends HTMLElement` with `setConfig`, `set hass`, `static get configElement`, etc.
- [ ] Register: `customElements.define("irrigation-et0-card", IrrigationEt0Card)`
- [ ] Push to `window.customCards` for picker UI
- [ ] In `__init__.async_setup_entry`: register card via `frontend.add_extra_js_url(hass, "/irrigation_et0/irrigation-et0-card.js?v=" + VERSION)` and serve it via `http.async_register_static_paths`
- [ ] Test: card-config validation throws on missing required fields
- [ ] Commit: `feat: card scaffold with registration`

### Task 7.2: Card 1 — Übersicht

- [ ] Implement render() per mockup at `~/irrigation-ha/.superpowers/brainstorm/77623-1777394916/overview-v3.html` (open in browser to reference visually):
  - One row per zone: mode badge, NFK bar with S/Z markers (Voll only), next start, quick start button
  - Click row → expand inline details panel
  - Footer: trafo state, last calc, frost warning
- [ ] Use sensor states from coordinator entities; subscribe to state-changed events
- [ ] Test: render snapshot for fixed state
- [ ] Commit: `feat: card 1 (Übersicht)`

### Task 7.3: Card 2 — Globale Einstellungen

- [ ] Implement per mockup `settings-cards.html` (first card):
  - Standort fields (read-only display, edit via Options Flow)
  - Wetter-Sensor entity rows with current value
  - Hardware row
- [ ] "Edit" button opens HA Options Flow
- [ ] Commit: `feat: card 2 (Globale Einstellungen)`

### Task 7.4: Card 3 — Berechnungsparameter

- [ ] Implement: ET-method pills (writes select.et_methode), zone tabs with all per-zone params (writes via number/time/select entities)
- [ ] Commit: `feat: card 3 (Berechnungsparameter)`

### Task 7.5: Card 4 — Verlauf & Bilanz

- [ ] Implement per mockup `history-card.html`:
  - Zone tabs, time-range pills (7/14/30/Jahr)
  - SVG chart: ETc orange bars, rain blue, irrigation green, NFK purple line, S/Z dashed
  - Summary row with totals
- [ ] Data source: HA history API for sensors `{zone}_etc_heute`, `{zone}_regen_heute`, `{zone}_beregnung_heute`, `{zone}_nfk`
- [ ] Test: chart renders for fixed history fixture
- [ ] Commit: `feat: card 4 (Verlauf & Bilanz)`

### Task 7.6: i18n

- [ ] Populate `translations/de.json` and `translations/en.json` with all UI strings (config flow, options flow, services, repair issues, notification titles)
- [ ] Cards use `hass.localize` for strings
- [ ] Test `test_translations_files_have_matching_keys`
- [ ] Commit: `feat: i18n DE and EN`

### Phase 7 Exit

- [ ] Add 4 cards to a dashboard; visually verify against mockups
- [ ] Test on mobile and desktop browsers
- [ ] Tag: `v0.0.7-cards`

---

## Phase 8 — HACS Setup, CI, Release

### Task 8.1: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] Matrix: HA versions `[2024.10.0, 2025.1.0, latest]`, Python `[3.12, 3.13]`
- [ ] Steps: checkout, setup-python, uv sync, ruff check, mypy, pytest with coverage, upload coverage to codecov
- [ ] Add hassfest action for manifest validation
- [ ] Commit: `ci: github actions test matrix`

### Task 8.2: HACS validator workflow

- [ ] Create `.github/workflows/hacs-validate.yml` running `hacs/action@main` with `category: integration`
- [ ] Push to GitHub, verify workflow passes
- [ ] Commit: `ci: HACS validator`

### Task 8.3: Release automation

- [ ] Create `.github/workflows/release.yml` triggered on tag `v*` — creates GitHub Release with auto-generated changelog
- [ ] Maintain `CHANGELOG.md` (Keep a Changelog format)
- [ ] Commit: `ci: release automation`

### Task 8.4: Documentation polish

- [ ] Fill out `README.md` per spec §14.4: screenshots of all 4 cards, install via HACS Custom Repo, config walkthrough, services reference, troubleshooting
- [ ] Fill out `info.md` (HACS landing page, shorter)
- [ ] Add badge: HACS, CI, codecov
- [ ] Commit: `docs: complete README and info`

### Phase 8 Exit

- [ ] Push to GitHub; verify all CI jobs green
- [ ] HACS validator passes
- [ ] Tag `v0.1.0` triggers Release
- [ ] Add HACS Custom Repository in own HA, install successfully

---

## Phase 9 — Migration & Soft Cutover

### Task 9.1: Node-RED migration service

- [ ] Service `import_node_red_state` already stubbed in Phase 6; now flesh out:
  - Iterate zones, look up `input_number.{zone_name_normalized}_bucket`
  - If found: set NFK to that value, mark imported in storage
  - Report summary via persistent_notification
- [ ] Test: `test_import_maps_node_red_buckets_to_zones`
- [ ] Commit: `feat: complete node-red migration service`

### Task 9.2: Schatten-Betrieb checklist

- [ ] Document in `docs/operations.md`: how to run dry-run alongside Node-RED, what to compare daily, when to flip dry-run off
- [ ] Add section to README "Migrating from Node-RED"
- [ ] Commit: `docs: schatten-betrieb playbook`

### Task 9.3: Cutover dashboard view

- [ ] Provide example Lovelace YAML in `docs/example-dashboard.yaml` showing all 4 cards
- [ ] Commit: `docs: example dashboard YAML`

### Phase 9 Exit

- [ ] Run dry-run for 2 weeks alongside Node-RED
- [ ] Compare daily NFK values, plan starts
- [ ] When confident: flip dry-run off, decommission Node-RED flows for one zone, monitor
- [ ] After 1 week of OK: migrate remaining zones

---

## Cross-Cutting Concerns (apply to every Task)

- **TDD strictly:** test first, see it fail, minimal code to pass, refactor, commit.
- **Coverage gate:** every PR must keep coverage ≥85%.
- **Hot-reload regression test:** `test_unload_reload_cycle` runs in CI on every push.
- **Spec as source of truth:** if implementation diverges from spec, update spec first.
- **No HA restart for any change:** all configuration via Options Flow, all code-changes hot-reloaded via HACS update.
- **Commit cadence:** small, atomic, conventional-commits style (`feat:`, `fix:`, `test:`, `docs:`, `ci:`).

---

## Skill References

- TDD: superpowers:test-driven-development
- Subagent-driven implementation: superpowers:subagent-driven-development
- Inline batch execution: superpowers:executing-plans
- Code review: superpowers:requesting-code-review
- Branch finishing: superpowers:finishing-a-development-branch
