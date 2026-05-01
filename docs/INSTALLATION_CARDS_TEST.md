# SmartGardn ET₀ - Installation & Card Testing Guide

Dieses Dokument beschreibt die vollautomatische Installation und das Testen der Custom Lovelace Cards.

---

## 🚀 Automatische Installation

Die Custom Cards werden **vollautomatisch** beim Laden des Integration registriert. Kein manuelles Setup nötig!

### Schritt 1: Installation der Integration

#### Via HACS (Empfohlen)
```
1. Öffne Home Assistant → Settings → Devices & Services → HACS
2. Klick "Custom repositories"
3. Füge hinzu: https://github.com/Presley2/ha-smartgardn
4. Kategorie: Integration
5. Suche nach "SmartGardn ET₀" → Install
6. Home Assistant neustarten
```

#### Manuell
```bash
1. Repository klonen: git clone https://github.com/Presley2/ha-smartgardn
2. Kopiere custom_components/smartgardn_et0/ zu <ha-config>/custom_components/
3. Home Assistant neustarten
```

### Schritt 2: Config Entry erstellen

```
1. Settings → Devices & Services → Create Integration
2. Suche nach "SmartGardn ET₀"
3. Folge dem Setup Flow (Name, GPS, Sensoren, Zonen)
4. Integration ist jetzt aktiv!
```

### Schritt 3: Cards sollten jetzt verfügbar sein

Die Static Path wird beim Setup automatisch registriert:
- Static Files unter `/smartgardn_et0_cards/`
- Lovelace Resources werden automatisch registriert (Storage Mode)

---

## 🧪 Testing der Cards auf Live Home Assistant

### Test 1: Card Resources überprüfen

**Browser Developer Tools (F12):**
```javascript
// Schau ob die Resources geladen sind
console.log(document.querySelector('head'))
  .querySelectorAll('script[src*="smartgardn"]')
```

**Oder via HTTP:**
```bash
# Test 1: Statische Dateien zugänglich?
curl -i http://ha.local:8123/smartgardn_et0_cards/overview-card.js

# Test 2: Returns 200?
curl -I http://ha.local:8123/smartgardn_et0_cards/overview-card.js | grep 200
```

### Test 2: Card im Dashboard hinzufügen

**Storage Mode (UI Editor):**
```
1. Home Assistant → Lovelace Dashboard
2. Klick Bearbeiten (Stift-Icon)
3. Klick + (Neue Karte)
4. Wähle "Custom: Irrigation Overview Card"
5. entry_id eingeben
```

**YAML Mode:**
```yaml
views:
  - title: Garten
    cards:
      - type: custom:irrigation-overview-card
        entry_id: abc123
```

### Test 3: Daten anzeigen

Nach Hinzufügen der Card sollte folgendes angezeigt werden:

**Overview Card:**
- ✅ Zone Namen
- ✅ NFK% (Bodenfeuchte %)
- ✅ ETc (Evapotranspiration)
- ✅ Regen heute
- ✅ Nächster Start (Zeitstempel)
- ✅ Modus (Aus/Semi/Voll/Ansaat)

**Settings Card:**
- ✅ Schieberegler für Schwellwerte
- ✅ Dropdowns für Einstellungen
- ✅ Änderungen speicherbar

**History Card:**
- ✅ 30-Tage Trend-Kurven
- ✅ NFK, ETc, Regen, Bewässerung
- ✅ 3-Tage Forecast

**Ansaat Card:**
- ✅ Bewässerungs-Timeline
- ✅ Intensives Bewässerungsschema

---

## 🔍 Debugging

### Problem: Cards werden nicht angezeigt

**Check 1: Static Path registriert?**
```
Home Assistant Logs (Settings → System → Logs):
Suche nach: "smartgardn_et0" und "Registered static path"
```

**Check 2: Browser Console Fehler**
```
F12 → Console → Suche nach Rot-gefärbten Fehlern
```

**Check 3: Network Tab**
```
F12 → Network → Suche nach smartgardn_et0_cards
- Status sollte 200 sein
- Größe > 0 KB
```

### Problem: Cards laden aber zeigen keine Daten

**Check 1: entry_id korrekt?**
```
Settings → Devices & Services → SmartGardn ET₀
Entry ID aus URL kopieren oder Details anschauen
```

