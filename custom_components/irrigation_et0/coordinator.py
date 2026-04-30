"""DataUpdateCoordinator for irrigation_et0."""
from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.irrigation_et0.const import DOMAIN
from custom_components.irrigation_et0.storage import IrrigationStorage, StorageData

_LOGGER = logging.getLogger(__name__)


class IrrigationCoordinator(DataUpdateCoordinator[dict]):  # type: ignore[type-arg]
    """Manages state, scheduling, and sensor polling for irrigation_et0."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.entry = entry
        self.storage = IrrigationStorage(hass)
        self._storage_data: StorageData | None = None
        self._unsubs: list[Callable[[], None]] = []

    async def async_setup(self) -> None:
        """Load storage and register scheduled callbacks."""
        self._storage_data = await self.storage.async_load()

    async def async_shutdown(self) -> None:
        """Cancel all tracked listeners/timers."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    async def _async_update_data(self) -> dict:  # type: ignore[override]
        """Poll current state from HA sensors and compute derived values."""
        data = self.entry.data
        trafo_state = self.hass.states.get(data.get("trafo_entity", ""))
        frost_threshold = data.get("frost_threshold", 4.0)
        temp_min_state = self.hass.states.get(data.get("temp_min_entity", ""))
        frost_active = False
        if temp_min_state and temp_min_state.state not in ("unknown", "unavailable"):
            with contextlib.suppress(ValueError):
                frost_active = float(temp_min_state.state) < frost_threshold

        return {
            "frost_active": frost_active,
            "trafo_state": trafo_state.state if trafo_state else "unavailable",
            "storage": self._storage_data,
        }
