"""Repair workflows for irrigation_et0.

Handles repair flows for missing entities, unavailable sensors, and other issues.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.repairs import RepairFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

_LOGGER = logging.getLogger(__name__)


class IrrigationRepairFlow(RepairFlow):
    """Repair flow for irrigation_et0 issues."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step of the repair flow."""
        if user_input is not None and user_input.get("action") == "ignore":
            return await self.async_step_ignore()
        return self.async_show_menu(
            step_id="init",
            menu_options=["ignore"],
        )

    async def async_step_ignore(self) -> FlowResult:
        """Abort the repair flow with ignore reason."""
        return self.async_abort(reason="user_ignored")


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, **kwargs: Any
) -> RepairFlow:
    """Create a repair flow for an issue."""
    return IrrigationRepairFlow()


async def async_check_issues(hass: HomeAssistant) -> list[ir.RepairIssue]:
    """Check for issues and return a list of repair issues.

    Currently returns an empty list. Full implementation will check for:
    - Missing entity references
    - Unavailable sensors
    - Invalid configuration
    """
    return []
