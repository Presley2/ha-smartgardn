# SmartGardn ET₀ — Comprehensive Code Audit Report
**Datum:** 2026-05-01  
**Status:** 150/150 Tests passing, aber kritische Issues identifiziert

---

## Executive Summary

Audit ergebnis: **5 CRITICAL**, **8 MEDIUM**, **8 LOW** Issues gefunden.

Das System funktioniert, aber hat einige kritische Fehler die zu:
- **Crashes** (Unsafe dict access bei Zone-Rekonfiguration)
- **Datenverlust** (Race conditions in startup recovery)
- **Silent failures** (Frost-lock funktioniert nicht mit neuer temp_entity config)
- **Performance issues** (Cycle & Soak blockiert Coordinator)

---

## CRITICAL ISSUES (Sofort beheben!)

### 🔴 Issue #1: Unsafe Dict Access During Zone Reconfiguration
**File:** `coordinator.py:490, 508, 826`  
**Risk:** Runtime crash wenn Zone während Bewässerung gelöscht wird  
**Scenario:**
1. Zone läuft (z.B. Valve offen)
2. User löscht die Zone aus Config
3. Coordinator versucht auf `entry.data["zones"][zone_id]` zuzugreifen
4. KeyError → Coordinator crashed

```python
# ❌ CURRENT (UNSAFE):
valve_id = self.entry.data["zones"][self.running.zone_id]["valve_entity"]

# ✅ FIX:
zone_cfg = self.entry.data.get("zones", {}).get(self.running.zone_id)
if not zone_cfg:
    _LOGGER.error("Zone %s not found", self.running.zone_id)
    self.running = None
    await self._run_next_in_queue()
    return
```

---

### 🔴 Issue #2: Frost Lock funktioniert nicht mit neuer Config
**File:** `coordinator.py:814`  
**Risk:** System kann bei Frost bewässern → Pflanzen-Schaden  
**Impact:** CRITICAL - Funktional falsch

**Problem:**
- Neue `config_flow.py` akzeptiert `temp_entity` (single merged sensor)
- Aber Frost-Check nur auf `temp_min_entity` implementiert
- Wenn nur `temp_entity` konfiguriert → Frost-Check macht nichts

```python
# ❌ CURRENT (NUR TEMP_MIN):
t_min_state = self.hass.states.get(self.entry.data.get("temp_min_entity"))

# ✅ FIX:
temp_entity = self.entry.data.get("temp_entity")
if temp_entity:
    t_min_state = self.hass.states.get(temp_entity)
else:
    t_min_state = self.hass.states.get(self.entry.data.get("temp_min_entity"))
```

---

### 🔴 Issue #3: Race Condition in Startup Recovery
**File:** `coordinator.py:145-201`  
**Risk:** Tägliche ET₀/NFK Berechnungen können gelöscht werden  
**Impact:** CRITICAL - Datenverlust

**Problem:**
```python
# _startup_recovery() läuft
zone_data = self._storage_data["zones"][zone_id]
running_since = zone_data.get("scheduling", {}).get("running_since")

# GLEICHZEITIG läuft _daily_calc():
zone_data["scheduling"]["running_since"] = None
await self.storage.async_save_immediate()  # <- Speichert NICHTS

# Später überschreibt Recovery den state der _daily_calc()
zone_data["scheduling"]["running_since"] = str(dt.now())
await self.storage.async_save_immediate()  # <- Speichert alte Daten!
```

**Lösung:** Startup recovery VORHER laufen lassen, nicht parallel:

```python
async def async_setup(self) -> None:
    self._storage_data = await self.storage.async_load()
    
    # 1. ERST Startup Recovery (blocking)
    await self._startup_recovery()
    
    # 2. DANN andere scheduled tasks registrieren
    unsub = async_track_time_change(self.hass, self._daily_calc, ...)
    self._unsubs.append(unsub)
```

---

### 🔴 Issue #4: Entity ID Parsing ist unsicher
**File:** `repairs.py:29, 48, 101, 118`  
**Risk:** False positives bei Entity-Rekonstruktion, Security  
**Impact:** CRITICAL - Logic error

**Problem:**
```python
# ❌ Naiv: Entity IDs mit "." → "_" und zurück
entity_id = "automation.zone_1_pump"
issue_id = "missing_entity_" + entity_id.replace(".", "_")
# issue_id = "missing_entity_automation_zone_1_pump"

# Reverse:
entity_id_reconstructed = issue_id.split("_", 2)[2].replace("_", ".")
# Result: "automation.zone.1.pump" ❌ FALSCH!
# Sollte: "automation.zone_1_pump"
```

**Lösung:** Base64 encoding oder JSON:

```python
import base64

def safe_encode_entity_id(entity_id: str) -> str:
    return base64.urlsafe_b64encode(entity_id.encode()).decode().rstrip('=')

def safe_decode_entity_id(encoded: str) -> str:
    padding = 4 - (len(encoded) % 4)
    encoded = encoded + '=' * padding if padding != 4 else encoded
    return base64.urlsafe_b64decode(encoded).decode()
```

---

### 🔴 Issue #5: Cycle & Soak blockiert den Coordinator
**File:** `coordinator.py:512-517`  
**Risk:** Keine Sensor-Updates während C&S-Pause, keine Fehler-Erkennung  
**Impact:** CRITICAL - Performance

