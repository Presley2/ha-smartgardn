# SmartGardn ET₀ - Code-Analyse

## Zusammenfassung

| Datei | Zeilen | Probleme | Priorität |
|-------|--------|----------|-----------|
| config_flow.py | 474 | Validierung könnte ausgelagert sein | 🟡 Mittel |
| coordinator.py | 1112 | **VIEL ZU GROSS** - Zu viele Aufgaben | 🔴 HOCH |
| __init__.py | 227 | Card-Registration OK | 🟢 OK |
| const.py | ~50 | OK | 🟢 OK |

---

## coordinator.py Detailanalyse

### Problem: Coordinator hat zu viele Verantwortungen

```
1112 Zeilen mit 37+ Funktionen in einer Klasse!
```

### Aktuelle Struktur (Spaghetti):

```
class IrrigationCoordinator:
  ├── Storage-Management (88 Zeilen)
  │   └── _ensure_storage_schema()
  │
  ├── Setup & Lifecycle (300+ Zeilen)
  │   ├── __init__()
  │   ├── async_setup()
  │   ├── _startup_recovery()
  │   ├── _zone_done_recovery()
  │   └── async_shutdown()
  │
  ├── Wetter-Integration (200+ Zeilen)
  │   ├── _get_daily_minmax()      ← Extract to weather/sensors.py
  │   ├── _read_sensor()            ← Extract to weather/sensors.py
  │   └── _fetch_dwd_forecast()     ← Extract to weather/forecast.py
  │
  ├── ET₀-Berechnung (150+ Zeilen)
  │   └── _compute_et0_with_fallback()  ← Extract to irrigation/et0.py
  │
  ├── Zone-Management (300+ Zeilen)
  │   ├── _trigger_zone_start()         ← Extract to irrigation/zones.py
  │   ├── async_start_zone()            ← Extract to irrigation/zones.py
  │   ├── async_stop_zone()             ← Extract to irrigation/zones.py
  │   ├── async_stop_all()              ← Extract to irrigation/zones.py
  │   └── _extract_zone_id_from_entity()← Extract to irrigation/zones.py
  │
  ├── Hardware-Steuerung (80+ Zeilen)
  │   ├── _trafo_on_then_valve()        ← Extract to irrigation/control.py
  │   ├── _valve_off_then_trafo_check() ← Extract to irrigation/control.py
  │   ├── _switch_service()             ← Extract to irrigation/control.py
  │   └── _check_trafo_state()          ← Extract to irrigation/control.py
  │
  ├── Zeitplanung (150+ Zeilen)
  │   ├── _compute_next_start_semi()    ← Extract to irrigation/scheduler.py
  │   ├── _compute_next_start_voll()    ← Extract to irrigation/scheduler.py
  │   ├── _compute_next_start_ansaat()  ← Extract to irrigation/scheduler.py
  │   └── _daily_calc()                 ← Extract to irrigation/scheduler.py
  │
  ├── Sicherheit (100+ Zeilen)
  │   ├── _check_frost_and_lock()       ← Extract to safety/safety.py
  │   ├── _failsafe_check()             ← Extract to safety/safety.py
  │   ├── _should_skip_for_rain()       ← Extract to safety/safety.py
  │   └── Recovery-Funktionen
  │
  └── Warteschlange (80+ Zeilen)
      ├── _run_next_in_queue()          ← Extract to queue/queue.py
      ├── _zone_done()                  ← Extract to queue/queue.py
      └── async_enqueue_start()         ← Extract to queue/queue.py
```

---

## config_flow.py Detailanalyse

### Problem: Validierung vermischt mit Flow-Logik

```python
# Zeilen 174-195: Validierung direkt im async_step_user()
if not name:
    errors["name"] = "required"
if not -90 <= latitude <= 90:
    errors["latitude"] = "invalid_latitude"
if not -180 <= longitude <= 180:
    errors["longitude"] = "invalid_longitude"
if not -500 <= elevation <= 9000:
    errors["elevation"] = "invalid_elevation"
```

