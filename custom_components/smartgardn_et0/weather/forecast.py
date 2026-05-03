"""DWD weather forecast integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def fetch_dwd_forecast(
    hass: HomeAssistant,
    latitude: float,
    longitude: float,
    elevation: int,
) -> list:
    """Fetch DWD forecast for given coordinates."""
    try:
        from custom_components.smartgardn_et0.dwd_forecast import fetch_dwd_forecast as _fetch

        return await _fetch(hass, latitude, longitude, elevation)
    except Exception as err:
        _LOGGER.warning("DWD forecast failed: %s", err)
        return []
