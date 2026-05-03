"""Safety checks for irrigation: frost detection and failsafe."""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import State

_LOGGER = logging.getLogger(__name__)


def check_frost_active(
    temp_state: State | None,
    frost_threshold: float,
) -> bool:
    """Check if frost is currently active.

    Args:
        temp_state: Current temperature sensor state
        frost_threshold: Frost threshold temperature

    Returns:
        True if temperature < threshold, False otherwise
    """
    if not temp_state or temp_state.state in ("unknown", "unavailable"):
        return False

    with contextlib.suppress(ValueError):
        return float(temp_state.state) < frost_threshold

    return False


def should_activate_frost_lock(
    frost_active: bool,
    frost_lock_active: bool,
) -> bool:
    """Determine if frost lock should be activated.

    Args:
        frost_active: Current frost detection status
        frost_lock_active: Current lock status

    Returns:
        True if frost lock should be activated
    """
    return frost_active and not frost_lock_active


def should_release_frost_lock(
    frost_active: bool,
    frost_lock_active: bool,
) -> bool:
    """Determine if frost lock should be released.

    Args:
        frost_active: Current frost detection status
        frost_lock_active: Current lock status

    Returns:
        True if frost lock should be released
    """
    return not frost_active and frost_lock_active


def check_failsafe_needed(
    trafo_state: State | None,
    valve_states: dict[str, State | None],
) -> bool:
    """Check if failsafe should activate.

    Failsafe activates when trafo is on but all valves are off (stuck trafo).

    Args:
        trafo_state: Current trafo switch state
        valve_states: Dict of zone_id → valve state

    Returns:
        True if failsafe should activate
    """
    if not trafo_state or trafo_state.state != "on":
        return False

    all_valves_off = all(
        (state and state.state == "off") for state in valve_states.values()
    )

    return all_valves_off
