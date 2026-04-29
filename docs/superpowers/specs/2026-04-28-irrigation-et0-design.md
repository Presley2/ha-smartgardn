# irrigation_et0 — Design Spec
**Datum:** 2026-04-29 (v2 — erweitert um Hot-Reload, HACS, Tests, Reliability)  
**Status:** Final — zur Implementierung freigegeben

---

## 1. Ziel

Eine native Home Assistant Custom Component (`irrigation_et0`) zur wissenschaftlich fundierten Bewässerungssteuerung auf Basis des FAO-56 Penman-Monteith-Modells mit täglicher Bodenwasserbilanz (NFK) pro Zone. Ablösung der bisherigen Node-RED + InfluxDB Lösung. Vollständig unabhängig von externen Diensten.

---

## 2. Systemarchitektur

### 2.1 Komponentenstruktur

```
irrigation-ha/                              # Repo-Root (HACS)
  custom_components/irrigation_et0/
    __init__.py              # Setup, Config Entry, Services, Recovery
    config_flow.py           # UI-Erstkonfiguration + OptionsFlow (Laufzeit-Edit)
    coordinator.py           # DataUpdateCoordinator, Scheduling, Trafo-Sequenz, Queue
    et0_calculator.py        # FAO-56 Penman-Monteith / Hargreaves / Haude
    water_balance.py         # NFK-Bilanzmodell pro Zone
    gts_calculator.py        # Grünlandtemperatursumme
    storage.py               # Persistenz (HA Storage API, Version + Migration)
    diagnostics.py           # async_get_config_entry_diagnostics (anonymisiert)
    repairs.py               # Repair Issues bei Sensor-Verlust
    recovery.py              # Startup-Recovery offener Ventile + verpasster Tage
    sensor.py                # ET₀, NFK, Timer, Prognose-Sensoren
    binary_sensor.py         # Frost-Warnung, Trafo-Problem, Sensor-Verfügbarkeit
    switch.py                # Zonen-Status, Wochentage, Dry-Run-Switch (global)
    select.py                # Automatik-Modus pro Zone, ET-Methode global
                             # ET-Methode-Änderung → async_call_later → hass.config_entries.async_reload
    number.py                # Dauer, Schwellwert, Zielwert, Durchfluss, C&S, Ansaat-Params
    button.py                # Manueller Start pro Zone
    time.py                  # Startzeit, Ansaat-Zeitfenster (von/bis)
    const.py                 # Konstanten, DOMAIN, Defaults, Event-Namen
    manifest.json            # HACS-Metadaten (siehe §14.2)
    services.yaml            # Service-Definitionen (siehe §15)
    translations/
      de.json
      en.json
  custom_components/irrigation_et0_card/   # Lovelace Custom Card
    irrigation-et0-card.js
    irrigation-et0-card-editor.js
  tests/                                   # pytest-homeassistant-custom-component
    conftest.py
    test_et0_calculator.py
    test_water_balance.py
    test_coordinator.py
    test_config_flow.py
    test_recovery.py
    fixtures/
      fao_annex6_examples.json             # Referenzwerte FAO-56 Annex 6
  .github/workflows/
    ci.yml                                 # pytest + HA-Versionen-Matrix
    hacs-validate.yml                      # HACS-Validator
    release.yml                            # Auto-Tag + GitHub Release
  hacs.json                                # HACS-Metadaten (Repo-Level)
  README.md                                # Installation, Config, Screenshots
  info.md                                  # HACS-Beschreibung
  LICENSE                                  # MIT
  pyproject.toml                           # uv/ruff/pytest-Config
```

### 2.2 Abhängigkeiten

- `PyETo` — FAO-56 ET₀-Berechnung (Python-Bibliothek)
- `homeassistant.helpers.storage` — Persistenz NFK-Verlauf
- `homeassistant.helpers.event` — `async_track_time_change`, `async_track_point_in_time`
- `homeassistant.helpers.update_coordinator.DataUpdateCoordinator` — zentraler Refresh
- `homeassistant.helpers.device_registry` — Zone als Device
- `homeassistant.helpers.issue_registry` — Repair Flows
- HA Recorder + History API — Historie und Catch-up

### 2.3 Coordinator-Pattern

Eine Instanz `IrrigationCoordinator(DataUpdateCoordinator)` pro Config Entry:

```python
class IrrigationCoordinator(DataUpdateCoordinator):
    update_interval = timedelta(minutes=5)   # Polling für Sensor-Refresh, Frost-Check
    # _async_update_data: liest Wetter-Sensoren, aktualisiert Frost-Status,
    #   prüft Trafo-Verfügbarkeit, gibt dict für alle abhängigen Entities zurück
    # Tägliche 00:05-Berechnung läuft separat via async_track_time_change
    #   und ruft am Ende coordinator.async_request_refresh() auf
```

Alle Sensor-/Switch-/Select-Entities sind `CoordinatorEntity` und teilen sich den Coordinator-Datenstand.

### 2.4 Device Registry

Pro Anlage:
- 1 Hub-Device `Bewässerung {anlage}` (Manufacturer "irrigation_et0", Model "FAO-56")
- N Zone-Devices `Zone {name}`, jeweils `via_device=Hub` — gruppiert alle Zone-Entities

### 2.5 unique_id-Strategie

```
{config_entry.entry_id}_{zone_id}_{platform_key}    # Zone-Entities
{config_entry.entry_id}_{global_key}                # Globale Entities
```

`zone_id` ist ein vom Coordinator vergebener UUID4-String (in Storage persistiert), nicht der Anzeigename. Anzeigename darf umbenannt werden ohne Entity-IDs zu zerstören.

### 2.6 OptionsFlow

Erst-Setup via Config Flow (§3). Laufzeit-Änderungen via OptionsFlow:
- Wetter-Sensoren neu zuordnen
- Frost-Schwelle, Standortdaten ändern
- Zonen hinzufügen / entfernen / umbenennen
- Trafo-Entity wechseln

OptionsFlow-Save → `hass.config_entries.async_reload(entry_id)` → Coordinator + Entities neu erstellt; Storage (NFK-Verlauf) bleibt erhalten.

### 2.7 Diagnostics

