# irrigation_et0 — Design Spec
**Datum:** 2026-04-28  
**Status:** Entwurf — zur Implementierung freigegeben

---

## 1. Ziel

Eine native Home Assistant Custom Component (`irrigation_et0`) zur wissenschaftlich fundierten Bewässerungssteuerung auf Basis des FAO-56 Penman-Monteith-Modells mit täglicher Bodenwasserbilanz (NFK) pro Zone. Ablösung der bisherigen Node-RED + InfluxDB Lösung. Vollständig unabhängig von externen Diensten.

---

## 2. Systemarchitektur

### 2.1 Komponentenstruktur

```
custom_components/irrigation_et0/
  __init__.py              # Setup, Config Entry, Services
  config_flow.py           # UI-geführte Erstkonfiguration
  coordinator.py           # Zentrale Logik, Scheduling, Trafo-Sequenz
  et0_calculator.py        # FAO-56 Penman-Monteith (via PyETo)
  water_balance.py         # NFK-Bilanzmodell pro Zone
  gts_calculator.py        # Grünlandtemperatursumme
  storage.py               # Persistenz (HA Storage API)
  sensor.py                # ET₀, NFK, Timer, Prognose-Sensoren
  binary_sensor.py         # Frost-Warnung
  switch.py                # Zonen-Status, Wochentage
  select.py                # Automatik-Modus pro Zone, ET-Methode global
                           # ET-Methode-Änderung löst async_call_later → hass.config_entries.async_reload aus
                           # damit bedingte Sensoren (et0_hargreaves / et0_haude) neu registriert werden
  number.py                # Dauer, Intervall, Durchfluss
  button.py                # Manueller Start pro Zone
  time.py                  # Startzeit, Ansaat-Zeitfenster (von/bis)
  const.py                 # Konstanten
  manifest.json            # HACS-Metadaten
  translations/
    de.json
    en.json
  services.yaml

custom_components/irrigation_et0_card/   # Lovelace Custom Card
  irrigation-et0-card.js
  irrigation-et0-card-editor.js
```

### 2.2 Abhängigkeiten

- `PyETo` — FAO-56 ET₀-Berechnung (Python-Bibliothek)
- `homeassistant.helpers.storage` — Persistenz NFK-Verlauf
- `homeassistant.helpers.event` — `async_track_time_change`, `async_track_point_in_time`
- HA Recorder — automatische Sensor-Historie

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
| `select.et_methode` | select | Aktive ET₀-Methode: Penman-Monteith / Hargreaves / Haude |

---

## 9. Datenpersistenz

### Kurzfristig (HA Recorder)
Alle Sensor-Entities werden automatisch vom HA-Recorder in SQLite gespeichert. Standard-Retention: 10 Tage (konfigurierbar).

### Langfristig (HA Statistics)
`sensor.{zone}_nfk` als `state_class: measurement` → Long-term Statistics in HA. Kein externes InfluxDB nötig.

### NFK-Zustandspersistenz über Neustarts
`homeassistant.helpers.storage` speichert täglich:

```json
{
  "zone_id": {
    "nfk_aktuell": 9.8,
    "letzte_berechnung": "2026-04-28",
    "verlauf": [
      {"datum": "2026-04-22", "nfk_ende": 6.2, "etc": 2.3, "regen": 0, "beregnung": 4.8},
      ...
    ]
  }
}
```

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
