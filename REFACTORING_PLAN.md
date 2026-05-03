# SmartGardn ET₀ - Code Refactoring Plan

## Aktuelle Struktur (Problem)
```
config_flow.py          474 Zeilen - OK
coordinator.py        1112 Zeilen - VIEL ZU GROSS!
```

## Ziel-Struktur

```
custom_components/smartgardn_et0/
├── __init__.py                          (Existing - unchanged)
├── const.py                             (Existing - constants)
├── config_flow.py                       (474 Zeilen - OK, aber validates auslagern?)
│
├── coordinator.py                       (MAIN - entry point, nur Orchestration)
│   └── ~150 Zeilen: __init__, async_setup, async_shutdown, _async_update_data
│
├── weather/
│   ├── __init__.py
│   ├── sensors.py                       (Wettersensor-Verwaltung)
│   │   └── read_sensor()
│   │   └── _get_daily_minmax()
│   │   └── Humidity/Solar/Wind/Rain handling
│   │
│   └── forecast.py                      (DWD Vorhersage)
│       └── _fetch_dwd_forecast()
│
├── irrigation/
│   ├── __init__.py
│   ├── et0.py                           (ET₀-Berechnung)
│   │   └── _compute_et0_with_fallback()
│   │   └── _compute_ka()
│   │   └── _compute_kc_factor()
│   │
│   ├── zones.py                         (Zone-Management)
│   │   └── _trigger_zone_start()
│   │   └── async_start_zone()
│   │   └── async_stop_zone()
│   │   └── async_stop_all()
│   │   └── _extract_zone_id_from_entity()
│   │
│   ├── scheduler.py                     (Zeitplanung)
│   │   └── _compute_next_start_semi()
│   │   └── _compute_next_start_voll()
│   │   └── _compute_next_start_ansaat()
│   │   └── _daily_calc()
│   │
│   └── control.py                       (Hardware-Steuerung)
│       └── _trafo_on_then_valve()
│       └── _valve_off_then_trafo_check()
│       └── _switch_service()
│       └── _check_trafo_state()
│
├── storage/
│   ├── __init__.py
│   └── storage.py                       (Persistierung)
│       └── _ensure_storage_schema()
│       └── Storage-Verwaltung
│
├── queue/
│   ├── __init__.py
│   └── queue.py                         (Zone-Warteschlange)
│       └── QueueItem
│       └── async_enqueue_start()
│       └── _run_next_in_queue()
│       └── _zone_done()
│
├── safety/
│   ├── __init__.py
│   └── safety.py                        (Sicherheitsprüfungen)
│       └── _check_frost_and_lock()
│       └── _failsafe_check()
│       └── _should_skip_for_rain()
│       └── Recovery-Funktionen
│
└── config_validators/
    ├── __init__.py
    └── validators.py                    (Config-Validierung)
        └── validate_name()
        └── validate_latitude()
        └── validate_longitude()
        └── etc.
```

## Refactoring-Phasen

### Phase 1: Extract Weather Module
- Erstelle `weather/sensors.py`
- Verschiebe `_get_daily_minmax()`, `_read_sensor()` dahin
- Update imports in `coordinator.py`

### Phase 2: Extract Irrigation Module
- Erstelle `irrigation/et0.py`
- Verschiebe `_compute_et0_with_fallback()` und verwandte
- Erstelle `irrigation/zones.py`
- Verschiebe Zone-Management
- Erstelle `irrigation/scheduler.py`
- Verschiebe Zeitplanungs-Logik

### Phase 3: Extract Control & Safety
- Erstelle `irrigation/control.py` für Hardware-Steuerung
- Erstelle `safety/safety.py` für Sicherheit

### Phase 4: Extract Queue & Storage
- Erstelle `queue/queue.py`
- Erstelle `storage/storage.py`

### Phase 5: Config Validators
- Erstelle `config_validators/validators.py`
- Mache config_flow.py sauberer

## Vorteile

✅ **Wartbarkeit**: Jede Datei hat eine klare Aufgabe
✅ **Testing**: Einfacher Unit-Tests schreiben
✅ **Wartung**: Bugs sind leichter zu finden/fixen
✅ **Erweiterbarkeit**: Neue Features ohne 1000-Zeilen-Datei
✅ **Lesbarkeit**: Max ~200 Zeilen pro Datei

## Reihenfolge

1. **Zuerst:** weather/ und irrigation/et0.py (keine Abhängigkeiten)
2. **Dann:** irrigation/zones.py, irrigation/scheduler.py
3. **Danach:** safety/, queue/, storage/
4. **Zuletzt:** config_validators/

## Tests

Nach jedem Schritt:
- `git push`
- HACS Update testen
- Keine Breaking Changes!
