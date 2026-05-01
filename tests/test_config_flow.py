"""Tests for smartgardn_et0 config flow."""
from __future__ import annotations

import pytest

from custom_components.smartgardn_et0.const import DOMAIN

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

_WEATHER_REQUIRED = {
    "temp_min_entity": "sensor.t_min",
    "temp_max_entity": "sensor.t_max",
}


async def test_user_step_creates_entry_with_basic_config(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Garten", "latitude": 50.3, "longitude": 8.7, "elevation": 163},
    )
    assert result["step_id"] == "weather"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _WEATHER_REQUIRED,
    )
    assert result["step_id"] == "hardware"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"trafo_entity": "switch.trafo", "frost_threshold": 4.0},
    )
    assert result["step_id"] == "zone"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
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
        },
    )
    assert result["step_id"] == "zone_menu"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "Garten"
    assert "zones" in result["data"]
    assert len(result["data"]["zones"]) == 1


async def test_invalid_lat_shows_error(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "X", "latitude": 200.0, "longitude": 8.7, "elevation": 100},
    )
    assert result["type"] == "form"
    assert "latitude" in result.get("errors", {}) or "base" in result.get("errors", {})


async def test_zone_with_predefined_soil_calculates_nfk_max(hass):
    """nfk_max = SOIL_TYPES['loam'] * root_depth_dm = 15 * 10 = 150 mm."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Test", "latitude": 50.0, "longitude": 8.0, "elevation": 100},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _WEATHER_REQUIRED,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"trafo_entity": "switch.trafo", "frost_threshold": 4.0}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "zone_name": "Z1",
            "zone_type": "lawn",
            "valve_entity": "switch.mv1",
            "kc": 0.8,
            "soil_type": "loam",
            "root_depth_dm": 10,
            "schwellwert_pct": 50,
            "zielwert_pct": 80,
            "durchfluss_mm_min": 0.8,
            "nfk_start_pct": 85,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] == "create_entry"
    zone_data = list(result["data"]["zones"].values())[0]
    assert zone_data["nfk_max"] == 150  # 15 mm/dm * 10 dm


async def test_two_zones_persist_independently(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "G", "latitude": 50.0, "longitude": 8.0, "elevation": 100},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _WEATHER_REQUIRED,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"trafo_entity": "switch.trafo", "frost_threshold": 4.0}
    )
    for valve, name in [("switch.mv1", "Zone A"), ("switch.mv2", "Zone B")]:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "zone_name": name,
                "zone_type": "lawn",
                "valve_entity": valve,
                "kc": 0.8,
                "soil_type": "loam",
                "root_depth_dm": 10,
                "schwellwert_pct": 50,
                "zielwert_pct": 80,
                "durchfluss_mm_min": 0.8,
                "nfk_start_pct": 85,
            },
        )
        if name == "Zone A":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {"next_step_id": "add_zone"}
            )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] == "create_entry"
    assert len(result["data"]["zones"]) == 2
