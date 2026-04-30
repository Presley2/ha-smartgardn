"""Select platform for irrigation_et0."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.irrigation_et0.const import DOMAIN, ET_METHODS, MODES
from custom_components.irrigation_et0.coordinator import IrrigationCoordinator


class IrrigationZoneModusSelect(CoordinatorEntity[IrrigationCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Modus"
    _attr_options = MODES

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_modus"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def current_option(self) -> str:
        return self.coordinator._zone_modus.get(self._zone_id, "aus")

    async def async_select_option(self, option: str) -> None:
        self.coordinator._zone_modus[self._zone_id] = option
        await self.coordinator.async_request_refresh()


class IrrigationEtMethodeSelect(CoordinatorEntity[IrrigationCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "ET Methode"
    _attr_options = ET_METHODS

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_et_methode"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def current_option(self) -> str:
        if self.coordinator.data:
            storage = self.coordinator.data.get("storage")
            if storage:
                return storage["globals"].get("et_methode", "fao56")
        return self.coordinator.entry.options.get("et_methode") or self.coordinator.entry.data.get(
            "et_methode", "fao56"
        )

    async def async_select_option(self, option: str) -> None:
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(self.coordinator.entry.entry_id)
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SelectEntity] = []

    for zone_id in entry.data.get("zones", {}):
        entities.append(IrrigationZoneModusSelect(coordinator, entry.entry_id, zone_id))

    entities.append(IrrigationEtMethodeSelect(coordinator, entry.entry_id))
    async_add_entities(entities)
