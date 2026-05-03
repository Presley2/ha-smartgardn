"""Sensor platform for smartgardn_et0."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.smartgardn_et0.const import DOMAIN
from custom_components.smartgardn_et0.coordinator import IrrigationCoordinator


class IrrigationNFKSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "NFk aktuell"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_nfk"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        storage = self.coordinator.data.get("storage")
        if not storage:
            return None
        zone = storage["zones"].get(self._zone_id)
        if not zone:
            return None
        return zone["nfk_aktuell"]

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        zone_verlauf = self.coordinator.data.get("zone_verlauf", {})
        verlauf = zone_verlauf.get(self._zone_id, [])
        return {"verlauf": verlauf}


class IrrigationNFKProzentSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "NFk Prozent"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_cfg = zone_cfg
        self._attr_unique_id = f"{entry_id}_{zone_id}_nfk_prozent"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        storage = self.coordinator.data.get("storage")
        if not storage:
            return None
        zone = storage["zones"].get(self._zone_id)
        if not zone:
            return None
        nfk_max = self._zone_cfg.get("nfk_max", 0)
        if not nfk_max or nfk_max <= 0:
            return None
        return zone["nfk_aktuell"] / nfk_max * 100


class IrrigationEtcHeuteSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "ETc heute"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_etc_heute"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("etc_heute", {}).get(self._zone_id)


class IrrigationRegenHeuteSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Regen heute"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_regen_heute"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("regen_heute", {}).get(self._zone_id)


class IrrigationBeregnungHeuteSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Beregnung heute"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_beregnung_heute"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("beregnung_heute", {}).get(self._zone_id)


class IrrigationTimerSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "min"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Timer verbleibend"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_timer"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("timer_remaining_min", {}).get(self._zone_id)


class IrrigationCsZyklenRestSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "CS Zyklen Rest"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_cs_zyklen_rest"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> int:
        if not self.coordinator.data:
            return 0
        return self.coordinator.data.get("cs_zyklen_rest", {}).get(self._zone_id, 0)


class IrrigationNaechsterStartSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_name = "Nächster Start"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_naechster_start"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> datetime | None:
        if not self.coordinator.data:
            return None
        storage = self.coordinator.data.get("storage")
        if not storage:
            return None
        zone = storage["zones"].get(self._zone_id)
        if not zone:
            return None
        iso = zone["scheduling"].get("next_start_dt")
        if not iso:
            return None
        try:
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is None:
                import datetime as _dt

                dt = dt.replace(tzinfo=_dt.UTC)
            return dt
        except (ValueError, TypeError):
            return None


class IrrigationBucketPrognoseSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Bucket Prognose"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry_id}_{zone_id}_bucket_prognose"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("bucket_prognose", {}).get(self._zone_id)


class IrrigationEt0FaoSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm/day"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "ET0 FAO-56"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_et0_fao"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("et0_fao")


class IrrigationEt0HargreavesSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm/day"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "ET0 Hargreaves"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_et0_hargreaves"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("et0_hargreaves")


class IrrigationEt0HaudeSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm/day"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "ET0 Haude"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_et0_haude"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("et0_haude")


class IrrigationGtsSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "GTS"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_gts"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        storage = self.coordinator.data.get("storage")
        if not storage:
            return None
        return storage["globals"]["gts"]


class IrrigationEt0ForecastMorgenSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm/day"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "ET₀ Prognose morgen"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_et0_forecast_morgen"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        forecast = self.coordinator.data.get("dwd_forecast", [])
        if len(forecast) > 0:
            return forecast[0].et0_mm
        return None


class IrrigationEt0ForecastUebermorgeSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm/day"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "ET₀ Prognose übermorgen"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_et0_forecast_uebermorgen"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        forecast = self.coordinator.data.get("dwd_forecast", [])
        if len(forecast) > 1:
            return forecast[1].et0_mm
        return None


class IrrigationEt0ForecastTag3Sensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm/day"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "ET₀ Prognose Tag 3"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_et0_forecast_tag3"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        forecast = self.coordinator.data.get("dwd_forecast", [])
        if len(forecast) > 2:
            return forecast[2].et0_mm
        return None


class IrrigationRegenForecastMorgenSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Regen Prognose morgen"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_regen_forecast_morgen"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        forecast = self.coordinator.data.get("dwd_forecast", [])
        if len(forecast) > 0:
            return forecast[0].precip_sum
        return None


class IrrigationRegenForecastUebermorgeSensor(
    CoordinatorEntity[IrrigationCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Regen Prognose übermorgen"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_regen_forecast_uebermorgen"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        forecast = self.coordinator.data.get("dwd_forecast", [])
        if len(forecast) > 1:
            return forecast[1].precip_sum
        return None


class IrrigationRegenForecastTag3Sensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Regen Prognose Tag 3"

    def __init__(self, coordinator: IrrigationCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_regen_forecast_tag3"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        forecast = self.coordinator.data.get("dwd_forecast", [])
        if len(forecast) > 2:
            return forecast[2].precip_sum
        return None


class IrrigationNfkForecastMorgenSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "NFK Prognose morgen"

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry_id: str,
        zone_id: str,
        zone_cfg: dict,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_cfg = zone_cfg
        self._attr_unique_id = f"{entry_id}_{zone_id}_nfk_forecast_morgen"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{zone_id}")})

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        storage = self.coordinator.data.get("storage")
        if not storage:
            return None
        zone = storage["zones"].get(self._zone_id)
        if not zone:
            return None
        forecast = self.coordinator.data.get("dwd_forecast", [])
        if len(forecast) == 0:
            return None

        nfk_aktuell = zone["nfk_aktuell"]
        nfk_max = self._zone_cfg.get("nfk_max", 150)
        etc_morgen = forecast[0].et0_mm
        regen_morgen = forecast[0].precip_sum

        nfk_morgen = nfk_aktuell - etc_morgen + regen_morgen
        nfk_morgen = max(0.0, min(nfk_max, nfk_morgen))
        return nfk_morgen


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: IrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = []

    for zone_id, zone_cfg in entry.data.get("zones", {}).items():
        entities.append(IrrigationNFKSensor(coordinator, entry.entry_id, zone_id, zone_cfg))
        entities.append(IrrigationNFKProzentSensor(coordinator, entry.entry_id, zone_id, zone_cfg))
        entities.append(IrrigationEtcHeuteSensor(coordinator, entry.entry_id, zone_id, zone_cfg))
        entities.append(IrrigationRegenHeuteSensor(coordinator, entry.entry_id, zone_id, zone_cfg))
        entities.append(
            IrrigationBeregnungHeuteSensor(coordinator, entry.entry_id, zone_id, zone_cfg)
        )
        entities.append(IrrigationTimerSensor(coordinator, entry.entry_id, zone_id, zone_cfg))
        entities.append(
            IrrigationCsZyklenRestSensor(coordinator, entry.entry_id, zone_id, zone_cfg)
        )
        entities.append(
            IrrigationNaechsterStartSensor(coordinator, entry.entry_id, zone_id, zone_cfg)
        )
        entities.append(
            IrrigationBucketPrognoseSensor(coordinator, entry.entry_id, zone_id, zone_cfg)
        )
        if entry.data.get("dwd_forecast_enabled"):
            entities.append(
                IrrigationNfkForecastMorgenSensor(coordinator, entry.entry_id, zone_id, zone_cfg)
            )

    entities.append(IrrigationEt0FaoSensor(coordinator, entry.entry_id))
    entities.append(IrrigationGtsSensor(coordinator, entry.entry_id))

    if entry.data.get("dwd_forecast_enabled"):
        entities.append(IrrigationEt0ForecastMorgenSensor(coordinator, entry.entry_id))
        entities.append(IrrigationEt0ForecastUebermorgeSensor(coordinator, entry.entry_id))
        entities.append(IrrigationEt0ForecastTag3Sensor(coordinator, entry.entry_id))
        entities.append(IrrigationRegenForecastMorgenSensor(coordinator, entry.entry_id))
        entities.append(IrrigationRegenForecastUebermorgeSensor(coordinator, entry.entry_id))
        entities.append(IrrigationRegenForecastTag3Sensor(coordinator, entry.entry_id))

    et_methode = entry.options.get("et_methode") or entry.data.get("et_methode")
    if et_methode == "hargreaves":
        entities.append(IrrigationEt0HargreavesSensor(coordinator, entry.entry_id))
    if et_methode == "haude":
        entities.append(IrrigationEt0HaudeSensor(coordinator, entry.entry_id))

    async_add_entities(entities)