**Besser:** In separate Validator-Funktionen auslagern:

```python
# validators.py
def validate_name(name: str) -> str | None:
    if not name.strip():
        return "required"
    return None

def validate_latitude(lat: float) -> str | None:
    if not -90 <= lat <= 90:
        return "invalid_latitude"
    return None
```

### Current Flows (OK, aber könnte klarer sein):

```
User Input
  ↓
async_step_user() → Validierung (aktuell inline)
  ↓
async_step_weather() → Keine Validierung (OK)
  ↓
async_step_hardware() → Keine Validierung (OK)
  ↓
async_step_zone() → Viel Validierung (aktuell inline)
  │
  ├─→ async_step_zone_menu()
  │     ├─→ add_zone (zurück zu async_step_zone)
  │     └─→ finish (zu async_step_finish)
  │
  └─→ async_step_finish() → _build_entry_data() → create_entry()

Options Flow (runtime):
  ├─→ async_step_general() (Update name, frost_threshold)
  ├─→ async_step_weather() (Update sensors)
  └─→ async_step_forecast() (Update DWD config)
```

---

## Empfehlungen zur Refaktorierung

### 1. **Sofort (Quick Wins)** ⚡
```
✅ Extract weather/sensors.py (30 min)
  - _get_daily_minmax()
  - _read_sensor()
  - Humidity/Solar handling

✅ Extract irrigation/et0.py (30 min)
  - _compute_et0_with_fallback()
  - All ET₀ math

✅ Extract config_validators/ (30 min)
  - Validation logic aus config_flow.py
```

### 2. **Mittelfristig (1-2 Wochen)** 📅
```
✅ Extract irrigation/zones.py (1-2 hours)
  - Zone start/stop logic
  - Zone queue management

✅ Extract irrigation/scheduler.py (1-2 hours)
  - _compute_next_start_*()
  - _daily_calc()
  - Timing logic

✅ Extract irrigation/control.py (1 hour)
  - Hardware control (valve, trafo)
  - Switch operations
```

### 3. **Langfristig (Clean-up)** 🔧
```
✅ Extract safety/safety.py
  - Frost checking
  - Failsafe logic
  - Recovery functions

✅ Extract queue/queue.py
  - QueueItem class
  - Queue management
  - _zone_done() logic

✅ Extract storage/storage.py
  - Storage schema
  - Persistence
```

---

## Keine Breaking Changes!

**WICHTIG:** Bei jedem Refactoring:
1. ✅ Alle imports updaten
2. ✅ Integration-Tests laufen
3. ✅ Neue Release erstellen
4. ✅ HACS Update testen
5. ✅ **Keine Breaking Changes in Config/UI!**

---

## Metriken (Ziel)

**Vorher:**
- coordinator.py: 1112 Zeilen
- config_flow.py: 474 Zeilen
- **Total: 1586 Zeilen in 2 Dateien**

**Nachher (Target):**
- coordinator.py: ~200 Zeilen (nur Orchestration)
- weather/sensors.py: ~150 Zeilen
- weather/forecast.py: ~100 Zeilen
- irrigation/et0.py: ~150 Zeilen
- irrigation/zones.py: ~200 Zeilen
- irrigation/scheduler.py: ~150 Zeilen
- irrigation/control.py: ~100 Zeilen
- safety/safety.py: ~100 Zeilen
- queue/queue.py: ~100 Zeilen
- storage/storage.py: ~80 Zeilen
- config_flow.py: ~380 Zeilen (nach validator extraction)
- config_validators/validators.py: ~100 Zeilen
- **Total: ~1810 Zeilen aber VIEL besser organisiert** ✅

---

## Testplan

Nach jedem Refactor:
1. Run syntax checks
2. Run existing tests
3. Create new unit test for extracted module
4. Update HACS test
5. Create release
6. Test in HA Live
