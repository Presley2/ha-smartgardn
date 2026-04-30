"""Tests for IrrigationStorage — load, save, round-trip, and verlauf retention."""

from homeassistant.core import HomeAssistant

from custom_components.irrigation_et0.storage import IrrigationStorage


async def test_storage_returns_default_when_empty(hass: HomeAssistant) -> None:
    """Empty store returns factory defaults."""
    storage = IrrigationStorage(hass)
    data = await storage.async_load()
    assert data["zones"] == {}
    assert data["globals"]["et_methode"] == "fao56"
    assert data["globals"]["gts"] == 0.0


async def test_round_trip_save_load_preserves_data(hass: HomeAssistant) -> None:
    """Data written with async_save_immediate is readable by a fresh instance."""
    storage = IrrigationStorage(hass)
    data = await storage.async_load()
    data["globals"]["gts"] = 150.5
    data["globals"]["gts_jahr"] = 2025
    await storage.async_save_immediate(data)

    storage2 = IrrigationStorage(hass)
    loaded = await storage2.async_load()
    assert loaded["globals"]["gts"] == 150.5
    assert loaded["globals"]["gts_jahr"] == 2025


async def test_verlauf_retention_365_days_truncates_oldest(hass: HomeAssistant) -> None:
    """Verlauf longer than 365 entries is trimmed to 365 on save."""
    storage = IrrigationStorage(hass)
    data = await storage.async_load()
    zone_id = "zone-1"
    data["zones"][zone_id] = {
        "name": "Test",
        "nfk_aktuell": 10.0,
        "letzte_berechnung": None,
        "ansaat_start_datum": None,
        "verlauf": [
            {
                "datum": f"2025-{(i % 12) + 1:02d}-01",
                "nfk_ende": 10.0,
                "etc": 1.0,
                "regen": 0.0,
                "beregnung": 0.0,
            }
            for i in range(400)
        ],
        "scheduling": {
            "next_start_dt": None,
            "next_ansaat_tick": None,
            "running_since": None,
            "active_zone_remaining_min": 0,
            "queue": [],
        },
    }
    await storage.async_save_immediate(data)

    storage2 = IrrigationStorage(hass)
    loaded = await storage2.async_load()
    assert len(loaded["zones"][zone_id]["verlauf"]) == 365
