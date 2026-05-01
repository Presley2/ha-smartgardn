"""Tests for Phase 7 Diagnostics."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartgardn_et0.const import DOMAIN


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_diagnostics_returns_redacted_config(hass: HomeAssistant) -> None:
    """Test diagnostics exports configuration with redacted lat/lon."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Garden",
            "latitude": 50.3673,
            "longitude": 8.7394,
            "elevation": 163,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "zone_type": "lawn",
                    "kc": 0.8,
                    "soil_type": "loam",
                    "root_depth_dm": 10,
                    "schwellwert_pct": 50,
                    "zielwert_pct": 80,
                    "durchfluss_mm_min": 0.8,
                    "nfk_start_pct": 85,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        with patch("custom_components.smartgardn_et0.coordinator.async_track_time_change"):
            with patch("custom_components.smartgardn_et0.coordinator.async_track_time_interval"):
                from custom_components.smartgardn_et0 import async_setup_entry

                await async_setup_entry(hass, entry)

    from custom_components.smartgardn_et0.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diag = await async_get_config_entry_diagnostics(hass, entry)

    # Check redacted fields
    assert diag["configuration"]["name"] == "Garden"
    assert diag["configuration"]["latitude"] == "***"
    assert diag["configuration"]["longitude"] == "***"
    assert diag["configuration"]["elevation"] == 163
    assert diag["configuration"]["zones_count"] == 1
    assert diag["domain"] == DOMAIN
    assert diag["title"] == entry.title


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_diagnostics_includes_zone_history(hass: HomeAssistant) -> None:
    """Test diagnostics includes zone history."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "G",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "frost_threshold": 4.0,
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.mv1",
                    "nfk_max": 150,
                    "zone_type": "lawn",
                    "kc": 0.8,
                    "soil_type": "loam",
                    "root_depth_dm": 10,
                    "schwellwert_pct": 50,
                    "zielwert_pct": 80,
                    "durchfluss_mm_min": 0.8,
                    "nfk_start_pct": 85,
                }
            },
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        with patch("custom_components.smartgardn_et0.coordinator.async_track_time_change"):
            with patch("custom_components.smartgardn_et0.coordinator.async_track_time_interval"):
                from custom_components.smartgardn_et0 import async_setup_entry

                await async_setup_entry(hass, entry)

    from custom_components.smartgardn_et0.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diag = await async_get_config_entry_diagnostics(hass, entry)

    # Check zone history is present (may be empty if no storage data)
    assert "zone_history" in diag
    assert isinstance(diag["zone_history"], dict)


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_diagnostics_includes_current_state(hass: HomeAssistant) -> None:
    """Test diagnostics includes current runtime state."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "frost_threshold": 4.0,
            "zones": {},
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        with patch("custom_components.smartgardn_et0.coordinator.async_track_time_change"):
            with patch("custom_components.smartgardn_et0.coordinator.async_track_time_interval"):
                from custom_components.smartgardn_et0 import async_setup_entry

                await async_setup_entry(hass, entry)

    from custom_components.smartgardn_et0.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diag = await async_get_config_entry_diagnostics(hass, entry)

    # Check current state
    assert "current_state" in diag
    assert "frost_active" in diag["current_state"]
    assert "dry_run" in diag["current_state"]
    assert "queue_length" in diag["current_state"]
    assert "running_zone" in diag["current_state"]


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_diagnostics_includes_sensor_values(hass: HomeAssistant) -> None:
    """Test diagnostics includes current sensor values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.trafo",
            "temp_min_entity": "sensor.t_min",
            "temp_max_entity": "sensor.t_max",
            "frost_threshold": 4.0,
            "zones": {},
        },
    )
    entry.add_to_hass(hass)

    # Set up some sensor states
    hass.states.async_set("sensor.t_min", "15.5")
    hass.states.async_set("sensor.t_max", "28.3")

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        with patch("custom_components.smartgardn_et0.coordinator.async_track_time_change"):
            with patch("custom_components.smartgardn_et0.coordinator.async_track_time_interval"):
                from custom_components.smartgardn_et0 import async_setup_entry

                await async_setup_entry(hass, entry)

    from custom_components.smartgardn_et0.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    diag = await async_get_config_entry_diagnostics(hass, entry)

    # Check sensor values
    assert "current_sensor_values" in diag
    assert diag["current_sensor_values"]["temp_min"] == "15.5"
    assert diag["current_sensor_values"]["temp_max"] == "28.3"
