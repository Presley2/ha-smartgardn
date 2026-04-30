"""Tests for entity platforms."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_et0.const import DOMAIN
from custom_components.irrigation_et0.coordinator import IrrigationCoordinator

ZONE_ID = "zone-abc-123"
ZONE_CFG = {
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
ENTRY_DATA = {
    "name": "Garten",
    "latitude": 50.3,
    "longitude": 8.7,
    "elevation": 163,
    "trafo_entity": "switch.trafo",
    "frost_threshold": 4.0,
    "temp_min_entity": "sensor.t_min",
    "temp_max_entity": "sensor.t_max",
    "zones": {ZONE_ID: ZONE_CFG},
}


@pytest.fixture
def mock_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, entry_id="test_eid")
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def coordinator(hass: HomeAssistant, mock_entry: MockConfigEntry) -> IrrigationCoordinator:
    from unittest.mock import patch
    coord = IrrigationCoordinator(hass, mock_entry)
    with patch("custom_components.irrigation_et0.coordinator.async_track_time_change"):
        with patch("custom_components.irrigation_et0.coordinator.async_track_time_interval"):
            await coord.async_setup()
    yield coord
    await coord.async_shutdown()


def _zone_data(nfk: float) -> dict:
    return {
        "name": "R1",
        "nfk_aktuell": nfk,
        "letzte_berechnung": None,
        "ansaat_start_datum": None,
        "verlauf": [],
        "scheduling": {
            "next_start_dt": None,
            "next_ansaat_tick": None,
            "running_since": None,
            "active_zone_remaining_min": 0,
            "queue": [],
        },
    }


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_nfk_sensor_returns_storage_value(
    hass: HomeAssistant,
    coordinator: IrrigationCoordinator,
    mock_entry: MockConfigEntry,
) -> None:
    from custom_components.irrigation_et0.sensor import IrrigationNFKSensor

    coordinator._storage_data["zones"][ZONE_ID] = _zone_data(9.5)
    coordinator.data = await coordinator._async_update_data()
    coordinator.data["storage"] = coordinator._storage_data

    sensor = IrrigationNFKSensor(coordinator, "test_eid", ZONE_ID, ZONE_CFG)
    assert sensor.native_value == 9.5


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_nfk_prozent_calculates_correctly(
    hass: HomeAssistant,
    coordinator: IrrigationCoordinator,
    mock_entry: MockConfigEntry,
) -> None:
    from custom_components.irrigation_et0.sensor import IrrigationNFKProzentSensor

    coordinator._storage_data["zones"][ZONE_ID] = _zone_data(7.5)
    coordinator.data = await coordinator._async_update_data()
    coordinator.data["storage"] = coordinator._storage_data

    sensor = IrrigationNFKProzentSensor(coordinator, "test_eid", ZONE_ID, ZONE_CFG)
    # nfk_aktuell=7.5, nfk_max=150 → 5.0%
    assert sensor.native_value == pytest.approx(5.0)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_frost_binary_sensor_active_when_coordinator_says_frost(
    hass: HomeAssistant,
    coordinator: IrrigationCoordinator,
    mock_entry: MockConfigEntry,
) -> None:
    from custom_components.irrigation_et0.binary_sensor import IrrigationFrostWarnungSensor

    coordinator.data = {"frost_active": True, "trafo_state": "off", "storage": None}
    sensor = IrrigationFrostWarnungSensor(coordinator, "test_eid")
    assert sensor.is_on is True


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_dry_run_switch_defaults_true(
    hass: HomeAssistant,
    coordinator: IrrigationCoordinator,
    mock_entry: MockConfigEntry,
) -> None:
    from custom_components.irrigation_et0.switch import IrrigationDryRunSwitch

    switch = IrrigationDryRunSwitch(coordinator, "test_eid")
    assert switch.is_on is True


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_zone_modus_select_default_aus(
    hass: HomeAssistant,
    coordinator: IrrigationCoordinator,
    mock_entry: MockConfigEntry,
) -> None:
    from custom_components.irrigation_et0.select import IrrigationZoneModusSelect

    sel = IrrigationZoneModusSelect(coordinator, "test_eid", ZONE_ID)
    assert sel.current_option == "aus"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_zone_number_schwellwert_initialized_from_config(
    hass: HomeAssistant,
    coordinator: IrrigationCoordinator,
    mock_entry: MockConfigEntry,
) -> None:
    from custom_components.irrigation_et0.number import IrrigationNumberEntity

    number = IrrigationNumberEntity(
        coordinator, "test_eid", ZONE_ID, "schwellwert", 10, 90, 5, "%", 50.0
    )
    assert number.native_value == 50.0
