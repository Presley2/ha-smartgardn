"""DWD forecast module — fetch MOSMIX-S data via brightsky.dev and calculate ET₀.

Weather data sourced from:
- Deutscher Wetterdienst (DWD) MOSMIX-S model
- brightsky.dev API (free wrapper, CC0 Public Domain)
- See THIRD_PARTY_LICENSES.md for complete attribution and terms
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.smartgardn_et0.et0_calculator import (
    calc_et0_fao56,
    calc_et0_hargreaves,
    calc_ka,
    convert_solar_to_w_m2,
)

_LOGGER = logging.getLogger(__name__)
BRIGHTSKY_API_URL = "https://api.brightsky.dev/weather"
BRIGHTSKY_TIMEOUT_S = 10


@dataclass
class ForecastDay:
    """Single forecast day result."""

    date: date
    t_min: float
    t_max: float
    rh_mean: float
    wind_mean: float
    solar_mean: float  # W/m²
    precip_sum: float  # mm
    et0_mm: float  # calculated


async def fetch_dwd_forecast(
    hass: HomeAssistant,
    latitude: float,
    longitude: float,
    elevation: float,
    days: int = 3,
) -> list[ForecastDay]:
    """Fetch DWD forecast from brightsky.dev and calculate ET₀.

    Args:
        hass: Home Assistant instance
        latitude: Location latitude (decimal degrees)
        longitude: Location longitude (decimal degrees)
        elevation: Elevation in metres
        days: Number of forecast days (default 3)

    Returns:
        List of ForecastDay objects (empty list if API fails)
    """
    try:
        session = async_get_clientsession(hass)
        results = []

        for offset in range(days):
            forecast_date = date.today() + timedelta(days=offset + 1)
            try:
                data = await _fetch_brightsky_day(
                    session, latitude, longitude, forecast_date
                )
                if data:
                    et0 = await _calculate_et0_from_forecast(
                        data, latitude, elevation, forecast_date
                    )
                    results.append(
                        ForecastDay(
                            date=forecast_date,
                            t_min=data["t_min"],
                            t_max=data["t_max"],
                            rh_mean=data["rh_mean"],
                            wind_mean=data["wind_mean"],
                            solar_mean=data["solar_mean"],
                            precip_sum=data["precip_sum"],
                            et0_mm=et0,
                        )
                    )
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Brightsky timeout for date %s (lat=%f, lon=%f)",
                    forecast_date,
                    latitude,
                    longitude,
                )
                continue
            except Exception as err:
                _LOGGER.error(
                    "Brightsky error for date %s: %s",
                    forecast_date,
                    err,
                )
                continue

        if results:
            _LOGGER.debug("DWD forecast: %d days retrieved", len(results))
        return results

    except Exception as err:
        _LOGGER.error("DWD forecast failed: %s", err)
        return []


async def _fetch_brightsky_day(
    session, latitude: float, longitude: float, forecast_date: date
) -> dict | None:
    """Fetch single day from brightsky.dev API.

    Returns dict with keys: t_min, t_max, rh_mean, wind_mean, solar_mean, precip_sum
    """
    params = {
        "lat": latitude,
        "lon": longitude,
        "date": forecast_date.isoformat(),
    }

    try:
        async with asyncio.timeout(BRIGHTSKY_TIMEOUT_S):
            async with session.get(BRIGHTSKY_API_URL, params=params) as resp:
                if resp.status != 200:
                    _LOGGER.warning(
                        "Brightsky returned %d for %s", resp.status, forecast_date
                    )
                    return None

                json_data = await resp.json()
                weather = json_data.get("weather", [])

                if not weather:
                    _LOGGER.debug("No weather data for %s", forecast_date)
                    return None

                # Aggregate hourly data to daily
                temps = []
                humidities = []
                winds = []
                solars = []
                precips = []

                for hour in weather:
                    if hour.get("temperature") is not None:
                        temps.append(float(hour["temperature"]))
                    if hour.get("relative_humidity") is not None:
                        humidities.append(float(hour["relative_humidity"]))
                    if hour.get("wind_speed") is not None:
                        winds.append(float(hour["wind_speed"]))
                    if hour.get("solar_radiation_instant") is not None:
                        solars.append(float(hour["solar_radiation_instant"]))
                    if hour.get("precipitation") is not None:
                        precips.append(float(hour["precipitation"]))

                if not temps:
                    return None

                return {
                    "t_min": min(temps),
                    "t_max": max(temps),
                    "rh_mean": sum(humidities) / len(humidities) if humidities else 50.0,
                    "wind_mean": sum(winds) / len(winds) if winds else 2.0,
                    "solar_mean": sum(solars) / len(solars) if solars else 100.0,
                    "precip_sum": sum(precips),
                }

    except asyncio.TimeoutError:
        raise
    except Exception as err:
        _LOGGER.error("Brightsky fetch error: %s", err)
        return None


async def _calculate_et0_from_forecast(
    data: dict, latitude: float, elevation: float, forecast_date: date
) -> float:
    """Calculate ET₀ from forecast data using FAO-56 or Hargreaves fallback."""
    t_min = data["t_min"]
    t_max = data["t_max"]
    rh_mean = data["rh_mean"]
    wind_mean = data["wind_mean"]
    solar_w_m2 = data["solar_mean"]
    day_of_year = forecast_date.timetuple().tm_yday

    # Try FAO-56 if we have solar data
    if solar_w_m2 > 0:
        try:
            et0 = calc_et0_fao56(
                t_min=t_min,
                t_max=t_max,
                rh_min=rh_mean - 5.0,  # approximate min from mean
                rh_max=rh_mean + 5.0,  # approximate max from mean
                solar_w_m2=solar_w_m2,
                wind_m_s=wind_mean,
                latitude=latitude,
                elevation=elevation,
                day_of_year=day_of_year,
            )
            _LOGGER.debug("ET₀ FAO-56 (forecast %s): %.2f mm/day", forecast_date, et0)
            return float(max(0.0, et0))
        except Exception as err:
            _LOGGER.debug("FAO-56 failed for forecast, falling back to Hargreaves: %s", err)

    # Fallback: Hargreaves (only needs temperature)
    try:
        et0 = calc_et0_hargreaves(
            t_min=t_min,
            t_max=t_max,
            latitude=latitude,
            day_of_year=day_of_year,
        )
        _LOGGER.debug(
            "ET₀ Hargreaves (forecast %s): %.2f mm/day", forecast_date, et0
        )
        return float(max(0.0, et0))
    except Exception as err:
        _LOGGER.error("ET₀ calculation failed for forecast %s: %s", forecast_date, err)
        return 0.0
