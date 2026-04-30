"""Tests for Phase 5 reliability features (startup recovery, fallback, trafo monitoring)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_et0.const import DOMAIN
from custom_components.irrigation_et0.coordinator import IrrigationCoordinator


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_startup_recovery_closes_stuck_valve(hass: HomeAssistant) -> None:
    """Test that startup recovery closes a valve that ran past its dauer."""
    from datetime import UTC

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "TestGarden",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "schwellwert_pct": 50,
                    "zielwert_pct": 80,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)

    # Simulate stuck valve (running_since 1 hour ago, dauer 30 min)
    now = datetime.now(UTC)
    coordinator._storage_data = {
        "zones": {
            "z1": {
                "name": "Z1",
                "nfk_aktuell": 100.0,
                "letzte_berechnung": None,
                "ansaat_start_datum": None,
                "verlauf": [],
                "scheduling": {
                    "next_start_dt": None,
                    "next_ansaat_tick": None,
                    "running_since": (now - timedelta(hours=1)).isoformat(),
                    "active_zone_remaining_min": 30.0,
                    "queue": [],
                },
            }
        },
        "globals": {
            "gts": 0.0,
            "gts_jahr": 2026,
            "et_methode": "fao56",
            "letzte_et0_berechnung": None,
        },
    }

    # Set valve to "on"
    hass.states.async_set("switch.mv1", "on")

    with patch.object(
        coordinator, "_valve_off_then_trafo_check", new_callable=AsyncMock
    ) as mock_valve_off, patch.object(coordinator, "storage") as mock_storage:
        mock_storage.async_save_immediate = AsyncMock()
        await coordinator._startup_recovery()
        # Should have closed the valve
        mock_valve_off.assert_called_once_with("switch.mv1")


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_startup_recovery_resumes_zone_in_progress(hass: HomeAssistant) -> None:
    """Test that startup recovery resumes a zone that has time remaining."""
    from datetime import UTC

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "TestGarden",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)

    # Simulate zone in progress (running_since 10 min ago, dauer 30 min)
    now = datetime.now(UTC)
    coordinator._storage_data = {
        "zones": {
            "z1": {
                "name": "Z1",
                "nfk_aktuell": 100.0,
                "letzte_berechnung": None,
                "ansaat_start_datum": None,
                "verlauf": [],
                "scheduling": {
                    "next_start_dt": None,
                    "next_ansaat_tick": None,
                    "running_since": (now - timedelta(minutes=10)).isoformat(),
                    "active_zone_remaining_min": 30.0,
                    "queue": [],
                },
            }
        },
        "globals": {
            "gts": 0.0,
            "gts_jahr": 2026,
            "et_methode": "fao56",
            "letzte_et0_berechnung": None,
        },
    }

    # Set valve to "on"
    hass.states.async_set("switch.mv1", "on")

    with patch(
        "custom_components.irrigation_et0.coordinator.async_track_point_in_time"
    ) as mock_track:
        await coordinator._startup_recovery()
        # Should have scheduled a timer for remaining time (~20 min)
        mock_track.assert_called_once()


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_et0_fallback_to_hargreaves_when_pm_missing(hass: HomeAssistant) -> None:
    """Test ET0 fallback to Hargreaves when PM inputs are missing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "TestGarden",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "humidity_min_entity": None,
            "humidity_max_entity": None,
            "solar_entity": None,
            "wind_entity": None,
            "rain_entity": None,
            "et_methode": "fao56",
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    coordinator._storage_data = {
        "zones": {},
        "globals": {
            "gts": 0.0,
            "gts_jahr": 2026,
            "et_methode": "fao56",
            "letzte_et0_berechnung": None,
            "et0_last_known": 0.0,
        },
    }

    # Set temperature sensors only
    hass.states.async_set("sensor.t_min", "10.0")
    hass.states.async_set("sensor.t_max", "25.0")

    et0, method, fallback = await coordinator._compute_et0_with_fallback()

    assert fallback is True
    assert method == "hargreaves"
    assert et0 > 0


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_et0_fallback_to_last_known_when_all_sensors_missing(hass: HomeAssistant) -> None:
    """Test ET0 fallback to last known value when all sensors are missing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "TestGarden",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "et_methode": "fao56",
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    coordinator._storage_data = {
        "zones": {},
        "globals": {
            "gts": 0.0,
            "gts_jahr": 2026,
            "et_methode": "fao56",
            "letzte_et0_berechnung": None,
            "et0_last_known": 5.5,
        },
    }

    # Don't set any temperature sensors (they'll be None)

    et0, method, fallback = await coordinator._compute_et0_with_fallback()

    assert fallback is True
    assert method == "last_known"
    assert et0 == 5.5


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_trafo_problem_detection_creates_repair_after_5min(hass: HomeAssistant) -> None:
    """Test that trafo unavailability for >5min creates a repair issue."""
    from datetime import UTC

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "TestGarden",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    coordinator._storage_data = {
        "zones": {},
        "globals": {
            "gts": 0.0,
            "gts_jahr": 2026,
            "et_methode": "fao56",
            "letzte_et0_berechnung": None,
        },
    }

    # Set trafo to unavailable
    hass.states.async_set("switch.trafo", "unavailable")

    # Simulate unavailable for 6 minutes
    coordinator._trafo_unavailable_since = datetime.now(UTC) - timedelta(minutes=6)

    with patch("homeassistant.helpers.issue_registry.async_create_issue") as mock_create:
        await coordinator._check_trafo_state()
        # Should have created an issue
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0][1] == DOMAIN
        assert "trafo_unavailable" in call_args[0][2]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_trafo_recovery_clears_unavailable_flag(hass: HomeAssistant) -> None:
    """Test that trafo recovering clears the unavailable flag."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "TestGarden",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)
    coordinator._storage_data = {
        "zones": {},
        "globals": {
            "gts": 0.0,
            "gts_jahr": 2026,
            "et_methode": "fao56",
            "letzte_et0_berechnung": None,
        },
    }

    # Set trafo to on (recovered)
    hass.states.async_set("switch.trafo", "on")

    # Pretend it was unavailable
    coordinator._trafo_unavailable_since = datetime.now()

    await coordinator._check_trafo_state()

    # Should have cleared the unavailable flag
    assert not hasattr(coordinator, "_trafo_unavailable_since")


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_catch_up_placeholder_does_not_error(hass: HomeAssistant) -> None:
    """Test that catch-up placeholder doesn't error on missed days."""
    from datetime import UTC

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "TestGarden",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    coordinator = IrrigationCoordinator(hass, entry)

    # Set last calc to 3 days ago (missed days)
    now = datetime.now(UTC)
    coordinator._storage_data = {
        "zones": {},
        "globals": {
            "gts": 0.0,
            "gts_jahr": 2026,
            "et_methode": "fao56",
            "letzte_et0_berechnung": (now - timedelta(days=3)).isoformat(),
        },
    }

    # Should not raise any exception
    await coordinator._catch_up_missed_days()
