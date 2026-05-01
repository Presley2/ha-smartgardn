"""Diagnostics for smartgardn_et0.

Exports diagnostic data for HA's debug system with redacted sensitive information.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.smartgardn_et0.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for config entry.

    Redacts sensitive data (latitude, longitude) to protect privacy.
    Includes current state, storage summary, and last 3 days of zone history.
    """
    # Get coordinator from hass.data
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")

    if not coordinator:
        return {"error": "Coordinator not initialized"}

    storage = coordinator._storage_data or {}

    # Entry metadata (redacted)
    redacted_data: dict[str, Any] = {
        "domain": entry.domain,
        "title": entry.title,
        "source": entry.source,
        "version": entry.version,
    }

    # Configuration summary (redacted)
    redacted_data["configuration"] = {
        "name": entry.data.get("name"),
        "latitude": "***",
        "longitude": "***",
        "elevation": entry.data.get("elevation"),
        "frost_threshold": entry.data.get("frost_threshold"),
        "zones_count": len(entry.data.get("zones", {})),
    }

    # Current runtime state
    current_state = {
        "frost_active": coordinator._frost_active,
        "dry_run": coordinator._dry_run,
        "queue_length": len(coordinator.queue),
        "running_zone": coordinator.running.zone_id if coordinator.running else None,
    }

    # Storage summary (no redaction needed for computed values)
    storage_summary = {
        "zones_in_storage": list(storage.get("zones", {}).keys()),
        "globals": {
            "gts": storage.get("globals", {}).get("gts"),
            "gts_jahr": storage.get("globals", {}).get("gts_jahr"),
            "et_methode": storage.get("globals", {}).get("et_methode"),
        },
    }

    # Zone history: last 3 days of NFK values per zone
    zone_history = {}
    for zone_id, zone_data in storage.get("zones", {}).items():
        verlauf = zone_data.get("verlauf", [])
        zone_history[zone_id] = {
            "nfk_aktuell": zone_data.get("nfk_aktuell"),
            "last_3_days": [
                {
                    "datum": v["datum"],
                    "nfk_ende": v["nfk_ende"],
                    "etc": v["etc"],
                    "regen": v["regen"],
                    "beregnung": v["beregnung"],
                }
                for v in verlauf[-3:]
            ],
        }

    # Current sensor values at export time
    sensor_values = {}
    # Support both new single sensors and legacy min/max pairs
    for key, entity_id in [
        ("temp", entry.data.get("temp_entity")),
        ("temp_min", entry.data.get("temp_min_entity")),
        ("temp_max", entry.data.get("temp_max_entity")),
        ("humidity", entry.data.get("humidity_entity")),
        ("humidity_min", entry.data.get("humidity_min_entity")),
        ("humidity_max", entry.data.get("humidity_max_entity")),
    ]:
        if entity_id:
            state = hass.states.get(entity_id)
            sensor_values[key] = state.state if state else "unknown"

    redacted_data["current_state"] = current_state
    redacted_data["storage"] = storage_summary
    redacted_data["zone_history"] = zone_history
    redacted_data["current_sensor_values"] = sensor_values

    return redacted_data