`diagnostics.py` exportiert via `async_get_config_entry_diagnostics`:
- Konfiguration (Sensor-Entity-IDs anonymisiert via `async_redact_data`)
- Aktueller NFK-Stand pro Zone
- Letzte 14 Tage Bilanz
- ET₀-Methode + letzte Berechnungswerte
- Queue-Zustand, laufende Zone, Trafo-Status
- Eingangs-Sensorwerte zum Zeitpunkt des Exports

### 2.8 Repairs

Wenn Wetter- oder Ventil-Entity verschwindet (`state == None` für >24h):
```python
ir.async_create_issue(
    hass, DOMAIN, f"missing_entity_{entity_id}",
    severity=ir.IssueSeverity.WARNING,
    translation_key="missing_entity",
    learn_more_url="https://github.com/.../wiki/troubleshooting",
)
```
Repair-Flow im UI bietet: alternative Entity wählen ODER auf Standardwert zurückfallen ODER Issue ignorieren.

### 2.9 Hot-Reload-Fähigkeit (kein HA-Neustart bei Updates)

**Anforderung:** Versions-Updates der Integration via HACS, OptionsFlow-Änderungen, ET-Methoden-Wechsel und Card-Updates dürfen KEINEN Home-Assistant-Neustart erfordern. Alle Änderungen werden via Config-Entry-Reload (`hass.config_entries.async_reload(entry_id)`) durchgeführt.

**Implementierungs-Regeln:**

1. **Vollständig im Config Entry**: Kein State, keine Listener, keine globalen Imports außerhalb von `async_setup_entry`. `hass.data[DOMAIN][entry_id]` ist die einzige State-Wurzel und wird in `async_unload_entry` vollständig geleert.

2. **Listener-Tracking**: Jeder `async_track_*`-Aufruf gibt eine Unsubscribe-Funktion zurück. Diese MUSS via `entry.async_on_unload(unsub)` registriert werden. So werden bei Reload alle Timer/Trigger sauber abgemeldet.

3. **Coordinator-Lifecycle**: Coordinator wird in `async_setup_entry` erstellt und in `async_unload_entry` via `coordinator.async_shutdown()` beendet. `async_shutdown` storniert pending `async_track_point_in_time`-Callbacks und schließt offene Ventile sicher.

4. **Storage über Reloads stabil**: Storage-Version + Migrationen (siehe §9.4) — beim Schema-Update nur die Daten migriert, keine Entity-IDs verändert.

5. **Konfigurations-Listener**: 
   ```python
   entry.async_on_unload(entry.add_update_listener(async_reload_entry))
   ```
   `async_reload_entry` ruft `hass.config_entries.async_reload(entry.entry_id)` auf — bei jeder Options-Änderung wird sauber neu geladen ohne HA-Neustart.

6. **PyETo-Import**: Top-Level-Import in `et0_calculator.py`. Bei Versions-Update der Bibliothek kommt ein HA-Neustart **NICHT** drumherum (Python-Modul-Cache) — daher: PyETo-Code für unsere Anwendung **vendor'n** (eigene `_pyeto_vendor.py`-Datei mit nur den 6 benötigten Funktionen). Dann ist auch ein Bibliotheks-Update neustart-frei.

7. **Frontend-Card Cache-Bust**: Card-File wird via `<script src="/local/.../card.js?v={VERSION}">` mit Versions-Query-String eingebunden. Bei Update ändert sich `VERSION` (im Manifest gepflegt) → Browser lädt neu, kein HA-Neustart nötig.

8. **Regression-Test**: Test `test_unload_reload_cycle` in `tests/test_coordinator.py` prüft: Setup → 10× Reload → Unload → keine offenen Listener, keine Memory-Leaks, kein doppelter `unique_id`-Konflikt.

**Akzeptable Ausnahmen:**
- Hinzufügen NEUER Platform-Files (z.B. erstmals `time.py`) erfordert HA-Reload — bei zukünftigen Erweiterungen sehr selten.
- Änderungen an `manifest.json` `requirements` (neue Python-Pakete) erfordern HA-Neustart, daher: neue Pflicht-Deps werden vermieden, Soft-Deps werden lazy importiert.

---

## 3. Konfiguration (Config Flow)

### Schritt 1: Anlage
- Name der Anlage (z.B. "Garten")
- Breitengrad, Längengrad, Höhe (m ü. NN)

### Schritt 2: Wetter-Sensoren
Jeder Parameter ist eine wählbare HA-Entity (Sensor oder Weather-Entity):

| Parameter | Einheit | Aggregation |
|---|---|---|
| Temperatur Min | °C | Tagesminimum |
| Temperatur Max | °C | Tagesmaximum |
| Luftfeuchtigkeit Min | % | Tagesminimum |
| Luftfeuchtigkeit Max | % | Tagesmaximum |
| Solarstrahlung | W/m² | Tagesmittel |
| Windgeschwindigkeit (2m) | m/s | Tagesmittel |
| Niederschlag | mm | Tagessumme |

DWD `weather.*`-Entities: automatische Extraktion via `weather.get_forecasts` Service.

### Schritt 3: Hardware
- Trafo-Entity (Switch, 24V AC, vor jedem Ventil einzuschalten)
- Frostschutz-Temperaturschwelle (°C, Standard: 4°C)

### Schritt 4: Zonen (N Zonen, wiederholbar)
Pro Zone:
- Name
- Zonentyp: Rasen / Tropf / Dach / Sonstiges
- Ventil-Entity (z.B. `switch.drs8_schaltaktor_bewasserung_mv4_ch26`)
- Kc (Kulturkoeffizient, Standard je Typ: Rasen 0.8, Tropf 1.0)
- Bodentyp (Voreinstellung mit NFK-Wert) oder manuell mm
- Wurzeltiefe (dm)
- Schwellwert % — Voll-Automatik-Auslöser
- Zielwert % — Voll-Automatik-Abbruch
- Durchfluss (mm/min)
- NFK-Startwert % (zum Jahresbeginn)
- Saisonaler Faktor (Automatisch Ka / Haude-Faktoren / Keiner)

**Bodentyp-Voreinstellungen:**

