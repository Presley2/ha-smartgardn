# SmartGardn ET₀ - Custom Lovelace Cards Setup

Die SmartGardn ET₀ Integration kommt mit 4 vordefinierten Lovelace Cards:

## 📊 Verfügbare Cards

| Card | Element | Beschreibung |
|------|---------|-------------|
| **Overview Card** | `irrigation-overview-card` | Zone Status mit NFK%, ETc, Regen, nächster Start |
| **Settings Card** | `irrigation-settings-card` | Zone Konfiguration mit Schiebereglern |
| **History Card** | `irrigation-history-card` | 30-Tage Trend-Kurven + 3-Tage Forecast |
| **Ansaat Card** | `irrigation-ansaat-card` | Saatgut-Bewässerung Timeline |

---

## 🔧 Installation

### 1️⃣ Automatische Registration (Storage Mode)

Wenn Home Assistant im **Storage Mode** läuft (Lovelace UI Editor), werden die Cards automatisch beim Laden des Integration registriert.

**Check ob Storage Mode aktiv ist:**
- Settings → Dashboards
- Wenn du einen "Lovelace Dashboard bearbeiten" Button siehst → **Storage Mode**

### 2️⃣ Manuelle Registration (YAML Mode)

Falls du im **YAML Mode** bist oder die automatische Registration nicht funktioniert:

**Öffne `ui-lovelace.yaml`** und füge folgende Ressourcen hinzu:

```yaml
title: Home
resources:
  # SmartGardn ET₀ Custom Cards
  - url: /smartgardn_et0_cards/overview-card.js
    type: module
  - url: /smartgardn_et0_cards/history-card.js
    type: module
  - url: /smartgardn_et0_cards/settings-card.js
    type: module
  - url: /smartgardn_et0_cards/ansaat-card.js
    type: module

views:
  - title: Garten
    cards:
      - type: custom:irrigation-overview-card
        entry_id: <deine_entry_id>
```

### 3️⃣ Debugging

Wenn die Cards nicht angezeigt werden:

1. **Aktiviere Debug Logging** in Home Assistant:
   ```yaml
   logger:
     logs:
       custom_components.smartgardn_et0: debug
   ```

2. **Schau dir die Logs an:**
   - Settings → System → Logs
   - Suche nach `smartgardn_et0`

3. **Browser Console checken** (F12):
   - Öffne Developer Tools (F12)
   - Schau in der Console nach Fehlern

---

## 📝 Card Konfiguration

### Overview Card

```yaml
type: custom:irrigation-overview-card
entry_id: abc123def456
title: Bewässerung Status
```

### Settings Card

```yaml
type: custom:irrigation-settings-card
entry_id: abc123def456
zone: zone0
```

### History Card

```yaml
type: custom:irrigation-history-card
entry_id: abc123def456
days: 30
```

### Ansaat Card

```yaml
type: custom:irrigation-ansaat-card
entry_id: abc123def456
zone: zone0
```

---

## 🆔 Entry ID finden

Die `entry_id` findest du unter:

1. Settings → Devices & Services
2. Suche nach "SmartGardn ET₀"
3. Klick auf den Entry
4. Die ID ist in der URL oder unter "Details"

Alternativ in der Browser Console:
```javascript
// Alle verfügbaren Entities auflisten
Object.keys(window.hass.states).filter(id => id.includes('sensor.'))
```

---

## 🐛 Häufige Probleme

### "Custom element not found"
→ Die Ressourcen wurden nicht registriert. Führe Schritt 2️⃣ aus.

### Cards laden aber zeigen keine Daten
→ `entry_id` ist falsch. Check deine Configuration Entry ID.

### HTTP 404 auf `/smartgardn_et0_cards/`
→ Home Assistant wurde nicht neu gestartet nach Integration Installation.

---

## 🛠️ Custom Cards erstellen

Um eine eigene Card zu erstellen:

1. Erstelle `src/cards/my-custom-card.js`:

```javascript
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('irrigation-my-custom-card')
export class MyCustomCard extends LitElement {
  @property({ attribute: false }) hass;
  @property({ type: Object }) config;

  setConfig(config) {
    this.config = config;
  }

  render() {
    return html`<ha-card><div>Meine Custom Card</div></ha-card>`;
  }

  static styles = css`
    ha-card { padding: 16px; }
  `;
}
```

2. Kopiere zur `custom_components/smartgardn_et0/www/my-custom-card.js`

3. Registriere in `custom_components/smartgardn_et0/cards.py`:

```python
CARDS = {
    ...
    "my-custom-card.js": "My Custom: Beschreibung",
}
```

4. Nutze in Lovelace:

```yaml
type: custom:irrigation-my-custom-card
entry_id: ...
```
