"""Number platform for smartgardn_et0."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.smartgardn_et0.const import DOMAIN
from custom_components.smartgardn_et0.coordinator import IrrigationCoordinator


class IrrigationNumberEntity(CoordinatorEntity[IrrigationCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        key: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None,
        default: float,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._key = key
        self._attr_unique_id = f"{entry_id}_{zone_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._default = default
        if zone_id not in coordinator._zone_numbers:
            coordinator._zone_numbers[zone_id] = {}
        coordinator._zone_numbers[zone_id].setdefault(key, default)

    @property
    def native_value(self) -> float:
        return self.coordinator._zone_numbers.get(self._zone_id, {}).get(self._key, self._default)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator._zone_numbers.setdefault(self._zone_id, {})[self._key] = value
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[NumberEntity] = []

    for zone_id, zone_cfg in entry.data.get("zones", {}).items():
        schwellwert_default = float(zone_cfg.get("schwellwert_pct", 50))
        zielwert_default = float(zone_cfg.get("zielwert_pct", 80))

        number_specs: list[tuple[str, float, float, float, str | None, float]] = [
            ("dauer", 1, 240, 1, "min", 30.0),
            ("schwellwert", 10, 90, 5, "%", schwellwert_default),
            ("zielwert", 20, 100, 5, "%", zielwert_default),
            ("manuelle_dauer", 1, 240, 1, "min", 15.0),
            ("cs_zyklen", 0, 10, 1, None, 0.0),
            ("cs_pause", 1, 60, 1, "min", 10.0),
            ("ansaat_intervall", 15, 240, 15, "min", 60.0),
            ("ansaat_dauer", 1, 60, 1, "min", 5.0),
            ("ansaat_laufzeit_tage", 0, 90, 1, None, 14.0),
        ]

        for key, min_v, max_v, step, unit, default in number_specs:
            entities.append(
                IrrigationNumberEntity(
                    coordinator, entry.entry_id, zone_id, key, min_v, max_v, step, unit, default
                )
            )

    async_add_entities(entities)
