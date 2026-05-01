"""Button platform for smartgardn_et0."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.smartgardn_et0.const import DOMAIN
from custom_components.smartgardn_et0.coordinator import IrrigationCoordinator


class IrrigationZoneStartButton(CoordinatorEntity[IrrigationCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Manuell starten"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_start_button"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    async def async_press(self) -> None:
        dauer_min = self.coordinator._zone_numbers.get(self._zone_id, {}).get(
            "manuelle_dauer", 15.0
        )
        await self.coordinator.start_zone_manual(self._zone_id, dauer_min)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[ButtonEntity] = [
        IrrigationZoneStartButton(coordinator, entry.entry_id, zone_id)
        for zone_id in entry.data.get("zones", {})
    ]
    async_add_entities(entities)
