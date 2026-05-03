"""Scheduling calculations for zone watering."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

from homeassistant.util.dt import UTC

from custom_components.smartgardn_et0.gts_calculator import needs_watering
from custom_components.smartgardn_et0.utils.time_helpers import (
    WEEKDAYS,
    check_rain_skip,
    get_next_enabled_weekday,
)

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


def compute_next_start_semi(
    zone_id: str,
    weekdays_enabled: dict[str, bool],
    start_time: time,
    forecast: list,
    rain_threshold_mm: float,
) -> datetime | None:
    """Compute next start for Semi-Automatik mode.

    Args:
        zone_id: Zone identifier
        weekdays_enabled: Dict with enabled weekdays
        start_time: Time to start watering
        forecast: DWD forecast list
        rain_threshold_mm: Rain threshold to skip watering

    Returns:
        Next scheduled start datetime or None
    """
    next_weekday = get_next_enabled_weekday(weekdays_enabled, date.today())
    if not next_weekday:
        return None

    # Check rain for days 1 and 2 only
    today = date.today()
    for i in range(1, 8):
        check_date = today + timedelta(days=i)
        weekday_name = WEEKDAYS[check_date.weekday()]
        if weekdays_enabled.get(weekday_name, True):
            # Check rain forecast for this day (only days 1 and 2)
            if i <= 2 and check_rain_skip(forecast, i, rain_threshold_mm):
                _LOGGER.info(
                    "Zone %s: semi-mode skip day %d, rain forecast >= threshold",
                    zone_id,
                    i,
                )
                continue  # Skip this day, find next
            return datetime.combine(check_date, start_time, tzinfo=UTC)
    return None


def compute_next_start_voll(
    zone_id: str,
    nfk_aktuell: float,
    nfk_max: float,
    schwellwert_pct: float,
    start_time: time,
    forecast: list,
    rain_threshold_mm: float,
) -> datetime | None:
    """Compute next start for Voll-Automatik mode.

    Args:
        zone_id: Zone identifier
        nfk_aktuell: Current water availability in soil
        nfk_max: Maximum water availability
        schwellwert_pct: Watering threshold percentage
        start_time: Time to start watering
        forecast: DWD forecast list
        rain_threshold_mm: Rain threshold to skip watering

    Returns:
        Next scheduled start datetime or None
    """
    if needs_watering(nfk_aktuell, nfk_max, schwellwert_pct):
        # Watering needed — check rain forecast
        if check_rain_skip(forecast, 1, rain_threshold_mm):
            _LOGGER.info(
                "Zone %s: skip today, rain forecast >= threshold", zone_id
            )
            if check_rain_skip(forecast, 2, rain_threshold_mm):
                _LOGGER.info(
                    "Zone %s: skip tomorrow too, rain forecast >= threshold", zone_id
                )
                return None  # Recheck after 2 days
            # Start day-after-tomorrow
            return datetime.combine(
                date.today() + timedelta(days=2), start_time, tzinfo=UTC
            )
        # No rain expected, start immediately
        return datetime.now(UTC) + timedelta(minutes=1)
    return None


def compute_next_start_ansaat(
    zone_id: str,
    ansaat_von: time,
    ansaat_bis: time,
    forecast: list,
    rain_threshold_mm: float,
) -> datetime | None:
    """Compute next start for Ansaat (seed watering) mode.

    Ansaat watering happens daily between ansaat_von and ansaat_bis.

    Args:
        zone_id: Zone identifier
        ansaat_von: Start time for daily watering
        ansaat_bis: End time for daily watering
        forecast: DWD forecast list
        rain_threshold_mm: Rain threshold to skip watering

    Returns:
        Next scheduled start datetime or None
    """
    today = date.today()

    for i in range(0, 7):
        check_date = today + timedelta(days=i)
        # Check if rain too high for this day
        if i <= 2 and check_rain_skip(forecast, max(i, 1), rain_threshold_mm):
            _LOGGER.info(
                "Zone %s: ansaat skip day, rain forecast >= threshold", zone_id
            )
            continue

        # Check if within ansaat window for today
        if i == 0:
            now = datetime.now(UTC)
            if now.time() < ansaat_von:
                return datetime.combine(check_date, ansaat_von, tzinfo=UTC)
            elif now.time() < ansaat_bis:
                return now  # Start immediately (within window)
            # Today's window passed, check tomorrow
            continue

        # For future days, start at ansaat_von
        return datetime.combine(check_date, ansaat_von, tzinfo=UTC)

    return None