| Typ | NFK (mm/dm) |
|---|---|
| Sand | 8 |
| Sandiger Lehm | 12 |
| Lehm | 15 |
| Toniger Lehm | 18 |
| Ton | 20 |

---

## 4. Berechnungsmodell

### 4.1 ET₀ — FAO-56 Penman-Monteith

Tägliche Referenz-Evapotranspiration nach FAO-56 via PyETo:

```python
from pyeto import fao, convert

et0 = fao.et0_pm(
    net_rad,        # Nettostrahlung (MJ/m²/d)
    t,              # Mittlere Tagestemperatur (°C)
    ws,             # Windgeschwindigkeit 2m (m/s)
    svp,            # Sättigungsdampfdruck (kPa)
    avp,            # Aktueller Dampfdruck (kPa)
    delta_svp,      # Steigung Dampfdruckkurve
    psy             # Psychrometerkonstante
)
```

Eingangswerte werden aus den konfigurierten HA-Sensoren gelesen. Alle Einheiten intern normalisiert.

### 4.2 ETc — Zonenspezifische Evapotranspiration

```
ETc = ET₀ × Kc × Ka
```

- **Kc**: Kulturkoeffizient (konfiguriert pro Zone)
- **Ka**: Saisonaler Klimakorrekturfaktor  
  Optional: `Ka = 0.6 + 0.028 × T_max - 0.0002 × T_max²` (Geisenheimer Ansatz)  
  Alternativ: Haude-Monatsfaktoren

### 4.3 Tägliche NFK-Bilanz

```
nfk_ende = nfk_anfang - ETc + regen + beregnung
nfk_morgen = clamp(nfk_ende, 0, nfk_max)
beregnung_mm = dauer_min × durchfluss_mm_min
```

Berechnung täglich um **00:05** mit den abgeschlossenen Tageswerten.

### 4.4 Grünlandtemperatursumme (GTS)

```
gts += T_mittel × gewicht    (nur wenn T_mittel > 0°C)
```

Gewichte: Januar 0.5 / Februar 0.75 / März–Dezember 1.0  
Reset: 1. Januar 00:01

### 4.5 ET-Methoden (auswählbar via `select.et_methode`)

| Methode | Sensor | Eingaben | Genauigkeit |
|---|---|---|---|
| Penman-Monteith FAO-56 | `sensor.et0_fao` | Temp, Feuchte, Solar, Wind | Hoch |
| Hargreaves | `sensor.et0_hargreaves` | Temp min/max, Ra (extraterrestrisch) | Mittel |
| Haude | `sensor.et0_haude` | Temp 14 Uhr, Feuchte 14 Uhr | Niedrig/einfach |

`sensor.et0_fao` ist immer vorhanden (Referenzwert). `sensor.et0_hargreaves` und `sensor.et0_haude` werden nur registriert wenn die jeweilige Methode in `select.et_methode` aktiv ist; beim Methodenwechsel via Config Entry reload.

---

## 5. Zonensteuerung

### 5.1 Automatik-Modi

| Modus | Verhalten |
|---|---|
| **Aus** | Keine automatische Bewässerung |
| **Semi Automatik** | Bewässert an konfigurierten Wochentagen zur Startzeit; Dauer = Basis-Dauer |
| **Voll Automatik** | Bewässert wenn NFK < Schwellwert; Dauer = (Zielwert − NFK_aktuell) / Durchfluss |
| **Ansaat** | Kurze Zyklen in einstellbarem Intervall innerhalb eines Zeitfensters |

### 5.2 Ansaat-Modus Parameter
- Intervall zwischen Durchgängen (min, z.B. 20) → `{zone}_ansaat_intervall`
- Dauer pro Durchgang (min, z.B. 2) → `{zone}_ansaat_dauer`
- Aktives Zeitfenster von/bis (z.B. 06:00–21:00) → `{zone}_ansaat_von` / `{zone}_ansaat_bis`
- Laufzeit in Tagen (oder 0 = manuell deaktivieren) → `{zone}_ansaat_laufzeit_tage`

**Auto-Deaktivierung:** Wenn `ansaat_laufzeit_tage > 0` wird ein Startdatum in Storage gespeichert. Im täglichen 00:05-Callback wird geprüft ob `heute ≥ startdatum + laufzeit_tage`. Bei Ablauf: `{zone}_modus` wird auf `Aus` gesetzt und das Startdatum aus Storage gelöscht.

### 5.3 Cycle & Soak
Optional pro Zone: lange Bewässerungszeiten in N Zyklen aufteilen mit Pause dazwischen.
- Anzahl Zyklen (z.B. 3)
- Soak-Pause zwischen Zyklen (min, z.B. 10)

### 5.4 Manueller Start
Pro Zone ein Button-Entity + konfigurierbarer Slider (1–120 min).  
Laufender Timer wird als `sensor.{zone}_timer` in mm:ss ausgegeben.

### 5.5 Frostschutz
Wenn aktuelle Außentemperatur < konfigurierter Frostschwelle (Standard 4°C):
- `binary_sensor.frost_warnung` = `on`
- Alle automatischen Starts werden blockiert (Semi, Voll, Ansaat)
- Manueller Start über Button ist ebenfalls gesperrt
- Läuft bereits eine Zone (inkl. Cycle & Soak): sofortiger Stopp — laufendes Ventil OFF, Trafo OFF, alle ausstehenden Zyklen dieser Zone aus der Queue entfernt
- Gesamte Pending Queue wird geleert (auch andere Zonen)
- Zustand bleibt gesperrt solange Temperatur unter Schwelle

**Sofortiger Stopp durch `{zone}_status = OFF`:** Identisches Verhalten wie Frost — laufendes Ventil OFF, Trafo OFF, ausstehende Zyklen dieser Zone aus Queue entfernt; andere Zonen in der Queue bleiben erhalten.

---

## 6. Trafo-Sequenzierung

Der 24V-Trafo muss vor jedem Magnetventil eingeschaltet sein:

```
Zone starten:
  1. Trafo ON
  2. 500ms warten
  3. Ventil ON
  4. Timer starten

Zone stoppen:
  1. Ventil OFF
  2. 500ms warten
  3. Prüfen: alle Ventile geschlossen?
  4. Wenn ja: Trafo OFF

Failsafe (alle 5 min):
  Wenn alle Ventile OFF → Trafo OFF
```