**Check 2: Entities existieren?**
```
Settings → Devices & Services → SmartGardn ET₀ → Entities
Suche nach sensor.*_nfk_prozent oder ähnliches
```

**Check 3: Browser Console für Fehler**
```javascript
// Manuell Entities abrufen
Object.keys(window.hass.states)
  .filter(id => id.includes('sensor.') && id.includes('nfk'))
```

---

## 📊 Erwartete Entities

Nach erfolgreicher Installation sollten folgende Entities existieren:

### Pro Zone
- `sensor.<entry_id>_<zone>_nfk` — Bodenfeuchte (mm)
- `sensor.<entry_id>_<zone>_nfk_prozent` — Bodenfeuchte (%)
- `sensor.<entry_id>_<zone>_etc_heute` — ETc heute (mm)
- `sensor.<entry_id>_<zone>_regen_heute` — Regen heute (mm)
- `sensor.<entry_id>_<zone>_beregnung_heute` — Bewässerung heute (mm)
- `select.<entry_id>_<zone>_modus` — Bewässerungsmodus

### Global
- `sensor.<entry_id>_et0_fao56` — Referenz ET₀ (FAO-56)
- `sensor.<entry_id>_gts` — Grünlandtemperatursumme
- `binary_sensor.<entry_id>_frost_warnung` — Frost-Warnung

---

## 🎯 Full Integration Test Checklist

### Phase 1: Installation ✅
- [ ] Integration aus HACS/Manual installiert
- [ ] Home Assistant neu gestartet
- [ ] Config Entry erstellt

### Phase 2: Entities ✅
- [ ] Sensoren sind in der UI sichtbar
- [ ] Weather-Sensoren sind verbunden
- [ ] Valve-Entities sind konfiguriert

### Phase 3: Cards Auto-Registration ✅
- [ ] Static Path unter `/smartgardn_et0_cards/` antwortet
- [ ] Card JS-Dateien sind laden (HTTP 200)
- [ ] Browser Console: keine roten Fehler

### Phase 4: Card Rendering ✅
- [ ] Overview Card rendert
- [ ] Echte Daten werden angezeigt (nicht "undefined")
- [ ] Settings Card funktioniert
- [ ] History Card lädt Daten

### Phase 5: Funktionalität ✅
- [ ] Manuelle Zone-Aktivierung funktioniert
- [ ] NFK-Werte aktualisieren sich
- [ ] Mode-Selector funktioniert
- [ ] Forecast wird angezeigt (falls DWD konfiguriert)

---

## 🐛 Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| "Custom element not found" | Card JS nicht geladen | Static Path prüfen, HA neu starten |
| "Cannot read property 'states'" | entry_id falsch | Entry ID prüfen |
| "undefined" statt Werten | Entities nicht erstellt | Config Entry vollständig? |
| HTTP 404 auf `/smartgardn_et0_cards/` | Static Path nicht registriert | HA neu starten |
| Cards im Lovelace Editor nicht sichtbar | Storage Mode nicht aktiviert | Via YAML registrieren |

---

## 📱 Test auf verschiedenen Clients

Die Cards sollten auf allen Clients funktionieren:

- [ ] Desktop Browser (Chrome)
- [ ] Safari
- [ ] Mobile Browser
- [ ] Home Assistant iOS App
- [ ] Home Assistant Android App

Falls die App nicht funktioniert → Lovelace Cache löschen:
```
Settings → Devices & Services → Lovelace
Click "Clear cache"
```

---

## 🚀 Performance Test

Stelle sicher, dass die Cards nicht zu lange laden:

```javascript
// In Browser Console:
performance.measure('card-load-start')
// Lade die Card... dann:
performance.measure('card-load-end')
performance.getEntriesByName('card-load-end')[0]
```

Ziel: **< 1 Sekunde** für Card-Rendering

---

## 📝 Reporting Issues

Falls etwas nicht funktioniert, sammle folgende Infos:

1. **Home Assistant Version:** Settings → About
2. **SmartGardn Version:** Settings → Devices & Services → SmartGardn
3. **Browser:** Chrome/Firefox/Safari/App
4. **Logs:** Settings → System → Logs (smartgardn_et0)
5. **Browser Console:** F12 → Console (Screenhot)

Dann: [GitHub Issues](https://github.com/Presley2/ha-smartgardn/issues)
