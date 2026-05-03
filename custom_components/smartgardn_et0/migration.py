"""Migration service for importing legacy Node-RED irrigation data."""

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


async def migrate_from_nodered(
    hass, legacy_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Migrate legacy Node-RED irrigation data to smartgardn_et0 format.

    Legacy Node-RED structure:
    {
      "zones": [
        {
          "name": "Zone 1",
          "soil_type": "sand",
          "root_depth_dm": 15,
          "nfk_max": 50,
          "entity_id": "switch.zone1"
        }
      ],
      "location": {
        "latitude": 51.5,
        "longitude": 7.5,
        "elevation": 100
      }
    }

    New smartgardn_et0 format:
    {
      "name": "Meine Anlage",
      "latitude": 51.5,
      "longitude": 7.5,
      "elevation": 100,
      "zones": {
        "<uuid>": {
          "name": "Zone 1",
          "soil_type": "sand",
          "root_depth_dm": 15,
          "nfk_max": 50,
          ...
        }
      }
    }
    """
    import uuid

    new_data = {
        "name": legacy_data.get("installation_name", "Bewässerung"),
        "latitude": legacy_data.get("location", {}).get("latitude"),
        "longitude": legacy_data.get("location", {}).get("longitude"),
        "elevation": legacy_data.get("location", {}).get("elevation", 0),
        "zones": {},
    }

    # Migrate zones
    for legacy_zone in legacy_data.get("zones", []):
        zone_id = str(uuid.uuid4())
        new_data["zones"][zone_id] = {
            "name": legacy_zone.get("name", f"Zone {zone_id[:8]}"),
            "soil_type": legacy_zone.get("soil_type", "loam"),
            "root_depth_dm": legacy_zone.get("root_depth_dm", 20),
            "nfk_max": legacy_zone.get("nfk_max", 100),
            "kc": legacy_zone.get("kc", 0.5),
            "modus": "aus",  # Default to off
            "enabled": True,
            "weekdays": [True] * 7,  # All days enabled by default
            "start_time": "19:00",
            "schwellwert_pct": legacy_zone.get("schwellwert_pct", 50),
            "zielwert_pct": legacy_zone.get("zielwert_pct", 80),
            "dauer_min": legacy_zone.get("dauer_min", 30),
            "manuelle_dauer_min": legacy_zone.get("manuelle_dauer_min", 30),
            "cs_zyklen": legacy_zone.get("cs_zyklen", 1),
            "cs_pause_min": legacy_zone.get("cs_pause_min", 30),
            "ansaat_intervall_h": legacy_zone.get("ansaat_intervall_h", 1),
            "ansaat_dauer_min": legacy_zone.get("ansaat_dauer_min", 5),
            "ansaat_laufzeit_tage": legacy_zone.get("ansaat_laufzeit_tage", 21),
            "ansaat_von": "06:00",
            "ansaat_bis": "10:00",
        }

    _LOGGER.info(
        "✓ Migrated %d zones from Node-RED to smartgardn_et0",
        len(new_data["zones"]),
    )
    return new_data


async def validate_migration(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate migrated data for completeness and correctness.

    Returns:
        (is_valid, list of warnings/errors)
    """
    issues = []

    # Check required location fields
    if not data.get("latitude"):
        issues.append("Missing latitude — required for ET₀ calculation")
    if not data.get("longitude"):
        issues.append("Missing longitude — required for ET₀ calculation")

    # Check zones
    zones = data.get("zones", {})
    if not zones:
        issues.append("No zones configured — add at least one zone")

    for zone_id, zone_data in zones.items():
        # Validate zone parameters
        if not zone_data.get("name"):
            issues.append(f"Zone {zone_id[:8]}: missing name")
        if zone_data.get("nfk_max", 0) <= 0:
            issues.append(f"Zone {zone_data.get('name')}: invalid nfk_max")
        if zone_data.get("root_depth_dm", 0) <= 0:
            issues.append(f"Zone {zone_data.get('name')}: invalid root_depth_dm")

    return len(issues) == 0, issues


async def async_setup_migration_service(hass, entry_id: str):
    """Register migration service with Home Assistant."""

    async def handle_import_nodered_data(service_call):
        """Handle import of Node-RED data."""
        legacy_data = service_call.data.get("data", {})
        is_valid, issues = await validate_migration(legacy_data)

        if not is_valid:
            _LOGGER.warning(
                "Migration validation failed with %d issues: %s",
                len(issues),
                "; ".join(issues),
            )
            hass.components.persistent_notification.async_create(
                "❌ Migration failed:\n" + "\n".join(f"• {issue}" for issue in issues),
                title="Irrigation ET₀: Migration Error",
                notification_id="irrigation_migration_error",
            )
            return

        migrated_data = await migrate_from_nodered(hass, legacy_data)
        _LOGGER.info("✓ Successfully migrated Node-RED data")
        hass.components.persistent_notification.async_create(
            f"✓ Migration successful!\n"
            f"Imported {len(migrated_data['zones'])} zones.\n"
            "Start with configuration in Settings > Devices & Services.",
            title="Irrigation ET₀: Migration Complete",
            notification_id="irrigation_migration_success",
        )

    hass.services.async_register(
        "smartgardn_et0",
        "import_nodered_data",
        handle_import_nodered_data,
        schema=None,  # Accept any data structure
    )
    _LOGGER.debug("✓ Registered smartgardn_et0.import_nodered_data service")
