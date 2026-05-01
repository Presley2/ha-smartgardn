"""Tests for Phase 7 Repairs."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartgardn_et0.const import DOMAIN


def _safe_encode_entity_id(entity_id: str) -> str:
    """Safely encode entity_id to base64 for issue_id."""
    return base64.urlsafe_b64encode(entity_id.encode()).decode().rstrip('=')


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_missing_entity_repair_flow_init(hass: HomeAssistant) -> None:
    """Test MissingEntityRepairFlow shows correct description."""
    from custom_components.smartgardn_et0.repairs import MissingEntityRepairFlow

    flow = MissingEntityRepairFlow()
    flow.hass = hass
    entity_id = "switch.valve_1"
    encoded = _safe_encode_entity_id(entity_id)
    flow.issue_id = f"missing_entity_{encoded}"

    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert "entity" in result["description_placeholders"]
    assert result["description_placeholders"]["entity"] == entity_id


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_missing_entity_repair_flow_confirm(hass: HomeAssistant) -> None:
    """Test MissingEntityRepairFlow confirm step resolves issue."""
    from custom_components.smartgardn_et0.repairs import MissingEntityRepairFlow

    flow = MissingEntityRepairFlow()
    flow.hass = hass
    flow.issue_id = "missing_entity_switch_valve"

    result = await flow.async_step_confirm()

    assert result["type"] == "abort"
    assert result["reason"] == "issue_resolved"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_trafo_unavailable_repair_flow_init(hass: HomeAssistant) -> None:
    """Test TrafoUnavailableRepairFlow shows correct description."""
    from custom_components.smartgardn_et0.repairs import TrafoUnavailableRepairFlow

    flow = TrafoUnavailableRepairFlow()
    flow.hass = hass
    entity_id = "switch.trafo"
    encoded = _safe_encode_entity_id(entity_id)
    flow.issue_id = f"trafo_unavailable_{encoded}"

    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert "entity" in result["description_placeholders"]
    assert result["description_placeholders"]["entity"] == entity_id


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_trafo_unavailable_repair_flow_confirm(hass: HomeAssistant) -> None:
    """Test TrafoUnavailableRepairFlow confirm step resolves issue."""
    from custom_components.smartgardn_et0.repairs import TrafoUnavailableRepairFlow

    flow = TrafoUnavailableRepairFlow()
    flow.hass = hass
    flow.issue_id = "trafo_unavailable_switch_trafo"

    result = await flow.async_step_confirm()

    assert result["type"] == "abort"
    assert result["reason"] == "issue_resolved"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_create_fix_flow_missing_entity(hass: HomeAssistant) -> None:
    """Test async_create_fix_flow creates MissingEntityRepairFlow for missing_entity issues."""
    from custom_components.smartgardn_et0.repairs import async_create_fix_flow

    flow = await async_create_fix_flow(hass, "missing_entity_switch_valve")

    assert flow.__class__.__name__ == "MissingEntityRepairFlow"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_create_fix_flow_trafo_unavailable(hass: HomeAssistant) -> None:
    """Test async_create_fix_flow creates TrafoUnavailableRepairFlow for trafo issues."""
    from custom_components.smartgardn_et0.repairs import async_create_fix_flow

    flow = await async_create_fix_flow(hass, "trafo_unavailable_switch_trafo")

    assert flow.__class__.__name__ == "TrafoUnavailableRepairFlow"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_create_fix_flow_unknown_issue(hass: HomeAssistant) -> None:
    """Test async_create_fix_flow defaults to MissingEntityRepairFlow."""
    from custom_components.smartgardn_et0.repairs import async_create_fix_flow

    flow = await async_create_fix_flow(hass, "unknown_issue")

    assert flow.__class__.__name__ == "MissingEntityRepairFlow"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_check_and_create_issues_missing_valve(hass: HomeAssistant) -> None:
    """Test async_check_and_create_issues creates issue for unavailable valve."""
    from homeassistant.helpers import issue_registry as ir

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
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.missing_valve",
                    "zone_type": "lawn",
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

    # Set up trafo as available, but valve is missing
    hass.states.async_set("switch.trafo", "on")

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        with patch("custom_components.smartgardn_et0.coordinator.async_track_time_change"):
            with patch("custom_components.smartgardn_et0.coordinator.async_track_time_interval"):
                from custom_components.smartgardn_et0 import async_setup_entry

                await async_setup_entry(hass, entry)

    from custom_components.smartgardn_et0.repairs import async_check_and_create_issues

    await async_check_and_create_issues(hass, entry)

    # Check if issue was created
    issue_registry = ir.async_get(hass)
    # List all issues in the registry
    entity_id = "switch.missing_valve"
    encoded = _safe_encode_entity_id(entity_id)
    issue = issue_registry.async_get_issue(DOMAIN, f"missing_entity_{encoded}")

    assert issue is not None


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_check_and_create_issues_missing_trafo(hass: HomeAssistant) -> None:
    """Test async_check_and_create_issues creates issue for unavailable trafo."""
    from homeassistant.helpers import issue_registry as ir

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test",
            "latitude": 50.0,
            "longitude": 8.0,
            "elevation": 100,
            "trafo_entity": "switch.missing_trafo",
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

    from custom_components.smartgardn_et0.repairs import async_check_and_create_issues

    await async_check_and_create_issues(hass, entry)

    # Check if issue was created
    issue_registry = ir.async_get(hass)
    entity_id = "switch.missing_trafo"
    encoded = _safe_encode_entity_id(entity_id)
    issue = issue_registry.async_get_issue(DOMAIN, f"trafo_unavailable_{encoded}")

    assert issue is not None


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_async_check_and_create_issues_no_issues_when_entities_available(
    hass: HomeAssistant,
) -> None:
    """Test no issues created when all entities are available."""
    from homeassistant.helpers import issue_registry as ir

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
            "zones": {
                "z1": {
                    "zone_name": "Z1",
                    "valve_entity": "switch.valve_1",
                    "zone_type": "lawn",
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

    # Set up all entities as available
    hass.states.async_set("switch.trafo", "on")
    hass.states.async_set("switch.valve_1", "off")

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        with patch("custom_components.smartgardn_et0.coordinator.async_track_time_change"):
            with patch("custom_components.smartgardn_et0.coordinator.async_track_time_interval"):
                from custom_components.smartgardn_et0 import async_setup_entry

                await async_setup_entry(hass, entry)

    from custom_components.smartgardn_et0.repairs import async_check_and_create_issues

    await async_check_and_create_issues(hass, entry)

    # Check no issues were created
    issue_registry = ir.async_get(hass)
    # Try to get issues - should be None
    missing_issue = issue_registry.async_get_issue(DOMAIN, "missing_entity_switch_missing_valve")
    trafo_issue = issue_registry.async_get_issue(DOMAIN, "trafo_unavailable_switch_trafo")

    assert missing_issue is None
    assert trafo_issue is None