**Queue**: Nur eine Zone läuft gleichzeitig. Parallele Starts werden in eine FIFO-Queue gestellt.

---

## 7. Scheduling (HA-intern, kein Cron-Dienst)

```python
# Startup-Routine (coordinator.__init__ / async_setup_entry)
# Liest persistierte next_start_dt-Werte aus Storage.
# Für jede Zone mit next_start_dt > now(): async_track_point_in_time neu registrieren.
# Für Ansaat-Zonen: nächsten Durchgang innerhalb des Zeitfensters berechnen und registrieren.

# Tägliche Berechnung + Jahresreset-Prüfung
async_track_time_change(hass, _daily_calc, hour=0, minute=5, second=0)
# _daily_calc prüft intern: if date.today() == date(year, 1, 1): _year_reset()
# _daily_calc aktualisiert danach für jede Zone sensor.{zone}_naechster_start
#   und registriert _start_zone via async_track_point_in_time neu (Semi/Voll)
# _daily_calc registriert für jede Ansaat-Zone den ersten _ansaat_tick des Tages
#   (= ansaat_von-Uhrzeit heute, sofern modus==Ansaat und status==ON und kein Frost)
# _daily_calc feuert am Ende: hass.bus.async_fire("irrigation_et0_calc_done",
#   {"et0": ..., "methode": ..., "datum": today})

# Startzeiten pro Zone — Semi/Voll (one-shot, nach Zonenende neu registriert)
async_track_point_in_time(hass, _start_zone, next_start_dt)
# _zone_done: sensor.{zone}_naechster_start aktualisieren, next_start_dt persistieren,
#   nächsten Start via async_track_point_in_time neu registrieren

# Ansaat-Modus: chained async_track_point_in_time innerhalb des Zeitfensters
# _ansaat_tick berechnet: next_tick = now() + ansaat_intervall_min
# Wenn next_tick innerhalb von [ansaat_von, ansaat_bis]: Zone in Queue stellen,
#   async_track_point_in_time(hass, _ansaat_tick, next_tick) registrieren
# Wenn next_tick außerhalb Fenster: auf nächsten Tag warten (über _daily_calc)

# Failsafe Trafo
async_track_time_interval(hass, _trafo_failsafe, timedelta(minutes=5))
```

---

## 8. HA-Entities pro Zone

### Sensoren (sensor.*)
| Entity | Beschreibung |
|---|---|
| `{zone}_nfk` | NFK aktuell (mm) |
| `{zone}_nfk_prozent` | NFK aktuell (%) = nfk_mm / nfk_max × 100 — für Lovelace-Balken und S/Z-Marker |
| `{zone}_etc_heute` | ETc heute (mm) |
| `{zone}_regen_heute` | Niederschlag heute (mm) |
| `{zone}_beregnung_heute` | Bewässerung heute (mm) |
| `{zone}_timer` | Countdown aktiver Bewässerung (mm:ss); leer wenn inaktiv |
| `{zone}_cs_zyklen_rest` | Verbleibende C&S-Zyklen (int); 0 wenn kein C&S aktiv |
| `{zone}_naechster_start` | Nächster geplanter Start — `device_class: timestamp`, ISO 8601 UTC; aktualisiert nach Zonenende (`_zone_done`) und nach täglicher 00:05-Berechnung |
| `{zone}_bucket_prognose` | NFK-Prognose morgen (mm) |

### Steuerung
| Entity | Typ | Beschreibung |
|---|---|---|
| `{zone}_modus` | select | Aus / Semi / Voll / Ansaat |
| `{zone}_status` | switch | Zone aktiviert — wenn OFF: keine automatischen Starts, laufende Bewässerung wird sofort gestoppt; ergänzt `Modus = Aus` (schnelle Deaktivierung ohne Modus-Änderung) |
| `{zone}_montag` … `{zone}_sonntag` | switch | Wochentage (Semi-Automatik) |
| `{zone}_dauer` | number | Basisdauer (min) — Semi-Automatik |
| `{zone}_ansaat_intervall` | number | Pause zwischen Ansaat-Durchgängen (min) |
| `{zone}_ansaat_dauer` | number | Dauer pro Ansaat-Durchgang (min) |
| `{zone}_schwellwert` | number | Voll-Automatik Auslöser (%) |
| `{zone}_zielwert` | number | Voll-Automatik Abbruch (%) |
| `{zone}_ansaat_laufzeit_tage` | number | Ansaat aktiv für N Tage (0 = manuell) |
| `{zone}_ansaat_von` | time | Ansaat-Zeitfenster Beginn |
| `{zone}_ansaat_bis` | time | Ansaat-Zeitfenster Ende |
| `{zone}_manuelle_dauer` | number | Manuelle Dauer (min) |
| `{zone}_start` | time | Tägliche Startzeit (Semi-Automatik) |
| `{zone}_start_button` | button | Manueller Start/Stop |
| `{zone}_cs_zyklen` | number | Cycle & Soak: Anzahl Zyklen |
| `{zone}_cs_pause` | number | Cycle & Soak: Pause zwischen Zyklen (min) |

### Globale Entities (pro Anlage)
| Entity | Typ | Beschreibung |
|---|---|---|
| `sensor.et0_fao` | sensor | Tages-ET₀ Penman-Monteith (mm) — immer vorhanden |
| `sensor.et0_hargreaves` | sensor | ET₀ Hargreaves (mm) — nur wenn Hargreaves aktiv |
| `sensor.et0_haude` | sensor | ET₀ Haude (mm) — nur wenn Haude aktiv |
| `sensor.gts` | sensor | Grünlandtemperatursumme |
| `binary_sensor.frost_warnung` | binary_sensor | Frost aktiv (on/off) |
| `binary_sensor.trafo_problem` | binary_sensor | Trafo unavailable oder Soll/Ist-Mismatch (siehe §9a.3) |
| `binary_sensor.et_fallback_active` | binary_sensor | Eine Fallback-ET-Methode ist aktiv weil Inputs fehlen (§9a.2) |
| `binary_sensor.sensoren_ok` | binary_sensor | Alle konfigurierten Wetter-Sensoren liefern valide Werte |
| `select.et_methode` | select | Aktive ET₀-Methode: Penman-Monteith / Hargreaves / Haude |
| `switch.irrigation_dry_run` | switch | Dry-Run global — Berechnung ja, Ventil-Aktion nein (§17.1) |