**Problem:**
```python
# ❌ CURRENT: asyncio.sleep blockiert Coordinator
if self.running.cs_remaining > 0:
    self.running.cs_remaining -= 1
    await asyncio.sleep(self.running.cs_pause_min * 60)  # ← 10+ minutes blocked!
    await self.async_enqueue_start(...)
```

Während dieser 10 Minuten:
- Keine Sensor-Updates
- Keine Fehler-Detektion (z.B. Trafo ausfällt)
- Keine Frost-Checks

**Lösung:** `async_track_point_in_time` statt Sleep

---

## MEDIUM ISSUES (Diese Woche fixen)

### 🟡 Issue #6: Recorder.get_history() hat keinen Timeout
**File:** `coordinator.py:237-244`  
**Symptom:** ET₀-Berechnungen hängen wenn Recorder langsam ist

### 🟡 Issue #7: Drip Zone Logic unvollständig
**File:** `coordinator.py:582-584`  
**Problem:** Keine Audittrail für DRIP-Zonen, unklar wie sie gesteuert werden

### 🟡 Issue #8: Solar PAR Konversion ist falsch
**File:** `et0_calculator.py:26`  
**Impact:** ET₀ wird um ~2.3× zu hoch berechnet wenn PAR-Sensor verwendet

Die aktuelle Formel:
```python
"par": 0.51,  # ← FALSCH! Sollte ~0.0219 sein
```

Korrekt:
```python
"par": 0.0219,  # µmol/m²/s to W/m²
```

### 🟡 Issue #9: DWD Forecast RH_min/max sind Approximationen
**File:** `dwd_forecast.py:196-199`  
**Impact:** ±10% Fehler in ET₀ wenn RH geschätzt wird

### 🟡 Issue #10: Entity ID Parsing Fragility
**File:** `coordinator.py:916-930`  
**Problem:** String-Slicing statt Regex, fragil mit Edge-cases

### 🟡 Issue #11: Insufficient Input Validation
**File:** `config_flow.py:164-189`  
**Missing:** longitude range check, elevation validation, Kc plausibility

### 🟡 Issue #12: Temp-Entity Fallback ist inkonsistent
**File:** `coordinator.py:276-285`  
**Problem:** Code unterstützt beide `temp_entity` und `temp_min_entity`, aber inkonsistent

### 🟡 Issue #13: Migration Function ist Stub
**File:** `storage.py:94-96`  
**Problem:** `async_migrate()` macht nichts, zukünftige Migrations brauchen manuelle Migration

---

## LOW ISSUES (Nice-to-have Improvements)

- **Issue #14:** Logger inconsistency
- **Issue #15:** Magic numbers sollten in const.py sein
- **Issue #16:** Code duplication (`running_since = None`)
- **Issue #17:** Missing NFK documentation
- **Issue #18:** Missing type hints
- **Issue #19:** Inconsistent event bus usage
- **Issue #20:** Verbose `_build_entry_data()` function
- **Issue #21:** Redundant ternary operators

---

## Test Coverage Gaps

Tests existieren (150 passing), aber folgende Szenarien sind nicht getestet:

1. **Zone-Rekonfiguration während Bewässerung**
   ```python
   # Test: Zone wird gelöscht während running_since != None
   # Erwartet: Kein Crash, Zone wird ordnungsgemäß gestoppt
   ```

2. **Startup Recovery mit Race Condition**
   ```python
   # Test: _startup_recovery() und _daily_calc() laufen parallel
   # Erwartet: Keine Überschreibung von Daten
   ```

3. **Frost Lock mit neuem temp_entity**
   ```python
   # Test: Nur "temp_entity" konfiguriert, Temperatur < frost_threshold
   # Erwartet: Irrigation wird blockiert
   ```

4. **Recorder Timeout**
   ```python
   # Test: Recorder.get_history() hängt 30+ Sekunden
   # Erwartet: Coordinator bleibt responsive, history wird skipped
   ```

5. **Cycle & Soak mit langen Pausen**
   ```python
   # Test: 20-minute C&S pause, Sensor-Update sollte ankommen
   # Erwartet: Sensor wird aktualisiert, nicht blockiert
   ```

---

## Fix Priority & Estimated Effort

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| #2 (Frost logic) | CRITICAL | 30 min | **NOW** |
| #1 (Dict access) | CRITICAL | 1 h | **NOW** |
| #4 (Entity ID) | CRITICAL | 2 h | **This week** |
| #3 (Race cond.) | CRITICAL | 1.5 h | **This week** |
| #5 (C&S blocking) | CRITICAL | 2 h | **This week** |
| #6-13 (MEDIUM) | MEDIUM | 1-2 h each | **Next 2 weeks** |
| #14-21 (LOW) | LOW | 30 min - 1 h | **Backlog** |

---

## Recommendations

1. **Add configuration validation** in config_flow
2. **Use type-safe entity parsing** (Base64 or JSON)
3. **Add zone-existence checks** before all dict accesses
4. **Refactor C&S to use event scheduling** instead of sleep
5. **Document NFK, ET₀, GTS calculations** thoroughly
6. **Add integration tests** for edge cases
7. **Implement proper migration framework** for storage schema
8. **Use consistent temperature entity fallback** throughout

---

## Files to Review First

1. `coordinator.py` — Main logic, has multiple critical issues
2. `config_flow.py` — Input validation
3. `repairs.py` — Entity ID parsing
4. `et0_calculator.py` — Solar conversion accuracy

