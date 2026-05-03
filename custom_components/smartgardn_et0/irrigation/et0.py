"""ET₀ (Reference Evapotranspiration) computation with fallback chain."""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

from custom_components.smartgardn_et0.et0_calculator import (
    calc_et0_fao56,
    calc_et0_hargreaves,
    convert_solar_to_w_m2,
)
from custom_components.smartgardn_et0.weather.sensors import get_daily_minmax, read_sensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def compute_et0_with_fallback(
    hass: HomeAssistant,
    entry: ConfigEntry,
    storage_data: dict | None = None,
) -> tuple[float, str, bool]:
    """Compute ET₀ with fallback chain.

    Returns:
        (et0_value, method_used, fallback_active)
        - et0_value: Computed ET₀ in mm/day
        - method_used: "fao56", "hargreaves", or "last_known"
        - fallback_active: True if using fallback method
    """
    today = date.today()

    # Get temperature: new single temp_entity or old min/max
    temp_entity = entry.data.get("temp_entity")
    if temp_entity:
        t_min, t_max = await get_daily_minmax(hass, temp_entity)
    else:
        # Fallback to old min/max entities for backwards compatibility
        t_min = read_sensor(hass, entry.data.get("temp_min_entity"))
        t_max = read_sensor(hass, entry.data.get("temp_max_entity"))

    if not t_min or not t_max:
        _LOGGER.error("No temperature data, using last known or 0")
        if storage_data and "globals" in storage_data:
            last_et0 = storage_data["globals"].get("et0_last_known", 0.0)
        else:
            last_et0 = 0.0
        return last_et0, "last_known", True

    et_method = entry.data.get("et_methode", "fao56")

    # Try primary method (FAO56 Penman-Monteith)
    if et_method == "fao56":
        # Get humidity: new single entity or old min/max
        humidity_entity = entry.data.get("humidity_entity")
        if humidity_entity:
            rh_min, rh_max = await get_daily_minmax(hass, humidity_entity)
        else:
            rh_min = read_sensor(hass, entry.data.get("humidity_min_entity"))
            rh_max = read_sensor(hass, entry.data.get("humidity_max_entity"))

        # Get solar radiation and convert
        solar_raw = read_sensor(hass, entry.data.get("solar_entity"))
        solar_sensor_type = entry.data.get("solar_sensor_type", "w_m2")
        solar = convert_solar_to_w_m2(solar_raw, solar_sensor_type) if solar_raw else None

        # Get wind speed
        wind = read_sensor(hass, entry.data.get("wind_entity"))

        # If all inputs available, use FAO56
        if all(x is not None for x in [rh_min, rh_max, solar, wind]):
            et0 = calc_et0_fao56(
                t_min,
                t_max,
                rh_min,
                rh_max,
                solar,
                wind,
                entry.data["latitude"],
                entry.data["elevation"],
                today.timetuple().tm_yday,
            )
            if storage_data and "globals" in storage_data:
                storage_data["globals"]["et0_last_known"] = et0
            return et0, "fao56", False

        # Fallback to Hargreaves (simpler, only needs temperature)
        _LOGGER.warning("PM inputs missing, falling back to Hargreaves")
        et0 = calc_et0_hargreaves(
            t_min, t_max, entry.data["latitude"], today.timetuple().tm_yday
        )
        if storage_data and "globals" in storage_data:
            storage_data["globals"]["et0_last_known"] = et0
        return et0, "hargreaves", True

    # If method is already Hargreaves
    if (et_method == "hargreaves" or et_method == "haude") and t_min and t_max:
        et0 = calc_et0_hargreaves(
            t_min, t_max, entry.data["latitude"], today.timetuple().tm_yday
        )
        if storage_data and "globals" in storage_data:
            storage_data["globals"]["et0_last_known"] = et0
        return et0, "hargreaves", False

    # Fallback to last known value
    if storage_data and "globals" in storage_data:
        last_et0 = storage_data["globals"].get("et0_last_known", 0.0)
    else:
        last_et0 = 0.0
    return last_et0, "last_known", True