---

## 9. Datenpersistenz

### Kurzfristig (HA Recorder)
Alle Sensor-Entities werden automatisch vom HA-Recorder in SQLite gespeichert. Standard-Retention: 10 Tage (konfigurierbar).

### Langfristig (HA Statistics)
`sensor.{zone}_nfk` als `state_class: measurement` → Long-term Statistics in HA. Kein externes InfluxDB nötig.

### NFK-Zustandspersistenz über Neustarts
`homeassistant.helpers.storage` mit `STORAGE_VERSION = 1` speichert:

```json
{
  "version": 1,
  "data": {
    "zones": {
      "<zone_uuid>": {
        "name": "Rasenkreis 1",
        "nfk_aktuell": 9.8,
        "letzte_berechnung": "2026-04-28",
        "ansaat_start_datum": null,
        "verlauf": [
          {"datum": "2026-04-22", "nfk_ende": 6.2, "etc": 2.3, "regen": 0, "beregnung": 4.8},
          ...
        ],
        "scheduling": {
          "next_start_dt": "2026-04-29T19:00:00+00:00",
          "next_ansaat_tick": null,
          "running_since": null,
          "active_zone_remaining_min": 0,
          "queue": []
        }
      }
    },
    "globals": {
      "gts": 124.3,
      "gts_jahr": 2026,
      "et_methode": "fao56",
      "letzte_et0_berechnung": "2026-04-28T00:05:00+00:00"
    }
  }
}
```

Verlauf-Retention: 365 Tage rolling (älter wird beim täglichen Save abgeschnitten).

### 9.4 Storage-Migrationen
Bei Schema-Updates (`STORAGE_VERSION` erhöht) wird in `_async_migrate_func` migriert. Migration ist **rückwärtskompatibel** — alte Felder werden gemappt, fehlende Felder mit Defaults gefüllt. Tests in `test_storage_migration.py` decken jede Schema-Version ab.

### 9.5 Catch-up nach Ausfall
Wenn beim Startup oder beim ersten 00:05-Lauf festgestellt wird, dass `letzte_berechnung < heute - 1`:
- Recorder-History wird via `homeassistant.components.recorder.history.get_significant_states` ausgelesen
- Für jeden verpassten Tag: Tagesaggregate (T_min, T_max, RH_min, RH_max, Solar, Wind, Niederschlag) rekonstruieren
- ET₀ + ETc + NFK rückwirkend berechnen, Verlauf eintragen
- `letzte_berechnung` auf heute setzen
- Wenn History-Lücken zu groß sind (>3 fehlende Tage): nicht extrapolieren, sondern Repair-Issue erstellen mit Hinweis auf manuelle NFK-Korrektur

---

## 9a. Reliability & Recovery

### 9a.1 Startup-Recovery offener Ventile
In `__init__.async_setup_entry` nach Coordinator-Init:
1. Trafo-State lesen. Wenn `unavailable`: Repair-Issue, alle automatischen Aktionen blockiert.
2. Für jedes Zonen-Ventil: aktuellen State lesen.
   - `on` und Storage `running_since` gesetzt: berechne `verbleibend = dauer - (now - running_since)`. Wenn `verbleibend > 0`: Zone in Queue als laufend markieren, Timer fortsetzen. Wenn `verbleibend ≤ 0`: Ventil schließen, Trafo prüfen.
   - `on` und kein `running_since` (HA-Crash, unbekannter Zustand): hart schließen + Log-Warning + Event `irrigation_et0_unexpected_state`.
   - `off`: nichts tun.
3. Trafo-Failsafe nach Recovery aufrufen: alle Ventile zu, dann Trafo OFF.

### 9a.2 Sensor-Ausfälle
Wetter-Sensor liefert `unavailable`/`unknown`/`None` oder unsinnige Werte:
- **Clamp-Limits** auf jeden Eingangswert: T ∈ [-50, 60]°C, RH ∈ [0, 100]%, Wind ∈ [0, 50] m/s, Solar ∈ [0, 1500] W/m², Niederschlag ∈ [0, 200] mm/d. Werte außerhalb: auf Limit clampen + Log-Warning.
- **Fallback-Kette für ET₀-Berechnung**:
  1. Aktive Methode (PM / Hargreaves / Haude) wenn alle Inputs valid
  2. Wenn PM-Inputs fehlen: automatisch auf Hargreaves degradieren (nur T_min/T_max nötig) — Sensor `binary_sensor.et_fallback_active` = on
  3. Wenn auch Hargreaves-Inputs fehlen: letzten bekannten ET₀-Wert verwenden, Log-Warning, Repair-Issue erstellen
  4. Wenn keine History: ET₀ = 0 (NFK bleibt stabil) + Issue
- Beim Wechsel auf Fallback wird `binary_sensor.et_fallback_active` aktiv und Event gefeuert.

### 9a.3 Trafo-Probleme
- `binary_sensor.trafo_problem` = on wenn:
  - Trafo-Entity `unavailable` für >2 min
  - Trafo soll ON sein laut Coordinator, ist aber OFF (Mismatch >30s)
  - Trafo soll OFF sein laut Coordinator, ist aber ON nach Failsafe (>30s)
- Wenn aktiv: alle automatischen + manuellen Starts blockiert; laufende Zone wird gestoppt; Notification erstellt.

### 9a.4 Mismatch-Detection
Coordinator vergleicht alle 5 Minuten Soll-Zustand mit Ist-Zustand aller Ventile. Bei Abweichung >30s:
- Falls Soll=ON, Ist=OFF: Repair-Issue, evtl. Hardware-Problem, keine automatische Korrektur.
- Falls Soll=OFF, Ist=ON: Aggressive Schließung (Ventil OFF Befehl alle 5s für 30s), dann Repair-Issue.

