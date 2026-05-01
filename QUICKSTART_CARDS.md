# SmartGardn ET₀ - Lovelace Cards Quick Start

**The cards are automatically available after installation!** Here's how to use them.

---

## 🎯 Get Started in 2 Minutes

### 1️⃣ Install Integration

```
Settings → Devices & Services → HACS
Custom Repositories → https://github.com/Presley2/ha-smartgardn
Search for "SmartGardn ET₀" → Install → Restart HA
```

### 2️⃣ Create Configuration Entry

```
Settings → Devices & Services → Create Integration
Search for "SmartGardn ET₀" → Follow the 5-step flow
```

### 3️⃣ Add Cards to Dashboard

```
Lovelace Dashboard → Edit (Pencil icon) → + (Add Card)
Type "irrigation" in Custom Cards → Select one:
```

---

## 📊 Available Cards

### Overview Card
**Type:** `custom:irrigation-overview-card`

Shows real-time status:
- Zone names and NFK% (soil moisture)
- Today's ETc and rainfall
- Next scheduled irrigation
- Current mode (Off/Semi/Full/Seed)

```yaml
- type: custom:irrigation-overview-card
  entry_id: abc123
```

### Settings Card
**Type:** `custom:irrigation-settings-card`

Configure zone parameters:
- NFK thresholds (%)
- Irrigation duration (min)
- Weekday schedule toggle
- Enable/disable zones

```yaml
- type: custom:irrigation-settings-card
  entry_id: abc123
  zone: zone0
```

### History Card
**Type:** `custom:irrigation-history-card`

30-day trend analysis:
- NFK water balance trend
- Daily ETc consumption
- Rainfall history
- 3-day forecast (if DWD enabled)

```yaml
- type: custom:irrigation-history-card
  entry_id: abc123
```

### Ansaat (Seed) Card
**Type:** `custom:irrigation-ansaat-card`

Intensive seed watering mode:
- Hourly watering schedule
- Germination timeline
- Duration counter

```yaml
- type: custom:irrigation-ansaat-card
  entry_id: abc123
```

---

## 🔑 How to Find Your entry_id

The `entry_id` is your SmartGardn configuration ID:

**Method 1: From Settings**
```
Settings → Devices & Services
Find "SmartGardn ET₀" → Click it
Look at the URL: /config/devices/.../{ENTRY_ID}
```

**Method 2: From Entities**
```
Settings → Devices & Services → Entities
Look for sensor.{ENTRY_ID}_nfk
The part before _nfk is your entry_id
```

**Method 3: Browser Console**
```javascript
// In Home Assistant Lovelace:
Object.keys(window.hass.states)
  .filter(id => id.includes('sensor.') && id.includes('_nfk'))[0]
  .split('_nfk')[0]
  .replace('sensor.', '')
```

---

## 🎨 Example Dashboard Configuration

Complete YAML example:

```yaml
# ui-lovelace.yaml or Lovelace UI

views:
  - title: Garten
    path: garten
    cards:
      # Overview (main display)
      - type: custom:irrigation-overview-card
        entry_id: abc123
        title: Bewässerungsanlage Status

      # Settings (adjust config)
      - type: custom:irrigation-settings-card
        entry_id: abc123
        zone: zone0
        title: Zone 1 - Rasen

      - type: custom:irrigation-settings-card
        entry_id: abc123
        zone: zone1
        title: Zone 2 - Beete

      # History (trends)
      - type: custom:irrigation-history-card
        entry_id: abc123
        title: Verlauf (30 Tage)

      # Ansaat (seed mode)
      - type: custom:irrigation-ansaat-card
        entry_id: abc123
        title: Saatgut-Bewässerung
```

---

## ✅ Quick Verification

After adding cards to dashboard:

- [ ] Overview Card shows zone names
- [ ] NFK values are displayed (not "undefined")
- [ ] Settings Card sliders are responsive
- [ ] History Card loads trend data
- [ ] Cards update every minute (data is live)

If any card shows "undefined" → your entry_id is wrong → check Step 3 above.

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Cards don't appear in Custom list | Refresh browser (F5), check HA logs for "smartgardn_et0" |
| "Custom element not found" | Restart Home Assistant |
| Shows "undefined" for values | entry_id is wrong - verify against settings |
| Cards added but are blank | Wait 30 seconds for data load, check integration status |

---

## 📚 Learn More

- **Full documentation:** [docs/INSTALLATION_CARDS_TEST.md](docs/INSTALLATION_CARDS_TEST.md)
- **Testing & verification:** [TESTING_CARDS.md](TESTING_CARDS.md)
- **Development:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Technical details:** [docs/IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)

---

## 🎉 That's it!

Your SmartGardn irrigation dashboard is ready. The cards automatically update as your integration calculates irrigation needs.

**Happy watering!** 🌱💧
