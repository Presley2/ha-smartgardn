"""Tests for IrrigationStorage migration framework."""

from homeassistant.core import HomeAssistant

from custom_components.smartgardn_et0.storage import IrrigationStorage


async def test_async_migrate_v1_returns_unchanged(hass: HomeAssistant) -> None:
    """Migrating from v1 returns the data unchanged (v1 is the first schema version)."""
    storage = IrrigationStorage(hass)
    sample = {
        "zones": {},
        "globals": {
            "gts": 50.0,
            "gts_jahr": 2025,
            "et_methode": "fao56",
            "letzte_et0_berechnung": None,
        },
    }
    result = await storage.async_migrate(1, sample)
    assert result == sample
