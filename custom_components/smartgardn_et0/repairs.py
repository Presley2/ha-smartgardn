"""Repair workflows for smartgardn_et0.

Handles repair flows for missing entities, unavailable sensors, and other issues.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from custom_components.smartgardn_et0.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _safe_encode_entity_id(entity_id: str) -> str:
    """Safely encode entity_id to base64 for issue_id."""
    return base64.urlsafe_b64encode(entity_id.encode()).decode().rstrip('=')


def _safe_decode_entity_id(encoded: str) -> str:
    """Safely decode entity_id from base64 in issue_id."""
    padding = 4 - (len(encoded) % 4)
    if padding != 4:
        encoded = encoded + '=' * padding
    try:
        return base64.urlsafe_b64decode(encoded).decode()
    except Exception:
        _LOGGER.error("Failed to decode entity_id from %s", encoded)
        return ""


class MissingEntityRepairFlow(RepairsFlow):
    """Repair flow for missing entities."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show description of missing entity issue."""
        issue_id = self.issue_id
        # Extract entity from issue_id format: missing_entity_<base64_encoded_entity_id>
        if not issue_id.startswith("missing_entity_"):
            entity_id = ""
        else:
            encoded = issue_id.replace("missing_entity_", "")
            entity_id = _safe_decode_entity_id(encoded)

        return self.async_show_form(
            step_id="init",
            description_placeholders={"entity": entity_id},
        )

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """User confirmed repair (acknowledged the issue)."""
        return self.async_abort(reason="issue_resolved")


class TrafoUnavailableRepairFlow(RepairsFlow):
    """Repair flow for transformer unavailability."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show trafo unavailability issue."""
        issue_id = self.issue_id
        # Extract entity from issue_id format: trafo_unavailable_<base64_encoded_entity_id>
        if not issue_id.startswith("trafo_unavailable_"):
            entity_id = ""
        else:
            encoded = issue_id.replace("trafo_unavailable_", "")
            entity_id = _safe_decode_entity_id(encoded)

        return self.async_show_form(
            step_id="init",
            description_placeholders={"entity": entity_id},
        )

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """User confirmed trafo availability restored."""
        return self.async_abort(reason="issue_resolved")


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, **kwargs: Any
) -> RepairsFlow:
    """Create repair flow based on issue type."""
    if issue_id.startswith("missing_entity_"):
        return MissingEntityRepairFlow()
    elif issue_id.startswith("trafo_unavailable_"):
        return TrafoUnavailableRepairFlow()

    # Default: simple acknowledge flow
    return MissingEntityRepairFlow()


async def async_check_and_create_issues(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Check for common issues and create repair issues if needed.

    Called during coordinator startup to detect:
    - Missing weather sensor entities
    - Unavailable zone valve entities
    - Trafo unavailability
    """
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    if not coordinator:
        return

    # Check if required weather sensors are configured
    # Support both new single sensors and legacy min/max pairs
    missing_sensors = []
    temp_configured = entry.data.get("temp_entity") or (
        entry.data.get("temp_min_entity") and entry.data.get("temp_max_entity")
    )
    if not temp_configured:
        missing_sensors.append("Temperature Sensor")

    # Check if configured zone valves are available
    for _zone_id, zone_cfg in entry.data.get("zones", {}).items():
        valve_id = zone_cfg.get("valve_entity")
        if valve_id:
            state = hass.states.get(valve_id)
            if not state or state.state == "unavailable":
                # Create issue for missing valve entity
                encoded_id = _safe_encode_entity_id(valve_id)
                issue_id = f"missing_entity_{encoded_id}"
                ir.async_create_issue(
                    hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=True,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="missing_entity",
                    translation_placeholders={"entity": valve_id},
                )

    # Check trafo entity
    trafo_id = entry.data.get("trafo_entity")
    if trafo_id:
        state = hass.states.get(trafo_id)
        if not state or state.state == "unavailable":
            # Create issue for unavailable trafo
            encoded_id = _safe_encode_entity_id(trafo_id)
            issue_id = f"trafo_unavailable_{encoded_id}"
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=True,
                severity=ir.IssueSeverity.ERROR,
                translation_key="trafo_unavailable",
                translation_placeholders={"entity": trafo_id},
            )
