"""Persistent storage for smartgardn_et0 — schema v1."""

from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.smartgardn_et0.const import STORAGE_KEY, STORAGE_VERSION

VERLAUF_MAX_DAYS = 365


class VerlaufEntry(TypedDict):
    datum: str
    nfk_ende: float
    etc: float
    regen: float
    beregnung: float


class SchedulingData(TypedDict):
    next_start_dt: str | None
    next_ansaat_tick: str | None
    running_since: str | None
    active_zone_remaining_min: float
    queue: list[str]


class ZoneData(TypedDict):
    name: str
    nfk_aktuell: float
    letzte_berechnung: str | None
    ansaat_start_datum: str | None
    verlauf: list[VerlaufEntry]
    scheduling: SchedulingData


class GlobalData(TypedDict):
    gts: float
    gts_jahr: int
    et_methode: str
    letzte_et0_berechnung: str | None


class StorageData(TypedDict):
    zones: dict[str, ZoneData]
    globals: GlobalData


def _default_storage_data() -> StorageData:
    """Return factory-default storage (no zones, zero GTS, fao56 method)."""
    return {
        "zones": {},
        "globals": {
            "gts": 0.0,
            "gts_jahr": 0,
            "et_methode": "fao56",
            "letzte_et0_berechnung": None,
        },
    }


def _trim_verlauf(data: StorageData) -> None:
    """Trim each zone's verlauf to the most recent VERLAUF_MAX_DAYS entries."""
    for zone in data["zones"].values():
        verlauf = zone["verlauf"]
        if len(verlauf) > VERLAUF_MAX_DAYS:
            zone["verlauf"] = verlauf[-VERLAUF_MAX_DAYS:]


class IrrigationStorage:
    """Manages reading and writing irrigation state to HA storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[StorageData] = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(self) -> StorageData:
        """Load from disk, returning defaults if no file exists."""
        raw = await self._store.async_load()
        if raw is None:
            return _default_storage_data()
        return raw

    async def async_save(self, data: StorageData) -> None:
        """Coalesced save (30-second delay, suitable for normal daily saves)."""
        _trim_verlauf(data)
        self._store.async_delay_save(lambda: data, delay=30)

    async def async_save_immediate(self, data: StorageData) -> None:
        """Immediate save — no coalescing. Use for zone-start/stop (power-loss safety)."""
        _trim_verlauf(data)
        await self._store.async_save(data)

    async def async_migrate(self, old_version: int, old_data: dict) -> dict:  # type: ignore[type-arg]
        """Migrate storage data from old_version to current STORAGE_VERSION."""
        return old_data
