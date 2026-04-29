# irrigation_et0

> Smart irrigation scheduling for Home Assistant using reference evapotranspiration (ET₀).

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

---

## About

`irrigation_et0` is a Home Assistant custom component that calculates daily
reference evapotranspiration (ET₀) using the FAO-56 Penman-Monteith equation
and uses that value to drive intelligent, weather-adaptive irrigation schedules.

Instead of running your sprinklers on a fixed timer, this integration adjusts
run times daily based on how much water the soil actually lost to evaporation
and transpiration — no more over- or under-watering.

---

## Features

- ET₀ calculation via FAO-56 Penman-Monteith using local weather sensors
- Per-zone water-budget accounting with configurable crop coefficients (Kc)
- Sunrise-relative schedule windows (e.g. "start 30 min before sunrise")
- Skip logic for rain days and recent rainfall
- Full UI configuration via Home Assistant config flow
- HACS-compatible

---

## Installation via HACS

1. Open **HACS** in your Home Assistant sidebar.
2. Go to **Integrations → ⋮ → Custom repositories**.
3. Add `https://github.com/youruser/irrigation-ha` with category **Integration**.
4. Search for **irrigation_et0** and click **Download**.
5. Restart Home Assistant.

---

## Configuration

After installation, add the integration via **Settings → Devices & Services → Add Integration → Irrigation ET₀**.

The config flow will ask for:

| Field | Description |
|---|---|
| Weather station entity | Entity providing temperature, humidity, wind speed, solar radiation |
| Latitude / Longitude | Used for astronomical calculations |
| Rain sensor (optional) | Skip irrigation when recent rainfall exceeds threshold |

---

## Cards

*(Lovelace card documentation — coming soon)*

---

## Services

| Service | Description |
|---|---|
| `irrigation_et0.run_zone` | Manually trigger a zone for a given duration |
| `irrigation_et0.skip_today` | Skip today's scheduled run for one or all zones |
| `irrigation_et0.reset_budget` | Reset the water budget for a zone |

---

## Troubleshooting

- **ET₀ sensor shows unavailable** — Check that all required weather sensor entities are providing valid numeric states.
- **Zones not running** — Verify the schedule window and that the zone switch entity is correctly configured.
- **Logs** — Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.irrigation_et0: debug
```
