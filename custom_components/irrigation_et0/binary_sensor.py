"""Binary sensor platform for irrigation_et0."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.irrigation_et0.const import DOMAIN
from custom_components.irrigation_et0.coordinator import IrrigationCoordinator


class IrrigationFrostWarnungSensor(CoordinatorEntity[IrrigationCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.COLD
    _attr_name = "Frostwarnung"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_frost_warnung"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("frost_active", False)


class IrrigationTrafoProblemSensor(CoordinatorEntity[IrrigationCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Trafo Problem"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_trafo_problem"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("trafo_state") == "unavailable"


class IrrigationEtFallbackActiveSensor(
    CoordinatorEntity[IrrigationCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "ET Fallback aktiv"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_et_fallback_active"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("et_fallback_active", False)


class IrrigationSensorenOkSensor(CoordinatorEntity[IrrigationCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Sensoren OK"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_sensoren_ok"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return True
        return self.coordinator.data.get("sensoren_ok", True)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            IrrigationFrostWarnungSensor(coordinator, entry.entry_id),
            IrrigationTrafoProblemSensor(coordinator, entry.entry_id),
            IrrigationEtFallbackActiveSensor(coordinator, entry.entry_id),
            IrrigationSensorenOkSensor(coordinator, entry.entry_id),
        ]
    )
