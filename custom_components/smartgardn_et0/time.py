"""Time platform for smartgardn_et0."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.smartgardn_et0.const import DOMAIN
from custom_components.smartgardn_et0.coordinator import IrrigationCoordinator


class IrrigationZoneTimeEntity(CoordinatorEntity[IrrigationCoordinator], TimeEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        key: str,
        name: str,
        default: time,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._key = key
        self._default = default
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{zone_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})
        if zone_id not in coordinator._zone_times:
            coordinator._zone_times[zone_id] = {}
        coordinator._zone_times[zone_id].setdefault(key, default)

    @property
    def native_value(self) -> time:
        return self.coordinator._zone_times.get(self._zone_id, {}).get(self._key, self._default)

    async def async_set_value(self, value: time) -> None:
        self.coordinator._zone_times.setdefault(self._zone_id, {})[self._key] = value
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[TimeEntity] = []

    for zone_id in entry.data.get("zones", {}):
        entities.append(
            IrrigationZoneTimeEntity(
                coordinator, entry.entry_id, zone_id, "start", "Startzeit", time(19, 0)
            )
        )
        entities.append(
            IrrigationZoneTimeEntity(
                coordinator,
                entry.entry_id,
                zone_id,
                "ansaat_von",
                "Ansaat von",
                time(6, 0),
            )
        )
        entities.append(
            IrrigationZoneTimeEntity(
                coordinator,
                entry.entry_id,
                zone_id,
                "ansaat_bis",
                "Ansaat bis",
                time(10, 0),
            )
        )

    async_add_entities(entities)