### 9a.5 Power-Loss-Safety
Bei jedem Zonen-Start wird `zones.<uuid>.scheduling.running_since` (siehe §9.3) sofort persistiert via `Store.async_save()` (kein Delay-Coalescing). Bei jedem normalen Stop wird der Eintrag auf `null` gesetzt und ebenfalls sofort persistiert. Ist beim Startup ein `running_since` vorhanden, läuft die Recovery-Logik aus §9a.1. Der reguläre Tagesabschluss-Save um 00:05 nutzt das normale Coalescing.

---

## 10. Custom Lovelace Card — 4 Karten

### Karte 1: Übersicht
- Eine Zeile pro Zone: Modus-Badge (farbig), NFK-Balken mit S/Z-Markern (nur bei Voll-Auto), nächster Start, Schnellstart-Button
- Klick auf Zeile → inline Detail-Panel: Status | Zeitplan | Parameter
- Farbschema: gedämpft (kein übermäßiges Bunt)
- Footer: Trafo-Status, ET₀ letzter Berechnungszeitpunkt, Frost-Warnung

### Karte 2: Globale Einstellungen
- Standort (Lat/Lon/Höhe)
- Wetter-Sensor-Zuordnung (pro Parameter: Entity-Auswahl + aktueller Wert)
- Hardware (Trafo-Entity, Frostschutz-Schwelle)

### Karte 3: Berechnungsparameter
- ET-Methode global (Pills)
- Pro Zone (Tabs): Kc, Bodentyp, NFK-Max, Wurzeltiefe, Schwellwert, Zielwert, Durchfluss, Startwert, Ventil-Entity

### Karte 4: Verlauf & Bilanz
- Zonenauswahl (Tabs)
- Zeitbereich: 7 / 14 / 30 Tage / Jahr
- SVG-Chart: ET₀ (orange Balken), Regen (blau), Beregnung (grün), NFK-Linie (lila), S/Z-Linien gestrichelt
- Kurzübersicht: ETc gesamt, Regen, Beregnung, NFK aktuell, ET₀ Ø/Tag

---

## 11. Hardware-Übersicht (bestehende Anlage)

### Magnetventile (DRS8-Aktoren)
| Zone | Entity | HomeMatic Kanal |
|---|---|---|
| MV1 (Garten) | `switch.drs8_schaltaktor_garten_bewasserung_mv1_ch22` | 001618A99C5DC2:22 |
| MV2 (Garten) | `switch.drs8_schaltaktor_garten_bewasserung_mv2_ch26` | 001618A99C5DC2:26 |
| MV3 (Garten) | `switch.drs8_schaltaktor_garten_bewasserung_mv3_ch30` | 001618A99C5DC2:30 |
| MV4 (Bewäss.) | `switch.drs8_schaltaktor_bewasserung_mv4_ch26` | 001618A98F988F:26 |
| MV5 (Bewäss.) | `switch.drs8_schaltaktor_bewasserung_mv5_ch30` | 001618A98F988F:30 |
| Trafo 24V | `switch.drs8_schaltaktor_bewasserung_trafo_ch14` | 001618A98F988F:14 |

### Bestehende HA-Entities (werden ersetzt/zusammengeführt)
Vorhandene `input_number`, `input_select`, `input_datetime`, `switch` und `sensor` Entities für die 5 Zonen bleiben initial parallel bestehen bis Migration abgeschlossen.

---

## 12. Bekannte Bugs in der Node-RED-Implementierung (zu korrigieren)

1. **Lat/Lon vertauscht**: `latitudeDegrees = 8.74` (Längengrad), `longitudeDegrees = 50.37` (Breitengrad) — FAO benötigt korrekten Breitengrad ~50.37°N
2. **Elevation double-convert**: `163 * 3.28084` ft → dann wieder `FttoM()` zurück — im neuen Code direkt 163m verwenden

---

## 13. Entscheidungen

- [x] **Card Sprache**: i18n (DE/EN) — `translations/de.json` und `translations/en.json` wie in Section 2.1 vorgesehen.
- [x] **Cycle & Soak**: pro Zone konfigurierbar (via `{zone}_cs_zyklen` / `{zone}_cs_pause` in Section 8).
- [x] **Vorschau-Berechnung NFK-Prognose**: Morgen-Prognose via `weather.get_forecasts` Service (DWD `weather.*`-Entity). ETc_morgen = ET₀_hargreaves_prognose × Kc × Ka; Niederschlag aus `precipitation`-Feld. `{zone}_bucket_prognose` = nfk_heute − ETc_morgen + regen_morgen.
- [x] **Hot-Reload ohne HA-Neustart**: Pflicht-Anforderung. Siehe §2.9.

---

## 14. HACS-Integration

### 14.1 `hacs.json` (Repo-Root)
```json
{
  "name": "Irrigation ET₀",
  "render_readme": true,
  "country": ["DE", "AT", "CH"],
  "homeassistant": "2024.10.0",
  "zip_release": false
}
```

### 14.2 `manifest.json`
```json
{
  "domain": "irrigation_et0",
  "name": "Irrigation ET₀",
  "version": "0.1.0",
  "documentation": "https://github.com/<user>/irrigation-ha",
  "issue_tracker": "https://github.com/<user>/irrigation-ha/issues",
  "codeowners": ["@<user>"],
  "iot_class": "local_polling",
  "integration_type": "service",
  "dependencies": [],
  "requirements": [],
  "config_flow": true
}
```
**Hinweis**: Keine `requirements`-Einträge — PyETo ist vendored (siehe §2.9 Punkt 6), damit kein HA-Neustart bei Updates.

### 14.3 Brands-PR
Logo + Icon (256×256 PNG) an `home-assistant/brands` PR-en, separater Workflow nach Veröffentlichung.

### 14.4 README-Pflichtinhalte
- Screenshots der 4 Karten
- Installation via HACS (Custom Repo, später Default)
- Config-Flow-Walkthrough mit Bildern
- Troubleshooting-FAQ
- Versionierung (semver, CHANGELOG)
- Lizenz, Beitragsleitfaden

### 14.5 Releases
- Semver-Tags `v0.1.0`, `v0.1.1` …
- GitHub Action `release.yml`: bei Push auf `main` mit Tag → automatisch Release erstellen, ZIP nicht nötig (HACS klont direkt)
- CHANGELOG.md gepflegt (Keep a Changelog)

