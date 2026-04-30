"""DataUpdateCoordinator for irrigation_et0."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from datetime import time as dtime
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.irrigation_et0.const import DOMAIN, MODE_OFF, WEEKDAYS
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
        self._zone_enabled: dict[str, bool] = {}
        self._zone_weekdays: dict[str, dict[str, bool]] = {}
        self._zone_modus: dict[str, str] = {}
        self._zone_numbers: dict[str, dict[str, float]] = {}
        self._zone_times: dict[str, dict[str, dtime]] = {}
        self._dry_run: bool = True

    async def async_setup(self) -> None:
        """Load storage and register scheduled callbacks."""
        self._storage_data = await self.storage.async_load()
        for zone_id, zone_cfg in self.entry.data.get("zones", {}).items():
            self._zone_enabled[zone_id] = True
            self._zone_weekdays[zone_id] = dict.fromkeys(WEEKDAYS, True)
            self._zone_modus[zone_id] = MODE_OFF
            self._zone_numbers[zone_id] = {
                "dauer": 30.0,
                "schwellwert": float(zone_cfg.get("schwellwert_pct", 50)),
                "zielwert": float(zone_cfg.get("zielwert_pct", 80)),
                "manuelle_dauer": 15.0,
                "cs_zyklen": 0.0,
                "cs_pause": 10.0,
                "ansaat_intervall": 60.0,
                "ansaat_dauer": 5.0,
                "ansaat_laufzeit_tage": 14.0,
            }
            self._zone_times[zone_id] = {
                "start": dtime(19, 0),
                "ansaat_von": dtime(6, 0),
                "ansaat_bis": dtime(10, 0),
            }

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

    async def start_zone_manual(self, zone_id: str, dauer_min: float) -> None:
        """Manually start a zone. Full implementation in Phase 4."""
        _LOGGER.info("Manual start zone %s for %.1f min", zone_id, dauer_min)
