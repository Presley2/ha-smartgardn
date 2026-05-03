"""Weather sensor reading and history extraction."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.helpers.recorder import get_instance
from homeassistant.util.dt import UTC

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def get_daily_minmax(
    hass: HomeAssistant,
    entity_id: str | None,
    start_time: datetime | None = None,
) -> tuple[float | None, float | None]:
    """Read min/max values from HA history for a sensor.

    Args:
        hass: Home Assistant instance
        entity_id: The sensor entity ID
        start_time: Start of window (default: today 00:00)

    Returns:
        (min_value, max_value) or (None, None) if no data available
    """
    if not entity_id:
        return None, None

    if start_time is None:
        start_time = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        recorder = get_instance(hass)
        if not recorder or not recorder.async_block_till_done:
            _LOGGER.warning("Recorder not available for %s", entity_id)
            return None, None

        try:
            history = await asyncio.wait_for(
                hass.loop.run_in_executor(
                    None,
                    recorder.history.get_significant_states,
                    hass,
                    start_time,
                    None,
                    [entity_id],
                    False,
                ),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            _LOGGER.warning("Recorder timeout for history of %s, skipping history", entity_id)
            return None, None

        if not history or entity_id not in history:
            _LOGGER.debug("No history data for %s", entity_id)
            return None, None

        states = history[entity_id]
        values = []
        for state_obj in states:
            try:
                val = float(state_obj.state)
                if val is not None:
                    values.append(val)
            except (ValueError, TypeError):
                pass

        if not values:
            _LOGGER.debug("No numeric values in history for %s", entity_id)
            return None, None

        return min(values), max(values)

    except Exception as err:
        _LOGGER.error("Error reading history for %s: %s", entity_id, err)
        return None, None


def read_sensor(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Read a sensor value, return None if unavailable or not a number."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if not state or state.state in ("unknown", "unavailable"):
        return None
    try:
        return float(state.state)
    except ValueError:
        return None
