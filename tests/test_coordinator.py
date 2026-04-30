"""Tests for IrrigationCoordinator."""
from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_et0.const import DOMAIN
from custom_components.irrigation_et0.coordinator import IrrigationCoordinator


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_coordinator_setup_loads_storage(hass: HomeAssistant) -> None:
    from unittest.mock import patch
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {},
            "name": "Test",
        },
    )
    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"):
        with patch("custom_components.irrigation_et0.coordinator.async_track_time_interval"):
            await coordinator.async_setup()
    try:
        # After setup, storage data is loaded (defaults when no file exists)
        assert coordinator._storage_data is not None
        assert coordinator._storage_data["zones"] == {}
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_coordinator_update_data_returns_dict(hass: HomeAssistant) -> None:
    from unittest.mock import patch
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {},
            "name": "Test",
        },
    )
    coordinator = IrrigationCoordinator(hass, entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"):
        with patch("custom_components.irrigation_et0.coordinator.async_track_time_interval"):
            await coordinator.async_setup()
    try:
        data = await coordinator._async_update_data()
        assert "frost_active" in data
        assert "trafo_state" in data
        assert data["frost_active"] is False  # no temp sensor state → not frost
    finally:
        await coordinator.async_shutdown()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_coordinator_shutdown_clears_unsubs(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"zones": {}, "name": "Test"})
    coordinator = IrrigationCoordinator(hass, entry)
    called: list[int] = []
    coordinator._unsubs.append(lambda: called.append(1))
    coordinator._unsubs.append(lambda: called.append(2))
    await coordinator.async_shutdown()
    assert called == [1, 2]
    assert coordinator._unsubs == []


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_setup_creates_hub_and_zone_devices(hass: HomeAssistant) -> None:
    from unittest.mock import AsyncMock, patch

    from homeassistant.helpers import device_registry as dr

    zone_id = "zone-uuid-1"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Garten",
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "frost_threshold": 4.0,
            "zones": {
                zone_id: {
                    "zone_name": "Rasenkreis 1",
                    "zone_type": "lawn",
                    "valve_entity": "switch.mv1",
                    "kc": 0.8,
                    "soil_type": "loam",
                    "root_depth_dm": 10,
                    "schwellwert_pct": 50,
                    "zielwert_pct": 80,
                    "durchfluss_mm_min": 0.8,
                    "nfk_start_pct": 85,
                    "nfk_max": 150,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"):
            with patch("custom_components.irrigation_et0.coordinator.async_track_time_interval"):
                from custom_components.irrigation_et0 import async_setup_entry

                result = await async_setup_entry(hass, entry)
                assert result is True

    dev_reg = dr.async_get(hass)
    hub = dev_reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert hub is not None
    assert hub.name == "Bewässerung Garten"

    zone_device = dev_reg.async_get_device(
        identifiers={(DOMAIN, f"{entry.entry_id}_{zone_id}")}
    )
    assert zone_device is not None
    assert zone_device.name == "Zone Rasenkreis 1"
