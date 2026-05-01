"""Switch platform for smartgardn_et0."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.smartgardn_et0.const import DOMAIN, WEEKDAYS
from custom_components.smartgardn_et0.coordinator import IrrigationCoordinator


class IrrigationZoneStatusSwitch(CoordinatorEntity[IrrigationCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Zone aktiv"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_status"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def is_on(self) -> bool:
        return self.coordinator._zone_enabled.get(self._zone_id, True)

    async def async_turn_on(self, **kwargs: object) -> None:
        self.coordinator._zone_enabled[self._zone_id] = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        self.coordinator._zone_enabled[self._zone_id] = False
        await self.coordinator.async_request_refresh()


class IrrigationWeekdaySwitch(CoordinatorEntity[IrrigationCoordinator], SwitchEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        weekday: str,
        weekday_label: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._weekday = weekday
        self._attr_name = weekday_label
        self._attr_unique_id = f"{entry_id}_{zone_id}_{weekday}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def is_on(self) -> bool:
        zone_weekdays = self.coordinator._zone_weekdays.get(self._zone_id, {})
        return zone_weekdays.get(self._weekday, True)

    async def async_turn_on(self, **kwargs: object) -> None:
        self.coordinator._zone_weekdays.setdefault(self._zone_id, {})[self._weekday] = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        self.coordinator._zone_weekdays.setdefault(self._zone_id, {})[self._weekday] = False
        await self.coordinator.async_request_refresh()


class IrrigationDryRunSwitch(CoordinatorEntity[IrrigationCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Trockenlauf"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_dry_run"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool:
        return self.coordinator._dry_run

    async def async_turn_on(self, **kwargs: object) -> None:
        self.coordinator._dry_run = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        self.coordinator._dry_run = False
        await self.coordinator.async_request_refresh()


_WEEKDAY_LABELS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SwitchEntity] = []

    for zone_id in entry.data.get("zones", {}):
        entities.append(IrrigationZoneStatusSwitch(coordinator, entry.entry_id, zone_id))
        for weekday, label in zip(WEEKDAYS, _WEEKDAY_LABELS, strict=True):
            entities.append(
                IrrigationWeekdaySwitch(coordinator, entry.entry_id, zone_id, weekday, label)
            )

    entities.append(IrrigationDryRunSwitch(coordinator, entry.entry_id))
    async_add_entities(entities)