---

## 15. Services (`services.yaml`)

**Zonen-Identifikation in Services:** Der Service nimmt eine `zone`-Entity (das `select.{zone}_modus`-Entity dieser Zone) als Selector. Aus der Entity-ID extrahiert der Service-Handler die interne `zone_id` (UUID). So bleibt der UI-Picker bedienbar, ohne dass der User UUIDs eintippen muss.

```yaml
start_zone:
  name: Zone starten
  description: Startet eine Zone manuell für N Minuten
  fields:
    zone:
      required: true
      selector:
        entity:
          integration: irrigation_et0
          domain: select
    dauer_min:
      required: true
      selector: { number: { min: 1, max: 240, unit_of_measurement: min } }

stop_zone:
  name: Zone stoppen
  fields:
    zone:
      required: true
      selector:
        entity: { integration: irrigation_et0, domain: select }

stop_all:
  name: Alle Zonen stoppen
  description: Stoppt alle Zonen und schaltet Trafo ab

recalculate_now:
  name: ET₀ jetzt neu berechnen
  description: Triggert sofort die tägliche Berechnung außer der Reihe

set_nfk:
  name: NFK manuell setzen
  description: Korrigiert den NFK-Wert einer Zone (z.B. nach Starkregen-Sensor-Lücke)
  fields:
    zone:
      required: true
      selector:
        entity: { integration: irrigation_et0, domain: select }
    value_mm:
      required: true
      selector: { number: { min: 0, max: 100, unit_of_measurement: mm } }

skip_next_run:
  name: Nächsten Lauf überspringen
  fields:
    zone:
      required: true
      selector:
        entity: { integration: irrigation_et0, domain: select }

import_node_red_state:
  name: NFK aus Node-RED importieren
  description: Migrations-Service — liest input_number.{zone}_bucket-Entities und übernimmt Werte als NFK-Startwerte
```

Alle Services sind in `__init__.async_setup_entry` via `hass.services.async_register` registriert und in `async_unload_entry` wieder entfernt (für sauberen Reload).

---

## 16. Event Bus (für Automatisierungen)

```python
hass.bus.async_fire("irrigation_et0_zone_started",
    {"zone_id": ..., "name": ..., "modus": ..., "dauer_min": ...})

hass.bus.async_fire("irrigation_et0_zone_finished",
    {"zone_id": ..., "name": ..., "beregnet_mm": ..., "abgebrochen": False})

hass.bus.async_fire("irrigation_et0_frost_lock",
    {"temperatur": ..., "schwelle": ...})

hass.bus.async_fire("irrigation_et0_frost_release",
    {"temperatur": ...})

hass.bus.async_fire("irrigation_et0_calc_done",
    {"et0": ..., "methode": ..., "datum": ...})

hass.bus.async_fire("irrigation_et0_fallback_active",
    {"reason": "missing_pm_inputs", "fallback_method": "hargreaves"})

hass.bus.async_fire("irrigation_et0_unexpected_state",
    {"entity_id": ..., "expected": ..., "actual": ...})
```

Alle Events sind in `const.py` als Konstanten definiert (`EVENT_ZONE_STARTED` etc.).

---

## 17. UX & Sicherheit

### 17.1 Dry-Run-Modus
Globaler Switch `switch.irrigation_dry_run`:
- Wenn ON: alle Berechnungen laufen normal, Events werden gefeuert, Sensoren aktualisiert — aber Trafo + Ventile werden NICHT geschaltet
- Default beim ersten Setup: ON (sicheres Onboarding)
- User schaltet bewusst OFF wenn er die Werte plausibel findet

### 17.2 NFK-manuelle-Korrektur
- Service `irrigation_et0.set_nfk` (siehe §15)
- Im UI: Karte 3 enthält pro Zone einen "NFK korrigieren"-Button → Dialog mit Slider + Speichern

### 17.3 Notifications (HA persistent_notification)
Bei kritischen Ereignissen wird `persistent_notification.create` aufgerufen:
- Frost-Lock aktiviert (mit Temperatur)
- Sensor-Ausfall (Wetter oder Ventil)
- Trafo-Problem
- ET-Fallback aktiv
- Unerwartetes Ventil-State (Crash-Recovery)
- Migration nötig (Storage-Schema-Update)

User kann Notifications individuell abschalten via Options.

### 17.4 Trockenlauf-Visualisierung
Karte 1 zeigt bei Dry-Run einen orangen Banner "DRY-RUN: Ventile werden NICHT geschaltet".
Karte 4 zeigt im Verlauf eine zusätzliche Linie "geplante Beregnung" wenn Dry-Run aktiv war (graue Striche).

### 17.5 Manueller Override
Wenn Zone via Auto-Modus läuft und User drückt "Stop"-Button:
- Aktuelle Bewässerung wird sauber gestoppt (Ventil OFF, Trafo OFF wenn keine andere Zone)
- `next_start_dt` für heute wird auf "morgen" gesetzt (heute keine erneute Auslösung)
- Event `irrigation_et0_zone_finished` mit `abgebrochen: True`

---

## 18. Tests

### 18.1 Test-Stack
- `pytest`
- `pytest-homeassistant-custom-component` (HA-Test-Fixtures)
- `pytest-asyncio`
- `pytest-cov` (Ziel: ≥85% Coverage)
- `freezegun` für Zeitsteuerung

### 18.2 Test-Module
| Datei | Coverage |
|---|---|
| `test_et0_calculator.py` | FAO-56 Annex 6 Beispielwerte (Vergleich mit Referenztabelle ±0.1 mm), Hargreaves, Haude, Edge-Cases (negative Solarstrahlung, T_min > T_max) |
| `test_water_balance.py` | NFK-Bilanz: Start-Werte, Clamp 0/max, Regen-Übersättigung, Beregnung negativ unmöglich, Verlauf-Retention 365d |
| `test_gts_calculator.py` | Gewichte Jan/Feb/restl., Reset 1.1., negative T ignoriert |
| `test_coordinator.py` | Trafo-Sequenz (ON-Wait-ON, OFF-Wait-Check), Queue (FIFO, parallele Anfragen), Frost-Lock blockiert alle Modi, `{zone}_status=OFF` stoppt nur diese Zone, Fallback-Kette PM→Hargreaves→Last→0 |
| `test_recovery.py` | HA-Crash mit offenem Ventil → Recovery, missed days catch-up, Trafo-Mismatch-Detection |
| `test_config_flow.py` | Erst-Setup alle Schritte, OptionsFlow-Reload, ungültige Inputs (negative Höhe, Lat>90) |
| `test_storage_migration.py` | Migration v1→v2 (Platzhalter für Zukunft), Default-Werte für fehlende Felder |
| `test_services.py` | Alle Services mit gültigen + ungültigen Argumenten, zone-Entity → zone_id Mapping |
| `test_repairs.py` | Missing-Entity-Issue erstellt, Resolve-Flow, Auto-Resolve wenn Entity zurückkehrt |
| `test_diagnostics.py` | Diagnostics-Export enthält alle Sektionen, sensible Daten redacted |
| `test_unload_reload_cycle.py` | Setup → 10× Reload → Unload, keine offenen Listener (Hot-Reload-Garantie aus §2.9) |
| `test_card_data_contract.py` | Sensor-Entitäten liefern erwartete Attribute für Custom Card |

### 18.3 CI (`.github/workflows/ci.yml`)
- Matrix: HA-Versionen `["2024.10.0", "2025.1.0", "latest"]`, Python `["3.12", "3.13"]`
- Schritte: lint (ruff), type-check (mypy), pytest mit Coverage, hassfest
- Bei PR: Coverage-Diff-Kommentar via `pytest-cov` + `codecov`

### 18.4 HACS-Validator
`.github/workflows/hacs-validate.yml` läuft `hacs/action@main` bei jedem Push.

### 18.5 Manuelle Test-Checkliste
- Trafo-Failsafe: Ventil manuell offen lassen → nach max. 5 min Trafo OFF
- Frost-Auslöser: Sensor-Wert <4°C → laufende Zone stoppt + Notification
- HA-Restart mid-zone: Ventil bleibt offen → nach Reboot Recovery + Timer-Resume
- HACS-Update: Version bump → Reload via OptionsFlow → kein HA-Neustart
- Sensor-Ausfall: Wetter-Sensor `unavailable` → Fallback-Kette greift
- Catch-up: HA 3 Tage aus → Startup berechnet rückwirkend

---

## 19. Rollout-Plan (Node-RED → irrigation_et0)

### Phase 1: Lokale Entwicklung (Wochen 1–2)
- Repo `irrigation-ha` mit Struktur aus §2.1 anlegen
- Symlink `~/.homeassistant/custom_components/irrigation_et0` → `~/irrigation-ha/custom_components/irrigation_et0`
- Pytest-Suite + GitHub Actions einrichten
- Coordinator + ET₀-Calculator + Water-Balance + Storage zuerst (ohne UI)

### Phase 2: Schatten-Betrieb (Wochen 3–6)
- Integration installiert, **Dry-Run = ON** (Default)
- Alte Node-RED-Flows laufen parallel
- Karten installiert, Vergleich täglich: NFK-Werte, geplante Starts, ET₀
- Migrations-Service nutzt vorhandene `input_number.{zone}_bucket`-Werte als NFK-Startwerte

### Phase 3: Soft-Cutover (Woche 7)
- Eine Zone (z.B. Tropfkreis 2) aus Node-RED entfernt, übernimmt irrigation_et0
- 1 Woche scharfes Monitoring dieser Zone
- Bei Erfolg: weitere Zonen migriert
- Alte Node-RED-Flows deaktivieren (nicht löschen) — schnelles Rollback möglich

### Phase 4: Vollbetrieb (Woche 8+)
- Alle Zonen über irrigation_et0
- Dry-Run = OFF
- Alte Helper-Entities bleiben 1 Saison parallel (Read-only-Vergleich), dann gelöscht

### Phase 5: HACS Custom Repository (sofort nach Phase 1)
- GitHub Repo öffentlich
- HACS → Custom Repository → URL eintragen
- Versions-Updates fließen via HACS-Update (kein HA-Neustart, siehe §2.9)

### Phase 6: HACS Default + Brands (nach 1 Saison Stabilität)
- PR an `hacs/default`
- PR an `home-assistant/brands` mit Logo
- Wartung: Issues, PRs, Roadmap

---

## 20. Roadmap (post-v1)

### v0.1 MVP-Scope (vollständig)
- Alle 4 Modi: Aus / Semi / Voll / Ansaat
- Cycle & Soak pro Zone
- Frostschutz (binary_sensor + Auto-Stop)
- Trafo-Sequenz inkl. Failsafe und Mismatch-Detection
- FIFO-Queue
- Recovery offener Ventile beim Startup (§9a.1)
- Catch-up bei verpassten Tagen (§9.5)
- Sensor-Fallback-Kette PM → Hargreaves → Last → 0 (§9a.2)
- Alle 4 Karten (Übersicht, Globale Settings, Berechnungsparameter, Verlauf)
- Services aus §15
- Events aus §16
- Dry-Run-Switch (§17.1)
- Notifications für kritische Ereignisse (§17.3)
- Diagnostics + Repairs (§2.7, §2.8)
- HACS Custom Repository
- Pytest-Suite ≥85% Coverage
- i18n DE/EN
- Hot-Reload ohne HA-Neustart (§2.9)
- Migrations-Service `import_node_red_state`

### Roadmap nach v0.1

| Version | Feature |
|---|---|
| v0.2 | Wettervorhersage-Integration für Skip-Logik (z.B. "morgen >5mm Regen → heute nicht bewässern") |
| v0.3 | Multi-Anlagen-Support (mehrere Config Entries pro HA) |
| v0.4 | Statistik-Dashboard mit Saisonvergleich, m³-Verbrauch |
| v0.5 | Smart-Scheduling: ET₀-Vorhersage 7d → optimaler Bewässerungszeitpunkt minimiert Verdunstungsverluste |
| v1.0 | HACS Default, Brands-Logo, Production-grade, 1+ Saison Stabilität |
